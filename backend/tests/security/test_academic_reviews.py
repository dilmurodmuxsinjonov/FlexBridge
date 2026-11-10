"""Actual-session academic feedback, durable replay and immutable SQL history.

Staff/document/publication metadata is trusted setup; admission and submission
use the real HTTP flow. Pointer advances model a future amendment, not its API.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from time import sleep
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db.storage import get_engine, table, transaction, now
from app.services.academic_reviews import academic_review_service
from app.services.academic_admission import snapshot
from app.services.placement_admission import evidence
from app.services.placements import get_row, insert_row
from test_academic_admission import pending_http, plan
from test_academic_views import active_revision
from test_admission_lifecycle import terms_request
from test_internship_admission import post
from test_regressions import count
from test_org_authority_transactions import wait_for_blocker
from test_organizations import actor
from academic_review_observer import labeled_requests,wait_for_requests


def ready(client, identities, organization, *, submit=True):
    f = pending_http(client, identities, organization)
    assignment, draft = active_revision(client, f)
    if submit:
        post(client, '/api/v1/logs/' + draft['id'] + '/submit', f['candidate'], {}, 200)
    return f, assignment, draft


def body(assignment, **extra):
    return dict(academic_assignment_id=assignment['id'], decision='REVIEWED', comment='Independent academic feedback.',
                idempotency_key=str(uuid4()), **extra)


def send(client, f, draft, payload, *, user=None):
    return client.post('/api/v1/log-revisions/' + draft['current_revision_id'] + '/academic-reviews',
                       headers=(user or f['teacher'])['headers'], json=payload)


@pytest.mark.parametrize('decision', ['REVIEWED', 'NEEDS_REVISION'])
def test_named_password_teacher_review_is_independent_and_replays_across_alias(client, identities, organization, decision):
    f, assignment, draft = ready(client, identities, organization)
    payload = body(assignment);payload['decision'] = decision
    response = send(client, f, draft, payload)
    assert response.status_code == 201, response.text
    assert response.headers['cache-control'] == 'no-store'
    receipt = response.json()
    assert receipt['revision_id'] == draft['current_revision_id'] and receipt['decision'] == decision
    assert send(client, f, draft, payload).json() == receipt
    alias = client.post('/api/v1/internship-logs/daily-logs/' + draft['id'] + '/academic-reviews',
        headers=f['teacher']['headers'], json={**payload, 'placement_id':f['placement']['id'],
                                             'expected_revision_id':draft['current_revision_id']})
    assert alias.status_code == 201 and alias.json() == receipt, alias.text
    assert send(client, f, draft, {**payload, 'comment':'Changed intent.'}).status_code == 409
    assert send(client, f, draft, {**payload, 'idempotency_key':str(uuid4())}).status_code == 409
    assert count('academic_log_reviews') == count('academic_review_proofs') == 1
    assert count('workplace_log_reviews') == 0
    with transaction() as conn:
        proof = dict(conn.execute(select(table('academic_review_proofs'))).mappings().one())
        assert proof['actor_id'] == f['teacher']['user_id'] and proof['session_id'] == f['teacher']['session_id']
        assert proof['teacher_grant_id'] == f['teacher_grant']['id']
        assert proof['teacher_appointment_id'] == f['teacher_appointment']['id']
        assert proof['revision_snapshot']['id'] == draft['current_revision_id']
        assert proof['initial_snapshot']['decision'] == decision and proof['receipt'] == receipt
        assert get_row(conn, 'placements', f['placement']['id'])['status'] == 'ACTIVE'
        assert get_row(conn, 'log_revisions', draft['current_revision_id'])['status'] == 'SUBMITTED'
        events = table('audit_events')
        assert len(conn.execute(select(events.c.id).where(events.c.action == 'ACADEMIC_LOG_REVIEWED')).all()) == 1


@pytest.mark.parametrize('same_key', [True, False])
def test_concurrent_feedback_has_one_effect(client, identities, organization, same_key,record_testsuite_property):
    f, assignment, draft = ready(client, identities, organization)
    payload = body(assignment);other=dict(payload)
    if not same_key:other['idempotency_key']=str(uuid4())
    labels=['review-'+str(uuid4())+'-'+str(i) for i in range(2)]
    with labeled_requests(get_engine()) as call,ThreadPoolExecutor(max_workers=2) as pool:
        with get_engine().begin() as holder:
            holder.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                {'key':'academic-review:'+f['teacher']['user_id']+':'+payload['idempotency_key']})
            first=pool.submit(call,labels[0],send,client,f,draft,payload)
            wait_for_requests(get_engine(),labels[:1],intent_only=True)
            second=pool.submit(call,labels[1],send,client,f,draft,other)
            observed=wait_for_requests(get_engine(),labels)
            assert len({row['pid'] for row in observed})==2
            import json
            record_testsuite_property('same_revision_overlap_'+str(same_key),json.dumps(observed))
        responses=[first.result(timeout=30),second.result(timeout=30)]
    assert sorted(r.status_code for r in responses) == ([201, 201] if same_key else [201, 409])
    if same_key:assert responses[0].json() == responses[1].json()
    assert count('academic_log_reviews') == count('academic_review_proofs') == 1


@pytest.mark.parametrize('who', ['candidate', 'coord', 'owner', 'outsider'])
def test_only_personally_named_teacher_can_write(client, identities, organization, who):
    f, assignment, draft = ready(client, identities, organization)
    user = identities() if who == 'outsider' else f[who]
    before = count('audit_events')
    response = send(client, f, draft, body(assignment), user=user)
    assert response.status_code == 403, response.text
    assert count('academic_log_reviews') == count('academic_review_proofs') == 0
    assert count('audit_events') == before


@pytest.mark.parametrize('extra', [{'decision':'APPROVED'}, {'decision':'REJECTED'}, {'academic_grade':5},
                                  {'decision':'CHANGES_REQUESTED'}, {'actor_id':str(uuid4())}, {'idempotency_key':''}])
def test_new_review_contract_rejects_old_vocabulary_grade_and_actor_injection(client, identities, organization, extra):
    f, assignment, draft = ready(client, identities, organization)
    response = send(client, f, draft, {**body(assignment), **extra})
    assert response.status_code == 422, response.text
    assert count('academic_log_reviews') == count('academic_review_proofs') == 0


def test_unsubmitted_revision_and_missing_alias_intent_fail_closed(client, identities, organization):
    f, assignment, draft = ready(client, identities, organization, submit=False)
    response = send(client, f, draft, body(assignment))
    assert response.status_code == 409 and response.json()['detail']['code'] == 'SUBMITTED_REVISION_REQUIRED'
    alias = client.post('/api/v1/internship-logs/daily-logs/' + draft['id'] + '/academic-reviews',
        headers=f['teacher']['headers'],json={**body(assignment),'placement_id':f['placement']['id']})
    assert alias.status_code == 422
    assert count('academic_log_reviews') == 0


def test_pointer_change_cannot_redirect_alias_but_exact_submitted_revision_remains_reviewable(client, identities, organization):
    f, assignment, draft = ready(client, identities, organization)
    p = plan(client,f)
    with transaction() as conn:
        replacement = insert_row(conn, 'log_revisions', daily_log_id=draft['id'], revision=2,
            terms_id=p['terms_id'], author_id=f['candidate']['user_id'], day_type='WORKED',
            summary='Private new draft', total_minutes=0, status='DRAFT', idempotency_key=str(uuid4()))
        logs = table('daily_logs')
        conn.execute(logs.update().where(logs.c.id == draft['id']).values(current_revision_id=replacement['id']))
    payload = body(assignment)
    alias_body = {**payload,'placement_id':f['placement']['id'],'expected_revision_id':draft['current_revision_id']}
    url = '/api/v1/internship-logs/daily-logs/' + draft['id'] + '/academic-reviews'
    stale = client.post(url,headers=f['teacher']['headers'],json=alias_body)
    assert stale.status_code == 409 and stale.json()['detail']['code'] == 'STALE_LOG_REVISION'
    response = send(client,f,draft,payload);assert response.status_code == 201,response.text
    # An exact prior intent can replay its original receipt; it never reviews the new pointer.
    assert client.post(url,headers=f['teacher']['headers'],json=alias_body).json() == response.json()
    with transaction() as conn:
        assert get_row(conn,'log_revisions',replacement['id'])['status'] == 'DRAFT'
    assert count('academic_log_reviews') == 1


def test_cancellation_denies_new_feedback_and_replay_keeps_historical_receipt(client, identities, organization):
    f, assignment, draft = ready(client, identities, organization);payload = body(assignment)
    first = send(client,f,draft,payload);assert first.status_code == 201,first.text
    p = plan(client,f)
    post(client,'/api/v1/placements/' + f['placement']['id'] + '/host-decisions',f['owner'],
         {**terms_request(p),'action':'CANCEL'},200)
    repeated = send(client,f,draft,payload);assert repeated.status_code == 201,repeated.text
    assert repeated.json() == first.json()
    response = send(client,f,draft,{**payload,'idempotency_key':str(uuid4())})
    assert response.status_code == 403,response.text


@pytest.mark.parametrize('change', ['session','grant'])
def test_revocation_after_actual_business_lock_wait_prevents_feedback(client, identities, organization, change):
    f, assignment, draft = ready(client, identities, organization);before = count('audit_events')
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            holder.execute(select(table('institutions')).where(table('institutions').c.id == f['inst']['id']).with_for_update())
            pid = holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending = pool.submit(send,client,f,draft,body(assignment));wait_for_blocker(pid)
            if change == 'session':
                response = client.delete('/api/v1/me/sessions/' + f['teacher']['session_id'],headers=f['teacher']['headers'])
                assert response.status_code == 200,response.text
            else:
                with transaction() as conn:
                    grants = table('institution_role_grants')
                    conn.execute(grants.update().where(grants.c.id == f['teacher_grant']['id']).values(revoked_at=now()))
        response = pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert count('academic_log_reviews') == count('academic_review_proofs') == 0
    # Actual session revocation has its own legitimate audit event.
    assert count('audit_events') == before + (1 if change == 'session' else 0)


def test_review_audit_failure_rolls_back_review_proof_and_nonce(client, identities, organization, monkeypatch):
    f, assignment, draft = ready(client, identities, organization);payload = body(assignment)
    before = count('audit_events');original = academic_review_service.audit.append_audit_event
    def fail(**values):
        original(**values)
        raise RuntimeError('Injected audit failure after insert')
    with monkeypatch.context() as patch:
        patch.setattr(academic_review_service.audit,'append_audit_event',fail)
        response = send(client,f,draft,payload)
    assert response.status_code == 503,response.text
    assert count('academic_log_reviews') == count('academic_review_proofs') == 0 and count('audit_events') == before
    assert send(client,f,draft,payload).status_code == 201


@pytest.mark.parametrize('name', ['academic_log_reviews','academic_review_proofs'])
@pytest.mark.parametrize('mutation', ['update','delete'])
def test_review_and_proof_are_immutable_in_sql(client, identities, organization, name, mutation):
    f, assignment, draft = ready(client, identities, organization)
    response = send(client,f,draft,body(assignment));assert response.status_code == 201,response.text
    t = table(name)
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(t.delete() if mutation == 'delete' else t.update().values(
            **({'comment':'Rewritten'} if name == 'academic_log_reviews' else {'receipt':{}})))
    assert count('academic_log_reviews') == count('academic_review_proofs') == 1


def test_sql_review_without_proof_cannot_commit(client, identities, organization):
    f, assignment, draft = ready(client, identities, organization)
    with pytest.raises(IntegrityError,match='requires immutable proof'),transaction() as conn:
        insert_row(conn,'academic_log_reviews',revision_id=draft['current_revision_id'],placement_id=f['placement']['id'],
                   academic_assignment_id=assignment['id'],decision='REVIEWED',comment='Unproved SQL write',decided_at=now())
    assert count('academic_log_reviews') == count('academic_review_proofs') == 0


def test_expiry_during_real_intent_lock_wait_denies_receipt_replay(client, identities, organization):
    f, assignment, draft = ready(client, identities, organization);payload = body(assignment)
    first = send(client,f,draft,payload);assert first.status_code == 201,first.text
    expires = now() + timedelta(seconds=6)
    with transaction() as conn:
        sessions = table('sessions')
        conn.execute(sessions.update().where(sessions.c.id == f['teacher']['session_id']).values(expires_at=expires))
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            holder.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                {'key':'academic-review:' + f['teacher']['user_id'] + ':' + payload['idempotency_key']})
            pid = holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending = pool.submit(send,client,f,draft,payload);wait_for_blocker(pid)
            sleep(max(0,(expires-now()).total_seconds()) + 0.1)
        response = pending.result(timeout=30)
    assert response.status_code == 401,response.text
    assert count('academic_log_reviews') == count('academic_review_proofs') == 1


def test_sql_proof_cannot_store_a_receipt_with_different_feedback(client, identities, organization):
    f, assignment, draft = ready(client, identities, organization)
    with pytest.raises(IntegrityError,match='exact current teacher'),transaction() as conn:
        review = insert_row(conn,'academic_log_reviews',revision_id=draft['current_revision_id'],placement_id=f['placement']['id'],
            academic_assignment_id=assignment['id'],decision='REVIEWED',comment='The original teacher feedback.',decided_at=now())
        stored = snapshot(conn,'academic_log_reviews',review['id']);receipt = {**stored,'comment':'Different replayed feedback.'}
        conn.execute(table('academic_review_proofs').insert().values(review_id=review['id'],created_at=now(),origin='PUBLIC',
            initial_snapshot=stored,terms_id=snapshot(conn,'log_revisions',draft['current_revision_id'])['terms_id'],
            **evidence(conn,actor(f['teacher'])),teacher_grant_id=f['teacher_grant']['id'],
            teacher_appointment_id=f['teacher_appointment']['id'],revision_snapshot=snapshot(conn,'log_revisions',draft['current_revision_id']),
            assignment_proof_snapshot=conn.execute(text('SELECT to_jsonb(q) FROM flexbridge.academic_assignment_proofs q WHERE assignment_id=:a'),
                {'a':assignment['id']}).scalar_one(),idempotency_key=str(uuid4()),request_fingerprint='a'*64,receipt=receipt))
    assert count('academic_log_reviews') == count('academic_review_proofs') == 0
