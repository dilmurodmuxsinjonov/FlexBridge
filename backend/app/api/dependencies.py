"""Server-side ActorContext and authentication dependencies (TD-001 Section 3 & 5, FIX-03, FIX-04, R-01)."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import Header, HTTPException

from app.services.auth import AuthError, auth_service


@dataclass(frozen=True)
class ActorContext:
    """Authenticated actor resolved strictly from server-side session token (`DB-004 sessions`)."""

    user_id: str
    session_id: str
    roles: tuple[str, ...]

    def has_any_role(self, *allowed_roles: str) -> bool:
        return any(r in self.roles for r in allowed_roles)


def require_actor_context(authorization: str | None = Header(default=None)) -> ActorContext:
    """Resolve and validate the current `ActorContext` from `Authorization: Bearer <token>`."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_REQUIRED",
                "message": "Himoyalangan amal uchun Authorization: Bearer <token> sarlavhasi majburiy (R-01)",
            },
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        sess = auth_service.validate_session(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    return ActorContext(
        user_id=str(sess["user_id"]),
        session_id=str(sess["session_id"]),
        roles=tuple(sess.get("roles", [])),
    )
