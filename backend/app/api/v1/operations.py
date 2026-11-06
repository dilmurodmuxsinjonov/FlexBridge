"""S2.9.1 & S2.10.1: FastAPI Endpoints for Moderation Appeals, Retention Execution & R1 Pilot Readiness."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.operations import OperationsInvariantError, PilotOperationsService

router = APIRouter(prefix="/api/v1/operations", tags=["operations-pilot"])
operations_service = PilotOperationsService()


class ModerationAppealRequest(BaseModel):
    moderation_action_id: str
    appellant_user_id: str
    original_moderator_id: str
    appeal_reviewer_id: str
    appeal_reason: str
    decision: str
    resolution_note: str


class RetentionJobRequest(BaseModel):
    data_category: str
    age_days: int
    records_scanned: int
    executed_by: str


@router.post("/moderation-appeals", status_code=201)
def resolve_moderation_appeal_endpoint(req: ModerationAppealRequest):
    try:
        rec = operations_service.submit_and_resolve_moderation_appeal(
            moderation_action_id=req.moderation_action_id,
            appellant_user_id=req.appellant_user_id,
            original_moderator_id=req.original_moderator_id,
            appeal_reviewer_id=req.appeal_reviewer_id,
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


@router.post("/retention-executions", status_code=201)
def execute_retention_job_endpoint(req: RetentionJobRequest):
    try:
        rec = operations_service.execute_retention_job(
            data_category=req.data_category,
            age_days=req.age_days,
            records_scanned=req.records_scanned,
            executed_by=req.executed_by,
        )
        return {
            "execution_id": rec.id,
            "data_category": rec.data_category,
            "records_scanned": rec.records_scanned,
            "records_actioned": rec.records_actioned,
            "executed_action": rec.executed_action,
            "legal_basis": rec.legal_basis,
        }
    except (OperationsInvariantError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/pilot-readiness")
def get_pilot_readiness_endpoint():
    return operations_service.get_pilot_readiness_report()
