"""FastAPI router for Internship Daily Logs and Separated Mentor vs Academic Reviews (`S2.6.1`, `FIX-11`, `INV-09`, `AC-040`)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ActorContext, require_actor_context
from app.services.internship_logs import InternshipLogScopeError, internship_log_service

class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

router = APIRouter(prefix="/api/v1/internship-logs", tags=["internship-logs"])


class CreateMentorAssignmentRequest(StrictDTO):
    placement_id: UUID
    organization_id: UUID
    mentor_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=128)


class CreateAcademicAssignmentLogScopeRequest(StrictDTO):
    placement_id: str
    institution_id: str
    supervisor_id: str
    supervision_id: str


class CreateDailyLogRequest(StrictDTO):
    placement_id: str
    log_date: str
    summary_text: str
    total_minutes: int = 240
    day_type: str = "WORKED"


class WorkplaceLogReviewRequest(StrictDTO):
    placement_id: str
    mentor_assignment_id: str
    decision: str
    comment: str


class AcademicLogReviewRequest(StrictDTO):
    placement_id: str
    academic_assignment_id: str
    decision: str
    academic_grade: int | None = None
    comment: str = ""


@router.post("/mentor-assignments", status_code=201)
def create_mentor_assignment_endpoint(payload: CreateMentorAssignmentRequest, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    return internship_log_service.create_mentor_assignment(
        placement_id=str(payload.placement_id),
        organization_id=str(payload.organization_id),
        mentor_id=str(payload.mentor_id),
        actor=actor,
        idempotency_key=payload.idempotency_key,
    )


@router.post("/academic-assignments", status_code=201)
def create_academic_assignment_log_scope_endpoint(
    payload: CreateAcademicAssignmentLogScopeRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    return internship_log_service.create_academic_assignment(
        placement_id=payload.placement_id,
        institution_id=payload.institution_id,
        supervisor_id=payload.supervisor_id,
        supervision_id=payload.supervision_id,
        actor=actor,
    )


@router.post("/daily-logs", status_code=201)
def create_daily_log_endpoint(payload: CreateDailyLogRequest, actor: ActorContext = Depends(require_actor_context)) -> Any:
    try:
        return internship_log_service.create_daily_log_with_revision(
            placement_id=payload.placement_id,
            author_id=actor.user_id,
            log_date=payload.log_date,
            summary_text=payload.summary_text,
            total_minutes=payload.total_minutes,
            day_type=payload.day_type,
        )
    except InternshipLogScopeError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": {"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
                "status": "REJECTED",
                "current_revision_id": exc.rejected_revision_id,
            },
        )


@router.post("/daily-logs/{daily_log_id}/workplace-reviews", status_code=201)
def submit_workplace_review_endpoint(
    daily_log_id: str,
    payload: WorkplaceLogReviewRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return internship_log_service.review(
            daily_log_id=daily_log_id,
            placement_id=payload.placement_id,
            assignment_id=payload.mentor_assignment_id,
            actor=actor,
            decision=payload.decision,
            comment=payload.comment,
        )
    except InternshipLogScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.post("/daily-logs/{daily_log_id}/academic-reviews", status_code=201)
def submit_academic_review_endpoint(
    daily_log_id: str,
    payload: AcademicLogReviewRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        if payload.academic_grade is not None:
            raise HTTPException(422,detail={'code':'OFFICIAL_GRADE_USE_SEPARATE_WORKFLOW'})
        return internship_log_service.review_academic(
            daily_log_id=daily_log_id,
            placement_id=payload.placement_id,
            assignment_id=payload.academic_assignment_id,
            actor=actor,
            decision=payload.decision,
            comment=payload.comment,
        )
    except InternshipLogScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc
