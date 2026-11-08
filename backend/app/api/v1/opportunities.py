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
