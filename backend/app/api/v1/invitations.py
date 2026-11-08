"""Canonical invitation preview/accept and explicit organization invitations."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field
from app.api.dependencies import ActorContext, require_actor_context
from app.services.invitations import invitation_service as service

router = APIRouter(prefix='/api/v1', tags=['invitations'])
Token = Path(min_length=43,max_length=43,pattern=r'^[A-Za-z0-9_-]{43}$')

class Input(BaseModel):model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class CreateInput(Input):
    channel: Literal['PHONE','EMAIL']
    destination: str = Field(min_length=3,max_length=254)
    role_code: Literal['HR','HOST_COORDINATOR','MENTOR','BILLING']
class RevokeInput(Input):reason:str=Field(min_length=15,max_length=2000)

@router.post('/organizations/{org}/invitations',status_code=201)
def create(org:UUID,payload:CreateInput,actor:ActorContext=Depends(require_actor_context)):
    return {'contract_id':'API-074',**service.create(actor,str(org),**payload.model_dump())}

@router.get('/invitations/{token}')
def preview(token:str=Token):
    return {'contract_id':'API-024',**service.preview(token)}

@router.post('/invitations/{token}/accept')
def accept(payload:Input,token:str=Token,actor:ActorContext=Depends(require_actor_context)):
    return {'contract_id':'API-025',**service.accept(actor,token)}

@router.post('/organizations/{org}/invitations/{id}/revoke')
def revoke(org:UUID,id:UUID,payload:RevokeInput,actor:ActorContext=Depends(require_actor_context)):
    return service.revoke(actor,str(org),str(id),payload.reason)
