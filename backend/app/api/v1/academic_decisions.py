"""Whole-placement nonofficial academic conclusion under exact current teacher."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter,Depends
from pydantic import BaseModel,ConfigDict,Field,StrictInt,StrictStr

from app.api.dependencies import ActorContext,require_actor_context
from app.core.iam_security import rate_limit
from app.services.academic_decisions import academic_decision_service as service

router=APIRouter(prefix='/api/v1',tags=['academic-decisions'])


class AcademicDecisionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    academic_assignment_id:UUID
    terms_id:UUID
    version:StrictInt=Field(ge=1)
    expected_basis_digest:StrictStr=Field(pattern=r'^[0-9a-f]{64}$')
    decision:Literal['ACADEMIC_REVIEW_COMPLETE','ACADEMIC_REVISION_REQUIRED']
    reason:StrictStr=Field(min_length=1,max_length=2000)
    idempotency_key:StrictStr=Field(min_length=8,max_length=128)


@router.get('/placements/{id}/academic-decision-context')
def conclusion_context(id:UUID,academic_assignment_id:UUID,
        actor:ActorContext=Depends(require_actor_context)):
    rate_limit('academic-conclusion-context',actor.user_id,60,600)
    return service.context(actor=actor,placement_id=str(id),assignment_id=str(academic_assignment_id))


@router.post('/placements/{id}/academic-decisions',status_code=201)
def conclude_academic(id:UUID,payload:AcademicDecisionRequest,
        actor:ActorContext=Depends(require_actor_context)):
    rate_limit('academic-conclusion',actor.user_id,20,600)
    return service.conclude(actor=actor,placement_id=str(id),assignment_id=str(payload.academic_assignment_id),
        terms_id=str(payload.terms_id),version=payload.version,expected_basis_digest=payload.expected_basis_digest,
        decision=payload.decision,reason=payload.reason,idempotency_key=payload.idempotency_key)
