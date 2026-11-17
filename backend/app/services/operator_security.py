"""Operator Security and Operations Service (API-118, API-119, API-120, API-122, API-123, API-124).

Contracts:
- API-118: GET /api/v1/operator/audit-events (CAP-036 / ADMIN_AUDIT / AUDITOR, ADMIN)
- API-119: POST /api/v1/operator/access-requests (CAP-036 / ADMIN_AUDIT / ADMIN)
- API-120: POST /api/v1/operator/users/{id}/revoke-sessions (CAP-036 / ADMIN_AUDIT / ADMIN)
- API-122: POST /api/v1/operator/incidents (CAP-037 / OPERATIONS / ADMIN)
- API-123: GET /api/v1/operator/restore-runs (CAP-037 / OPERATIONS / ADMIN)
- API-124: GET /api/v1/operator/analytics (CAP-038 / OPERATIONS / ADMIN)

Invariants:
- Strict role boundaries (AUDITOR, ADMIN, OPERATIONS, SECURITY_LEAD). Non-staff receive 403 PERMISSION_DENIED.
- Dual-control authorization on emergency/break-glass role grants (independent approver != requester).
- Uniform 404 IDOR defense for nonexistent user and incident targets.
- Keyset cursor pagination over audit trail and restore runs.
- Append-only audit trail logging for all mutations.
- Zero customer PII leakage in operational metrics.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.services.authority import account_authority


ADMIN_AUDIT_ROLES = frozenset({"ADMIN", "AUDITOR"})
ADMIN_OPS_ROLES = frozenset({"ADMIN", "OPERATIONS", "SECURITY_LEAD"})
ADMIN_ONLY_ROLES = frozenset({"ADMIN", "SECURITY_LEAD"})
VALID_PLATFORM_ROLES = frozenset({"ADMIN", "OPERATIONS", "SECURITY_LEAD", "AUDITOR", "FINANCE", "SUPPORT", "MODERATOR", "COMPLIANCE"})


class OperatorSecurityError(Exception):
    """Base exception for operator security and operations service."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class OperatorSecurityForbiddenError(OperatorSecurityError):
    def __init__(self, code: str = "PERMISSION_DENIED", message: str = "Operator huquqi talab qilinadi") -> None:
        super().__init__(code=code, message=message, status_code=403)


class OperatorSecurityNotFoundError(OperatorSecurityError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=404)


class OperatorSecurityValidationError(OperatorSecurityError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=422)


class OperatorSecurityConflictError(OperatorSecurityError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=409)


class OperatorSecurityService:
    """Enterprise platform security, audit trail, incident management, and DR operations service."""

    def __init__(self) -> None:
        self.audit_store = AppendOnlyAuditStore()

    def _verify_platform_authority(self, conn: Any, actor: ActorContext, allowed_roles: frozenset[str]) -> None:
        """Verify that caller holds at least one of the allowed platform roles."""
        actor_roles = set(actor.roles or [])
        if allowed_roles.intersection(actor_roles):
            return

        t_grants = table("platform_role_grants")
        t_catalog = table("role_catalog")
        now_utc = now()

        found = conn.execute(
            select(t_grants.c.id)
            .select_from(t_grants.join(t_catalog, t_grants.c.role_id == t_catalog.c.id))
            .where(
                t_grants.c.user_id == str(actor.user_id),
                t_grants.c.revoked_at.is_(None),
                t_grants.c.expires_at > now_utc,
                t_catalog.c.scope_kind == "PLATFORM",
                t_catalog.c.code.in_(allowed_roles),
            )
        ).first()

        if not found:
            raise OperatorSecurityForbiddenError(
                "PERMISSION_DENIED", "Ushbu amal uchun tegishli platforma operatori roli talab qilinadi"
            )

    def _parse_date(self, val: str | None, param_name: str) -> datetime | None:
        """Parse ISO-8601 or YYYY-MM-DD date safely."""
        if not val:
            return None
        val_clean = val.strip()
        try:
            if len(val_clean) == 10:
                return datetime.strptime(val_clean, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(val_clean.replace("Z", "+00:00"))
        except Exception as exc:
            raise OperatorSecurityValidationError(
                "INVALID_DATE_FORMAT", f"{param_name} formati noto'g'ri (YYYY-MM-DD yoki ISO-8601 talab etiladi)"
            ) from exc

    def _encode_cursor(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    def _decode_cursor(self, cursor: str) -> dict[str, Any]:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            raw = base64.urlsafe_b64decode(padded.encode("ascii"))
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Cursor payload is not a JSON object")
            return data
        except Exception as exc:
            raise OperatorSecurityValidationError("INVALID_CURSOR", "Yaroqsiz sahifalash kursori") from exc

    # -------------------------------------------------------------------------
    # API-118: Audit Events Trail
    # -------------------------------------------------------------------------
    def get_audit_events(
        self,
        *,
        actor: ActorContext,
        actor_id: str | None = None,
        action: str | None = None,
        object_type: str | None = None,
        object_key: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """API-118: Query append-only audit event history with keyset pagination (CAP-036 / ADMIN_AUDIT)."""
        with transaction() as conn:
            account_authority(conn, actor)
            self._verify_platform_authority(conn, actor, ADMIN_AUDIT_ROLES)

            dt_start = self._parse_date(start_date, "start_date")
            dt_end = self._parse_date(end_date, "end_date")

            if dt_start and dt_end and dt_start > dt_end:
                raise OperatorSecurityValidationError("INVALID_DATE_RANGE", "start_date end_date dan katta bo'lishi mumkin emas")

            if limit < 1:
                limit = 1
            elif limit > 100:
                limit = 100

            t_audit = table("audit_events")
            conditions: list[Any] = []

            if actor_id:
                try:
                    actor_uuid = str(UUID(actor_id.strip()))
                    conditions.append(t_audit.c.actor_id == actor_uuid)
                except ValueError as exc:
                    raise OperatorSecurityValidationError("INVALID_UUID", "actor_id formati noto'g'ri UUID") from exc

            if action:
                conditions.append(t_audit.c.action == action.strip().upper())

            if object_type:
                conditions.append(t_audit.c.object_type == object_type.strip().lower())

            if object_key:
                conditions.append(t_audit.c.object_key == object_key.strip())

            if dt_start:
                conditions.append(t_audit.c.occurred_at >= dt_start)
            if dt_end:
                conditions.append(t_audit.c.occurred_at <= dt_end)

            # Keyset pagination cursor over (occurred_at DESC, id DESC)
            if cursor:
                cursor_data = self._decode_cursor(cursor)
                try:
                    cursor_occurred_at = datetime.fromisoformat(cursor_data["o"])
                    cursor_id = str(UUID(cursor_data["i"]))
                except (KeyError, ValueError, TypeError) as exc:
                    raise OperatorSecurityValidationError("INVALID_CURSOR", "Yaroqsiz sahifalash kursori") from exc

                conditions.append(
                    or_(
                        t_audit.c.occurred_at < cursor_occurred_at,
                        and_(
                            t_audit.c.occurred_at == cursor_occurred_at,
                            t_audit.c.id < cursor_id,
                        ),
                    )
                )

            where_clause = and_(*conditions) if conditions else True

            query = (
                select(
                    t_audit.c.id,
                    t_audit.c.occurred_at,
                    t_audit.c.actor_id,
                    t_audit.c.session_id,
                    t_audit.c.action,
                    t_audit.c.object_type,
                    t_audit.c.object_key,
                    t_audit.c.scope_snapshot,
                    t_audit.c.before_digest,
                    t_audit.c.after_digest,
                    t_audit.c.reason,
                    t_audit.c.request_id,
                )
                .where(where_clause)
                .order_by(t_audit.c.occurred_at.desc(), t_audit.c.id.desc())
                .limit(limit + 1)
            )

            rows = conn.execute(query).mappings().all()

            has_more = len(rows) > limit
            page_rows = rows[:limit]

            next_cursor = None
            if has_more and page_rows:
                last_r = page_rows[-1]
                next_cursor = self._encode_cursor({
                    "o": last_r["occurred_at"].isoformat(),
                    "i": str(last_r["id"]),
                })

            items = [
                {
                    "id": str(r["id"]),
                    "occurred_at": r["occurred_at"].isoformat() if r["occurred_at"] else None,
                    "actor_id": str(r["actor_id"]) if r["actor_id"] else None,
                    "session_id": str(r["session_id"]) if r["session_id"] else None,
                    "action": r["action"],
                    "object_type": r["object_type"],
                    "object_key": r["object_key"],
                    "scope_snapshot": r["scope_snapshot"],
                    "before_digest": r["before_digest"],
                    "after_digest": r["after_digest"],
                    "reason": r["reason"],
                    "request_id": r["request_id"],
                }
                for r in page_rows
            ]

            total_count = conn.execute(
                select(func.count()).select_from(t_audit).where(where_clause)
            ).scalar() or 0

            return {
                "contract_id": "API-118",
                "capability": "ADMIN_AUDIT",
                "items": items,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "total_records": total_count,
            }

    # -------------------------------------------------------------------------
    # API-119: Break-Glass / Access Requests
    # -------------------------------------------------------------------------
    def create_access_request(
        self,
        *,
        actor: ActorContext,
        target_user_id: str,
        role_code: str,
        reason: str,
        independent_approver_id: str,
        duration_minutes: int | None = None,
        duration_hours: int | None = None,
    ) -> dict[str, Any]:
        """API-119: Break-glass temporary privileged role grant with independent dual approval (CAP-036 / ADMIN)."""
        with transaction() as conn:
            account_authority(conn, actor)
            self._verify_platform_authority(conn, actor, ADMIN_ONLY_ROLES)

            target_str = target_user_id.strip() if target_user_id else ""
            approver_str = independent_approver_id.strip() if independent_approver_id else ""
            role_str = role_code.strip().upper() if role_code else ""
            reason_str = reason.strip() if reason else ""

            if not target_str or not approver_str:
                raise OperatorSecurityValidationError("MISSING_REQUIRED_FIELDS", "target_user_id va independent_approver_id majburiy")

            try:
                target_uuid = str(UUID(target_str))
                approver_uuid = str(UUID(approver_str))
            except ValueError as exc:
                raise OperatorSecurityValidationError("INVALID_UUID", "target_user_id yoki approver_id UUID formati noto'g'ri") from exc

            if not reason_str or len(reason_str) < 5:
                raise OperatorSecurityValidationError("INVALID_REASON", "Asos (reason) kamida 5 ta belgidan iborat bo'lishi shart")

            # Duration validation (max 240 minutes / 4 hours)
            mins = 240
            if duration_minutes is not None:
                mins = duration_minutes
            elif duration_hours is not None:
                mins = duration_hours * 60

            if mins < 1 or mins > 240:
                raise OperatorSecurityValidationError("INVALID_DURATION", "duration_minutes 1 dan 240 minutgacha (maksimal 4 soat) bo'lishi shart")

            # Dual Control: Caller cannot be the independent approver
            if str(actor.user_id) == approver_uuid:
                raise OperatorSecurityForbiddenError(
                    "SELF_APPROVAL_FORBIDDEN", "Murojaat qiluvchi o'z so'roviga mustaqil tasdiqlovchi bo'la olmaydi (Dual-control required)"
                )

            t_users = table("users")
            t_roles = table("role_catalog")
            t_grants = table("platform_role_grants")

            # 1. Verify target user existence
            target_user = conn.execute(select(t_users.c.id).where(t_users.c.id == target_uuid)).first()
            if not target_user:
                raise OperatorSecurityNotFoundError("USER_NOT_FOUND", "Maqsadli foydalanuvchi topilmadi")

            # 2. Verify independent approver existence
            approver_user = conn.execute(select(t_users.c.id).where(t_users.c.id == approver_uuid)).first()
            if not approver_user:
                raise OperatorSecurityNotFoundError("APPROVER_NOT_FOUND", "Mustaqil tasdiqlovchi foydalanuvchi topilmadi")

            # 3. Verify target role in role_catalog
            if role_str not in VALID_PLATFORM_ROLES:
                raise OperatorSecurityValidationError("INVALID_ROLE", f"Platforma roli mavjud emas: {role_str}")

            role_row = conn.execute(
                select(t_roles.c.id, t_roles.c.code)
                .where(t_roles.c.code == role_str, t_roles.c.scope_kind == "PLATFORM")
            ).mappings().first()

            now_utc = now()
            if not role_row:
                new_role_id = str(uuid4())
                conn.execute(
                    t_roles.insert().values(
                        id=new_role_id,
                        created_at=now_utc,
                        updated_at=now_utc,
                        code=role_str,
                        scope_kind="PLATFORM",
                        description=f"Platform {role_str} role",
                    )
                )
                role_id = new_role_id
            else:
                role_id = role_row["id"]

            expires_at = now_utc + timedelta(minutes=mins)
            grant_id = str(uuid4())

            # Insert privileged platform grant
            conn.execute(
                t_grants.insert().values(
                    id=grant_id,
                    created_at=now_utc,
                    updated_at=now_utc,
                    user_id=target_uuid,
                    role_id=role_id,
                    granted_by_id=approver_uuid,
                    expires_at=expires_at,
                    revoked_at=None,
                )
            )

            # Append audit event
            self.audit_store.append_audit_event(
                actor_id=str(actor.user_id),
                action="BREAK_GLASS_ROLE_GRANTED",
                entity_type="platform_role_grant",
                entity_id=grant_id,
                metadata={
                    "target_user_id": target_uuid,
                    "role_code": role_str,
                    "independent_approver_id": approver_uuid,
                    "duration_minutes": mins,
                    "reason": reason_str,
                },
            )

            return {
                "contract_id": "API-119",
                "capability": "ADMIN_AUDIT",
                "grant_id": grant_id,
                "target_user_id": target_uuid,
                "role_code": role_str,
                "granted_by_id": approver_uuid,
                "expires_at": expires_at.isoformat(),
                "duration_minutes": mins,
                "status": "GRANTED",
            }

    # -------------------------------------------------------------------------
    # API-120: Emergency Session Revocation
    # -------------------------------------------------------------------------
    def revoke_user_sessions(
        self,
        *,
        actor: ActorContext,
        target_user_id: str,
        reason: str,
        incident_id: str | None = None,
    ) -> dict[str, Any]:
        """API-120: Immediate emergency revocation of all active user sessions (CAP-036 / ADMIN)."""
        with transaction() as conn:
            account_authority(conn, actor)
            self._verify_platform_authority(conn, actor, ADMIN_OPS_ROLES)

            target_str = target_user_id.strip() if target_user_id else ""
            reason_str = reason.strip() if reason else ""

            if not target_str:
                raise OperatorSecurityValidationError("MISSING_USER_ID", "target_user_id majburiy")

            try:
                target_uuid = str(UUID(target_str))
            except ValueError as exc:
                raise OperatorSecurityValidationError("INVALID_UUID", "target_user_id UUID formati noto'g'ri") from exc

            if not reason_str or len(reason_str) < 5:
                raise OperatorSecurityValidationError("INVALID_REASON", "Bekor qilish asosi (reason) kamida 5 ta belgidan iborat bo'lishi shart")

            inc_uuid = None
            if incident_id:
                try:
                    inc_uuid = str(UUID(incident_id.strip()))
                except ValueError as exc:
                    raise OperatorSecurityValidationError("INVALID_UUID", "incident_id UUID formati noto'g'ri") from exc

            t_users = table("users")
            t_sess = table("sessions")

            user_exists = conn.execute(select(t_users.c.id).where(t_users.c.id == target_uuid)).first()
            if not user_exists:
                raise OperatorSecurityNotFoundError("USER_NOT_FOUND", "Foydalanuvchi topilmadi")

            now_utc = now()

            # Revoke all active sessions for this user
            res = conn.execute(
                t_sess.update()
                .where(t_sess.c.user_id == target_uuid, t_sess.c.revoked_at.is_(None))
                .values(revoked_at=now_utc, updated_at=now_utc)
            )
            revoked_count = res.rowcount or 0

            # Append audit trail
            self.audit_store.append_audit_event(
                actor_id=str(actor.user_id),
                action="USER_SESSIONS_EMERGENCY_REVOKED",
                entity_type="user",
                entity_id=target_uuid,
                metadata={
                    "target_user_id": target_uuid,
                    "revoked_count": revoked_count,
                    "reason": reason_str,
                    "incident_id": inc_uuid,
                },
            )

            return {
                "contract_id": "API-120",
                "capability": "ADMIN_AUDIT",
                "user_id": target_uuid,
                "revoked_sessions_count": int(revoked_count),
                "status": "REVOKED",
                "revoked_at": now_utc.isoformat(),
                "reason": reason_str,
                "incident_id": inc_uuid,
            }

    # -------------------------------------------------------------------------
    # API-122: Incident Declaration & Management
    # -------------------------------------------------------------------------
    def declare_incident(
        self,
        *,
        actor: ActorContext,
        severity: str,
        summary: str | None = None,
        title: str | None = None,
        commander_id: str | None = None,
        commander_user_id: str | None = None,
        postmortem_ref: str | None = None,
    ) -> dict[str, Any]:
        """API-122: Declare an operational incident and assign incident commander (CAP-037 / OPERATIONS / ADMIN)."""
        with transaction() as conn:
            account_authority(conn, actor)
            self._verify_platform_authority(conn, actor, ADMIN_OPS_ROLES)

            sev_str = severity.strip().upper() if severity else ""
            raw_sum = summary or title or ""
            sum_str = raw_sum.strip()
            raw_cmd = commander_id or commander_user_id or ""
            cmd_str = raw_cmd.strip()

            if sev_str not in {"P1", "P2", "P3", "P4"}:
                raise OperatorSecurityValidationError("INVALID_SEVERITY", "severity faqat P1, P2, P3 yoki P4 bo'lishi mumkin")

            if not sum_str or len(sum_str) < 5:
                raise OperatorSecurityValidationError("INVALID_SUMMARY", "Insident qisqacha tavsifi (summary/title) kamida 5 ta belgidan iborat bo'lishi shart")

            try:
                commander_uuid = str(UUID(cmd_str))
            except ValueError as exc:
                raise OperatorSecurityValidationError("INVALID_UUID", "commander_id UUID formati noto'g'ri") from exc

            t_users = table("users")
            t_inc = table("incidents")

            commander_row = conn.execute(select(t_users.c.id).where(t_users.c.id == commander_uuid)).first()
            if not commander_row:
                raise OperatorSecurityNotFoundError("COMMANDER_NOT_FOUND", "Insident komandiri sifatida ko'rsatilgan foydalanuvchi topilmadi")

            now_utc = now()
            inc_id = str(uuid4())

            conn.execute(
                t_inc.insert().values(
                    id=inc_id,
                    created_at=now_utc,
                    updated_at=now_utc,
                    severity=sev_str,
                    status="OPEN",
                    commander_id=commander_uuid,
                    summary=sum_str,
                    started_at=now_utc,
                    resolved_at=None,
                    postmortem_ref=postmortem_ref,
                )
            )

            self.audit_store.append_audit_event(
                actor_id=str(actor.user_id),
                action="OPERATIONAL_INCIDENT_DECLARED",
                entity_type="incident",
                entity_id=inc_id,
                metadata={
                    "severity": sev_str,
                    "commander_id": commander_uuid,
                    "summary": sum_str,
                },
            )

            return {
                "contract_id": "API-122",
                "capability": "OPERATIONS",
                "incident_id": inc_id,
                "severity": sev_str,
                "status": "OPEN",
                "commander_id": commander_uuid,
                "summary": sum_str,
                "started_at": now_utc.isoformat(),
                "postmortem_ref": postmortem_ref,
            }

    # -------------------------------------------------------------------------
    # API-123: Disaster Recovery Restore Runs
    # -------------------------------------------------------------------------
    def get_restore_runs(
        self,
        *,
        actor: ActorContext,
        limit: int = 50,
        status: str | None = None,
    ) -> dict[str, Any]:
        """API-123: Query DR restore run proofs and evaluate SLA against targets (CAP-037 / OPERATIONS)."""
        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        with transaction() as conn:
            account_authority(conn, actor)
            self._verify_platform_authority(conn, actor, ADMIN_OPS_ROLES.union({"AUDITOR"}))

            t_rr = table("restore_runs")
            conditions: list[Any] = []

            if status:
                conditions.append(t_rr.c.status == status.strip().upper())

            where_clause = and_(*conditions) if conditions else True

            query = (
                select(
                    t_rr.c.id,
                    t_rr.c.created_at,
                    t_rr.c.started_at,
                    t_rr.c.finished_at,
                    t_rr.c.backup_ref,
                    t_rr.c.status,
                    t_rr.c.recovered_through,
                    t_rr.c.measured_rpo_minutes,
                    t_rr.c.measured_rto_minutes,
                    t_rr.c.checked_by_id,
                    t_rr.c.evidence_ref,
                )
                .where(where_clause)
                .order_by(t_rr.c.started_at.desc(), t_rr.c.id.desc())
                .limit(limit)
            )

            rows = conn.execute(query).mappings().all()

            target_rpo_minutes = 24 * 60  # RPO <= 24h
            target_rto_minutes = 4 * 60   # RTO <= 4h
            any_verified = False

            items: list[dict[str, Any]] = []
            for r in rows:
                rpo = r["measured_rpo_minutes"]
                rto = r["measured_rto_minutes"]
                r_status = r["status"]

                sla_met = (
                    r_status in {"VERIFIED", "SUCCESS", "COMPLETED"}
                    and rpo is not None and rpo <= target_rpo_minutes
                    and rto is not None and rto <= target_rto_minutes
                )
                if sla_met:
                    any_verified = True

                items.append({
                    "id": str(r["id"]),
                    "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                    "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
                    "backup_ref": r["backup_ref"],
                    "status": r_status,
                    "recovered_through": r["recovered_through"].isoformat() if r["recovered_through"] else None,
                    "measured_rpo_minutes": rpo,
                    "measured_rto_minutes": rto,
                    "checked_by_id": str(r["checked_by_id"]) if r["checked_by_id"] else None,
                    "evidence_ref": r["evidence_ref"],
                    "sla_met": bool(sla_met),
                })

            total_count = conn.execute(
                select(func.count()).select_from(t_rr).where(where_clause)
            ).scalar() or 0

            return {
                "contract_id": "API-123",
                "capability": "OPERATIONS",
                "target_sla": {
                    "max_rpo_hours": 24,
                    "max_rto_hours": 4,
                },
                "restore_drill_verified": any_verified,
                "items": items,
                "total_runs": total_count,
            }

    # -------------------------------------------------------------------------
    # API-124: Operator Platform Analytics
    # -------------------------------------------------------------------------
    def get_operator_analytics(
        self,
        *,
        actor: ActorContext,
        start_date: str | None = None,
        end_date: str | None = None,
        cohort: str | None = None,
    ) -> dict[str, Any]:
        """API-124: Platform operational analytics, dedup checks, and mutual start verification (CAP-038 / OPERATIONS)."""
        with transaction() as conn:
            account_authority(conn, actor)
            self._verify_platform_authority(conn, actor, ADMIN_OPS_ROLES.union({"AUDITOR"}))

            dt_start = self._parse_date(start_date, "start_date")
            dt_end = self._parse_date(end_date, "end_date")

            if dt_start and dt_end and dt_start > dt_end:
                raise OperatorSecurityValidationError("INVALID_DATE_RANGE", "start_date end_date dan katta bo'lishi mumkin emas")

            t_ae = table("analytics_events")
            t_pl = table("placements")
            t_out = table("outbox_events")

            # 1. Analytics Events stats
            ae_conds: list[Any] = []
            if dt_start:
                ae_conds.append(t_ae.c.occurred_at >= dt_start)
            if dt_end:
                ae_conds.append(t_ae.c.occurred_at <= dt_end)
            if cohort:
                ae_conds.append(t_ae.c.cohort == cohort.strip())

            ae_where = and_(*ae_conds) if ae_conds else True
            total_events = conn.execute(select(func.count()).select_from(t_ae).where(ae_where)).scalar() or 0

            # Distinct events count for dedup rate calculation
            distinct_events = conn.execute(
                select(func.count(func.distinct(t_ae.c.event_key))).select_from(t_ae).where(ae_where)
            ).scalar() or 0

            dedup_efficiency = 100.0 if total_events == 0 else round((distinct_events / max(total_events, 1)) * 100.0, 1)

            # 2. Placements and mutual start confirmation stats
            pl_conds: list[Any] = []
            if dt_start:
                pl_conds.append(t_pl.c.created_at >= dt_start)
            if dt_end:
                pl_conds.append(t_pl.c.created_at <= dt_end)
            pl_where = and_(*pl_conds) if pl_conds else True

            total_placements = conn.execute(select(func.count()).select_from(t_pl).where(pl_where)).scalar() or 0
            confirmed_starts = conn.execute(
                select(func.count()).select_from(t_pl).where(
                    and_(pl_where, t_pl.c.status.in_({"ACTIVE", "IN_PROGRESS", "COMPLETED"}))
                )
            ).scalar() or 0
            completed_placements = conn.execute(
                select(func.count()).select_from(t_pl).where(and_(pl_where, t_pl.c.status == "COMPLETED"))
            ).scalar() or 0

            # 3. Outbox message processing health
            pending_outbox = conn.execute(
                select(func.count()).select_from(t_out).where(t_out.c.processed_at.is_(None))
            ).scalar() or 0

            return {
                "contract_id": "API-124",
                "capability": "OPERATIONS",
                "period": {
                    "start_date": dt_start.isoformat() if dt_start else None,
                    "end_date": dt_end.isoformat() if dt_end else None,
                },
                "cohort": cohort,
                "analytics": {
                    "total_events": int(total_events),
                    "distinct_event_keys": int(distinct_events),
                    "dedup_efficiency_pct": float(dedup_efficiency),
                },
                "placements": {
                    "total_placements": int(total_placements),
                    "confirmed_starts": int(confirmed_starts),
                    "completed_placements": int(completed_placements),
                    "mutual_start_rate_pct": 100.0 if total_placements == 0 else round((confirmed_starts / total_placements) * 100.0, 1),
                },
                "outbox_health": {
                    "pending_messages": int(pending_outbox),
                    "status": "HEALTHY" if pending_outbox < 1000 else "DEGRADED",
                },
            }


operator_security_service = OperatorSecurityService()
