"""ORG HTTP authority boundaries, PostgreSQL constraints and real transaction races."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import ActorContext
from app.db.storage import table, transaction, now, org_verification_submissions as submissions
from app.services.auth import auth_service, generate_totp_code
from app.services.organizations import organization_service as service, require_capability, due_date
from app.services.governance import GovernanceError
from app.services.placements import insert_row
from test_candidate import cv_fixture
from test_regressions import checkout, capture, billing
from test_adapters_and_quota import draft, approve_for_test


def mfa_user(identities):
    user=identities()
    secret=auth_service.enroll_totp(user['user_id'],'correct-passphrase-2026')
    auth_service.confirm_totp(user['user_id'],generate_totp_code(secret))
    session=auth_service.login(user_id=user['user_id'],password='correct-passphrase-2026',totp_code=generate_totp_code(secret))
    return {**user,**session,'headers':{'Authorization':'Bearer '+session['access_token']}}


def actor(user):return ActorContext(user['user_id'],user['session_id'],())


def register(client,user,tax_id='123456789',**extra):
    file=cv_fixture(user)
    body={'tax_id':tax_id,'legal_name':'Test Legal Company','public_name':'Test Company','region':'Tashkent',
        'file_ids':[file['id']],'evidence_note':'Authorized representative proof',**extra}
    return client.post('/api/v1/organizations',headers=user['headers'],json=body)


def claim(client,moderator,case):
    return client.post('/api/v1/operator/verification-cases/'+case+'/claim',headers=moderator['headers'])


def decide(client,moderator,case,decision='APPROVE',revision=1):
    return client.post('/api/v1/operator/verification-cases/'+case+'/decide',headers=moderator['headers'],
        json={'decision':decision,'expected_revision':revision,'reason':'Independent evidence review completed'})


def onboard(client,identities):
    user=mfa_user(identities);mod=identities('MODERATOR')
    response=register(client,user)
    assert response.status_code==202,response.text
    result=response.json()
    assert claim(client,mod,result['case_id']).status_code==200
    response=decide(client,mod,result['case_id'])
    assert response.status_code==200,response.text
    return user,mod,result


def request_cap(client,user,org,kind='JOB_EMPLOYER',**extra):
    file=cv_fixture(user)
    return client.post('/api/v1/organizations/'+org+'/verification',headers=user['headers'],json={
        'kind':kind,'file_ids':[file['id']],'evidence_note':'Capability supporting evidence',**extra})


def test_registration_stays_pending_and_deduplicates(client,identities):
    user=mfa_user(identities)
    response=register(client,user,tax_id='123-456-789')
    assert response.status_code==202,response.text
    result=response.json();org=result['organization_id']
    assert result['membership_status']=='PENDING_VERIFICATION'
    assert client.get('/api/v1/auth/me',headers=user['headers']).json()['roles']==['CANDIDATE']
    assert client.get('/api/v1/organizations/'+org+'/memberships',headers=user['headers']).status_code==403
    assert client.get('/api/v1/organizations/'+org+'/public').status_code==404
    repeated=register(client,user,tax_id='123 456 789').json()
    assert repeated['organization_id']==org and repeated['case_id']==result['case_id']
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('organizations'))).scalar_one()==1
        assert conn.execute(select(table('organizations').c.tax_id)).scalar_one()=='123456789'
        assert conn.execute(select(func.count()).select_from(table('org_role_grants'))).scalar_one()==0


def test_onboarding_requires_mfa_and_owned_clean_evidence(client,identities):
    plain=identities()
    assert register(client,plain).status_code==403
    user=mfa_user(identities);foreign=cv_fixture(plain)
    assert register(client,user,file_ids=[foreign['id']]).status_code==403
    dirty=cv_fixture(user,status='PENDING_SCAN')
    assert register(client,user,file_ids=[dirty['id']]).status_code==409
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('organizations'))).scalar_one()==0


@pytest.mark.parametrize('changes',[{'roles':['OWNER']},{'status':'VERIFIED'},{'assigned_reviewer_id':str(uuid4())},
    {'tax_id':'１２３４５６７８９'},{'website':'javascript:alert(1)'},{'evidence_note':'short'},{'membership_role':'OWNER'}])
def test_onboarding_rejects_forged_authority(client,identities,changes):
    response=register(client,mfa_user(identities),**changes)
    assert response.status_code==422,response.text


def test_first_owner_requires_assigned_independent_moderator(client,identities):
    requester=identities('MODERATOR');other=identities('MODERATOR');unassigned=identities('MODERATOR')
    result=register(client,requester).json();case=result['case_id'];org=result['organization_id']
    assert claim(client,requester,case).status_code==403
    assert decide(client,other,case).status_code==403
    assert claim(client,other,case).status_code==200
    assert claim(client,unassigned,case).status_code==403
    assert decide(client,unassigned,case).status_code==403
    response=decide(client,other,case)
    assert response.status_code==200,response.text
    assert decide(client,other,case).status_code==409
    assert 'OWNER' in client.get('/api/v1/auth/me',headers=requester['headers']).json()['roles']
    assert client.get('/api/v1/organizations/'+org+'/memberships',headers=requester['headers']).status_code==200
    public=client.get('/api/v1/organizations/'+org+'/public')
    assert public.status_code==200 and public.json()['capabilities']==[]
    assert not any(k in public.json() for k in ('tax_id','file_ids','case_id','legal_name','requester_id'))
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==1


def test_parallel_tax_registration_and_competing_first_owner_approvals(client,identities):
    a,b=mfa_user(identities),mfa_user(identities)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(register,client,u,tax_id='123-456-789' if i else '123456789') for i,u in enumerate((a,b))]
        results=[f.result(timeout=20) for f in futures]
    assert all(r.status_code==202 for r in results),[r.text for r in results]
    rows=[r.json() for r in results]
    assert rows[0]['organization_id']==rows[1]['organization_id']
    mods=[identities('MODERATOR'),identities('MODERATOR')]
    for mod,row in zip(mods,rows):assert claim(client,mod,row['case_id']).status_code==200
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(decide,client,mod,row['case_id']) for mod,row in zip(mods,rows)]
        codes=sorted(f.result(timeout=20).status_code for f in futures)
    assert codes==[200,409]
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==1


def test_capabilities_are_separate_and_enforced_at_publish(client,identities):
    user,mod,result=onboard(client,identities);org=result['organization_id']
    order,invoice,payment=checkout(user,org);capture(payment)
    revision=draft(user,org);approve_for_test(revision)
    url='/api/v1/opportunities/'+revision['opportunity_id']+'/publish'
    assert client.post(url,headers=user['headers']).status_code==403
    response=request_cap(client,user,org)
    assert response.status_code==202,response.text
    cap=response.json()['id']
    assert request_cap(client,user,org).status_code==409
    assert claim(client,mod,cap).status_code==200
    assert decide(client,mod,cap).status_code==200
    assert client.post(url,headers=user['headers']).status_code==200
    public=client.get('/api/v1/organizations/'+org+'/public').json()
    assert public['capabilities']==['JOB_EMPLOYER']
    with transaction() as conn:
        require_capability(conn,org,'JOB_EMPLOYER')
        with pytest.raises(GovernanceError):require_capability(conn,org,'INTERNSHIP_HOST')
    host=request_cap(client,user,org,'INTERNSHIP_HOST').json()['id']
    assert claim(client,mod,host).status_code==200
    assert decide(client,mod,host).status_code==200
    assert set(client.get('/api/v1/organizations/'+org+'/public').json()['capabilities'])=={'JOB_EMPLOYER','INTERNSHIP_HOST'}


def test_resubmission_preserves_history_and_rejects_stale_revision(client,identities):
    user=mfa_user(identities);mod=identities('MODERATOR');row=register(client,user).json();case=row['case_id'];org=row['organization_id']
    assert claim(client,mod,case).status_code==200
    assert decide(client,mod,case,'NEEDS_INFO').status_code==200
    response=request_cap(client,user,org,'ORG_REPRESENTATIVE',case_id=case)
    assert response.status_code==202,response.text
    assert response.json()['current_revision']==2
    assert decide(client,mod,case,revision=1).status_code==409
    assert decide(client,mod,case,revision=2).status_code==200
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(submissions).where(submissions.c.case_id==case)).scalar_one()==2
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(submissions.update().where(submissions.c.case_id==case).values(proposed_fields={'injected':True}))


def test_evidence_is_assigned_private_and_rechecked_on_approval(client,identities,monkeypatch):
    user=mfa_user(identities);mod,other=identities('MODERATOR'),identities('MODERATOR')
    row=register(client,user).json();case=row['case_id']
    base='/api/v1/operator/verification-cases/'+case
    assert client.get(base,headers=other['headers']).status_code==403
    assert claim(client,mod,case).status_code==200
    detail=client.get(base,headers=mod['headers'])
    assert detail.status_code==200,detail.text
    assert detail.headers['cache-control']=='no-store' and 'storage_key' not in detail.text
    file_id=next(e['file_id'] for e in detail.json()['evidence'] if e['file_id'])
    from app.adapters import storage
    monkeypatch.setattr(storage,'presign_get',lambda key:'https://private.test/signed')
    url=base+'/files/'+file_id+'/download'
    assert client.get(url,headers=other['headers']).status_code==403
    assert client.get(url,headers=mod['headers']).json()['expires_in_seconds']==60
    assert client.get(base+'/files/'+str(uuid4())+'/download',headers=mod['headers']).status_code==403
    with transaction() as conn:
        conn.execute(table('files').update().where(table('files').c.id==file_id).values(deleted_at=now()))
    assert client.get(url,headers=mod['headers']).status_code==409
    assert decide(client,mod,case).status_code==409
    with transaction() as conn:
        assert conn.execute(select(table('org_memberships').c.status).where(table('org_memberships').c.id==row['membership_id'])).scalar_one()=='PENDING_VERIFICATION'


def test_material_edit_waits_for_review(client,identities):
    user,mod,row=onboard(client,identities);org=row['organization_id'];file=cv_fixture(user)
    response=client.patch('/api/v1/organizations/'+org,headers=user['headers'],json={
        'public_name':'Reviewed Company Name','file_ids':[file['id']],'evidence_note':'Official organization change proof'})
    assert response.status_code==202,response.text
    assert client.get('/api/v1/organizations/'+org+'/public').json()['public_name']=='Test Company'
    case=response.json()['case_id']
    assert claim(client,mod,case).status_code==200
    assert decide(client,mod,case).status_code==200
    assert client.get('/api/v1/organizations/'+org+'/public').json()['public_name']=='Reviewed Company Name'


def test_existing_org_join_never_grants_owner_and_ignores_replacement_fields(client,identities,monkeypatch):
    owner,mod,row=onboard(client,identities);org=row['organization_id'];joiner=mfa_user(identities)
    response=register(client,joiner,legal_name='Attempted overwrite',public_name='Overwrite',membership_role='HR')
    assert response.status_code==202,response.text
    result=response.json();assert result['case_id'] is None and result['organization_id']==org
    assert client.get('/api/v1/organizations/'+org+'/public').json()['public_name']=='Test Company'
    base='/api/v1/organizations/'+org+'/membership-requests/'+result['membership_id']
    assert client.get(base,headers=joiner['headers']).status_code==403
    response=client.get(base,headers=owner['headers']);assert response.status_code==200,response.text
    file_id=response.json()['file_ids'][0]
    from app.adapters import storage
    monkeypatch.setattr(storage,'presign_get',lambda key:'https://private.test/signed')
    assert client.get(base+'/files/'+file_id+'/download',headers=owner['headers']).status_code==200
    approve='/api/v1/organizations/'+org+'/members/'+result['membership_id']+'/approve'
    assert client.post(approve,headers=owner['headers'],json={}).status_code==200
    roles=client.get('/api/v1/auth/me',headers=joiner['headers']).json()['roles']
    assert 'HR' in roles and 'OWNER' not in roles
    assert client.get('/api/v1/organizations/'+org+'/memberships',headers=joiner['headers']).status_code==403
    assert client.get(base,headers=owner['headers']).status_code==403


def test_verified_org_does_not_reopen_bootstrap_when_owner_suspended(client,identities):
    owner,mod,row=onboard(client,identities)
    with transaction() as conn:
        conn.execute(table('users').update().where(table('users').c.id==owner['user_id']).values(status='SUSPENDED'))
    result=register(client,mfa_user(identities)).json()
    assert result['organization_id']==row['organization_id'] and result['case_id'] is None
    assert result['membership_status']=='PENDING_APPROVAL'


def test_last_owner_and_parallel_self_revoke(client,identities):
    owner,mod,row=onboard(client,identities);org=row['organization_id'];mid=row['membership_id']
    url='/api/v1/organizations/'+org+'/memberships/'+mid+'/revoke'
    assert client.post(url,headers=owner['headers'],json={'reason':'End organization membership'}).status_code==409
    other=identities('OWNER',org)
    with transaction() as conn:
        other_mid=conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.user_id==other['user_id'])).scalar_one()
    def revoke(user,membership):
        return client.post('/api/v1/organizations/'+org+'/memberships/'+membership+'/revoke',
            headers=user['headers'],json={'reason':'End organization membership'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(revoke,owner,mid),pool.submit(revoke,other,other_mid)]
        results=[f.result(timeout=20) for f in futures]
    assert sorted(r.status_code for r in results)==[200,409],[r.text for r in results]
    revoked_user=owner if results[0].status_code==200 else other
    assert client.get('/api/v1/organizations/'+org+'/memberships',headers=revoked_user['headers']).status_code==403


def test_operator_role_revoke_takes_effect_immediately(client,identities):
    user=mfa_user(identities);mod=identities('MODERATOR');row=register(client,user).json()
    assert claim(client,mod,row['case_id']).status_code==200
    with transaction() as conn:
        conn.execute(table('platform_role_grants').update().where(table('platform_role_grants').c.user_id==mod['user_id']).values(revoked_at=now()))
    assert decide(client,mod,row['case_id']).status_code==403
    assert client.get('/api/v1/operator/verification-cases',headers=mod['headers']).status_code==403


def test_normalized_tax_unique_constraint_and_submission_scope(client,identities):
    user=mfa_user(identities);row=register(client,user).json()
    with pytest.raises(IntegrityError),transaction() as conn:
        insert_row(conn,'organizations',tax_id='123 456 789',legal_name='Duplicate',public_name='Duplicate',region='Tashkent',status='PENDING_VERIFICATION')
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(submissions.insert().values(case_id=row['case_id'],revision=2,organization_id=str(uuid4()),proposed_fields={},created_at=now()))


def test_two_business_day_target_skips_weekend(monkeypatch):
    from app.services import organizations
    monkeypatch.setattr(organizations,'now',lambda:datetime(2026,11,6,5,0,tzinfo=timezone.utc))
    assert due_date().date().isoformat()=='2026-11-10'


def test_suspended_requester_cannot_receive_owner_grant(client,identities):
    user=mfa_user(identities);mod=identities('MODERATOR');row=register(client,user).json()
    assert claim(client,mod,row['case_id']).status_code==200
    with transaction() as conn:
        conn.execute(table('users').update().where(table('users').c.id==user['user_id']).values(status='SUSPENDED'))
    assert decide(client,mod,row['case_id']).status_code==409


def test_org_affiliated_moderator_cannot_review_another_requester(client,identities):
    user=mfa_user(identities);mod=identities('MODERATOR');row=register(client,user).json()
    joined=register(client,mod).json()
    assert joined['organization_id']==row['organization_id']
    assert claim(client,mod,row['case_id']).status_code==403


def test_capability_proof_for_another_org_is_not_authority(client,identities,organization):
    user=identities()
    with transaction() as conn:
        original=conn.execute(select(table('verification_cases')).where(table('verification_cases').c.organization_id==organization,
            table('verification_cases').c.kind=='JOB_EMPLOYER')).mappings().one()
        other=insert_row(conn,'organizations',tax_id='987654321',legal_name='Other',public_name='Other',region='Tashkent',status='VERIFIED')
        case=insert_row(conn,'verification_cases',requester_id=original['requester_id'],organization_id=other['id'],kind='JOB_EMPLOYER',
            status='APPROVED',assigned_reviewer_id=original['assigned_reviewer_id'],current_revision=1,due_at=now())
        conn.execute(table('organization_capabilities').update().where(table('organization_capabilities').c.organization_id==organization,
            table('organization_capabilities').c.capability=='JOB_EMPLOYER').values(approved_case_id=case['id']))
    with transaction() as conn,pytest.raises(GovernanceError):require_capability(conn,organization,'JOB_EMPLOYER')
    assert 'JOB_EMPLOYER' not in client.get('/api/v1/organizations/'+organization+'/public').json()['capabilities']


@pytest.mark.parametrize('method,path',[
    ('POST','/api/v1/organizations'),('GET','/api/v1/operator/verification-cases'),
    ('GET','/api/v1/organizations/'+str(uuid4())+'/verification'),
    ('GET','/api/v1/organizations/'+str(uuid4())+'/capabilities')])
def test_private_org_routes_require_session(client,method,path):
    assert client.request(method,path,json={}).status_code==401
