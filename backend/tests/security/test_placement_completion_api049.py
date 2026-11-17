"""Security and contract tests for Placement Completion Requests (API-049).

Verifies two-sided sign-off (Candidate + Host/Mentor), relationship-based authorization,
preconditions (ACTIVE/COMPLETION_REQUESTED, no open NEEDS_REVISION logs),
minutes vs required_minutes validation, early completion explanations, and idempotency.
"""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.storage import table, transaction, now
from app.db.institution_scope import TASHKENT
from test_academic_reviews import ready, body as review_body, send as review_send


def reviewed_placement(client, identities, organization, required_minutes=0, review_decision='REVIEWED'):
    start = now().astimezone(TASHKENT).date() - timedelta(days=1)
    f, assignment, draft = ready(
        client,
        identities,
        organization,
        placement_start_date=start,
        required_minutes=required_minutes,
    )
    response = review_send(client, f, draft, review_body(assignment, decision=review_decision))
    assert response.status_code == 201, response.text
    return f, assignment, draft


def completion_body(f, **extra):
    with transaction() as conn:
        p = conn.execute(
            select(table('placements')).where(table('placements').c.id == f['placement']['id'])
        ).mappings().one()
        t = conn.execute(
            select(table('placement_terms')).where(table('placement_terms').c.id == p['current_terms_id'])
        ).mappings().one()
    return {
        'terms_id': str(t['id']),
        'version': t['version'],
        'idempotency_key': str(uuid4()),
        'decision': 'REQUEST_COMPLETION',
        'reason': 'Internship period completed as planned.',
        **extra,
    }


def test_candidate_requests_completion_and_host_confirms(client, identities, organization):
    f, _, _ = reviewed_placement(client, identities, organization, required_minutes=0)
    pid = f['placement']['id']

    # 1. Candidate requests completion
    payload = completion_body(f, decision='REQUEST_COMPLETION')
    r1 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=payload,
    )
    assert r1.status_code == 201, r1.text
    data1 = r1.json()
    assert data1['side'] == 'CANDIDATE'
    assert data1['decision'] == 'REQUEST_COMPLETION'
    assert data1['status'] == 'PENDING_HOST'
    assert data1['placement_status'] == 'COMPLETION_REQUESTED'
    assert data1['contract_id'] == 'API-049'

    # Check placement status in DB
    with transaction() as conn:
        p_row = conn.execute(
            select(table('placements')).where(table('placements').c.id == pid)
        ).mappings().one()
        assert p_row['status'] == 'COMPLETION_REQUESTED'

    # 2. Host coordinator confirms completion
    payload2 = completion_body(f, decision='CONFIRM_COMPLETION')
    r2 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['owner']['headers'],
        json=payload2,
    )
    assert r2.status_code == 201, r2.text
    data2 = r2.json()
    assert data2['side'] in ('HOST', 'MENTOR')
    assert data2['decision'] == 'CONFIRM_COMPLETION'
    assert data2['status'] == 'COMPLETED'
    assert data2['placement_status'] == 'COMPLETED'

    # Check placement status is now COMPLETED
    with transaction() as conn:
        p_row = conn.execute(
            select(table('placements')).where(table('placements').c.id == pid)
        ).mappings().one()
        assert p_row['status'] == 'COMPLETED'


def test_host_requests_completion_and_candidate_confirms(client, identities, organization):
    f, _, _ = reviewed_placement(client, identities, organization, required_minutes=0)
    pid = f['placement']['id']

    # 1. Host requests completion
    payload1 = completion_body(f, decision='REQUEST_COMPLETION')
    r1 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['owner']['headers'],
        json=payload1,
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()['status'] == 'PENDING_CANDIDATE'
    assert r1.json()['placement_status'] == 'COMPLETION_REQUESTED'

    # 2. Candidate confirms completion
    payload2 = completion_body(f, decision='CONFIRM_COMPLETION')
    r2 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=payload2,
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()['status'] == 'COMPLETED'
    assert r2.json()['placement_status'] == 'COMPLETED'


def test_early_completion_requires_explicit_reason(client, identities, organization):
    # Required minutes is 10000, but logged minutes is only 240
    f, _, _ = reviewed_placement(client, identities, organization, required_minutes=10000)
    pid = f['placement']['id']

    # 1. Candidate requests completion without early_reason -> 422
    payload = completion_body(f, early_reason=None)
    r1 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=payload,
    )
    assert r1.status_code == 422, r1.text
    assert 'EARLY_COMPLETION_REASON_REQUIRED' in r1.text

    # 2. Candidate requests with valid early_reason -> 201
    payload_valid = completion_body(
        f,
        early_reason='Student accomplished all internship learning tasks ahead of schedule with exemplary performance.',
    )
    r2 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=payload_valid,
    )
    assert r2.status_code == 201, r2.text
    data = r2.json()
    assert data['early_completion'] is True
    assert data['early_reason'] is not None


def test_open_needs_revision_logs_blocks_completion(client, identities, organization):
    # Placement with a log reviewed as NEEDS_REVISION
    f, _, _ = reviewed_placement(client, identities, organization, review_decision='NEEDS_REVISION')
    pid = f['placement']['id']

    # Candidate requests completion -> 409
    payload = completion_body(f)
    r = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=payload,
    )
    assert r.status_code == 409, r.text
    assert 'OPEN_LOGS_NEED_REVISION' in r.text


def test_open_workplace_changes_requested_blocks_completion(client, identities, organization):
    start = now().astimezone(TASHKENT).date() - timedelta(days=1)
    f, assignment, draft = ready(
        client,
        identities,
        organization,
        placement_start_date=start,
        required_minutes=0,
    )
    pid = f['placement']['id']

    # Mentor reviews log with CHANGES_REQUESTED
    with transaction() as conn:
        lr = conn.execute(
            select(table('daily_logs')).where(table('daily_logs').c.id == draft['id'])
        ).mappings().one()
        ma = conn.execute(
            select(table('mentor_assignments')).where(table('mentor_assignments').c.placement_id == pid)
        ).mappings().one()
        conn.execute(
            table('workplace_log_reviews').insert().values(
                id=str(uuid4()),
                placement_id=pid,
                revision_id=lr['current_revision_id'],
                mentor_assignment_id=ma['id'],
                decision='CHANGES_REQUESTED',
                comment='Please detail the engineering milestones.',
                decided_at=now(),
            )
        )

    # Calling completion request -> blocked with 409 OPEN_LOGS_NEED_REVISION
    payload = completion_body(f)
    r = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=payload,
    )
    assert r.status_code == 409, r.text
    assert 'OPEN_LOGS_NEED_REVISION' in r.text


def test_unauthorized_user_forbidden(client, identities, organization):
    f, _, _ = reviewed_placement(client, identities, organization, required_minutes=0)
    pid = f['placement']['id']

    # Another unassigned user attempts to call completion-requests
    attacker = identities()
    payload = completion_body(f)
    r = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=attacker['headers'],
        json=payload,
    )
    assert r.status_code == 403, r.text
    assert 'PLACEMENT_ACTOR_FORBIDDEN' in r.text

    # Probing with bogus terms_id still yields 403 FORBIDDEN without revealing terms mismatch
    bogus_payload = completion_body(f, terms_id=str(uuid4()), version=999)
    r_probe = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=attacker['headers'],
        json=bogus_payload,
    )
    assert r_probe.status_code == 403, r_probe.text
    assert 'PLACEMENT_ACTOR_FORBIDDEN' in r_probe.text


def test_idempotent_replay_and_key_reuse(client, identities, organization):
    f, _, _ = reviewed_placement(client, identities, organization, required_minutes=0)
    pid = f['placement']['id']

    key = str(uuid4())
    payload = completion_body(f, idempotency_key=key, reason='Original submission')

    # First call
    r1 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=payload,
    )
    assert r1.status_code == 201, r1.text

    # Replay with identical payload and key
    r2 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=payload,
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()['id'] == r1.json()['id']

    # Replay with same key but different reason -> 409
    tampered = {**payload, 'reason': 'Tampered modified text'}
    r3 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=tampered,
    )
    assert r3.status_code == 409, r3.text
    assert 'IDEMPOTENCY_KEY_REUSE' in r3.text


def test_already_completed_placement_cannot_be_recompleted(client, identities, organization):
    f, _, _ = reviewed_placement(client, identities, organization, required_minutes=0)
    pid = f['placement']['id']

    # Candidate requests completion
    client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=completion_body(f, decision='REQUEST_COMPLETION'),
    )
    # Host confirms -> status becomes COMPLETED
    host_key = str(uuid4())
    host_payload = completion_body(f, decision='CONFIRM_COMPLETION', idempotency_key=host_key)
    r_host = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['owner']['headers'],
        json=host_payload,
    )
    assert r_host.status_code == 201, r_host.text
    final_id = r_host.json()['id']

    # Retrying the exact final sign-off with the same idempotency key succeeds via replay
    r_replay = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['owner']['headers'],
        json=host_payload,
    )
    assert r_replay.status_code == 201, r_replay.text
    assert r_replay.json()['id'] == final_id

    # Calling completion again with a NEW idempotency key on a COMPLETED placement -> 409
    r = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=completion_body(f, decision='REQUEST_COMPLETION'),
    )
    assert r.status_code == 409, r.text
    assert 'PLACEMENT_ALREADY_COMPLETED' in r.text


def test_idempotency_actor_mismatch_forbidden(client, identities, organization):
    f, _, _ = reviewed_placement(client, identities, organization, required_minutes=0)
    pid = f['placement']['id']

    key = str(uuid4())
    payload = completion_body(f, idempotency_key=key, reason='Candidate original request')

    # Candidate requests completion
    r1 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=payload,
    )
    assert r1.status_code == 201, r1.text

    # Host attempts to replay candidate's idempotency key -> 403 Forbidden
    r2 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['owner']['headers'],
        json=payload,
    )
    assert r2.status_code == 403, r2.text
    assert 'IDEMPOTENCY_ACTOR_MISMATCH' in r2.text


def test_rejection_invalidates_earlier_signoffs_requiring_fresh_bilateral_signoff(client, identities, organization):
    f, _, _ = reviewed_placement(client, identities, organization, required_minutes=0)
    pid = f['placement']['id']

    # Step 1: Candidate requests completion
    r1 = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=completion_body(f, decision='REQUEST_COMPLETION', reason='Initial request'),
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()['placement_status'] == 'COMPLETION_REQUESTED'

    # Step 2: Host rejects completion
    r_reject = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['owner']['headers'],
        json=completion_body(f, decision='REJECT_COMPLETION', reason='Need additional work'),
    )
    assert r_reject.status_code == 201, r_reject.text
    assert r_reject.json()['status'] == 'REJECTED'
    assert r_reject.json()['placement_status'] == 'ACTIVE'

    # Step 3: Host later requests completion.
    # CRITICAL: Since prior candidate sign-off was superseded upon rejection,
    # this request must NOT automatically complete the placement!
    r_host_req = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['owner']['headers'],
        json=completion_body(f, decision='REQUEST_COMPLETION', reason='Host now requests completion'),
    )
    assert r_host_req.status_code == 201, r_host_req.text
    assert r_host_req.json()['placement_status'] == 'COMPLETION_REQUESTED'
    assert r_host_req.json()['status'] == 'PENDING_CANDIDATE'

    # Step 4: Candidate provides fresh sign-off -> Now transitions to COMPLETED
    r_cand_confirm = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=completion_body(f, decision='CONFIRM_COMPLETION', reason='Candidate confirms'),
    )
    assert r_cand_confirm.status_code == 201, r_cand_confirm.text
    assert r_cand_confirm.json()['status'] == 'COMPLETED'
    assert r_cand_confirm.json()['placement_status'] == 'COMPLETED'


def test_multiple_reviews_do_not_multiply_logged_minutes(client, identities, organization):
    # A single submitted log of 60 minutes with both an academic review and a workplace review
    start = now().astimezone(TASHKENT).date() - timedelta(days=1)
    f, assignment, draft = ready(
        client,
        identities,
        organization,
        placement_start_date=start,
        required_minutes=120,  # Requires 120 minutes
    )
    pid = f['placement']['id']

    # Submit an academic review
    review_send(client, f, draft, review_body(assignment, decision='REVIEWED'))

    # Submit a workplace review on the same revision
    with transaction() as conn:
        lr = conn.execute(
            select(table('daily_logs')).where(table('daily_logs').c.id == draft['id'])
        ).mappings().one()
        ma = conn.execute(
            select(table('mentor_assignments')).where(table('mentor_assignments').c.placement_id == pid)
        ).mappings().one()
        conn.execute(
            table('workplace_log_reviews').insert().values(
                id=str(uuid4()),
                placement_id=pid,
                revision_id=lr['current_revision_id'],
                mentor_assignment_id=ma['id'],
                decision='APPROVED',
                comment='Great work.',
                decided_at=now(),
            )
        )

    # Calling completion without early_reason MUST fail with 422 because minutes = 60 < 120
    # (If the join multiplied minutes 2x to 120, it would incorrectly pass without early_reason!)
    r_fail = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=completion_body(f, decision='REQUEST_COMPLETION', reason='Unmet without explanation'),
    )
    assert r_fail.status_code == 422, r_fail.text
    assert 'EARLY_COMPLETION_REASON_REQUIRED' in r_fail.text

    # Calling with early_reason succeeds and correctly reports logged_minutes == 60 (not 120)
    r_ok = client.post(
        f'/api/v1/placements/{pid}/completion-requests',
        headers=f['candidate']['headers'],
        json=completion_body(
            f,
            decision='REQUEST_COMPLETION',
            reason='Internship shortened by mutual agreement',
            early_reason='Mutual sponsor release',
        ),
    )
    assert r_ok.status_code == 201, r_ok.text
    assert r_ok.json()['logged_minutes'] == 60
    assert r_ok.json()['required_minutes'] == 120
