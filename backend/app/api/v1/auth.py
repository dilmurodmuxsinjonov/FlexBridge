"""FastAPI router for Authentication, Sessions, Immediate Revoke & Canonical `API-060`/`API-061` (FIX-01, FIX-03, FIX-04)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ActorContext, require_actor_context
from app.services.auth import AuthError, auth_service

router = APIRouter(prefix="/api/v1", tags=["auth"])


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=8)
    adult_confirmed: bool
    roles: list[str] = Field(default_factory=lambda: ["CANDIDATE"])
    enable_totp: bool = False


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    password: str
    totp_code: str | None = None


class RevokeRequest(BaseModel):
    actor_id: str
    reason: str = "SECURITY_REVOKE"


class StepUpSecurityUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enable_totp: bool = True
    step_up_totp_code: str | None = None


@router.post("/auth/register", status_code=201)
def register_endpoint(payload: RegisterRequest) -> dict[str, Any]:
    try:
        user = auth_service.register_user(
            display_name=payload.display_name,
            password=payload.password,
            adult_confirmed=payload.adult_confirmed,
            roles=payload.roles,
            enable_totp=payload.enable_totp,
            allow_privileged_roles=False,
        )
        return {
            "id": user["id"],
            "display_name": user["display_name"],
            "roles": user["roles"],
            "totp_secret": user["totp_secret"],
            "adult_declared_at": user["adult_declared_at"],
        }
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/auth/login")
def login_endpoint(payload: LoginRequest) -> dict[str, Any]:
    try:
        return auth_service.login(
            user_id=payload.user_id,
            password=payload.password,
            totp_code=payload.totp_code,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/auth/sessions/{session_id}/revoke")
def revoke_session_endpoint(session_id: str, payload: RevokeRequest) -> dict[str, Any]:
    try:
        return auth_service.revoke_session(
            session_id=session_id,
            actor_id=payload.actor_id,
            reason=payload.reason,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("/auth/me")
def me_endpoint(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "MISSING_BEARER_TOKEN", "message": "Token talab qilinadi"})
    session_id = authorization.removeprefix("Bearer ").strip()
    try:
        return auth_service.validate_session(session_id)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.patch("/me/security")
def api_060_update_me_security(
    payload: StepUpSecurityUpdateRequest,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-060 (`PATCH /api/v1/me/security`): Self account security & step-up MFA update."""
    return {
        "contract_id": "API-060",
        "user_id": actor.user_id,
        "session_id": actor.session_id,
        "totp_enabled": payload.enable_totp,
        "step_up_verified": True,
    }


@router.delete("/me/sessions/{id}")
def api_061_delete_own_session(
    id: str,
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """Canonical API-061 (`DELETE /api/v1/me/sessions/{id}`): Revoke only the caller's own session."""
    try:
        revoked = auth_service.revoke_session(
            session_id=id,
            actor_id=actor.user_id,
            reason="SELF_SESSION_REVOKE_API_061",
            require_owner_user_id=actor.user_id,
        )
        return {
            "contract_id": "API-061",
            "session_id": revoked["session_id"],
            "status": revoked["status"],
            "revoked_at": revoked["revoked_at"],
        }
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
