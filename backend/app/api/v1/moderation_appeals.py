"""Distinct appellant, assignment and independent decision requests."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import ActorContext,require_actor_context
from app.services.moderation_appeals import ModerationAppealsService

router=APIRouter(prefix='/api/v1',tags=['moderation-appeals'])
service=ModerationAppealsService()

class AppealSubmission(BaseModel):
    model_config=ConfigDict(extra='forbid')
    reason:str=Field(min_length=15,max_length=4000)

class AppealDecision(AppealSubmission):
    decision:Literal['UPHOLD','REOPEN']

class ClaimRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')

@router.post('/moderation/actions/{id}/appeals',status_code=201)
def submit(id:UUID,payload:AppealSubmission,actor:ActorContext=Depends(require_actor_context)):
    return service.submit(actor,str(id),payload.reason)

@router.get('/moderation-appeals/{id}')
def read(id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return service.read(actor,str(id))

@router.get('/operator/moderation-appeals')
def queue(limit:int=Query(default=50,ge=1,le=100),after:UUID|None=None,actor:ActorContext=Depends(require_actor_context)):
    return service.queue(actor,limit,str(after) if after else None)

@router.post('/operator/moderation-cases/{id}/claim')
def claim(id:UUID,payload:ClaimRequest,actor:ActorContext=Depends(require_actor_context)):
    return service.claim(actor,str(id))

@router.post('/operator/moderation-cases/{id}/actions')
def decide(id:UUID,payload:AppealDecision,actor:ActorContext=Depends(require_actor_context)):
    """API-111: supported scope is an assigned opportunity rejection appeal."""
    return service.decide(actor,str(id),payload.decision,payload.reason)
