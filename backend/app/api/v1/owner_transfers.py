"""Existing-owner successor consent and independently reviewed OWNER departure."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Header,Query
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.api.dependencies import ActorContext,require_actor_context
from app.services.owner_transfers import owner_transfer_service as service

router=APIRouter(prefix='/api/v1',tags=['owner-transfers'])

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class Evidence(Input):
    file_ids:list[UUID]=Field(min_length=1,max_length=5)
    evidence_note:str=Field(min_length=15,max_length=4000)

class Proposal(Evidence):
    target_membership_id:UUID

class Resubmission(Evidence):
    expected_revision:int=Field(strict=True,ge=1)

class Consent(Input):
    expected_revision:int=Field(strict=True,ge=1)
    decision:Literal['ACCEPT','DECLINE']
    contact_id:UUID|None=None

    @model_validator(mode='after')
    def require_contact(self):
        if (self.decision=='ACCEPT')!=(self.contact_id is not None):
            raise ValueError('ACCEPT requires a current verified contact; DECLINE does not accept contact fields')
        return self

class Cancellation(Input):
    reason:str=Field(min_length=15,max_length=2000)

@router.post('/organizations/{org}/owner-transfers',status_code=202)
def submit(org:UUID,payload:Proposal,idempotency_key:str=Header(alias='Idempotency-Key',min_length=8,max_length=128),
    actor:ActorContext=Depends(require_actor_context)):
    return service.submit(actor,str(org),target_membership_id=str(payload.target_membership_id),file_ids=payload.file_ids,
        evidence_note=payload.evidence_note,idempotency_key=idempotency_key)

@router.get('/me/owner-transfers')
def queue(limit:int=Query(default=50,ge=1,le=100),after:UUID|None=None,actor:ActorContext=Depends(require_actor_context)):
    return service.target_queue(actor,limit,str(after) if after else None)

@router.get('/owner-transfers/{id}')
def read(id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return service.read(actor,str(id))

@router.post('/owner-transfers/{id}/consent')
def consent(id:UUID,payload:Consent,actor:ActorContext=Depends(require_actor_context)):
    return service.consent(actor,str(id),expected_revision=payload.expected_revision,decision=payload.decision,
        contact_id=str(payload.contact_id) if payload.contact_id else None)

@router.post('/owner-transfers/{id}/resubmit')
def resubmit(id:UUID,payload:Resubmission,actor:ActorContext=Depends(require_actor_context)):
    return service.resubmit(actor,str(id),expected_revision=payload.expected_revision,file_ids=payload.file_ids,evidence_note=payload.evidence_note)

@router.post('/owner-transfers/{id}/cancel')
def cancel(id:UUID,payload:Cancellation,actor:ActorContext=Depends(require_actor_context)):
    return service.cancel(actor,str(id),payload.reason)
