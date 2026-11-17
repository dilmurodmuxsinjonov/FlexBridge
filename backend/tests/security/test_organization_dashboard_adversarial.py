"""Adversarial security and IDOR tests for Organization Dashboard & Public Endpoints (API-068, API-009, API-010)."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def _create_opp(conn, org_id, author_id, title="Test Opp", status="PUBLISHED", capacity=2, occupied=0, kind="PART_TIME", closed_at=None):
    opp_id = str(uuid4())
    rev_id = str(uuid4())
    insert_row(
        conn,
        "opportunities",
        id=opp_id,
        organization_id=org_id,
        kind=kind,
        status=status,
        capacity=capacity,
        occupied_count=occupied,
        closed_at=closed_at,
        created_at=now(),
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
        start_date=now().date(),
        schedule_policy="FIXED",
        shift_match_mode="ANY",
        snapshot_schema=1,
        created_at=now(),
    )
    conn.execute(
        table("opportunities").update().where(table("opportunities").c.id == opp_id).values(current_revision_id=rev_id)
    )
    return opp_id


def test_adversarial_idor_foreign_org_staff_denied(client, identities, organization):
    """API-068 IDOR: Staff member of foreign organization receives uniform 404 (anti-enumeration)."""
    org_a = organization
    foreign_org_id = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn,
            "organizations",
            id=foreign_org_id,
            tax_id=f"999{foreign_org_id[:6].replace('-', '')}",
            legal_name="Foreign Org LLC",
            public_name="Foreign Org",
            region="Tashkent",
            status="VERIFIED",
            created_at=now(),
        )

    foreign_hr = identities("HR", foreign_org_id)

    # Foreign HR attempts to view Org A's dashboard
    res = client.get(f"/api/v1/organizations/{org_a}/dashboard", headers=foreign_hr["headers"])
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_adversarial_idor_candidate_denied(client, identities, organization):
    """API-068 IDOR: Unaffiliated candidate receives uniform 404."""
    org_id = organization
    candidate = identities()

    res = client.get(f"/api/v1/organizations/{org_id}/dashboard", headers=candidate["headers"])
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_adversarial_unauthenticated_dashboard_denied(client, organization):
    """API-068: Unauthenticated access is blocked by auth boundary with 401."""
    res = client.get(f"/api/v1/organizations/{organization}/dashboard")
    assert res.status_code == 401, res.text
    assert res.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_adversarial_revoked_member_denied(client, identities, organization):
    """API-068: Revoked org membership receives uniform 404."""
    org_id = organization
    hr_user = identities("HR", org_id)

    with transaction() as conn:
        t_members = table("org_memberships")
        conn.execute(
            t_members.update()
            .where(t_members.c.organization_id == org_id, t_members.c.user_id == hr_user["user_id"])
            .values(status="REVOKED", revoked_at=now())
        )

    res = client.get(f"/api/v1/organizations/{org_id}/dashboard", headers=hr_user["headers"])
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_adversarial_nonexistent_org_uniform_404(client, identities):
    """API-068: Nonexistent organization UUID produces uniform 404."""
    user = identities()
    fake_org_id = str(uuid4())

    res = client.get(f"/api/v1/organizations/{fake_org_id}/dashboard", headers=user["headers"])
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_adversarial_invalid_uuid_uniform_404(client, identities):
    """API-068: Malformed organization identifier safely produces 404 or 422 validation rejection."""
    user = identities()
    for bad_id in ("not-a-uuid", "12345", "admin", "null"):
        res = client.get(f"/api/v1/organizations/{bad_id}/dashboard", headers=user["headers"])
        assert res.status_code in (404, 422), res.text


def test_adversarial_tenant_isolation(client, identities, organization):
    """API-068: Cross-tenant metrics never leak between distinct organizations."""
    org_a = organization
    org_b = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn,
            "organizations",
            id=org_b,
            tax_id=f"888{org_b[:6].replace('-', '')}",
            legal_name="Tenant B Corp",
            public_name="Tenant B",
            region="Samarkand",
            status="VERIFIED",
            created_at=now(),
        )

    owner_b = identities("OWNER", org_b)

    with transaction() as conn:
        # Create 10 opportunities for Org B
        for i in range(10):
            _create_opp(conn, org_b, owner_b["user_id"], f"Org B Opp #{i}", "PUBLISHED")

    owner_a = identities("OWNER", org_a)

    # Query Org A's dashboard: must remain 0 despite Org B having 10 opportunities
    res = client.get(f"/api/v1/organizations/{org_a}/dashboard", headers=owner_a["headers"])
    assert res.status_code == 200, res.text
    assert res.json()["opportunities"]["total"] == 0
    assert res.json()["opportunities"]["published"] == 0


def test_adversarial_public_opportunities_nonexistent_org_404(client):
    """API-009: Nonexistent org in public opportunities returns 404."""
    fake_id = str(uuid4())
    res = client.get(f"/api/v1/organizations/{fake_id}/opportunities")
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_adversarial_public_opportunities_closed_suppressed(client, identities, organization):
    """API-009: Opportunities with status CLOSED are suppressed from public opportunities."""
    org_id = organization
    owner = identities("OWNER", org_id)

    with transaction() as conn:
        _create_opp(conn, org_id, owner["user_id"], "Closed Opp", "CLOSED", closed_at=now())

    res = client.get(f"/api/v1/organizations/{org_id}/opportunities")
    assert res.status_code == 200, res.text
    assert len(res.json()["items"]) == 0


def test_adversarial_public_rating_summary_nonexistent_org_404(client):
    """API-010: Nonexistent org in public rating summary returns 404."""
    fake_id = str(uuid4())
    res = client.get(f"/api/v1/organizations/{fake_id}/rating-summary")
    assert res.status_code == 404, res.text
    assert res.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"
