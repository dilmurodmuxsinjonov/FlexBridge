"""Transaction-bound authority; callers acquire business locks before these guards."""
from sqlalchemy import select
from app.db.storage import table,now
from app.services.governance import GovernanceError


def session_authority(conn,actor,*,require_mfa=False):
    users,sessions=(table(n) for n in ('users','sessions'))
    # Match password/recovery mutations: user before sessions.
    user=conn.execute(select(users.c.auth_version).where(users.c.id==actor.user_id,users.c.status=='ACTIVE')
        .with_for_update(read=True)).first()
    if not user:raise GovernanceError('MFA_REQUIRED' if require_mfa else 'AUTH_REVOKED',status_code=403 if require_mfa else 401)
    query=select(sessions.c.id).where(sessions.c.id==actor.session_id,
        sessions.c.user_id==actor.user_id,sessions.c.auth_version==user.auth_version,
        sessions.c.revoked_at.is_(None),sessions.c.expires_at>now())
    if require_mfa:query=query.where(sessions.c.assurance=='MFA')
    session=conn.execute(query.with_for_update(read=True)).first()
    if not session:raise GovernanceError('MFA_REQUIRED' if require_mfa else 'AUTH_REVOKED',status_code=403 if require_mfa else 401)


def mfa_authority(conn,actor):
    session_authority(conn,actor,require_mfa=True)


def platform_authority(conn,actor,*allowed):
    mfa_authority(conn,actor)
    grants,roles=(table(n) for n in ('platform_role_grants','role_catalog'))
    grant=conn.execute(select(grants.c.id).join(roles,roles.c.id==grants.c.role_id).where(
        grants.c.user_id==actor.user_id,grants.c.revoked_at.is_(None),grants.c.expires_at>now(),
        roles.c.code.in_(allowed),roles.c.scope_kind=='PLATFORM').with_for_update(read=True,of=(grants,roles))).first()
    if not grant:raise GovernanceError('FORBIDDEN_ROLE',status_code=403)


def moderator_authority(conn,actor):
    platform_authority(conn,actor,'MODERATOR')


def org_authority(conn,user_id,org_id,*allowed,nowait=False):
    users,members,grants,roles=(table(n) for n in ('users','org_memberships','org_role_grants','role_catalog'))
    row=conn.execute(select(members,grants.c.id.label('_authority_grant_id')).join(users,users.c.id==members.c.user_id)
        .join(grants,grants.c.membership_id==members.c.id).join(roles,roles.c.id==grants.c.role_id).where(
            users.c.status=='ACTIVE',members.c.user_id==user_id,members.c.organization_id==org_id,
            members.c.status=='ACTIVE',members.c.revoked_at.is_(None),grants.c.revoked_at.is_(None),
            roles.c.scope_kind=='ORG',roles.c.code.in_(allowed))
        .with_for_update(read=True,of=(users,members,grants,roles),nowait=nowait)).mappings().first()
    if not row:raise GovernanceError('ORG_SCOPE_FORBIDDEN',status_code=403)
    return dict(row)


def institution_role_authority(conn,user_id,institution_id,*allowed,nowait=False):
    from app.db.institution_scope import institution_scope_query
    from sqlalchemy.exc import OperationalError
    try:row=conn.execute(institution_scope_query(user_id,institution_id,allowed,lock=True,nowait=nowait)).mappings().first()
    except OperationalError as exc:
        if nowait and getattr(exc.orig,'sqlstate',None)=='55P03':
            raise GovernanceError('INSTITUTION_AUTHORITY_BUSY_RETRY',status_code=409) from exc
        raise
    if not row:raise GovernanceError('INSTITUTION_SCOPE_FORBIDDEN',status_code=403)
    return dict(row)


def institution_authority(conn,actor,institution_id,*allowed,require_mfa=False):
    session_authority(conn,actor,require_mfa=require_mfa)
    row=institution_role_authority(conn,actor.user_id,institution_id,*allowed)
    if row['_authority_role']=='COORDINATOR' and not require_mfa:mfa_authority(conn,actor)
    return row
