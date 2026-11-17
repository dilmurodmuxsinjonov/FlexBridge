"""Adversarial and security boundary tests for Operator Finance (API-115, API-117)."""

import json
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from app.db.storage import now, table, transaction
from app.services.billing import billing_service
from app.services.placements import insert_row


def test_adversarial_unauthenticated_requests_denied_401(client):
    # API-115
    res1 = client.get("/api/v1/operator/reconciliation")
    assert res1.status_code == 401, res1.text

    # API-117
    res2 = client.get("/api/v1/operator/finance-summary")
    assert res2.status_code == 401, res2.text


def test_adversarial_non_finance_actors_forbidden_403(client, identities):
    user = identities()  # regular candidate
    support_staff = identities("SUPPORT")  # support without finance role

    for actor in [user, support_staff]:
        res_rec = client.get("/api/v1/operator/reconciliation", headers=actor["headers"])
        assert res_rec.status_code == 403, res_rec.text
        assert res_rec.json()["detail"]["code"] == "PERMISSION_DENIED"

        res_sum = client.get("/api/v1/operator/finance-summary", headers=actor["headers"])
        assert res_sum.status_code == 403, res_sum.text
        assert res_sum.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_adversarial_zero_customer_pii_leakage_audit(client, identities, organization):
    finance_op = identities("FINANCE")
    user = identities()

    # Seed an order and ledger entry
    now_utc = now()
    order_id = str(uuid4())
    attempt_id = str(uuid4())
    ledger_id = str(uuid4())

    with transaction() as conn:
        price_id, tariff = billing_service._seed_tariff(conn, "ORG_PLAN_30D")
        insert_row(
            conn, "orders",
            id=order_id, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, purchaser_id=user["user_id"],
            price_id=price_id, opportunity_id=None, amount=300000.0,
            currency="UZS", price_snapshot={"plan_code": "ORG_PLAN_30D", "duration_days": 30},
            status="COMPLETED", idempotency_key=f"ord-pii-{uuid4()}",
        )
        insert_row(
            conn, "payment_attempts",
            id=attempt_id, created_at=now_utc, updated_at=now_utc,
            order_id=order_id, provider="CLICK", provider_transaction_id="tx-pii-777",
            amount=300000.0, currency="UZS", status="CAPTURED",
            requested_at=now_utc, confirmed_at=now_utc,
        )
        insert_row(
            conn, "billing_ledger",
            id=ledger_id, created_at=now_utc, updated_at=now_utc,
            organization_id=organization, order_id=order_id, payment_attempt_id=attempt_id,
            refund_id=None, entry_kind="PAYMENT_CAPTURED", amount=300000.0,
            currency="UZS", occurred_at=now_utc, dedupe_key=f"capture:{attempt_id}",
        )

    # 1. Audit API-115 response body
    res_rec = client.get("/api/v1/operator/reconciliation", headers=finance_op["headers"])
    assert res_rec.status_code == 200, res_rec.text
    rec_text = json.dumps(res_rec.json()).lower()

    # Prohibited customer PII keywords
    prohibited_pii_fields = [
        "email", "phone", "first_name", "last_name", "full_name",
        "passport", "pan", "cvv", "card_number", "cardholder",
    ]
    for pii in prohibited_pii_fields:
        assert f'"{pii}"' not in rec_text, f"PII key '{pii}' detected in reconciliation output!"

    # 2. Audit API-117 response body
    res_sum = client.get("/api/v1/operator/finance-summary", headers=finance_op["headers"])
    assert res_sum.status_code == 200, res_sum.text
    sum_text = json.dumps(res_sum.json()).lower()

    for pii in prohibited_pii_fields:
        assert f'"{pii}"' not in sum_text, f"PII key '{pii}' detected in finance summary output!"


def test_adversarial_invalid_date_formats_and_inverted_range_422(client, identities):
    finance_op = identities("FINANCE")

    # Invalid start_date
    res1 = client.get("/api/v1/operator/reconciliation?start_date=not-a-valid-date", headers=finance_op["headers"])
    assert res1.status_code == 422, res1.text
    assert res1.json()["detail"]["code"] == "INVALID_DATE_FORMAT"

    # Invalid end_date in summary
    res2 = client.get("/api/v1/operator/finance-summary?end_date=bad-date-format", headers=finance_op["headers"])
    assert res2.status_code == 422, res2.text
    assert res2.json()["detail"]["code"] == "INVALID_DATE_FORMAT"

    # Inverted date range (start_date > end_date)
    res3 = client.get("/api/v1/operator/reconciliation?start_date=2026-12-31&end_date=2026-01-01", headers=finance_op["headers"])
    assert res3.status_code == 422, res3.text
    assert res3.json()["detail"]["code"] == "INVALID_DATE_RANGE"


def test_adversarial_invalid_cursor_422(client, identities):
    finance_op = identities("FINANCE")

    res = client.get("/api/v1/operator/reconciliation?cursor=CORRUPTED_CURSOR!@#$", headers=finance_op["headers"])
    assert res.status_code == 422, res.text
    assert res.json()["detail"]["code"] == "INVALID_CURSOR"
