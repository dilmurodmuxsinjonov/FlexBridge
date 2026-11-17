"""Unit, contract, and adversarial security tests for Organization Entitlements (API-070) & Billing Overview (API-093).

Contracts:
- API-070: GET /api/v1/organizations/{org}/entitlements (CAP-025, CAP-029 / BILLING)
- API-093: GET /api/v1/organizations/{org}/billing (CAP-026, CAP-029 / BILLING)
"""
from uuid import uuid4
import pytest
from app.db.storage import table, transaction, now
from test_regressions import checkout, capture


def test_org_entitlements_api070_empty_state_and_success(client, identities, organization):
    owner = identities("OWNER", organization)
    billing = identities("BILLING", organization)

    # 1. Fresh organization without entitlement returns safe default (no 500)
    res_empty = client.get(f"/api/v1/organizations/{organization}/entitlements", headers=owner["headers"])
    assert res_empty.status_code == 200, res_empty.text
    data_empty = res_empty.json()
    assert data_empty["contract_id"] == "API-070"
    assert data_empty["organization_id"] == organization
    assert data_empty["has_active_entitlement"] is False
    assert data_empty["active_entitlement"] is None
    assert data_empty["usage"]["concurrent_active_opportunities"] == 0
    assert data_empty["usage"]["concurrent_active_limit"] == 0

    # 2. Checkout and capture an ORG_PLAN_30D entitlement
    order, invoice, attempt = checkout(owner, organization, plan="ORG_PLAN_30D")
    capture(attempt)

    # 3. OWNER can retrieve active entitlement
    res_owner = client.get(f"/api/v1/organizations/{organization}/entitlements", headers=owner["headers"])
    assert res_owner.status_code == 200, res_owner.text
    assert res_owner.headers.get("cache-control") == "no-store"
    data_owner = res_owner.json()
    assert data_owner["contract_id"] == "API-070"
    assert data_owner["organization_id"] == organization
    assert data_owner["has_active_entitlement"] is True
    ent = data_owner["active_entitlement"]
    assert ent is not None
    assert ent["service_kind"] == "ORG_PLAN_30D"
    assert ent["status"] == "ACTIVE"
    assert ent["concurrent_active_limit"] == 5
    assert ent["concurrent_active_count"] == 0
    assert ent["concurrent_slots_remaining"] == 5
    assert ent["days_remaining"] > 0
    assert data_owner["usage"]["concurrent_active_limit"] == 5
    assert data_owner["usage"]["concurrent_slots_available"] == 5

    # 4. BILLING role can also retrieve active entitlement
    res_billing = client.get(f"/api/v1/organizations/{organization}/entitlements", headers=billing["headers"])
    assert res_billing.status_code == 200, res_billing.text
    data_billing = res_billing.json()
    assert data_billing["contract_id"] == "API-070"
    assert data_billing["has_active_entitlement"] is True
    assert data_billing["active_entitlement"]["service_kind"] == "ORG_PLAN_30D"


def test_org_billing_overview_api093_success(client, identities, organization):
    owner = identities("OWNER", organization)
    billing = identities("BILLING", organization)

    # 1. Fresh organization billing overview
    res_init = client.get(f"/api/v1/organizations/{organization}/billing", headers=owner["headers"])
    assert res_init.status_code == 200, res_init.text
    data_init = res_init.json()
    assert data_init["contract_id"] == "API-093"
    assert data_init["organization_id"] == organization
    assert data_init["plan"]["status"] == "INACTIVE"
    assert data_init["orders"] == []
    assert data_init["invoices"] == []

    # 2. Checkout and capture
    order, invoice, attempt = checkout(owner, organization, plan="ORG_PLAN_30D")
    capture(attempt)

    # 3. OWNER retrieves billing overview
    res_owner = client.get(f"/api/v1/organizations/{organization}/billing", headers=owner["headers"])
    assert res_owner.status_code == 200, res_owner.text
    assert res_owner.headers.get("cache-control") == "no-store"
    data_owner = res_owner.json()
    assert data_owner["contract_id"] == "API-093"
    assert data_owner["organization_id"] == organization
    assert data_owner["plan"]["code"] == "ORG_PLAN_30D"
    assert data_owner["plan"]["status"] == "ACTIVE"
    assert data_owner["entitlement"]["has_active"] is True
    assert data_owner["entitlement"]["concurrent_active_limit"] == 5

    # Orders check
    assert len(data_owner["orders"]) >= 1
    recent_order = data_owner["orders"][0]
    assert recent_order["amount"] == 599000
    assert recent_order["currency"] == "UZS"
    assert recent_order["status"] == "COMPLETED"

    # Invoices check
    assert len(data_owner["invoices"]) >= 1
    recent_inv = data_owner["invoices"][0]
    assert recent_inv["amount"] == 599000
    assert recent_inv["currency"] == "UZS"
    assert recent_inv["status"] == "PAID"
    assert recent_inv["paid_at"] is not None

    # 4. BILLING role retrieves identical billing overview
    res_billing = client.get(f"/api/v1/organizations/{organization}/billing", headers=billing["headers"])
    assert res_billing.status_code == 200, res_billing.text
    data_billing = res_billing.json()
    assert data_billing["contract_id"] == "API-093"
    assert data_billing["plan"]["code"] == "ORG_PLAN_30D"


def test_org_entitlements_and_billing_idor_and_unauthorized(client, identities, organization):
    owner = identities("OWNER", organization)
    hr = identities("HR", organization)
    outsider = identities()
    fake_org_id = str(uuid4())

    # 1. Unauthenticated (no token) -> 401
    assert client.get(f"/api/v1/organizations/{organization}/entitlements").status_code == 401
    assert client.get(f"/api/v1/organizations/{organization}/billing").status_code == 401

    # 2. Unauthorized internal role (HR is not OWNER or BILLING) -> 403 ORG_SCOPE_FORBIDDEN
    res_hr_ent = client.get(f"/api/v1/organizations/{organization}/entitlements", headers=hr["headers"])
    assert res_hr_ent.status_code == 403, res_hr_ent.text
    assert res_hr_ent.json()["detail"]["code"] == "ORG_SCOPE_FORBIDDEN"

    res_hr_bill = client.get(f"/api/v1/organizations/{organization}/billing", headers=hr["headers"])
    assert res_hr_bill.status_code == 403, res_hr_bill.text
    assert res_hr_bill.json()["detail"]["code"] == "ORG_SCOPE_FORBIDDEN"

    # 3. Outsider user without org membership -> 404 uniform IDOR
    res_out_ent = client.get(f"/api/v1/organizations/{organization}/entitlements", headers=outsider["headers"])
    assert res_out_ent.status_code == 404
    assert res_out_ent.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"

    res_out_bill = client.get(f"/api/v1/organizations/{organization}/billing", headers=outsider["headers"])
    assert res_out_bill.status_code == 404
    assert res_out_bill.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"

    # 4. Cross-tenant IDOR: Owner of Org A attempts to access Org B -> 404 uniform IDOR
    other_org = str(uuid4())
    with transaction() as conn:
        conn.execute(table("organizations").insert().values(
            id=other_org, created_at=now(), updated_at=now(),
            tax_id=str(uuid4())[:16], legal_name="Other Org", public_name="Other Org",
            region="Samarkand", status="VERIFIED"
        ))
    res_cross_ent = client.get(f"/api/v1/organizations/{other_org}/entitlements", headers=owner["headers"])
    assert res_cross_ent.status_code == 404
    assert res_cross_ent.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"

    res_cross_bill = client.get(f"/api/v1/organizations/{other_org}/billing", headers=owner["headers"])
    assert res_cross_bill.status_code == 404
    assert res_cross_bill.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"

    # 5. Non-existent org UUID -> 404 uniform IDOR
    res_fake_ent = client.get(f"/api/v1/organizations/{fake_org_id}/entitlements", headers=owner["headers"])
    assert res_fake_ent.status_code == 404
    assert res_fake_ent.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"

    res_fake_bill = client.get(f"/api/v1/organizations/{fake_org_id}/billing", headers=owner["headers"])
    assert res_fake_bill.status_code == 404
    assert res_fake_bill.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_org_entitlements_concurrent_count_reflection(client, identities, organization):
    owner = identities("OWNER", organization)
    order, invoice, attempt = checkout(owner, organization, plan="ORG_PLAN_30D")
    capture(attempt)

    # Initial concurrent active count is 0
    res1 = client.get(f"/api/v1/organizations/{organization}/entitlements", headers=owner["headers"])
    assert res1.json()["active_entitlement"]["concurrent_active_count"] == 0

    # Insert a published opportunity
    opp_id = str(uuid4())
    with transaction() as conn:
        conn.execute(table("opportunities").insert().values(
            id=opp_id, created_at=now(), updated_at=now(),
            organization_id=organization, kind="PART_TIME",
            status="PUBLISHED", capacity=2, occupied_count=0,
            published_at=now()
        ))

    # Entitlements reflects 1 concurrent active opportunity
    res2 = client.get(f"/api/v1/organizations/{organization}/entitlements", headers=owner["headers"])
    data2 = res2.json()
    assert data2["active_entitlement"]["concurrent_active_count"] == 1
    assert data2["active_entitlement"]["concurrent_slots_remaining"] == 4
    assert data2["usage"]["concurrent_active_opportunities"] == 1
    assert data2["usage"]["concurrent_slots_available"] == 4

    # Close the opportunity -> concurrent count returns to 0
    with transaction() as conn:
        t_opps = table("opportunities")
        conn.execute(t_opps.update().where(t_opps.c.id == opp_id).values(status="CLOSED"))

    res3 = client.get(f"/api/v1/organizations/{organization}/entitlements", headers=owner["headers"])
    data3 = res3.json()
    assert data3["active_entitlement"]["concurrent_active_count"] == 0
    assert data3["active_entitlement"]["concurrent_slots_remaining"] == 5
