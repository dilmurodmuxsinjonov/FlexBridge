"""FastAPI router for Applications, Offers, and Dual-Confirmed Placements (`S2.5.1`, `INV-08`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.placements import PlacementScopeError, placement_service

router = APIRouter(prefix="/api/v1", tags=["placements"])


class CreateApplicationRequest(BaseModel):
    opportunity_id: str
    candidate_id: str


class CreateApplicationAttemptRequest(BaseModel):
    opportunity_id: str
    attempt_no: int = 1


class CreateOfferRequest(BaseModel):
    application_id: str
    opportunity_id: str
    candidate_id: str
    offered_by: str


class CreatePlacementRequest(BaseModel):
    application_id: str
    offer_id: str
    opportunity_id: str
    candidate_id: str
    organization_id: str


class ConfirmPlacementStartRequest(BaseModel):
    party: str  # CANDIDATE | ORGANIZATION


@router.post("/applications", status_code=201)
def create_application_endpoint(payload: CreateApplicationRequest) -> dict[str, Any]:
    return placement_service.create_application(
        opportunity_id=payload.opportunity_id,
        candidate_id=payload.candidate_id,
    )


@router.post("/applications/{application_id}/attempts", status_code=201)
def create_application_attempt_endpoint(
    application_id: str,
    payload: CreateApplicationAttemptRequest,
) -> dict[str, Any]:
    try:
        return placement_service.create_application_attempt(
            application_id=application_id,
            opportunity_id=payload.opportunity_id,
            attempt_no=payload.attempt_no,
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.post("/offers", status_code=201)
def create_offer_endpoint(payload: CreateOfferRequest) -> dict[str, Any]:
    try:
        return placement_service.create_offer(
            application_id=payload.application_id,
            opportunity_id=payload.opportunity_id,
            candidate_id=payload.candidate_id,
            offered_by=payload.offered_by,
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.post("/placements", status_code=201)
def create_placement_endpoint(payload: CreatePlacementRequest) -> dict[str, Any]:
    try:
        return placement_service.create_placement(
            application_id=payload.application_id,
            offer_id=payload.offer_id,
            opportunity_id=payload.opportunity_id,
            candidate_id=payload.candidate_id,
            organization_id=payload.organization_id,
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
) -> dict[str, Any]:
    try:
        return placement_service.confirm_placement_start(
            placement_id=placement_id,
            party=payload.party,
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc
