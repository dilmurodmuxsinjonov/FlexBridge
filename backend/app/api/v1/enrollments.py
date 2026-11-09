"""Canonical own education history and private lifecycle helpers."""
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from app.api.dependencies import ActorContext, require_actor_context
from app.services.enrollments import enrollment_service as service

router=APIRouter(prefix='/api/v1/me/enrollments',tags=['enrollments'])


class Input(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


class Proposal(Input):
    program: str=Field(min_length=1,max_length=250)
    start_date: date
    end_date: date|None=None
    student_ref: str|None=Field(default=None,min_length=1,max_length=256)
    file_ids: list[UUID]=Field(default_factory=list,max_length=5)
    evidence_note: str=Field(default='',max_length=4000)


class Create(Proposal):
    institution_id: UUID
    idempotency_key: str=Field(min_length=8,max_length=128)


class Revision(Proposal):
    expected_revision: int=Field(strict=True,ge=1)
    file_ids: list[UUID]=Field(min_length=1,max_length=5)
    evidence_note: str=Field(min_length=15,max_length=4000)


class End(Input):
    idempotency_key: str=Field(min_length=8,max_length=128)
    reason: str=Field(min_length=15,max_length=2000)
    effective_end_date: date|None=None


@router.post('',status_code=201)
def create(payload:Create,actor:ActorContext=Depends(require_actor_context)):
    fields=payload.model_dump(exclude={'institution_id'})
    return {'contract_id':'API-027',**service.create(actor,institution_id=str(payload.institution_id),**fields)}


@router.get('')
def list_own(limit:int=Query(default=50,ge=1,le=100),after_id:UUID|None=None,actor:ActorContext=Depends(require_actor_context)):
    return {'contract_id':'API-034',**service.list_own(actor,limit=limit,after_id=str(after_id) if after_id else None)}


@router.get('/{id}')
def detail(id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return service.detail_own(actor,str(id))


@router.post('/{id}/verification',status_code=202)
def submit(id:UUID,payload:Revision,actor:ActorContext=Depends(require_actor_context)):
    return service.submit_revision(actor,str(id),**payload.model_dump(exclude_unset=True))


@router.post('/{id}/end')
def end(id:UUID,payload:End,actor:ActorContext=Depends(require_actor_context)):
    return service.end_own(actor,str(id),**payload.model_dump())
