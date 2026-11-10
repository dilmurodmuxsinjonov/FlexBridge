"""FastAPI router for Applications, Offers, and Dual-Confirmed Placements (`S2.5.1`, `INV-08`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field
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
    idempotency_key: str = Field(min_length=8, max_length=128)


class ConfirmPlacementStartRequest(TermsRequest):
    party: str  # CANDIDATE | ORGANIZATION


class PlacementCompletionRequest(StrictDTO):
    terms_id: UUID
    version: int
    idempotency_key: str = Field(min_length=8, max_length=128)
    decision: str = Field(default='REQUEST_COMPLETION', pattern='^(REQUEST_COMPLETION|CONFIRM_COMPLETION|REJECT_COMPLETION)$')
    reason: str | None = Field(default=None, max_length=2000)
    early_reason: str | None = Field(default=None, max_length=2000)


class PlacementExportRequest(StrictDTO):
    idempotency_key: str = Field(min_length=8, max_length=128)
    format: str = Field(default='PDF', pattern='^(PDF|JSON)$')
    include_reviews: bool = True


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
            idempotency_key=payload.idempotency_key,
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


@router.post("/placements/{placement_id}/completion-requests", status_code=201)
def request_placement_completion_endpoint(
    placement_id: str,
    payload: PlacementCompletionRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        from app.services.placement_completion import completion_service
        return completion_service.request_or_confirm_completion(
            actor=actor,
            placement_id=placement_id,
            terms_id=str(payload.terms_id),
            version=payload.version,
            idempotency_key=payload.idempotency_key,
            decision=payload.decision,
            reason=payload.reason,
            early_reason=payload.early_reason,
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.post("/placements/{placement_id}/exports", status_code=201)
def export_placement_endpoint(
    placement_id: str,
    payload: PlacementExportRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    try:
        from app.services.placement_export import export_service
        return export_service.export_placement(
            actor=actor,
            placement_id=placement_id,
            idempotency_key=payload.idempotency_key,
            export_format=payload.format,
            include_reviews=payload.include_reviews,
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc


@router.get("/placements/{placement_id}/logs")
def get_placement_logs_endpoint(
    placement_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    include_tasks: bool = True,
    include_reviews: bool = True,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Single Placement Diary Logs View (API-053 / CAP-022 / PG-022.S01)."""
    try:
        from app.services.placement_logs import placement_logs_service
        return placement_logs_service.get_placement_logs_api_053(
            actor=actor,
            placement_id=placement_id,
            from_date=from_date,
            to_date=to_date,
            status=status,
            page=page,
            page_size=page_size,
            include_tasks=include_tasks,
            include_reviews=include_reviews,
        )
    except PlacementScopeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "sqlstate": exc.sqlstate, "message": str(exc)},
        ) from exc
