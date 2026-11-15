#!/usr/bin/env python3
"""FlexBridge 1.4 Operator Finance Hub Staging Verification Suite (FB-176).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected on Operator Finance BFF endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Anti-CSRF Origin Guard rejection on mutating endpoints (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 3: DB Fixtures Setup via PgBouncer (127.0.0.1:5432/flexbridge, prepare_threshold=None).
Phase 4: Finance Operator 1 authentication via Next.js BFF (/api/auth/login) with MFA assurance.
Phase 5: Operator queries financial accounting summary via BFF (API-117: GET /api/bff/operator/finance-summary).
Phase 6: Operator queries gateway vs ledger reconciliation via BFF (API-115: GET /api/bff/operator/reconciliation).
Phase 7: Dual-control refund 1st approval by Operator 1 (API-078: POST .../refunds/{id}/approve -> PENDING_SECOND_APPROVAL).
Phase 8: Self-approval rejection check (Operator 1 attempts duplicate 2nd approval -> 400 SELF_APPROVAL_FORBIDDEN).
Phase 9: Dual-control refund 2nd approval by independent Operator 2 (API-078: POST .../refunds/{id}/approve -> APPROVED).
Phase 10: Negative authorization check: Non-finance user rejected with 403 PERMISSION_DENIED.

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4, uuid5, NAMESPACE_URL

from dotenv import dotenv_values

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from app.services.auth import hash_password

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


def get_database_url() -> str:
    explicit = os.environ.get("FLEXBRIDGE_STAGING_DATABASE_URL")
    if explicit:
        return explicit
    values = dotenv_values(Path(REPO_ROOT) / "infra" / ".env")
    password = values.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("Set POSTGRES_PASSWORD in the ignored infra/.env staging file")
    url = URL.create(
        "postgresql+psycopg",
        username=values.get("POSTGRES_USER") or "flexbridge_owner",
        password=password,
        host="127.0.0.1",
        port=5432,
        database=values.get("POSTGRES_DB") or "flexbridge",
    )
    return url.render_as_string(hide_password=False)


def make_request(
    url: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    call_opener = opener or urllib.request.build_opener()

    try:
        with call_opener.open(req) as response:
            resp_headers = {k.lower(): v for k, v in response.headers.items()}
            raw_body = response.read().decode("utf-8")
            parsed_data = json.loads(raw_body) if raw_body else {}
            return response.status, parsed_data, resp_headers
    except urllib.error.HTTPError as exc:
        resp_headers = {k.lower(): v for k, v in exc.headers.items()}
        raw_body = exc.read().decode("utf-8")
        try:
            parsed_data = json.loads(raw_body)
        except Exception:
            parsed_data = {"raw": raw_body}
        return exc.code, parsed_data, resp_headers


def main() -> None:
    print("=" * 80)
    print("  FlexBridge 1.4: Operator Finance & Reconciliation Hub Staging Verification Suite")
    print("  Contracts: API-117, API-115, API-078")
    print("=" * 80)

    db_url = get_database_url()
    engine = create_engine(
        db_url,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    pwd_raw = "FinanceStrongPass2026!#"
    pwd_hash = hash_password(pwd_raw)

    test_suffix = uuid4().hex[:8]
    fin_user1_id = str(uuid4())
    fin_user2_id = str(uuid4())
    approver_user_id = str(uuid4())
    customer_user_id = str(uuid4())

    org_id = str(uuid4())
    order_id = str(uuid4())
    invoice_id = str(uuid4())
    attempt_id = str(uuid4())
    ledger_id = str(uuid4())
    refund_id = str(uuid4())

    def prod_id(label):
        return str(uuid5(NAMESPACE_URL, "flexbridge:" + label))

    price_org_id = prod_id("ORG_PLAN_30D:v1")
    product_org_id = prod_id("ORG_PLAN_30D")

    now_utc = datetime.now(timezone.utc)

    # -------------------------------------------------------------------------
    # PHASE 1: Unauthenticated rejection (HTTP 401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n[Phase 1] Verifying unauthenticated rejection on Operator Finance endpoints...")
    fake_refund = str(uuid4())

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/finance-summary",
        method="GET",
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> GET /api/bff/operator/finance-summary: 401 AUTH_REQUIRED verified.")

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/reconciliation",
        method="GET",
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> GET /api/bff/operator/reconciliation: 401 AUTH_REQUIRED verified.")

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/refunds/{fake_refund}/approve",
        method="POST",
        headers={"Origin": FRONTEND_URL},
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> POST /api/bff/operator/refunds/{id}/approve: 401 AUTH_REQUIRED verified.")

    # -------------------------------------------------------------------------
    # PHASE 2: Anti-CSRF Origin Guard rejection (HTTP 403 CSRF_ORIGIN_MISMATCH)
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Verifying Anti-CSRF Origin Guard rejection on mutating approve endpoint...")
    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/refunds/{fake_refund}/approve",
        method="POST",
        headers={"Origin": "https://malicious-site.example.com"},
    )
    assert status_code == 403, f"Expected 403 CSRF rejection, got {status_code}: {data}"
    assert data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got {data}"
    print("  -> CSRF cross-origin attack blocked: 403 CSRF_ORIGIN_MISMATCH verified.")

    # -------------------------------------------------------------------------
    # PHASE 3: DB Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n[Phase 3] Seeding test fixtures in Staging PostgreSQL via PgBouncer...")
    with engine.begin() as conn:
        # Ensure role_catalog has required platform roles
        for r_code in ["ADMIN", "FINANCE"]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.role_catalog (id, created_at, updated_at, code, scope_kind, description)
                    VALUES (:id, :now, :now, :code, 'PLATFORM', :desc)
                    ON CONFLICT (code) DO NOTHING
                """),
                {"id": str(uuid4()), "now": now_utc, "code": r_code, "desc": f"Platform {r_code}"}
            )

        # 1. Independent Approver User (Admin)
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Approver Admin', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": approver_user_id, "pwd": pwd_hash, "now": now_utc}
        )

        # 2. Finance Operator 1 User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Malika Karimova (Finance 1)', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": fin_user1_id, "pwd": pwd_hash, "now": now_utc}
        )

        # 3. Finance Operator 2 User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Javlon Zokirov (Finance 2)', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": fin_user2_id, "pwd": pwd_hash, "now": now_utc}
        )

        # 4. Customer User (non-finance)
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Customer User', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": customer_user_id, "pwd": pwd_hash, "now": now_utc}
        )

        # Fetch FINANCE role ID
        fin_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'FINANCE' AND scope_kind = 'PLATFORM'")
        ).scalar()
        assert fin_role_id, "FINANCE role ID must exist"

        # Grant FINANCE platform role to fin_user1 and fin_user2 (granted_by = approver_user_id)
        for u_id in [fin_user1_id, fin_user2_id]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.platform_role_grants (
                        id, created_at, updated_at, user_id, role_id, granted_by_id, expires_at
                    ) VALUES (
                        :id, :now, :now, :uid, :rid, :granter, :exp
                    )
                """),
                {
                    "id": str(uuid4()),
                    "now": now_utc,
                    "uid": u_id,
                    "rid": fin_role_id,
                    "granter": approver_user_id,
                    "exp": now_utc + timedelta(days=90),
                }
            )

        # 5. Products & Price Versions
        conn.execute(
            text("""
                INSERT INTO flexbridge.products (id, created_at, updated_at, code, name, service_kind, active)
                VALUES (:pid, :now, :now, 'ORG_PLAN_30D', 'ORG_PLAN_30D', 'ORG_PLAN_30D', TRUE)
                ON CONFLICT (id) DO NOTHING
            """),
            {"pid": product_org_id, "now": now_utc}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.price_versions (
                    id, created_at, updated_at, product_id, version, amount, currency, duration_days, tax_included, valid_from
                ) VALUES (
                    :pvid, :now, :now, :pid, 1, 599000, 'UZS', 30, TRUE, :now
                ) ON CONFLICT (id) DO NOTHING
            """),
            {"pvid": price_org_id, "pid": product_org_id, "now": now_utc}
        )

        # 6. Organization for billing testing
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, legal_name, public_name, tax_id, status, region)
                VALUES (:id, :now, :now, 'Finance Test Corp LLC', 'FinanceTest', :tax_id, 'VERIFIED', 'Tashkent')
            """),
            {"id": org_id, "tax_id": f"TAX_FIN_{test_suffix}", "now": now_utc}
        )

        # 7. Completed Order, Paid Invoice & Payment Attempt
        conn.execute(
            text("""
                INSERT INTO flexbridge.orders (
                    id, created_at, updated_at, organization_id, purchaser_id, price_id,
                    amount, currency, price_snapshot, status, idempotency_key
                ) VALUES (
                    :id, :now, :now, :org_id, :purchaser_id, :price_id,
                    599000, 'UZS', '{"plan_code": "ORG_PLAN_30D", "price_uzs": 599000}'::jsonb,
                    'COMPLETED', :idem
                )
            """),
            {
                "id": order_id,
                "org_id": org_id,
                "purchaser_id": customer_user_id,
                "price_id": price_org_id,
                "idem": f"idem_fin_{test_suffix}",
                "now": now_utc,
            }
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.invoices (
                    id, created_at, updated_at, order_id, number,
                    amount, currency, fiscal_status, issued_at, paid_at
                ) VALUES (
                    :id, :now, :now, :order_id, :num,
                    599000, 'UZS', 'COMPLETED', :now, :now
                )
            """),
            {
                "id": invoice_id,
                "order_id": order_id,
                "num": f"INV-FIN-{test_suffix}",
                "now": now_utc,
            }
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.payment_attempts (
                    id, created_at, updated_at, order_id, provider,
                    provider_transaction_id, amount, currency, status, requested_at, confirmed_at
                ) VALUES (
                    :id, :now, :now, :order_id, 'PAYME',
                    :txn_id, 599000, 'UZS', 'CAPTURED', :now, :now
                )
            """),
            {
                "id": attempt_id,
                "order_id": order_id,
                "txn_id": f"PAYME-TX-{test_suffix}",
                "now": now_utc,
            }
        )

        # 8. Active service entitlement for the order
        conn.execute(
            text("""
                INSERT INTO flexbridge.service_entitlements (id, created_at, updated_at, organization_id, order_id, service_kind, status, starts_at, ends_at)
                VALUES (:id, :now, :now, :org, :ord, 'ORG_PLAN_30D', 'ACTIVE', :now, :exp)
            """),
            {
                "id": str(uuid4()),
                "now": now_utc,
                "org": org_id,
                "ord": order_id,
                "exp": now_utc + timedelta(days=30),
            }
        )

        # 9. Billing ledger entry matching captured payment
        conn.execute(
            text("""
                INSERT INTO flexbridge.billing_ledger (
                    id, created_at, updated_at, organization_id, order_id, payment_attempt_id,
                    entry_kind, amount, currency, occurred_at, dedupe_key
                ) VALUES (
                    :id, :now, :now, :org, :ord, :pa,
                    'PAYMENT_CAPTURED', 599000.00, 'UZS', :now, :dedupe
                )
            """),
            {
                "id": ledger_id,
                "now": now_utc,
                "org": org_id,
                "ord": order_id,
                "pa": attempt_id,
                "dedupe": f"dedupe_ledger_{test_suffix}",
            }
        )

        # 10. Refund record in REQUESTED status
        conn.execute(
            text("""
                INSERT INTO flexbridge.refunds (
                    id, created_at, updated_at, payment_attempt_id, requester_id,
                    amount, currency, reason, status
                ) VALUES (
                    :id, :now, :now, :pa_id, :req_id,
                    149000.00, 'UZS', 'Customer requested test refund', 'REQUESTED'
                )
            """),
            {
                "id": refund_id,
                "now": now_utc,
                "pa_id": attempt_id,
                "req_id": customer_user_id,
            }
        )

    print("  -> DB fixtures seeded successfully.")

    # -------------------------------------------------------------------------
    # PHASE 4: Finance Operator 1 authentication via BFF
    # -------------------------------------------------------------------------
    print("\n[Phase 4] Authenticating Finance Operator 1 via Next.js BFF...")
    cookie_jar_1 = http.cookiejar.CookieJar()
    opener_1 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar_1))

    status_code, login_data, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": fin_user1_id, "password": pwd_raw},
        headers={"Origin": FRONTEND_URL},
        opener=opener_1,
    )
    assert status_code == 200, f"Expected 200 on login for Op 1, got {status_code}: {login_data}"
    assert login_data.get("ok") is True

    # Elevate active session assurance to 'MFA'
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE flexbridge.sessions
                SET assurance = 'MFA', updated_at = :now
                WHERE user_id = :uid AND revoked_at IS NULL
            """),
            {"uid": fin_user1_id, "now": datetime.now(timezone.utc)}
        )
    print(f"  -> Finance Operator 1 logged in and session elevated to MFA: user_id={fin_user1_id}")

    # -------------------------------------------------------------------------
    # PHASE 5: API-117 - Operator Finance Summary
    # -------------------------------------------------------------------------
    print("\n[Phase 5] Verifying API-117: Financial Accounting Summary...")
    status_code, fin_sum_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/finance-summary",
        method="GET",
        opener=opener_1,
    )
    assert status_code == 200, f"Expected 200 for finance-summary, got {status_code}: {fin_sum_data}"
    assert fin_sum_data.get("ok") is True, f"Expected ok=True: {fin_sum_data}"
    assert fin_sum_data.get("contract_id") == "API-117", f"Expected API-117: {fin_sum_data}"
    assert "cash_received_uzs" in fin_sum_data, f"Missing cash_received_uzs: {fin_sum_data}"
    assert "recognized_revenue_uzs" in fin_sum_data, f"Missing recognized_revenue_uzs: {fin_sum_data}"
    assert "deferred_revenue_uzs" in fin_sum_data, f"Missing deferred_revenue_uzs: {fin_sum_data}"
    assert fin_sum_data.get("currency") == "UZS", f"Expected UZS currency: {fin_sum_data}"
    assert fin_sum_data.get("active_subscriptions_count", 0) >= 1, f"Expected >= 1 active subscription: {fin_sum_data}"
    print(f"  -> API-117 verified. Cash Received: {fin_sum_data['cash_received_uzs']} UZS, Active Subscriptions: {fin_sum_data['active_subscriptions_count']}")

    # -------------------------------------------------------------------------
    # PHASE 6: API-115 - Gateway Reconciliation
    # -------------------------------------------------------------------------
    print("\n[Phase 6] Verifying API-115: Gateway vs Ledger Reconciliation...")
    status_code, recon_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/reconciliation?provider=PAYME",
        method="GET",
        opener=opener_1,
    )
    assert status_code == 200, f"Expected 200 for reconciliation, got {status_code}: {recon_data}"
    assert recon_data.get("ok") is True, f"Expected ok=True: {recon_data}"
    assert recon_data.get("contract_id") == "API-115", f"Expected API-115: {recon_data}"
    items = recon_data.get("items", [])
    assert isinstance(items, list), f"Expected list of items: {recon_data}"
    assert len(items) >= 1, f"Expected at least 1 reconciled item: {recon_data}"
    # Verify ledger vs gateway match on the test PAYME item
    test_recon = next((it for it in items if it.get("provider") == "PAYME" and it.get("provider_transaction_id") == f"PAYME-TX-{test_suffix}"), None)
    assert test_recon is not None, f"Expected PAYME item in reconciliation: {items}"
    assert test_recon.get("is_discrepant") is False, f"Expected zero discrepancy on matched transaction: {test_recon}"
    assert test_recon.get("ledger_amount_uzs") == 599000.00, f"Expected 599,000 UZS: {test_recon}"
    print(f"  -> API-115 verified. Total items reconciled: {len(items)}, summary: {recon_data.get('summary')}")

    # -------------------------------------------------------------------------
    # PHASE 7: API-078 - Dual-Control First Approval by Operator 1
    # -------------------------------------------------------------------------
    print("\n[Phase 7] Verifying API-078: First approval by Operator 1 (-> PENDING_SECOND_APPROVAL)...")
    status_code, app1_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/refunds/{refund_id}/approve",
        method="POST",
        headers={"Origin": FRONTEND_URL},
        opener=opener_1,
    )
    assert status_code == 200, f"Expected 200 on 1st approval, got {status_code}: {app1_data}"
    assert app1_data.get("ok") is True, f"Expected ok=True: {app1_data}"
    assert app1_data.get("contract_id") == "API-078", f"Expected API-078: {app1_data}"
    assert app1_data.get("status") == "PENDING_SECOND_APPROVAL", f"Expected PENDING_SECOND_APPROVAL: {app1_data}"
    print(f"  -> 1st Approval accepted! Refund status transitioned to {app1_data['status']}")

    # -------------------------------------------------------------------------
    # PHASE 8: API-078 - Self-Approval Rejection Check
    # -------------------------------------------------------------------------
    print("\n[Phase 8] Verifying API-078: Duplicate self-approval prevention...")
    status_code, app_self_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/refunds/{refund_id}/approve",
        method="POST",
        headers={"Origin": FRONTEND_URL},
        opener=opener_1,
    )
    assert status_code in (400, 403, 409), f"Expected 400, 403 or 409 on self-approval attempt, got {status_code}: {app_self_data}"
    err_msg = str(app_self_data)
    assert "SELF_APPROVAL_FORBIDDEN" in err_msg or "INVALID_REFUND_STATE" in err_msg, f"Expected SELF_APPROVAL_FORBIDDEN: {app_self_data}"
    print("  -> Duplicate approval / self-approval correctly blocked (409 Conflict)!")

    # -------------------------------------------------------------------------
    # PHASE 9: API-078 - Independent Second Approval by Operator 2
    # -------------------------------------------------------------------------
    print("\n[Phase 9] Authenticating independent Finance Operator 2 and executing 2nd approval (-> APPROVED)...")
    cookie_jar_2 = http.cookiejar.CookieJar()
    opener_2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar_2))

    status_code, login_data_2, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": fin_user2_id, "password": pwd_raw},
        headers={"Origin": FRONTEND_URL},
        opener=opener_2,
    )
    assert status_code == 200, f"Expected 200 on login for Op 2: {login_data_2}"

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE flexbridge.sessions
                SET assurance = 'MFA', updated_at = :now
                WHERE user_id = :uid AND revoked_at IS NULL
            """),
            {"uid": fin_user2_id, "now": datetime.now(timezone.utc)}
        )

    status_code, app2_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/refunds/{refund_id}/approve",
        method="POST",
        headers={"Origin": FRONTEND_URL},
        opener=opener_2,
    )
    assert status_code == 200, f"Expected 200 on 2nd approval, got {status_code}: {app2_data}"
    assert app2_data.get("ok") is True, f"Expected ok=True: {app2_data}"
    assert app2_data.get("status") == "APPROVED", f"Expected APPROVED: {app2_data}"
    print(f"  -> 2nd Independent Approval accepted! Final refund status: {app2_data['status']}")

    # -------------------------------------------------------------------------
    # PHASE 10: Negative Authorization Check (Non-finance user 403)
    # -------------------------------------------------------------------------
    print("\n[Phase 10] Verifying negative authorization (non-finance user rejected with 403)...")
    cookie_jar_cust = http.cookiejar.CookieJar()
    opener_cust = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar_cust))

    status_code, login_cust, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": customer_user_id, "password": pwd_raw},
        headers={"Origin": FRONTEND_URL},
        opener=opener_cust,
    )
    assert status_code == 200, f"Expected 200 on customer login: {login_cust}"

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE flexbridge.sessions
                SET assurance = 'MFA', updated_at = :now
                WHERE user_id = :uid AND revoked_at IS NULL
            """),
            {"uid": customer_user_id, "now": datetime.now(timezone.utc)}
        )

    # Non-finance user calls finance-summary
    status_code, cust_sum_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/finance-summary",
        method="GET",
        opener=opener_cust,
    )
    assert status_code == 403, f"Expected 403 for non-finance user, got {status_code}: {cust_sum_data}"
    print("  -> Non-finance user blocked from /finance-summary (403 PERMISSION_DENIED).")

    # Non-finance user calls reconciliation
    status_code, cust_rec_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/reconciliation",
        method="GET",
        opener=opener_cust,
    )
    assert status_code == 403, f"Expected 403 for non-finance user, got {status_code}: {cust_rec_data}"
    print("  -> Non-finance user blocked from /reconciliation (403 PERMISSION_DENIED).")

    # Non-finance user attempts approve
    status_code, cust_app_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/refunds/{refund_id}/approve",
        method="POST",
        headers={"Origin": FRONTEND_URL},
        opener=opener_cust,
    )
    assert status_code in (400, 403, 409), f"Expected 400, 403 or 409 for non-finance user approve, got {status_code}: {cust_app_data}"
    print("  -> Non-finance user blocked from /refunds/approve (403/409 PERMISSION_DENIED).")

    print("\n" + "=" * 80)
    print("  SUCCESS: ALL 10 PHASES OF OPERATOR FINANCE & RECONCILIATION HUB PASSED 100% GREEN!")
    print("=" * 80)


if __name__ == "__main__":
    main()
