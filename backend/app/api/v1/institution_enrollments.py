"""University coordinators confirm their own students' enrollment (until HEMIS).

The same independent-review lifecycle as the moderator queue (claim -> detail ->
evidence -> decision), scoped to enrollments that name the coordinator's
institution. Authority is rechecked by the service and by the 0022 DB guard.
"""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.dependencies import ActorContext, require_actor_context
from app.db.storage import table, transaction
from app.services.enrollments import enrollment_service as service

router = APIRouter(prefix='/api/v1/institutions', tags=['institution-enrollments'])
FILES_BASE = '/api/v1/institutions/{inst}/enrollment-requests/'


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    decision: Literal['APPROVE', 'REJECT', 'NEEDS_INFO']
    expected_revision: int = Field(strict=True, ge=1)
    reason: str = Field(min_length=15, max_length=2000)


def _case_in_institution(inst: UUID, case_id: UUID) -> None:
    """The path institution must be the enrollment's institution (no cross-institution IDs)."""
    cases, enrollments = table('verification_cases'), table('enrollments')
    with transaction() as conn:
        found = conn.execute(select(cases.c.id).join(enrollments, enrollments.c.id == cases.c.enrollment_id).where(
            cases.c.id == str(case_id), cases.c.kind == 'ENROLLMENT',
            enrollments.c.institution_id == str(inst))).first()
    if not found:
        raise HTTPException(404, detail={'code': 'ENROLLMENT_REQUEST_NOT_FOUND'})


@router.get('/{inst}/enrollment-requests')
def list_requests(inst: UUID, mine: bool = False, limit: int = Query(default=50, ge=1, le=100),
                  actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    return {'institution_id': str(inst), 'items': service.institution_queue(actor, str(inst), mine=mine, limit=limit)}


@router.post('/{inst}/enrollment-requests/{case_id}/claim')
def claim(inst: UUID, case_id: UUID, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    _case_in_institution(inst, case_id)
    return service.claim(actor, str(case_id))


@router.get('/{inst}/enrollment-requests/{case_id}')
def detail(inst: UUID, case_id: UUID, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    _case_in_institution(inst, case_id)
    return service.case_detail(actor, str(case_id), files_base=FILES_BASE.format(inst=inst))


@router.get('/{inst}/enrollment-requests/{case_id}/files/{file_id}/download')
def download(inst: UUID, case_id: UUID, file_id: UUID,
             actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    _case_in_institution(inst, case_id)
    return service.download_evidence(actor, str(case_id), str(file_id))


@router.post('/{inst}/enrollment-requests/{case_id}/decision')
def decide(inst: UUID, case_id: UUID, payload: Decision,
           actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    _case_in_institution(inst, case_id)
    return service.decide(actor, str(case_id), decision=payload.decision,
                          expected_revision=payload.expected_revision, reason=payload.reason)


# --- Account recovery vouched by the student's university (Issue #237) -------
from app.services.institution_recovery import institution_recovery_service as recovery_service  # noqa: E402


class RecoveryDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    decision: Literal['APPROVE', 'REJECT']
    reason: str = Field(min_length=15, max_length=2000)


@router.get('/{inst}/recovery-requests')
def recovery_queue(inst: UUID, actor: ActorContext = Depends(require_actor_context)):
    """Coordinator: pending password-recovery requests of the institution's verified students."""
    return recovery_service.queue(actor, str(inst))


@router.post('/{inst}/recovery-requests/{request_id}/decide')
def recovery_decide(inst: UUID, request_id: UUID, payload: RecoveryDecision,
                    actor: ActorContext = Depends(require_actor_context)):
    return recovery_service.decide(actor, str(inst), str(request_id), decision=payload.decision, reason=payload.reason)
