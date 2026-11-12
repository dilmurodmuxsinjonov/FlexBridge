"""Functional contract tests for Operator Finance & Reconciliation (API-115, API-117).

Contracts:
- API-115: GET /api/v1/operator/reconciliation (CAP-030 / FINANCE)
- API-117: GET /api/v1/operator/finance-summary (CAP-038 / FINANCE_REPORT)
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from app.db.storage import now, table, transaction
from app.services.billing import billing_service
from app.services.placements import insert_row


def test_api115_operator_reconciliation_ledger_vs_attempts(client, identities, organization):
    finance_op = identities("FINANCE")
    user = identities()

    now_utc = now()
    order_id1 = str(uuid4())
    attempt_id1 = str(uuid4())
    ledger_id1 = str(uuid4())

    order_id2 = str(uuid4())
    attempt_id2 = str(uuid4())
    ledger_id2 = str(uuid4())

    with transaction() as conn:
        price_id, tariff = billing_service._seed_tariff(conn, "ORG_PLAN_30D")

        # Order 1 & Attempt 1: Matched (500,000 UZS)
        insert_row(
            conn, "orders",
            id=order_id1, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, purchaser_id=user["user_id"],
            price_id=price_id, opportunity_id=None, amount=500000.0,
            currency="UZS", price_snapshot={"plan_code": "ORG_PLAN_30D", "duration_days": 30},
            status="COMPLETED", idempotency_key=f"ord-rec-1-{uuid4()}",
        )
        insert_row(
            conn, "payment_attempts",
            id=attempt_id1, created_at=now_utc, updated_at=now_utc,
            order_id=order_id1, provider="CLICK", provider_transaction_id="clk-tx-1001",
            amount=500000.0, currency="UZS", status="CAPTURED",
            requested_at=now_utc, confirmed_at=now_utc,
        )
        insert_row(
            conn, "billing_ledger",
            id=ledger_id1, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, order_id=order_id1, payment_attempt_id=attempt_id1,
            refund_id=None, entry_kind="PAYMENT_CAPTURED", amount=500000.0,
            currency="UZS", occurred_at=now_utc, dedupe_key=f"capture:{attempt_id1}",
        )

        # Order 2 & Attempt 2: Discrepant amount (Ledger 1,000,000 UZS vs Gateway Attempt 800,000 UZS)
        insert_row(
            conn, "orders",
            id=order_id2, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, purchaser_id=user["user_id"],
            price_id=price_id, opportunity_id=None, amount=1000000.0,
            currency="UZS", price_snapshot={"plan_code": "ORG_PLAN_30D", "duration_days": 30},
            status="COMPLETED", idempotency_key=f"ord-rec-2-{uuid4()}",
        )
        insert_row(
            conn, "payment_attempts",
            id=attempt_id2, created_at=now_utc, updated_at=now_utc,
            order_id=order_id2, provider="PAYME", provider_transaction_id="payme-tx-2002",
            amount=800000.0, currency="UZS", status="CAPTURED",  # Amount mismatch!
            requested_at=now_utc, confirmed_at=now_utc,
        )
        insert_row(
            conn, "billing_ledger",
            id=ledger_id2, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, order_id=order_id2, payment_attempt_id=attempt_id2,
            refund_id=None, entry_kind="PAYMENT_CAPTURED", amount=1000000.0,
            currency="UZS", occurred_at=now_utc, dedupe_key=f"capture:{attempt_id2}",
        )

    # 1. Query operator reconciliation
    res = client.get("/api/v1/operator/reconciliation?limit=100", headers=finance_op["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-115"
    assert data["capability"] == "FINANCE"
    assert data["total_records"] >= 2
    assert "summary" in data

    items = data["items"]
    ledger_ids = [it["ledger_entry_id"] for it in items]
    assert ledger_id1 in ledger_ids
    assert ledger_id2 in ledger_ids

    # Item 1 must be clean and matched
    it1 = next(it for it in items if it["ledger_entry_id"] == ledger_id1)
    assert it1["is_discrepant"] is False
    assert len(it1["discrepancy_flags"]) == 0
    assert it1["provider"] == "CLICK"
    assert it1["ledger_amount_uzs"] == 500000.0

    # Item 2 must have amount_mismatch discrepancy
    it2 = next(it for it in items if it["ledger_entry_id"] == ledger_id2)
    assert it2["is_discrepant"] is True
    assert "amount_mismatch" in it2["discrepancy_flags"]

    # 2. Query with discrepancy_only=true
    res_disc = client.get("/api/v1/operator/reconciliation?discrepancy_only=true", headers=finance_op["headers"])
    assert res_disc.status_code == 200, res_disc.text
    disc_data = res_disc.json()
    assert all(it["is_discrepant"] for it in disc_data["items"])

    # 3. Keyset cursor pagination: limit=1
    res_p1 = client.get("/api/v1/operator/reconciliation?limit=1", headers=finance_op["headers"])
    assert res_p1.status_code == 200, res_p1.text
    p1 = res_p1.json()
    assert len(p1["items"]) == 1
    assert p1["has_more"] is True
    assert p1["next_cursor"] is not None

    # Fetch page 2
    res_p2 = client.get(f"/api/v1/operator/reconciliation?limit=1&cursor={p1['next_cursor']}", headers=finance_op["headers"])
    assert res_p2.status_code == 200, res_p2.text
    p2 = res_p2.json()
    assert len(p2["items"]) == 1
    assert p1["items"][0]["ledger_entry_id"] != p2["items"][0]["ledger_entry_id"]


def test_api117_operator_finance_summary(client, identities, organization):
    finance_op = identities("FINANCE")
    user = identities()

    now_utc = now()
    order_id = str(uuid4())
    inv_id = str(uuid4())
    ent_id = str(uuid4())

    with transaction() as conn:
        price_id, tariff = billing_service._seed_tariff(conn, "ORG_PLAN_30D")
        # Create order, paid invoice, and active service entitlement
        insert_row(
            conn, "orders",
            id=order_id, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, purchaser_id=user["user_id"],
            price_id=price_id, opportunity_id=None, amount=1200000.0,
            currency="UZS", price_snapshot={"plan_code": "ORG_PLAN_30D", "duration_days": 30},
            status="COMPLETED", idempotency_key=f"ord-fin-1-{uuid4()}",
        )
        insert_row(
            conn, "invoices",
            id=inv_id, created_at=now_utc, updated_at=now_utc,
            order_id=order_id, number=f"INV-FIN-{uuid4().hex[:6]}",
            amount=1200000.0, currency="UZS", fiscal_status="REGISTERED",
            fiscal_reference="FISC-1002", issued_at=now_utc, paid_at=now_utc,
        )
        insert_row(
            conn, "service_entitlements",
            id=ent_id, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, order_id=order_id, opportunity_id=None,
            service_kind="ORG_PLAN_30D", status="ACTIVE",
            starts_at=now_utc, ends_at=now_utc + timedelta(days=30),
            quota=100, granted_by_id=user["user_id"], grant_reason="Enterprise subscription",
            concurrent_active_limit=10,
        )

    # Query finance summary
    res = client.get("/api/v1/operator/finance-summary", headers=finance_op["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-117"
    assert data["capability"] == "FINANCE_REPORT"
    assert data["currency"] == "UZS"
    assert data["cash_received_uzs"] >= 1200000.0
    assert data["active_subscriptions_count"] >= 1
    assert data["recognized_revenue_uzs"] >= 0.0
    assert data["deferred_revenue_uzs"] >= 0.0
    assert data["net_revenue_uzs"] >= 0.0
    assert isinstance(data["plans_breakdown"], list)
    assert any(p["plan_code"] == "ORG_PLAN_30D" for p in data["plans_breakdown"])


def test_api115_provider_filtering_and_refund_reconciliation(client, identities, organization):
    finance_op = identities("FINANCE")
    user = identities()

    now_utc = now()
    order_id = str(uuid4())
    attempt_id = str(uuid4())
    refund_id = str(uuid4())
    ledger_id = str(uuid4())

    with transaction() as conn:
        price_id, tariff = billing_service._seed_tariff(conn, "SINGLE_POST_30D")

        insert_row(
            conn, "orders",
            id=order_id, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, purchaser_id=user["user_id"],
            price_id=price_id, opportunity_id=None, amount=149000.0,
            currency="UZS", price_snapshot={"plan_code": "SINGLE_POST_30D", "duration_days": 30},
            status="COMPLETED", idempotency_key=f"ord-ref-{uuid4()}",
        )
        insert_row(
            conn, "payment_attempts",
            id=attempt_id, created_at=now_utc, updated_at=now_utc,
            order_id=order_id, provider="PAYME", provider_transaction_id="payme-ref-99",
            amount=149000.0, currency="UZS", status="REFUNDED",
            requested_at=now_utc, confirmed_at=now_utc,
        )
        insert_row(
            conn, "refunds",
            id=refund_id, created_at=now_utc, updated_at=now_utc,
            payment_attempt_id=attempt_id, requester_id=user["user_id"],
            approver_id=user["user_id"], amount=149000.0, currency="UZS",
            reason="Candidate requested refund", status="REFUNDED",
            provider_refund_id="payme-refund-999", resolved_at=now_utc,
            second_approver_id=user["user_id"],
        )
        insert_row(
            conn, "billing_ledger",
            id=ledger_id, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, order_id=order_id, payment_attempt_id=attempt_id,
            refund_id=refund_id, entry_kind="REFUND_EXECUTED", amount=-149000.0,
            currency="UZS", occurred_at=now_utc, dedupe_key=f"refund:{refund_id}",
        )

    # 1. Test provider filtering for PAYME
    res_payme = client.get("/api/v1/operator/reconciliation?provider=PAYME", headers=finance_op["headers"])
    assert res_payme.status_code == 200, res_payme.text
    data_payme = res_payme.json()
    assert all(it["provider"] == "PAYME" for it in data_payme["items"] if it.get("provider"))

    # 2. Check the refund entry
    items = data_payme["items"]
    refund_entries = [it for it in items if it["ledger_entry_id"] == ledger_id]
    assert len(refund_entries) == 1
    r_item = refund_entries[0]
    assert r_item["entry_kind"] == "REFUND_EXECUTED"
    assert r_item["refund_id"] == refund_id
    assert r_item["is_discrepant"] is False


def test_api117_date_range_window_filtering(client, identities, organization):
    finance_op = identities("FINANCE")
    user = identities()

    today = datetime.now(timezone.utc)
    old_date = today - timedelta(days=90)
    now_utc = now()

    order_id_old = str(uuid4())
    inv_id_old = str(uuid4())

    with transaction() as conn:
        price_id, tariff = billing_service._seed_tariff(conn, "SINGLE_POST_30D")

        # 90-day-old invoice
        insert_row(
            conn, "orders",
            id=order_id_old, created_at=old_date, updated_at=old_date,
            organization_id=organization, purchaser_id=user["user_id"],
            price_id=price_id, opportunity_id=None, amount=999999.0,
            currency="UZS", price_snapshot={"plan_code": "SINGLE_POST_30D"},
            status="COMPLETED", idempotency_key=f"ord-old-{uuid4()}",
        )
        insert_row(
            conn, "invoices",
            id=inv_id_old, created_at=old_date, updated_at=old_date,
            order_id=order_id_old, number=f"INV-OLD-{uuid4().hex[:6]}",
            amount=999999.0, currency="UZS", fiscal_status="PAID",
            fiscal_reference="FISC-OLD-01", issued_at=old_date, paid_at=old_date,
        )

    # Query with date window: last 7 days only
    start_str = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    res = client.get(f"/api/v1/operator/finance-summary?start_date={start_str}&end_date={end_str}", headers=finance_op["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["period"]["start_date"] is not None
    assert data["period"]["end_date"] is not None

