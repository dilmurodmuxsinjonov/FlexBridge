"""S2.9.1 & S2.10.1: FastAPI Endpoints for Moderation Appeals, Retention Execution & R1 Pilot Readiness."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel,ConfigDict
from app.db.storage import transaction
from app.services.placements import get_row

from app.api.dependencies import ActorContext, require_actor_context, require_platform
from app.services.operations import OperationsInvariantError, PilotOperationsService

router = APIRouter(prefix="/api/v1/operations", tags=["operations-pilot"])
operations_service = PilotOperationsService()


class ModerationAppealRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    moderation_action_id: str
    appellant_user_id: str
    appeal_reason: str
    decision: str
    resolution_note: str


class RetentionJobRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    data_category: str
    age_days: int
    records_scanned: int


@router.post("/moderation-appeals", status_code=201)
def resolve_moderation_appeal_endpoint(req: ModerationAppealRequest, actor: ActorContext = Depends(require_actor_context)):
    require_platform(actor,'MODERATOR')
    with transaction() as conn:
        original=get_row(conn,'moderation_actions',req.moderation_action_id)
    try:
        rec = operations_service.submit_and_resolve_moderation_appeal(
            moderation_action_id=req.moderation_action_id,
            appellant_user_id=req.appellant_user_id,
            original_moderator_id=original['actor_id'],
            appeal_reviewer_id=actor.user_id,
            appeal_reason=req.appeal_reason,
            decision=req.decision,
            resolution_note=req.resolution_note,
        )
        return {
            "appeal_id": rec.id,
            "moderation_action_id": rec.moderation_action_id,
            "decision": rec.decision,
            "appeal_reviewer_id": rec.appeal_reviewer_id,
            "resolution_note": rec.resolution_note,
        }
    except OperationsInvariantError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/retention-executions")
def execute_retention_job_endpoint(req: RetentionJobRequest, actor: ActorContext = Depends(require_actor_context)):
    require_platform(actor,'COMPLIANCE')
    try:
        evaluation=operations_service.retention_service.evaluate_age_days(req.data_category,req.age_days)
        return {
            'dry_run':True,'execution_status':'NOT_EXECUTED','records_actioned':0,'evaluation':evaluation,
        }
    except (OperationsInvariantError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/pilot-readiness")
def get_pilot_readiness_endpoint(actor: ActorContext = Depends(require_actor_context)):
    require_platform(actor,'ADMIN','COMPLIANCE')
    return operations_service.get_pilot_readiness_report()
