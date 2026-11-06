"""FastAPI router for Authentication, Sessions, and Immediate Revoke (`S2.2.1`, `AC-017`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.auth import AuthError, auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    display_name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=8)
    adult_confirmed: bool
    roles: list[str] = Field(default_factory=lambda: ["CANDIDATE"])
    enable_totp: bool = False


class LoginRequest(BaseModel):
    user_id: str
    password: str
    totp_code: str | None = None


class RevokeRequest(BaseModel):
    actor_id: str
    reason: str = "SECURITY_REVOKE"


@router.post("/register", status_code=201)
def register_endpoint(payload: RegisterRequest) -> dict[str, Any]:
    try:
        user = auth_service.register_user(
            display_name=payload.display_name,
            password=payload.password,
            adult_confirmed=payload.adult_confirmed,
            roles=payload.roles,
            enable_totp=payload.enable_totp,
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


@router.post("/login")
def login_endpoint(payload: LoginRequest) -> dict[str, Any]:
    try:
        return auth_service.login(
            user_id=payload.user_id,
            password=payload.password,
            totp_code=payload.totp_code,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/sessions/{session_id}/revoke")
def revoke_session_endpoint(session_id: str, payload: RevokeRequest) -> dict[str, Any]:
    try:
        return auth_service.revoke_session(
            session_id=session_id,
            actor_id=payload.actor_id,
            reason=payload.reason,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("/me")
def me_endpoint(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "MISSING_BEARER_TOKEN", "message": "Token talab qilinadi"})
    session_id = authorization.removeprefix("Bearer ").strip()
    try:
        return auth_service.validate_session(session_id)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
