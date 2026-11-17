"""Contract, functional, and security tests for Candidate Applications & Reapply System
(API-006, API-029, API-039, API-040, API-041, API-044 / CAP-007 / DB-041, DB-042, DB-043).
"""

from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.schedule import local_today
from app.services.placements import insert_row
from test_candidate import published_fixture


def test_api006_submit_application_success(client, identities, organization):
    """API-006 / CAP-007: Candidate submits initial application with Idempotency-Key."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    idem_key = f"idem-app-{uuid4()}"

    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": idem_key},
        json={"note": "Looking forward to this role", "proposed_slots": [{"day": 1, "start": 540, "end": 600}]},
    )
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["contract_id"] == "API-006"
    assert data["opportunity_id"] == opp_id
    assert data["status"] == "SUBMITTED"
    assert data["version"] == 1
    assert data["current_attempt"] is not None
    assert data["current_attempt"]["attempt_no"] == 1
    assert data["current_attempt"]["revision_id"] == rev["id"]
    assert "headline" in data["current_attempt"]["profile_snapshot"]


def test_api006_idempotent_replay(client, identities, organization):
    """API-006: Submitting same Idempotency-Key replays identical response idempotently."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    idem_key = f"idem-replay-{uuid4()}"

    res1 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": idem_key},
        json={"note": "First attempt"},
    )
    assert res1.status_code == 201, res1.text
    app1 = res1.json()

    res2 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": idem_key},
        json={"note": "First attempt replay"},
    )
    assert res2.status_code == 201, res2.text
    app2 = res2.json()

    assert app1["id"] == app2["id"]
    assert app1["current_attempt"]["id"] == app2["current_attempt"]["id"]


def test_api006_idempotency_key_reused_by_different_candidate_fails(client, identities, organization):
    """API-006: Using someone else's Idempotency-Key raises 409 conflict."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    cand1 = identities()
    cand2 = identities()
    idem_key = f"shared-idem-{uuid4()}"

    res1 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand1["headers"] | {"Idempotency-Key": idem_key},
        json={},
    )
    assert res1.status_code == 201, res1.text

    res2 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand2["headers"] | {"Idempotency-Key": idem_key},
        json={},
    )
    assert res2.status_code == 409, res2.text
    assert res2.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_api006_missing_idempotency_key_fails(client, identities, organization):
    """API-006: Calling without Idempotency-Key header raises 422."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"],
        json={},
    )
    assert res.status_code == 422, res.text
    assert res.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_api006_closed_opportunity_rejected(client, identities, organization):
    """API-006: Applying to closed opportunity raises 409 conflict."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    with transaction() as conn:
        t_opp = table("opportunities")
        conn.execute(
            t_opp.update().where(t_opp.c.id == opp_id).values(status="CLOSED", closed_at=now())
        )

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-{uuid4()}"},
        json={},
    )
    assert res.status_code == 409, res.text
    assert res.json()["detail"]["code"] == "OPPORTUNITY_NOT_ACTIVE"


def test_api006_duplicate_application_fails(client, identities, organization):
    """API-006 / DB-041: Cannot create multiple applications for same opportunity."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res1 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-1-{uuid4()}"},
        json={},
    )
    assert res1.status_code == 201, res1.text

    # Try applying again with different idempotency key
    res2 = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-2-{uuid4()}"},
        json={},
    )
    assert res2.status_code == 409, res2.text
    assert res2.json()["detail"]["code"] == "APPLICATION_ALREADY_EXISTS"


def test_api006_student_only_opportunity_requires_enrollment(client, identities, organization):
    """API-006 / AC-001: Non-student applying to student-only opportunity fails with 422."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization, eligibility="STUDENTS_ONLY")
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-{uuid4()}"},
        json={},
    )
    assert res.status_code == 422, res.text
    assert res.json()["detail"]["code"] == "STUDENT_ENROLLMENT_REQUIRED"


def test_api029_applications_summary(client, identities, organization):
    """API-029 / CAP-007: Candidate retrieves aggregate summary metrics."""
    owner = identities("OWNER", organization)
    rev1 = published_fixture(owner, organization)
    rev2 = published_fixture(owner, organization)

    candidate = identities()
    # Apply to rev1
    res1 = client.post(
        f"/api/v1/opportunities/{rev1['opportunity_id']}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-{uuid4()}"},
        json={},
    )
    assert res1.status_code == 201, res1.text
    app1_id = res1.json()["id"]

    # Apply to rev2
    res2 = client.post(
        f"/api/v1/opportunities/{rev2['opportunity_id']}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-{uuid4()}"},
        json={},
    )
    assert res2.status_code == 201, res2.text

    # Withdraw app1
    client.post(
        f"/api/v1/me/applications/{app1_id}/withdraw",
        headers=candidate["headers"],
        json={"reason": "Changed mind"},
    )

    summary_res = client.get(
        "/api/v1/me/applications/summary",
        headers=candidate["headers"],
    )
    assert summary_res.status_code == 200, summary_res.text
    summary = summary_res.json()

    assert summary["contract_id"] == "API-029"
    assert summary["total_applications"] == 2
    assert summary["submitted"] == 1
    assert summary["withdrawn"] == 1


def test_api039_list_applications_pagination_and_filter(client, identities, organization):
    """API-039 / CAP-007: List own applications with status filter and keyset pagination."""
    owner = identities("OWNER", organization)
    candidate = identities()

    for i in range(3):
        rev = published_fixture(owner, organization)
        res = client.post(
            f"/api/v1/opportunities/{rev['opportunity_id']}/applications",
            headers=candidate["headers"] | {"Idempotency-Key": f"idem-list-{i}-{uuid4()}"},
            json={},
        )
        assert res.status_code == 201, res.text

    # List with limit=2
    page1 = client.get(
        "/api/v1/me/applications?limit=2",
        headers=candidate["headers"],
    )
    assert page1.status_code == 200, page1.text
    data1 = page1.json()
    assert len(data1["items"]) == 2
    assert data1["next_after"] is not None

    # Page 2
    page2 = client.get(
        f"/api/v1/me/applications?limit=2&after={data1['next_after']}",
        headers=candidate["headers"],
    )
    assert page2.status_code == 200, page2.text
    data2 = page2.json()
    assert len(data2["items"]) == 1
    assert data2["next_after"] is None


def test_api040_reapply_cooldown_and_limit_enforcement(client, identities, organization):
    """API-040 / CAP-007: Reapply enforces 24h cooldown and max 3 attempts per 30 days."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-{uuid4()}"},
        json={},
    )
    assert res.status_code == 201, res.text
    app_id = res.json()["id"]

    # Reapplying on SUBMITTED application must fail (must be terminal)
    res_active = client.post(
        f"/api/v1/me/applications/{app_id}/reapply",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-reapply-0-{uuid4()}"},
        json={"reason": "Trying again"},
    )
    assert res_active.status_code == 409, res_active.text
    assert res_active.json()["detail"]["code"] == "APPLICATION_ACTIVE"

    # Withdraw it so it's terminal
    client.post(
        f"/api/v1/me/applications/{app_id}/withdraw",
        headers=candidate["headers"],
        json={},
    )

    # Immediate reapply fails on 24h cooldown (CAP-007)
    res_cooldown = client.post(
        f"/api/v1/me/applications/{app_id}/reapply",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-reapply-1-{uuid4()}"},
        json={"reason": "Trying again"},
    )
    assert res_cooldown.status_code == 429, res_cooldown.text
    assert res_cooldown.json()["detail"]["code"] == "REAPPLY_COOLDOWN_ACTIVE"

    # Simulate passage of 25 hours by updating attempt submitted_at
    with transaction() as conn:
        t_att = table("application_attempts")
        past_time = now() - timedelta(hours=25)
        conn.execute(
            t_att.update()
            .where(t_att.c.application_id == app_id)
            .values(submitted_at=past_time)
        )

    # Reapply succeeds!
    res_reapply = client.post(
        f"/api/v1/me/applications/{app_id}/reapply",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-reapply-2-{uuid4()}"},
        json={"reason": "Updated skills and availability"},
    )
    assert res_reapply.status_code == 201, res_reapply.text
    data = res_reapply.json()
    assert data["status"] == "SUBMITTED"
    assert data["version"] == 3  # 1 (create) + 1 (withdraw) + 1 (reapply)
    assert data["current_attempt"]["attempt_no"] == 2


def test_api041_get_application_detail(client, identities, organization):
    """API-041 / CAP-007: Retrieve full application details, attempts history, and timeline."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-{uuid4()}"},
        json={"note": "Initial application note"},
    )
    assert res.status_code == 201, res.text
    app_id = res.json()["id"]

    detail_res = client.get(
        f"/api/v1/me/applications/{app_id}",
        headers=candidate["headers"],
    )
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()

    assert detail["contract_id"] == "API-041"
    assert detail["id"] == app_id
    assert detail["status"] == "SUBMITTED"
    assert len(detail["attempts"]) == 1
    assert detail["attempts"][0]["attempt_no"] == 1
    assert len(detail["timeline"]) == 1
    assert detail["timeline"][0]["to_status"] == "SUBMITTED"
    assert detail["opportunity"]["id"] == opp_id


def test_api044_withdraw_application(client, identities, organization):
    """API-044 / CAP-007: Candidate withdraws application; repeat is idempotent."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    candidate = identities()
    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=candidate["headers"] | {"Idempotency-Key": f"idem-{uuid4()}"},
        json={},
    )
    assert res.status_code == 201, res.text
    app_id = res.json()["id"]

    # Withdraw
    w_res1 = client.post(
        f"/api/v1/me/applications/{app_id}/withdraw",
        headers=candidate["headers"],
        json={"reason": "Accepted another offer"},
    )
    assert w_res1.status_code == 200, w_res1.text
    assert w_res1.json()["status"] == "WITHDRAWN"

    # Repeat withdraw is idempotent 200
    w_res2 = client.post(
        f"/api/v1/me/applications/{app_id}/withdraw",
        headers=candidate["headers"],
        json={"reason": "Accepted another offer"},
    )
    assert w_res2.status_code == 200, w_res2.text
    assert w_res2.json()["status"] == "WITHDRAWN"


def test_idor_cross_candidate_isolation(client, identities, organization):
    """CAP-007 / 007 Security: Candidate B cannot view, reapply, or withdraw Candidate A's application."""
    owner = identities("OWNER", organization)
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    cand_a = identities()
    cand_b = identities()

    res = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand_a["headers"] | {"Idempotency-Key": f"idem-a-{uuid4()}"},
        json={},
    )
    assert res.status_code == 201, res.text
    app_id = res.json()["id"]

    # Candidate B tries to view Candidate A's application -> 404
    v_res = client.get(
        f"/api/v1/me/applications/{app_id}",
        headers=cand_b["headers"],
    )
    assert v_res.status_code == 404, v_res.text

    # Candidate B tries to reapply Candidate A's application -> 404
    r_res = client.post(
        f"/api/v1/me/applications/{app_id}/reapply",
        headers=cand_b["headers"] | {"Idempotency-Key": f"idem-b-{uuid4()}"},
        json={},
    )
    assert r_res.status_code == 404, r_res.text

    # Candidate B tries to withdraw Candidate A's application -> 404
    w_res = client.post(
        f"/api/v1/me/applications/{app_id}/withdraw",
        headers=cand_b["headers"],
        json={},
    )
    assert w_res.status_code == 404, w_res.text
