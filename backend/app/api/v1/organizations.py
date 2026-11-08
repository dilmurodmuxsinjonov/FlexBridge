"""Organization onboarding and assigned ORG verification endpoints."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator
from app.api.dependencies import ActorContext, require_actor_context
from app.services.organizations import organization_service as service

router = APIRouter(prefix='/api/v1', tags=['organizations'])

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class EvidenceInput(Input):
    file_ids: list[UUID] = Field(min_length=1, max_length=5)
    evidence_note: str = Field(min_length=15, max_length=4000)

class RegisterInput(EvidenceInput):
    tax_id: str = Field(min_length=3, max_length=64)
    legal_name: str = Field(min_length=2, max_length=250)
    public_name: str = Field(min_length=2, max_length=200)
    region: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    website: HttpUrl | None = None
    membership_role: Literal['HR','HOST_COORDINATOR','MENTOR','BILLING'] = 'HR'

class VerificationInput(EvidenceInput):
    kind: Literal['ORG_REPRESENTATIVE','ORG_PROFILE_CHANGE','JOB_EMPLOYER','INTERNSHIP_HOST']
    case_id: UUID | None = None

class OrganizationPatch(EvidenceInput):
    legal_name: str | None = Field(default=None, min_length=2, max_length=250)
    public_name: str | None = Field(default=None, min_length=2, max_length=200)
    region: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    website: HttpUrl | None = None

    @model_validator(mode='after')
    def nonnull(self):
        if any(getattr(self, name) is None for name in self.model_fields_set & {'legal_name','public_name','region'}):
            raise ValueError('Only description and website may be cleared')
        return self

class DecisionInput(Input):
    decision: Literal['APPROVE','REJECT','NEEDS_INFO']
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=15, max_length=2000)

class RevokeInput(Input):
    reason: str = Field(min_length=15, max_length=2000)

@router.post('/organizations', status_code=202)
def register(payload: RegisterInput, actor: ActorContext = Depends(require_actor_context)):
    fields = payload.model_dump()
    fields['website'] = str(payload.website) if payload.website else None
    return {'contract_id':'API-065', **service.register(actor, **fields)}

@router.get('/organizations/{id}/public')
def public(id: UUID):
    return {'contract_id':'API-008', **service.public(str(id))}

@router.post('/organizations/{id}/verification', status_code=202)
def submit(id: UUID, payload: VerificationInput, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id':'API-066', **service.submit(actor, str(id), kind=payload.kind,
        file_ids=payload.file_ids, evidence_note=payload.evidence_note, case_id=str(payload.case_id) if payload.case_id else None)}

@router.get('/organizations/{id}/verification')
def status(id: UUID, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id':'API-067', **service.status(actor, str(id))}

@router.patch('/organizations/{org}', status_code=202)
def patch(org: UUID, payload: OrganizationPatch, actor: ActorContext = Depends(require_actor_context)):
    changes = payload.model_dump(exclude_unset=True, exclude={'file_ids','evidence_note'})
    if 'website' in changes:
        changes['website'] = str(payload.website) if payload.website else None
    return {'contract_id':'API-071', **service.patch(actor, str(org), changes, payload.file_ids, payload.evidence_note)}

@router.get('/organizations/{org}/capabilities')
def capabilities(org: UUID, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id':'API-072', 'items':service.capabilities(actor, str(org))}

@router.post('/organizations/{org}/memberships/{id}/revoke')
def revoke(org: UUID, id: UUID, payload: RevokeInput, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id':'API-075', **service.revoke(actor, str(org), str(id), payload.reason)}

@router.get('/operator/verification-cases')
def queue(unassigned: bool = False, limit: int = Query(default=50, ge=1, le=100), actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id':'API-109', 'items':service.queue(actor, unassigned, limit)}

@router.post('/operator/verification-cases/{id}/claim')
def claim(id: UUID, actor: ActorContext = Depends(require_actor_context)):
    return service.claim(actor, str(id))

@router.get('/operator/verification-cases/{id}')
def detail(id: UUID, actor: ActorContext = Depends(require_actor_context)):
    return service.case_detail(actor, str(id))

@router.get('/operator/verification-cases/{id}/files/{file_id}/download')
def download(id: UUID, file_id: UUID, actor: ActorContext = Depends(require_actor_context)):
    return service.download_evidence(actor, str(id), str(file_id))

@router.post('/operator/verification-cases/{id}/decide')
def decide(id: UUID, payload: DecisionInput, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id':'API-110', **service.decide(actor, str(id), **payload.model_dump())}

@router.get('/organizations/{org}/membership-requests/{id}')
def join_detail(org: UUID, id: UUID, actor: ActorContext = Depends(require_actor_context)):
    return service.join_detail(actor, str(org), str(id))

@router.get('/organizations/{org}/membership-requests/{id}/files/{file_id}/download')
def join_download(org: UUID, id: UUID, file_id: UUID, actor: ActorContext = Depends(require_actor_context)):
    return service.join_download(actor, str(org), str(id), str(file_id))
