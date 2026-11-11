"""Dual-Confirmed Job Engagements System (API-045, API-046 / CAP-012 / AC-014, AC-016 / DB-047, DB-048).

Implements canonical contracts:
- `API-045`: `GET /api/v1/me/engagements/{id}` (View engagement details, confirmations, dual-sided status).
- `API-046`: `POST /api/v1/engagements/{id}/confirmations` (Dual-party START/END/DISPUTE confirmation; transitions to ACTIVE only after both CANDIDATE and EMPLOYER confirm).

Invariants & Constraints:
- Main/master is strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6.
- Zero touches to production database `pg_live`. All tests run on isolated PostgreSQL.
- Server-side side resolution: candidate vs employer determined strictly from verified ActorContext; cannot be spoofed.
- AC-014: Status transitions to ACTIVE only when BOTH CANDIDATE and EMPLOYER confirm CONFIRM_START. Single dispute sets DISPUTED without automatic negative rating.
- AC-016: Non-internship job engagements do not require academic diaries; /logs route does not open diaries for job engagements.
- Strict IDOR isolation: uniform 404 returned on any unauthorized access attempt.
- Concurrency control: row-level locking with `with_for_update()` prevents race conditions during concurrent confirmations.
- Clean decoupling: Freelance logic is completely excluded from R1 scope.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select

from app.api.dependencies import ActorContext, owns_candidate, require_org
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.services.authority import account_authority
from app.services.placements import insert_row


class JobEngagementError(Exception):
    """Base exception for job engagement operations."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class EngagementNotFoundError(JobEngagementError):
    def __init__(self, message: str = "Ish munosabati topilmadi") -> None:
        super().__init__(code="ENGAGEMENT_NOT_FOUND", message=message, status_code=404)


class EngagementForbiddenError(JobEngagementError):
    def __init__(self, code: str = "FORBIDDEN", message: str = "Ruxsat etilmagan amal") -> None:
        super().__init__(code=code, message=message, status_code=403)


class EngagementConflictError(JobEngagementError):
    def __init__(self, code: str = "CONFLICT", message: str = "Holat mos kelmaydi") -> None:
        super().__init__(code=code, message=message, status_code=409)


class EngagementValidationError(JobEngagementError):
    def __init__(self, code: str = "VALIDATION_ERROR", message: str = "Yaroqsiz ma'lumot") -> None:
        super().__init__(code=code, message=message, status_code=422)


def _to_utc_iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat()
        return dt.astimezone(timezone.utc).isoformat()
    return str(dt)


def _validate_uuid(val: Any, field_name: str) -> str:
    try:
        return str(UUID(str(val)))
    except (ValueError, TypeError, AttributeError):
        raise EngagementValidationError(
            code=f"INVALID_{field_name.upper()}",
            message=f"Yaroqsiz {field_name} UUID formati",
        )


class JobEngagementService:
    """Service encapsulating dual-confirmed job engagements and confirmations."""

    def __init__(self) -> None:
        self.audit_store = AppendOnlyAuditStore()

    def _resolve_party(
        self,
        conn: Any,
        actor: ActorContext,
        candidate_id: str,
        organization_id: str,
        party: Optional[str] = None,
    ) -> str:
        """Strict server-side resolution of actor side (CANDIDATE vs EMPLOYER)."""
        is_candidate = False
        try:
            is_candidate = owns_candidate(actor.user_id, candidate_id)
        except Exception:
            is_candidate = False

        if not is_candidate:
            t_profiles = table("candidate_profiles")
            prof = conn.execute(
                select(t_profiles).where(
                    t_profiles.c.user_id == actor.user_id,
                    t_profiles.c.id == candidate_id,
                )
            ).mappings().first()
            if prof:
                is_candidate = True

        # Check organization membership for EMPLOYER side
        t_memberships = table("org_memberships")
        membership = conn.execute(
            select(t_memberships).where(
                t_memberships.c.organization_id == organization_id,
                t_memberships.c.user_id == actor.user_id,
                t_memberships.c.status == "ACTIVE",
                t_memberships.c.revoked_at.is_(None),
            )
        ).mappings().first()

        # If a specific party was asserted by caller, verify eligibility against that party
        if party in ("ORGANIZATION", "EMPLOYER"):
            if not membership:
                raise EngagementForbiddenError(
                    code="ENGAGEMENT_ACTOR_FORBIDDEN",
                    message="Faqat vakolatli ish beruvchi ushbu tomon nomidan tasdiqlay oladi",
                )
            return "EMPLOYER"

        if party == "CANDIDATE":
            if not is_candidate:
                raise EngagementForbiddenError(
                    code="ENGAGEMENT_ACTOR_FORBIDDEN",
                    message="Faqat nomzod o'z nomidan tasdiqlay oladi",
                )
            return "CANDIDATE"

        # Party not explicitly specified: resolve automatically from verified identity
        if is_candidate:
            return "CANDIDATE"

        if membership:
            return "EMPLOYER"

        # Actor is neither candidate nor org member -> uniform 404 to prevent IDOR probing
        raise EngagementNotFoundError(message="Ish munosabati topilmadi")

    # -------------------------------------------------------------------------
    # API-045: GET /api/v1/me/engagements/{id}
    # -------------------------------------------------------------------------
    def get_engagement(self, actor: ActorContext, engagement_id: str) -> dict[str, Any]:
        """View engagement details, confirmations, and dual-party status (API-045 / CAP-012)."""
        eng_uuid = _validate_uuid(engagement_id, "engagement_id")

        with transaction() as conn:
            account_authority(conn, actor)
            t_eng = table("job_engagements")
            t_apps = table("applications")
            t_opp = table("opportunities")
            t_conf = table("engagement_confirmations")

            engagement = conn.execute(
                select(t_eng).where(t_eng.c.id == eng_uuid)
            ).mappings().first()
            if not engagement:
                raise EngagementNotFoundError(message="Ish munosabati topilmadi")

            app = conn.execute(
                select(t_apps).where(t_apps.c.id == engagement["application_id"])
            ).mappings().first()
            if not app:
                raise EngagementNotFoundError(message="Tegishli ariza topilmadi")

            opp = conn.execute(
                select(t_opp).where(t_opp.c.id == app["opportunity_id"])
            ).mappings().first()
            if not opp:
                raise EngagementNotFoundError(message="Tegishli e'lon topilmadi")

            # Check party authorization (uniform 404 on foreign access)
            side = self._resolve_party(conn, actor, str(app["candidate_id"]), str(opp["organization_id"]))

            # Fetch confirmations
            confirmations = conn.execute(
                select(t_conf)
                .where(t_conf.c.engagement_id == eng_uuid)
                .order_by(t_conf.c.occurred_at.asc())
            ).mappings().all()

            confirmed_sides = {c["side"] for c in confirmations if c["action"] == "CONFIRM_START"}
            pending_sides = [s for s in ("CANDIDATE", "EMPLOYER") if s not in confirmed_sides]

            return {
                "contract_id": "API-045",
                "id": str(engagement["id"]),
                "application_id": str(engagement["application_id"]),
                "offer_id": str(engagement["offer_id"]),
                "status": engagement["status"],
                "start_date": engagement["start_date"].isoformat() if engagement["start_date"] else None,
                "end_date": engagement["end_date"].isoformat() if engagement.get("end_date") else None,
                "terms_snapshot": engagement["terms_snapshot"] or {},
                "confirmed_started_at": _to_utc_iso(engagement["confirmed_started_at"]),
                "my_side": side,
                "opportunity": {
                    "id": str(opp["id"]),
                    "organization_id": str(opp["organization_id"]),
                    "kind": opp["kind"],
                    "status": opp["status"],
                },
                "confirmations": [
                    {
                        "id": str(c["id"]),
                        "side": c["side"],
                        "action": c["action"],
                        "response": c["response"],
                        "occurred_at": _to_utc_iso(c["occurred_at"]),
                    }
                    for c in confirmations
                ],
                "pending_sides": pending_sides,
            }

    # -------------------------------------------------------------------------
    # API-046: POST /api/v1/engagements/{id}/confirmations
    # -------------------------------------------------------------------------
    def confirm_engagement(
        self,
        actor: ActorContext,
        engagement_id: str,
        action: str = "CONFIRM_START",
        party: Optional[str] = None,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        """Dual-party start/end/dispute confirmation (API-046 / CAP-012 / AC-014).

        INVARIANT AC-014:
        Status transitions to ACTIVE only after BOTH CANDIDATE and EMPLOYER confirm CONFIRM_START.
        Dispute sets DISPUTED without automatic negative rating.
        """
        eng_uuid = _validate_uuid(engagement_id, "engagement_id")
        action_clean = str(action).strip().upper()
        allowed_actions = ("CONFIRM_START", "CONFIRM_END", "DISPUTE_START", "DISPUTE_END")
        if action_clean not in allowed_actions:
            raise EngagementValidationError(
                code="INVALID_ACTION",
                message=f"Yaroqsiz amal. Ruxsat etilgan: {', '.join(allowed_actions)}",
            )

        with transaction() as conn:
            account_authority(conn, actor)
            t_eng = table("job_engagements")
            t_apps = table("applications")
            t_opp = table("opportunities")
            t_conf = table("engagement_confirmations")

            # 1. Lock job_engagements row
            engagement = conn.execute(
                select(t_eng).where(t_eng.c.id == eng_uuid).with_for_update()
            ).mappings().first()
            if not engagement:
                raise EngagementNotFoundError(message="Ish munosabati topilmadi")

            app = conn.execute(
                select(t_apps).where(t_apps.c.id == engagement["application_id"])
            ).mappings().first()
            if not app:
                raise EngagementNotFoundError(message="Tegishli ariza topilmadi")

            opp = conn.execute(
                select(t_opp).where(t_opp.c.id == app["opportunity_id"])
            ).mappings().first()
            if not opp:
                raise EngagementNotFoundError(message="Tegishli e'lon topilmadi")

            # 2. Strict IDOR and party authorization
            side = self._resolve_party(conn, actor, str(app["candidate_id"]), str(opp["organization_id"]), party)

            # 3. State eligibility
            curr_status = engagement["status"]
            if action_clean in ("CONFIRM_START", "DISPUTE_START"):
                if curr_status not in ("PENDING_START_CONFIRMATION", "ACTIVE", "DISPUTED"):
                    raise EngagementConflictError(
                        code="ENGAGEMENT_NOT_CONFIRMABLE",
                        message=f"Ish boshlanishini tasdiqlab bo'lmaydi (joriy holat: {curr_status})",
                    )
            elif action_clean in ("CONFIRM_END", "DISPUTE_END"):
                if curr_status not in ("ACTIVE", "DISPUTED"):
                    raise EngagementConflictError(
                        code="ENGAGEMENT_NOT_ACTIVE",
                        message=f"Faqat faol ish munosabatini yakunlash mumkin (joriy holat: {curr_status})",
                    )

            # 4. Idempotency check: UNIQUE(engagement_id, side, action)
            existing_conf = conn.execute(
                select(t_conf).where(
                    t_conf.c.engagement_id == eng_uuid,
                    t_conf.c.side == side,
                    t_conf.c.action == action_clean,
                )
            ).mappings().first()

            now_dt = now()
            if not existing_conf:
                insert_row(
                    conn,
                    "engagement_confirmations",
                    id=str(uuid4()),
                    engagement_id=eng_uuid,
                    user_id=actor.user_id,
                    side=side,
                    action=action_clean,
                    response=action_clean,
                    occurred_at=now_dt,
                )

            # 5. Evaluate overall status from all recorded confirmations
            all_confs = conn.execute(
                select(t_conf).where(t_conf.c.engagement_id == eng_uuid)
            ).mappings().all()

            has_start_dispute = any(c["action"] == "DISPUTE_START" for c in all_confs)
            has_end_dispute = any(c["action"] == "DISPUTE_END" for c in all_confs)
            start_confirmed_sides = {c["side"] for c in all_confs if c["action"] == "CONFIRM_START"}
            end_confirmed_sides = {c["side"] for c in all_confs if c["action"] == "CONFIRM_END"}

            both_confirmed_start = start_confirmed_sides == {"CANDIDATE", "EMPLOYER"}
            both_confirmed_end = end_confirmed_sides == {"CANDIDATE", "EMPLOYER"}

            new_status = curr_status
            confirmed_started_at = engagement["confirmed_started_at"]

            if has_start_dispute or has_end_dispute:
                new_status = "DISPUTED"
            elif both_confirmed_end:
                new_status = "COMPLETED"
            elif both_confirmed_start:
                new_status = "ACTIVE"
                if not confirmed_started_at:
                    confirmed_started_at = now_dt
            else:
                new_status = "PENDING_START_CONFIRMATION"

            # 6. Update job_engagements
            conn.execute(
                t_eng.update()
                .where(t_eng.c.id == eng_uuid)
                .values(
                    status=new_status,
                    confirmed_started_at=confirmed_started_at,
                    updated_at=now_dt,
                )
            )

            # 7. Audit log
            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action=f"ENGAGEMENT_{action_clean}",
                entity_type="job_engagement",
                entity_id=eng_uuid,
                metadata={
                    "side": side,
                    "action": action_clean,
                    "new_status": new_status,
                    "note": note,
                },
            )

            return {
                "contract_id": "API-046",
                "id": eng_uuid,
                "status": new_status,
                "side": side,
                "action": action_clean,
                "confirmed_started_at": _to_utc_iso(confirmed_started_at),
                "message": f"Munosabat holati: {new_status}",
            }


job_engagement_service = JobEngagementService()
