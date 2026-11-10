"""Security and contract tests for Single Placement Diary Logs View (API-053 / CAP-022 / PG-022.S01).

Verifies:
1. Multi-role access control (Candidate, Host Owner, Pure Mentor, Teacher, Coordinator)
2. Confidentiality & anti-probing: non-candidate stakeholders only see SUBMITTED logs
3. Candidate draft privacy: non-candidate query for status=DRAFT returns empty list
4. Rejections: 403 for unrelated actors, 403 for revoked mentors/teachers, 401 unauthenticated, 404 nonexistent placement
5. Date range filtering and validation (422 on invalid order or format)
6. Pagination controls (page, page_size, total_pages) and bounds validation
7. Inclusion flags (include_tasks, include_reviews)
8. 130 tables migration schema regression
"""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.db.institution_scope import TASHKENT
from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_academic_admission import nominate, pending_http, plan
from test_academic_lifecycle import teacher_accept
from test_academic_reviews import body as review_body, send as review_send
from test_admission_lifecycle import terms_request
from test_internship_admission import post


def logs_setup(client, identities, organization):
    """Set up a placement with 5 distinct actors, 1 submitted log (day 1), and 1 draft log (day 2)."""
    start = now().astimezone(TASHKENT).date() - timedelta(days=3)
    f = pending_http(
        client,
        identities,
        organization,
        placement_start_date=start,
        required_minutes=0,
    )
    pid = f['placement']['id']
    base = f'/api/v1/placements/{pid}'

    # 1. Setup pure mentor (distinct from f['owner'])
    pure_mentor = identities()
    with transaction() as conn:
        m_mem = insert_row(conn, 'org_memberships', organization_id=organization, user_id=pure_mentor['user_id'], status='ACTIVE')
        roles = table('role_catalog')
        rid = conn.execute(select(roles.c.id).where(roles.c.code == 'MENTOR', roles.c.scope_kind == 'ORG')).scalar_one()
        insert_row(conn, 'org_role_grants', membership_id=m_mem['id'], role_id=rid, granted_by_id=f['owner']['user_id'])

    # 2. Academic nomination
    academic_assignment = nominate(client, f)
    p = plan(client, f)

    # 3. Candidate accepts
    post(client, base + '/accept', f['candidate'], terms_request(p), 200)

    # 4. Pure mentor nominated and accepted
    nom = post(client, base + '/mentor-assignments', f['owner'], dict(mentor_id=pure_mentor['user_id'], idempotency_key=str(uuid4())), 201)
    post(client, f"{base}/assignments/{nom['id']}/accept", pure_mentor, terms_request(p), 200)
    pure_mentor['assignment_id'] = nom['id']

    # 5. Teacher accepts
    _, _, t_resp = teacher_accept(client, f, academic_assignment, p)
    assert t_resp.status_code == 200, t_resp.text

    # 6. Host activates
    post(client, base + '/host-decisions', f['owner'], {**terms_request(p), 'action': 'ACTIVATE'}, 200)

    # 7. Day 1 log submitted
    r1 = client.put(base + '/logs/' + p['start_date'], headers=f['candidate']['headers'], json={
        'day_type': 'WORKED', 'summary_text': 'Submitted day 1 work', 'total_minutes': 60
    })
    assert r1.status_code == 200, r1.text
    draft1 = r1.json()
    post(client, '/api/v1/logs/' + draft1['id'] + '/submit', f['candidate'], {}, 200)

    # 8. Teacher reviews day 1
    review_send(client, f, draft1, review_body(academic_assignment, decision='REVIEWED', comment='Good work on day 1'))

    # 9. Day 2 draft log created
    day2 = (start + timedelta(days=1)).isoformat()
    r2 = client.put(
        f'/api/v1/placements/{pid}/logs/{day2}',
        headers=f['candidate']['headers'],
        json={
            'day_type': 'WORKED',
            'summary_text': 'Draft work for day 2',
            'total_minutes': 120,
            'tasks': [{'title': 'Feature implementation', 'minutes': 120}],
        },
    )
    assert r2.status_code == 200, r2.text
    draft2 = r2.json()

    f['pure_mentor'] = pure_mentor
    f['plan'] = p
    return f, academic_assignment, draft1, draft2, start


def test_candidate_can_view_own_placement_logs_including_drafts(client, identities, organization):
    f, _, draft1, draft2, start = logs_setup(client, identities, organization)
    pid = f['placement']['id']

    # 1. Candidate views all logs (no status filter) -> sees both DRAFT and SUBMITTED
    r = client.get(f'/api/v1/placements/{pid}/logs', headers=f['candidate']['headers'])
    assert r.status_code == 200, r.text
    data = r.json()

    assert data['contract_id'] == 'API-053'
    assert data['placement_id'] == pid
    assert data['total'] == 2
    assert len(data['items']) == 2

    statuses = {item['current_revision']['status'] for item in data['items']}
    assert statuses == {'SUBMITTED', 'DRAFT'}

    # 2. Candidate filters by status=DRAFT
    r_draft = client.get(f'/api/v1/placements/{pid}/logs?status=DRAFT', headers=f['candidate']['headers'])
    assert r_draft.status_code == 200
    d_draft = r_draft.json()
    assert d_draft['total'] == 1
    assert d_draft['items'][0]['current_revision']['status'] == 'DRAFT'
    assert d_draft['items'][0]['current_revision']['summary'] == 'Draft work for day 2'

    # 3. Candidate filters by status=SUBMITTED
    r_sub = client.get(f'/api/v1/placements/{pid}/logs?status=SUBMITTED', headers=f['candidate']['headers'])
    assert r_sub.status_code == 200
    d_sub = r_sub.json()
    assert d_sub['total'] == 1
    assert d_sub['items'][0]['current_revision']['status'] == 'SUBMITTED'


def test_host_owner_can_view_placement_logs_drafts_hidden(client, identities, organization):
    f, _, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']

    # Host owner views logs -> ONLY SUBMITTED logs are visible (draft is hidden)
    r = client.get(f'/api/v1/placements/{pid}/logs', headers=f['owner']['headers'])
    assert r.status_code == 200, r.text
    data = r.json()

    assert data['total'] == 1
    assert len(data['items']) == 1
    assert data['items'][0]['current_revision']['status'] == 'SUBMITTED'

    # If host requests status=DRAFT -> returns empty list (anti-probing privacy)
    r_draft = client.get(f'/api/v1/placements/{pid}/logs?status=DRAFT', headers=f['owner']['headers'])
    assert r_draft.status_code == 200
    d_draft = r_draft.json()
    assert d_draft['total'] == 0
    assert d_draft['items'] == []


def test_assigned_mentor_can_view_placement_logs_drafts_hidden(client, identities, organization):
    f, _, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']
    mentor = f['pure_mentor']

    # Mentor views logs -> only sees SUBMITTED log
    r = client.get(f'/api/v1/placements/{pid}/logs', headers=mentor['headers'])
    assert r.status_code == 200, r.text
    data = r.json()

    assert data['total'] == 1
    assert data['items'][0]['current_revision']['status'] == 'SUBMITTED'

    # Mentor requests status=DRAFT -> returns 0 items
    r_draft = client.get(f'/api/v1/placements/{pid}/logs?status=DRAFT', headers=mentor['headers'])
    assert r_draft.status_code == 200
    assert r_draft.json()['total'] == 0


def test_assigned_teacher_can_view_placement_logs_with_academic_reviews(client, identities, organization):
    f, _, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']

    r = client.get(f'/api/v1/placements/{pid}/logs', headers=f['teacher']['headers'])
    assert r.status_code == 200, r.text
    data = r.json()

    assert data['total'] == 1
    rev = data['items'][0]['current_revision']
    assert rev['status'] == 'SUBMITTED'
    assert 'academic_reviews' in rev
    assert len(rev['academic_reviews']) == 1
    assert rev['academic_reviews'][0]['decision'] == 'REVIEWED'
    assert rev['academic_reviews'][0]['comment'] == 'Good work on day 1'


def test_institutional_coordinator_can_view_placement_logs(client, identities, organization):
    f, _, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']

    r = client.get(f'/api/v1/placements/{pid}/logs', headers=f['coord']['headers'])
    assert r.status_code == 200, r.text
    data = r.json()

    assert data['total'] == 1
    assert data['items'][0]['current_revision']['status'] == 'SUBMITTED'


def test_unrelated_actor_rejected_with_403(client, identities, organization):
    f, _, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']
    outsider = identities()

    r = client.get(f'/api/v1/placements/{pid}/logs', headers=outsider['headers'])
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_revoked_mentor_rejected_with_403(client, identities, organization):
    f, _, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']
    mentor = f['pure_mentor']

    # Revoke pure mentor through proper admission route
    r_rev = client.post(
        f"/api/v1/placements/{pid}/mentor-assignments/{mentor['assignment_id']}/revoke",
        headers=f['owner']['headers'],
        json=terms_request(f['plan']),
    )
    assert r_rev.status_code == 200, r_rev.text

    # Mentor now receives 403
    r = client.get(f'/api/v1/placements/{pid}/logs', headers=mentor['headers'])
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_revoked_teacher_rejected_with_403(client, identities, organization):
    f, assignment, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']

    from app.services.academic_admission import academic_service
    from test_organizations import actor
    academic_service.revoke(actor(f['coord']), assignment['id'], idempotency_key=str(uuid4()))

    r = client.get(f'/api/v1/placements/{pid}/logs', headers=f['teacher']['headers'])
    assert r.status_code == 403, r.text
    assert r.json()['detail']['code'] == 'PLACEMENT_ACTOR_FORBIDDEN'


def test_guest_unauthenticated_is_401(client, identities, organization):
    f, _, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']

    r = client.get(f'/api/v1/placements/{pid}/logs')
    assert r.status_code == 401


def test_placement_not_found_is_404(client, identities):
    user = identities()
    fake_pid = str(uuid4())

    r = client.get(f'/api/v1/placements/{fake_pid}/logs', headers=user['headers'])
    assert r.status_code == 404, r.text
    assert r.json()['detail']['code'] in ('PLACEMENTS_NOT_FOUND', 'PLACEMENT_NOT_FOUND')


def test_date_range_filtering(client, identities, organization):
    f, _, _, _, start = logs_setup(client, identities, organization)
    pid = f['placement']['id']
    day1_str = start.isoformat()
    day2_str = (start + timedelta(days=1)).isoformat()

    # Filter to day 1 only
    r1 = client.get(f'/api/v1/placements/{pid}/logs?from_date={day1_str}&to_date={day1_str}', headers=f['candidate']['headers'])
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1['total'] == 1
    assert d1['items'][0]['local_date'] == day1_str

    # Filter to day 2 only
    r2 = client.get(f'/api/v1/placements/{pid}/logs?from_date={day2_str}&to_date={day2_str}', headers=f['candidate']['headers'])
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2['total'] == 1
    assert d2['items'][0]['local_date'] == day2_str


def test_date_range_validation_invalid_order_rejected_with_422(client, identities, organization):
    f, _, _, _, start = logs_setup(client, identities, organization)
    pid = f['placement']['id']
    day1_str = start.isoformat()
    day2_str = (start + timedelta(days=1)).isoformat()

    # from_date > to_date
    r = client.get(f'/api/v1/placements/{pid}/logs?from_date={day2_str}&to_date={day1_str}', headers=f['candidate']['headers'])
    assert r.status_code == 422, r.text
    assert r.json()['detail']['code'] == 'INVALID_DATE_RANGE'

    # Malformed date string
    r_bad = client.get(f'/api/v1/placements/{pid}/logs?from_date=not-a-date', headers=f['candidate']['headers'])
    assert r_bad.status_code == 422, r_bad.text
    assert r_bad.json()['detail']['code'] == 'INVALID_DATE_FORMAT'


def test_pagination_controls(client, identities, organization):
    f, _, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']

    # Page 1 with page_size=1
    r_p1 = client.get(f'/api/v1/placements/{pid}/logs?page=1&page_size=1', headers=f['candidate']['headers'])
    assert r_p1.status_code == 200
    dp1 = r_p1.json()
    assert dp1['total'] == 2
    assert dp1['page'] == 1
    assert dp1['page_size'] == 1
    assert dp1['total_pages'] == 2
    assert len(dp1['items']) == 1

    # Page 2 with page_size=1
    r_p2 = client.get(f'/api/v1/placements/{pid}/logs?page=2&page_size=1', headers=f['candidate']['headers'])
    assert r_p2.status_code == 200
    dp2 = r_p2.json()
    assert dp2['page'] == 2
    assert len(dp2['items']) == 1
    assert dp2['items'][0]['id'] != dp1['items'][0]['id']

    # Invalid pagination bounds
    r_zero = client.get(f'/api/v1/placements/{pid}/logs?page=0', headers=f['candidate']['headers'])
    assert r_zero.status_code == 422
    assert r_zero.json()['detail']['code'] == 'INVALID_PAGINATION'

    r_large = client.get(f'/api/v1/placements/{pid}/logs?page_size=101', headers=f['candidate']['headers'])
    assert r_large.status_code == 422
    assert r_large.json()['detail']['code'] == 'INVALID_PAGE_SIZE'


def test_reviews_and_tasks_inclusion_flags(client, identities, organization):
    f, _, _, _, _ = logs_setup(client, identities, organization)
    pid = f['placement']['id']

    # include_tasks=false and include_reviews=false
    r = client.get(
        f'/api/v1/placements/{pid}/logs?include_tasks=false&include_reviews=false',
        headers=f['candidate']['headers'],
    )
    assert r.status_code == 200, r.text
    data = r.json()
    for item in data['items']:
        rev = item['current_revision']
        assert 'tasks' not in rev
        assert 'workplace_reviews' not in rev
        assert 'academic_reviews' not in rev


def test_130_tables_migration_regression():
    """Verify runtime PostgreSQL schema contains all 130 tables including all log tables."""
    with transaction() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'flexbridge'")
        ).scalar_one()
        assert count == 130, f"Expected 130 tables, got {count}"

        # Verify daily_logs and log_revisions exist
        for tbl in ['daily_logs', 'log_revisions', 'log_task_entries', 'workplace_log_reviews', 'academic_log_reviews']:
            exists = conn.execute(
                text("SELECT 1 FROM information_schema.tables WHERE table_schema = 'flexbridge' AND table_name = :t"),
                {'t': tbl},
            ).scalar()
            assert exists == 1, f"Table flexbridge.{tbl} must exist"
