"""Fixed-revision continuity intake and separate, independently claimed review stages."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Header,Query
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import ActorContext,require_actor_context
from app.services.owner_continuity import owner_continuity_service as service

router=APIRouter(prefix='/api/v1',tags=['owner-continuity'])
Stage=Literal['moderator','compliance']

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class Request(Input):
    contact_id:UUID
    file_ids:list[UUID]=Field(min_length=1,max_length=5)
    evidence_note:str=Field(min_length=15,max_length=4000)

class Reason(Input):
    reason:str=Field(min_length=15,max_length=2000)

class Decision(Reason):
    expected_revision:int=Field(strict=True,ge=1,le=1)
    decision:Literal['RECOMMEND','APPROVE','REJECT','NEEDS_INFO']

@router.post('/organizations/{org}/owner-continuity',status_code=202)
def submit(org:UUID,payload:Request,idempotency_key:str=Header(alias='Idempotency-Key',min_length=8,max_length=128),
    actor:ActorContext=Depends(require_actor_context)):
    return service.submit(actor,str(org),contact_id=str(payload.contact_id),file_ids=payload.file_ids,
        evidence_note=payload.evidence_note,idempotency_key=idempotency_key)

@router.get('/organizations/{org}/owner-continuity')
def pending(org:UUID,actor:ActorContext=Depends(require_actor_context)):
    return service.owner_pending(actor,str(org))

@router.get('/owner-continuity/{id}')
def read(id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return service.read(actor,str(id))

@router.post('/owner-continuity/{id}/withdraw')
def withdraw(id:UUID,payload:Reason,actor:ActorContext=Depends(require_actor_context)):
    return service.withdraw(actor,str(id),payload.reason)

@router.post('/organizations/{org}/owner-continuity/{id}/object')
def object(org:UUID,id:UUID,payload:Reason,actor:ActorContext=Depends(require_actor_context)):
    return service.object(actor,str(org),str(id),payload.reason)

@router.get('/operator/owner-continuity/{stage}/cases')
def queue(stage:Stage,unassigned:bool=False,limit:int=Query(default=50,ge=1,le=100),actor:ActorContext=Depends(require_actor_context)):
    return {'items':service.queue(actor,stage.upper(),unassigned,limit)}

@router.post('/operator/owner-continuity/{stage}/cases/{id}/claim')
def claim(stage:Stage,id:UUID,payload:Input|None=None,actor:ActorContext=Depends(require_actor_context)):
    return service.claim(actor,str(id),stage.upper())

@router.get('/operator/owner-continuity/{stage}/cases/{id}')
def detail(stage:Stage,id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return service.detail(actor,str(id),stage.upper())

@router.get('/operator/owner-continuity/{stage}/cases/{id}/evidence/{file}/download')
def download(stage:Stage,id:UUID,file:UUID,actor:ActorContext=Depends(require_actor_context)):
    return service.download(actor,str(id),stage.upper(),str(file))

@router.post('/operator/owner-continuity/{stage}/cases/{id}/decide')
def decide(stage:Stage,id:UUID,payload:Decision,actor:ActorContext=Depends(require_actor_context)):
    return service.decide(actor,str(id),stage.upper(),**payload.model_dump())
