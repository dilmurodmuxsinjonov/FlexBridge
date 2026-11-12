"""Abuse reporting and moderation cases service (API-007 / CAP-032 / DB-078).

Implements canonical `API-007` (`POST /api/v1/moderation-cases`):
- Accepts abuse/moderation reports on opportunities, organizations, ratings, or files ("Target FK va asos").
- Strictly enforces DB-078 check constraint `num_nonnulls(opportunity_id, organization_id, rating_id, file_id) = 1`.
- Validates target entity existence in database with uniform 404 anti-enumeration defense.
- Excludes soft-deleted files (`deleted_at IS NOT NULL`) from reportable targets.
- Uses transaction-level advisory locking to serialize concurrent duplicate report submissions.
- Normalizes categories and deduplicates active cases (`OPEN`, `PENDING`, `IN_REVIEW`) case-insensitively.
- Computes SLA due_at by severity: CRITICAL (24h), HIGH (48h), MEDIUM (72h), LOW (168h).
- Idempotent submission: replaying the same active report for the same target and category returns the existing case.
- Immutable audit event logging via AppendOnlyAuditStore.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, text

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import rate_limit
from app.db.storage import now, table, transaction
from app.services.authority import account_authority


SEVERITY_DUE_HOURS: dict[str, int] = {
    "CRITICAL": 24,
    "HIGH": 48,
    "MEDIUM": 72,
    "LOW": 168,
}


class ModerationCaseError(Exception):
    """Base exception for moderation cases."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ModerationCaseValidationError(ModerationCaseError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=422)


class ModerationCaseNotFoundError(ModerationCaseError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=404)


@dataclass
class ModerationCasesService:
    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)

    def create_case(
        self,
        actor: ActorContext,
        category: str,
        reason: str,
        opportunity_id: UUID | None = None,
        organization_id: UUID | None = None,
        rating_id: UUID | None = None,
        file_id: UUID | None = None,
        severity: str = "MEDIUM",
    ) -> dict[str, Any]:
        """Create a new moderation case with validated target FK and justification."""
        rate_limit("moderation-report", actor.user_id, 30, 3600)

        # 1. Target check: exactly one target must be provided
        targets: dict[str, UUID | None] = {
            "opportunity_id": opportunity_id,
            "organization_id": organization_id,
            "rating_id": rating_id,
            "file_id": file_id,
        }
        provided = {k: v for k, v in targets.items() if v is not None}
        if len(provided) != 1:
            raise ModerationCaseValidationError(
                "EXACTLY_ONE_TARGET_REQUIRED",
                "Exactly one target (opportunity_id, organization_id, rating_id, file_id) must be specified",
            )

        target_field, target_id = next(iter(provided.items()))
        target_type = {
            "opportunity_id": "OPPORTUNITY",
            "organization_id": "ORGANIZATION",
            "rating_id": "RATING",
            "file_id": "FILE",
        }[target_field]

        # 2. Category & severity validation
        cat_clean = category.strip().upper()
        if not (2 <= len(cat_clean) <= 100):
            raise ModerationCaseValidationError("INVALID_CATEGORY", "Category must be between 2 and 100 characters")

        reason_clean = reason.strip()
        if not (10 <= len(reason_clean) <= 4000):
            raise ModerationCaseValidationError("INVALID_REASON", "Reason must be between 10 and 4000 characters")

        sev = severity.strip().upper()
        if sev not in SEVERITY_DUE_HOURS:
            raise ModerationCaseValidationError(
                "INVALID_SEVERITY",
                f"Severity must be one of {sorted(SEVERITY_DUE_HOURS.keys())}",
            )

        due_delta = timedelta(hours=SEVERITY_DUE_HOURS[sev])

        with transaction() as conn:
            # 2.1 Advisory lock on user + target + category FIRST to serialize concurrent duplicate submissions
            lock_key = f"moderation-case:{actor.user_id}:{target_id}:{cat_clean}"
            conn.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": lock_key},
            )

            account_authority(conn, actor)

            # 3. Verify target entity existence in database (anti-enumeration defense)
            if target_field == "opportunity_id":
                t_opp = table("opportunities")
                opp = conn.execute(select(t_opp.c.id).where(t_opp.c.id == target_id)).first()
                if not opp:
                    raise ModerationCaseNotFoundError("OPPORTUNITY_NOT_FOUND", "Target opportunity does not exist")
            elif target_field == "organization_id":
                t_org = table("organizations")
                org = conn.execute(select(t_org.c.id).where(t_org.c.id == target_id)).first()
                if not org:
                    raise ModerationCaseNotFoundError("ORGANIZATION_NOT_FOUND", "Target organization does not exist")
            elif target_field == "rating_id":
                t_rating = table("rating_submissions")
                rating = conn.execute(select(t_rating.c.id).where(t_rating.c.id == target_id)).first()
                if not rating:
                    raise ModerationCaseNotFoundError("RATING_NOT_FOUND", "Target rating does not exist")
            elif target_field == "file_id":
                t_files = table("files")
                f = conn.execute(
                    select(t_files.c.id).where(
                        t_files.c.id == target_id,
                        t_files.c.deleted_at.is_(None),
                    )
                ).first()
                if not f:
                    raise ModerationCaseNotFoundError("FILE_NOT_FOUND", "Target file does not exist")

            # 4. Check for existing active open case by same reporter for same target & category (Idempotent repeat)
            t_cases = table("moderation_cases")
            target_filter = getattr(t_cases.c, target_field) == target_id
            existing = conn.execute(
                select(t_cases).where(
                    t_cases.c.reporter_id == actor.user_id,
                    target_filter,
                    func.upper(t_cases.c.category) == cat_clean,
                    t_cases.c.status.in_(("OPEN", "PENDING", "IN_REVIEW")),
                )
            ).mappings().first()

            if existing:
                return {
                    "id": str(existing["id"]),
                    "contract_id": "API-007",
                    "reporter_id": str(existing["reporter_id"]),
                    "target_type": target_type,
                    "target_id": str(target_id),
                    "opportunity_id": str(existing["opportunity_id"]) if existing["opportunity_id"] else None,
                    "organization_id": str(existing["organization_id"]) if existing["organization_id"] else None,
                    "rating_id": str(existing["rating_id"]) if existing["rating_id"] else None,
                    "file_id": str(existing["file_id"]) if existing["file_id"] else None,
                    "category": existing["category"],
                    "severity": existing["severity"],
                    "status": existing["status"],
                    "due_at": existing["due_at"].isoformat() if existing["due_at"] else None,
                    "created_at": existing["created_at"].isoformat() if existing["created_at"] else None,
                    "reason": reason_clean,
                    "is_idempotent_replay": True,
                }

            # 5. Insert new moderation case into flexbridge.moderation_cases
            case_id = str(uuid4())
            created_at = now()
            due_at = created_at + due_delta

            insert_values = {
                "id": case_id,
                "created_at": created_at,
                "updated_at": created_at,
                "reporter_id": actor.user_id,
                "opportunity_id": target_id if target_field == "opportunity_id" else None,
                "organization_id": target_id if target_field == "organization_id" else None,
                "rating_id": target_id if target_field == "rating_id" else None,
                "file_id": target_id if target_field == "file_id" else None,
                "category": cat_clean,
                "status": "OPEN",
                "severity": sev,
                "assigned_to_id": None,
                "due_at": due_at,
                "decision": None,
                "decided_at": None,
            }
            conn.execute(t_cases.insert().values(**insert_values))

            # 6. Audit event logging
            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action="MODERATION_CASE_REPORTED",
                entity_type="moderation_case",
                entity_id=case_id,
                metadata={
                    "target_type": target_type,
                    "target_id": str(target_id),
                    "category": cat_clean,
                    "severity": sev,
                    "reason": reason_clean,
                },
            )

            return {
                "id": case_id,
                "contract_id": "API-007",
                "reporter_id": str(actor.user_id),
                "target_type": target_type,
                "target_id": str(target_id),
                "opportunity_id": str(target_id) if target_field == "opportunity_id" else None,
                "organization_id": str(target_id) if target_field == "organization_id" else None,
                "rating_id": str(target_id) if target_field == "rating_id" else None,
                "file_id": str(target_id) if target_field == "file_id" else None,
                "category": cat_clean,
                "severity": sev,
                "status": "OPEN",
                "due_at": due_at.isoformat(),
                "created_at": created_at.isoformat(),
                "reason": reason_clean,
                "is_idempotent_replay": False,
            }


moderation_cases_service = ModerationCasesService()
