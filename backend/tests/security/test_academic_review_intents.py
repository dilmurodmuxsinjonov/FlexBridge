"""Additional actual-session cross-placement intent and revoked receipt controls."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app.db.storage import table, transaction, now
from app.db.institution_scope import TASHKENT
from app.services.placements import insert_row
from app.services.placements import get_row
from test_academic_admission import pending_http
from test_academic_reviews import ready, body, send
from test_academic_views import active_revision
from test_candidate import cv_fixture
from test_internship_admission import post
from test_regressions import count
from test_academic_migration import legacy_academic
from test_institution_migration import populated_database
from academic_review_observer import labeled_requests,wait_for_requests
from app.db.storage import get_engine
from sqlalchemy import text


def test_one_teacher_key_cannot_commit_different_intent_on_two_placements(client, identities, organization,record_testsuite_property):
    first = pending_http(client,identities,organization)
    # Distinct institutions AND hosts avoid accidentally serializing this case
    # on a shared organization lock before the actor/key intent lock.
    with transaction() as conn:
        host = insert_row(conn,'organizations',tax_id=str(uuid4()),legal_name='Second trusted host',
            public_name='Second trusted host',region='Tashkent',status='VERIFIED')
        case = insert_row(conn,'verification_cases',requester_id=first['owner']['user_id'],organization_id=host['id'],
            kind='INTERNSHIP_HOST',status='APPROVED',current_revision=1,assigned_reviewer_id=first['coord']['user_id'],
            due_at=now(),decided_at=now())
        insert_row(conn,'organization_capabilities',organization_id=host['id'],capability='INTERNSHIP_HOST',
            status='ACTIVE',approved_case_id=case['id'])
    second = pending_http(client,identities,host['id'])
    assert first['inst']['id'] != second['inst']['id'] and first['organization'] != second['organization']
    document = cv_fixture(first['teacher'])
    # Trusted formal school membership in the second institution. Personal
    # nomination/acceptance/start and both submissions below use actual HTTP.
    with transaction() as conn:
        member = insert_row(conn,'institution_memberships',institution_id=second['inst']['id'],
            user_id=first['teacher']['user_id'],status='ACTIVE',accepted_at=now())
        appointment = insert_row(conn,'institution_appointments',institution_id=second['inst']['id'],
            user_id=first['teacher']['user_id'],document_file_id=document['id'],status='ACTIVE',
            valid_from=now().astimezone(TASHKENT).date(),accepted_at=now())
        grant = insert_row(conn,'institution_role_grants',membership_id=member['id'],
            role_id=second['teacher_grant']['role_id'],appointment_id=appointment['id'])
    second.update(teacher=first['teacher'],teacher_member=member,teacher_appointment=appointment,teacher_grant=grant)
    cases = []
    key = str(uuid4())
    for f in (first,second):
        assignment,draft = active_revision(client,f)
        post(client,'/api/v1/logs/' + draft['id'] + '/submit',f['candidate'],{},200)
        cases.append((f,draft,{**body(assignment),'idempotency_key':key}))
    labels=['cross-host-'+str(uuid4())+'-'+str(i) for i in range(2)]
    with labeled_requests(get_engine()) as call,ThreadPoolExecutor(max_workers=2) as pool:
        with get_engine().begin() as holder:
            holder.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                {'key':'academic-review:'+first['teacher']['user_id']+':'+key})
            futures=[pool.submit(call,label,send,client,*case) for label,case in zip(labels,cases)]
            observed=wait_for_requests(get_engine(),labels,intent_only=True)
            assert len({row['pid'] for row in observed})==2
            import json
            record_testsuite_property('cross_host_actor_key_overlap',json.dumps(observed))
        responses=[future.result(timeout=30) for future in futures]
    assert sorted(r.status_code for r in responses) == [201,409],[r.text for r in responses]
    rejected = next(r for r in responses if r.status_code == 409)
    assert rejected.json()['detail']['code'] == 'IDEMPOTENCY_KEY_REUSED'
    assert count('academic_log_reviews') == count('academic_review_proofs') == 1


def test_reappointed_teacher_cannot_replay_receipt_from_revoked_original_grant(client, identities, organization):
    f,assignment,draft = ready(client,identities,organization);payload = body(assignment)
    first = send(client,f,draft,payload);assert first.status_code == 201,first.text
    with transaction() as conn:
        grants = table('institution_role_grants')
        conn.execute(grants.update().where(grants.c.id == f['teacher_grant']['id']).values(revoked_at=now()))
        appointment = insert_row(conn,'institution_appointments',institution_id=f['inst']['id'],user_id=f['teacher']['user_id'],
            document_file_id=f['teacher_appointment']['document_file_id'],status='ACTIVE',
            valid_from=now().astimezone(TASHKENT).date(),accepted_at=now())
        insert_row(conn,'institution_role_grants',membership_id=f['teacher_member']['id'],
            role_id=f['teacher_grant']['role_id'],appointment_id=appointment['id'])
    response = send(client,f,draft,payload)
    assert response.status_code == 403,response.text
    assert response.json()['detail']['code'] == 'ORIGINAL_TEACHER_AUTHORITY_REQUIRED'
    assert count('academic_log_reviews') == count('academic_review_proofs') == 1


def test_foreign_revision_does_not_take_authority_from_another_assignment(client, identities, organization):
    f,assignment,draft = ready(client,identities,organization)
    other,_,foreign = ready(client,identities,organization)
    response = send(client,f,foreign,body(assignment))
    assert response.status_code == 403,response.text
    response = client.post('/api/v1/log-revisions/'+draft['current_revision_id']+'/academic-reviews',
        json=body(assignment))
    assert response.status_code == 401,response.text
    response = client.post('/api/v1/internship-logs/daily-logs/'+draft['id']+'/academic-reviews',json={
        **body(assignment),'placement_id':f['placement']['id'],'expected_revision_id':draft['current_revision_id']})
    assert response.status_code == 401,response.text
    assert count('academic_log_reviews') == count('academic_review_proofs') == 0


def test_populated_legacy_teacher_actual_session_can_read_but_cannot_write_without_plan_consent(monkeypatch):
    from fastapi.testclient import TestClient
    from app.db import storage
    from app.main import app
    from app.services.auth import auth_service,hash_password
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:
            f = legacy_academic(conn)
            p = get_row(conn,'placements',f['placement_id']);candidate = get_row(conn,'candidate_profiles',p['candidate_id'])
            log = insert_row(conn,'daily_logs',placement_id=p['id'],local_date=p['start_date'],version=1)
            revision = insert_row(conn,'log_revisions',daily_log_id=log['id'],revision=1,terms_id=f['terms_id'],
                author_id=candidate['user_id'],day_type='DAY_OFF',summary='Retained imported submitted diary',total_minutes=0,
                status='SUBMITTED',submitted_at=now(),idempotency_key=str(uuid4()))
            users = table('users')
            conn.execute(users.update().where(users.c.id == f['teacher_id']).values(password_hash=hash_password('legacy-teacher-passphrase-2026')))
        migrate('head')
        # The alternate database is disposable upgrade_* data. Restore the normal
        # fixture engine before that context disposes it; no dependency overrides.
        with monkeypatch.context() as patch:
            patch.setattr(storage,'_ENGINE',engine)
            session = auth_service.login(user_id=f['teacher_id'],password='legacy-teacher-passphrase-2026')
            headers = {'Authorization':'Bearer '+session['access_token']}
            with TestClient(app) as client:
                view = client.get('/api/v1/log-revisions/'+revision['id']+'/academic',headers=headers)
                assert view.status_code == 200,view.text
                assert view.json()['summary'] == 'Retained imported submitted diary'
                payload = dict(academic_assignment_id=f['assignment_id'],decision='REVIEWED',idempotency_key=str(uuid4()))
                for path,extra in (
                    ('/api/v1/log-revisions/'+revision['id']+'/academic-reviews',{}),
                    ('/api/v1/internship-logs/daily-logs/'+log['id']+'/academic-reviews',
                     {'placement_id':p['id'],'expected_revision_id':revision['id']})):
                    response = client.post(path,headers=headers,json={**payload,**extra})
                    assert response.status_code == 403,response.text
                    assert response.json()['detail']['code'] == 'TEACHER_PLAN_ACCEPTANCE_REQUIRED'
                assert count('academic_log_reviews') == count('academic_review_proofs') == 0
