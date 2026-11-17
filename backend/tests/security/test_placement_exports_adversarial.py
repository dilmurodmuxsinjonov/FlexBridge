"""Adversarial stress-testing suite for Placement Report Export (API-052 / CAP-026).

Empirically tests multi-tenancy isolation, academic tracking isolation across institutions,
host role privilege boundaries, proof revocation enforcement, SQL injection resistance,
and payload tampering defense.
"""
from datetime import timedelta
import secrets
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.institution_scope import TASHKENT
from app.db.storage import now, table, transaction
from app.services.placement_export import EXPORT_DISCLAIMER
from test_academic_admission import plan
from test_academic_reviews import ready, body as review_body, send as review_send
from test_admission_lifecycle import terms_request
from test_institution_authority import setup_scope


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


def create_second_organization():
    """Helper to create a second verified organization."""
    oid = str(uuid4())
    with transaction() as conn:
        conn.execute(
            table('organizations').insert().values(
                id=oid,
                created_at=now(),
                updated_at=now(),
                tax_id=secrets.token_hex(8),
                legal_name='Adversarial Org B',
                public_name='Adversarial Org B',
                region='Samarkand',
                status='VERIFIED',
            )
        )
        from app.services.placements import insert_row
        requester = insert_row(conn, 'users', display_name='Org B requester', status='ACTIVE', locale='uz', timezone='Asia/Tashkent')
        reviewer = insert_row(conn, 'users', display_name='Org B reviewer', status='ACTIVE', locale='uz', timezone='Asia/Tashkent')
        for code in ('JOB_EMPLOYER', 'INTERNSHIP_HOST'):
            case = insert_row(
                conn, 'verification_cases', requester_id=requester['id'], organization_id=oid, kind=code,
                status='APPROVED', current_revision=1, assigned_reviewer_id=reviewer['id'], due_at=now(), decided_at=now()
            )
            insert_row(conn, 'organization_capabilities', organization_id=oid, capability=code, status='ACTIVE', approved_case_id=case['id'])
    return oid


# ============================================================================
# 1. Multi-Tenancy Isolation
# ============================================================================

def test_host_owner_org_b_cannot_export_org_a_placement(client, identities, organization):
    """Host owner of Org B must NOT be able to export a placement belonging to Org A."""
    f, _, _ = export_setup(client, identities, organization)
    pid_org_a = f['placement']['id']

    # Create Org B and an owner for Org B
    org_b = create_second_organization()
    owner_org_b = identities('OWNER', org=org_b)

    r = client.post(
        f'/api/v1/placements/{pid_org_a}/exports',
        headers=owner_org_b['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_host_member_without_privileged_role_cannot_export(client, identities, organization):
    """A member of the placement's host organization with role MEMBER (non-owner/HR) must NOT export."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    # Create a user with regular 'MEMBER' role in the host organization
    member_user = identities('MEMBER', org=organization)

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=member_user['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_cross_candidate_isolation(client, identities, organization):
    """Candidate of Placement A must NOT be able to export Placement B."""
    f_a, _, _ = export_setup(client, identities, organization)
    pid_a = f_a['placement']['id']

    # Another candidate user completely unrelated
    unrelated_candidate = identities()

    r = client.post(
        f'/api/v1/placements/{pid_a}/exports',
        headers=unrelated_candidate['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


# ============================================================================
# 2. Academic Tracking & Cross-Institution Isolation
# ============================================================================

def test_cross_institution_coordinator_isolation(client, identities, organization):
    """Coordinator of Institution Y must NOT be able to export placement under Institution X."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    # Setup a second completely separate institution and its coordinator
    coord_y, _, inst_y, _, _, _, _ = setup_scope(identities)

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=coord_y['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_cross_institution_teacher_isolation(client, identities, organization):
    """Teacher from Institution Y must NOT be able to export placement under Institution X."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    # Setup second institution
    _, _, inst_y, _, _, _, _ = setup_scope(identities)
    teacher_y = identities()

    with transaction() as conn:
        insert_row = lambda name, **kw: conn.execute(table(name).insert().values(id=str(uuid4()), created_at=now(), updated_at=now(), **kw))
        insert_row('institution_memberships', institution_id=inst_y['id'], user_id=teacher_y['user_id'], status='ACTIVE', accepted_at=now())

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=teacher_y['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_revoked_teacher_assignment_cannot_export(client, identities, organization):
    """If a teacher's assignment is revoked by the coordinator, they must lose export authorization immediately."""
    f, assignment, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    # 1. Teacher exports once successfully
    r1 = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['teacher']['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'JSON'},
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()['actor_role'] == 'TEACHER'

    # 2. Coordinator revokes teacher's academic assignment via API
    r_revoke = client.post(
        f'/api/v1/academic-assignments/{assignment["id"]}/revoke',
        headers=f['coord']['headers'],
        json={'idempotency_key': str(uuid4())},
    )
    assert r_revoke.status_code == 200, r_revoke.text

    # 3. Attempt export after revocation -> must be forbidden
    r2 = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['teacher']['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'JSON'},
    )
    assert r2.status_code == 403, r2.text
    assert r2.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_revoked_mentor_assignment_cannot_export(client, identities, organization):
    """If a dedicated workplace mentor's assignment is revoked, they must lose export authorization."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    base = f'/api/v1/placements/{pid}'

    # In export_setup, an initial mentor was already accepted. Find and revoke it first.
    with transaction() as conn:
        t_m = table('mentor_assignments')
        initial_m = conn.execute(
            select(t_m).where(
                t_m.c.placement_id == pid,
                t_m.c.accepted_at.is_not(None),
                t_m.c.revoked_at.is_(None),
            )
        ).mappings().first()

    p = client.get(f'{base}/plan', headers=f['owner']['headers']).json()
    if initial_m:
        rev_initial = client.post(
            f'{base}/mentor-assignments/{initial_m["id"]}/revoke',
            headers=f['owner']['headers'],
            json=terms_request(p),
        )
        assert rev_initial.status_code == 200, rev_initial.text
        # Refresh plan terms after revocation
        p = client.get(f'{base}/plan', headers=f['owner']['headers']).json()

    # Create a dedicated mentor (non-owner) in organization
    dedicated_mentor = identities('MENTOR', org=organization)

    # Host owner nominates dedicated mentor
    m_res = client.post(
        f'{base}/mentor-assignments',
        headers=f['owner']['headers'],
        json={'mentor_id': dedicated_mentor['user_id'], 'idempotency_key': str(uuid4())},
    )
    assert m_res.status_code == 201, m_res.text
    mentor_assignment = m_res.json()

    # Dedicated mentor accepts assignment with refreshed plan
    acc = client.post(
        f'{base}/assignments/{mentor_assignment["id"]}/accept',
        headers=dedicated_mentor['headers'],
        json=terms_request(p),
    )
    assert acc.status_code == 200, acc.text

    # Dedicated mentor exports successfully
    r1 = client.post(
        f'{base}/exports',
        headers=dedicated_mentor['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()['actor_role'] == 'MENTOR'

    # Host owner revokes dedicated mentor assignment
    p_latest = client.get(f'{base}/plan', headers=f['owner']['headers']).json()
    rev = client.post(
        f'{base}/mentor-assignments/{mentor_assignment["id"]}/revoke',
        headers=f['owner']['headers'],
        json=terms_request(p_latest),
    )
    assert rev.status_code == 200, rev.text

    # Dedicated mentor attempts export after revocation -> must be forbidden
    r2 = client.post(
        f'{base}/exports',
        headers=dedicated_mentor['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r2.status_code == 403, r2.text
    assert r2.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_unaccepted_mentor_cannot_export(client, identities, organization):
    """A nominated mentor who has not accepted the assignment must NOT be able to export."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    base = f'/api/v1/placements/{pid}'

    dedicated_mentor = identities('MENTOR', org=organization)

    # Nominate without accepting
    m_res = client.post(
        f'{base}/mentor-assignments',
        headers=f['owner']['headers'],
        json={'mentor_id': dedicated_mentor['user_id'], 'idempotency_key': str(uuid4())},
    )
    assert m_res.status_code == 201, m_res.text

    # Attempt export prior to acceptance -> forbidden
    r = client.post(
        f'{base}/exports',
        headers=dedicated_mentor['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


# ============================================================================
# 3. Input Validation, Injection Defense, and Tampering
# ============================================================================

def test_sql_injection_in_idempotency_key(client, identities, organization):
    """SQL injection payloads in idempotency_key must be safely parameterized without corruption."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    sqli_key = "test_key'; DROP TABLE flexbridge.placement_exports; --"

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': sqli_key, 'format': 'PDF'},
    )
    assert r.status_code == 201, r.text
    assert r.json()['actor_role'] == 'CANDIDATE'

    # Verify table placement_exports was NOT dropped
    with transaction() as conn:
        t_pe = table('placement_exports')
        row = conn.execute(
            select(t_pe).where(t_pe.c.idempotency_key == sqli_key)
        ).mappings().first()
        assert row is not None
        assert row['idempotency_key'] == sqli_key


def test_sql_injection_in_placement_id(client, identities):
    """SQL injection in path parameter placement_id must return 404 or 422 cleanly, never 500."""
    user = identities()
    malicious_pid = "00000000-0000-0000-0000-000000000000' OR 1=1;--"

    r = client.post(
        f'/api/v1/placements/{malicious_pid}/exports',
        headers=user['headers'],
        json={'idempotency_key': str(uuid4()), 'format': 'PDF'},
    )
    assert r.status_code in (404, 422), r.text
    assert r.status_code != 500


def test_payload_tampering_extra_fields_rejected(client, identities, organization):
    """StrictDTO must reject unexpected fields (extra='forbid') with 422."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={
            'idempotency_key': str(uuid4()),
            'format': 'PDF',
            'actor_role': 'COORDINATOR',  # Tampered field
            'bypass_auth': True,          # Tampered field
        },
    )
    assert r.status_code == 422, r.text


@pytest.mark.parametrize('bad_format', [
    '', 'pdf', 'json', 'XML', 'CSV', 'HTML', 'PDF\x00', '..//PDF', 'JSON; SELECT 1',
])
def test_format_fuzzing_rejected(client, identities, organization, bad_format):
    """All invalid formats must be strictly rejected with 422."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    r = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': str(uuid4()), 'format': bad_format},
    )
    assert r.status_code == 422, r.text


def test_idempotency_key_length_boundaries(client, identities, organization):
    """Idempotency key length boundaries: min 8, max 128 characters."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']

    # Too short (< 8 chars) -> 422
    r_short = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': '1234567', 'format': 'PDF'},
    )
    assert r_short.status_code == 422, r_short.text

    # Too long (> 128 chars) -> 422
    r_long = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': 'a' * 129, 'format': 'PDF'},
    )
    assert r_long.status_code == 422, r_long.text

    # Exact min length (8 chars) -> 201
    r_min = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': '12345678', 'format': 'PDF'},
    )
    assert r_min.status_code == 201, r_min.text

    # Exact max length (128 chars) -> 201
    r_max = client.post(
        f'/api/v1/placements/{pid}/exports',
        headers=f['candidate']['headers'],
        json={'idempotency_key': 'b' * 128, 'format': 'PDF'},
    )
    assert r_max.status_code == 201, r_max.text


# ============================================================================
# 4. Concurrency and Race Stress Testing
# ============================================================================

def test_concurrent_idempotency_requests(client, identities, organization):
    """Multiple concurrent requests with identical idempotency key must be handled safely."""
    f, _, _ = export_setup(client, identities, organization)
    pid = f['placement']['id']
    key = str(uuid4())

    from concurrent.futures import ThreadPoolExecutor

    def make_export_request():
        return client.post(
            f'/api/v1/placements/{pid}/exports',
            headers=f['candidate']['headers'],
            json={'idempotency_key': key, 'format': 'PDF'},
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(make_export_request) for _ in range(4)]
        responses = [fut.result() for fut in futures]

    status_codes = [r.status_code for r in responses]
    assert 201 in status_codes, f"Expected 201 in status codes, got: {status_codes}"
    successful = [r.json() for r in responses if r.status_code == 201]
    first_receipt = successful[0]
    for r_json in successful[1:]:
        assert r_json['export_id'] == first_receipt['export_id']
        assert r_json['file_id'] == first_receipt['file_id']

