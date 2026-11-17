"""Canonical host admission and bounded plan/revocation helpers."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ActorContext, require_actor_context
from app.services.placement_admission import admission_service as service
from app.services.placements import get_row
from app.db.storage import transaction

router = APIRouter(prefix='/api/v1', tags=['placement-admission'])


class TermsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    terms_id: UUID
    version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=128)

    def arguments(self):
        return {**self.model_dump(exclude={'terms_id'}), 'terms_id': str(self.terms_id)}


class HostDecisionRequest(TermsRequest):
    action: Literal['ACTIVATE', 'CANCEL', 'APPROVE_COMPLETION', 'DISPUTE']


class AssignmentAcceptRequest(TermsRequest):
    assignment_kind:Literal['MENTOR','TEACHER']='MENTOR'


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_.-]+$')
    title: str = Field(min_length=1, max_length=250)
    expected_result: str = Field(min_length=1, max_length=2000)
    required: bool
    target_minutes: int | None = Field(default=None, ge=0)


class PlanRequest(TermsRequest):
    title: str = Field(min_length=1, max_length=250)
    objectives: str = Field(min_length=1, max_length=4000)
    daily_limit_minutes: int = Field(ge=1, le=1440)
    weekly_limit_minutes: int = Field(ge=1, le=10080)
    required_minutes: int = Field(ge=0)
    tasks: list[TaskRequest] = Field(min_length=1, max_length=100)


class NominateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mentor_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=128)


@router.get('/me/placements')
def own_placements(limit: int=Query(default=50,ge=1,le=100), after: UUID|None=None,
                   actor: ActorContext = Depends(require_actor_context)):
    res = service.own_placements(actor,limit=limit,after=after)
    return {'contract_id': 'API-030', **res}


@router.get('/organizations/{org}/placements')
def host_placements(org: UUID, limit: int=Query(default=50,ge=1,le=100), after: UUID|None=None,
                    actor: ActorContext = Depends(require_actor_context)):
    res = service.host_placements(actor,str(org),limit=limit,after=after)
    return {'contract_id': 'API-069', **res}


@router.get('/me/mentor-assignments')
def own_mentor_assignments(limit: int=Query(default=50,ge=1,le=100), after: UUID|None=None,
                           actor: ActorContext = Depends(require_actor_context)):
    res = service.own_mentor_assignments(actor,limit=limit,after=after)
    return {'contract_id': 'API-089', **res}


@router.get('/placements/{id}/plan')
def plan(id: UUID, actor: ActorContext = Depends(require_actor_context)):
    res = service.plan(actor=actor, placement_id=str(id))
    return {'contract_id': 'API-050', **res}


@router.put('/placements/{id}/plan')
def publish_plan(id: UUID, payload: PlanRequest, actor: ActorContext = Depends(require_actor_context)):
    values = payload.arguments()
    values['tasks'] = [task.model_dump() for task in payload.tasks]
    return service.publish_plan(actor=actor, placement_id=str(id), **values)


@router.post('/placements/{id}/accept')
def accept_candidate(id: UUID, payload: TermsRequest, actor: ActorContext = Depends(require_actor_context)):
    return service.accept_candidate(actor=actor, placement_id=str(id), **payload.arguments())


@router.post('/placements/{id}/assignments/{assignment}/accept')
def accept_assignment(id: UUID, assignment: UUID, payload: AssignmentAcceptRequest, actor: ActorContext = Depends(require_actor_context)):
    values=payload.arguments();kind=values.pop('assignment_kind')
    if kind=='TEACHER':
        from app.services.academic_admission import academic_service
        receipt = academic_service.accept(actor=actor,placement_id=str(id),assignment_id=str(assignment),**values)
    else:
        receipt = service.accept_mentor(actor=actor, placement_id=str(id), assignment_id=str(assignment), **values)
    return {'contract_id': 'API-051', **receipt}


@router.post('/placements/{id}/mentor-assignments', status_code=201)
def nominate(id: UUID, payload: NominateRequest, actor: ActorContext = Depends(require_actor_context)):
    with transaction() as conn:
        organization_id = get_row(conn, 'placements', str(id))['organization_id']
    return service.nominate_mentor(actor=actor, placement_id=str(id), organization_id=organization_id,
                                  mentor_id=str(payload.mentor_id), idempotency_key=payload.idempotency_key)


@router.post('/placements/{id}/mentor-assignments/{assignment}/revoke')
def revoke(id: UUID, assignment: UUID, payload: TermsRequest, actor: ActorContext = Depends(require_actor_context)):
    return service.revoke_mentor(actor=actor, placement_id=str(id), assignment_id=str(assignment), **payload.arguments())


@router.post('/placements/{id}/host-decisions')
def host_decision(id: UUID, payload: HostDecisionRequest, actor: ActorContext = Depends(require_actor_context)):
    return service.host_decision(actor=actor, placement_id=str(id), **payload.arguments())
