"""Existing institutional role labels/scope must honor the linked appointment."""
from datetime import date,datetime,timedelta,timezone
from uuid import uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import require_institution,ActorContext
from app.db.storage import table,transaction,now
from app.services.placements import insert_row
from test_candidate import cv_fixture
from test_organizations import mfa_user


def setup_scope(identities,role='COORDINATOR'):
    user=mfa_user(identities);other=identities();file=cv_fixture(user)
    with transaction() as conn:
        def institution(label):
            row=dict(id=str(uuid4()),created_at=now(),updated_at=now(),registry_code=str(uuid4()),name=label,region='Tashkent',status='VERIFIED')
            conn.execute(table('institutions').insert().values(**row))
            return row
        inst=institution('Scope Test Institution');foreign=institution('Other Scope Institution')
        member=insert_row(conn,'institution_memberships',institution_id=inst['id'],user_id=user['user_id'],status='ACTIVE',accepted_at=now())
        appointment=insert_row(conn,'institution_appointments',institution_id=inst['id'],user_id=user['user_id'],document_file_id=file['id'],
            status='ACTIVE',valid_from=date.today()-timedelta(days=30),valid_to=date.today()+timedelta(days=30),accepted_at=now())
        roles=table('role_catalog')
        rid=conn.execute(select(roles.c.id).where(roles.c.code==role,roles.c.scope_kind=='INSTITUTION')).scalar_one_or_none()
        if not rid:rid=insert_row(conn,'role_catalog',code=role,scope_kind='INSTITUTION',description='Trusted institution staff fixture')['id']
        grant=insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=rid,appointment_id=appointment['id'])
    return user,other,inst,foreign,member,appointment,grant


@pytest.mark.parametrize('role',['COORDINATOR','TEACHER'])
@pytest.mark.parametrize('state',['expired','future','revoked','unaccepted','membership_unaccepted',
    'grant_revoked','membership_revoked','institution_unverified','future_acceptance','future_membership_acceptance'])
def test_invalid_linked_appointment_cannot_supply_role_label_or_scope(client,identities,state,role):
    user,other,inst,foreign,member,appointment,grant=setup_scope(identities,role)
    expected=role
    with transaction() as conn:
        appts,members=table('institution_appointments'),table('institution_memberships')
        changes={
            'expired':{'valid_to':date.today()-timedelta(days=1)},
            'future':{'valid_from':date.today()+timedelta(days=1)},
            'revoked':{'status':'REVOKED'},'unaccepted':{'accepted_at':None},
            'future_acceptance':{'accepted_at':now()+timedelta(days=1)}}
        if state in changes:conn.execute(appts.update().where(appts.c.id==appointment['id']).values(**changes[state]))
        elif state=='membership_unaccepted':conn.execute(members.update().where(members.c.id==member['id']).values(accepted_at=None))
        elif state=='future_membership_acceptance':conn.execute(members.update().where(members.c.id==member['id']).values(accepted_at=now()+timedelta(days=1)))
        elif state=='membership_revoked':conn.execute(members.update().where(members.c.id==member['id']).values(revoked_at=now()))
        elif state=='grant_revoked':
            t=table('institution_role_grants');conn.execute(t.update().where(t.c.id==grant['id']).values(revoked_at=now()))
        elif state=='institution_unverified':
            t=table('institutions');conn.execute(t.update().where(t.c.id==inst['id']).values(status='PENDING'))
        else:raise AssertionError('Unhandled invalid scope state')
    response=client.get('/api/v1/auth/me',headers=user['headers']);assert response.status_code==200,response.text
    permitted=True
    try:require_institution(ActorContext(user['user_id'],user['session_id'],()),inst['id'],role)
    except HTTPException as exc:
        assert exc.status_code==403
        permitted=False
    assert expected not in response.json()['roles'] and not permitted,(state,response.json()['roles'],permitted)


@pytest.mark.parametrize('role',['COORDINATOR','TEACHER'])
@pytest.mark.parametrize('state',['wrong_user','wrong_institution','wrong_role_scope'])
def test_new_structural_corruption_is_rejected_without_changing_valid_authority(client,identities,role,state):
    user,other,inst,foreign,member,appointment,grant=setup_scope(identities,role)
    # Since0011, these new writes fail in PostgreSQL before an invalid link exists.
    # Preserved malformed0010 history is separately tested by the populated upgrade.
    with transaction() as conn:
        roles=table('role_catalog')
        rid=conn.execute(select(roles.c.id).where(roles.c.code=='FINANCE',roles.c.scope_kind=='PLATFORM')).scalar_one_or_none()
        if not rid:rid=insert_row(conn,'role_catalog',code='FINANCE',scope_kind='PLATFORM',description='Finance fixture')['id']
    with pytest.raises(IntegrityError) as exc,transaction() as conn:
        if state=='wrong_role_scope':
            grants=table('institution_role_grants');conn.execute(grants.update().where(grants.c.id==grant['id']).values(role_id=rid))
        else:
            values={'user_id':other['user_id']} if state=='wrong_user' else {'institution_id':foreign['id']}
            appts=table('institution_appointments');conn.execute(appts.update().where(appts.c.id==appointment['id']).values(**values))
    assert exc.value.orig.sqlstate=='23514'
    response=client.get('/api/v1/auth/me',headers=user['headers']);assert response.status_code==200,response.text
    assert role in response.json()['roles'] and 'FINANCE' not in response.json()['roles']
    require_institution(ActorContext(user['user_id'],user['session_id'],()),inst['id'],role)


def test_current_accepted_linked_appointment_is_a_valid_control(client,identities):
    user,_,inst,_,_,_,_=setup_scope(identities)
    response=client.get('/api/v1/auth/me',headers=user['headers']);assert response.status_code==200,response.text
    assert 'COORDINATOR' in response.json()['roles']
    require_institution(ActorContext(user['user_id'],user['session_id'],()),inst['id'],'COORDINATOR')


@pytest.mark.parametrize('utc_hour,valid_offset,allowed',[(18,0,True),(19,0,False),(19,1,True),(18,1,False)])
def test_appointment_dates_use_tashkent_midnight_inclusive(identities,monkeypatch,utc_hour,valid_offset,allowed):
    from app.db import institution_scope
    user,_,inst,_,member,appointment,_=setup_scope(identities)
    fixed=datetime(2026,11,9,utc_hour,30,tzinfo=timezone.utc);valid_day=fixed.date()+timedelta(days=valid_offset)
    with transaction() as conn:
        conn.execute(table('institution_memberships').update().where(table('institution_memberships').c.id==member['id']).values(accepted_at=fixed-timedelta(days=10)))
        conn.execute(table('institution_appointments').update().where(table('institution_appointments').c.id==appointment['id']).values(
            accepted_at=fixed-timedelta(days=10),valid_from=valid_day,valid_to=valid_day))
    monkeypatch.setattr(institution_scope,'now',lambda:fixed)
    if allowed:require_institution(ActorContext(user['user_id'],user['session_id'],()),inst['id'],'COORDINATOR')
    else:
        with pytest.raises(HTTPException) as exc:require_institution(ActorContext(user['user_id'],user['session_id'],()),inst['id'],'COORDINATOR')
        assert exc.value.status_code==403
