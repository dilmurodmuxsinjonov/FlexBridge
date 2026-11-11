"""Contract and functional tests for Application Review & HR Transitions (API-082, API-083, API-084 / CAP-008).

Specifications:
- API-082: GET /api/v1/opportunities/{id}/applications
  * Scoped strictly to applications submitted for the given opportunity.
  * Keyset cursor pagination over (created_at DESC, id DESC), status filter.
  * Returns contract_id: API-082.
- API-083: POST /api/v1/applications/{id}/transition
  * Validates state machine status transitions.
  * Appends event to application_events, updates version, and releases capacity if rejected.
  * Returns contract_id: API-083.
- API-084: GET /api/v1/applications/{id}/hr
  * Retrieves attempt snapshot, schedule matching score, and timeline of events.
  * Returns contract_id: API-084.
"""

from __future__ import annotations

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.db.storage import now, table, transaction
from test_candidate import published_fixture


def test_api082_list_opportunity_applications_empty(client: TestClient, identities, organization):
    """API-082: Returns empty application list when no candidates have applied."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    res = client.get(f"/api/v1/opportunities/{opp_id}/applications", headers=owner["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["contract_id"] == "API-082"
    assert data["opportunity_id"] == opp_id
    assert data["items"] == []
    assert data["has_more"] is False
    assert data["next_cursor"] is None


def test_api082_list_opportunity_applications_with_items_and_pagination(client: TestClient, identities, organization):
    """API-082: List multiple applications with keyset cursor pagination and status filter."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    # Candidate 1 applies
    c1 = identities()
    res1 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=c1["headers"] | {"Idempotency-Key": f"idem-c1-{uuid4()}"},
        json={"note": "Candidate 1 application"},
    )
    assert res1.status_code == 201, res1.text
    app1_id = res1.json()["id"]

    # Candidate 2 applies
    c2 = identities()
    res2 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=c2["headers"] | {"Idempotency-Key": f"idem-c2-{uuid4()}"},
        json={"note": "Candidate 2 application"},
    )
    assert res2.status_code == 201, res2.text
    app2_id = res2.json()["id"]

    # List page 1 with limit=1
    page1 = client.get(
        f"/api/v1/opportunities/{opp_id}/applications?limit=1",
        headers=owner["headers"],
    )
    assert page1.status_code == 200, page1.text
    d1 = page1.json()

    assert d1["contract_id"] == "API-082"
    assert len(d1["items"]) == 1
    assert d1["has_more"] is True
    assert d1["next_cursor"] is not None

    # List page 2 with next_cursor
    cursor = d1["next_cursor"]
    page2 = client.get(
        f"/api/v1/opportunities/{opp_id}/applications?limit=1&cursor={cursor}",
        headers=owner["headers"],
    )
    assert page2.status_code == 200, page2.text
    d2 = page2.json()

    assert len(d2["items"]) == 1
    # Page 1 item and Page 2 item must be distinct
    assert d1["items"][0]["application_id"] != d2["items"][0]["application_id"]

    # Filter by status=SUBMITTED
    sub_res = client.get(
        f"/api/v1/opportunities/{opp_id}/applications?status=SUBMITTED",
        headers=owner["headers"],
    )
    assert sub_res.status_code == 200
    assert len(sub_res.json()["items"]) == 2

    # Filter by status=REJECTED (empty)
    rej_res = client.get(
        f"/api/v1/opportunities/{opp_id}/applications?status=REJECTED",
        headers=owner["headers"],
    )
    assert rej_res.status_code == 200
    assert len(rej_res.json()["items"]) == 0


def test_api083_transition_application_state_machine_flow(client: TestClient, identities, organization):
    """API-083: Progress application through full valid state machine lifecycle."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-trans-{uuid4()}"},
        json={"note": "Initial submission"},
    )
    assert res.status_code == 201, res.text
    app_id = res.json()["id"]

    # 1. SUBMITTED -> REVIEWING
    t1 = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "REVIEWING", "reason": "HR started profile evaluation"},
    )
    assert t1.status_code == 200, t1.text
    d1 = t1.json()
    assert d1["contract_id"] == "API-083"
    assert d1["application_id"] == app_id
    assert d1["from_status"] == "SUBMITTED"
    assert d1["to_status"] == "REVIEWING"
    assert d1["version"] == 2

    # 2. REVIEWING -> SHORTLISTED
    t2 = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "SHORTLISTED", "reason": "Candidate meets requirements"},
    )
    assert t2.status_code == 200, t2.text
    d2 = t2.json()
    assert d2["from_status"] == "REVIEWING"
    assert d2["to_status"] == "SHORTLISTED"
    assert d2["version"] == 3

    # 3. SHORTLISTED -> INVITED_TO_INTERVIEW
    t3 = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "INVITED_TO_INTERVIEW", "reason": "Scheduling technical round"},
    )
    assert t3.status_code == 200, t3.text
    d3 = t3.json()
    assert d3["from_status"] == "SHORTLISTED"
    assert d3["to_status"] == "INVITED_TO_INTERVIEW"
    assert d3["version"] == 4

    # 4. INVITED_TO_INTERVIEW -> REJECTED
    t4 = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "REJECTED", "reason": "Position filled by another candidate"},
    )
    assert t4.status_code == 200, t4.text
    d4 = t4.json()
    assert d4["from_status"] == "INVITED_TO_INTERVIEW"
    assert d4["to_status"] == "REJECTED"
    assert d4["version"] == 5


def test_api083_capacity_release_on_rejection(client: TestClient, identities, organization):
    """API-083: If application occupied capacity, rejecting releases the capacity."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-cap-{uuid4()}"},
        json={"note": "Capacity release test"},
    )
    assert res.status_code == 201, res.text
    app_id = res.json()["id"]

    # Artificially simulate that capacity was occupied for this application
    with transaction() as conn:
        t_apps = table("applications")
        t_opp = table("opportunities")
        conn.execute(
            update(t_apps)
            .where(t_apps.c.id == app_id)
            .values(occupied_at=now(), status="REVIEWING")
        )
        conn.execute(
            update(t_opp)
            .where(t_opp.c.id == opp_id)
            .values(occupied_count=1)
        )

    # Reject the application
    rej = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "REJECTED", "reason": "Declined"},
    )
    assert rej.status_code == 200, rej.text

    # Verify database state
    with transaction() as conn:
        t_apps = table("applications")
        t_opp = table("opportunities")
        app_row = conn.execute(select(t_apps).where(t_apps.c.id == app_id)).mappings().first()
        opp_row = conn.execute(select(t_opp).where(t_opp.c.id == opp_id)).mappings().first()

        assert app_row["status"] == "REJECTED"
        assert app_row["released_at"] is not None
        assert opp_row["occupied_count"] == 0


def test_api084_get_application_hr_detail(client: TestClient, identities, organization):
    """API-084: HR retrieves candidate snapshot, schedule result, and event audit history."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-hr-view-{uuid4()}"},
        json={"note": "Cover letter text for HR review"},
    )
    assert res.status_code == 201, res.text
    app_id = res.json()["id"]

    # Transition once to add an event
    client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers=owner["headers"],
        json={"to_status": "REVIEWING", "reason": "Under active review"},
    )

    # Query HR snapshot
    hr_res = client.get(f"/api/v1/applications/{app_id}/hr", headers=owner["headers"])
    assert hr_res.status_code == 200, hr_res.text
    data = hr_res.json()

    assert data["contract_id"] == "API-084"
    assert data["application_id"] == app_id
    assert data["opportunity_id"] == opp_id
    assert data["status"] == "REVIEWING"
    assert data["version"] == 2

    # Attempt snapshot
    attempt = data["attempt"]
    assert attempt is not None
    assert attempt["attempt_no"] == 1
    assert attempt["revision_id"] == rev["id"]
    assert "headline" in attempt["profile_snapshot"]
    assert attempt["profile_snapshot"]["candidate_note"] == "Cover letter text for HR review"

    # Events history
    events = data["events"]
    assert len(events) >= 2
    assert events[0]["from_status"] is None
    assert events[0]["to_status"] == "SUBMITTED"
    assert events[1]["from_status"] == "SUBMITTED"
    assert events[1]["to_status"] == "REVIEWING"
    assert events[1]["reason"] == "Under active review"
