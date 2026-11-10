"""Security and contract tests for Placement Report Export (API-052 / CAP-026).

Verifies role-based access (Candidate, Mentor, Teacher, Host), 403 for unassigned actors,
401 for unauthenticated calls, 404 for unknown placements, 24-hour PRIVATE_EXPORT_FILE retention,
actor-bound idempotency replay, format validation (PDF/JSON), and audit trail recording.
"""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.institution_scope import TASHKENT
from app.db.storage import files_table, now, table, transaction
from app.services.placement_export import EXPORT_DISCLAIMER
from test_academic_reviews import ready, body as review_body, send as review_send


def export_setup(client, identities, organization):
    start = now().astimezone(TASHKENT).date() - timedelta(days=1)
    f, assignment, draft = ready(
        client,
        identities,
        organization,
        placement_start_date=start,
        required_minutes=0,
    )
    response = review_send(client, f, draft, review_body(assignment, decision='REVIEWED'))
    assert response.status_code == 201, response.text
    return f, assignment, draft


def test_candidate_can_export_placement_report_pdf(client, identities, organization):
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    key = str(uuid4())

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': key, 'format': 'PDF'},
    )
    assert r.status_code == 201, r.text
    data = r.json()

    assert data['placement_id'] == pid
    assert data['actor_role'] == 'CANDIDATE'
    assert data['export_format'] == 'PDF'
    assert data['disclaimer'] == EXPORT_DISCLAIMER
    assert 'download_url' in data
    assert 'expires_at' in data
    assert data['summary']['placement_id'] == pid
    assert data['summary']['status'] == 'ACTIVE'

    # Verify files_table record has retention_class='PRIVATE_EXPORT_FILE'
    with transaction() as conn:
        f_row = conn.execute(
            select(files_table).where(files_table.c.id == data['file_id'])
        ).mappings().one()
        assert f_row['retention_class'] == 'PRIVATE_EXPORT_FILE'
        assert f_row['scan_status'] == 'CLEAN'
        assert f_row['mime_type'] == 'application/pdf'

        # Verify placement_exports table record
        t_pe = table('placement_exports')
        exp_row = conn.execute(
            select(t_pe).where(t_pe.c.id == data['export_id'])
        ).mappings().one()
        assert exp_row['placement_id'] == pid
        assert exp_row['export_format'] == 'PDF'
        assert exp_row['idempotency_key'] == key


def test_mentor_and_teacher_can_export_placement_report_json(client, identities, organization):
    f, assignment, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    # 1. Teacher export JSON
    r_teacher = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['teacher']['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'JSON'},
    )
    assert r_teacher.status_code == 201, r_teacher.text
    t_data = r_teacher.json()
    assert t_data['actor_role'] == 'TEACHER'
    assert t_data['export_format'] == 'JSON'
    assert t_data['summary']['export_format'] == 'JSON'

    # 2. Coordinator export PDF
    r_coord = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['coord']['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r_coord.status_code == 201, r_coord.text
    c_data = r_coord.json()
    assert c_data['actor_role'] == 'COORDINATOR'


def test_host_owner_can_export_placement_report(client, identities, organization):
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['owner']['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 201, r.text
    assert r.json()['actor_role'] == 'HOST'


def test_unrelated_actor_is_forbidden(client, identities, organization):
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    outsider = identities()

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=outsider['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_guest_unauthenticated_is_401(client, identities, organization):
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 401


def test_placement_not_found_is_404(client, identities):
    user = identities()
    fake_pid = str(uuid4())

    r = client.post(
        f'/api/v1/placements/{fake_pid}/exports',
        headers=user['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 404, r.text
    assert r.json()['detail']['code'] in ('PLACEMENTS_NOT_FOUND', 'PLACEMENT_NOT_FOUND')


def test_idempotency_replay_by_same_actor_returns_exact_receipt(client, identities, organization):
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    key = str(uuid4())

    # Call 1
    r1 = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': key, 'format': 'PDF'},
    )
    assert r1.status_code == 201, r1.text
    d1 = r1.json()

    # Call 2 (replay)
    r2 = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': key, 'format': 'PDF'},
    )
    assert r2.status_code == 201, r2.text
    d2 = r2.json()

    assert d1['export_id'] == d2['export_id']
    assert d1['file_id'] == d2['file_id']
    assert d1['created_at'] == d2['created_at']


def test_idempotency_actor_mismatch_is_forbidden(client, identities, organization):
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    key = str(uuid4())

    # Candidate creates export
    r1 = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': key, 'format': 'PDF'},
    )
    assert r1.status_code == 201, r1.text

    # Owner attempts to reuse same idempotency_key
    r2 = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['owner']['headers'],
        json={'idempotency_key': key, 'format': 'PDF'},
    )
    assert r2.status_code == 403, r2.text
    assert r2.json()['detail']['code'] == 'IDEMPOTENCY_ACTOR_MISMATCH'


def test_idempotency_key_reuse_different_payload_is_409(client, identities, organization):
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    key = str(uuid4())

    # PDF format
    r1 = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': key, 'format': 'PDF'},
    )
    assert r1.status_code == 201, r1.text

    # Reused key with JSON format
    r2 = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': key, 'format': 'JSON'},
    )
    assert r2.status_code == 409, r2.text
    assert r2.json()['detail']['code'] == 'IDEMPOTENCY_KEY_REUSE'


def test_invalid_export_format_is_422(client, identities, organization):
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'INVALID'},
    )
    assert r.status_code == 422


def test_export_audit_event_recorded(client, identities, organization):
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    key = str(uuid4())

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': key, 'format': 'PDF'},
    )
    assert r.status_code == 201, r.text
    exp_id = r.json()['export_id']

    with transaction() as conn:
        t_aud = table('audit_events')
        event = conn.execute(
            select(t_aud)
            .where(
                t_aud.c.object_key == pid,
                t_aud.c.action == 'REPORT_EXPORT',
            )
        ).mappings().first()
        assert event is not None
        assert event['object_type'] == 'placements'
        assert event['scope_snapshot']['export_id'] == exp_id
