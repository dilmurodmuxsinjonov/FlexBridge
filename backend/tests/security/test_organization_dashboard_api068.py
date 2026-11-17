"""Contract and functional tests for Organization HR Dashboard & Public Profiles (API-068, API-009, API-010 / CAP-015, CAP-001, CAP-027)."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def _create_rubric(status: str = "ACTIVE") -> str:
    rubric_id = str(uuid4())
    with transaction() as conn:
        insert_row(
            conn,
            "rubric_versions",
            id=rubric_id,
            family="WORKPLACE_JOB",
            version=1,
            status=status,
            scale_min=1,
            scale_max=5,
            published_at=now(),
        )
    return rubric_id


def _create_opp(conn, org_id, author_id, title="Test Opp", status="PUBLISHED", capacity=2, occupied=0, kind="PART_TIME", delta_minutes=0):
    opp_id = str(uuid4())
    rev_id = str(uuid4())
    created = now() - timedelta(minutes=delta_minutes)
    insert_row(
        conn,
        "opportunities",
        id=opp_id,
        organization_id=org_id,
        kind=kind,
        status=status,
        capacity=capacity,
        occupied_count=occupied,
        created_at=created,
    )
    insert_row(
        conn,
        "opportunity_revisions",
        id=rev_id,
        opportunity_id=opp_id,
        revision=1,
        author_id=author_id,
        title=title,
        description="Preserve the snapshot",
        work_mode="REMOTE",
        region="Tashkent",
        eligibility="OPEN",
        contract_type="INTERNSHIP_AGREEMENT" if kind == "INTERNSHIP" else "LABOR_PART_TIME",
        currency="UZS",
        is_paid=False,
        start_date=created.date(),
        schedule_policy="FIXED",
        shift_match_mode="ANY",
        snapshot_schema=1,
        created_at=created,
    )
    conn.execute(
        table("opportunities").update().where(table("opportunities").c.id == opp_id).values(current_revision_id=rev_id)
    )
    return opp_id


def test_organization_dashboard_zero_data(client, identities, organization):
    """API-068: Empty organization returns 200 with zero counts (no division by zero or NoneType)."""
    org_id = organization
    owner = identities("OWNER", org_id)

    res = client.get(f"/api/v1/organizations/{org_id}/dashboard", headers=owner["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-068"
    assert data["organization_id"] == org_id
    assert data["opportunities"]["total"] == 0
    assert data["opportunities"]["draft"] == 0
    assert data["opportunities"]["published"] == 0
    assert data["applications"]["total"] == 0
    assert data["engagements"]["total"] == 0
    assert data["interviews"]["total"] == 0


def test_organization_dashboard_counts_breakdown(client, identities, organization):
    """API-068: Aggregated metrics accurately match database records across domains."""
    org_id = organization
    owner = identities("OWNER", org_id)
    hr_user = identities("HR", org_id)
    candidate_1 = identities()
    candidate_2 = identities()

    author_id = hr_user["user_id"]
    with transaction() as conn:
        opp_draft = _create_opp(conn, org_id, author_id, "Junior Dev", "DRAFT", 2, 0)
        opp_pub1 = _create_opp(conn, org_id, author_id, "Senior Dev", "PUBLISHED", 3, 0)
        opp_pub2 = _create_opp(conn, org_id, author_id, "Intern QA", "PUBLISHED", 1, 0, kind="INTERNSHIP")
        opp_closed = _create_opp(conn, org_id, author_id, "Closed Architect", "CLOSED", 1, 1)

    # 1. Candidate 1 applies to opp_pub1
    res_app1 = client.post(
        f"/api/v1/opportunities/{opp_pub1}/applications",
        headers=candidate_1["headers"] | {"Idempotency-Key": f"app-{uuid4()}"},
        json={"note": "Applying for senior dev"},
    )
    assert res_app1.status_code == 201, res_app1.text
    app1_id = res_app1.json()["id"]

    # 2. Host schedules interview for app1
    now_utc = datetime.now(timezone.utc)
    s_time = (now_utc + timedelta(days=2)).isoformat()
    e_time = (now_utc + timedelta(days=2, hours=1)).isoformat()
    res_int = client.post(
        f"/api/v1/applications/{app1_id}/interviews",
        headers=owner["headers"],
        json={
            "starts_at": s_time,
            "ends_at": e_time,
            "timezone": "Asia/Tashkent",
            "mode": "ONLINE",
            "location_or_link": "https://meet.google.com/xyz",
        },
    )
    assert res_int.status_code in (200, 201), res_int.text

    # 3. Candidate 2 applies to opp_pub1
    res_app2 = client.post(
        f"/api/v1/opportunities/{opp_pub1}/applications",
        headers=candidate_2["headers"] | {"Idempotency-Key": f"app-{uuid4()}"},
        json={"note": "Applying for job"},
    )
    assert res_app2.status_code == 201, res_app2.text
    app2_id = res_app2.json()["id"]

    # 4. Host issues offer to Candidate 2
    res_off = client.post(
        f"/api/v1/applications/{app2_id}/offers",
        headers=owner["headers"],
        json={"terms_snapshot": {"position": "Senior Dev", "rate": 60000}},
    )
    assert res_off.status_code == 200, res_off.text
    offer_id = res_off.json()["id"]

    # 5. Candidate 2 accepts offer -> produces engagement
    res_acc = client.post(
        f"/api/v1/offers/{offer_id}/respond",
        headers=candidate_2["headers"],
        json={"decision": "ACCEPT"},
    )
    assert res_acc.status_code == 200, res_acc.text
    eng_id = res_acc.json().get("engagement_id")
    assert eng_id is not None

    # 6. Confirm start so engagement status becomes ACTIVE
    client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=candidate_2["headers"],
        json={"action": "CONFIRM_START", "party": "CANDIDATE"},
    )
    client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=owner["headers"],
        json={"action": "CONFIRM_START", "party": "EMPLOYER"},
    )

    # 7. HR queries dashboard
    res = client.get(f"/api/v1/organizations/{org_id}/dashboard", headers=hr_user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-068"
    assert data["opportunities"]["total"] == 4
    assert data["opportunities"]["draft"] == 1
    assert data["opportunities"]["published"] == 2
    assert data["opportunities"]["closed"] == 1
    assert data["applications"]["total"] == 2
    assert data["engagements"]["total"] == 1
    assert data["engagements"]["active"] == 1
    assert data["interviews"]["total"] == 1
    assert data["interviews"]["scheduled"] == 1


def test_organization_dashboard_authorized_roles(client, identities, organization):
    """API-068: OWNER, HR, and HOST_COORDINATOR can all access dashboard."""
    org_id = organization
    owner = identities("OWNER", org_id)
    hr = identities("HR", org_id)
    host_coord = identities("HOST_COORDINATOR", org_id)

    for role_user in (owner, hr, host_coord):
        res = client.get(f"/api/v1/organizations/{org_id}/dashboard", headers=role_user["headers"])
        assert res.status_code == 200, res.text
        assert res.json()["contract_id"] == "API-068"


def test_public_opportunities_api_009_published_only(client, identities, organization):
    """API-009: Public endpoint only reveals PUBLISHED opportunities, hiding DRAFT and CLOSED."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        _create_opp(conn, org_id, owner["user_id"], "Visible Job", "PUBLISHED", 5, 2)
        _create_opp(conn, org_id, owner["user_id"], "Secret Draft", "DRAFT", 1, 0)
        _create_opp(conn, org_id, owner["user_id"], "Archived Old", "CLOSED", 1, 1)

    # Public unauthenticated request
    res = client.get(f"/api/v1/organizations/{org_id}/opportunities")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-009"
    assert data["organization_id"] == org_id
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Visible Job"
    assert data["items"][0]["vacancies_available"] == 3


def test_public_opportunities_api_009_keyset_pagination(client, identities, organization):
    """API-009: Keyset cursor pagination over (created_at, id)."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        for i in range(5):
            _create_opp(conn, org_id, owner["user_id"], f"Position #{i}", "PUBLISHED", 1, 0, delta_minutes=i)

    # First page: limit 2
    res1 = client.get(f"/api/v1/organizations/{org_id}/opportunities?limit=2")
    assert res1.status_code == 200, res1.text
    d1 = res1.json()
    assert len(d1["items"]) == 2
    assert d1["has_more"] is True
    assert d1["next_cursor"] is not None

    # Second page: with cursor
    res2 = client.get(f"/api/v1/organizations/{org_id}/opportunities?limit=2&after={d1['next_cursor']}")
    assert res2.status_code == 200, res2.text
    d2 = res2.json()
    assert len(d2["items"]) == 2
    # Ensure items are disjoint
    ids_p1 = {item["id"] for item in d1["items"]}
    ids_p2 = {item["id"] for item in d2["items"]}
    assert ids_p1.isdisjoint(ids_p2)


def test_public_rating_summary_api_010_unrated(client, organization):
    """API-010: Organization without rating submissions returns UNRATED."""
    org_id = organization

    res = client.get(f"/api/v1/organizations/{org_id}/rating-summary")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-010"
    assert data["target_org_id"] == org_id
    assert data["score"] is None
    assert data["score_status"] == "UNRATED"
    assert data["sample_size"] == 0


def test_public_rating_summary_api_010_privacy_threshold(client, organization):
    """API-010: AC-023 sample size threshold (< 5) suppresses numeric rating score."""
    org_id = organization
    rubric_id = _create_rubric()

    with transaction() as conn:
        insert_row(
            conn,
            "rating_aggregates",
            id=str(uuid4()),
            target_org_id=org_id,
            rubric_id=rubric_id,
            sample_size=3,
            score=4.67,
            window_start=now().date() - timedelta(days=90),
            window_end=now().date(),
            computed_at=now(),
        )

    res = client.get(f"/api/v1/organizations/{org_id}/rating-summary")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-010"
    assert data["score"] is None
    assert data["score_status"] == "WITHHELD_INSUFFICIENT_SAMPLE"
    assert data["sample_size"] == 3


def test_public_rating_summary_api_010_published(client, organization):
    """API-010: AC-023 publishes rating when n >= 5."""
    org_id = organization
    rubric_id = _create_rubric()

    with transaction() as conn:
        insert_row(
            conn,
            "rating_aggregates",
            id=str(uuid4()),
            target_org_id=org_id,
            rubric_id=rubric_id,
            sample_size=6,
            score=4.85,
            window_start=now().date() - timedelta(days=90),
            window_end=now().date(),
            computed_at=now(),
        )

    res = client.get(f"/api/v1/organizations/{org_id}/rating-summary")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-010"
    assert data["score"] == 4.85
    assert data["score_status"] == "PUBLISHED"
    assert data["sample_size"] == 6
