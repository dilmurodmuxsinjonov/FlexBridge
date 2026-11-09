"""Institution claim intake and narrowly scoped appointment status."""
from datetime import date
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Header,Query
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import ActorContext,require_actor_context
from app.services.institution_onboarding import institution_onboarding_service as service

router=APIRouter(prefix='/api/v1',tags=['institution-onboarding'])


class AppointmentInput(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    registry_code:str=Field(min_length=3,max_length=64)
    document_file_id:UUID
    contact_id:UUID
    valid_from:date
    valid_to:date|None=None
    legal_basis:str=Field(min_length=15,max_length=4000)
    file_ids:list[UUID]=Field(min_length=1,max_length=5)
    evidence_note:str=Field(min_length=15,max_length=4000)
    name:str|None=Field(default=None,min_length=2,max_length=250)
    region:str|None=Field(default=None,min_length=1,max_length=100)
    agreement_id:UUID|None=None
    agreement_file_id:UUID|None=None
    agreement_valid_from:date|None=None
    agreement_valid_to:date|None=None
    purposes:list[Literal['ACADEMIC_VIEW']]|None=Field(default=None,min_length=1,max_length=1)
    target_channel:Literal['PHONE','EMAIL']|None=None
    target_destination:str|None=Field(default=None,min_length=3,max_length=254)


class ConsentInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_revision:int=Field(strict=True,ge=1)
    decision:Literal['ACCEPT','DECLINE']
    contact_id:UUID|None=None


class RevisionInput(AppointmentInput):
    expected_revision:int=Field(strict=True,ge=1)


class RevokeInput(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    reason:str=Field(min_length=15,max_length=4000)


@router.get('/institution-onboarding/options')
def options(actor:ActorContext=Depends(require_actor_context)):
    return {'contract_id':'API-017',**service.options(actor)}


@router.post('/institution-appointments',status_code=202)
def submit(payload:AppointmentInput,actor:ActorContext=Depends(require_actor_context),
    idempotency_key:str=Header(alias='Idempotency-Key',min_length=8,max_length=128)):
    return {'contract_id':'API-096',**service.submit(actor,**payload.model_dump(),idempotency_key=idempotency_key)}


@router.get('/institution-appointments/{id}')
def status(id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return {'contract_id':'API-097',**service.status(actor,str(id))}


@router.get('/me/institution-appointments')
def inbox(limit:int=Query(default=50,ge=1,le=100),actor:ActorContext=Depends(require_actor_context)):
    return {'items':service.inbox(actor,limit)}


@router.post('/institution-appointments/{id}/consent')
def consent(id:UUID,payload:ConsentInput,actor:ActorContext=Depends(require_actor_context)):
    return service.consent(actor,str(id),expected_revision=payload.expected_revision,decision=payload.decision,
        contact_id=str(payload.contact_id) if payload.contact_id else None)


@router.post('/institution-appointments/{id}/revisions',status_code=202)
def resubmit(id:UUID,payload:RevisionInput,actor:ActorContext=Depends(require_actor_context)):
    return service.resubmit(actor,str(id),**payload.model_dump())


@router.post('/institution-appointments/{id}/revoke')
def revoke(id:UUID,payload:RevokeInput,actor:ActorContext=Depends(require_actor_context)):
    return service.revoke(actor,str(id),reason=payload.reason)


@router.get('/institution-appointments/{id}/files/{file_id}/download')
def download(id:UUID,file_id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return service.download_own(actor,str(id),str(file_id))
