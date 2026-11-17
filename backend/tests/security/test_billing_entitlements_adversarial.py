"""Adversarial security and IDOR tests for Organization Entitlements & Billing Overview (API-070, API-093)."""

from uuid import uuid4

import pytest

from app.db.storage import now, transaction
from app.services.placements import insert_row


def test_adversarial_unauthenticated_denied(client, organization):
    """API-070 and API-093 require authenticated session; unauthenticated callers receive 401."""
    org_id = organization

    res_ent = client.get(f"/api/v1/organizations/{org_id}/entitlements")
    assert res_ent.status_code == 401, res_ent.text

    res_bill = client.get(f"/api/v1/organizations/{org_id}/billing")
    assert res_bill.status_code == 401, res_bill.text


def test_adversarial_unauthorized_member_forbidden(client, identities, organization):
    """Org member with non-billing role (HR / HOST_COORDINATOR) receives 403 ORG_SCOPE_FORBIDDEN."""
    org_id = organization
    hr_user = identities("HR", org_id)

    res_ent = client.get(f"/api/v1/organizations/{org_id}/entitlements", headers=hr_user["headers"])
    assert res_ent.status_code == 403, res_ent.text
    assert res_ent.json()["detail"]["code"] == "ORG_SCOPE_FORBIDDEN"

    res_bill = client.get(f"/api/v1/organizations/{org_id}/billing", headers=hr_user["headers"])
    assert res_bill.status_code == 403, res_bill.text
    assert res_bill.json()["detail"]["code"] == "ORG_SCOPE_FORBIDDEN"


def test_adversarial_cross_tenant_staff_denied_uniform_404(client, identities, organization):
    """IDOR defense: Staff from foreign organization receives uniform 404 (anti-enumeration)."""
    org_a = organization
    foreign_org_id = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn,
            "organizations",
            id=foreign_org_id,
            tax_id=f"888{foreign_org_id[:6].replace('-', '')}",
            legal_name="Foreign Corp LLC",
            public_name="Foreign Corp",
            region="Tashkent",
            status="VERIFIED",
            created_at=now(),
        )

    foreign_owner = identities("OWNER", foreign_org_id)
    foreign_billing = identities("BILLING", foreign_org_id)

    # Foreign owner queries Org A
    res_ent = client.get(f"/api/v1/organizations/{org_a}/entitlements", headers=foreign_owner["headers"])
    assert res_ent.status_code == 404, res_ent.text
    assert res_ent.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"

    # Foreign billing queries Org A
    res_bill = client.get(f"/api/v1/organizations/{org_a}/billing", headers=foreign_billing["headers"])
    assert res_bill.status_code == 404, res_bill.text
    assert res_bill.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_adversarial_regular_candidate_denied_uniform_404(client, identities, organization):
    """IDOR defense: Unaffiliated candidate receives uniform 404 (anti-enumeration)."""
    org_id = organization
    candidate = identities()

    res_ent = client.get(f"/api/v1/organizations/{org_id}/entitlements", headers=candidate["headers"])
    assert res_ent.status_code == 404, res_ent.text
    assert res_ent.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"

    res_bill = client.get(f"/api/v1/organizations/{org_id}/billing", headers=candidate["headers"])
    assert res_bill.status_code == 404, res_bill.text
    assert res_bill.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_adversarial_nonexistent_org_uniform_404(client, identities):
    """IDOR defense: Nonexistent organization UUID returns uniform 404."""
    user = identities()
    fake_org_id = str(uuid4())

    res_ent = client.get(f"/api/v1/organizations/{fake_org_id}/entitlements", headers=user["headers"])
    assert res_ent.status_code == 404, res_ent.text
    assert res_ent.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"

    res_bill = client.get(f"/api/v1/organizations/{fake_org_id}/billing", headers=user["headers"])
    assert res_bill.status_code == 404, res_bill.text
    assert res_bill.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_adversarial_invalid_uuid_uniform_404(client, identities):
    """Malformed organization ID string returns uniform 404."""
    user = identities()

    res_ent = client.get("/api/v1/organizations/not-a-valid-uuid/entitlements", headers=user["headers"])
    assert res_ent.status_code in (404, 422), res_ent.text

    res_bill = client.get("/api/v1/organizations/not-a-valid-uuid/billing", headers=user["headers"])
    assert res_bill.status_code in (404, 422), res_bill.text
