"""Saved opportunities service (API-004 / API-037 / API-038 / CAP-006 / DB-040).

Implements canonical contracts:
- `API-004`: `POST /api/v1/saved-opportunities` (Toggle idempotent, candidate's own profile only).
- `API-037`: `GET /api/v1/me/saved-opportunities` (List candidate's saved opportunities; closed/archived status preserved).
- `API-038`: `DELETE /api/v1/me/saved-opportunities/{id}` (Candidate's own row only; idempotent repeat 204).
- Enforces strict candidate profile ownership (`candidate_id_for`, `owns_candidate`).
- Preserves opportunity status and flags (`is_closed`).
- Append-only audit trails (`AppendOnlyAuditStore`).
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select

from app.api.dependencies import ActorContext, candidate_id_for, owns_candidate
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.services.authority import account_authority
from app.services.placements import insert_row


class SavedOpportunityError(Exception):
    """Base exception for saved opportunity operations."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class SavedOpportunityNotFoundError(SavedOpportunityError):
    def __init__(self, message: str = "E'lon topilmadi") -> None:
        super().__init__(code="OPPORTUNITY_NOT_FOUND", message=message, status_code=404)


class SavedOpportunityForbiddenError(SavedOpportunityError):
    def __init__(self, code: str = "FORBIDDEN", message: str = "Ruxsat etilmagan amal") -> None:
        super().__init__(code=code, message=message, status_code=403)


class SavedOpportunityValidationError(SavedOpportunityError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=422)


class SavedOpportunitiesService:
    """Service encapsulating Candidate Saved Opportunities business logic."""

    def __init__(self) -> None:
        self.audit_store = AppendOnlyAuditStore()

    def _validate_uuid(self, val: Any, field_name: str) -> str:
        try:
            return str(UUID(str(val)))
        except (ValueError, TypeError, AttributeError):
            raise SavedOpportunityValidationError(
                code=f"INVALID_{field_name.upper()}",
                message=f"Yaroqsiz {field_name} UUID formati",
            )

    def save_opportunity(
        self,
        actor: ActorContext,
        opportunity_id: str,
        candidate_id: Optional[str] = None,
        toggle: bool = False,
    ) -> tuple[dict[str, Any], int]:
        """Save an opportunity for the candidate, with idempotency or optional toggle."""
        opp_uuid = self._validate_uuid(opportunity_id, "opportunity_id")

        with transaction() as conn:
            account_authority(conn, actor)
            user_id = str(actor.user_id)
            actor_candidate_id = candidate_id_for(actor)

            # Enforce candidate isolation: faqat o'z nomzodi
            if candidate_id:
                target_cand_uuid = self._validate_uuid(candidate_id, "candidate_id")
                if target_cand_uuid != actor_candidate_id:
                    if not owns_candidate(user_id, target_cand_uuid):
                        raise SavedOpportunityForbiddenError(
                            code="CANDIDATE_ACCESS_DENIED",
                            message="Boshqa nomzod nomidan e'lon saqlash taqiqlangan",
                        )
                    resolved_candidate_id = target_cand_uuid
                else:
                    resolved_candidate_id = actor_candidate_id
            else:
                resolved_candidate_id = actor_candidate_id

            t_opp = table("opportunities")
            opp_row = conn.execute(
                select(t_opp.c.id, t_opp.c.status, t_opp.c.organization_id).where(
                    t_opp.c.id == opp_uuid
                )
            ).mappings().first()
            if not opp_row:
                raise SavedOpportunityNotFoundError("E'lon topilmadi")

            t_saved = table("saved_opportunities")
            existing = conn.execute(
                select(t_saved.c.id, t_saved.c.created_at, t_saved.c.updated_at).where(
                    t_saved.c.candidate_id == resolved_candidate_id,
                    t_saved.c.opportunity_id == opp_uuid,
                )
            ).mappings().first()

            if toggle and existing:
                # Toggle on existing item: remove it
                conn.execute(t_saved.delete().where(t_saved.c.id == existing["id"]))
                self.audit_store.append_audit_event(
                    actor_id=user_id,
                    action="OPPORTUNITY_UNSAVED",
                    entity_type="saved_opportunity",
                    entity_id=existing["id"],
                    metadata={
                        "opportunity_id": opp_uuid,
                        "candidate_id": resolved_candidate_id,
                        "toggle": True,
                    },
                )
                return {
                    "saved": False,
                    "opportunity_id": opp_uuid,
                    "candidate_id": resolved_candidate_id,
                    "id": None,
                }, 200

            if existing:
                # Idempotent save: already saved
                return {
                    "saved": True,
                    "opportunity_id": opp_uuid,
                    "candidate_id": resolved_candidate_id,
                    "id": existing["id"],
                    "created_at": (
                        existing["created_at"].isoformat()
                        if existing.get("created_at")
                        else None
                    ),
                }, 200

            # New save
            new_id = str(uuid4())
            insert_row(
                conn,
                "saved_opportunities",
                id=new_id,
                created_at=now(),
                updated_at=now(),
                candidate_id=resolved_candidate_id,
                opportunity_id=opp_uuid,
            )
            self.audit_store.append_audit_event(
                actor_id=user_id,
                action="OPPORTUNITY_SAVED",
                entity_type="saved_opportunity",
                entity_id=new_id,
                metadata={
                    "opportunity_id": opp_uuid,
                    "candidate_id": resolved_candidate_id,
                    "toggle": toggle,
                },
            )

            return {
                "saved": True,
                "opportunity_id": opp_uuid,
                "candidate_id": resolved_candidate_id,
                "id": new_id,
            }, 201

    def get_my_saved_opportunities(
        self,
        actor: ActorContext,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List candidate's saved opportunities with preserved opportunity status."""
        safe_page = max(1, page)
        safe_page_size = min(100, max(1, page_size))

        with transaction() as conn:
            account_authority(conn, actor)
            c_id = candidate_id_for(actor)

            t_saved = table("saved_opportunities")
            t_opp = table("opportunities")
            t_rev = table("opportunity_revisions")

            total = conn.execute(
                select(func.count(t_saved.c.id)).where(t_saved.c.candidate_id == c_id)
            ).scalar_one()

            stmt = (
                select(
                    t_saved.c.id.label("saved_id"),
                    t_saved.c.created_at.label("saved_at"),
                    t_saved.c.opportunity_id,
                    t_opp.c.organization_id,
                    t_opp.c.kind,
                    t_opp.c.status,
                    t_opp.c.closed_at,
                    t_opp.c.published_at,
                    t_opp.c.current_revision_id,
                    t_rev.c.title,
                    t_rev.c.work_mode,
                    t_rev.c.contract_type,
                    t_rev.c.is_paid,
                )
                .select_from(
                    t_saved.join(t_opp, t_opp.c.id == t_saved.c.opportunity_id).outerjoin(
                        t_rev, t_rev.c.id == t_opp.c.current_revision_id
                    )
                )
                .where(t_saved.c.candidate_id == c_id)
                .order_by(t_saved.c.created_at.desc())
                .offset((safe_page - 1) * safe_page_size)
                .limit(safe_page_size)
            )

            rows = conn.execute(stmt).mappings().all()

            items = []
            for row in rows:
                status = row["status"]
                closed_at = row["closed_at"]
                is_closed = status in ("CLOSED", "ARCHIVED") or closed_at is not None
                items.append(
                    {
                        "id": row["saved_id"],
                        "candidate_id": c_id,
                        "opportunity_id": row["opportunity_id"],
                        "created_at": (
                            row["saved_at"].isoformat() if row["saved_at"] else None
                        ),
                        "opportunity": {
                            "id": row["opportunity_id"],
                            "organization_id": row["organization_id"],
                            "kind": row["kind"],
                            "status": status,
                            "is_closed": is_closed,
                            "closed_at": (
                                closed_at.isoformat() if closed_at else None
                            ),
                            "published_at": (
                                row["published_at"].isoformat()
                                if row["published_at"]
                                else None
                            ),
                            "current_revision_id": row["current_revision_id"],
                            "title": row["title"],
                            "work_mode": row["work_mode"],
                            "contract_type": row["contract_type"],
                            "is_paid": row["is_paid"],
                        },
                    }
                )

            return {
                "items": items,
                "total": total,
                "page": safe_page,
                "page_size": safe_page_size,
            }

    def delete_saved_opportunity(
        self,
        actor: ActorContext,
        identifier: str,
    ) -> None:
        """Unsave an opportunity. Idempotent repeat 204. Cross-candidate deletion rejected."""
        ident_uuid = self._validate_uuid(identifier, "id")

        with transaction() as conn:
            account_authority(conn, actor)
            user_id = str(actor.user_id)
            c_id = candidate_id_for(actor)

            t_saved = table("saved_opportunities")
            # Search by saved_opportunity.id OR opportunity_id
            existing_rows = conn.execute(
                select(t_saved.c.id, t_saved.c.candidate_id, t_saved.c.opportunity_id).where(
                    or_(t_saved.c.id == ident_uuid, t_saved.c.opportunity_id == ident_uuid)
                )
            ).mappings().all()

            if not existing_rows:
                # Idempotent repeat 204
                return

            my_row = next((r for r in existing_rows if r["candidate_id"] == c_id), None)
            if my_row:
                conn.execute(t_saved.delete().where(t_saved.c.id == my_row["id"]))
                self.audit_store.append_audit_event(
                    actor_id=user_id,
                    action="OPPORTUNITY_UNSAVED",
                    entity_type="saved_opportunity",
                    entity_id=my_row["id"],
                    metadata={
                        "opportunity_id": my_row["opportunity_id"],
                        "candidate_id": c_id,
                    },
                )
                return

            # Exists but belongs to another candidate
            raise SavedOpportunityForbiddenError(
                code="SAVED_OPPORTUNITY_ACCESS_DENIED",
                message="Boshqa nomzodning saqlangan e'lonini o'chirish taqiqlangan",
            )


saved_opportunities_service = SavedOpportunitiesService()
