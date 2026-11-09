"""Effective institutional grants, shared by labels, scoped checks and write guards."""
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.db.storage import table,now

INSTITUTION_ROLES=('COORDINATOR','TEACHER')
TASHKENT=ZoneInfo('Asia/Tashkent')


def institution_scope_query(user_id,institution_id=None,allowed=None,*,lock=False,nowait=False):
    users,insts,members,grants,roles,appointments=(table(name) for name in (
        'users','institutions','institution_memberships','institution_role_grants','role_catalog','institution_appointments'))
    instant=now();day=instant.astimezone(TASHKENT).date()
    query=select(members,grants.c.id.label('_authority_grant_id'),roles.c.code.label('_authority_role'),
        appointments.c.id.label('_authority_appointment_id')).select_from(
        members.join(users,users.c.id==members.c.user_id).join(insts,insts.c.id==members.c.institution_id)
        .join(grants,grants.c.membership_id==members.c.id).join(roles,roles.c.id==grants.c.role_id)
        .join(appointments,(appointments.c.id==grants.c.appointment_id)&
            (appointments.c.user_id==members.c.user_id)&(appointments.c.institution_id==members.c.institution_id))).where(
        users.c.status=='ACTIVE',insts.c.status=='VERIFIED',members.c.user_id==user_id,
        members.c.status=='ACTIVE',members.c.revoked_at.is_(None),members.c.accepted_at.is_not(None),members.c.accepted_at<=instant,
        grants.c.revoked_at.is_(None),roles.c.scope_kind=='INSTITUTION',roles.c.code.in_(INSTITUTION_ROLES),
        appointments.c.status=='ACTIVE',appointments.c.accepted_at.is_not(None),appointments.c.accepted_at<=instant,
        appointments.c.valid_from<=day,(appointments.c.valid_to.is_(None)|(appointments.c.valid_to>=day)))
    if institution_id is not None:query=query.where(members.c.institution_id==institution_id)
    if allowed is not None:query=query.where(roles.c.code.in_(allowed))
    if lock:query=query.with_for_update(read=True,of=(users,insts,members,grants,roles,appointments),nowait=nowait)
    return query
