"""Current coordinator supervision and personally named teacher admission."""
from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,Query
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import ActorContext,require_actor_context
from app.services.academic_admission import academic_service as service
from app.services.academic_views import academic_view_service as views
from app.services.academic_records import academic_record_service as records
from app.services.academic_reviews import academic_review_service as reviews
from app.api.v1.placement_admission import TermsRequest

router=APIRouter(prefix='/api/v1',tags=['academic-admission'])


class SupervisionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    institution_id:UUID
    enrollment_id:UUID
    agreement_id:UUID
    purpose:str=Field(min_length=1,max_length=80)
    legal_basis:str=Field(min_length=1,max_length=2000)
    idempotency_key:str=Field(min_length=8,max_length=128)


class NominationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    institution_id:UUID
    supervisor_id:UUID
    supervision_id:UUID
    idempotency_key:str=Field(min_length=8,max_length=128)


class RevokeRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    idempotency_key:str=Field(min_length=8,max_length=128)


class StudentRequest(TermsRequest):
    enrollment_id:UUID


@router.post('/placements/{id}/academic-requests',status_code=201)
def request_student(id:UUID,payload:StudentRequest,actor:ActorContext=Depends(require_actor_context)):
    values=payload.arguments();values['enrollment_id']=str(payload.enrollment_id)
    return service.request_student(actor=actor,placement_id=str(id),**values)


@router.post('/student-supervisions',status_code=201)
def create_supervision(payload:SupervisionRequest,actor:ActorContext=Depends(require_actor_context)):
    return service.create_supervision(actor,institution_id=str(payload.institution_id),enrollment_id=str(payload.enrollment_id),
        agreement_id=str(payload.agreement_id),purpose=payload.purpose,legal_basis=payload.legal_basis,idempotency_key=payload.idempotency_key)


@router.post('/placements/{id}/academic-assignments',status_code=201)
def nominate(id:UUID,payload:NominationRequest,actor:ActorContext=Depends(require_actor_context)):
    return service.nominate(actor=actor,placement_id=str(id),institution_id=str(payload.institution_id),
        supervisor_id=str(payload.supervisor_id),supervision_id=str(payload.supervision_id),idempotency_key=payload.idempotency_key)


@router.post('/academic-assignments/{id}/revoke')
def revoke(id:UUID,payload:RevokeRequest,actor:ActorContext=Depends(require_actor_context)):
    return service.revoke(actor,str(id),idempotency_key=payload.idempotency_key)


@router.get('/me/academic-assignments')
def own(limit:int=Query(default=50,ge=1,le=100),after:UUID|None=None,actor:ActorContext=Depends(require_actor_context)):
    return service.own_assignments(actor,limit=limit,after=after)


@router.get('/institutions/{inst}/supervisions')
def supervisions(inst:UUID,enrollment_id:UUID|None=None,purpose:str|None=Query(default=None,min_length=1,max_length=80),
        limit:int=Query(default=50,ge=1,le=100),after:UUID|None=None,actor:ActorContext=Depends(require_actor_context)):
    return views.supervisions(actor,str(inst),enrollment_id=str(enrollment_id) if enrollment_id else None,purpose=purpose,
        limit=limit,after=str(after) if after else None)


@router.get('/institutions/{inst}/assignment-queue')
def assignment_queue(inst:UUID,limit:int=Query(default=50,ge=1,le=100),after:UUID|None=None,
        actor:ActorContext=Depends(require_actor_context)):
    return views.assignment_queue(actor,str(inst),limit=limit,after=str(after) if after else None)


@router.get('/student-supervisions/{id}/academic-assignments')
def supervision_assignments(id:UUID,limit:int=Query(default=50,ge=1,le=100),after:UUID|None=None,
        actor:ActorContext=Depends(require_actor_context)):
    return views.supervision_assignments(actor,str(id),limit=limit,after=str(after) if after else None)


@router.get('/institutions/{inst}/academic-agreements')
def agreements(inst:UUID,limit:int=Query(default=50,ge=1,le=100),after:UUID|None=None,
        actor:ActorContext=Depends(require_actor_context)):
    return views.agreements(actor,str(inst),limit=limit,after=str(after) if after else None)


@router.get('/institutions/{inst}/academic-teachers')
def teachers(inst:UUID,limit:int=Query(default=50,ge=1,le=100),after:UUID|None=None,
        actor:ActorContext=Depends(require_actor_context)):
    return views.teachers(actor,str(inst),limit=limit,after=str(after) if after else None)


@router.get('/me/academic-review-queue')
@router.get('/me/teacher-review-queue')
def review_queue(limit:int=Query(default=50,ge=1,le=100),after:UUID|None=None,actor:ActorContext=Depends(require_actor_context)):
    return views.review_queue(actor,limit=limit,after=str(after) if after else None)


@router.get('/log-revisions/{revision}/academic')
def academic_revision(revision:UUID,actor:ActorContext=Depends(require_actor_context)):
    return records.detail(actor,str(revision))


class AcademicReviewRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    academic_assignment_id:UUID
    decision:Literal['REVIEWED','NEEDS_REVISION']
    comment:str=Field(default='',max_length=10000)
    idempotency_key:str=Field(min_length=8,max_length=128)


@router.post('/log-revisions/{revision}/academic-reviews',status_code=201)
def review_revision(revision:UUID,payload:AcademicReviewRequest,actor:ActorContext=Depends(require_actor_context)):
    return reviews.review(actor=actor,revision_id=str(revision),assignment_id=str(payload.academic_assignment_id),
        decision=payload.decision,comment=payload.comment,idempotency_key=payload.idempotency_key)
