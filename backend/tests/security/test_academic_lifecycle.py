"""Academic consent continuity, rollback and current authority at actual HTTP boundaries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select,text

from app.db.storage import get_engine,table,transaction,now
from app.db.institution_scope import TASHKENT
from app.services.academic_admission import academic_service
from app.services.enrollments import enrollment_service
from app.services.placements import get_row,insert_row
from test_academic_admission import pending_http,nominate,plan,accept_candidate_mentor
from test_admission_lifecycle import terms_request,publish
from test_internship_admission import post
from test_org_authority_transactions import wait_for_blocker
from test_regressions import count
from test_candidate import cv_fixture
from test_institution_authority import setup_scope
from test_organizations import actor


def teacher_accept(client,f,a,p,**extra):
    body={**terms_request(p),'assignment_kind':'TEACHER',**extra}
    url='/api/v1/placements/'+f['placement']['id']+'/assignments/'+a['id']+'/accept'
    return url,body,client.post(url,headers=f['teacher']['headers'],json=body)


@pytest.mark.parametrize('retire_old_appointment',[False,True])
def test_teacher_regrant_cannot_revive_original_assignment(client,identities,organization,retire_old_appointment):
    f=pending_http(client,identities,organization);a=nominate(client,f);p=plan(client,f)
    accept_candidate_mentor(client,f,p)
    _,_,accepted=teacher_accept(client,f,a,p);assert accepted.status_code==200,accepted.text
    with transaction() as conn:
        conn.execute(table('institution_role_grants').update().where(table('institution_role_grants').c.id==f['teacher_grant']['id']).values(revoked_at=now()))
        appointment=f['teacher_appointment']
        if retire_old_appointment:
            conn.execute(table('institution_appointments').update().where(table('institution_appointments').c.id==appointment['id']).values(status='REVOKED'))
        # Grant history has an unconditional membership/role/appointment unique key:
        # restoration requires a new formal appointment, even if the old one is active.
        appointment=insert_row(conn,'institution_appointments',institution_id=f['inst']['id'],user_id=f['teacher']['user_id'],
            document_file_id=appointment['document_file_id'],status='ACTIVE',valid_from=now().astimezone(TASHKENT).date(),accepted_at=now())
        insert_row(conn,'institution_role_grants',membership_id=f['teacher_member']['id'],role_id=f['teacher_grant']['role_id'],appointment_id=appointment['id'])
        assert not conn.execute(text('SELECT flexbridge.academic_teacher_current(:a,:t)'),{'a':a['id'],'t':p['terms_id']}).scalar_one()
    _,_,denied=teacher_accept(client,f,a,p);assert denied.status_code==403,denied.text
    inbox=client.get('/api/v1/me/academic-assignments',headers=f['teacher']['headers'])
    assert inbox.status_code==200 and inbox.json()['items']==[],inbox.text
    base='/api/v1/placements/'+f['placement']['id']
    denied=client.post(base+'/host-decisions',headers=f['owner']['headers'],json={**terms_request(p),'action':'ACTIVATE'})
    assert denied.status_code==409,denied.text
    post(client,'/api/v1/academic-assignments/'+a['id']+'/revoke',f['coord'],{'idempotency_key':str(uuid4())},200)
    fresh=nominate(client,f);assert fresh['id']!=a['id']
    _,_,accepted=teacher_accept(client,f,fresh,p);assert accepted.status_code==200,accepted.text
    post(client,base+'/host-decisions',f['owner'],{**terms_request(p),'action':'ACTIVATE'},200)


def test_new_plan_requires_fresh_teacher_consent_and_preserves_historical_receipt(client,identities,organization):
    f=pending_http(client,identities,organization);a=nominate(client,f);p=plan(client,f)
    url,body,accepted=teacher_accept(client,f,a,p);assert accepted.status_code==200,accepted.text
    accept_candidate_mentor(client,f,p)
    new=publish(client,f['owner'],{'id':f['placement']['id'],'current_terms_id':p['terms_id'],'version':p['version']})
    assert new['version']==p['version']+1
    assert plan(client,f)['academic_scope']==p['academic_scope']
    assert client.post(url,headers=f['teacher']['headers'],json=body).json()==accepted.json()
    stale=client.post(url,headers=f['teacher']['headers'],json={**body,'idempotency_key':str(uuid4())})
    assert stale.status_code==409,stale.text
    base='/api/v1/placements/'+f['placement']['id']
    post(client,base+'/accept',f['candidate'],terms_request(new),200)
    with transaction() as conn:
        mentor=dict(conn.execute(select(table('mentor_assignments'))).mappings().one())
    post(client,base+'/assignments/'+mentor['id']+'/accept',f['owner'],terms_request(new),200)
    denied=client.post(base+'/host-decisions',headers=f['owner']['headers'],json={**terms_request(new),'action':'ACTIVATE'})
    assert denied.status_code==409,denied.text
    _,_,accepted=teacher_accept(client,f,a,new);assert accepted.status_code==200,accepted.text
    post(client,base+'/host-decisions',f['owner'],{**terms_request(new),'action':'ACTIVATE'},200)
    assert count('academic_assignment_consents')==2


def test_nomination_audit_failure_rolls_back_new_school_binding_and_plan(client,identities,organization,monkeypatch):
    f=pending_http(client,identities,organization);before=count('audit_events')
    events_before=count('outbox_events')
    append=academic_service.audit.append_audit_event
    def fail(**kwargs):
        if kwargs['action']=='ACADEMIC_ASSIGNMENT_CREATED':raise RuntimeError('Nomination audit unavailable')
        return append(**kwargs)
    monkeypatch.setattr(academic_service.audit,'append_audit_event',fail)
    response=client.post('/api/v1/placements/'+f['placement']['id']+'/academic-assignments',headers=f['coord']['headers'],json=dict(
        institution_id=f['inst']['id'],supervision_id=f['supervision']['id'],supervisor_id=f['teacher_member']['id'],idempotency_key=str(uuid4())))
    assert response.status_code==503,response.text
    assert count('academic_assignments')==0 and count('placement_academic_bindings')==0
    assert count('academic_assignment_proofs')==0 and count('placement_terms')==1 and count('audit_events')==before
    assert count('outbox_events')==events_before
    with transaction() as conn:
        p=get_row(conn,'placements',f['placement']['id'])
        assert not p['academic_track'] and p['enrollment_id'] is None and p['current_terms_id']==f['placement']['current_terms_id']


@pytest.mark.parametrize('change',['session','grant','appointment','account_version'])
def test_teacher_acceptance_rechecks_authority_after_business_lock_wait(client,identities,organization,change):
    f=pending_http(client,identities,organization);a=nominate(client,f);p=plan(client,f)
    before=count('audit_events')
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as blocker:
            blocker.execute(select(table('institutions')).where(table('institutions').c.id==f['inst']['id']).with_for_update())
            pid=blocker.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(teacher_accept,client,f,a,p);wait_for_blocker(pid)
            with transaction() as conn:
                if change=='session':name,key,values='sessions',f['teacher']['session_id'],{'revoked_at':now()}
                elif change=='grant':name,key,values='institution_role_grants',f['teacher_grant']['id'],{'revoked_at':now()}
                elif change=='appointment':name,key,values='institution_appointments',f['teacher_appointment']['id'],{'status':'REVOKED'}
                else:name,key,values='users',f['teacher']['user_id'],{'auth_version':get_row(conn,'users',f['teacher']['user_id'])['auth_version']+1}
                t=table(name);conn.execute(t.update().where(t.c.id==key).values(**values))
        _,_,response=pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert count('academic_assignment_consents')==0 and count('audit_events')==before
    with transaction() as conn:assert get_row(conn,'academic_assignments',a['id'])['accepted_at'] is None


def test_cleanup_after_agreement_expiry_and_start_replay_cannot_restart_cancelled_placement(client,identities,organization):
    f=pending_http(client,identities,organization);a=nominate(client,f);p=plan(client,f)
    accept_candidate_mentor(client,f,p)
    _,_,accepted=teacher_accept(client,f,a,p);assert accepted.status_code==200,accepted.text
    base='/api/v1/placements/'+f['placement']['id']
    body={**terms_request(p),'action':'ACTIVATE'}
    receipt=post(client,base+'/host-decisions',f['owner'],body,200)
    post(client,base+'/host-decisions',f['owner'],{**terms_request(p),'action':'CANCEL'},200)
    with transaction() as conn:
        conn.execute(table('institution_agreements').update().where(table('institution_agreements').c.id==f['agreement']['id'])
            .values(valid_to=now().astimezone(TASHKENT).date()-timedelta(days=1)))
    revoke_url='/api/v1/academic-assignments/'+a['id']+'/revoke';key={'idempotency_key':str(uuid4())}
    revoked=post(client,revoke_url,f['coord'],key,200)
    assert post(client,revoke_url,f['coord'],key,200)==revoked
    assert post(client,base+'/host-decisions',f['owner'],body,200)==receipt
    assert plan(client,f)['status']=='CANCELLED'
    assert count('academic_assignment_events')==1


def test_candidate_with_formal_teacher_role_cannot_be_nominated_to_own_placement(client,identities,organization):
    f=pending_http(client,identities,organization)
    with transaction() as conn:
        member=insert_row(conn,'institution_memberships',institution_id=f['inst']['id'],user_id=f['candidate']['user_id'],status='ACTIVE',accepted_at=now())
        appointment=insert_row(conn,'institution_appointments',institution_id=f['inst']['id'],user_id=f['candidate']['user_id'],
            document_file_id=f['teacher_appointment']['document_file_id'],status='ACTIVE',valid_from=now().astimezone(TASHKENT).date(),accepted_at=now())
        insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=f['teacher_grant']['role_id'],appointment_id=appointment['id'])
    before=count('audit_events')
    response=client.post('/api/v1/placements/'+f['placement']['id']+'/academic-assignments',headers=f['coord']['headers'],json=dict(
        institution_id=f['inst']['id'],supervision_id=f['supervision']['id'],supervisor_id=member['id'],idempotency_key=str(uuid4())))
    assert response.status_code==403 and response.json()['detail']['code']=='SELF_ASSIGNMENT_FORBIDDEN',response.text
    assert count('academic_assignments')==0 and count('placement_academic_bindings')==0 and count('audit_events')==before


@pytest.mark.parametrize('wrong_actor',['candidate','coord','owner'])
def test_other_party_cannot_give_named_teachers_personal_consent(client,identities,organization,wrong_actor):
    f=pending_http(client,identities,organization);a=nominate(client,f);p=plan(client,f)
    response=client.post('/api/v1/placements/'+f['placement']['id']+'/assignments/'+a['id']+'/accept',headers=f[wrong_actor]['headers'],
        json={**terms_request(p),'assignment_kind':'TEACHER'})
    assert response.status_code==403,response.text
    assert count('academic_assignment_consents')==0


def test_latest_personal_school_choice_prevents_other_school_binding(client,identities,organization):
    f=pending_http(client,identities,organization)
    coord,_,inst,_,_,_,_=setup_scope(identities)
    candidate=f['candidate'];evidence=cv_fixture(candidate);reviewer=identities('MODERATOR')
    enrollment=enrollment_service.create(actor(candidate),institution_id=inst['id'],idempotency_key=str(uuid4()),program='Second institution',
        start_date=now().astimezone(TASHKENT).date()-timedelta(days=10),end_date=None,file_ids=[evidence['id']],evidence_note='Independent second-school enrollment evidence.')
    enrollment_service.claim(actor(reviewer),enrollment['case_id'])
    enrollment_service.decide(actor(reviewer),enrollment['case_id'],decision='APPROVE',expected_revision=1,reason='Independent second-school fixture review.')
    teacher=identities()
    with transaction() as conn:
        agreement=insert_row(conn,'institution_agreements',institution_id=inst['id'],version=1,status='ACTIVE',
            valid_from=now().astimezone(TASHKENT).date()-timedelta(days=10),purposes=['ACADEMIC_VIEW'])
        member=insert_row(conn,'institution_memberships',institution_id=inst['id'],user_id=teacher['user_id'],status='ACTIVE',accepted_at=now())
        appointment=insert_row(conn,'institution_appointments',institution_id=inst['id'],user_id=teacher['user_id'],
            document_file_id=f['teacher_appointment']['document_file_id'],status='ACTIVE',valid_from=now().astimezone(TASHKENT).date(),accepted_at=now())
        insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=f['teacher_grant']['role_id'],appointment_id=appointment['id'])
    supervision=post(client,'/api/v1/student-supervisions',coord,dict(institution_id=inst['id'],enrollment_id=enrollment['id'],agreement_id=agreement['id'],
        purpose='ACADEMIC_VIEW',legal_basis='Second institution agreement.',idempotency_key=str(uuid4())),201)
    base='/api/v1/placements/'+f['placement']['id']
    body={**terms_request(f['placement']),'enrollment_id':enrollment['id']}
    choice=post(client,base+'/academic-requests',candidate,body,201);assert choice['revision']==2
    assert post(client,base+'/academic-requests',candidate,body,201)==choice
    response=client.post(base+'/academic-assignments',headers=f['coord']['headers'],json=dict(institution_id=f['inst']['id'],
        supervision_id=f['supervision']['id'],supervisor_id=f['teacher_member']['id'],idempotency_key=str(uuid4())))
    assert response.status_code==403 and response.json()['detail']['code']=='STUDENT_SCHOOL_CHOICE_REQUIRED',response.text
    assert count('placement_academic_bindings')==0
    post(client,base+'/academic-assignments',coord,dict(institution_id=inst['id'],supervision_id=supervision['id'],supervisor_id=member['id'],idempotency_key=str(uuid4())),201)
    assert plan(client,f)['academic_scope']['institution_id']==inst['id']
