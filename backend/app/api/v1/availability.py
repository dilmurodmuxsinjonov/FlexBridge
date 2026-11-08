"""FastAPI router for Candidate Availability Rules and Exceptions (`S2.3.1`, `INV-01`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.api.dependencies import ActorContext, require_actor_context, candidate_id_for
from app.services.availability import AvailabilityConstraintError, availability_service

router = APIRouter(prefix="/api/v1/candidates", tags=["availability"])


class CreateAvailabilityRuleRequest(BaseModel):
    weekday: int
    start_minute: int
    end_minute: int
    is_active: bool = True


class CreateAvailabilityExceptionRequest(BaseModel):
    exception_date: str
    start_minute: int
    end_minute: int
    kind: str = "UNAVAILABLE"


@router.post("/{candidate_id}/availability-rules", status_code=201)
def create_availability_rule_endpoint(
    candidate_id: str,
    payload: CreateAvailabilityRuleRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    if candidate_id != candidate_id_for(actor):
        raise HTTPException(403,detail={"code":"CANDIDATE_SCOPE_FORBIDDEN"})
    try:
        return availability_service.add_availability_rule(
            candidate_id=candidate_id,
            weekday=payload.weekday,
            start_minute=payload.start_minute,
            end_minute=payload.end_minute,
            is_active=payload.is_active,
        )
    except AvailabilityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.post("/{candidate_id}/availability-exceptions", status_code=201)
def create_availability_exception_endpoint(
    candidate_id: str,
    payload: CreateAvailabilityExceptionRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    if candidate_id != candidate_id_for(actor):
        raise HTTPException(403,detail={"code":"CANDIDATE_SCOPE_FORBIDDEN"})
    try:
        return availability_service.add_availability_exception(
            candidate_id=candidate_id,
            exception_date=payload.exception_date,
            start_minute=payload.start_minute,
            end_minute=payload.end_minute,
            kind=payload.kind,
        )
    except AvailabilityConstraintError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc
