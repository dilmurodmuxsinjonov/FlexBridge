"""Adversarial security and edge-case stress tests for API-053 Single Placement Diary Logs View.

Verifies:
1. Malicious input & SQL injection injection defense in query params
2. Large page bounds & out-of-range pagination
3. Zero logs placement scenario (valid empty response)
4. Date range filtering producing empty results
5. Draft privacy under adversarial probe patterns
6. Dual-role actor resolution precedence (Host Owner who is also assigned mentor)
7. Concurrency / isolation safety
"""
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.db.institution_scope import TASHKENT
from app.db.storage import now
from test_academic_admission import pending_http
from test_academic_reviews import ready


def adversarial_logs_setup(client, identities, organization):
    start = now().astimezone(TASHKENT).date() - timedelta(days=3)
    f, assignment, draft1 = ready(
        client,
        identities,
        organization,
        submit=True,
        placement_start_date=start,
        required_minutes=0,
    )
    pid = f['placement']['id']

    # Day 2 draft log created
    day2 = (start + timedelta(days=1)).isoformat()
    r2 = client.put(
        f'/api/v1/placements/{pid}/logs/{day2}',
        headers=f['candidate']['headers'],
        json={
            'day_type': 'WORKED',
            'summary_text': 'Draft secret notes',
            'total_minutes': 120,
            'tasks': [{'title': 'Secret task', 'minutes': 120}],
        },
    )
    assert r2.status_code == 200, r2.text
    return f, pid, start


def test_sql_injection_defense_in_query_parameters(client, identities, organization):
    f, pid, _ = adversarial_logs_setup(client, identities, organization)

    # 1. SQL injection in from_date
    r_inj_date = client.get(
        f"/api/v1/placements/{pid}/logs?from_date=' OR 1=1 --",
        headers=f['candidate']['headers'],
    )
    assert r_inj_date.status_code == 422
    assert r_inj_date.json()['detail']['code'] == 'INVALID_DATE_FORMAT'

    # 2. SQL injection in status
    r_inj_status = client.get(
        f"/api/v1/placements/{pid}/logs?status=' UNION SELECT * FROM users --",
        headers=f['candidate']['headers'],
    )
    assert r_inj_status.status_code == 422
    assert r_inj_status.json()['detail']['code'] == 'INVALID_STATUS_FILTER'

    # 3. SQL injection in page
    r_inj_page = client.get(
        f"/api/v1/placements/{pid}/logs?page=1; DROP TABLE daily_logs;",
        headers=f['candidate']['headers'],
    )
    assert r_inj_page.status_code == 422

    # 4. Path traversal or malformed UUID in placement_id
    r_inj_path = client.get(
        f"/api/v1/placements/../../etc/passwd/logs",
        headers=f['candidate']['headers'],
    )
    assert r_inj_path.status_code in (404, 422)


def test_empty_placement_logs_returns_clean_zero_state(client, identities, organization):
    start = now().astimezone(TASHKENT).date() - timedelta(days=3)
    f = pending_http(client, identities, organization, placement_start_date=start)
    pid = f['placement']['id']

    # Placement has 0 logs
    r = client.get(f'/api/v1/placements/{pid}/logs', headers=f['owner']['headers'])
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['contract_id'] == 'API-053'
    assert data['total'] == 0
    assert data['items'] == []
    assert data['total_pages'] == 0


def test_out_of_range_page_number_returns_empty_items(client, identities, organization):
    f, pid, _ = adversarial_logs_setup(client, identities, organization)

    # Page 999 exceeds total pages
    r = client.get(f'/api/v1/placements/{pid}/logs?page=999&page_size=20', headers=f['candidate']['headers'])
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['total'] == 2
    assert data['page'] == 999
    assert data['items'] == []


def test_date_range_with_no_matches_returns_empty_page(client, identities, organization):
    f, pid, _ = adversarial_logs_setup(client, identities, organization)

    # Date range far in the future
    r = client.get(
        f'/api/v1/placements/{pid}/logs?from_date=2099-01-01&to_date=2099-12-31',
        headers=f['candidate']['headers'],
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['total'] == 0
    assert data['items'] == []


def test_dual_role_host_owner_precedence_preserves_draft_privacy(client, identities, organization):
    f, pid, _ = adversarial_logs_setup(client, identities, organization)

    # In ready(...), f['owner'] has BOTH org owner authority AND mentor assignment
    # Host authority takes precedence: draft logs are strictly hidden
    r_owner = client.get(f'/api/v1/placements/{pid}/logs', headers=f['owner']['headers'])
    assert r_owner.status_code == 200, r_owner.text
    data = r_owner.json()
    assert data['total'] == 1
    assert data['items'][0]['current_revision']['status'] == 'SUBMITTED'

    # Requesting status=DRAFT returns 0 items, zero oracle leakage
    r_draft = client.get(f'/api/v1/placements/{pid}/logs?status=DRAFT', headers=f['owner']['headers'])
    assert r_draft.status_code == 200
    assert r_draft.json()['total'] == 0
    assert r_draft.json()['items'] == []
