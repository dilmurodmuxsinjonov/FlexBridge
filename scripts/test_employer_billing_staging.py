#!/usr/bin/env python3
"""
FlexBridge 1.4 Staging Verification Suite:
Employer Billing Overview, Service Entitlements, Subscription Orders & Refunds Hub (FB-174)

Verifies:
- API-070: GET /api/bff/employer/organization/{org}/entitlements
- API-093: GET /api/bff/employer/organization/{org}/billing
- API-094: POST /api/bff/employer/organization/{org}/orders
- API-095: POST /api/bff/employer/orders/{id}/refund

Targets:
- Frontend Next.js BFF at http://127.0.0.1:3000
- Staging PostgreSQL via PgBouncer at 127.0.0.1:5432/flexbridge
"""

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_URL

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.services.auth import hash_password

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")


def get_database_url() -> str:
    explicit = os.environ.get("FLEXBRIDGE_STAGING_DATABASE_URL")
    if explicit:
        return explicit

    values = dotenv_values(REPO_ROOT / "infra" / ".env")
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


def api_request(url, method="GET", data=None, headers=None, opener=None):
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    active_opener = opener or urllib.request.build_opener()

    try:
        with active_opener.open(req) as resp:
            content = resp.read().decode("utf-8")
            parsed = json.loads(content) if content else {}
            return resp.status, parsed
    except urllib.error.HTTPError as err:
        content = err.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"raw": content}
        return err.code, parsed


def main():
    print("================================================================================")
    print("FLEXBRIDGE 1.4 STAGING SUITE: Employer Billing, Orders & Refunds Hub (FB-174)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print("Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("================================================================================")

    dummy_org = str(uuid4())
    dummy_order = str(uuid4())

    # -------------------------------------------------------------------------
    # PHASE 1: 401 AUTH_REQUIRED on all unauthenticated endpoints
    # -------------------------------------------------------------------------
    print("\n[Phase 1] 401 AUTH_REQUIRED on unauthenticated billing & entitlement endpoints...")

    unauth_endpoints = [
        ("GET", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/entitlements", None),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/billing", None),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/orders", {"plan_code": "ORG_PLAN_30D"}),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/orders/{dummy_order}/refund", {"amount_uzs": 100000, "reason": "Reason for refund at least 15 chars"}),
    ]

    for m, ep, payload in unauth_endpoints:
        code, resp = api_request(ep, method=m, data=payload)
        assert code == 401, f"Expected 401 on {m} {ep}, got {code}: {resp}"
        assert resp.get("error") == "AUTH_REQUIRED", f"Invalid 401 payload: {resp}"
    print("  ✓ All 4 endpoints strictly enforce 401 AUTH_REQUIRED.")

    # -------------------------------------------------------------------------
    # PHASE 2: Anti-CSRF Origin Guard
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Anti-CSRF Origin Guard (403 CSRF_ORIGIN_MISMATCH)...")
    csrf_headers = {
        "Origin": "https://malicious-attacker-domain.com",
        "Referer": "https://malicious-attacker-domain.com/hack",
    }

    mutating_csrf_endpoints = [
        ("POST", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/orders", {"plan_code": "ORG_PLAN_30D"}),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/orders/{dummy_order}/refund", {"amount_uzs": 100000, "reason": "Reason for refund at least 15 chars"}),
    ]

    for m, ep, payload in mutating_csrf_endpoints:
        code, resp = api_request(ep, method=m, data=payload, headers=csrf_headers)
        assert code == 403, f"Expected 403 on CSRF attack for {m} {ep}, got {code}: {resp}"
        assert resp.get("error") == "CSRF_ORIGIN_MISMATCH", f"Invalid CSRF payload: {resp}"
    print("  ✓ Anti-CSRF guard properly blocked cross-origin mutating requests.")

    # -------------------------------------------------------------------------
    # PHASE 3: DB Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n[Phase 3] Setting up DB fixtures in PostgreSQL via PgBouncer...")
    db_url = get_database_url()
    engine = create_engine(
        db_url,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_suffix = uuid4().hex[:8]
    owner_user_id = str(uuid4())
    mentor_user_id = str(uuid4())
    other_owner_id = str(uuid4())

    org_id = str(uuid4())
    other_org_id = str(uuid4())

    owner_membership_id = str(uuid4())
    mentor_membership_id = str(uuid4())
    other_membership_id = str(uuid4())

    refund_order_id = str(uuid4())
    refund_invoice_id = str(uuid4())
    refund_attempt_id = str(uuid4())
    refund_entitlement_id = str(uuid4())

    owner_password = f"TestOwnerPass_{test_suffix}!123"
    owner_hash = hash_password(owner_password)
    now_ts = datetime.now(timezone.utc)

    # Helper function for product UUIDs matching backend
    def prod_id(label):
        return str(uuid5(NAMESPACE_URL, "flexbridge:" + label))

    price_org_id = prod_id("ORG_PLAN_30D:v1")
    product_org_id = prod_id("ORG_PLAN_30D")

    with engine.begin() as conn:
        conn.execute(text("SET search_path TO flexbridge, public;"))

        # Ensure role_catalog has OWNER, BILLING, MENTOR
        for r_code in ["OWNER", "BILLING", "MENTOR"]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.role_catalog (id, created_at, updated_at, code, scope_kind, description)
                    VALUES (:id, :ts, :ts, :code, 'ORG', :desc)
                    ON CONFLICT (code) DO NOTHING
                """),
                {"id": str(uuid4()), "ts": now_ts, "code": r_code, "desc": f"Org {r_code}"}
            )

        # 1. Users
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (
                    id, created_at, updated_at, display_name, password_hash,
                    status, locale, timezone, adult_declared_at
                ) VALUES
                (:oid, :ts, :ts, 'Apex Technologies Owner', :chash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts),
                (:mid, :ts, :ts, 'Apex Technologies Mentor', :chash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts),
                (:other_oid, :ts, :ts, 'Other Corp Owner', :chash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
            """),
            {
                "oid": owner_user_id,
                "mid": mentor_user_id,
                "other_oid": other_owner_id,
                "chash": owner_hash,
                "ts": now_ts,
            },
        )

        # 2. Organizations
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (
                    id, created_at, updated_at, legal_name, public_name, tax_id, status, region
                ) VALUES
                (:id, :ts, :ts, 'Apex Tech Solutions MCHJ', 'ApexTech', :tax_id, 'VERIFIED', 'Tashkent'),
                (:other_id, :ts, :ts, 'Other Global Corp', 'OtherCorp', :other_tax_id, 'VERIFIED', 'Samarkand')
            """),
            {
                "id": org_id,
                "tax_id": f"TAX_FB174_{test_suffix}",
                "other_id": other_org_id,
                "other_tax_id": f"TAX_OTHER_{test_suffix}",
                "ts": now_ts,
            },
        )

        # 3. Org Memberships
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (
                    id, created_at, updated_at, organization_id, user_id, status, accepted_at
                ) VALUES
                (:omid, :ts, :ts, :org_id, :oid, 'ACTIVE', :ts),
                (:mmid, :ts, :ts, :org_id, :mid, 'ACTIVE', :ts),
                (:other_mid, :ts, :ts, :other_id, :other_oid, 'ACTIVE', :ts)
            """),
            {
                "omid": owner_membership_id,
                "org_id": org_id,
                "oid": owner_user_id,
                "mmid": mentor_membership_id,
                "mid": mentor_user_id,
                "other_mid": other_membership_id,
                "other_id": other_org_id,
                "other_oid": other_owner_id,
                "ts": now_ts,
            },
        )

        # 4. Role Grants
        owner_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'OWNER' AND scope_kind = 'ORG' LIMIT 1")
        ).scalar_one()

        billing_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'BILLING' AND scope_kind = 'ORG' LIMIT 1")
        ).scalar_one()

        mentor_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'MENTOR' AND scope_kind = 'ORG' LIMIT 1")
        ).scalar_one()

        conn.execute(
            text("""
                INSERT INTO flexbridge.org_role_grants (
                    id, created_at, updated_at, membership_id, role_id, granted_by_id
                ) VALUES
                (:g1, :ts, :ts, :omid, :rid1, :oid),
                (:g2, :ts, :ts, :omid, :rid2, :oid),
                (:g3, :ts, :ts, :mmid, :rid3, :oid),
                (:g4, :ts, :ts, :other_mid, :rid1, :other_oid)
            """),
            {
                "g1": str(uuid4()),
                "g2": str(uuid4()),
                "g3": str(uuid4()),
                "g4": str(uuid4()),
                "omid": owner_membership_id,
                "mmid": mentor_membership_id,
                "other_mid": other_membership_id,
                "rid1": owner_role_id,
                "rid2": billing_role_id,
                "rid3": mentor_role_id,
                "oid": owner_user_id,
                "other_oid": other_owner_id,
                "ts": now_ts,
            },
        )

        # 5. Products & Price Versions (for ORG_PLAN_30D)
        conn.execute(
            text("""
                INSERT INTO flexbridge.products (id, created_at, updated_at, code, name, service_kind, active)
                VALUES (:pid, :ts, :ts, 'ORG_PLAN_30D', 'ORG_PLAN_30D', 'ORG_PLAN_30D', TRUE)
                ON CONFLICT (id) DO NOTHING
            """),
            {"pid": product_org_id, "ts": now_ts}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.price_versions (
                    id, created_at, updated_at, product_id, version, amount, currency, duration_days, tax_included, valid_from
                ) VALUES (
                    :pvid, :ts, :ts, :pid, 1, 599000, 'UZS', 30, TRUE, :ts
                ) ON CONFLICT (id) DO NOTHING
            """),
            {"pvid": price_org_id, "pid": product_org_id, "ts": now_ts}
        )

        # 6. Existing Order, Invoice, Payment Attempt & Entitlement (for refund testing)
        conn.execute(
            text("""
                INSERT INTO flexbridge.orders (
                    id, created_at, updated_at, organization_id, purchaser_id, price_id,
                    amount, currency, price_snapshot, status, idempotency_key
                ) VALUES (
                    :id, :ts, :ts, :org_id, :purchaser_id, :price_id,
                    599000, 'UZS', '{"plan_code": "ORG_PLAN_30D", "price_uzs": 599000}'::jsonb,
                    'PAID', :idem
                )
            """),
            {
                "id": refund_order_id,
                "org_id": org_id,
                "purchaser_id": owner_user_id,
                "price_id": price_org_id,
                "idem": f"idem_ref_{test_suffix}",
                "ts": now_ts,
            }
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.invoices (
                    id, created_at, updated_at, order_id, number,
                    amount, currency, fiscal_status, issued_at, paid_at
                ) VALUES (
                    :id, :ts, :ts, :order_id, :num,
                    599000, 'UZS', 'COMPLETED', :ts, :ts
                )
            """),
            {
                "id": refund_invoice_id,
                "order_id": refund_order_id,
                "num": f"FB-{refund_invoice_id}",
                "ts": now_ts,
            }
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.payment_attempts (
                    id, created_at, updated_at, order_id, provider,
                    provider_transaction_id, amount, currency, status, requested_at, confirmed_at
                ) VALUES (
                    :id, :ts, :ts, :order_id, 'PAYME',
                    :txn_id, 599000, 'UZS', 'CAPTURED', :ts, :ts
                )
            """),
            {
                "id": refund_attempt_id,
                "order_id": refund_order_id,
                "txn_id": f"payme_txn_{test_suffix}",
                "ts": now_ts,
            }
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.service_entitlements (
                    id, created_at, updated_at, organization_id, order_id,
                    service_kind, status, starts_at, ends_at, quota, concurrent_active_limit
                ) VALUES (
                    :id, :ts, :ts, :org_id, :order_id,
                    'ORG_PLAN_30D', 'ACTIVE', :starts, :ends, 50, 5
                )
            """),
            {
                "id": refund_entitlement_id,
                "org_id": org_id,
                "order_id": refund_order_id,
                "starts": now_ts,
                "ends": now_ts + timedelta(days=30),
                "ts": now_ts,
            }
        )

    print("  ✓ Database fixtures seeded successfully via PgBouncer.")

    # -------------------------------------------------------------------------
    # PHASE 4: Employer Owner Login via BFF & Session MFA Elevation
    # -------------------------------------------------------------------------
    print("\n[Phase 4] Employer Owner login and MFA assurance elevation...")
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    code, resp = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": owner_user_id, "password": owner_password},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert code == 200, f"Login failed: status {code}, {resp}"
    assert resp.get("ok") is True, f"Login response not ok: {resp}"
    print(f"  ✓ Owner login successful. User: {resp.get('user', {}).get('display_name')}")

    # Elevate active session assurance to 'MFA'
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE flexbridge.sessions
                SET assurance = 'MFA', updated_at = :now
                WHERE user_id = :uid AND revoked_at IS NULL
            """),
            {"uid": owner_user_id, "now": datetime.now(timezone.utc)}
        )
    print("  ✓ Active session assurance upgraded to 'MFA' in PostgreSQL.")

    # -------------------------------------------------------------------------
    # PHASE 5: Querying Service Entitlements via BFF (API-070)
    # -------------------------------------------------------------------------
    print("\n[Phase 5] Querying organization service entitlements via BFF (API-070)...")
    code, ent_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/entitlements",
        method="GET",
        opener=opener,
    )
    assert code == 200, f"Expected 200 on API-070, got {code}: {ent_resp}"
    assert ent_resp.get("contract_id") == "API-070", f"Contract ID mismatch: {ent_resp}"
    assert ent_resp.get("has_active_entitlement") is True, f"Expected has_active_entitlement: True: {ent_resp}"
    active_ent = ent_resp.get("active_entitlement")
    assert active_ent is not None, f"Active entitlement is null: {ent_resp}"
    assert active_ent.get("service_kind") == "ORG_PLAN_30D", f"Service kind mismatch: {active_ent}"
    assert active_ent.get("concurrent_active_limit") == 5, f"Limit mismatch: {active_ent}"
    assert "usage" in ent_resp, f"Usage dictionary missing: {ent_resp}"
    usage = ent_resp["usage"]
    assert usage.get("concurrent_slots_available") == 5, f"Available slots mismatch: {usage}"
    print(f"  ✓ Service entitlements verified (Plan: {active_ent.get('service_kind')}, Available slots: {usage.get('concurrent_slots_available')}).")

    # -------------------------------------------------------------------------
    # PHASE 6: Querying Billing Overview via BFF (API-093)
    # -------------------------------------------------------------------------
    print("\n[Phase 6] Querying organization billing overview via BFF (API-093)...")
    code, bill_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/billing",
        method="GET",
        opener=opener,
    )
    assert code == 200, f"Expected 200 on API-093, got {code}: {bill_resp}"
    assert bill_resp.get("contract_id") == "API-093", f"Contract ID mismatch: {bill_resp}"
    plan = bill_resp.get("plan", {})
    assert plan.get("code") == "ORG_PLAN_30D", f"Plan code mismatch: {plan}"
    assert plan.get("status") == "ACTIVE", f"Plan status mismatch: {plan}"
    orders = bill_resp.get("orders", [])
    assert len(orders) >= 1, f"Expected at least 1 order: {orders}"
    found_order = next((o for o in orders if o.get("id") == refund_order_id), None)
    assert found_order is not None, f"Seeded order {refund_order_id} not found in {orders}"
    assert found_order.get("status") == "PAID", f"Order status mismatch: {found_order}"
    print(f"  ✓ Billing overview verified ({len(orders)} orders, Active Plan: {plan.get('code')}).")

    # -------------------------------------------------------------------------
    # PHASE 7: Placing New Subscription Order via BFF (API-094)
    # -------------------------------------------------------------------------
    print("\n[Phase 7] Placing subscription order via BFF (API-094)...")
    new_idem = f"ord_test_{uuid4().hex}"
    code, order_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/orders",
        method="POST",
        data={"plan_code": "SINGLE_POST_30D", "idempotency_key": new_idem},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert code == 201, f"Expected 201 on API-094, got {code}: {order_resp}"
    assert order_resp.get("contract_id") == "API-094", f"Contract ID mismatch: {order_resp}"
    created_order = order_resp.get("order")
    assert created_order is not None, f"Order object missing: {order_resp}"
    assert created_order.get("amount_uzs") == 149000 or created_order.get("amount") == 149000, f"Amount mismatch: {created_order}"
    assert created_order.get("status") == "PENDING_PAYMENT", f"Status mismatch: {created_order}"
    created_invoice = order_resp.get("invoice")
    assert created_invoice is not None, f"Invoice object missing: {order_resp}"
    print(f"  ✓ Subscription order successfully placed (Order ID: {created_order.get('id')[:8]}, Status: {created_order.get('status')}).")

    # -------------------------------------------------------------------------
    # PHASE 8: Negative Validation on Refund Endpoint (HTTP 422)
    # -------------------------------------------------------------------------
    print("\n[Phase 8] Verifying negative validation on refund endpoint (HTTP 422)...")

    # 1. Invalid amount <= 0
    code, neg1 = api_request(
        f"{FRONTEND_URL}/api/bff/employer/orders/{refund_order_id}/refund",
        method="POST",
        data={"amount_uzs": 0, "reason": "Sabab kamida 15 ta belgidan iborat"},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert code == 422, f"Expected 422 on amount <= 0, got {code}: {neg1}"
    assert neg1.get("error") == "INVALID_REFUND_AMOUNT", f"Error code mismatch: {neg1}"
    print("  ✓ Zero refund amount cleanly rejected with 422 INVALID_REFUND_AMOUNT.")

    # 2. Reason too short (< 15 chars)
    code, neg2 = api_request(
        f"{FRONTEND_URL}/api/bff/employer/orders/{refund_order_id}/refund",
        method="POST",
        data={"amount_uzs": 100000, "reason": "Too short"},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert code == 422, f"Expected 422 on reason < 15 chars, got {code}: {neg2}"
    assert neg2.get("error") == "INVALID_REFUND_REASON", f"Error code mismatch: {neg2}"
    print("  ✓ Short refund reason cleanly rejected with 422 INVALID_REFUND_REASON.")

    # -------------------------------------------------------------------------
    # PHASE 9: Submitting Order Refund Request via BFF (API-095)
    # -------------------------------------------------------------------------
    print("\n[Phase 9] Submitting order refund request via BFF (API-095)...")
    code, refund_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/orders/{refund_order_id}/refund",
        method="POST",
        data={
            "amount_uzs": 250000,
            "reason": "Tarif rejasi korxona talablariga mos kelmaganligi sababli qisman qaytarish",
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert code == 201, f"Expected 201 on API-095, got {code}: {refund_resp}"
    assert refund_resp.get("contract_id") == "API-095", f"Contract ID mismatch: {refund_resp}"
    assert refund_resp.get("status") == "REQUESTED", f"Expected status 'REQUESTED', got {refund_resp}"
    assert "refund_id" in refund_resp, f"refund_id missing: {refund_resp}"
    print(f"  ✓ Refund request submitted successfully (Refund ID: {refund_resp.get('refund_id')[:8]}, Status: {refund_resp.get('status')}).")

    # -------------------------------------------------------------------------
    # PHASE 10: Multi-Tenant RBAC & Foreign Org IDOR Isolation
    # -------------------------------------------------------------------------
    print("\n[Phase 10] Multi-Tenant RBAC & Foreign Org IDOR Isolation...")
    # Owner trying to access other_org_id billing overview -> 404 ORGANIZATION_NOT_FOUND (IDOR defense)
    code, idor_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{other_org_id}/billing",
        method="GET",
        opener=opener,
    )
    assert code == 404, f"Expected 404 on cross-organization billing query, got {code}: {idor_resp}"
    print("  ✓ Cross-organization IDOR query strictly rejected with HTTP 404.")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF EMPLOYER BILLING, ORDERS & REFUNDS PASSED (100% GREEN)!")
    print("================================================================================")


if __name__ == "__main__":
    main()
