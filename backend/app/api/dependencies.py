"""Server-side ActorContext and authentication dependencies (TD-001 Section 3 & 5, FIX-03, FIX-04, R-01, REV-002)."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import Header, HTTPException
from sqlalchemy import select
from app.db.storage import table, transaction, now

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


def optional_actor_context(authorization: str | None = Header(default=None)) -> ActorContext | None:
    """Optionally resolve `ActorContext` from `Authorization: Bearer <token>`; returns None for guests."""
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_REQUIRED",
                "message": "Authorization sarlavhasi 'Bearer <token>' formatida bo'lishi kerak",
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

def require_platform(actor: ActorContext, *allowed: str) -> None:
    grants,catalog=table('platform_role_grants'),table('role_catalog')
    with transaction() as conn:
        found=conn.execute(select(grants.c.id).select_from(grants.join(catalog,grants.c.role_id==catalog.c.id)).where(
            grants.c.user_id==actor.user_id,grants.c.revoked_at.is_(None),grants.c.expires_at>now(),
            catalog.c.scope_kind=='PLATFORM',catalog.c.code.in_(allowed))).first()
    if not found:
        raise HTTPException(403,detail={'code':'FORBIDDEN_ROLE'})

def require_org(actor: ActorContext, organization_id: str, *allowed: str) -> None:
    membership,grants,catalog=table('org_memberships'),table('org_role_grants'),table('role_catalog')
    with transaction() as conn:
        found=conn.execute(select(membership.c.id).select_from(membership.join(grants,grants.c.membership_id==membership.c.id)
            .join(catalog,grants.c.role_id==catalog.c.id)).where(membership.c.user_id==actor.user_id,
            membership.c.organization_id==organization_id,membership.c.status=='ACTIVE',membership.c.revoked_at.is_(None),
            grants.c.revoked_at.is_(None),catalog.c.scope_kind=='ORG',catalog.c.code.in_(allowed))).first()
    if not found:
        raise HTTPException(403,detail={'code':'ORG_SCOPE_FORBIDDEN'})

def candidate_id_for(actor: ActorContext) -> str:
    with transaction() as conn:
        result=conn.execute(select(table('candidate_profiles').c.id).where(table('candidate_profiles').c.user_id==actor.user_id)).scalar_one_or_none()
    if not result:
        raise HTTPException(403,detail={'code':'CANDIDATE_PROFILE_REQUIRED'})
    return str(result)

def owns_candidate(user_id: str,candidate_id: str) -> bool:
    with transaction() as conn:
        return conn.execute(select(table('candidate_profiles').c.id).where(table('candidate_profiles').c.id==candidate_id,
            table('candidate_profiles').c.user_id==user_id)).first() is not None

def require_institution(actor: ActorContext, institution_id: str, *allowed: str) -> None:
    from app.db.institution_scope import institution_scope_query
    with transaction() as conn:
        found=conn.execute(institution_scope_query(actor.user_id,institution_id,allowed)).first()
    if not found: raise HTTPException(403,detail={'code':'INSTITUTION_SCOPE_FORBIDDEN'})
