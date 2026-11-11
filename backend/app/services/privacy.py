"""Privacy requests and data subject rights service (API-062 / CAP-032 / DB-082 / DB-084 / AC-031).

Implements canonical contract `API-062` (`POST /api/v1/me/privacy-requests`) and `GET /api/v1/me/privacy-requests`:
- Data subject rights management: export (`EXPORT`), erasure (`DELETE`), and rectification (`RECTIFY`).
- Statutory 30-day fulfillment SLA (`due_at = created_at + 30 days`).
- Legal hold protection (`DB-084` / `AC-031`): blocks data erasure when active legal holds exist.
- Anti-duplication / in-flight concurrency protection (HTTP 409 `PRIVACY_REQUEST_ALREADY_PENDING`).
- Immutable append-only auditing (`AppendOnlyAuditStore`).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, func, select

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.services.authority import account_authority
from app.services.placements import PlacementScopeError, insert_row


VALID_KINDS = frozenset({"EXPORT", "DELETE", "RECTIFY"})
VALID_STATUSES = frozenset({"PENDING", "IN_PROGRESS", "COMPLETED", "REJECTED"})


class PrivacyError(Exception):
    """Base exception for privacy requests service."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class PrivacyValidationError(PrivacyError):
    """Raised when request payload or parameters fail validation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=422)


class PrivacyConflictError(PrivacyError):
    """Raised when a concurrent in-flight privacy request of the same kind already exists."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=409)


class PrivacyLegalHoldError(PrivacyError):
    """Raised when an active legal hold prohibits requested privacy action (e.g. deletion)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=422)


class PrivacyService:
    """Enterprise privacy management service executing within PostgreSQL transactions."""

    def create_privacy_request_api_062(
        self,
        *,
        actor: ActorContext,
        kind: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a formal privacy request (API-062)."""
        kind_clean = (kind or "").strip().upper()
        if kind_clean not in VALID_KINDS:
            raise PrivacyValidationError(
                "INVALID_PRIVACY_REQUEST_KIND",
                f"Privacy request kind '{kind}' is invalid. Must be one of: {', '.join(sorted(VALID_KINDS))}.",
            )

        if reason is not None and len(reason.strip()) == 0:
            reason = None

        with transaction() as conn:
            # 1. Authority validation
            account_authority(conn, actor)
            user_id = str(actor.user_id)

            t_reqs = table("privacy_requests")
            t_holds = table("legal_holds")

            now_utc = now()

            # 2. Legal hold check (DB-084 / AC-031) for DELETE requests
            if kind_clean == "DELETE":
                active_hold = conn.execute(
                    select(t_holds).where(
                        t_holds.c.user_id == user_id,
                        t_holds.c.released_at.is_(None),
                        t_holds.c.expires_at > now_utc,
                    )
                ).mappings().first()

                if active_hold:
                    raise PrivacyLegalHoldError(
                        "LEGAL_HOLD_ACTIVE",
                        f"Active legal hold '{active_hold['reason']}' prevents deletion until resolution.",
                    )

            # 3. Anti-duplication check: prevent duplicate PENDING or IN_PROGRESS requests of same kind
            existing_pending = conn.execute(
                select(t_reqs).where(
                    t_reqs.c.user_id == user_id,
                    t_reqs.c.kind == kind_clean,
                    t_reqs.c.status.in_(["PENDING", "IN_PROGRESS"]),
                )
            ).mappings().first()

            if existing_pending:
                raise PrivacyConflictError(
                    "PRIVACY_REQUEST_ALREADY_PENDING",
                    f"A privacy request of kind '{kind_clean}' is already {existing_pending['status'].lower()}.",
                )

            # 4. Compute statutory due date (30 days SLA)
            due_utc = now_utc + timedelta(days=30)
            req_id = str(uuid4())

            # 5. Insert new privacy request row
            insert_row(
                conn,
                "privacy_requests",
                id=req_id,
                created_at=now_utc,
                updated_at=now_utc,
                user_id=user_id,
                kind=kind_clean,
                status="PENDING",
                verified_at=now_utc,
                due_at=due_utc,
                result_file_id=None,
                resolved_at=None,
                reason=reason,
            )

            # 6. Immutable audit log entry
            AppendOnlyAuditStore().append_audit_event(
                actor_id=user_id,
                action="PRIVACY_REQUEST_CREATED",
                entity_type="privacy_request",
                entity_id=req_id,
                metadata={
                    "kind": kind_clean,
                    "reason": reason,
                    "due_at": due_utc.isoformat(),
                },
            )

            return {
                "id": req_id,
                "user_id": str(user_id),
                "kind": kind_clean,
                "status": "PENDING",
                "verified_at": now_utc.isoformat(),
                "due_at": due_utc.isoformat(),
                "result_file_id": None,
                "resolved_at": None,
                "reason": reason,
                "created_at": now_utc.isoformat(),
                "updated_at": now_utc.isoformat(),
            }

    def get_my_privacy_requests(
        self,
        *,
        actor: ActorContext,
        kind: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Query privacy requests for current authenticated actor."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        with transaction() as conn:
            account_authority(conn, actor)
            user_id = str(actor.user_id)

            t_reqs = table("privacy_requests")
            conditions = [t_reqs.c.user_id == user_id]

            if kind:
                k_clean = kind.strip().upper()
                if k_clean in VALID_KINDS:
                    conditions.append(t_reqs.c.kind == k_clean)

            if status:
                s_clean = status.strip().upper()
                if s_clean in VALID_STATUSES:
                    conditions.append(t_reqs.c.status == s_clean)

            where_clause = and_(*conditions)

            # Count total
            total_count = conn.execute(
                select(func.count()).select_from(t_reqs).where(where_clause)
            ).scalar() or 0

            # Fetch page items
            query = (
                select(t_reqs)
                .where(where_clause)
                .order_by(t_reqs.c.created_at.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )

            rows = conn.execute(query).mappings().all()

            items = [
                {
                    "id": str(r["id"]),
                    "user_id": str(r["user_id"]),
                    "kind": r["kind"],
                    "status": r["status"],
                    "verified_at": r["verified_at"].isoformat() if r["verified_at"] else None,
                    "due_at": r["due_at"].isoformat() if r["due_at"] else None,
                    "result_file_id": str(r["result_file_id"]) if r["result_file_id"] else None,
                    "resolved_at": r["resolved_at"].isoformat() if r["resolved_at"] else None,
                    "reason": r["reason"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
                }
                for r in rows
            ]

            return {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "items": items,
            }


privacy_service = PrivacyService()
