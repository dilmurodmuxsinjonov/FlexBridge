"""Named staff consent, independent OWNER proof, SQL history and real transaction races."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.db.storage import table,transaction,now
from test_candidate import cv_fixture
from test_invitations import contact
from test_organizations import claim,decide
from app.services.placements import insert_row

NOTE='Evidence authorizing this additional organization representative'


def member_id(user,org):
    with transaction() as conn:
        return conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.user_id==user['user_id'],
            table('org_memberships').c.organization_id==org)).scalar_one()


def has_owner(member):
    with transaction() as conn:
        grants,roles=table('org_role_grants'),table('role_catalog')
        return conn.execute(select(grants.c.id).join(roles,roles.c.id==grants.c.role_id).where(
            grants.c.membership_id==member,grants.c.revoked_at.is_(None),roles.c.code=='OWNER',roles.c.scope_kind=='ORG')).first() is not None


@pytest.fixture
def setup_owner(identities,organization):
    owner=identities('OWNER',organization);target=identities('HR',organization);moderator=identities('MODERATOR')
    verified=contact(target,value=str(uuid4())+'@example.test',channel='EMAIL')
    return dict(owner=owner,target=target,moderator=moderator,org=organization,target_member=member_id(target,organization),
        file=cv_fixture(owner),contact=verified)


def submit(client,flow,**changes):
    return client.post('/api/v1/organizations/'+flow['org']+'/owner-requests',headers={
        **flow['owner']['headers'],'Idempotency-Key':'owner-addition-request'},json={
            'target_membership_id':flow['target_member'],'file_ids':[flow['file']['id']],'evidence_note':NOTE,**changes})


def consent(client,flow,case,*,actor=None,revision=1,decision='ACCEPT',contact_id=None,**changes):
    payload={'expected_revision':revision,'decision':decision,**changes}
    if decision=='ACCEPT':payload['contact_id']=contact_id or flow['contact']['id']
    return client.post('/api/v1/owner-requests/'+case+'/consent',headers=(actor or flow['target'])['headers'],json=payload)


def accepted(client,flow):
    response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];response=consent(client,flow,case)
    assert response.status_code==200,response.text
    return case


def ready(client,flow):
    case=accepted(client,flow);response=claim(client,flow['moderator'],case)
    assert response.status_code==200,response.text
    return case


def test_real_target_consent_and_independent_approval_grant_only_owner(client,setup_owner):
    flow=setup_owner;response=submit(client,flow)
    assert response.status_code==202,response.text
    case=response.json()['id'];assert response.json()['status']=='WAITING_CONSENT'
    assert response.headers['cache-control']=='no-store' and not has_owner(flow['target_member'])
    response=claim(client,flow['moderator'],case);assert response.status_code==409,response.text
    response=consent(client,flow,case,actor=flow['owner']);assert response.status_code==403,response.text
    response=consent(client,flow,case);assert response.status_code==200,response.text
    assert response.json()['status']=='PENDING' and not has_owner(flow['target_member'])
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    detail=client.get('/api/v1/operator/verification-cases/'+case,headers=flow['moderator']['headers'])
    assert detail.status_code==200,detail.text
    assert detail.json()['owner_request']['target_user_id']==flow['target']['user_id']
    assert flow['contact']['normalized_value'] not in detail.text
    response=decide(client,flow['moderator'],case);assert response.status_code==200,response.text
    assert response.json()['status']=='APPROVED' and has_owner(flow['target_member'])
    event=response.json()['ownership_event_id'];assert event
    repeat=decide(client,flow['moderator'],case);assert repeat.status_code==200,repeat.text
    assert repeat.json()['idempotent_replay'] and repeat.json()['ownership_event_id']==event
    response=client.get('/api/v1/organizations/'+flow['org']+'/memberships',headers=flow['target']['headers'])
    assert response.status_code==200,response.text
    with transaction() as conn:
        grants,roles=table('org_role_grants'),table('role_catalog')
        codes=conn.execute(select(roles.c.code).join(grants,grants.c.role_id==roles.c.id).where(
            grants.c.membership_id==flow['target_member'],grants.c.revoked_at.is_(None))).scalars().all()
        assert set(codes)=={'HR','OWNER'}
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==1


def test_new_evidence_revision_requires_fresh_named_target_consent(client,setup_owner):
    flow=setup_owner;case=accepted(client,flow)
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],case,'NEEDS_INFO');assert response.status_code==200,response.text
    revised_file=cv_fixture(flow['owner'])
    response=client.post('/api/v1/owner-requests/'+case+'/resubmit',headers=flow['owner']['headers'],json={
        'expected_revision':1,'file_ids':[revised_file['id']],'evidence_note':'Additional evidence for the same named target'})
    assert response.status_code==200,response.text
    assert response.json()['revision']==2 and response.json()['status']=='WAITING_CONSENT'
    response=decide(client,flow['moderator'],case,revision=2);assert response.status_code==409,response.text
    response=consent(client,flow,case,revision=1);assert response.status_code==409,response.text
    response=consent(client,flow,case,revision=2);assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],case,revision=2);assert response.status_code==200,response.text
    assert has_owner(flow['target_member'])
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('owner_addition_consents'))).scalar_one()==2
        assert conn.execute(select(func.count()).select_from(table('org_verification_submissions'))).scalar_one()==2


@pytest.mark.parametrize('changes',[{'actor_id':str(uuid4())},{'target_user_id':str(uuid4())},
    {'role_code':'OWNER'},{'approved':True}])
def test_proposal_does_not_accept_client_authority_fields(client,setup_owner,changes):
    response=submit(client,setup_owner,**changes)
    assert response.status_code==422,response.text
    assert not has_owner(setup_owner['target_member'])


def test_wrong_org_self_and_revoked_staff_targets_are_rejected(client,setup_owner,identities):
    flow=setup_owner
    response=submit(client,flow,target_membership_id=member_id(flow['owner'],flow['org']))
    assert response.status_code==422,response.text
    with transaction() as conn:
        other_org=insert_row(conn,'organizations',tax_id=str(uuid4()),legal_name='Different organization',
            public_name='Different organization',region='Tashkent',status='VERIFIED')
    stranger=identities('HR',other_org['id'])
    response=submit(client,flow,target_membership_id=member_id(stranger,other_org['id']))
    assert response.status_code==403,response.text
    with transaction() as conn:
        conn.execute(table('org_memberships').update().where(table('org_memberships').c.id==flow['target_member'])
            .values(status='REVOKED',revoked_at=now()))
    response=submit(client,flow);assert response.status_code==403,response.text


def test_verified_contact_is_owned_current_and_never_returned(client,setup_owner):
    flow=setup_owner;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id']
    foreign=contact(flow['owner'],value=str(uuid4())+'@example.test',channel='EMAIL')
    response=consent(client,flow,case,contact_id=foreign['id']);assert response.status_code==403,response.text
    unverified=contact(flow['target'],value=str(uuid4())+'@example.test',channel='EMAIL',verified=False)
    response=consent(client,flow,case,contact_id=unverified['id']);assert response.status_code==403,response.text
    response=consent(client,flow,case);assert response.status_code==200,response.text
    for forbidden in ('normalized_value','contact_digest','auth_version','session_id',flow['contact']['normalized_value']):
        assert forbidden not in response.text
    response=client.get('/api/v1/me/owner-requests',headers=flow['owner']['headers'])
    assert response.status_code==200 and response.json()['items']==[]
    response=client.get('/api/v1/me/owner-requests',headers=flow['target']['headers'])
    assert response.status_code==200 and response.json()['items'][0]['case_id']==case


def test_password_only_target_cannot_consent(client,setup_owner,identities):
    flow=setup_owner;user=identities()
    with transaction() as conn:
        role=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='HR',
            table('role_catalog').c.scope_kind=='ORG')).scalar_one()
        member=insert_row(conn,'org_memberships',organization_id=flow['org'],user_id=user['user_id'],status='ACTIVE')
        insert_row(conn,'org_role_grants',membership_id=member['id'],role_id=role,granted_by_id=flow['owner']['user_id'])
    verified=contact(user,value=str(uuid4())+'@example.test',channel='EMAIL')
    changed={**flow,'target':user,'target_member':member['id'],'contact':verified}
    response=submit(client,changed);assert response.status_code==202,response.text
    case=response.json()['id'];response=consent(client,changed,case)
    assert response.status_code==403,response.text
    assert not has_owner(member['id'])


def test_self_review_and_unassigned_review_are_rejected(client,setup_owner,identities):
    flow=setup_owner;case=accepted(client,flow)
    # Give the two participants real MODERATOR grants so independence, not role absence, rejects them.
    with transaction() as conn:
        role=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='MODERATOR')).scalar_one()
        for user in (flow['owner'],flow['target']):
            insert_row(conn,'platform_role_grants',user_id=user['user_id'],role_id=role,
                granted_by_id=flow['moderator']['user_id'],expires_at=now()+timedelta(hours=1))
    for user in (flow['owner'],flow['target']):
        response=claim(client,user,case)
        assert response.status_code==403 and response.json()['detail']['code']=='SELF_REVIEW_FORBIDDEN'
    other=identities('MODERATOR')
    response=decide(client,other,case);assert response.status_code==403,response.text
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    response=decide(client,other,case);assert response.status_code==403,response.text
    response=client.get('/api/v1/operator/verification-cases/'+case,headers=other['headers'])
    assert response.status_code==403,response.text


@pytest.mark.parametrize('change,expected',[
    ('requester_grant',403),('requester_version',409),('target_inactive',403),('target_membership',403),
    ('target_grant',403),('target_version',409),('contact_revoked',403),('contact_recycled',409),('expired_consent',409)])
def test_approval_rechecks_current_requester_target_and_consent(client,setup_owner,change,expected):
    flow=setup_owner;case=ready(client,flow)
    with transaction() as conn:
        if change=='requester_grant':
            conn.execute(table('org_role_grants').update().where(table('org_role_grants').c.membership_id==member_id(flow['owner'],flow['org'])).values(revoked_at=now()))
        elif change=='requester_version':
            conn.execute(table('users').update().where(table('users').c.id==flow['owner']['user_id']).values(auth_version=table('users').c.auth_version+1))
        elif change=='target_inactive':
            conn.execute(table('users').update().where(table('users').c.id==flow['target']['user_id']).values(status='SUSPENDED'))
        elif change=='target_membership':
            conn.execute(table('org_memberships').update().where(table('org_memberships').c.id==flow['target_member']).values(status='REVOKED',revoked_at=now()))
        elif change=='target_grant':
            conn.execute(table('org_role_grants').update().where(table('org_role_grants').c.membership_id==flow['target_member']).values(revoked_at=now()))
        elif change=='target_version':
            conn.execute(table('users').update().where(table('users').c.id==flow['target']['user_id']).values(auth_version=table('users').c.auth_version+1))
        elif change=='contact_revoked':
            conn.execute(table('user_contacts').update().where(table('user_contacts').c.id==flow['contact']['id']).values(revoked_at=now()))
        elif change=='contact_recycled':
            conn.execute(table('user_contacts').update().where(table('user_contacts').c.id==flow['contact']['id']).values(normalized_value=str(uuid4())+'@example.test'))
        else:
            # Explicit expired-history fixture; immutable earlier consent is not overwritten.
            events=table('owner_addition_consents');old=dict(conn.execute(select(events)).mappings().one())
            conn.execute(events.insert().values(**{**old,'id':str(uuid4()),'event_no':old['event_no']+1,
                'created_at':now()-timedelta(hours=2),'expires_at':now()-timedelta(hours=1)}))
    response=decide(client,flow['moderator'],case)
    assert response.status_code==expected,response.text
    assert not has_owner(flow['target_member'])
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==0


def test_generic_verification_cannot_approve_owner_case_without_consent(client,setup_owner):
    flow=setup_owner;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id']
    response=client.post('/api/v1/organizations/'+flow['org']+'/verification',headers=flow['owner']['headers'],json={
        'kind':'ORG_OWNER_ADDITION','case_id':case,'file_ids':[flow['file']['id']],'evidence_note':NOTE})
    assert response.status_code==422,response.text
    with transaction() as conn:
        # Trusted-corruption fixture exercises the explicit decision branch, beyond queue state.
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case).values(status='PENDING'))
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],case)
    assert response.status_code==409 and response.json()['detail']['code']=='OWNER_TARGET_CONSENT_REQUIRED'
    assert not has_owner(flow['target_member'])


@pytest.mark.parametrize('action',['decline','withdraw','cancel','reject','needs_info_decline'])
def test_decline_withdraw_cancel_and_reject_never_grant(client,setup_owner,action):
    flow=setup_owner
    if action in ('withdraw','reject','needs_info_decline'):case=ready(client,flow)
    else:
        response=submit(client,flow);assert response.status_code==202,response.text
        case=response.json()['id']
    if action=='needs_info_decline':
        response=decide(client,flow['moderator'],case,'NEEDS_INFO');assert response.status_code==200,response.text
    if action in ('decline','withdraw','needs_info_decline'):
        response=consent(client,flow,case,decision='DECLINE')
    elif action=='cancel':
        response=client.post('/api/v1/owner-requests/'+case+'/cancel',headers=flow['owner']['headers'],json={'reason':'Requester cancelled this ownership proposal'})
    else:response=decide(client,flow['moderator'],case,'REJECT')
    assert response.status_code==200,response.text
    assert response.json()['status']==('REJECTED' if action=='reject' else 'CANCELLED')
    assert not has_owner(flow['target_member'])
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==0


def test_new_private_routes_require_an_authenticated_session(client):
    key=str(uuid4())
    for method,path in [('GET','/api/v1/me/owner-requests'),('GET','/api/v1/owner-requests/'+key),
        ('POST','/api/v1/organizations/'+key+'/owner-requests'),('POST','/api/v1/owner-requests/'+key+'/consent'),
        ('POST','/api/v1/owner-requests/'+key+'/resubmit'),('POST','/api/v1/owner-requests/'+key+'/cancel')]:
        response=client.request(method,path,**({'json':{}} if method=='POST' else {}))
        assert response.status_code==401,(method,path,response.status_code)


def test_other_owner_cannot_read_or_cancel_another_persons_proposal(client,setup_owner,identities):
    flow=setup_owner;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];other=identities('OWNER',flow['org'])
    response=client.get('/api/v1/owner-requests/'+case,headers=other['headers'])
    assert response.status_code==403,response.text
    response=client.post('/api/v1/owner-requests/'+case+'/cancel',headers=other['headers'],
        json={'reason':'Attempt to cancel another owner proposal'})
    assert response.status_code==403,response.text
    response=consent(client,flow,case,actor=other);assert response.status_code==403,response.text


@pytest.mark.parametrize('change,expected',[('deleted',409),('scan_error',409),('wrong_owner',403)])
def test_approval_rechecks_current_clean_owned_evidence(client,setup_owner,change,expected):
    flow=setup_owner;case=ready(client,flow)
    with transaction() as conn:
        values={'deleted_at':now()} if change=='deleted' else ({'scan_status':'ERROR'} if change=='scan_error'
            else {'owner_user_id':flow['target']['user_id']})
        conn.execute(table('files').update().where(table('files').c.id==flow['file']['id']).values(**values))
    response=decide(client,flow['moderator'],case)
    assert response.status_code==expected,response.text
    assert not has_owner(flow['target_member'])


def test_target_can_give_fresh_consent_after_account_security_changes(client,setup_owner):
    from app.services.auth import generate_totp_code
    flow=setup_owner;case=ready(client,flow)
    with transaction() as conn:
        conn.execute(table('users').update().where(table('users').c.id==flow['target']['user_id'])
            .values(auth_version=table('users').c.auth_version+1))
    response=decide(client,flow['moderator'],case);assert response.status_code==409,response.text
    response=consent(client,flow,case);assert response.status_code==401,response.text
    target=flow['target']
    response=client.post('/api/v1/auth/login',json={'user_id':target['user_id'],'password':'correct-passphrase-2026',
        'totp_code':generate_totp_code(target['totp_secret'])})
    assert response.status_code==200,response.text
    signed_in={**target,**response.json(),'headers':{'Authorization':'Bearer '+response.json()['access_token']}}
    response=consent(client,flow,case,actor=signed_in);assert response.status_code==200,response.text
    assert not response.json()['idempotent_replay']
    response=decide(client,flow['moderator'],case);assert response.status_code==200,response.text
    assert has_owner(flow['target_member'])
