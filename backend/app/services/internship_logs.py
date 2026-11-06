"""Internship Daily Logs, Revisions, Validation (`0 < total_minutes <= 480`, `R-08`), and Separated Mentor vs Academic Teacher Reviews (`S2.6.1`, `FIX-11`, `INV-09`, `AC-040`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.placements import placement_service


class InternshipLogScopeError(Exception):
    """Raised when a daily log or mentor/academic review violates `INV-09`, `AC-040`, or `R-08`."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 409,
        sqlstate: str = "23503",
        rejected_revision_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.sqlstate = sqlstate
        self.rejected_revision_id = rejected_revision_id


@dataclass
class InternshipLogService:
    """Manages `mentor_assignments`, `daily_logs`, `log_revisions`, `workplace_log_reviews`, and `academic_log_reviews` (`AC-040`)."""

    mentor_assignments: dict[str, dict[str, Any]] = field(default_factory=dict)
    academic_assignments: dict[str, dict[str, Any]] = field(default_factory=dict)
    daily_logs: dict[str, dict[str, Any]] = field(default_factory=dict)
    log_revisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    workplace_reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    academic_reviews: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _placement_exists(self, placement_id: str) -> bool:
        if placement_id in placement_service.placements:
            return True
        if any(ma["placement_id"] == placement_id for ma in self.mentor_assignments.values()):
            return True
        if any(aa["placement_id"] == placement_id for aa in self.academic_assignments.values()):
            return True
        return False

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

    def _validate_minutes_and_placement(
        self,
        *,
        placement_id: str,
        author_id: str,
        summary_text: str,
        total_minutes: int,
        day_type: str = "WORKED",
    ) -> None:
        if day_type not in ("WORKED", "ABSENT"):
            rev_id = str(uuid4())
            self.log_revisions[rev_id] = {
                "id": rev_id,
                "author_id": author_id,
                "summary_text": summary_text,
                "total_minutes": total_minutes,
                "status": "REJECTED",
            }
            raise InternshipLogScopeError(
                code="INVALID_DAY_TYPE",
                message="day_type faqat WORKED yoki ABSENT bo'lishi mumkin",
                status_code=422,
                sqlstate="23514",
                rejected_revision_id=rev_id,
            )

        if (day_type == "WORKED" and not (1 <= total_minutes <= 480)) or (
            day_type == "ABSENT" and total_minutes != 0
        ):
            rev_id = str(uuid4())
            self.log_revisions[rev_id] = {
                "id": rev_id,
                "author_id": author_id,
                "summary_text": summary_text,
                "total_minutes": total_minutes,
                "status": "REJECTED",
            }
            raise InternshipLogScopeError(
                code="INVALID_DAILY_LOG_MINUTES",
                message="WORKED kunlik log uchun 0 < total_minutes <= 480 (ABSENT uchun 0) bo'lishi shart (AC-040 / R-08)",
                status_code=422,
                sqlstate="23514",
                rejected_revision_id=rev_id,
            )

        if not self._placement_exists(placement_id):
            rev_id = str(uuid4())
            self.log_revisions[rev_id] = {
                "id": rev_id,
                "author_id": author_id,
                "summary_text": summary_text,
                "total_minutes": total_minutes,
                "status": "REJECTED",
            }
            raise InternshipLogScopeError(
                code="PLACEMENT_NOT_FOUND",
                message=f"Placement '{placement_id}' topilmadi (INV-09 / R-08)",
                status_code=422,
                sqlstate="23503",
                rejected_revision_id=rev_id,
            )

    def create_daily_log_with_revision(
        self,
        *,
        placement_id: str,
        author_id: str,
        log_date: str,
        summary_text: str,
        total_minutes: int = 240,
        day_type: str = "WORKED",
    ) -> dict[str, Any]:
        self._validate_minutes_and_placement(
            placement_id=placement_id,
            author_id=author_id,
            summary_text=summary_text,
            total_minutes=total_minutes,
            day_type=day_type,
        )
        log_id = str(uuid4())
        rev_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        log_row = {
            "id": log_id,
            "placement_id": placement_id,
            "author_id": author_id,
            "log_date": log_date,
            "day_type": day_type,
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
            "day_type": day_type,
            "status": "SUBMITTED",
            "created_at": now,
        }
        self.daily_logs[log_id] = log_row
        self.log_revisions[rev_id] = rev_row
        return dict(log_row)

    def save_draft_daily_log_api_054(
        self,
        *,
        placement_id: str,
        author_id: str,
        log_date: str,
        summary_text: str,
        total_minutes: int = 240,
        day_type: str = "WORKED",
    ) -> dict[str, Any]:
        """API-054: Save a DRAFT daily log validating minutes (`0 < total_minutes <= 480`) and placement scope (`FIX-11`)."""
        self._validate_minutes_and_placement(
            placement_id=placement_id,
            author_id=author_id,
            summary_text=summary_text,
            total_minutes=total_minutes,
            day_type=day_type,
        )
        log_id = str(uuid4())
        rev_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        log_row = {
            "id": log_id,
            "placement_id": placement_id,
            "author_id": author_id,
            "log_date": log_date,
            "day_type": day_type,
            "current_revision_id": rev_id,
            "status": "DRAFT",
            "created_at": now,
        }
        rev_row = {
            "id": rev_id,
            "daily_log_id": log_id,
            "revision": 1,
            "author_id": author_id,
            "summary_text": summary_text,
            "total_minutes": total_minutes,
            "day_type": day_type,
            "status": "DRAFT",
            "created_at": now,
        }
        self.daily_logs[log_id] = log_row
        self.log_revisions[rev_id] = rev_row
        return {"contract_id": "API-054", **dict(log_row)}

    def submit_daily_log_api_056(
        self,
        *,
        placement_id: str,
        author_id: str,
        log_date: str,
    ) -> dict[str, Any]:
        """API-056: Submit a DRAFT daily log for mentor & academic review (`FIX-11`)."""
        for log_row in self.daily_logs.values():
            if log_row["placement_id"] == placement_id and log_row["log_date"] == log_date:
                log_row["status"] = "SUBMITTED"
                rev_id = log_row["current_revision_id"]
                if rev_id in self.log_revisions:
                    self.log_revisions[rev_id]["status"] = "SUBMITTED"
                return {"contract_id": "API-056", **dict(log_row)}

        raise InternshipLogScopeError(
            code="DAILY_LOG_NOT_FOUND",
            message=f"{placement_id} va {log_date} uchun kunlik log topilmadi",
            status_code=404,
            sqlstate="02000",
        )

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
