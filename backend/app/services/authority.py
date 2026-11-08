"""Transaction-bound authority; callers acquire business locks before these guards."""
from sqlalchemy import select
from app.db.storage import table,now
from app.services.governance import GovernanceError


def mfa_authority(conn,actor):
    users,sessions=(table(n) for n in ('users','sessions'))
    # Match password/recovery mutations: user before sessions.
    user=conn.execute(select(users.c.auth_version).where(users.c.id==actor.user_id,users.c.status=='ACTIVE')
        .with_for_update(read=True)).first()
    session=None if not user else conn.execute(select(sessions.c.id).where(sessions.c.id==actor.session_id,
        sessions.c.user_id==actor.user_id,sessions.c.auth_version==user.auth_version,sessions.c.assurance=='MFA',
        sessions.c.revoked_at.is_(None),sessions.c.expires_at>now()).with_for_update(read=True)).first()
    if not session:raise GovernanceError('MFA_REQUIRED',status_code=403)


def platform_authority(conn,actor,*allowed):
    mfa_authority(conn,actor)
    grants,roles=(table(n) for n in ('platform_role_grants','role_catalog'))
    grant=conn.execute(select(grants.c.id).join(roles,roles.c.id==grants.c.role_id).where(
        grants.c.user_id==actor.user_id,grants.c.revoked_at.is_(None),grants.c.expires_at>now(),
        roles.c.code.in_(allowed),roles.c.scope_kind=='PLATFORM').with_for_update(read=True,of=(grants,roles))).first()
    if not grant:raise GovernanceError('FORBIDDEN_ROLE',status_code=403)


def moderator_authority(conn,actor):
    platform_authority(conn,actor,'MODERATOR')


def org_authority(conn,user_id,org_id,*allowed):
    users,members,grants,roles=(table(n) for n in ('users','org_memberships','org_role_grants','role_catalog'))
    row=conn.execute(select(members,grants.c.id.label('_authority_grant_id')).join(users,users.c.id==members.c.user_id)
        .join(grants,grants.c.membership_id==members.c.id).join(roles,roles.c.id==grants.c.role_id).where(
            users.c.status=='ACTIVE',members.c.user_id==user_id,members.c.organization_id==org_id,
            members.c.status=='ACTIVE',members.c.revoked_at.is_(None),grants.c.revoked_at.is_(None),
            roles.c.scope_kind=='ORG',roles.c.code.in_(allowed))
        .with_for_update(read=True,of=(users,members,grants,roles))).mappings().first()
    if not row:raise GovernanceError('ORG_SCOPE_FORBIDDEN',status_code=403)
    return dict(row)
