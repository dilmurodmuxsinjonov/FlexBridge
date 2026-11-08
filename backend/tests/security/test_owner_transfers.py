"""HTTP departure, successor consent, preserved staff access and last-owner races."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.db.storage import table,transaction,now
from app.services.placements import insert_row
from app.services.organizations import role_id,owner_ids
from test_owner_additions import member_id,has_owner
from test_candidate import cv_fixture
from test_invitations import contact
from test_organizations import claim,decide

NOTE='Evidence authorizing my departure with this named existing OWNER successor'

@pytest.fixture
def setup_transfer(identities,organization):
    owner=identities('OWNER',organization);target=identities('OWNER',organization);moderator=identities('MODERATOR')
    owner_member=member_id(owner,organization);target_member=member_id(target,organization)
    with transaction() as conn:
        insert_row(conn,'org_role_grants',membership_id=owner_member,role_id=role_id(conn,'HR'),granted_by_id=owner['user_id'])
    return dict(owner=owner,target=target,moderator=moderator,org=organization,owner_member=owner_member,
        target_member=target_member,file=cv_fixture(owner),contact=contact(target,value=str(uuid4())+'@example.test',channel='EMAIL'))

def submit(client,flow,key='owner-departure-request',actor=None,**changes):
    return client.post('/api/v1/organizations/'+flow['org']+'/owner-transfers',headers={
        **(actor or flow['owner'])['headers'],'Idempotency-Key':key},json={
        'target_membership_id':flow['target_member'],'file_ids':[flow['file']['id']],'evidence_note':NOTE,**changes})

def consent(client,flow,case,actor=None,revision=1,decision='ACCEPT',**changes):
    payload={'expected_revision':revision,'decision':decision}
    if decision=='ACCEPT':payload['contact_id']=flow['contact']['id']
    return client.post('/api/v1/owner-transfers/'+case+'/consent',headers=(actor or flow['target'])['headers'],json={**payload,**changes})

def ready(client,flow):
    response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];response=consent(client,flow,case);assert response.status_code==200,response.text
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    return case

def test_departure_requires_named_consent_and_review_preserves_other_roles_and_receipt(client,setup_transfer):
    flow=setup_transfer;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];assert response.json()['status']=='WAITING_CONSENT'
    assert response.headers['cache-control']=='no-store'
    response=claim(client,flow['moderator'],case);assert response.status_code==409,response.text
    response=consent(client,flow,case,actor=flow['owner']);assert response.status_code==403,response.text
    assert has_owner(flow['owner_member']) and has_owner(flow['target_member'])
    response=consent(client,flow,case);assert response.status_code==200,response.text
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    detail=client.get('/api/v1/operator/verification-cases/'+case,headers=flow['moderator']['headers'])
    assert detail.status_code==200,detail.text
    assert detail.json()['owner_transfer']['target_user_id']==flow['target']['user_id']
    assert flow['contact']['normalized_value'] not in detail.text
    response=decide(client,flow['moderator'],case);assert response.status_code==200,response.text
    event=response.json()['ownership_event_id'];assert event
    assert not has_owner(flow['owner_member']) and has_owner(flow['target_member'])
    with transaction() as conn:
        member=conn.execute(select(table('org_memberships')).where(table('org_memberships').c.id==flow['owner_member'])).mappings().one()
        assert member['status']=='ACTIVE' and member['revoked_at'] is None
        grants,roles=table('org_role_grants'),table('role_catalog')
        codes=conn.execute(select(roles.c.code).join(grants,grants.c.role_id==roles.c.id).where(
            grants.c.membership_id==flow['owner_member'],grants.c.revoked_at.is_(None))).scalars().all()
        assert codes==['HR']
        assert conn.execute(select(func.count()).select_from(grants)).scalar_one()==3
        history=conn.execute(select(table('org_ownership_events')).where(table('org_ownership_events').c.id==event)).mappings().one()
        assert history['previous_membership_id']==flow['owner_member'] and history['new_membership_id']==flow['target_member']
    response=client.get('/api/v1/organizations/'+flow['org']+'/memberships',headers=flow['owner']['headers'])
    assert response.status_code==403,response.text
    receipt=client.get('/api/v1/owner-transfers/'+case,headers=flow['owner']['headers'])
    assert receipt.status_code==200 and receipt.json()['status']=='APPROVED',receipt.text
    replay=submit(client,flow);assert replay.status_code==202 and replay.json()['idempotent_replay'],replay.text
    response=submit(client,flow,key='a-new-mutation-after-departure');assert response.status_code==403,response.text
    replay=decide(client,flow['moderator'],case)
    assert replay.status_code==200 and replay.json()['ownership_event_id']==event and replay.json()['idempotent_replay'],replay.text

def test_needs_info_requires_new_revision_consent(client,setup_transfer):
    flow=setup_transfer;case=ready(client,flow)
    response=decide(client,flow['moderator'],case,decision='NEEDS_INFO');assert response.status_code==200,response.text
    response=consent(client,flow,case);assert response.status_code==409,response.text
    response=client.post('/api/v1/owner-transfers/'+case+'/resubmit',headers=flow['owner']['headers'],json={
        'expected_revision':1,'file_ids':[flow['file']['id']],'evidence_note':'Revised evidence for the exact same successor'})
    assert response.status_code==200 and response.json()['revision']==2,response.text
    response=consent(client,flow,case);assert response.status_code==409,response.text
    response=consent(client,flow,case,revision=2);assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],case,revision=2);assert response.status_code==200,response.text

@pytest.mark.parametrize('decision',['DECLINE','CANCEL','REJECT'])
def test_closed_without_departure_keeps_both_owners(client,setup_transfer,decision):
    flow=setup_transfer;case=ready(client,flow)
    if decision=='DECLINE':response=consent(client,flow,case,decision='DECLINE')
    elif decision=='CANCEL':response=client.post('/api/v1/owner-transfers/'+case+'/cancel',headers=flow['owner']['headers'],json={'reason':'Withdraw my request to relinquish the OWNER role'})
    else:response=decide(client,flow['moderator'],case,decision='REJECT')
    assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],case);assert response.status_code==409,response.text
    assert has_owner(flow['owner_member']) and has_owner(flow['target_member'])

@pytest.mark.parametrize('stage',['event','audit','deferred_proof'])
def test_departure_history_case_and_audit_rollback(client,setup_transfer,monkeypatch,stage):
    from app.services import owner_transfers as module
    flow=setup_transfer;case=ready(client,flow);original=module.insert_row
    def insert(conn,name,**values):
        if name=='org_ownership_events':
            if stage=='event':raise RuntimeError('Synthetic transfer event failure')
            if stage=='deferred_proof':values['previous_membership_id']=flow['target_member']
        return original(conn,name,**values)
    def audit(**kwargs):raise RuntimeError('Synthetic transfer audit failure')
    monkeypatch.setattr(module,'insert_row',insert)
    if stage=='audit':monkeypatch.setattr(module.owner_transfer_service.audit_store,'append_audit_event',audit)
    response=decide(client,flow['moderator'],case)
    assert response.status_code==(409 if stage=='deferred_proof' else 503),response.text
    assert has_owner(flow['owner_member']) and has_owner(flow['target_member'])
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==0
        assert conn.execute(select(table('verification_cases').c.status).where(table('verification_cases').c.id==case)).scalar_one()=='IN_REVIEW'

def test_opposite_concurrent_departures_leave_one_owner(client,setup_transfer):
    flow=setup_transfer;first=ready(client,flow)
    opposite={**flow,'owner':flow['target'],'target':flow['owner'],'owner_member':flow['target_member'],
        'target_member':flow['owner_member'],'file':cv_fixture(flow['target']),
        'contact':contact(flow['owner'],value=str(uuid4())+'@example.test',channel='EMAIL')}
    second=ready(client,opposite)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda case:decide(client,flow['moderator'],case),(first,second)))
    assert sorted(r.status_code for r in responses) in ([200,403],[200,409]),[r.status_code for r in responses]
    with transaction() as conn:
        assert len(owner_ids(conn,flow['org']))==1
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==1

def test_generic_revoke_racing_departure_never_removes_both_owners(client,setup_transfer):
    flow=setup_transfer;case=ready(client,flow)
    def revoke():return client.post('/api/v1/organizations/'+flow['org']+'/memberships/'+flow['target_member']+'/revoke',
        headers=flow['owner']['headers'],json={'reason':'End the successor membership before approval'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(decide,client,flow['moderator'],case);b=pool.submit(revoke)
        responses=[a.result(),b.result()]
    assert sorted(r.status_code for r in responses) in ([200,403],[200,409]),[r.status_code for r in responses]
    with transaction() as conn:assert len(owner_ids(conn,flow['org']))==1

@pytest.mark.parametrize('change,expected',[
    ('requester_grant',403),('requester_version',409),('target_inactive',403),('target_membership',403),
    ('target_grant',403),('target_version',409),('contact_revoked',403),('contact_recycled',409),
    ('expired_consent',409),('file_deleted',409),('file_scan_error',409),('file_foreign',403)])
def test_departure_rechecks_current_authority_contact_evidence(client,setup_transfer,change,expected):
    flow=setup_transfer;case=ready(client,flow)
    with transaction() as conn:
        if change in ('requester_grant','target_grant'):
            member=flow['owner_member'] if change=='requester_grant' else flow['target_member']
            grants=table('org_role_grants')
            conn.execute(grants.update().where(grants.c.membership_id==member,grants.c.role_id==role_id(conn,'OWNER')).values(revoked_at=now()))
        elif change in ('requester_version','target_version'):
            uid=flow['owner']['user_id'] if change=='requester_version' else flow['target']['user_id']
            conn.execute(table('users').update().where(table('users').c.id==uid).values(auth_version=table('users').c.auth_version+1))
        elif change=='target_inactive':
            conn.execute(table('users').update().where(table('users').c.id==flow['target']['user_id']).values(status='SUSPENDED'))
        elif change=='target_membership':
            conn.execute(table('org_memberships').update().where(table('org_memberships').c.id==flow['target_member']).values(status='REVOKED',revoked_at=now()))
        elif change in ('contact_revoked','contact_recycled'):
            values={'revoked_at':now()} if change=='contact_revoked' else {'normalized_value':str(uuid4())+'@example.test'}
            conn.execute(table('user_contacts').update().where(table('user_contacts').c.id==flow['contact']['id']).values(**values))
        elif change.startswith('file_'):
            values={'deleted_at':now()} if change=='file_deleted' else ({'scan_status':'ERROR'} if change=='file_scan_error' else {'owner_user_id':flow['target']['user_id']})
            conn.execute(table('files').update().where(table('files').c.id==flow['file']['id']).values(**values))
        else:
            # Trusted expired-history fixture, leaving the earlier immutable consent intact.
            events=table('owner_transfer_consents');old=dict(conn.execute(select(events)).mappings().one())
            conn.execute(events.insert().values(**{**old,'id':str(uuid4()),'event_no':old['event_no']+1,
                'created_at':now()-timedelta(hours=2),'expires_at':now()-timedelta(hours=1)}))
    response=decide(client,flow['moderator'],case)
    assert response.status_code==expected,response.text
    # The transfer itself has made no source revocation, regardless of the synthetic mutation above.
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==0
        if change!='requester_grant':assert has_owner(flow['owner_member'])

@pytest.mark.parametrize('extra',[{'actor_id':str(uuid4())},{'approved':True},{'requester_grant_id':str(uuid4())},{'role':'OWNER'}])
def test_client_cannot_supply_authority_or_approval(client,setup_transfer,extra):
    response=submit(client,setup_transfer,**extra);assert response.status_code==422,response.text

def test_all_transfer_routes_require_authenticated_session(client):
    uid=str(uuid4())
    for method,path in [('GET','/api/v1/me/owner-transfers'),('GET','/api/v1/owner-transfers/'+uid),
        ('POST','/api/v1/organizations/'+uid+'/owner-transfers'),('POST','/api/v1/owner-transfers/'+uid+'/consent'),
        ('POST','/api/v1/owner-transfers/'+uid+'/resubmit'),('POST','/api/v1/owner-transfers/'+uid+'/cancel')]:
        response=client.request(method,path,json={} if method=='POST' else None)
        assert response.status_code==401,(method,path,response.status_code)
        assert response.headers['cache-control']=='no-store'

def test_successor_must_be_other_existing_owner_in_same_org(client,setup_transfer,identities):
    flow=setup_transfer
    response=submit(client,flow,target_membership_id=flow['owner_member']);assert response.status_code==422,response.text
    staff=identities('HR',flow['org'])
    response=submit(client,flow,target_membership_id=member_id(staff,flow['org']));assert response.status_code==403,response.text
    other=insert_other_org(identities)
    response=submit(client,flow,target_membership_id=other);assert response.status_code==403,response.text

def insert_other_org(identities):
    with transaction() as conn:
        org=insert_row(conn,'organizations',tax_id='other-'+uuid4().hex,legal_name='Other organization',public_name='Other organization',region='Tashkent',status='VERIFIED')
    return member_id(identities('OWNER',org['id']),org['id'])

def test_contact_and_receipts_are_private(client,setup_transfer,identities):
    flow=setup_transfer;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id']
    foreign=contact(flow['owner'],value=str(uuid4())+'@example.test',channel='EMAIL')
    response=consent(client,flow,case,contact_id=foreign['id']);assert response.status_code==403,response.text
    unverified=contact(flow['target'],value=str(uuid4())+'@example.test',channel='EMAIL',verified=False)
    response=consent(client,flow,case,contact_id=unverified['id']);assert response.status_code==403,response.text
    response=consent(client,flow,case);assert response.status_code==200,response.text
    for forbidden in ('contact_digest','normalized_value','auth_version','session_id','target_grant_id',flow['contact']['normalized_value']):
        assert forbidden not in response.text
    other=identities('OWNER',flow['org'])
    response=client.get('/api/v1/owner-transfers/'+case,headers=other['headers']);assert response.status_code==403,response.text
    response=client.get('/api/v1/me/owner-transfers',headers=other['headers']);assert response.status_code==200 and response.json()['items']==[],response.text
    response=client.get('/api/v1/me/owner-transfers',headers=flow['target']['headers']);assert response.status_code==200 and response.json()['items'][0]['case_id']==case,response.text

def test_password_only_successor_cannot_consent(client,setup_transfer,identities):
    flow=setup_transfer;user=identities()
    with transaction() as conn:
        member=insert_row(conn,'org_memberships',organization_id=flow['org'],user_id=user['user_id'],status='ACTIVE')
        insert_row(conn,'org_role_grants',membership_id=member['id'],role_id=role_id(conn,'OWNER'),granted_by_id=flow['owner']['user_id'])
    changed={**flow,'target':user,'target_member':member['id'],'contact':contact(user,value=str(uuid4())+'@example.test',channel='EMAIL')}
    response=submit(client,changed);assert response.status_code==202,response.text
    response=consent(client,changed,response.json()['id']);assert response.status_code==403,response.text
    assert has_owner(flow['owner_member'])

def test_participants_with_real_moderator_grants_cannot_review(client,setup_transfer,identities):
    flow=setup_transfer;response=submit(client,flow);case=response.json()['id']
    response=consent(client,flow,case);assert response.status_code==200,response.text
    with transaction() as conn:
        role=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='MODERATOR')).scalar_one()
        for user in (flow['owner'],flow['target']):
            insert_row(conn,'platform_role_grants',user_id=user['user_id'],role_id=role,
                granted_by_id=flow['moderator']['user_id'],expires_at=now()+timedelta(hours=1))
    for user in (flow['owner'],flow['target']):
        response=claim(client,user,case)
        assert response.status_code==403 and response.json()['detail']['code']=='SELF_REVIEW_FORBIDDEN',response.text
    other=identities('MODERATOR')
    response=decide(client,other,case);assert response.status_code==403,response.text
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    response=decide(client,other,case);assert response.status_code==403,response.text

def test_transfer_proposal_consent_and_history_are_immutable(client,setup_transfer):
    flow=setup_transfer;case=ready(client,flow)
    response=decide(client,flow['moderator'],case);assert response.status_code==200,response.text
    targets=[('owner_transfer_requests','case_id',case),('owner_transfer_consents','case_id',case),
        ('org_ownership_events','id',response.json()['ownership_event_id'])]
    for name,key,value in targets:
        target=table(name)
        with pytest.raises(IntegrityError) as error,transaction() as conn:
            conn.execute(target.update().where(target.c[key]==value).values(created_at=now()))
        assert error.value.orig.sqlstate=='23514'
        with pytest.raises(IntegrityError),transaction() as conn:conn.execute(target.delete().where(target.c[key]==value))

def test_parallel_retries_are_single_effect(client,setup_transfer):
    flow=setup_transfer
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:submit(client,flow),range(2)))
    assert [r.status_code for r in responses]==[202,202]
    assert responses[0].json()['id']==responses[1].json()['id']
    assert sorted(r.json()['idempotent_replay'] for r in responses)==[False,True]
    case=responses[0].json()['id']
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:consent(client,flow,case),range(2)))
    assert [r.status_code for r in responses]==[200,200]
    assert sorted(r.json()['idempotent_replay'] for r in responses)==[False,True]
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:decide(client,flow['moderator'],case),range(2)))
    assert [r.status_code for r in responses]==[200,200]
    assert sorted(r.json()['idempotent_replay'] for r in responses)==[False,True]
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==1
        audits=table('audit_events')
        assert conn.execute(select(func.count()).select_from(audits).where(audits.c.object_key==case,audits.c.action=='OWNER_TRANSFER_APPROVED')).scalar_one()==1

def test_generic_or_forged_case_cannot_bypass_transfer_consent(client,setup_transfer):
    flow=setup_transfer;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id']
    response=client.post('/api/v1/organizations/'+flow['org']+'/verification',headers=flow['owner']['headers'],json={
        'kind':'ORG_OWNER_TRANSFER','case_id':case,'file_ids':[flow['file']['id']],'evidence_note':NOTE})
    assert response.status_code==422,response.text
    with transaction() as conn:
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case).values(status='PENDING'))
        forged=insert_row(conn,'verification_cases',organization_id=flow['org'],requester_id=flow['owner']['user_id'],kind='ORG_OWNER_TRANSFER',status='PENDING',current_revision=1,due_at=now()+timedelta(days=1))
    response=claim(client,flow['moderator'],forged['id']);assert response.status_code==404,response.text
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],case);assert response.status_code==409,response.text
    response=client.post('/api/v1/operator/verification-cases/'+case+'/decide',headers=flow['moderator']['headers'],json={
        'decision':'APPROVE','expected_revision':True,'reason':'A boolean is never a valid evidence revision'})
    assert response.status_code==422,response.text
    assert has_owner(flow['owner_member'])
