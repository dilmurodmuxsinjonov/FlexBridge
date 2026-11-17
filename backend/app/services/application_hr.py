"""Application HR Service (CAP-008 / APPLICATION_HR).

Implements canonical contracts:
- `API-082`: `GET /api/v1/opportunities/{id}/applications` (Opportunity Applications List with Keyset Cursor Pagination)
- `API-083`: `POST /api/v1/applications/{id}/transition` (State Machine Status Transitions & Audit Events)
- `API-084`: `GET /api/v1/applications/{id}/hr` (Applicant Attempt Snapshot & Event History)
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, update

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.services.placements import insert_row


class ApplicationHRError(Exception):
    """Domain exception for Application HR operations."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "SUBMITTED": {"REVIEWING", "REJECTED"},
    "REVIEWING": {"SHORTLISTED", "INVITED_TO_INTERVIEW", "OFFER_PENDING", "REJECTED"},
    "SHORTLISTED": {"INVITED_TO_INTERVIEW", "OFFER_PENDING", "REJECTED"},
    "INVITED_TO_INTERVIEW": {"OFFER_PENDING", "REJECTED"},
    "OFFER_PENDING": {"REJECTED"},
}

TERMINAL_STATES: set[str] = {"REJECTED", "WITHDRAWN", "ACCEPTED"}


def _to_utc_iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt)


class ApplicationHRService:
    """Service handling HR review, state machine transitions, and applicant inspection."""

    def __init__(self) -> None:
        self.audit_store = AppendOnlyAuditStore()

    def _authorize_opportunity(
        self,
        conn: Any,
        opportunity_id: str,
        actor: ActorContext,
        for_update: bool = False,
    ) -> dict[str, Any]:
        """Verify opportunity exists and caller has active staff role in owning organization."""
        try:
            opp_uuid = str(UUID(str(opportunity_id)))
        except (ValueError, TypeError, AttributeError):
            raise ApplicationHRError("OPPORTUNITY_NOT_FOUND", "E'lon topilmadi", status_code=404)

        t_opp = table("opportunities")
        stmt = select(t_opp).where(t_opp.c.id == opp_uuid)
        if for_update:
            stmt = stmt.with_for_update()
        opp = conn.execute(stmt).mappings().first()
        if not opp:
            raise ApplicationHRError("OPPORTUNITY_NOT_FOUND", "E'lon topilmadi", status_code=404)

        # Verify caller has an active role in the owning organization
        t_mem = table("org_memberships")
        t_ogrants = table("org_role_grants")
        t_rcat = table("role_catalog")
        org_roles = conn.execute(
            select(t_rcat.c.code)
            .select_from(
                t_mem.join(t_ogrants, t_ogrants.c.membership_id == t_mem.c.id)
                .join(t_rcat, t_ogrants.c.role_id == t_rcat.c.id)
            )
            .where(
                t_mem.c.user_id == actor.user_id,
                t_mem.c.organization_id == opp["organization_id"],
                t_mem.c.status == "ACTIVE",
                t_mem.c.revoked_at.is_(None),
                t_ogrants.c.revoked_at.is_(None),
                t_rcat.c.scope_kind == "ORG",
                t_rcat.c.code.in_(("OWNER", "HR", "HOST_COORDINATOR")),
            )
        ).scalars().all()

        if not org_roles:
            # IDOR defense: return uniform 404
            raise ApplicationHRError("OPPORTUNITY_NOT_FOUND", "E'lon topilmadi", status_code=404)

        # HOST_COORDINATOR constraint: only INTERNSHIP opportunities (CAP-008)
        if "HOST_COORDINATOR" in org_roles and not ("OWNER" in org_roles or "HR" in org_roles):
            if opp["kind"] != "INTERNSHIP":
                raise ApplicationHRError(
                    "HOST_COORDINATOR_INTERNSHIP_ONLY",
                    "HOST_COORDINATOR faqat INTERNSHIP e'lonlarini boshqarishi mumkin",
                    status_code=403,
                )

        return dict(opp)

    def _authorize_application(
        self,
        conn: Any,
        application_id: str,
        actor: ActorContext,
        for_update: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Verify application exists and caller has active staff role in owning organization."""
        try:
            app_uuid = str(UUID(str(application_id)))
        except (ValueError, TypeError, AttributeError):
            raise ApplicationHRError("APPLICATION_NOT_FOUND", "Ariza topilmadi", status_code=404)

        t_apps = table("applications")
        stmt = select(t_apps).where(t_apps.c.id == app_uuid)
        if for_update:
            stmt = stmt.with_for_update()
        app = conn.execute(stmt).mappings().first()
        if not app:
            raise ApplicationHRError("APPLICATION_NOT_FOUND", "Ariza topilmadi", status_code=404)

        # Verify through the owning opportunity
        t_opp = table("opportunities")
        opp = conn.execute(select(t_opp).where(t_opp.c.id == app["opportunity_id"])).mappings().first()
        if not opp:
            raise ApplicationHRError("APPLICATION_NOT_FOUND", "Ariza topilmadi", status_code=404)

        t_mem = table("org_memberships")
        t_ogrants = table("org_role_grants")
        t_rcat = table("role_catalog")
        org_roles = conn.execute(
            select(t_rcat.c.code)
            .select_from(
                t_mem.join(t_ogrants, t_ogrants.c.membership_id == t_mem.c.id)
                .join(t_rcat, t_ogrants.c.role_id == t_rcat.c.id)
            )
            .where(
                t_mem.c.user_id == actor.user_id,
                t_mem.c.organization_id == opp["organization_id"],
                t_mem.c.status == "ACTIVE",
                t_mem.c.revoked_at.is_(None),
                t_ogrants.c.revoked_at.is_(None),
                t_rcat.c.scope_kind == "ORG",
                t_rcat.c.code.in_(("OWNER", "HR", "HOST_COORDINATOR")),
            )
        ).scalars().all()

        if not org_roles:
            raise ApplicationHRError("APPLICATION_NOT_FOUND", "Ariza topilmadi", status_code=404)

        if "HOST_COORDINATOR" in org_roles and not ("OWNER" in org_roles or "HR" in org_roles):
            if opp["kind"] != "INTERNSHIP":
                raise ApplicationHRError(
                    "HOST_COORDINATOR_INTERNSHIP_ONLY",
                    "HOST_COORDINATOR faqat INTERNSHIP arizalarini boshqarishi mumkin",
                    status_code=403,
                )

        return dict(app), dict(opp)

    # -------------------------------------------------------------------------
    # API-082: GET /api/v1/opportunities/{id}/applications
    # -------------------------------------------------------------------------
    def list_opportunity_applications(
        self,
        actor: ActorContext,
        opportunity_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> dict[str, Any]:
        """List applications submitted for this specific opportunity with keyset cursor pagination."""
        valid_limit = max(1, min(100, int(limit)))

        with transaction() as conn:
            opp = self._authorize_opportunity(conn, opportunity_id, actor, for_update=False)
            opp_uuid = opp["id"]

            t_apps = table("applications")
            t_attempts = table("application_attempts")

            stmt = (
                select(
                    t_apps.c.id,
                    t_apps.c.candidate_id,
                    t_apps.c.opportunity_id,
                    t_apps.c.status,
                    t_apps.c.current_attempt_id,
                    t_apps.c.version,
                    t_apps.c.created_at,
                    t_apps.c.updated_at,
                    t_attempts.c.attempt_no,
                    t_attempts.c.profile_snapshot,
                    t_attempts.c.schedule_result,
                    t_attempts.c.submitted_at,
                )
                .select_from(
                    t_apps.outerjoin(
                        t_attempts,
                        t_attempts.c.id == t_apps.c.current_attempt_id,
                    )
                )
                .where(t_apps.c.opportunity_id == opp_uuid)
            )

            if status and str(status).strip():
                clean_status = str(status).strip().upper()
                stmt = stmt.where(t_apps.c.status == clean_status)

            if cursor:
                try:
                    decoded = base64.b64decode(cursor.encode("utf-8")).decode("utf-8")
                    after_ts_str, after_id_str = decoded.split("|", 1)
                    after_ts = datetime.fromisoformat(after_ts_str)
                    after_id = str(UUID(after_id_str))
                except Exception as exc:
                    raise ApplicationHRError(
                        "INVALID_CURSOR",
                        "Noto'g'ri yoki buzilgan sahifalash kursori",
                        status_code=400,
                    ) from exc

                stmt = stmt.where(
                    or_(
                        t_apps.c.created_at < after_ts,
                        and_(t_apps.c.created_at == after_ts, t_apps.c.id < after_id),
                    )
                )

            stmt = stmt.order_by(t_apps.c.created_at.desc(), t_apps.c.id.desc()).limit(valid_limit + 1)
            rows = conn.execute(stmt).mappings().all()

            has_more = len(rows) > valid_limit
            page_rows = rows[:valid_limit]

            next_cursor = None
            if has_more and page_rows:
                last = page_rows[-1]
                created_iso = last["created_at"].isoformat() if hasattr(last["created_at"], "isoformat") else str(last["created_at"])
                payload = f"{created_iso}|{last['id']}"
                next_cursor = base64.b64encode(payload.encode("utf-8")).decode("utf-8")

            items = []
            for r in page_rows:
                snap = r["profile_snapshot"] or {}
                items.append({
                    "application_id": str(r["id"]),
                    "opportunity_id": str(r["opportunity_id"]),
                    "candidate_id": str(r["candidate_id"]),
                    "status": r["status"],
                    "attempt_no": r["attempt_no"] or 1,
                    "headline": snap.get("headline"),
                    "region": snap.get("region"),
                    "schedule_result": r["schedule_result"],
                    "created_at": _to_utc_iso(r["created_at"]),
                    "updated_at": _to_utc_iso(r["updated_at"]),
                    "submitted_at": _to_utc_iso(r["submitted_at"] or r["created_at"]),
                })

            return {
                "contract_id": "API-082",
                "opportunity_id": str(opp_uuid),
                "items": items,
                "limit": valid_limit,
                "has_more": has_more,
                "next_cursor": next_cursor,
            }

    # -------------------------------------------------------------------------
    # API-083: POST /api/v1/applications/{id}/transition
    # -------------------------------------------------------------------------
    def transition_application_status(
        self,
        actor: ActorContext,
        application_id: str,
        to_status: str,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """Transition application status according to allowed state machine transitions."""
        if not to_status or not str(to_status).strip():
            raise ApplicationHRError("INVALID_STATUS", "Yangi holat ko'rsatilishi shart", status_code=422)

        target_status = str(to_status).strip().upper()
        allowed_targets = {"REVIEWING", "SHORTLISTED", "INVITED_TO_INTERVIEW", "OFFER_PENDING", "REJECTED"}
        if target_status not in allowed_targets:
            raise ApplicationHRError(
                "INVALID_STATUS",
                f"Noma'lum holat: {target_status}. Ruxsat etilgan: {', '.join(sorted(allowed_targets))}",
                status_code=422,
            )

        with transaction() as conn:
            app, opp = self._authorize_application(conn, application_id, actor, for_update=True)
            app_uuid = app["id"]
            current_status = app["status"]

            # Idempotent no-op if status is already target
            if current_status == target_status:
                return {
                    "contract_id": "API-083",
                    "application_id": str(app_uuid),
                    "from_status": current_status,
                    "to_status": target_status,
                    "version": app["version"],
                    "transitioned_at": _to_utc_iso(app["updated_at"]),
                }

            # Check if current status is terminal
            if current_status in TERMINAL_STATES:
                raise ApplicationHRError(
                    "APPLICATION_TERMINAL_STATE",
                    f"Ariza yakuniy holatda ({current_status}). Uni o'zgartirib bo'lmaydi",
                    status_code=409,
                )

            # Check allowed transition
            allowed = ALLOWED_TRANSITIONS.get(current_status, set())
            if target_status not in allowed:
                raise ApplicationHRError(
                    "INVALID_APPLICATION_TRANSITION",
                    f"'{current_status}' holatidan '{target_status}' holatiga o'tishga ruxsat etilmagan",
                    status_code=409,
                )

            now_dt = now()
            new_version = app["version"] + 1

            # 1. Record event in application_events
            event_id = str(uuid4())
            insert_row(
                conn,
                "application_events",
                id=event_id,
                application_id=app_uuid,
                attempt_id=app.get("current_attempt_id"),
                actor_id=actor.user_id,
                from_status=current_status,
                to_status=target_status,
                reason=str(reason)[:1000] if reason else None,
                occurred_at=now_dt,
                created_at=now_dt,
                updated_at=now_dt,
            )

            # 2. Update applications table
            t_apps = table("applications")
            update_vals: dict[str, Any] = {
                "status": target_status,
                "version": new_version,
                "updated_at": now_dt,
            }

            # Capacity release invariant: if rejected and occupied capacity previously
            if target_status == "REJECTED" and app.get("occupied_at") and not app.get("released_at"):
                update_vals["released_at"] = now_dt
                t_opp = table("opportunities")
                conn.execute(
                    update(t_opp)
                    .where(t_opp.c.id == app["opportunity_id"])
                    .values(
                        occupied_count=func.greatest(0, t_opp.c.occupied_count - 1),
                        updated_at=now_dt,
                    )
                )

            conn.execute(
                update(t_apps)
                .where(t_apps.c.id == app_uuid)
                .values(**update_vals)
            )

            # 3. Append to immutable audit store
            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action="APPLICATION_HR_TRANSITION",
                entity_type="application",
                entity_id=str(app_uuid),
                metadata={
                    "from_status": current_status,
                    "to_status": target_status,
                    "reason": reason,
                    "version": new_version,
                },
            )

            return {
                "contract_id": "API-083",
                "application_id": str(app_uuid),
                "from_status": current_status,
                "to_status": target_status,
                "version": new_version,
                "transitioned_at": _to_utc_iso(now_dt),
            }

    # -------------------------------------------------------------------------
    # API-084: GET /api/v1/applications/{id}/hr
    # -------------------------------------------------------------------------
    def get_application_hr_detail(
        self,
        actor: ActorContext,
        application_id: str,
    ) -> dict[str, Any]:
        """Retrieve minimal applicant snapshot, schedule matching score, and event timeline."""
        with transaction() as conn:
            app, opp = self._authorize_application(conn, application_id, actor, for_update=False)
            app_uuid = app["id"]

            t_attempts = table("application_attempts")
            attempt_row = None
            if app.get("current_attempt_id"):
                attempt_row = conn.execute(
                    select(t_attempts).where(t_attempts.c.id == app["current_attempt_id"])
                ).mappings().first()

            if not attempt_row:
                attempt_row = conn.execute(
                    select(t_attempts)
                    .where(t_attempts.c.application_id == app_uuid)
                    .order_by(t_attempts.c.attempt_no.desc())
                    .limit(1)
                ).mappings().first()

            t_events = table("application_events")
            event_rows = conn.execute(
                select(t_events)
                .where(t_events.c.application_id == app_uuid)
                .order_by(t_events.c.occurred_at.asc(), t_events.c.created_at.asc())
            ).mappings().all()

            events = [
                {
                    "id": str(e["id"]),
                    "from_status": e["from_status"],
                    "to_status": e["to_status"],
                    "reason": e.get("reason"),
                    "actor_id": str(e["actor_id"]),
                    "occurred_at": _to_utc_iso(e["occurred_at"]),
                }
                for e in event_rows
            ]

            return {
                "contract_id": "API-084",
                "application_id": str(app_uuid),
                "opportunity_id": str(app["opportunity_id"]),
                "candidate_id": str(app["candidate_id"]),
                "status": app["status"],
                "version": app["version"],
                "created_at": _to_utc_iso(app["created_at"]),
                "updated_at": _to_utc_iso(app["updated_at"]),
                "attempt": {
                    "attempt_id": str(attempt_row["id"]) if attempt_row else None,
                    "attempt_no": attempt_row["attempt_no"] if attempt_row else 1,
                    "revision_id": str(attempt_row["revision_id"]) if attempt_row else None,
                    "enrollment_id": str(attempt_row["enrollment_id"]) if attempt_row and attempt_row.get("enrollment_id") else None,
                    "profile_snapshot": attempt_row["profile_snapshot"] if attempt_row else {},
                    "schedule_result": attempt_row["schedule_result"] if attempt_row else "UNKNOWN",
                    "matching_version": attempt_row["matching_version"] if attempt_row else "1.0",
                    "proposed_slots": attempt_row.get("proposed_slots") if attempt_row else None,
                    "submitted_at": _to_utc_iso(attempt_row["submitted_at"]) if attempt_row else _to_utc_iso(app["created_at"]),
                },
                "events": events,
            }


application_hr_service = ApplicationHRService()
