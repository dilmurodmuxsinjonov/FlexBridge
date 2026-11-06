"""FastAPI router for Organization Dual-Control (`INV-11`), Canonical `API-073`, Academic Assignments, and Moderation (`AC-041`).

Enforces server-side `ActorContext` (`Authorization: Bearer <token>`) on academic assignment endpoints (`R-01`).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import ActorContext, require_actor_context
from app.services.governance import GovernanceError, governance_service

router = APIRouter(prefix="/api/v1", tags=["governance"])


class CreateOrgMemberRequest(BaseModel):
    user_id: str
    role_code: str
    created_by: str


class ApproveOrgMemberRequest(BaseModel):
    approved_by: str
    approver_org_id: str


class CreateAcademicAssignmentRequest(BaseModel):
    actor_id: str | None = None
    actor_role: str | None = None
    actor_institution_id: str | None = None
    institution_id: str
    placement_id: str
    supervision_id: str
    supervisor_id: str


class UpdateAcademicAssignmentRequest(BaseModel):
    actor_id: str | None = None
    actor_role: str | None = None
    actor_institution_id: str | None = None
    status: str | None = None
    evaluation_note: str | None = None


class ModerationActionRequest(BaseModel):
    actor_id: str
    target_entity_type: str
    target_entity_id: str
    action_type: str
    policy_code: str
    reason_code: str
    justification: str


@router.get("/organizations/{org}/memberships")
def api_073_list_org_memberships(org: str) -> dict[str, Any]:
    """Canonical API-073 (`GET /api/v1/organizations/{org}/memberships`): List organization memberships."""
    items = [m for m in governance_service.org_members.values() if m["organization_id"] == org]
    return {"contract_id": "API-073", "organization_id": org, "items": items}


@router.post("/organizations/{org_id}/members", status_code=201)
def create_org_member_endpoint(org_id: str, payload: CreateOrgMemberRequest) -> dict[str, Any]:
    return governance_service.create_org_member_request(
        organization_id=org_id,
        user_id=payload.user_id,
        role_code=payload.role_code,
        created_by=payload.created_by,
    )


@router.post("/organizations/{org_id}/members/{member_id}/approve")
def approve_org_member_endpoint(
    org_id: str,
    member_id: str,
    payload: ApproveOrgMemberRequest,
) -> dict[str, Any]:
    try:
        return governance_service.approve_org_member(
            organization_id=org_id,
            member_id=member_id,
            approved_by=payload.approved_by,
            approver_org_id=payload.approver_org_id,
        )
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/internships/academic-assignments", status_code=201)
def create_academic_assignment_endpoint(
    payload: CreateAcademicAssignmentRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Create academic assignment requiring server-authenticated `ActorContext` (`R-01`, `AC-041`)."""
    effective_role = actor.roles[0] if actor.roles else "CANDIDATE"
    try:
        return governance_service.create_academic_assignment_api_060(
            actor_id=actor.user_id,
            actor_role=effective_role,
            actor_institution_id=payload.actor_institution_id,
            institution_id=payload.institution_id,
            placement_id=payload.placement_id,
            supervision_id=payload.supervision_id,
            supervisor_id=payload.supervisor_id,
        )
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.patch("/internships/academic-assignments/{assignment_id}")
def update_academic_assignment_endpoint(
    assignment_id: str,
    payload: UpdateAcademicAssignmentRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Update academic assignment requiring server-authenticated `ActorContext` (`R-01`, `AC-041`)."""
    effective_role = actor.roles[0] if actor.roles else "CANDIDATE"
    try:
        return governance_service.update_academic_assignment_api_061(
            assignment_id=assignment_id,
            actor_id=actor.user_id,
            actor_role=effective_role,
            actor_institution_id=payload.actor_institution_id,
            status=payload.status,
            evaluation_note=payload.evaluation_note,
        )
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/moderation/actions", status_code=201)
def create_moderation_action_endpoint(payload: ModerationActionRequest) -> dict[str, Any]:
    try:
        return governance_service.record_moderation_action(
            actor_id=payload.actor_id,
            target_entity_type=payload.target_entity_type,
            target_entity_id=payload.target_entity_id,
            action_type=payload.action_type,
            policy_code=payload.policy_code,
            reason_code=payload.reason_code,
            justification=payload.justification,
        )
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
