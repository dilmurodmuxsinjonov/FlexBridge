"""University coordinators vouch for their own students' account recovery.

A student without an authenticator or backup code verifies a contact by OTP and
files a recovery request (PENDING_REVIEW). A current, MFA-authenticated
COORDINATOR of an institution where that student holds a current VERIFIED
enrollment may approve or reject it after checking the student's identity
out-of-band. An approval is not a reset: it lets the same contact complete a new
recovery within 72 hours, once (identity.request_recovery consumes it).
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import and_, exists, or_, select

from app.core.audit import AppendOnlyAuditStore
from app.db.institution_scope import TASHKENT
from app.db.storage import now, table, transaction
from app.services.authority import institution_authority
from app.services.governance import GovernanceError
from app.services.placements import get_row

audit = AppendOnlyAuditStore()
REQUEST_WINDOW = timedelta(days=7)


def _student_of(institution_id, user_col):
    """EXISTS: the user holds a current VERIFIED enrollment at this institution."""
    e, c = table("enrollments"), table("candidate_profiles")
    today = now().astimezone(TASHKENT).date()
    return exists(
        select(e.c.id)
        .join(c, c.c.id == e.c.candidate_id)
        .where(
            c.c.user_id == user_col,
            e.c.institution_id == institution_id,
            e.c.status == "VERIFIED",
            e.c.start_date <= today,
            or_(e.c.end_date.is_(None), e.c.end_date >= today),
        )
    )


def _mask(value: str) -> str:
    if "@" in value:
        local, domain = value.split("@", 1)
        return (local[:2] + "***@" + domain) if len(local) > 2 else ("***@" + domain)
    return value[:6] + "***" + value[-4:] if len(value) >= 7 else "***"


class InstitutionRecoveryService:
    def queue(self, actor, institution_id, limit=50):
        with transaction() as conn:
            get_row(conn, "institutions", institution_id)
            institution_authority(conn, actor, institution_id, "COORDINATOR", require_mfa=True)
            r, u, uc = table("recovery_requests"), table("users"), table("user_contacts")
            rows = list(
                conn.execute(
                    select(r.c.id, r.c.created_at, r.c.user_id, u.c.display_name)
                    .join(u, u.c.id == r.c.user_id)
                    .where(
                        r.c.kind == "ACCOUNT_ACCESS",
                        r.c.status == "PENDING_REVIEW",
                        r.c.user_id.is_not(None),
                        r.c.user_id != actor.user_id,
                        r.c.created_at > now() - REQUEST_WINDOW,
                        _student_of(institution_id, r.c.user_id),
                    )
                    .order_by(r.c.created_at, r.c.id)
                    .limit(limit)
                ).mappings()
            )
            items = []
            for row in rows:
                contacts = conn.execute(
                    select(uc.c.channel, uc.c.normalized_value)
                    .where(uc.c.user_id == row["user_id"], uc.c.verified_at.is_not(None), uc.c.revoked_at.is_(None))
                    .order_by(uc.c.is_primary.desc(), uc.c.created_at)
                ).mappings()
                items.append(
                    {
                        "id": str(row["id"]),
                        "created_at": row["created_at"],
                        "student_name": row["display_name"],
                        "contacts": [{"channel": c["channel"], "masked": _mask(str(c["normalized_value"] or ""))} for c in contacts],
                    }
                )
            return {"items": items, "approval_valid_hours": 72}

    def decide(self, actor, institution_id, request_id, *, decision, reason):
        if decision not in ("APPROVE", "REJECT"):
            raise GovernanceError("INVALID_DECISION", status_code=422)
        if not isinstance(reason, str) or not 15 <= len(reason.strip()) <= 2000:
            raise GovernanceError("RECOVERY_DECISION_REASON_REQUIRED", status_code=422)
        with transaction() as conn:
            get_row(conn, "institutions", institution_id)
            r = table("recovery_requests")
            request = conn.execute(select(r).where(r.c.id == request_id).with_for_update()).mappings().first()
            institution_authority(conn, actor, institution_id, "COORDINATOR", require_mfa=True)
            eligible = request is not None and conn.execute(
                select(
                    and_(
                        r.c.kind == "ACCOUNT_ACCESS",
                        r.c.status == "PENDING_REVIEW",
                        r.c.user_id.is_not(None),
                        r.c.user_id != actor.user_id,
                        r.c.created_at > now() - REQUEST_WINDOW,
                        _student_of(institution_id, r.c.user_id),
                    )
                ).where(r.c.id == request_id)
            ).scalar()
            # Same answer for unknown, foreign, decided or expired requests.
            if not eligible:
                raise GovernanceError("RECOVERY_REQUEST_NOT_AVAILABLE", status_code=404)
            status = "APPROVED" if decision == "APPROVE" else "REJECTED"
            stamp = now()
            conn.execute(
                r.update()
                .where(r.c.id == request_id, r.c.status == "PENDING_REVIEW")
                .values(status=status, reviewer_id=actor.user_id, resolved_at=stamp, updated_at=stamp)
            )
            audit.append_audit_event(
                actor_id=actor.user_id,
                action="ACCOUNT_RECOVERY_" + status + "_BY_INSTITUTION",
                entity_type="recovery_request",
                entity_id=str(request_id),
                metadata={"institution_id": str(institution_id), "student_user_id": str(request["user_id"]), "reason": reason.strip()},
            )
            return {
                "id": str(request_id),
                "status": status,
                "valid_until": (stamp + timedelta(hours=72)).isoformat() if status == "APPROVED" else None,
            }


institution_recovery_service = InstitutionRecoveryService()
