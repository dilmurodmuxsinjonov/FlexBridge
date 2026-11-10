"""Actual fresh legacy teacher consent and local worker delivery after upgrade.

Pre-upgrade staff/documents/accounts/passwords are trusted import metadata, not
external identity proof. Actual sessions, HTTP consent/review and worker run normally.
"""
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import storage
from app.db.storage import table,transaction,now,enqueue
from app.main import app
from app.services.auth import auth_service,hash_password
from app.services.placements import get_row,insert_row
from app.services.academic_notices import run_notice,apply_notice
from app.workers.outbox import relay_pending_outbox_events
from test_academic_migration import legacy_academic
from test_institution_migration import populated_database

TOPIC='PLACEMENT_ACADEMIC_NOTICE'


@pytest.fixture
def legacy_http(monkeypatch,request):
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:
            f=legacy_academic(conn)
            if getattr(request,'param',None)=='other_assignment':
                original=get_row(conn,'academic_assignments',f['assignment_id'])
                other=insert_row(conn,'academic_assignments',placement_id=f['placement_id'],institution_id=f['institution_id'],
                    teacher_membership_id=f['teacher_member_id'],supervision_id=f['supervision_id'],
                    assigned_by_id=original['assigned_by_id'],assigned_at=now())
                f['other_assignment_id']=other['id']
            p=get_row(conn,'placements',f['placement_id']);candidate=get_row(conn,'candidate_profiles',p['candidate_id'])
            log=insert_row(conn,'daily_logs',placement_id=p['id'],local_date=p['start_date'],version=1)
            revision=insert_row(conn,'log_revisions',daily_log_id=log['id'],revision=1,terms_id=f['terms_id'],
                author_id=candidate['user_id'],day_type='DAY_OFF',summary='Retained imported work record',total_minutes=0,
                status='SUBMITTED',submitted_at=now(),idempotency_key=str(uuid4()))
            for uid in (f['teacher_id'],candidate['user_id']):
                conn.execute(table('users').update().where(table('users').c.id==uid).values(password_hash=hash_password('legacy-notice-fixture-passphrase')))
        migrate('head')
        with monkeypatch.context() as patch:
            patch.setattr(storage,'_ENGINE',engine)
            teacher=auth_service.login(user_id=f['teacher_id'],password='legacy-notice-fixture-passphrase')
            student=auth_service.login(user_id=candidate['user_id'],password='legacy-notice-fixture-passphrase')
            with TestClient(app) as client:
                yield f,client,{'Authorization':'Bearer '+teacher['access_token']},teacher['session_id'],{
                    'Authorization':'Bearer '+student['access_token']},revision


def accept(f,client,headers):
    url='/api/v1/placements/'+f['placement_id']+'/assignments/'+f['assignment_id']+'/accept'
    body=dict(terms_id=f['terms_id'],version=1,assignment_kind='TEACHER',idempotency_key=str(uuid4()))
    first=client.post(url,headers=headers,json=body)
    assert first.status_code==200,first.text
    again=client.post(url,headers=headers,json=body)
    assert again.status_code==200 and again.json()==first.json(),again.text
    assert first.json()['side']=='TEACHER'
    return first.json()


def inbox(client,headers):
    response=client.get('/api/v1/me/notifications',headers=headers)
    assert response.status_code==200,response.text
    return response.json()['items']


def test_fresh_personal_legacy_consent_review_and_logout_deliver_one_minimum_notice(legacy_http):
    f,client,teacher,session,student,revision=legacy_http
    with transaction() as conn:
        assert conn.execute(select(table('academic_assignment_consents'))).first() is None
        assert conn.execute(select(table('outbox_events'))).first() is None
    receipt=accept(f,client,teacher)
    review=client.post('/api/v1/log-revisions/'+revision['id']+'/academic-reviews',headers=teacher,json=dict(
        academic_assignment_id=f['assignment_id'],decision='REVIEWED',idempotency_key=str(uuid4())))
    assert review.status_code==201,review.text
    logout=client.delete('/api/v1/me/sessions/'+session,headers=teacher)
    assert logout.status_code==200,logout.text
    assert relay_pending_outbox_events(event_types=(TOPIC,))==1
    assert relay_pending_outbox_events(event_types=(TOPIC,))==0
    items=inbox(client,student);assert len(items)==1
    notice=items[0]['notice']
    assert notice['kind']=='ACCEPTED' and notice['teacher_user_id']==f['teacher_id']
    assert notice['assignment_id']==f['assignment_id'] and notice['terms_id']==f['terms_id']
    assert notice['historical'] is True and notice['current_authority_required'] is True
    assert not {'legal_basis','file_ids','enrollment_id','session_id','auth_version','salary_min'} & notice.keys()
    with transaction() as conn:
        proof=conn.execute(select(table('academic_assignment_proofs'))).mappings().one()
        assert proof['origin']=='LEGACY_IMPORT' and proof['receipt'] is None and proof['actor_id'] is None
        consent=conn.execute(select(table('academic_assignment_consents'))).mappings().one()
        assert consent['id']==receipt['consent_id'] and consent['session_id']==session


def test_imported_nomination_without_public_intent_cannot_fabricate_candidate_notice(legacy_http):
    f,client,teacher,session,student,revision=legacy_http
    with transaction() as conn:
        # Adversarial trusted SQL envelope, not a public way to create history.
        enqueue(conn,TOPIC,f['placement_id'],dict(kind='NOMINATED',placement_id=f['placement_id'],
            assignment_id=f['assignment_id'],evidence_id=f['assignment_id']),'forged-import-nomination:'+str(uuid4()))
    assert relay_pending_outbox_events(event_types=(TOPIC,))==0
    assert inbox(client,student)==[]
    with transaction() as conn:
        assert conn.execute(select(table('academic_assignment_consents'))).first() is None
        event=conn.execute(select(table('outbox_events'))).mappings().one()
        assert event['processed_at'] is None


@pytest.mark.parametrize('mode',['apply_failure','stale_fence'])
def test_retained_scope_new_notice_failure_and_retry_are_atomic(legacy_http,mode):
    f,client,teacher,session,student,revision=legacy_http;accept(f,client,teacher)
    def fail(conn,event,payload):
        apply_notice(conn,event,payload)
        raise RuntimeError('Injected after retained-scope inbox insert')
    def stale(event):
        with transaction() as conn:
            e=table('outbox_events');conn.execute(e.update().where(e.c.id==event['id']).values(claim_token=str(uuid4())))
        return run_notice(event)
    registry={TOPIC:(stale,apply_notice) if mode=='stale_fence' else (run_notice,fail)}
    assert relay_pending_outbox_events(event_types=(TOPIC,),registry=registry)==0
    assert inbox(client,student)==[]
    with transaction() as conn:
        e=table('outbox_events');event=conn.execute(select(e).where(e.c.event_type==TOPIC)).mappings().one()
        assert event['processed_at'] is None
        expired=now()-timedelta(seconds=1)
        conn.execute(e.update().where(e.c.id==event['id']).values(available_at=expired,lease_until=expired))
    assert relay_pending_outbox_events(event_types=(TOPIC,))==1
    assert len(inbox(client,student))==1


def test_retained_accepted_envelope_without_new_consent_cannot_create_notice(legacy_http):
    f,client,teacher,session,student,revision=legacy_http
    with transaction() as conn:
        enqueue(conn,TOPIC,f['placement_id'],dict(kind='ACCEPTED',placement_id=f['placement_id'],
            assignment_id=f['assignment_id'],evidence_id=str(uuid4())),'forged-missing-consent:'+str(uuid4()))
    assert relay_pending_outbox_events(event_types=(TOPIC,))==0
    assert inbox(client,student)==[]
    with transaction() as conn:
        assert conn.execute(select(table('academic_assignment_consents'))).first() is None
        assert conn.execute(select(table('outbox_events').c.processed_at)).scalar_one() is None


@pytest.mark.parametrize('legacy_http',['other_assignment'],indirect=True)
def test_retained_accepted_envelope_cannot_borrow_another_assignment_consent(legacy_http):
    f,client,teacher,session,student,revision=legacy_http;receipt=accept(f,client,teacher)
    with transaction() as conn:
        key='forged-other-consent:'+str(uuid4())
        # Both captured assignments have the same placement and original teacher/
        # grant/appointment. The second never acquired this personal consent.
        enqueue(conn,TOPIC,f['placement_id'],dict(kind='ACCEPTED',placement_id=f['placement_id'],
            assignment_id=f['other_assignment_id'],evidence_id=receipt['consent_id']),key)
    assert relay_pending_outbox_events(event_types=(TOPIC,))==1
    items=inbox(client,student)
    assert len(items)==1 and items[0]['notice']['assignment_id']==f['assignment_id']
    with transaction() as conn:
        e=table('outbox_events')
        assert conn.execute(select(e.c.processed_at).where(e.c.dedupe_key==key)).scalar_one() is None
