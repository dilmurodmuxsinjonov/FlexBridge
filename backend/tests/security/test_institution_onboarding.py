"""Actual HTTP claim intake; review/consent/grant acceptance is separate below."""
from datetime import date,timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.db.storage import table,transaction,now
from test_candidate import cv_fixture
from test_invitations import contact
from test_organizations import mfa_user
from test_regressions import count
from app.services.placements import insert_row


def first_claim(identities,*,mfa=True):
    user=mfa_user(identities) if mfa else identities()
    verified=contact(user,value=str(uuid4())+'@example.test',channel='EMAIL')
    document=cv_fixture(user);agreement=cv_fixture(user);today=date.today()
    body=dict(registry_code='INST-'+uuid4().hex[:12],name='Reviewed Academic Institution',region='Tashkent',
        document_file_id=document['id'],contact_id=verified['id'],valid_from=today.isoformat(),valid_to=(today+timedelta(days=365)).isoformat(),
        legal_basis='Institution assignment under the submitted academic agreement',file_ids=[document['id'],agreement['id']],evidence_note='Formal appointment and agreement provided for independent review',
        agreement_file_id=agreement['id'],agreement_valid_from=today.isoformat(),agreement_valid_to=(today+timedelta(days=365)).isoformat(),purposes=['ACADEMIC_VIEW'])
    return dict(user=user,contact=verified,document=document,agreement=agreement,body=body)


def submit(client,flow,**changes):
    return client.post('/api/v1/institution-appointments',headers={**flow['user']['headers'],'Idempotency-Key':'institution-first-request'},json={**flow['body'],**changes})


def test_first_claim_is_a_real_zero_grant_request_with_private_status_and_replay(client,identities):
    f=first_claim(identities)
    r=submit(client,f);assert r.status_code==202,r.text
    data=r.json();assert data['contract_id']=='API-096' and data['mode']=='FIRST_COORDINATOR'
    assert data['status']=='PENDING_REVIEW' and data['case_status']=='PENDING' and data['ever_activated'] is False
    assert count('institution_role_grants')==count('institution_memberships')==count('institution_onboarding_consents')==0
    assert count('institution_onboarding_requests')==count('institution_onboarding_submissions')==1
    me=client.get('/api/v1/auth/me',headers=f['user']['headers']);assert 'COORDINATOR' not in me.json()['roles']
    again=submit(client,f);assert again.status_code==202,again.text
    assert again.json()['id']==data['id'] and count('institution_onboarding_requests')==1
    own=client.get('/api/v1/institution-appointments/'+data['id'],headers=f['user']['headers']);assert own.status_code==200,own.text
    stranger=identities()
    assert client.get('/api/v1/institution-appointments/'+data['id'],headers=stranger['headers']).status_code==403
    for key in ('evidence','submissions','target_contact_digest','target_user_id'):
        assert key not in own.json()
    with transaction() as conn:
        case=conn.execute(select(table('verification_cases')).where(table('verification_cases').c.id==data['case_id'])).mappings().one()
        assert case['appointment_id']==data['id'] and case['institution_id'] is None and case['organization_id'] is None
        assert conn.execute(select(table('institutions').c.status)).scalar_one()=='PENDING_VERIFICATION'


def test_ungranted_password_user_can_read_generic_options_but_cannot_submit(client,identities):
    f=first_claim(identities,mfa=False)
    options=client.get('/api/v1/institution-onboarding/options',headers=f['user']['headers']);assert options.status_code==200,options.text
    assert options.json()['contract_id']=='API-017' and 'institutions' not in options.json()
    r=submit(client,f);assert r.status_code==403,r.text
    assert count('institutions')==count('institution_onboarding_requests')==0


@pytest.mark.parametrize('change',['role_flag','unverified_contact','foreign_file','unverified_file','expired_dates'])
def test_claim_validation_does_not_leave_pending_institution_or_grant(client,identities,change):
    f=first_claim(identities);body={}
    if change=='role_flag':body['roles']=['COORDINATOR']
    elif change=='foreign_file':
        foreign=cv_fixture(identities());body['document_file_id']=foreign['id'];body['file_ids']=[foreign['id'],f['agreement']['id']]
    elif change=='expired_dates':body['valid_to']=(date.today()-timedelta(days=1)).isoformat()
    else:
        with transaction() as conn:
            if change=='unverified_contact':
                t=table('user_contacts');conn.execute(t.update().where(t.c.id==f['contact']['id']).values(verified_at=None))
            else:
                t=table('files');conn.execute(t.update().where(t.c.id==f['document']['id']).values(scan_status='QUARANTINED'))
    r=submit(client,f,**body);assert r.status_code in (403,409,422),r.text
    assert count('institutions')==count('institution_onboarding_requests')==count('institution_role_grants')==0


def test_anonymous_options_and_claim_are_denied(client,identities):
    f=first_claim(identities)
    assert client.get('/api/v1/institution-onboarding/options').status_code==401
    assert client.post('/api/v1/institution-appointments',json=f['body'],headers={'Idempotency-Key':'anonymous-attempt'}).status_code==401
    assert count('institutions')==0


def accept(client,f,appointment,*,user=None,revision=1,contact_id=None):
    return client.post('/api/v1/institution-appointments/'+appointment+'/consent',headers=(user or f['user'])['headers'],json={
        'expected_revision':revision,'decision':'ACCEPT','contact_id':contact_id or f['contact']['id']})


def claim(client,moderator,case):
    return client.post('/api/v1/operator/verification-cases/'+case+'/claim',headers=moderator['headers'])


def decide(client,moderator,case,decision='APPROVE',revision=1):
    return client.post('/api/v1/operator/verification-cases/'+case+'/decide',headers=moderator['headers'],json={
        'expected_revision':revision,'decision':decision,'reason':'Independent review of formal appointment and agreement evidence'})


@pytest.mark.parametrize('consent_first',[True,False])
def test_first_coordinator_requires_both_independent_review_and_exact_named_consent(client,identities,consent_first):
    f=first_claim(identities);r=submit(client,f);assert r.status_code==202,r.text
    appointment=r.json()['id'];case=r.json()['case_id'];moderator=identities('MODERATOR')
    if consent_first:
        consent=accept(client,f,appointment);assert consent.status_code==200,consent.text
        assert count('institution_role_grants')==0
    claimed=claim(client,moderator,case);assert claimed.status_code==200,claimed.text
    reviewed=decide(client,moderator,case);assert reviewed.status_code==200,reviewed.text
    if not consent_first:
        assert count('institution_role_grants')==0
        assert reviewed.json()['status']=='APPROVED_PENDING_ACCEPT'
        consent=accept(client,f,appointment);assert consent.status_code==200,consent.text
    assert count('institution_role_grants')==count('institution_memberships')==1
    status=client.get('/api/v1/institution-appointments/'+appointment,headers=f['user']['headers']);assert status.status_code==200,status.text
    assert status.json()['status']=='ACTIVE' and status.json()['ever_activated']
    assert 'COORDINATOR' in client.get('/api/v1/auth/me',headers=f['user']['headers']).json()['roles']
    before=count('audit_events')
    assert accept(client,f,appointment).status_code==200
    assert decide(client,moderator,case).status_code==200
    assert count('audit_events')==before and count('institution_role_grants')==1
    with transaction() as conn:
        assert conn.execute(select(table('institutions').c.status)).scalar_one()=='VERIFIED'
        assert conn.execute(select(table('institution_agreements').c.status)).scalar_one()=='ACTIVE'


def active_coordinator(client,identities):
    f=first_claim(identities);r=submit(client,f);assert r.status_code==202,r.text
    moderator=identities('MODERATOR');case=r.json()['case_id'];appointment=r.json()['id']
    assert accept(client,f,appointment).status_code==200
    assert claim(client,moderator,case).status_code==200
    response=decide(client,moderator,case);assert response.status_code==200,response.text
    f.update(appointment=appointment,case=case,moderator=moderator,institution_id=r.json()['institution_id'])
    with transaction() as conn:f['agreement_id']=conn.execute(select(table('institution_agreements').c.id)).scalar_one()
    return f


def staff_claim(client,f,teacher,extra_file_ids=()):
    verified=contact(teacher,value=str(uuid4())+'@example.test',channel='EMAIL');document=cv_fixture(f['user'])
    body=dict(registry_code=f['body']['registry_code'],document_file_id=document['id'],contact_id=f['contact']['id'],
        valid_from=date.today().isoformat(),valid_to=(date.today()+timedelta(days=90)).isoformat(),legal_basis='Teacher appointment under the reviewed institution agreement',
        file_ids=[document['id'],*extra_file_ids],evidence_note='Teacher formal appointment for independent platform review',agreement_id=f['agreement_id'],
        target_channel='EMAIL',target_destination=verified['normalized_value'])
    r=client.post('/api/v1/institution-appointments',headers={**f['user']['headers'],'Idempotency-Key':'institution-teacher-request'},json=body)
    assert r.status_code==202,r.text
    return r.json(),verified,body


def test_existing_coordinator_requests_named_teacher_without_granting_coordinator(client,identities):
    f=active_coordinator(client,identities);teacher=identities();request,verified,body=staff_claim(client,f,teacher)
    assert request['mode']=='STAFF_TEACHER' and request['requested_role']=='TEACHER'
    assert count('institution_role_grants')==1
    inbox=client.get('/api/v1/me/institution-appointments',headers=teacher['headers']);assert inbox.status_code==200,inbox.text
    assert [item['id'] for item in inbox.json()['items']]==[request['id']]
    assert accept(client,f,request['id']).status_code==403
    accepted=accept(client,f,request['id'],user=teacher,contact_id=verified['id']);assert accepted.status_code==200,accepted.text
    assert count('institution_role_grants')==1
    assert claim(client,f['moderator'],request['case_id']).status_code==200
    result=decide(client,f['moderator'],request['case_id']);assert result.status_code==200,result.text
    assert result.json()['status']=='ACTIVE' and count('institution_role_grants')==2
    me=client.get('/api/v1/auth/me',headers=teacher['headers']);assert me.status_code==200,me.text
    assert 'TEACHER' in me.json()['roles'] and 'COORDINATOR' not in me.json()['roles']


def test_independent_reviewer_and_private_queue_dispatch(client,identities):
    f=first_claim(identities);r=submit(client,f);assert r.status_code==202,r.text
    case=r.json()['case_id'];moderator=identities('MODERATOR');other=identities('MODERATOR')
    # Actual MFA requester also receives a trusted moderator fixture grant.
    with transaction() as conn:
        roles=table('role_catalog');rid=conn.execute(select(roles.c.id).where(roles.c.code=='MODERATOR',roles.c.scope_kind=='PLATFORM')).scalar_one()
        insert_row(conn,'platform_role_grants',user_id=f['user']['user_id'],role_id=rid,granted_by_id=moderator['user_id'],expires_at=now()+timedelta(hours=1))
    assert claim(client,f['user'],case).status_code==403
    queue=client.get('/api/v1/operator/verification-cases?unassigned=true',headers=moderator['headers']);assert queue.status_code==200,queue.text
    assert case in [item['id'] for item in queue.json()['items']]
    assert claim(client,moderator,case).status_code==200
    assert claim(client,other,case).status_code==403
    detail=client.get('/api/v1/operator/verification-cases/'+case,headers=moderator['headers']);assert detail.status_code==200,detail.text
    assert detail.json()['case']['appointment_id']==r.json()['id']
    assert client.get('/api/v1/operator/verification-cases/'+case,headers=other['headers']).status_code==403
    assert client.get('/api/v1/operator/verification-cases/'+case,headers=f['user']['headers']).status_code==403


def test_needs_info_resubmission_preserves_history_and_requires_new_consent(client,identities):
    f=first_claim(identities);created=submit(client,f);assert created.status_code==202,created.text
    appointment,case=created.json()['id'],created.json()['case_id'];moderator=identities('MODERATOR')
    assert accept(client,f,appointment).status_code==200
    assert claim(client,moderator,case).status_code==200
    response=decide(client,moderator,case,'NEEDS_INFO');assert response.status_code==200,response.text
    original_due=response.json()['due_at']
    body={**f['body'],'expected_revision':1,'evidence_note':'Additional appointment evidence after independent reviewer feedback'}
    revised=client.post('/api/v1/institution-appointments/'+appointment+'/revisions',headers=f['user']['headers'],json=body)
    assert revised.status_code==202,revised.text
    assert revised.json()['revision']==2 and revised.json()['due_at']==original_due
    assert count('institution_onboarding_submissions')==2 and count('institution_onboarding_consents')==1
    replay=client.post('/api/v1/institution-appointments/'+appointment+'/revisions',headers=f['user']['headers'],json=body)
    assert replay.status_code==202,replay.text
    assert count('institution_onboarding_submissions')==2
    reviewed=decide(client,moderator,case,revision=2);assert reviewed.status_code==200,reviewed.text
    assert reviewed.json()['status']=='APPROVED_PENDING_ACCEPT' and count('institution_role_grants')==0
    assert accept(client,f,appointment,revision=1).status_code==409
    accepted=accept(client,f,appointment,revision=2);assert accepted.status_code==200,accepted.text
    assert accepted.json()['status']=='ACTIVE' and count('institution_role_grants')==1
    with transaction() as conn:
        outcomes=conn.execute(select(table('institution_onboarding_decisions').c.decision).order_by(table('institution_onboarding_decisions').c.revision)).scalars().all()
        assert outcomes==['NEEDS_INFO','APPROVE']
        assert conn.execute(select(table('verification_evidence').c.revision).distinct().order_by(table('verification_evidence').c.revision)).scalars().all()==[1,2]


def test_revocation_closes_current_rights_and_replays_never_resurrect_grants(client,identities):
    f=active_coordinator(client,identities)
    before=count('audit_events')
    r=client.post('/api/v1/institution-appointments/'+f['appointment']+'/revoke',headers=f['user']['headers'],json={'reason':'Personal withdrawal of this formal institution appointment'})
    assert r.status_code==200,r.text
    assert r.json()['status']=='REVOKED'
    with transaction() as conn:
        original=conn.execute(select(table('institution_role_grants'))).mappings().one()
        assert original['revoked_at'] is not None
    assert 'COORDINATOR' not in client.get('/api/v1/auth/me',headers=f['user']['headers']).json()['roles']
    assert accept(client,f,f['appointment']).status_code==200
    assert decide(client,f['moderator'],f['case']).status_code==200
    again=client.post('/api/v1/institution-appointments/'+f['appointment']+'/revoke',headers=f['user']['headers'],json={'reason':'Personal withdrawal of this formal institution appointment'})
    assert again.status_code==200,again.text
    assert count('audit_events')==before+1
    with transaction() as conn:
        current=conn.execute(select(table('institution_role_grants'))).mappings().one()
        assert current['id']==original['id'] and current['revoked_at']==original['revoked_at']
    # A fresh key must not turn the known verified institution into first bootstrap.
    retry=client.post('/api/v1/institution-appointments',headers={**f['user']['headers'],'Idempotency-Key':'new-bootstrap-attempt'},json=f['body'])
    assert retry.status_code in (403,409,422),retry.text
    assert count('institutions')==count('institution_onboarding_requests')==count('institution_role_grants')==1


def test_named_teacher_can_view_only_current_appointment_and_agreement_files(client,identities,monkeypatch):
    from app.adapters import storage
    f=active_coordinator(client,identities);teacher=identities();extra=cv_fixture(f['user'])
    request,verified,body=staff_claim(client,f,teacher,extra_file_ids=[extra['id']])
    calls=[]
    def presign(key):calls.append(key);return 'https://storage.example.test/temporary-object'
    monkeypatch.setattr(storage,'presign_get',presign)
    status=client.get('/api/v1/institution-appointments/'+request['id'],headers=teacher['headers']);assert status.status_code==200,status.text
    proposal=status.json()['proposal'];assert proposal['legal_basis']==body['legal_basis']
    assert len(proposal['files'])==2 and 'storage_key' not in str(proposal)
    path=proposal['files'][0]['download_path']
    stranger=identities()
    assert client.get(path,headers=stranger['headers']).status_code==403 and calls==[]
    response=client.get(path,headers=teacher['headers']);assert response.status_code==200,response.text
    assert response.json()['expires_in_seconds']==60 and len(calls)==1
    unrelated=cv_fixture(f['user'])
    assert client.get('/api/v1/institution-appointments/'+request['id']+'/files/'+unrelated['id']+'/download',headers=teacher['headers']).status_code==403
    assert len(calls)==1
    extra_path='/api/v1/institution-appointments/'+request['id']+'/files/'+extra['id']+'/download'
    assert client.get(extra_path,headers=teacher['headers']).status_code==403 and len(calls)==1
    assert client.get(extra_path,headers=f['user']['headers']).status_code==200 and len(calls)==2
