"""FastAPI router for Applications, Offers, and Dual-Confirmed Placements (`S2.5.1`, `INV-08`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date

from app.api.dependencies import ActorContext, require_actor_context, candidate_id_for,require_org
from app.services.placements import PlacementScopeError, placement_service
from app.api.v1.placement_admission import TermsRequest

router = APIRouter(prefix="/api/v1", tags=["placements"])


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateApplicationRequest(StrictDTO):
    opportunity_id: UUID
    candidate_id: UUID


class CreateApplicationAttemptRequest(StrictDTO):
    opportunity_id: UUID
    attempt_no: int = 1


class CreateOfferRequest(StrictDTO):
    application_id: UUID
    opportunity_id: UUID
    candidate_id: UUID


class CreatePlacementRequest(StrictDTO):
    application_id: UUID
    offer_id: UUID
    opportunity_id: UUID
    candidate_id: UUID
    organization_id: UUID


class ConfirmPlacementStartRequest(TermsRequest):
    party: str  # CANDIDATE | ORGANIZATION


@router.post("/applications", status_code=201)
def create_application_endpoint(payload: CreateApplicationRequest, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    return placement_service.create_application(
        opportunity_id=str(payload.opportunity_id),
        candidate_id=str(payload.candidate_id),
        actor_user_id=actor.user_id,
    )


@router.post("/applications/{application_id}/attempts", status_code=201)
def create_application_attempt_endpoint(
    application_id: str,
    payload: CreateApplicationAttemptRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return placement_service.create_application_attempt(
            application_id=application_id,
            opportunity_id=str(payload.opportunity_id),
            attempt_no=payload.attempt_no,
            actor_user_id=actor.user_id,
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.post("/offers", status_code=201)
def create_offer_endpoint(payload: CreateOfferRequest, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    try:
        return placement_service.create_offer(
            application_id=str(payload.application_id),
            opportunity_id=str(payload.opportunity_id),
            candidate_id=str(payload.candidate_id),
            offered_by=actor.user_id,
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.post("/placements", status_code=201)
def create_placement_endpoint(payload: CreatePlacementRequest, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    require_org(actor,str(payload.organization_id),'OWNER','HOST_COORDINATOR')
    try:
        return placement_service.create_placement(
            application_id=str(payload.application_id),
            offer_id=str(payload.offer_id),
            opportunity_id=str(payload.opportunity_id),
            candidate_id=str(payload.candidate_id),
            organization_id=str(payload.organization_id),
            actor=actor,
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.post("/placements/{placement_id}/confirm-start")
def confirm_placement_start_endpoint(
    placement_id: str,
    payload: ConfirmPlacementStartRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        return placement_service.confirm_placement_start(
            placement_id=placement_id,
            actor=actor,
            **payload.arguments(),
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc
