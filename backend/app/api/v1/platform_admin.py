"""Super Admin, Staff Role Grants, Operator Directories, Feature Flags Read & Governance Queues API (API-126..API-135)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from app.api.dependencies import ActorContext, require_actor_context, require_platform
from app.services.organizations import require_mfa
from app.services.platform_admin import PlatformAdminError, platform_admin_service

router = APIRouter(prefix="/api/v1/operator", tags=["platform-admin"])


class StaffGrantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    role_code: StrictStr = Field(min_length=2, max_length=64)
    reason: StrictStr = Field(min_length=10, max_length=1000)
    duration_days: StrictInt = Field(default=3650, ge=1, le=3650)


class StaffGrantRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: StrictStr = Field(min_length=10, max_length=1000)


class RecoveryDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: StrictStr = Field(pattern="^(APPROVE|REJECT)$")
    reason: StrictStr = Field(min_length=15, max_length=2000)


def _http_error(exc: PlatformAdminError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/staff-grants")
def api_126_list_staff_grants(
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-126: List platform role catalog, active/revoked staff grants, and authoritative role matrix."""
    require_platform(actor, "ADMIN", "SECURITY_LEAD")
    try:
        return platform_admin_service.list_staff_grants(actor=actor)
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc


@router.post("/staff-grants", status_code=201)
def api_127_create_staff_grant(
    payload: StaffGrantCreateRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-127: Grant a standing platform role (ADMIN + MFA required; self-grant forbidden)."""
    require_platform(actor, "ADMIN")
    require_mfa(actor)
    try:
        return platform_admin_service.grant_staff_role(
            actor=actor,
            user_id=str(payload.user_id),
            role_code=payload.role_code,
            reason=payload.reason,
            duration_days=payload.duration_days,
        )
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc


@router.post("/staff-grants/{grant_id}/revoke")
def api_128_revoke_staff_grant(
    grant_id: UUID,
    payload: StaffGrantRevokeRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-128: Revoke a platform role grant (ADMIN + MFA; protects self-admin and last active ADMIN)."""
    require_platform(actor, "ADMIN")
    require_mfa(actor)
    try:
        return platform_admin_service.revoke_staff_grant(
            actor=actor,
            grant_id=str(grant_id),
            reason=payload.reason,
        )
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc


@router.get("/directory/users")
def api_129_directory_users(
    q: str | None = Query(default=None, max_length=120),
    role: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=40, ge=1, le=100),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-129: Search operator user directory with masked contacts only."""
    require_platform(actor, "ADMIN", "SECURITY_LEAD", "OPERATIONS", "AUDITOR")
    try:
        return platform_admin_service.directory_users(actor=actor, q=q, role=role, limit=limit)
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc


@router.get("/directory/organizations")
def api_130_directory_organizations(
    q: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=40, ge=1, le=100),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-130: Search organization directory with verification status and batched activity counts."""
    require_platform(actor, "ADMIN", "OPERATIONS", "MODERATOR", "AUDITOR")
    try:
        return platform_admin_service.directory_organizations(actor=actor, q=q, status=status, limit=limit)
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc


@router.get("/directory/institutions")
def api_131_directory_institutions(
    q: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=40, ge=1, le=100),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-131: Search institution directory with verified students and active staff counts."""
    require_platform(actor, "ADMIN", "OPERATIONS", "MODERATOR", "AUDITOR")
    try:
        return platform_admin_service.directory_institutions(actor=actor, q=q, status=status, limit=limit)
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc


@router.get("/feature-flags")
def api_132_list_feature_flags(
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-132: List global feature flags with proof-backed effective state and PATCH If-Match versions."""
    require_platform(actor, "ADMIN", "AUDITOR", "OPERATIONS")
    try:
        return platform_admin_service.list_feature_flags(actor=actor)
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc


@router.get("/privacy-requests")
def api_133_list_privacy_requests(
    status: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=100),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-133: List GDPR privacy requests for compliance/support/admin queue."""
    require_platform(actor, "ADMIN", "COMPLIANCE", "SUPPORT", "MODERATOR")
    try:
        return platform_admin_service.list_privacy_requests(actor=actor, status=status, limit=limit)
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc


@router.get("/recovery-requests")
def api_134_list_recovery_requests(
    status: str | None = Query(default="PENDING_REVIEW", max_length=40),
    limit: int = Query(default=50, ge=1, le=100),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-134: List account recovery requests excluding actor's own requests (ADMIN/SUPPORT + MFA)."""
    require_platform(actor, "ADMIN", "SUPPORT")
    require_mfa(actor)
    try:
        return platform_admin_service.list_recovery_requests(actor=actor, status=status, limit=limit)
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc


@router.post("/recovery-requests/{request_id}/decide")
def api_135_decide_recovery_request(
    request_id: UUID,
    payload: RecoveryDecisionRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """API-135: Approve or reject account recovery request (ADMIN/SUPPORT + MFA; forbids self-review)."""
    require_platform(actor, "ADMIN", "SUPPORT")
    require_mfa(actor)
    try:
        return platform_admin_service.decide_recovery_request(
            actor=actor,
            request_id=str(request_id),
            decision=payload.decision,
            reason=payload.reason,
        )
    except PlatformAdminError as exc:
        raise _http_error(exc) from exc
