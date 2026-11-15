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
from app.services.university_directory import university_directory_service
from app.services.university_timetable import university_timetable_service
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


class InstitutionDirectoryInput(BaseModel):
    model_config=ConfigDict(extra='allow')
    official_name:str|None=None
    short_name:str|None=None
    registry_code:str|None=None
    institution_type:str|None=None
    region:str|None=None
    address:str|None=None
    rector_name:str|None=None
    career_center_head:str|None=None
    contact_phone:str|None=None
    contact_email:str|None=None
    website_url:str|None=None
    faculties:list[dict]|None=None
    programs:list[dict]|None=None
    annual_intern_quota:int|None=None
    internship_policy_summary:str|None=None


class PartnerAgreementCreateInput(BaseModel):
    model_config=ConfigDict(extra='allow')
    partner_organization_name:str=Field(min_length=2,max_length=200)
    agreement_number:str|None=Field(default=None,max_length=80)
    valid_from:str|None=None
    valid_to:str|None=None
    purposes:list[str]=Field(default_factory=lambda:['ACADEMIC_VIEW','INTERNSHIP_SUPERVISION'])
    quota_slots:int=Field(default=25,ge=1,le=5000)
    coordinator_note:str|None=Field(default=None,max_length=1000)
    signed_file_id:UUID|None=None


@router.get('/institutions/{inst}/directory-profile')
def get_institution_directory_profile(inst:UUID,actor:ActorContext=Depends(require_actor_context)):
    return university_directory_service.get_directory_profile(actor,str(inst))


@router.put('/institutions/{inst}/directory-profile')
def put_institution_directory_profile(inst:UUID,payload:InstitutionDirectoryInput,actor:ActorContext=Depends(require_actor_context)):
    return university_directory_service.update_directory_profile(actor,str(inst),payload.model_dump(exclude_unset=True))


@router.post('/institutions/{inst}/academic-agreements',status_code=201)
def create_institution_agreement(inst:UUID,payload:PartnerAgreementCreateInput,actor:ActorContext=Depends(require_actor_context)):
    return university_directory_service.create_partner_agreement(actor,str(inst),payload.model_dump())


class TimetableManualSaveInput(BaseModel):
    model_config=ConfigDict(extra='allow')
    mode:Literal['REPLACE','APPEND','DELETE_SLOT','MERGE_GROUP']='REPLACE'
    slots:list[dict]|None=None
    slot:dict|None=None
    slot_id:str|None=None
    group_code:str|None=None
    academic_semester:str|None=None
    commute_buffer_minutes:int|None=Field(default=30,ge=0,le=120)
    sync_student_availability:bool=True


class TimetableTemplateImportInput(BaseModel):
    model_config=ConfigDict(extra='allow')
    format:Literal['CSV','JSON']='CSV'
    content:str|None=Field(default=None,max_length=5_000_000)
    content_base64:str|None=Field(default=None,max_length=7_000_000)
    replace_existing:bool=True
    academic_semester:str|None=None
    commute_buffer_minutes:int|None=Field(default=30,ge=0,le=120)
    sync_student_availability:bool=True


@router.get('/institutions/{inst}/timetables')
def get_institution_timetable(
    inst:UUID,
    group_code:str|None=Query(default=None,max_length=60),
    actor:ActorContext=Depends(require_actor_context),
):
    return university_timetable_service.get_timetable(actor,str(inst),group_code=group_code)


@router.put('/institutions/{inst}/timetables')
def put_institution_timetable(
    inst:UUID,
    payload:TimetableManualSaveInput,
    actor:ActorContext=Depends(require_actor_context),
):
    return university_timetable_service.save_manual_timetable(actor,str(inst),payload.model_dump(exclude_unset=True))


@router.get('/institutions/{inst}/timetables/template')
def get_institution_timetable_template(
    inst:UUID,
    format:Literal['CSV','JSON']=Query(default='CSV'),
    actor:ActorContext=Depends(require_actor_context),
):
    return university_timetable_service.get_template_specification(actor,str(inst),template_format=format)


@router.post('/institutions/{inst}/timetables/import',status_code=201)
def import_institution_timetable(
    inst:UUID,
    payload:TimetableTemplateImportInput,
    actor:ActorContext=Depends(require_actor_context),
):
    return university_timetable_service.import_timetable_from_template(actor,str(inst),payload.model_dump(exclude_unset=True))


