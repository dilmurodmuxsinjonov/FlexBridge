"""FastAPI router for Opportunities, Shifts, and `API-003` Schedule Matching (`S2.4.1`, `AC-039`)."""

from __future__ import annotations

from typing import Any
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.api.dependencies import ActorContext, require_actor_context, candidate_id_for
from app.services.opportunities import OpportunityConstraintError, opportunity_service

router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


class CreateOpportunityRevisionRequest(BaseModel):
    organization_id: str
    title: str
    opportunity_kind: str = "PART_TIME_JOB"
    contract_type: str
    compensation_type: str = "HOURLY"
    hourly_pay: int | None = None
    stipend_amount: int | None = None
    fee_terms_note: str | None = None
    published: bool = False


class CreateOpportunityShiftRequest(BaseModel):
    group_code: str = "GROUP_A"
    weekday: int
    start_minute: int
    end_minute: int
    is_required: bool = True


@router.post("/revisions", status_code=201)
def create_opportunity_revision_endpoint(payload: CreateOpportunityRevisionRequest, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    try:
        return opportunity_service.create_opportunity_revision(
            organization_id=payload.organization_id,
            title=payload.title,
            opportunity_kind=payload.opportunity_kind,
            contract_type=payload.contract_type,
            compensation_type=payload.compensation_type,
            hourly_pay=payload.hourly_pay,
            stipend_amount=payload.stipend_amount,
            fee_terms_note=payload.fee_terms_note,
            published=payload.published,
            actor_user_id=actor.user_id,
        )
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.post("/revisions/{revision_id}/shifts", status_code=201)
def create_opportunity_shift_endpoint(
    revision_id: str,
    payload: CreateOpportunityShiftRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return opportunity_service.add_opportunity_shift(
            revision_id=revision_id,
            group_code=payload.group_code,
            weekday=payload.weekday,
            start_minute=payload.start_minute,
            end_minute=payload.end_minute,
            is_required=payload.is_required,
            actor_user_id=actor.user_id,
        )
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.get("/feed")
def api_003_opportunity_feed(
    actor: ActorContext = Depends(require_actor_context),
    candidate_id: UUID = Query(...),
    schedule_match_mode: str = Query(default="ALL_SHIFTS_IN_GROUP"),
    check_date: date | None = Query(default=None),
    commute_buffer_minutes: int = Query(default=30, ge=0, le=180),
    limit: int = Query(default=100, ge=1, le=100),
    after_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    """API-003: Deterministic schedule matching feed (`ALL_SHIFTS_IN_GROUP` vs `ANY_SHIFT_IN_GROUP`, `AC-039`)."""
    if str(candidate_id) != candidate_id_for(actor):
        raise HTTPException(403,detail={"code":"CANDIDATE_SCOPE_FORBIDDEN"})
    try:
        page = opportunity_service.match_feed_page(
            candidate_id=str(candidate_id),
            schedule_match_mode=schedule_match_mode,
            check_date=check_date,
            commute_buffer_minutes=commute_buffer_minutes,
            limit=limit,
            after_id=str(after_id) if after_id else None,
        )
        return {
            "contract_id": "API-003",
            "candidate_id": candidate_id,
            "schedule_match_mode": schedule_match_mode,
            "items": page['items'],
            "next_cursor": page['next_cursor'],
        }
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.get("", status_code=200)
@router.get("/", status_code=200, include_in_schema=False)
def search_public_opportunities_endpoint(
    region: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    is_paid: bool | None = Query(default=None),
    min_hourly_pay: int | None = Query(default=None),
    schedule_policy: str | None = Query(default=None),
    query: str | None = Query(default=None),
    skill_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    after: str | None = Query(default=None),
) -> dict[str, Any]:
    """API-001: Public opportunity search and discovery catalog (`CAP-001`, `PUBLIC_SEARCH`)."""
    try:
        return opportunity_service.search_public_opportunities(
            region=region,
            kind=kind,
            is_paid=is_paid,
            min_hourly_pay=min_hourly_pay,
            schedule_policy=schedule_policy,
            query=query,
            skill_id=str(skill_id) if skill_id else None,
            limit=limit,
            after=after,
        )
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


class UpdateOpportunityDraftRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    region: str | None = None
    work_mode: str | None = None
    eligibility: str | None = None
    capacity: int | None = None
    contract_type: str | None = None
    program_required: str | None = None


class UpdateOpportunityTermsRequest(BaseModel):
    is_paid: bool
    salary_min: float | int | None = None
    salary_max: float | int | None = None
    currency: str = "UZS"
    salary_period: str | None = None
    salary_basis: str | None = None
    start_date: date | str | None = None
    end_date: date | str | None = None
    program_required: str | None = None
    fee_terms_note: str | None = None


class ShiftIntervalItem(BaseModel):
    weekday: int
    start_minute: int
    end_minute: int
    group_code: str = "GROUP_A"
    timezone: str = "Asia/Tashkent"


class UpdateOpportunityScheduleRequest(BaseModel):
    schedule_policy: str = "STRICT"
    shift_match_mode: str = "ALL"
    shifts: list[ShiftIntervalItem] | None = None


@router.put("/{id}/draft", status_code=200)
def api_078_update_opportunity_draft(
    id: UUID,
    payload: UpdateOpportunityDraftRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-078: Update opportunity draft core metadata (`CAP-016`, `JOB_PUBLISH`)."""
    try:
        return opportunity_service.update_opportunity_draft_api_078(
            opportunity_id=str(id),
            actor=actor,
            title=payload.title,
            description=payload.description,
            region=payload.region,
            work_mode=payload.work_mode,
            eligibility=payload.eligibility,
            capacity=payload.capacity,
            contract_type=payload.contract_type,
            program_required=payload.program_required,
        )
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.put("/{id}/draft/terms", status_code=200)
def api_079_update_opportunity_terms(
    id: UUID,
    payload: UpdateOpportunityTermsRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-079: Update opportunity draft financial and duration terms (`CAP-016`, `JOB_PUBLISH`)."""
    try:
        return opportunity_service.update_opportunity_terms_api_079(
            opportunity_id=str(id),
            actor=actor,
            is_paid=payload.is_paid,
            salary_min=payload.salary_min,
            salary_max=payload.salary_max,
            currency=payload.currency,
            salary_period=payload.salary_period,
            salary_basis=payload.salary_basis,
            start_date=payload.start_date,
            end_date=payload.end_date,
            program_required=payload.program_required,
            fee_terms_note=payload.fee_terms_note,
        )
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.put("/{id}/draft/schedule", status_code=200)
def api_080_update_opportunity_schedule(
    id: UUID,
    payload: UpdateOpportunityScheduleRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-080: Update opportunity draft schedule policy, match mode, and shift intervals (`CAP-016`, `JOB_PUBLISH`)."""
    try:
        return opportunity_service.update_opportunity_schedule_api_080(
            opportunity_id=str(id),
            actor=actor,
            schedule_policy=payload.schedule_policy,
            shift_match_mode=payload.shift_match_mode,
            shifts=[s.model_dump() for s in payload.shifts] if payload.shifts is not None else None,
        )
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
