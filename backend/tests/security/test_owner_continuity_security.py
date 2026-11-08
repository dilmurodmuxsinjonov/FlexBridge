"""Current role/contact/roster proof, distinct reviewers and private continuity boundaries."""
from datetime import timedelta
import time
from uuid import uuid4
import pytest
from sqlalchemy import select,func,text
from app.db.storage import table,transaction,now
from app.services.placements import insert_row
from app.services.organizations import role_id
from test_owner_continuity import setup_continuity,submit,claim,decide,ready,recommended,path,NOTE
from test_owner_additions import member_id,has_owner
from test_candidate import cv_fixture
from test_invitations import contact

def platform_grant(user,role,by):
    with transaction() as conn:
        rid=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code==role,
            table('role_catalog').c.scope_kind=='PLATFORM')).scalar_one()
        return insert_row(conn,'platform_role_grants',user_id=user['user_id'],role_id=rid,granted_by_id=by['user_id'],expires_at=now()+timedelta(days=1))

@pytest.mark.parametrize('extra',[{'applicant_id':str(uuid4())},{'membership_id':str(uuid4())},
    {'role':'OWNER'},{'approved':True},{'owner_roster':[]},{'auth_version':1}])
def test_client_cannot_choose_target_or_authority(client,setup_continuity,extra):
    response=submit(client,setup_continuity,**extra);assert response.status_code==422,response.text

def test_every_continuity_route_requires_authenticated_session(client):
    uid=str(uuid4());base='/api/v1/operator/owner-continuity/moderator/cases'
    calls=[('POST','/api/v1/organizations/'+uid+'/owner-continuity'),('GET','/api/v1/organizations/'+uid+'/owner-continuity'),
        ('GET','/api/v1/owner-continuity/'+uid),('POST','/api/v1/owner-continuity/'+uid+'/withdraw'),
        ('POST','/api/v1/organizations/'+uid+'/owner-continuity/'+uid+'/object'),('GET',base),('POST',base+'/'+uid+'/claim'),
        ('GET',base+'/'+uid),('GET',base+'/'+uid+'/evidence/'+uid+'/download'),('POST',base+'/'+uid+'/decide')]
    for method,url in calls:
        response=client.request(method,url,json={} if method=='POST' else None)
        assert response.status_code==401,(method,url,response.status_code)
        assert response.headers['cache-control']=='no-store'

def test_staff_scope_and_current_mfa_are_required(client,setup_continuity,identities):
    flow=setup_continuity;user=identities()
    with transaction() as conn:
        member=insert_row(conn,'org_memberships',organization_id=flow['org'],user_id=user['user_id'],status='ACTIVE')
        insert_row(conn,'org_role_grants',membership_id=member['id'],role_id=role_id(conn,'HR'),granted_by_id=flow['owner']['user_id'])
    changed={**flow,'applicant':user,'member':member['id'],'contact':contact(user,value=str(uuid4())+'@example.test',channel='EMAIL'),'file':cv_fixture(user)}
    response=submit(client,changed);assert response.status_code==403,response.text
    stranger=identities('CANDIDATE')
    response=submit(client,flow,actor=stranger);assert response.status_code==403,response.text
    # A real OWNER also holding HR must not use continuity to add themselves again.
    with transaction() as conn:
        insert_row(conn,'org_role_grants',membership_id=flow['owner_member'],role_id=role_id(conn,'HR'),granted_by_id=flow['owner']['user_id'])
    owner_flow={**flow,'applicant':flow['owner'],'contact':contact(flow['owner'],value=str(uuid4())+'@example.test',channel='EMAIL'),'file':cv_fixture(flow['owner'])}
    response=submit(client,owner_flow);assert response.status_code==409,response.text

def test_verified_contact_belongs_to_applicant_and_reports_hide_proof(client,setup_continuity):
    flow=setup_continuity;foreign=contact(flow['owner'],value=str(uuid4())+'@example.test',channel='EMAIL')
    response=submit(client,flow,contact_id=foreign['id']);assert response.status_code==403,response.text
    unverified=contact(flow['applicant'],value=str(uuid4())+'@example.test',channel='EMAIL',verified=False)
    response=submit(client,flow,contact_id=unverified['id']);assert response.status_code==403,response.text
    response=submit(client,flow);assert response.status_code==202,response.text
    for forbidden in ('auth_version','session_id','staff_grant_id','contact_digest',flow['contact']['normalized_value']):assert forbidden not in response.text
    case=response.json()['id']
    response=client.get('/api/v1/owner-continuity/'+case,headers=flow['owner']['headers']);assert response.status_code==403,response.text

def test_two_roles_on_one_account_cannot_supply_both_reviews(client,setup_continuity):
    flow=setup_continuity;case=recommended(client,flow)
    platform_grant(flow['moderator'],'COMPLIANCE',flow['compliance'])
    response=claim(client,flow,case,'compliance',actor=flow['moderator'])
    assert response.status_code==403 and response.json()['detail']['code']=='CONTINUITY_DISTINCT_REVIEWERS_REQUIRED',response.text
    response=client.get('/api/v1/operator/owner-continuity/compliance/cases?unassigned=true',headers=flow['moderator']['headers'])
    assert response.status_code==200 and response.json()['items']==[],response.text
    assert not has_owner(flow['member'])

def test_participants_with_real_operator_roles_cannot_review(client,setup_continuity):
    flow=setup_continuity;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id']
    for user in (flow['applicant'],flow['owner']):
        platform_grant(user,'MODERATOR',flow['compliance'])
        response=claim(client,flow,case,'moderator',actor=user)
        assert response.status_code==403 and response.json()['detail']['code']=='SELF_REVIEW_FORBIDDEN',response.text

def test_unassigned_private_evidence_and_generic_review_are_rejected(client,setup_continuity,identities,monkeypatch):
    from app.adapters import storage
    flow=setup_continuity;case=ready(client,flow);other=identities('MODERATOR');calls=[]
    monkeypatch.setattr(storage,'presign_get',lambda key:calls.append(key) or 'https://fixture.invalid/private')
    for suffix in ('','/evidence/'+flow['file']['id']+'/download'):
        response=client.get(path(case,'moderator')+suffix,headers=other['headers']);assert response.status_code==403,response.text
    response=decide(client,flow,case,'compliance',actor=other);assert response.status_code==403,response.text
    response=client.post('/api/v1/operator/verification-cases/'+case+'/claim',headers=flow['moderator']['headers']);assert response.status_code==422,response.text
    response=client.post('/api/v1/operator/verification-cases/'+case+'/decide',headers=flow['moderator']['headers'],json={
        'decision':'APPROVE','expected_revision':1,'reason':'Generic moderation is not continuity finalization'})
    assert response.status_code==422,response.text
    assert calls==[] and not has_owner(flow['member'])
    response=client.get(path(case,'moderator')+'/evidence/'+flow['file']['id']+'/download',headers=flow['moderator']['headers'])
    assert response.status_code==200 and len(calls)==1,response.text

@pytest.mark.parametrize('change',[
    'staff_grant','applicant_version','applicant_suspended','membership_revoked','owner_version','new_owner',
    'contact_revoked','contact_recycled','file_deleted','file_scan_error','file_foreign',
    'moderator_grant','moderator_version','compliance_grant','compliance_version'])
def test_stale_pending_intent_or_claim_expires_atomically_without_owner(client,setup_continuity,identities,change):
    flow=setup_continuity;case=ready(client,flow)
    if change=='new_owner':identities('OWNER',flow['org']) # Explicit trusted metadata change; real regrant is tested separately.
    with transaction() as conn:
        if change=='staff_grant':
            conn.execute(table('org_role_grants').update().where(table('org_role_grants').c.membership_id==flow['member']).values(revoked_at=now()))
        elif change.endswith('_version'):
            actor=flow[change.removesuffix('_version')]
            conn.execute(table('users').update().where(table('users').c.id==actor['user_id']).values(auth_version=table('users').c.auth_version+1))
        elif change=='applicant_suspended':
            conn.execute(table('users').update().where(table('users').c.id==flow['applicant']['user_id']).values(status='SUSPENDED'))
        elif change=='membership_revoked':
            conn.execute(table('org_memberships').update().where(table('org_memberships').c.id==flow['member']).values(status='REVOKED',revoked_at=now()))
        elif change in ('contact_revoked','contact_recycled'):
            values={'revoked_at':now()} if change=='contact_revoked' else {'normalized_value':str(uuid4())+'@example.test'}
            conn.execute(table('user_contacts').update().where(table('user_contacts').c.id==flow['contact']['id']).values(**values))
        elif change.startswith('file_'):
            values={'deleted_at':now()} if change=='file_deleted' else ({'scan_status':'ERROR'} if change=='file_scan_error' else {'owner_user_id':flow['owner']['user_id']})
            conn.execute(table('files').update().where(table('files').c.id==flow['file']['id']).values(**values))
        elif change.endswith('_grant'):
            actor=flow[change.removesuffix('_grant')]
            conn.execute(table('platform_role_grants').update().where(table('platform_role_grants').c.user_id==actor['user_id']).values(revoked_at=now()))
    if change.startswith('compliance_'):
        response=client.get('/api/v1/owner-continuity/'+case,headers=flow['applicant']['headers'])
    else:response=decide(client,flow,case,'compliance')
    assert response.status_code==200 and response.json()['status']=='EXPIRED' and response.json()['closed_automatically'],response.text
    assert not has_owner(flow['member'])
    with transaction() as conn:
        assert conn.execute(select(table('recovery_requests').c.status)).scalar_one()=='EXPIRED'
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==0

def test_expired_consent_is_closed_and_a_new_request_can_start(client,setup_continuity,monkeypatch):
    from app.services import owner_continuity as module
    # Shorten only the test deadline; PostgreSQL still enforces actual clock expiry.
    monkeypatch.setattr(module,'timedelta',lambda **kwargs:timedelta(seconds=5))
    flow=setup_continuity;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];time.sleep(5.1)
    response=client.get('/api/v1/owner-continuity/'+case,headers=flow['applicant']['headers'])
    assert response.status_code==200 and response.json()['status']=='EXPIRED',response.text
    monkeypatch.undo()
    response=submit(client,flow,key='fresh-request-after-real-expiry');assert response.status_code==202,response.text
    assert response.json()['id']!=case and not has_owner(flow['member'])

def test_contact_binding_is_stable_across_database_timezones(client,setup_continuity):
    from app.services.owner_continuity import contact_binding
    flow=setup_continuity;bindings=[]
    for zone in ('UTC','Asia/Tashkent'):
        with transaction() as conn:
            conn.execute(text("SELECT set_config('TimeZone',:zone,true)"),{'zone':zone})
            bindings.append(contact_binding(conn,flow['applicant']['user_id'],flow['contact']['id'])[1])
    assert bindings[0]==bindings[1]
