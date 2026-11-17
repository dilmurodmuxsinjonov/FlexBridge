"""Functional and contract tests for Organization Entitlements & Billing Overview (API-070, API-093 / CAP-025, CAP-026, CAP-029)."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.billing import billing_service
from app.services.placements import insert_row


def _create_opp(conn, org_id, author_id, title="Test Opp", status="PUBLISHED", capacity=2, occupied=0, kind="PART_TIME"):
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
        published_at=now(),
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
        description="Preserve snapshot",
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


def test_api070_org_entitlements_no_active(client, identities, organization):
    """API-070: Organization with no active entitlement returns 200 with has_active_entitlement=False."""
    org_id = organization
    owner = identities("OWNER", org_id)

    res = client.get(f"/api/v1/organizations/{org_id}/entitlements", headers=owner["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-070"
    assert data["organization_id"] == org_id
    assert data["has_active_entitlement"] is False
    assert data["active_entitlement"] is None
    assert "usage" in data
    assert data["usage"]["concurrent_active_opportunities"] == 0
    assert data["usage"]["concurrent_active_limit"] == 0
    assert data["usage"]["concurrent_slots_available"] == 0


def test_api070_org_entitlements_active_with_usage(client, identities, organization):
    """API-070: Active entitlement accurately reflects quota, days remaining, and concurrent usage."""
    org_id = organization
    owner = identities("OWNER", org_id)
    billing_user = identities("BILLING", org_id)

    ent_id = str(uuid4())
    order_id = str(uuid4())
    with transaction() as conn:
        price_id, _ = billing_service._seed_tariff(conn, "ORG_PLAN_30D")
        insert_row(
            conn,
            "orders",
            id=order_id,
            organization_id=org_id,
            purchaser_id=owner["user_id"],
            price_id=price_id,
            amount=599000,
            currency="UZS",
            price_snapshot={"plan_code": "ORG_PLAN_30D", "price_uzs": 599000, "concurrent_active_limit": 5, "duration_days": 30},
            status="COMPLETED",
            idempotency_key=str(uuid4()),
            created_at=now(),
        )
        insert_row(
            conn,
            "service_entitlements",
            id=ent_id,
            organization_id=org_id,
            order_id=order_id,
            service_kind="ORG_PLAN_30D",
            status="ACTIVE",
            starts_at=now() - timedelta(days=2),
            ends_at=now() + timedelta(days=28),
            quota=10,
            concurrent_active_limit=5,
            created_at=now(),
        )
        _create_opp(conn, org_id, owner["user_id"], "Active Dev Job 1", status="PUBLISHED")
        _create_opp(conn, org_id, owner["user_id"], "Active Dev Job 2", status="PUBLISHED")

    # Verify query via BILLING user
    res = client.get(f"/api/v1/organizations/{org_id}/entitlements", headers=billing_user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-070"
    assert data["has_active_entitlement"] is True
    ent = data["active_entitlement"]
    assert ent["id"] == ent_id
    assert ent["service_kind"] == "ORG_PLAN_30D"
    assert ent["status"] == "ACTIVE"
    assert ent["quota"] == 10
    assert ent["concurrent_active_limit"] == 5
    assert ent["concurrent_active_count"] == 2
    assert ent["concurrent_slots_remaining"] == 3
    assert ent["days_remaining"] >= 27

    usage = data["usage"]
    assert usage["concurrent_active_opportunities"] == 2
    assert usage["concurrent_active_limit"] == 5
    assert usage["concurrent_slots_available"] == 3
    assert usage["quota_remaining"] == 10


def test_api093_org_billing_overview_empty(client, identities, organization):
    """API-093: Empty organization billing overview returns default FREE plan and empty collections."""
    org_id = organization
    owner = identities("OWNER", org_id)

    res = client.get(f"/api/v1/organizations/{org_id}/billing", headers=owner["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-093"
    assert data["organization_id"] == org_id
    assert data["plan"]["code"] == "FREE"
    assert data["plan"]["status"] == "INACTIVE"
    assert data["entitlement"]["has_active"] is False
    assert data["orders"] == []
    assert data["invoices"] == []


def test_api093_org_billing_overview_with_orders_and_invoices(client, identities, organization):
    """API-093: Billing overview accurately returns orders, invoices, and active entitlement snapshot."""
    org_id = organization
    billing_user = identities("BILLING", org_id)

    order_id = str(uuid4())
    inv_id = str(uuid4())
    ent_id = str(uuid4())

    with transaction() as conn:
        price_id, _ = billing_service._seed_tariff(conn, "ORG_PLAN_30D")
        insert_row(
            conn,
            "orders",
            id=order_id,
            organization_id=org_id,
            purchaser_id=billing_user["user_id"],
            price_id=price_id,
            amount=599000,
            currency="UZS",
            price_snapshot={"plan_code": "ORG_PLAN_30D", "price_uzs": 599000, "concurrent_active_limit": 5, "duration_days": 30},
            status="COMPLETED",
            idempotency_key=str(uuid4()),
            created_at=now(),
        )
        insert_row(
            conn,
            "invoices",
            id=inv_id,
            order_id=order_id,
            number="FB-INV-001",
            amount=599000,
            currency="UZS",
            fiscal_status="COMPLETED",
            issued_at=now() - timedelta(days=1),
            paid_at=now(),
            created_at=now() - timedelta(days=1),
        )
        insert_row(
            conn,
            "service_entitlements",
            id=ent_id,
            organization_id=org_id,
            order_id=order_id,
            service_kind="ORG_PLAN_30D",
            status="ACTIVE",
            starts_at=now(),
            ends_at=now() + timedelta(days=30),
            quota=None,
            concurrent_active_limit=5,
            created_at=now(),
        )

    res = client.get(f"/api/v1/organizations/{org_id}/billing", headers=billing_user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-093"
    assert data["organization_id"] == org_id
    assert data["plan"]["code"] == "ORG_PLAN_30D"
    assert data["plan"]["status"] == "ACTIVE"
    assert data["entitlement"]["has_active"] is True
    assert data["entitlement"]["service_kind"] == "ORG_PLAN_30D"
    assert data["entitlement"]["concurrent_active_limit"] == 5

    assert len(data["orders"]) == 1
    ord_rec = data["orders"][0]
    assert ord_rec["id"] == order_id
    assert ord_rec["amount"] == 599000
    assert ord_rec["plan_code"] == "ORG_PLAN_30D"

    assert len(data["invoices"]) == 1
    inv_rec = data["invoices"][0]
    assert inv_rec["id"] == inv_id
    assert inv_rec["order_id"] == order_id
    assert inv_rec["number"] == "FB-INV-001"
    assert inv_rec["status"] == "PAID"
    assert inv_rec["amount"] == 599000


def test_platform_admin_access_api070_093(client, identities, organization):
    """Platform ADMIN can access organization entitlements and billing without explicit org membership."""
    org_id = organization
    admin_user = identities("ADMIN")

    res_ent = client.get(f"/api/v1/organizations/{org_id}/entitlements", headers=admin_user["headers"])
    assert res_ent.status_code == 200, res_ent.text
    assert res_ent.json()["contract_id"] == "API-070"

    res_bill = client.get(f"/api/v1/organizations/{org_id}/billing", headers=admin_user["headers"])
    assert res_bill.status_code == 200, res_bill.text
    assert res_bill.json()["contract_id"] == "API-093"
