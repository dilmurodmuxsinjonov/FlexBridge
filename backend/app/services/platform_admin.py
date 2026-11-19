"""Super Admin, Staff Role Grants, Operator Directories, Feature Flags Read & Governance Queues (API-126..API-135).

Contracts:
- API-126: GET  /api/v1/operator/staff-grants
- API-127: POST /api/v1/operator/staff-grants
- API-128: POST /api/v1/operator/staff-grants/{grant_id}/revoke
- API-129: GET  /api/v1/operator/directory/users
- API-130: GET  /api/v1/operator/directory/organizations
- API-131: GET  /api/v1/operator/directory/institutions
- API-132: GET  /api/v1/operator/feature-flags
- API-133: GET  /api/v1/operator/privacy-requests
- API-134: GET  /api/v1/operator/recovery-requests
- API-135: POST /api/v1/operator/recovery-requests/{request_id}/decide
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Text, and_, cast, exists, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import SENSITIVE_ROLES
from app.db.storage import now, table, transaction
from app.services.authority import account_authority, platform_authority
from app.services.feature_flag_admin import (
    FLAG_ALIASES,
    PROTECTED_FLAGS,
    R1_ENABLEABLE,
    R2_FLAG,
    flag_admin_service,
)
from app.services.operator_security import VALID_PLATFORM_ROLES
from app.services.privacy import VALID_STATUSES as PRIVACY_VALID_STATUSES

SYSTEM_AUTHORITY_USER_ID = "00000000-0000-0000-0000-000000000001"
PERMANENT_GRANT_THRESHOLD_DAYS = 365
RECOVERY_REQUEST_WINDOW = timedelta(days=7)
RECOVERY_APPROVAL_TTL = timedelta(hours=72)

STAFF_GRANTS_READ_ROLES = frozenset({"ADMIN", "SECURITY_LEAD"})
DIRECTORY_USERS_ROLES = frozenset({"ADMIN", "SECURITY_LEAD", "OPERATIONS", "AUDITOR"})
DIRECTORY_ENTITIES_ROLES = frozenset({"ADMIN", "OPERATIONS", "MODERATOR", "AUDITOR"})
FEATURE_FLAGS_READ_ROLES = frozenset({"ADMIN", "AUDITOR", "OPERATIONS"})
PRIVACY_READ_ROLES = frozenset({"ADMIN", "COMPLIANCE", "SUPPORT", "MODERATOR"})

PLATFORM_ROLE_DESCRIPTIONS: dict[str, str] = {
    "ADMIN": "Platforma Super Admini: xodim rollari, feature flaglar va xavfsizlik boshqaruvi",
    "MODERATOR": "Mustaqil KYB, OTM tayinlovlari, e'lonlar va apellyatsiyalar moderatori",
    "FINANCE": "To'lov solishtiruvi, moliyaviy hisobot va ikki bosqichli qaytarish tasdig'i",
    "SUPPORT": "Foydalanuvchi murojaatlari, GDPR va parol tiklash so'rovlari operatori",
    "AUDITOR": "O'zgarmas audit jurnali, kataloglar va tizim holatining faqat o'qish kuzatuvchisi",
    "COMPLIANCE": "Saqlash siyosatlari, maxfiylik so'rovlari va korxona egasi vorisligi nazorati",
    "OPERATIONS": "Insidentlar, zaxira tiklash (DR) mashqlari va platforma telemetriyasi operatori",
    "SECURITY_LEAD": "Xavfsizlik rahbari: favqulodda break-glass so'rovlari va sessiyani bekor qilish",
}

ROLE_AUTHORITY_MATRIX_ITEMS: tuple[dict[str, Any], ...] = (
    {
        "scope_kind": "SELF",
        "role_code": "CANDIDATE",
        "title": "Nomzod / Talaba",
        "capabilities": "Profil, dars jadvali, e'lonlarga ariza, amaliyot kundaligi, chat va shaxsiy murojaatlar",
        "granted_by": "Ro'yxatdan o'tishda avtomatik beriladi (POST /api/v1/auth/register)",
        "revoked_by": "Hisob bloklanganda yoki GDPR o'chirish bajarilganda to'xtatiladi",
        "mfa_required": False,
        "dual_control": False,
    },
    {
        "scope_kind": "ORG",
        "role_code": "OWNER",
        "title": "Korxona egasi",
        "capabilities": "KYB hujjatlari, xodimlarni taklif qilish/bekor qilish, e'lonlar, amaliyot va billing boshqaruvi",
        "granted_by": "Boshlang'ich: MODERATOR KYB tasdig'i; Qo'shimcha/Vorislik: OWNER + MODERATOR (+ COMPLIANCE)",
        "revoked_by": "Korxona OWNER (MFA) yoki OWNER transferi; oxirgi OWNER himoyalangan (409)",
        "mfa_required": True,
        "dual_control": True,
    },
    {
        "scope_kind": "ORG",
        "role_code": "HR",
        "title": "Korxona HR mutaxassisi",
        "capabilities": "Nomzod arizalari, intervyular, ish takliflari va ishga qabul jarayoni",
        "granted_by": "Korxona OWNER (MFA) taklifi + xodimning MFA roziligi (yoki ikkinchi OWNER tasdig'i)",
        "revoked_by": "Korxona OWNER (MFA) a'zolikni bekor qilishi orqali",
        "mfa_required": False,
        "dual_control": True,
    },
    {
        "scope_kind": "ORG",
        "role_code": "HOST_COORDINATOR",
        "title": "Amaliyot qabul koordinatori",
        "capabilities": "Amaliyot takliflari, joylashtirish (placement), mentor tayinlash va kundalik nazorati",
        "granted_by": "Korxona OWNER (MFA) taklifi + xodimning MFA roziligi",
        "revoked_by": "Korxona OWNER (MFA) a'zolikni bekor qilishi orqali",
        "mfa_required": False,
        "dual_control": True,
    },
    {
        "scope_kind": "ORG",
        "role_code": "MENTOR",
        "title": "Amaliyot mentori",
        "capabilities": "Biriktirilgan amaliyotchi talabalar kundaligi va yakuniy natijalarini tasdiqlash",
        "granted_by": "Korxona OWNER (MFA) taklifi + joylashtirishga biriktirish",
        "revoked_by": "Korxona OWNER (MFA) a'zolikni bekor qilishi orqali",
        "mfa_required": False,
        "dual_control": False,
    },
    {
        "scope_kind": "ORG",
        "role_code": "BILLING",
        "title": "Korxona moliya vakili",
        "capabilities": "Tarif buyurtmalari, hisob-fakturalar, to'lovlar va qaytarish (refund) so'rovi yaratish",
        "granted_by": "Korxona OWNER (MFA) taklifi + xodimning MFA roziligi",
        "revoked_by": "Korxona OWNER (MFA) a'zolikni bekor qilishi orqali",
        "mfa_required": True,
        "dual_control": False,
    },
    {
        "scope_kind": "INSTITUTION",
        "role_code": "COORDINATOR",
        "title": "OTM / Universitet koordinatori",
        "capabilities": "OTM katalogi, talabalikni tasdiqlash, o'qituvchi tayinlash, akademik qarorlar va parol tiklash tasdig'i",
        "granted_by": "Boshlang'ich ariza -> platforma MODERATOR (MFA) tasdig'i -> shaxsiy MFA rozilik",
        "revoked_by": "OTM COORDINATOR (MFA) tayinlovni bekor qilishi orqali",
        "mfa_required": True,
        "dual_control": True,
    },
    {
        "scope_kind": "INSTITUTION",
        "role_code": "TEACHER",
        "title": "OTM o'qituvchisi (rahbar)",
        "capabilities": "Biriktirilgan talabalarning amaliyot kundaligi va hisobotlarini tekshirish",
        "granted_by": "OTM COORDINATOR (MFA) taqdimnomasi -> MODERATOR tasdig'i -> shaxsiy rozilik",
        "revoked_by": "OTM COORDINATOR (MFA) tayinlovni bekor qilishi orqali",
        "mfa_required": False,
        "dual_control": True,
    },
    {
        "scope_kind": "PLATFORM",
        "role_code": "ADMIN",
        "title": "Platforma Super Admini",
        "capabilities": "Platforma xodimlariga rol berish/bekor qilish, feature flaglar, kataloglar, insidentlar, audit va tiklash navbatlari",
        "granted_by": "Ilk admin: bootstrap CLI (System Authority anchor); keyingi adminlar: ADMIN (MFA)",
        "revoked_by": "Boshqa ADMIN (MFA); o'zini va oxirgi faol ADMINni bekor qilish taqiqlangan",
        "mfa_required": True,
        "dual_control": True,
    },
    {
        "scope_kind": "PLATFORM",
        "role_code": "MODERATOR",
        "title": "Platforma moderatori",
        "capabilities": "Korxona KYB, OTM tayinlovlari, talabalik tasdig'i, e'lonlar moderatsiyasi, apellyatsiyalar",
        "granted_by": "ADMIN (MFA) doimiy berishi yoki Break-Glass (ikki tomonlama tasdiq)",
        "revoked_by": "ADMIN (MFA)",
        "mfa_required": True,
        "dual_control": True,
    },
    {
        "scope_kind": "PLATFORM",
        "role_code": "FINANCE",
        "title": "Platforma moliyachisi",
        "capabilities": "To'lov solishtiruvi, moliyaviy xulosa va ikki bosqichli qaytarish (refund) tasdig'i",
        "granted_by": "ADMIN (MFA) yoki Break-Glass",
        "revoked_by": "ADMIN (MFA)",
        "mfa_required": True,
        "dual_control": True,
    },
    {
        "scope_kind": "PLATFORM",
        "role_code": "SUPPORT",
        "title": "Qo'llab-quvvatlash operatori",
        "capabilities": "Tiketlar navbati, GDPR maxfiylik so'rovlari va parol tiklash navbatini ko'rib chiqish",
        "granted_by": "ADMIN (MFA) yoki Break-Glass",
        "revoked_by": "ADMIN (MFA)",
        "mfa_required": True,
        "dual_control": True,
    },
    {
        "scope_kind": "PLATFORM",
        "role_code": "AUDITOR",
        "title": "Xavfsizlik auditori",
        "capabilities": "O'zgarmas audit jurnali, kataloglar, DR mashqlari, analitika va flag holatini faqat o'qish",
        "granted_by": "ADMIN (MFA) yoki Break-Glass",
        "revoked_by": "ADMIN (MFA)",
        "mfa_required": False,
        "dual_control": False,
    },
    {
        "scope_kind": "PLATFORM",
        "role_code": "COMPLIANCE",
        "title": "Komplayens ofitseri",
        "capabilities": "Ma'lumot saqlash (retention) baholash, pilot tayyorligi, GDPR ko'rish va egasiz korxona vorisligi 2-bosqichi",
        "granted_by": "ADMIN (MFA) yoki Break-Glass",
        "revoked_by": "ADMIN (MFA)",
        "mfa_required": True,
        "dual_control": True,
    },
    {
        "scope_kind": "PLATFORM",
        "role_code": "OPERATIONS",
        "title": "Operatsiyalar muhandisi",
        "capabilities": "Insident e'lon qilish, sessiyalarni favqulodda yopish, DR mashqlari, analitika va kataloglar",
        "granted_by": "ADMIN (MFA) yoki Break-Glass",
        "revoked_by": "ADMIN (MFA)",
        "mfa_required": False,
        "dual_control": False,
    },
    {
        "scope_kind": "PLATFORM",
        "role_code": "SECURITY_LEAD",
        "title": "Xavfsizlik rahbari",
        "capabilities": "Xodim rollarini ko'rish, foydalanuvchilar katalogi, break-glass so'rovlari va favqulodda sessiya yopish",
        "granted_by": "ADMIN (MFA) yoki Break-Glass",
        "revoked_by": "ADMIN (MFA)",
        "mfa_required": False,
        "dual_control": True,
    },
)


class PlatformAdminError(Exception):
    """Structured error raised by PlatformAdminService."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def mask_contact_value(value: str) -> str:
    """Return a masked email or phone string without exposing raw contact details."""
    clean = (value or "").strip()
    if not clean:
        return "***"
    if "@" in clean:
        local, domain = clean.split("@", 1)
        return (local[:2] + "***@" + domain) if len(local) > 2 else ("***@" + domain)
    if len(clean) >= 11:
        return clean[:6] + "***" + clean[-4:]
    if len(clean) >= 7:
        return clean[:4] + "***" + clean[-2:]
    return "***"


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _clamp_limit(limit: int, *, default: int = 40, maximum: int = 100) -> int:
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def _parse_uuid(raw: str, code: str = "INVALID_UUID", message: str = "UUID formati noto'g'ri") -> str:
    try:
        return str(UUID(str(raw).strip()))
    except (TypeError, ValueError) as exc:
        raise PlatformAdminError(code, message, status_code=422) from exc


def _iso(val: datetime | None) -> str | None:
    return val.isoformat() if val is not None else None


def _advisory_lock(conn: Any, key: str) -> None:
    conn.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key})


class PlatformAdminService:
    """Service layer for Super Admin governance, directories, flags read, and recovery/privacy queues."""

    def __init__(self) -> None:
        self.audit_store = AppendOnlyAuditStore()

    def _require_platform_read_roles(self, conn: Any, actor: ActorContext, allowed_roles: frozenset[str]) -> None:
        """Verify active session (+ MFA if actor holds any SENSITIVE_ROLES) and active DB platform grant."""
        account_authority(conn, actor)
        grants, roles = table("platform_role_grants"), table("role_catalog")
        found = conn.execute(
            select(grants.c.id)
            .select_from(grants.join(roles, grants.c.role_id == roles.c.id))
            .where(
                grants.c.user_id == str(actor.user_id),
                grants.c.revoked_at.is_(None),
                grants.c.expires_at > now(),
                grants.c.granted_by_id != grants.c.user_id,
                roles.c.scope_kind == "PLATFORM",
                roles.c.code.in_(allowed_roles),
            )
            .with_for_update(read=True, of=(grants, roles))
        ).first()
        if not found:
            raise PlatformAdminError("FORBIDDEN_ROLE", "Ushbu amal uchun tegishli operator roli talab qilinadi", 403)

    def _batch_masked_contacts(self, conn: Any, user_ids: list[str]) -> tuple[dict[str, str], dict[str, list[dict[str, str]]]]:
        """Batch-load verified unrevoked contacts per user_id, returning primary masked and full masked list."""
        if not user_ids:
            return {}, {}
        uc = table("user_contacts")
        rows = conn.execute(
            select(uc.c.user_id, uc.c.channel, uc.c.normalized_value)
            .where(
                uc.c.user_id.in_(user_ids),
                uc.c.verified_at.is_not(None),
                uc.c.revoked_at.is_(None),
            )
            .order_by(uc.c.is_primary.desc(), uc.c.created_at.asc())
        ).mappings().all()
        primary: dict[str, str] = {}
        all_masked: dict[str, list[dict[str, str]]] = {}
        for r in rows:
            uid = str(r["user_id"])
            masked = mask_contact_value(str(r["normalized_value"] or ""))
            if uid not in primary:
                primary[uid] = masked
            all_masked.setdefault(uid, []).append({"channel": r["channel"], "masked": masked})
        return primary, all_masked

    def _batch_grant_reasons(self, conn: Any, grant_ids: list[str]) -> dict[str, str]:
        """Fetch latest grant/revoke audit reasons for a list of grant IDs."""
        if not grant_ids:
            return {}
        audits = table("audit_events")
        rows = conn.execute(
            select(audits.c.object_key, audits.c.scope_snapshot)
            .where(
                audits.c.object_type == "platform_role_grant",
                audits.c.object_key.in_(grant_ids),
                audits.c.action.in_(("PLATFORM_ROLE_GRANTED", "PLATFORM_ROLE_REVOKED", "SUPER_ADMIN_BOOTSTRAPPED")),
            )
            .order_by(audits.c.occurred_at.desc(), audits.c.id.desc())
        ).mappings().all()
        reasons: dict[str, str] = {}
        for r in rows:
            key = str(r["object_key"])
            if key in reasons:
                continue
            snap = r["scope_snapshot"] if isinstance(r["scope_snapshot"], dict) else {}
            reason = snap.get("reason")
            if isinstance(reason, str) and reason.strip():
                reasons[key] = reason.strip()
        return reasons

    # -------------------------------------------------------------------------
    # API-126: GET /api/v1/operator/staff-grants
    # -------------------------------------------------------------------------
    def list_staff_grants(self, *, actor: ActorContext) -> dict[str, Any]:
        with transaction() as conn:
            self._require_platform_read_roles(conn, actor, STAFF_GRANTS_READ_ROLES)
            now_utc = now()
            t_grants = table("platform_role_grants")
            t_roles = table("role_catalog")
            t_users = table("users")
            u_target = t_users.alias("u_target")
            u_granter = t_users.alias("u_granter")

            role_rows = conn.execute(
                select(t_roles.c.id, t_roles.c.code, t_roles.c.description)
                .where(t_roles.c.scope_kind == "PLATFORM")
            ).mappings().all()
            role_by_code = {r["code"]: dict(r) for r in role_rows}

            active_rows = conn.execute(
                select(
                    t_grants.c.id,
                    t_grants.c.user_id,
                    t_grants.c.role_id,
                    t_grants.c.granted_by_id,
                    t_grants.c.created_at,
                    t_grants.c.expires_at,
                    t_roles.c.code.label("role_code"),
                    u_target.c.display_name.label("user_display_name"),
                    u_target.c.status.label("user_status"),
                    u_granter.c.display_name.label("granter_display_name"),
                )
                .select_from(
                    t_grants.join(t_roles, t_grants.c.role_id == t_roles.c.id)
                    .join(u_target, t_grants.c.user_id == u_target.c.id)
                    .join(u_granter, t_grants.c.granted_by_id == u_granter.c.id)
                )
                .where(
                    t_roles.c.scope_kind == "PLATFORM",
                    t_grants.c.revoked_at.is_(None),
                    t_grants.c.expires_at > now_utc,
                )
                .order_by(t_grants.c.created_at.desc(), t_grants.c.id.desc())
            ).mappings().all()

            revoked_rows = conn.execute(
                select(
                    t_grants.c.id,
                    t_grants.c.user_id,
                    t_grants.c.role_id,
                    t_grants.c.granted_by_id,
                    t_grants.c.created_at,
                    t_grants.c.expires_at,
                    t_grants.c.revoked_at,
                    t_roles.c.code.label("role_code"),
                    u_target.c.display_name.label("user_display_name"),
                    u_granter.c.display_name.label("granter_display_name"),
                )
                .select_from(
                    t_grants.join(t_roles, t_grants.c.role_id == t_roles.c.id)
                    .join(u_target, t_grants.c.user_id == u_target.c.id)
                    .join(u_granter, t_grants.c.granted_by_id == u_granter.c.id)
                )
                .where(
                    t_roles.c.scope_kind == "PLATFORM",
                    t_grants.c.revoked_at.is_not(None),
                )
                .order_by(t_grants.c.revoked_at.desc(), t_grants.c.id.desc())
                .limit(30)
            ).mappings().all()

            all_user_ids = sorted({str(r["user_id"]) for r in active_rows} | {str(r["user_id"]) for r in revoked_rows})
            all_grant_ids = [str(r["id"]) for r in active_rows] + [str(r["id"]) for r in revoked_rows]
            primary_contacts, _ = self._batch_masked_contacts(conn, all_user_ids)
            reasons = self._batch_grant_reasons(conn, all_grant_ids)

            active_counts: dict[str, int] = {}
            active_grants: list[dict[str, Any]] = []
            for r in active_rows:
                code = r["role_code"]
                active_counts[code] = active_counts.get(code, 0) + 1
                is_perm = bool(
                    r["expires_at"]
                    and r["created_at"]
                    and (r["expires_at"] - r["created_at"]) >= timedelta(days=PERMANENT_GRANT_THRESHOLD_DAYS)
                )
                gid = str(r["id"])
                uid = str(r["user_id"])
                active_grants.append(
                    {
                        "id": gid,
                        "user_id": uid,
                        "display_name": r["user_display_name"],
                        "user_status": r["user_status"],
                        "masked_contact": primary_contacts.get(uid),
                        "role_code": code,
                        "role_id": str(r["role_id"]),
                        "granted_by_id": str(r["granted_by_id"]),
                        "granter_display_name": r["granter_display_name"],
                        "created_at": _iso(r["created_at"]),
                        "expires_at": _iso(r["expires_at"]),
                        "is_permanent": is_perm,
                        "reason": reasons.get(gid),
                    }
                )

            recent_revoked = [
                {
                    "id": str(r["id"]),
                    "user_id": str(r["user_id"]),
                    "display_name": r["user_display_name"],
                    "masked_contact": primary_contacts.get(str(r["user_id"])),
                    "role_code": r["role_code"],
                    "granted_by_id": str(r["granted_by_id"]),
                    "granter_display_name": r["granter_display_name"],
                    "created_at": _iso(r["created_at"]),
                    "expires_at": _iso(r["expires_at"]),
                    "revoked_at": _iso(r["revoked_at"]),
                    "reason": reasons.get(str(r["id"])),
                }
                for r in revoked_rows
            ]

            roles_catalog = [
                {
                    "id": str(role_by_code[code]["id"]) if code in role_by_code else None,
                    "code": code,
                    "scope_kind": "PLATFORM",
                    "description": PLATFORM_ROLE_DESCRIPTIONS.get(code)
                    or (role_by_code[code]["description"] if code in role_by_code else code),
                    "mfa_required": code in SENSITIVE_ROLES,
                    "active_count": active_counts.get(code, 0),
                }
                for code in sorted(VALID_PLATFORM_ROLES)
            ]

            return {
                "ok": True,
                "contract_id": "API-126",
                "roles_catalog": roles_catalog,
                "active_grants": active_grants,
                "recent_revoked": recent_revoked,
                "role_matrix": list(ROLE_AUTHORITY_MATRIX_ITEMS),
            }

    # -------------------------------------------------------------------------
    # API-127: POST /api/v1/operator/staff-grants
    # -------------------------------------------------------------------------
    def grant_staff_role(
        self,
        *,
        actor: ActorContext,
        user_id: str,
        role_code: str,
        reason: str,
        duration_days: int = 3650,
    ) -> dict[str, Any]:
        target_uuid = _parse_uuid(user_id, code="INVALID_USER_ID", message="user_id UUID formati noto'g'ri")
        role_clean = (role_code or "").strip().upper()
        if role_clean not in VALID_PLATFORM_ROLES:
            raise PlatformAdminError("INVALID_PLATFORM_ROLE", f"Noto'g'ri platforma roli: {role_clean}", 422)
        reason_clean = (reason or "").strip()
        if not 10 <= len(reason_clean) <= 1000:
            raise PlatformAdminError("INVALID_REASON", "Asos (reason) 10 dan 1000 belgigacha bo'lishi shart", 422)
        if type(duration_days) is not int or not 1 <= duration_days <= 3650:
            raise PlatformAdminError("INVALID_DURATION_DAYS", "duration_days 1 dan 3650 kungacha bo'lishi shart", 422)

        actor_uuid = _parse_uuid(actor.user_id, code="MFA_REQUIRED", message="Noto'g'ri aktor identifikatori")

        with transaction() as conn:
            if role_clean == "ADMIN":
                _advisory_lock(conn, "platform-admin-revoke:ADMIN")
            _advisory_lock(conn, f"platform-grant:{target_uuid}:{role_clean}")
            account_authority(conn, actor, require_mfa=True)
            platform_authority(conn, actor, "ADMIN")

            if target_uuid == actor_uuid:
                raise PlatformAdminError(
                    "SELF_ROLE_GRANT_FORBIDDEN",
                    "Operator o'z hisobiga platforma roli bera olmaydi",
                    403,
                )

            t_users = table("users")
            target_user = conn.execute(
                select(t_users.c.id, t_users.c.status)
                .where(t_users.c.id == target_uuid)
                .with_for_update(read=True)
            ).mappings().first()
            if not target_user:
                raise PlatformAdminError("USER_NOT_FOUND", "Maqsadli foydalanuvchi topilmadi", 404)
            if target_user["status"] != "ACTIVE":
                raise PlatformAdminError(
                    "TARGET_USER_NOT_ACTIVE",
                    "Faqat faol (ACTIVE) foydalanuvchiga rol berish mumkin",
                    409,
                )

            t_roles = table("role_catalog")
            now_utc = now()
            conn.execute(
                insert(t_roles)
                .values(
                    id=str(uuid4()),
                    created_at=now_utc,
                    updated_at=now_utc,
                    code=role_clean,
                    scope_kind="PLATFORM",
                    description=PLATFORM_ROLE_DESCRIPTIONS.get(role_clean, f"Platform {role_clean} role"),
                )
                .on_conflict_do_nothing(index_elements=["code"])
            )
            role_row = conn.execute(
                select(t_roles.c.id, t_roles.c.scope_kind).where(t_roles.c.code == role_clean)
            ).mappings().one()
            if role_row["scope_kind"] != "PLATFORM":
                raise PlatformAdminError("ROLE_SCOPE_MISMATCH", "Rol doirasi PLATFORM emas", 409)
            role_id = str(role_row["id"])

            t_grants = table("platform_role_grants")
            existing = conn.execute(
                select(t_grants.c.id)
                .where(
                    t_grants.c.user_id == target_uuid,
                    t_grants.c.role_id == role_id,
                    t_grants.c.revoked_at.is_(None),
                    t_grants.c.expires_at > now_utc,
                )
                .with_for_update()
            ).first()
            if existing:
                raise PlatformAdminError(
                    "GRANT_ALREADY_ACTIVE",
                    "Ushbu foydalanuvchida bu rol allaqachon faol",
                    409,
                )

            grant_id = str(uuid4())
            expires_at = now_utc + timedelta(days=duration_days)
            conn.execute(
                t_grants.insert().values(
                    id=grant_id,
                    created_at=now_utc,
                    updated_at=now_utc,
                    user_id=target_uuid,
                    role_id=role_id,
                    granted_by_id=actor_uuid,
                    expires_at=expires_at,
                    revoked_at=None,
                )
            )

            self.audit_store.append_audit_event(
                actor_id=actor_uuid,
                action="PLATFORM_ROLE_GRANTED",
                entity_type="platform_role_grant",
                entity_id=grant_id,
                metadata={
                    "target_user_id": target_uuid,
                    "role_code": role_clean,
                    "duration_days": duration_days,
                    "expires_at": expires_at.isoformat(),
                    "reason": reason_clean,
                },
            )

            return {
                "ok": True,
                "contract_id": "API-127",
                "grant_id": grant_id,
                "user_id": target_uuid,
                "role_code": role_clean,
                "expires_at": expires_at.isoformat(),
            }

    # -------------------------------------------------------------------------
    # API-128: POST /api/v1/operator/staff-grants/{grant_id}/revoke
    # -------------------------------------------------------------------------
    def revoke_staff_grant(
        self,
        *,
        actor: ActorContext,
        grant_id: str,
        reason: str,
    ) -> dict[str, Any]:
        grant_uuid = _parse_uuid(grant_id, code="INVALID_GRANT_ID", message="grant_id UUID formati noto'g'ri")
        reason_clean = (reason or "").strip()
        if not 10 <= len(reason_clean) <= 1000:
            raise PlatformAdminError("INVALID_REASON", "Bekor qilish asosi (reason) 10 dan 1000 belgigacha bo'lishi shart", 422)
        actor_uuid = _parse_uuid(actor.user_id, code="MFA_REQUIRED", message="Noto'g'ri aktor identifikatori")

        with transaction() as conn:
            # Serialize ADMIN revocations before authority locks so parallel revokes cannot bypass last-admin guard.
            _advisory_lock(conn, "platform-admin-revoke:ADMIN")
            account_authority(conn, actor, require_mfa=True)
            platform_authority(conn, actor, "ADMIN")

            t_grants = table("platform_role_grants")
            t_roles = table("role_catalog")
            t_users = table("users")

            grant = conn.execute(
                select(
                    t_grants.c.id,
                    t_grants.c.user_id,
                    t_grants.c.role_id,
                    t_grants.c.expires_at,
                    t_grants.c.revoked_at,
                    t_roles.c.code.label("role_code"),
                    t_roles.c.scope_kind.label("scope_kind"),
                )
                .select_from(t_grants.join(t_roles, t_grants.c.role_id == t_roles.c.id))
                .where(t_grants.c.id == grant_uuid)
                .with_for_update(of=(t_grants,))
            ).mappings().first()

            if not grant or grant["scope_kind"] != "PLATFORM":
                raise PlatformAdminError("GRANT_NOT_FOUND", "Platforma roli granti topilmadi", 404)
            if grant["revoked_at"] is not None:
                raise PlatformAdminError("GRANT_ALREADY_REVOKED", "Ushbu rol granti allaqachon bekor qilingan", 409)

            now_utc = now()
            role_code = grant["role_code"]
            target_uid = str(grant["user_id"])

            if role_code == "ADMIN":
                active_admin_grants = conn.execute(
                    select(t_grants.c.id)
                    .select_from(
                        t_grants.join(t_roles, t_grants.c.role_id == t_roles.c.id)
                        .join(t_users, t_grants.c.user_id == t_users.c.id)
                    )
                    .where(
                        t_roles.c.scope_kind == "PLATFORM",
                        t_roles.c.code == "ADMIN",
                        t_grants.c.revoked_at.is_(None),
                        t_grants.c.expires_at > now_utc,
                        t_grants.c.granted_by_id != t_grants.c.user_id,
                        t_users.c.status == "ACTIVE",
                    )
                ).scalars().all()
                remaining_active = [str(gid) for gid in active_admin_grants if str(gid) != grant_uuid]
                if len(remaining_active) == 0:
                    raise PlatformAdminError(
                        "LAST_ADMIN_CANNOT_BE_REVOKED",
                        "Tizimdagi oxirgi faol Super Admin (ADMIN) rolini bekor qilib bo'lmaydi",
                        409,
                    )
                if target_uid == actor_uuid:
                    raise PlatformAdminError(
                        "SELF_ADMIN_REVOKE_FORBIDDEN",
                        "Super Admin o'zining faol ADMIN rolini bekor qila olmaydi",
                        403,
                    )

            conn.execute(
                t_grants.update()
                .where(t_grants.c.id == grant_uuid, t_grants.c.revoked_at.is_(None))
                .values(revoked_at=now_utc, updated_at=now_utc)
            )

            self.audit_store.append_audit_event(
                actor_id=actor_uuid,
                action="PLATFORM_ROLE_REVOKED",
                entity_type="platform_role_grant",
                entity_id=grant_uuid,
                metadata={
                    "target_user_id": target_uid,
                    "role_code": role_code,
                    "reason": reason_clean,
                },
            )

            return {
                "ok": True,
                "contract_id": "API-128",
                "grant_id": grant_uuid,
                "user_id": target_uid,
                "role_code": role_code,
                "revoked_at": now_utc.isoformat(),
                "status": "REVOKED",
            }

    # -------------------------------------------------------------------------
    # API-129: GET /api/v1/operator/directory/users
    # -------------------------------------------------------------------------
    def directory_users(
        self,
        *,
        actor: ActorContext,
        q: str | None = None,
        role: str | None = None,
        limit: int = 40,
    ) -> dict[str, Any]:
        safe_limit = _clamp_limit(limit, default=40, maximum=100)
        with transaction() as conn:
            self._require_platform_read_roles(conn, actor, DIRECTORY_USERS_ROLES)
            now_utc = now()
            u = table("users")
            uc = table("user_contacts")
            grants = table("platform_role_grants")
            roles = table("role_catalog")
            mfa = table("mfa_credentials")

            conditions: list[Any] = [u.c.id != SYSTEM_AUTHORITY_USER_ID]

            if q and q.strip():
                pattern = f"%{_escape_like(q.strip())}%"
                conditions.append(
                    or_(
                        u.c.display_name.ilike(pattern, escape="\\"),
                        cast(u.c.id, Text).ilike(pattern, escape="\\"),
                        exists(
                            select(uc.c.id).where(
                                uc.c.user_id == u.c.id,
                                uc.c.revoked_at.is_(None),
                                uc.c.normalized_value.ilike(pattern, escape="\\"),
                            )
                        ),
                    )
                )

            if role and role.strip() and role.strip().upper() != "ALL":
                role_clean = role.strip().upper()
                conditions.append(
                    exists(
                        select(grants.c.id)
                        .select_from(grants.join(roles, grants.c.role_id == roles.c.id))
                        .where(
                            grants.c.user_id == u.c.id,
                            grants.c.revoked_at.is_(None),
                            grants.c.expires_at > now_utc,
                            roles.c.scope_kind == "PLATFORM",
                            roles.c.code == role_clean,
                        )
                    )
                )

            rows = conn.execute(
                select(u.c.id, u.c.display_name, u.c.status, u.c.created_at, u.c.last_login_at)
                .where(and_(*conditions))
                .order_by(u.c.created_at.desc(), u.c.id.desc())
                .limit(safe_limit)
            ).mappings().all()

            user_ids = [str(r["id"]) for r in rows]
            primary_contacts, _ = self._batch_masked_contacts(conn, user_ids)

            mfa_users: set[str] = set()
            roles_by_user: dict[str, list[str]] = {}
            if user_ids:
                mfa_users = {
                    str(uid)
                    for uid in conn.execute(
                        select(mfa.c.user_id)
                        .where(
                            mfa.c.user_id.in_(user_ids),
                            mfa.c.kind.in_(("TOTP", "PASSKEY")),
                            mfa.c.verified_at.is_not(None),
                            mfa.c.revoked_at.is_(None),
                        )
                        .distinct()
                    ).scalars().all()
                }
                role_rows = conn.execute(
                    select(grants.c.user_id, roles.c.code)
                    .select_from(grants.join(roles, grants.c.role_id == roles.c.id))
                    .where(
                        grants.c.user_id.in_(user_ids),
                        grants.c.revoked_at.is_(None),
                        grants.c.expires_at > now_utc,
                        roles.c.scope_kind == "PLATFORM",
                    )
                    .order_by(roles.c.code.asc())
                ).mappings().all()
                for rr in role_rows:
                    uid = str(rr["user_id"])
                    code = rr["code"]
                    if code not in roles_by_user.setdefault(uid, []):
                        roles_by_user[uid].append(code)

            items = [
                {
                    "id": str(r["id"]),
                    "display_name": r["display_name"],
                    "status": r["status"],
                    "masked_contact": primary_contacts.get(str(r["id"])),
                    "mfa_enabled": str(r["id"]) in mfa_users,
                    "platform_roles": roles_by_user.get(str(r["id"]), []),
                    "created_at": _iso(r["created_at"]),
                    "last_login_at": _iso(r["last_login_at"]),
                }
                for r in rows
            ]
            return {"ok": True, "contract_id": "API-129", "items": items}

    # -------------------------------------------------------------------------
    # API-130: GET /api/v1/operator/directory/organizations
    # -------------------------------------------------------------------------
    def directory_organizations(
        self,
        *,
        actor: ActorContext,
        q: str | None = None,
        status: str | None = None,
        limit: int = 40,
    ) -> dict[str, Any]:
        safe_limit = _clamp_limit(limit, default=40, maximum=100)
        with transaction() as conn:
            self._require_platform_read_roles(conn, actor, DIRECTORY_ENTITIES_ROLES)
            orgs = table("organizations")
            members = table("org_memberships")
            opps = table("opportunities")

            conditions: list[Any] = []
            if q and q.strip():
                pattern = f"%{_escape_like(q.strip())}%"
                conditions.append(
                    or_(
                        orgs.c.public_name.ilike(pattern, escape="\\"),
                        orgs.c.legal_name.ilike(pattern, escape="\\"),
                        orgs.c.tax_id.ilike(pattern, escape="\\"),
                        orgs.c.region.ilike(pattern, escape="\\"),
                    )
                )
            if status and status.strip() and status.strip().upper() != "ALL":
                conditions.append(orgs.c.status == status.strip().upper())

            where_clause = and_(*conditions) if conditions else True
            rows = conn.execute(
                select(
                    orgs.c.id,
                    orgs.c.public_name,
                    orgs.c.legal_name,
                    orgs.c.tax_id,
                    orgs.c.region,
                    orgs.c.status,
                    orgs.c.created_at,
                )
                .where(where_clause)
                .order_by(orgs.c.created_at.desc(), orgs.c.id.desc())
                .limit(safe_limit)
            ).mappings().all()

            org_ids = [str(r["id"]) for r in rows]
            members_count: dict[str, int] = {}
            opps_count: dict[str, int] = {}
            if org_ids:
                for mr in conn.execute(
                    select(members.c.organization_id, func.count().label("cnt"))
                    .where(
                        members.c.organization_id.in_(org_ids),
                        members.c.status == "ACTIVE",
                        members.c.revoked_at.is_(None),
                    )
                    .group_by(members.c.organization_id)
                ).mappings():
                    members_count[str(mr["organization_id"])] = int(mr["cnt"])

                for opr in conn.execute(
                    select(opps.c.organization_id, func.count().label("cnt"))
                    .where(
                        opps.c.organization_id.in_(org_ids),
                        opps.c.status == "PUBLISHED",
                        opps.c.closed_at.is_(None),
                    )
                    .group_by(opps.c.organization_id)
                ).mappings():
                    opps_count[str(opr["organization_id"])] = int(opr["cnt"])

            items = [
                {
                    "id": str(r["id"]),
                    "public_name": r["public_name"],
                    "legal_name": r["legal_name"],
                    "tax_id": r["tax_id"],
                    "region": r["region"],
                    "verification_status": r["status"],
                    "active_members_count": members_count.get(str(r["id"]), 0),
                    "published_opportunities_count": opps_count.get(str(r["id"]), 0),
                    "created_at": _iso(r["created_at"]),
                }
                for r in rows
            ]
            return {"ok": True, "contract_id": "API-130", "items": items}

    # -------------------------------------------------------------------------
    # API-131: GET /api/v1/operator/directory/institutions
    # -------------------------------------------------------------------------
    def directory_institutions(
        self,
        *,
        actor: ActorContext,
        q: str | None = None,
        status: str | None = None,
        limit: int = 40,
    ) -> dict[str, Any]:
        safe_limit = _clamp_limit(limit, default=40, maximum=100)
        with transaction() as conn:
            self._require_platform_read_roles(conn, actor, DIRECTORY_ENTITIES_ROLES)
            insts = table("institutions")
            enrollments = table("enrollments")
            members = table("institution_memberships")
            dr = table("domain_records")

            conditions: list[Any] = []
            if q and q.strip():
                pattern = f"%{_escape_like(q.strip())}%"
                conditions.append(
                    or_(
                        insts.c.name.ilike(pattern, escape="\\"),
                        insts.c.registry_code.ilike(pattern, escape="\\"),
                        insts.c.region.ilike(pattern, escape="\\"),
                        exists(
                            select(dr.c.record_id).where(
                                dr.c.namespace == "institution_directory_profile",
                                dr.c.record_id == cast(insts.c.id, Text),
                                or_(
                                    dr.c.payload_json["official_name"].astext.ilike(pattern, escape="\\"),
                                    dr.c.payload_json["short_name"].astext.ilike(pattern, escape="\\"),
                                ),
                            )
                        ),
                    )
                )
            if status and status.strip() and status.strip().upper() != "ALL":
                conditions.append(insts.c.status == status.strip().upper())

            where_clause = and_(*conditions) if conditions else True
            rows = conn.execute(
                select(
                    insts.c.id,
                    insts.c.name,
                    insts.c.registry_code,
                    insts.c.region,
                    insts.c.status,
                    insts.c.created_at,
                )
                .where(where_clause)
                .order_by(insts.c.created_at.desc(), insts.c.id.desc())
                .limit(safe_limit)
            ).mappings().all()

            inst_ids = [str(r["id"]) for r in rows]
            profiles: dict[str, dict[str, Any]] = {}
            student_counts: dict[str, int] = {}
            staff_counts: dict[str, int] = {}

            if inst_ids:
                for p in conn.execute(
                    select(dr.c.record_id, dr.c.payload_json).where(
                        dr.c.namespace == "institution_directory_profile",
                        dr.c.record_id.in_(inst_ids),
                    )
                ).mappings():
                    if isinstance(p["payload_json"], dict):
                        profiles[str(p["record_id"])] = p["payload_json"]

                for sr in conn.execute(
                    select(
                        enrollments.c.institution_id,
                        func.count(func.distinct(enrollments.c.candidate_id)).label("cnt"),
                    )
                    .where(
                        enrollments.c.institution_id.in_(inst_ids),
                        enrollments.c.status == "VERIFIED",
                    )
                    .group_by(enrollments.c.institution_id)
                ).mappings():
                    student_counts[str(sr["institution_id"])] = int(sr["cnt"])

                for st in conn.execute(
                    select(members.c.institution_id, func.count().label("cnt"))
                    .where(
                        members.c.institution_id.in_(inst_ids),
                        members.c.status == "ACTIVE",
                        members.c.revoked_at.is_(None),
                    )
                    .group_by(members.c.institution_id)
                ).mappings():
                    staff_counts[str(st["institution_id"])] = int(st["cnt"])

            items = []
            for r in rows:
                iid = str(r["id"])
                stored = profiles.get(iid, {})
                items.append(
                    {
                        "id": iid,
                        "official_name": stored.get("official_name") or r["name"],
                        "short_name": stored.get("short_name") or None,
                        "registry_code": r["registry_code"],
                        "tax_id": stored.get("tax_id") or None,
                        "region": r["region"],
                        "verification_status": r["status"],
                        "verified_students_count": student_counts.get(iid, 0),
                        "active_staff_count": staff_counts.get(iid, 0),
                        "created_at": _iso(r["created_at"]),
                    }
                )
            return {"ok": True, "contract_id": "API-131", "items": items}

    # -------------------------------------------------------------------------
    # API-132: GET /api/v1/operator/feature-flags
    # -------------------------------------------------------------------------
    def list_feature_flags(self, *, actor: ActorContext) -> dict[str, Any]:
        with transaction() as conn:
            self._require_platform_read_roles(conn, actor, FEATURE_FLAGS_READ_ROLES)
            flags_tbl = table("feature_flags")
            events_tbl = table("feature_flag_change_events")

            flag_rows = {
                r["code"]: dict(r)
                for r in conn.execute(select(flags_tbl)).mappings().all()
            }
            latest_versions = {
                str(r["flag_id"]): int(r["max_version"])
                for r in conn.execute(
                    select(
                        events_tbl.c.flag_id,
                        func.max(events_tbl.c.version).label("max_version"),
                    ).group_by(events_tbl.c.flag_id)
                ).mappings().all()
            }

            catalog_specs: list[tuple[str, str, bool, bool, str | None]] = [
                *((code, "R1", True, False, None) for code in R1_ENABLEABLE),
                *((code, "PROTECTED", False, True, None) for code in PROTECTED_FLAGS),
                (R2_FLAG, "R2", False, True, None),
                *((alias_code, "PROTECTED", False, True, target_code) for alias_code, target_code in FLAG_ALIASES.items()),
            ]

            items: list[dict[str, Any]] = []
            for code, category, mutable, disable_only, alias_of in catalog_specs:
                row = flag_rows.get(code)
                version = latest_versions.get(str(row["id"]), 0) if row is not None else 0
                enabled = bool(flag_admin_service.effective_enabled(code, conn=conn))
                items.append(
                    {
                        "code": code,
                        "category": category,
                        "enabled": enabled,
                        "version": version,
                        "mutable": mutable,
                        "disable_only": disable_only,
                        "updated_at": _iso(row["updated_at"]) if row else None,
                        "reason": row["reason"] if row else None,
                        "alias_of": alias_of,
                    }
                )
            return {"ok": True, "contract_id": "API-132", "items": items}

    # -------------------------------------------------------------------------
    # API-133: GET /api/v1/operator/privacy-requests
    # -------------------------------------------------------------------------
    def list_privacy_requests(
        self,
        *,
        actor: ActorContext,
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        safe_limit = _clamp_limit(limit, default=50, maximum=100)
        with transaction() as conn:
            self._require_platform_read_roles(conn, actor, PRIVACY_READ_ROLES)
            reqs = table("privacy_requests")
            users = table("users")

            conditions: list[Any] = []
            if status and status.strip() and status.strip().upper() != "ALL":
                s_clean = status.strip().upper()
                if s_clean not in PRIVACY_VALID_STATUSES:
                    raise PlatformAdminError("INVALID_PRIVACY_STATUS", f"Noto'g'ri status: {s_clean}", 422)
                conditions.append(reqs.c.status == s_clean)

            where_clause = and_(*conditions) if conditions else True
            rows = conn.execute(
                select(
                    reqs.c.id,
                    reqs.c.user_id,
                    users.c.display_name,
                    reqs.c.kind,
                    reqs.c.status,
                    reqs.c.reason,
                    reqs.c.due_at,
                    reqs.c.created_at,
                    reqs.c.resolved_at,
                )
                .select_from(reqs.join(users, users.c.id == reqs.c.user_id))
                .where(where_clause)
                .order_by(reqs.c.created_at.desc(), reqs.c.id.desc())
                .limit(safe_limit)
            ).mappings().all()

            items = [
                {
                    "id": str(r["id"]),
                    "user_id": str(r["user_id"]),
                    "display_name": r["display_name"],
                    "kind": r["kind"],
                    "status": r["status"],
                    "reason": r["reason"],
                    "due_at": _iso(r["due_at"]),
                    "created_at": _iso(r["created_at"]),
                    "resolved_at": _iso(r["resolved_at"]),
                }
                for r in rows
            ]
            return {"ok": True, "contract_id": "API-133", "items": items}

    # -------------------------------------------------------------------------
    # API-134: GET /api/v1/operator/recovery-requests
    # -------------------------------------------------------------------------
    def list_recovery_requests(
        self,
        *,
        actor: ActorContext,
        status: str | None = "PENDING_REVIEW",
        limit: int = 50,
    ) -> dict[str, Any]:
        safe_limit = _clamp_limit(limit, default=50, maximum=100)
        actor_uuid = _parse_uuid(actor.user_id, code="MFA_REQUIRED", message="Noto'g'ri aktor identifikatori")

        with transaction() as conn:
            account_authority(conn, actor, require_mfa=True)
            platform_authority(conn, actor, "ADMIN", "SUPPORT")

            r = table("recovery_requests")
            u = table("users")
            conditions: list[Any] = [
                r.c.kind == "ACCOUNT_ACCESS",
                r.c.user_id.is_not(None),
                r.c.user_id != actor_uuid,
            ]
            status_clean = (status or "").strip().upper()
            if status_clean and status_clean != "ALL":
                conditions.append(r.c.status == status_clean)

            order_col = r.c.created_at.asc() if status_clean == "PENDING_REVIEW" else r.c.created_at.desc()
            rows = conn.execute(
                select(
                    r.c.id,
                    r.c.user_id,
                    u.c.display_name,
                    r.c.status,
                    r.c.created_at,
                    r.c.resolved_at,
                    r.c.reviewer_id,
                )
                .select_from(r.join(u, u.c.id == r.c.user_id))
                .where(and_(*conditions))
                .order_by(order_col, r.c.id.asc())
                .limit(safe_limit)
            ).mappings().all()

            user_ids = sorted({str(row["user_id"]) for row in rows})
            _, all_masked = self._batch_masked_contacts(conn, user_ids)

            items = [
                {
                    "id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "display_name": row["display_name"],
                    "status": row["status"],
                    "masked_contacts": all_masked.get(str(row["user_id"]), []),
                    "created_at": _iso(row["created_at"]),
                    "resolved_at": _iso(row["resolved_at"]),
                    "reviewer_id": str(row["reviewer_id"]) if row["reviewer_id"] else None,
                }
                for row in rows
            ]
            return {"ok": True, "contract_id": "API-134", "items": items}

    # -------------------------------------------------------------------------
    # API-135: POST /api/v1/operator/recovery-requests/{request_id}/decide
    # -------------------------------------------------------------------------
    def decide_recovery_request(
        self,
        *,
        actor: ActorContext,
        request_id: str,
        decision: str,
        reason: str,
    ) -> dict[str, Any]:
        req_uuid = _parse_uuid(request_id, code="INVALID_RECOVERY_ID", message="request_id UUID formati noto'g'ri")
        decision_clean = (decision or "").strip().upper()
        if decision_clean not in ("APPROVE", "REJECT"):
            raise PlatformAdminError("INVALID_DECISION", "decision faqat APPROVE yoki REJECT bo'lishi kerak", 422)
        reason_clean = (reason or "").strip()
        if not 15 <= len(reason_clean) <= 2000:
            raise PlatformAdminError(
                "RECOVERY_DECISION_REASON_REQUIRED",
                "Qaror asosi 15 dan 2000 belgigacha bo'lishi shart",
                422,
            )
        actor_uuid = _parse_uuid(actor.user_id, code="MFA_REQUIRED", message="Noto'g'ri aktor identifikatori")

        with transaction() as conn:
            r = table("recovery_requests")
            req = conn.execute(
                select(r).where(r.c.id == req_uuid).with_for_update()
            ).mappings().first()

            account_authority(conn, actor, require_mfa=True)
            platform_authority(conn, actor, "ADMIN", "SUPPORT")

            if req is None:
                raise PlatformAdminError("RECOVERY_REQUEST_NOT_AVAILABLE", "Tiklash so'rovi topilmadi", 404)

            if req["user_id"] is not None and str(req["user_id"]) == actor_uuid:
                raise PlatformAdminError(
                    "SELF_REVIEW_FORBIDDEN",
                    "Operator o'zining parol tiklash so'rovini ko'rib chiqa olmaydi",
                    403,
                )

            stamp = now()
            eligible = (
                req["kind"] == "ACCOUNT_ACCESS"
                and req["status"] == "PENDING_REVIEW"
                and req["user_id"] is not None
                and req["created_at"] > stamp - RECOVERY_REQUEST_WINDOW
            )
            if not eligible:
                raise PlatformAdminError("RECOVERY_REQUEST_NOT_AVAILABLE", "Tiklash so'rovi mavjud emas yoki eskirgan", 404)

            if decision_clean == "APPROVE":
                target_user = conn.execute(
                    select(table("users").c.status).where(table("users").c.id == req["user_id"])
                ).mappings().first()
                if not target_user or target_user["status"] != "ACTIVE":
                    raise PlatformAdminError(
                        "TARGET_USER_NOT_ACTIVE",
                        "Faqat faol hisob uchun parol tiklash tasdiqlanadi",
                        409,
                    )

            status = "APPROVED" if decision_clean == "APPROVE" else "REJECTED"
            conn.execute(
                r.update()
                .where(r.c.id == req_uuid, r.c.status == "PENDING_REVIEW")
                .values(status=status, reviewer_id=actor_uuid, resolved_at=stamp, updated_at=stamp)
            )

            self.audit_store.append_audit_event(
                actor_id=actor_uuid,
                action=f"ACCOUNT_RECOVERY_{status}_BY_OPERATOR",
                entity_type="recovery_request",
                entity_id=req_uuid,
                metadata={
                    "target_user_id": str(req["user_id"]),
                    "reason": reason_clean,
                },
            )

            return {
                "ok": True,
                "contract_id": "API-135",
                "id": req_uuid,
                "status": status,
                "valid_until": (stamp + RECOVERY_APPROVAL_TTL).isoformat() if status == "APPROVED" else None,
            }


platform_admin_service = PlatformAdminService()
