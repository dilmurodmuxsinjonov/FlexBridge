"""Durable dry-run evaluation records and truthful operations readiness."""
from uuid import UUID
from fastapi import APIRouter,Depends,Header,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import ActorContext,require_actor_context,require_platform
from app.services.organizations import require_mfa
from app.services.operations import PilotOperationsService

router=APIRouter(prefix='/api/v1/operations',tags=['operations-pilot'])
operations_service=PilotOperationsService()

class RetentionEvaluationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    data_category:str=Field(min_length=1,max_length=80)
    age_days:int=Field(ge=0,le=365000)
    # Compatibility input; actual counters stay zero.
    records_scanned:int=Field(default=0,ge=0,le=1000000000)

@router.post('/moderation-appeals',status_code=410)
def retired_combined_appeal(actor:ActorContext=Depends(require_actor_context)):
    require_platform(actor,'MODERATOR');require_mfa(actor)
    raise HTTPException(410,detail={'code':'COMBINED_APPEAL_REMOVED_SEPARATE_DURABLE_REVIEW_REQUIRED'})

@router.post('/retention-executions')
def record_retention_evaluation(payload:RetentionEvaluationRequest,
    idempotency_key:str=Header(alias='Idempotency-Key',min_length=8,max_length=128),
    actor:ActorContext=Depends(require_actor_context)):
    return operations_service.record_retention_evaluation(actor,idempotency_key=idempotency_key,**payload.model_dump())

@router.get('/retention-executions/{id}')
def read_retention_evaluation(id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return operations_service.get_retention_evaluation(actor,str(id))

@router.get('/pilot-readiness')
def get_pilot_readiness_endpoint(actor:ActorContext=Depends(require_actor_context)):
    require_platform(actor,'ADMIN','COMPLIANCE')
    return operations_service.get_pilot_readiness_report()
