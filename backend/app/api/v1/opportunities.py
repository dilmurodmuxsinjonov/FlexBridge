"""FastAPI router for Opportunities, Shifts, and `API-003` Schedule Matching (`S2.4.1`, `AC-039`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.opportunities import OpportunityConstraintError, opportunity_service

router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


class CreateOpportunityRevisionRequest(BaseModel):
    organization_id: str
    title: str
    opportunity_kind: str = "PART_TIME_JOB"
    contract_type: str = "LABOR_PART_TIME"
    compensation_type: str = "HOURLY"
    hourly_pay: int | None = None
    stipend_amount: int | None = None
    fee_terms_note: str | None = None
    published: bool = True


class CreateOpportunityShiftRequest(BaseModel):
    group_code: str = "GROUP_A"
    weekday: int
    start_minute: int
    end_minute: int
    is_required: bool = True


@router.post("/revisions", status_code=201)
def create_opportunity_revision_endpoint(payload: CreateOpportunityRevisionRequest) -> dict[str, Any]:
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
) -> dict[str, Any]:
    try:
        return opportunity_service.add_opportunity_shift(
            revision_id=revision_id,
            group_code=payload.group_code,
            weekday=payload.weekday,
            start_minute=payload.start_minute,
            end_minute=payload.end_minute,
            is_required=payload.is_required,
        )
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.get("/feed")
def api_003_opportunity_feed(
    candidate_id: str = Query(...),
    schedule_match_mode: str = Query(default="ALL_SHIFTS_IN_GROUP"),
    check_date: str | None = Query(default=None),
) -> dict[str, Any]:
    """API-003: Deterministic schedule matching feed (`ALL_SHIFTS_IN_GROUP` vs `ANY_SHIFT_IN_GROUP`, `AC-039`)."""
    try:
        items = opportunity_service.match_candidate_feed_api_003(
            candidate_id=candidate_id,
            schedule_match_mode=schedule_match_mode,
            check_date=check_date,
        )
        return {
            "contract_id": "API-003",
            "candidate_id": candidate_id,
            "schedule_match_mode": schedule_match_mode,
            "items": items,
        }
    except OpportunityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc
