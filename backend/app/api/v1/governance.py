"""FastAPI router for Organization Dual-Control (`INV-11`), Canonical `API-073`, Academic Assignments, and Moderation (`AC-041`).

Enforces server-side `ActorContext` (`Authorization: Bearer <token>`) on academic assignment endpoints (`R-01`).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from app.services.internship_logs import internship_log_service
from app.db.storage import transaction,table,now
from app.services.placements import get_row

from app.api.dependencies import ActorContext, require_actor_context, require_org, require_institution, require_platform
from app.services.governance import GovernanceError, governance_service
from app.services.organizations import require_mfa

router = APIRouter(prefix="/api/v1", tags=["governance"])


class StrictDTO(BaseModel):
    model_config=ConfigDict(extra="forbid")

class CreateOrgMemberRequest(StrictDTO):
    user_id: str
    role_code: str


class ApproveOrgMemberRequest(StrictDTO):
    pass


class CreateAcademicAssignmentRequest(StrictDTO):
    institution_id: str
    placement_id: str
    supervision_id: str
    supervisor_id: str


class UpdateAcademicAssignmentRequest(StrictDTO):
    status: str | None = None
    evaluation_note: str | None = None


class ModerationActionRequest(StrictDTO):
    target_entity_type: str
    target_entity_id: str
    action_type: str
    policy_code: str
    reason_code: str
    justification: str


@router.get("/organizations/{org}/memberships")
def api_073_list_org_memberships(org: str, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    """Canonical API-073 (`GET /api/v1/organizations/{org}/memberships`): List organization memberships."""
    require_org(actor,org,'OWNER')
    from app.db.storage import table,transaction
    from sqlalchemy import select
    with transaction() as conn:
        items=[dict(r) for r in conn.execute(select(table('org_memberships')).where(table('org_memberships').c.organization_id==org)).mappings()]
    return {"contract_id": "API-073", "organization_id": org, "items": items}


@router.post("/organizations/{org_id}/members", status_code=201)
def create_org_member_endpoint(org_id: str, payload: CreateOrgMemberRequest, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    require_mfa(actor)
    require_org(actor,org_id,'OWNER')
    return governance_service.create_org_member_request(
        organization_id=org_id,
        user_id=payload.user_id,
        role_code=payload.role_code,
        actor=actor,
    )


@router.post("/organizations/{org_id}/members/{member_id}/approve")
def approve_org_member_endpoint(
    org_id: str,
    member_id: str,
    payload: ApproveOrgMemberRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    require_mfa(actor)
    require_org(actor,org_id,'OWNER')
    try:
        return governance_service.approve_org_member(
            organization_id=org_id,
            member_id=member_id,
            actor=actor,
            approver_org_id=org_id,
        )
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/internships/academic-assignments", status_code=201)
def create_academic_assignment_endpoint(
    payload: CreateAcademicAssignmentRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Create academic assignment requiring server-authenticated `ActorContext` (`R-01`, `AC-041`)."""
    return internship_log_service.create_academic_assignment(placement_id=payload.placement_id,institution_id=payload.institution_id,
        supervisor_id=payload.supervisor_id,supervision_id=payload.supervision_id,actor_user_id=actor.user_id)


@router.patch("/internships/academic-assignments/{assignment_id}")
def update_academic_assignment_endpoint(
    assignment_id: str,
    payload: UpdateAcademicAssignmentRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Update academic assignment requiring server-authenticated `ActorContext` (`R-01`, `AC-041`)."""
    with transaction() as conn:
        assignment=get_row(conn,'academic_assignments',assignment_id,True)
        require_institution(actor,assignment['institution_id'],'COORDINATOR')
        if payload.status!='REVOKED' or payload.evaluation_note is not None:
            raise HTTPException(422,detail={'code':'ONLY_REVOCATION_SUPPORTED_USE_SEPARATE_REVIEWS'})
        conn.execute(table('academic_assignments').update().where(table('academic_assignments').c.id==assignment_id).values(revoked_at=now(),updated_at=now()))
        return {**assignment,'revoked_at':now()}


@router.post("/moderation/actions", status_code=201)
def create_moderation_action_endpoint(payload: ModerationActionRequest, actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    require_platform(actor,'MODERATOR')
    try:
        return governance_service.record_moderation_action(
            actor_id=actor.user_id,
            target_entity_type=payload.target_entity_type,
            target_entity_id=payload.target_entity_id,
            action_type=payload.action_type,
            policy_code=payload.policy_code,
            reason_code=payload.reason_code,
            justification=payload.justification,
        )
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
