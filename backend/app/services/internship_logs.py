"""Internship Daily Logs, Revisions, and Separated Mentor vs Academic Teacher Reviews (`S2.6.1`, `INV-09`, `AC-040`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class InternshipLogScopeError(Exception):
    """Raised when a mentor or academic review violates `INV-09` composite FK scope (`AC-040`)."""

    def __init__(self, code: str, message: str, status_code: int = 409, sqlstate: str = "23503") -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.sqlstate = sqlstate


@dataclass
class InternshipLogService:
    """Manages `mentor_assignments`, `daily_logs`, `log_revisions`, `workplace_log_reviews`, and `academic_log_reviews` (`AC-040`)."""

    mentor_assignments: dict[str, dict[str, Any]] = field(default_factory=dict)
    academic_assignments: dict[str, dict[str, Any]] = field(default_factory=dict)
    daily_logs: dict[str, dict[str, Any]] = field(default_factory=dict)
    log_revisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    workplace_reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    academic_reviews: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create_mentor_assignment(
        self,
        *,
        placement_id: str,
        organization_id: str,
        mentor_id: str,
    ) -> dict[str, Any]:
        ma_id = str(uuid4())
        record = {
            "id": ma_id,
            "placement_id": placement_id,
            "organization_id": organization_id,
            "mentor_id": mentor_id,
            "status": "ACTIVE",
        }
        self.mentor_assignments[ma_id] = record
        return dict(record)

    def create_academic_assignment(
        self,
        *,
        placement_id: str,
        institution_id: str,
        supervisor_id: str,
    ) -> dict[str, Any]:
        aa_id = str(uuid4())
        record = {
            "id": aa_id,
            "placement_id": placement_id,
            "institution_id": institution_id,
            "supervisor_id": supervisor_id,
            "status": "ACTIVE",
        }
        self.academic_assignments[aa_id] = record
        return dict(record)

    def create_daily_log_with_revision(
        self,
        *,
        placement_id: str,
        author_id: str,
        log_date: str,
        summary_text: str,
        total_minutes: int = 240,
    ) -> dict[str, Any]:
        log_id = str(uuid4())
        rev_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        log_row = {
            "id": log_id,
            "placement_id": placement_id,
            "author_id": author_id,
            "log_date": log_date,
            "current_revision_id": rev_id,
            "status": "SUBMITTED",
            "created_at": now,
        }
        rev_row = {
            "id": rev_id,
            "daily_log_id": log_id,
            "revision": 1,
            "author_id": author_id,
            "summary_text": summary_text,
            "total_minutes": total_minutes,
            "status": "SUBMITTED",
            "created_at": now,
        }
        self.daily_logs[log_id] = log_row
        self.log_revisions[rev_id] = rev_row
        return dict(log_row)

    def submit_workplace_log_review(
        self,
        *,
        daily_log_id: str,
        placement_id: str,
        mentor_assignment_id: str,
        decision: str,
        comment: str,
    ) -> dict[str, Any]:
        """Enforce `fk_workplace_log_reviews_log_placement` and `fk_workplace_log_reviews_mentor_placement` (`INV-09`, `AC-040`)."""
        log_row = self.daily_logs.get(daily_log_id)
        if not log_row or log_row["placement_id"] != placement_id:
            raise InternshipLogScopeError(
                code="FK_WORKPLACE_LOG_REVIEWS_LOG_PLACEMENT_VIOLATION",
                message="workplace_log_reviews: daily_log_id va placement_id mos emas (INV-09, AC-040)",
                status_code=409,
                sqlstate="23503",
            )
        ma_row = self.mentor_assignments.get(mentor_assignment_id)
        if not ma_row or ma_row["placement_id"] != placement_id:
            raise InternshipLogScopeError(
                code="FK_WORKPLACE_LOG_REVIEWS_MENTOR_PLACEMENT_VIOLATION",
                message="workplace_log_reviews: mentor_assignment_id boshqa placementga tegishli (INV-09, AC-040)",
                status_code=409,
                sqlstate="23503",
            )
        review_id = str(uuid4())
        record = {
            "id": review_id,
            "daily_log_id": daily_log_id,
            "placement_id": placement_id,
            "mentor_assignment_id": mentor_assignment_id,
            "reviewer_kind": "WORKPLACE_MENTOR",
            "decision": decision,
            "comment": comment,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.workplace_reviews[review_id] = record
        return dict(record)

    def submit_academic_log_review(
        self,
        *,
        daily_log_id: str,
        placement_id: str,
        academic_assignment_id: str,
        decision: str,
        academic_grade: int | None = None,
        comment: str = "",
    ) -> dict[str, Any]:
        """Enforce `fk_academic_log_reviews_log_placement` and `fk_academic_log_reviews_academic_placement` (`INV-09`, `AC-040`)."""
        log_row = self.daily_logs.get(daily_log_id)
        if not log_row or log_row["placement_id"] != placement_id:
            raise InternshipLogScopeError(
                code="FK_ACADEMIC_LOG_REVIEWS_LOG_PLACEMENT_VIOLATION",
                message="academic_log_reviews: daily_log_id va placement_id mos emas (INV-09, AC-040)",
                status_code=409,
                sqlstate="23503",
            )
        aa_row = self.academic_assignments.get(academic_assignment_id)
        if not aa_row or aa_row["placement_id"] != placement_id:
            raise InternshipLogScopeError(
                code="FK_ACADEMIC_LOG_REVIEWS_ACADEMIC_PLACEMENT_VIOLATION",
                message="academic_log_reviews: academic_assignment_id boshqa placementga tegishli (INV-09, AC-040)",
                status_code=409,
                sqlstate="23503",
            )
        review_id = str(uuid4())
        record = {
            "id": review_id,
            "daily_log_id": daily_log_id,
            "placement_id": placement_id,
            "academic_assignment_id": academic_assignment_id,
            "reviewer_kind": "ACADEMIC_SUPERVISOR",
            "decision": decision,
            "academic_grade": academic_grade,
            "comment": comment,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.academic_reviews[review_id] = record
        return dict(record)


internship_log_service = InternshipLogService()
