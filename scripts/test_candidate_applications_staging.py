#!/usr/bin/env python3
"""FlexBridge 1.4 Candidate Applications Dashboard, Tracker & Withdrawal Workflow Staging Verification Suite (Issue #148).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated candidate summary attempt rejected (HTTP 401 AUTH_REQUIRED).
Phase 2: Unauthenticated candidate applications list attempt rejected (HTTP 401 AUTH_REQUIRED).
Phase 3: Candidate authentication via Next.js BFF (/api/auth/login) with encrypted HttpOnly cookie.
Phase 4: Candidate fetches empty application summary (HTTP 200, API-029 contract).
Phase 5: Candidate fetches empty applications list (HTTP 200, API-039 contract).
Phase 6: Candidate submits application to active opportunity (HTTP 201 CREATED, API-006 contract).
Phase 7: Candidate application summary verifies metrics increment (total=1, submitted=1).
Phase 8: Candidate applications list verifies opportunity metadata and SUBMITTED status (API-039).
Phase 9: Candidate application detail verifies full timeline events and attempt history (API-041).
Phase 10: Cross-site CSRF withdraw attempt rejected (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 11: Candidate withdraws active application with reason (HTTP 200, API-044 contract, status WITHDRAWN).
Phase 12: Post-withdrawal metrics and status verification (withdrawn=1, status=WITHDRAWN).

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import http.cookiejar
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4
from dotenv import dotenv_values

# Ensure backend modules can be imported
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
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
    op = opener or urllib.request.build_opener()

    try:
        with op.open(req, timeout=15) as resp:
            status = resp.status
            resp_headers = dict(resp.headers)
            content = resp.read().decode("utf-8")
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = {"raw": content}
            return status, parsed, resp_headers
    except urllib.error.HTTPError as err:
        status = err.code
        resp_headers = dict(err.headers)
        content = err.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"raw": content}
        return status, parsed, resp_headers


def run_candidate_applications_staging_tests() -> bool:
    print("=" * 80)
    print("FLEXBRIDGE 1.4 CANDIDATE APPLICATIONS TRACKER STAGING SUITE (Issue #148)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Fixture Seeding via PgBouncer (127.0.0.1:5432/flexbridge)
    # -------------------------------------------------------------------------
    print("\n[Setup] Seeding test fixtures in Staging PostgreSQL via PgBouncer...")
    db_url = get_database_url()
    engine = create_engine(db_url, connect_args={"prepare_threshold": None}, pool_pre_ping=True)

    candidate_user_id = str(uuid4())
    candidate_password = f"CandPass_{uuid4().hex[:10]}!"

    org_id = str(uuid4())
    opp_id = str(uuid4())
    rev_id = str(uuid4())

    with engine.begin() as conn:
        # 1. Candidate User & Profile
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'FB-148 Test Candidate', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": candidate_user_id, "password_hash": hash_password(candidate_password)},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, experience_months, visibility)
                VALUES (:profile_id, NOW(), NOW(), :user_id, 'Software Engineer Student', 'Tashkent', 12, 'PUBLIC')
            """),
            {"profile_id": str(uuid4()), "user_id": candidate_user_id},
        )

        # 2. Employer Organization
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, NOW(), NOW(), :tax_id, 'Staging Tracker Corp LLC', 'Tracker Corp', 'Tashkent', 'ACTIVE')
            """),
            {"id": org_id, "tax_id": f"TAX_{uuid4().hex[:8]}"},
        )

        # 3. Opportunity & Revision 1 (PUBLISHED)
        conn.execute(
            text("""
                INSERT INTO flexbridge.opportunities (
                    id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count, published_at, expires_at
                )
                VALUES (
                    :id, NOW(), NOW(), :org_id, 'PART_TIME', 'PUBLISHED', 5, 0, NOW(), NOW() + INTERVAL '30 days'
                )
            """),
            {"id": opp_id, "org_id": org_id},
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.opportunity_revisions (
                    id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                    region, work_mode, eligibility, is_paid, salary_min, salary_max, currency, salary_period,
                    salary_basis, start_date, schedule_policy, shift_match_mode, snapshot_schema, published_at, contract_type
                )
                VALUES (
                    :rev_id, NOW(), NOW(), :opp_id, 1, :author_id, 'Backend API Developer Intern',
                    'Exciting internship on Next.js and FastAPI',
                    'Tashkent', 'HYBRID', 'OPEN', true, 45000, 60000, 'UZS', 'HOUR', 'GROSS',
                    CURRENT_DATE, 'FLEXIBLE', 'ALL_SHIFTS_IN_GROUP', 1, NOW(), 'LABOR_PART_TIME'
                )
            """),
            {"rev_id": rev_id, "opp_id": opp_id, "author_id": candidate_user_id},
        )

        conn.execute(
            text("UPDATE flexbridge.opportunities SET current_revision_id = :rev_id WHERE id = :opp_id"),
            {"rev_id": rev_id, "opp_id": opp_id},
        )

    print("  [Setup OK] Candidate User:", candidate_user_id)
    print("  [Setup OK] Organization:", org_id)
    print("  [Setup OK] Opportunity:", opp_id)

    # Opener with cookie jar to test session persistence
    cookie_jar = http.cookiejar.CookieJar()
    session_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    # -------------------------------------------------------------------------
    # Phase 1: Unauthenticated Candidate Summary -> 401 AUTH_REQUIRED
    # -------------------------------------------------------------------------
    print("\n[Phase 1] Testing unauthenticated GET /api/bff/candidate/applications/summary...")
    p1_status, p1_data, _ = make_request(f"{FRONTEND_URL}/api/bff/candidate/applications/summary")
    print(f"  Response Status: {p1_status}, Body: {p1_data}")
    assert p1_status == 401, f"Expected 401, got {p1_status}"
    assert p1_data.get("error") == "AUTH_REQUIRED", f"Unexpected error code: {p1_data}"
    print("  [Phase 1 PASS] Unauthenticated summary access safely rejected with 401.")

    # -------------------------------------------------------------------------
    # Phase 2: Unauthenticated Candidate Applications List -> 401 AUTH_REQUIRED
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Testing unauthenticated GET /api/bff/candidate/applications...")
    p2_status, p2_data, _ = make_request(f"{FRONTEND_URL}/api/bff/candidate/applications")
    print(f"  Response Status: {p2_status}, Body: {p2_data}")
    assert p2_status == 401, f"Expected 401, got {p2_status}"
    assert p2_data.get("error") == "AUTH_REQUIRED", f"Unexpected error code: {p2_data}"
    print("  [Phase 2 PASS] Unauthenticated applications list safely rejected with 401.")

    # -------------------------------------------------------------------------
    # Phase 3: Candidate Login via Next.js BFF (/api/auth/login)
    # -------------------------------------------------------------------------
    print("\n[Phase 3] Authenticating candidate via Next.js BFF session layer...")
    login_payload = {
        "user_id": candidate_user_id,
        "password": candidate_password,
    }
    p3_status, p3_data, p3_headers = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data=login_payload,
        headers={"Origin": FRONTEND_URL},
        opener=session_opener,
    )
    print(f"  Login Status: {p3_status}, Data: {p3_data}")
    assert p3_status == 200, f"Expected login status 200, got {p3_status}"
    assert p3_data.get("ok") is True, f"Login response ok != True: {p3_data}"
    cookies_str = "; ".join(f"{c.name}={c.value}" for c in cookie_jar)
    assert "flexbridge_session" in cookies_str, "HttpOnly cookie flexbridge_session not found in jar"
    print("  [Phase 3 PASS] Candidate authenticated; HttpOnly session cookie established.")

    # -------------------------------------------------------------------------
    # Phase 4: Candidate Fetches Empty Application Summary (API-029)
    # -------------------------------------------------------------------------
    print("\n[Phase 4] Testing authenticated GET /api/bff/candidate/applications/summary (API-029)...")
    p4_status, p4_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/applications/summary",
        method="GET",
        opener=session_opener,
    )
    print(f"  Summary Status: {p4_status}, Data: {p4_data}")
    assert p4_status == 200, f"Expected 200, got {p4_status}"
    assert p4_data.get("contract_id") == "API-029", f"Contract ID mismatch: {p4_data}"
    assert p4_data.get("total_applications") == 0, f"Expected 0 total apps: {p4_data}"
    print("  [Phase 4 PASS] Initial summary retrieved cleanly via API-029 contract.")

    # -------------------------------------------------------------------------
    # Phase 5: Candidate Fetches Empty Applications List (API-039)
    # -------------------------------------------------------------------------
    print("\n[Phase 5] Testing authenticated GET /api/bff/candidate/applications (API-039)...")
    p5_status, p5_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/applications",
        method="GET",
        opener=session_opener,
    )
    print(f"  List Status: {p5_status}, Data: {p5_data}")
    assert p5_status == 200, f"Expected 200, got {p5_status}"
    assert p5_data.get("contract_id") == "API-039", f"Contract ID mismatch: {p5_data}"
    assert isinstance(p5_data.get("items"), list) and len(p5_data["items"]) == 0, f"Expected empty items: {p5_data}"
    print("  [Phase 5 PASS] Initial empty applications list returned cleanly via API-039.")

    # -------------------------------------------------------------------------
    # Phase 6: Candidate Submits Application to Opportunity (API-006)
    # -------------------------------------------------------------------------
    print("\n[Phase 6] Submitting candidate application to opportunity via BFF...")
    apply_payload = {
        "note": "Men ushbu amaliyot o'rniga jiddiy qiziqish bildiraman va shartlarga roziman.",
    }
    p6_status, p6_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/opportunities/{opp_id}/apply",
        method="POST",
        data=apply_payload,
        headers={"Origin": FRONTEND_URL, "Idempotency-Key": f"cand-idem-{uuid4().hex[:12]}"},
        opener=session_opener,
    )
    print(f"  Application Status: {p6_status}, Data: {p6_data}")
    assert p6_status == 201, f"Expected 201, got {p6_status}"
    assert p6_data.get("contract_id") == "API-006", f"Contract mismatch: {p6_data}"
    application_id = p6_data.get("id") or p6_data.get("application_id")
    assert application_id, f"Missing application ID: {p6_data}"
    print(f"  [Phase 6 PASS] Candidate application submitted; ID: {application_id}")

    # -------------------------------------------------------------------------
    # Phase 7: Candidate Summary Metrics Check (total=1, submitted=1)
    # -------------------------------------------------------------------------
    print("\n[Phase 7] Verifying updated application summary metrics (API-029)...")
    p7_status, p7_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/applications/summary",
        method="GET",
        opener=session_opener,
    )
    print(f"  Updated Summary: {p7_data}")
    assert p7_status == 200, f"Expected 200, got {p7_status}"
    assert p7_data.get("total_applications") == 1, f"Expected total 1, got {p7_data.get('total_applications')}"
    assert p7_data.get("submitted") == 1, f"Expected submitted 1, got {p7_data.get('submitted')}"
    print("  [Phase 7 PASS] Summary reflects submitted application (total=1, submitted=1).")

    # -------------------------------------------------------------------------
    # Phase 8: Candidate Applications List Check (API-039)
    # -------------------------------------------------------------------------
    print("\n[Phase 8] Verifying candidate applications list includes new application (API-039)...")
    p8_status, p8_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/applications",
        method="GET",
        opener=session_opener,
    )
    print(f"  List Data: {p8_data}")
    assert p8_status == 200, f"Expected 200, got {p8_status}"
    items = p8_data.get("items", [])
    assert len(items) == 1, f"Expected exactly 1 application in list, got {len(items)}"
    app_item = items[0]
    assert app_item["id"] == application_id, f"Application ID mismatch: {app_item['id']} vs {application_id}"
    assert app_item["status"] == "SUBMITTED", f"Expected status SUBMITTED, got {app_item['status']}"
    assert app_item["opportunity"]["title"] == "Backend API Developer Intern"
    assert app_item["opportunity"]["organization_name"] == "Tracker Corp"
    print("  [Phase 8 PASS] Application item accurately populated with opportunity metadata.")

    # -------------------------------------------------------------------------
    # Phase 9: Candidate Application Detail Fetch (API-041)
    # -------------------------------------------------------------------------
    print(f"\n[Phase 9] Testing authenticated GET /api/bff/candidate/applications/{application_id} (API-041)...")
    p9_status, p9_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/applications/{application_id}",
        method="GET",
        opener=session_opener,
    )
    print(f"  Detail Data: {p9_data}")
    assert p9_status == 200, f"Expected 200, got {p9_status}"
    assert p9_data.get("contract_id") == "API-041", f"Contract mismatch: {p9_data}"
    assert p9_data["id"] == application_id, f"ID mismatch: {p9_data['id']} vs {application_id}"
    assert len(p9_data.get("attempts", [])) >= 1, "Expected at least 1 attempt"
    assert len(p9_data.get("timeline", [])) >= 1, "Expected at least 1 timeline event"
    print("  [Phase 9 PASS] Application detail returned full attempts history and timeline events.")

    # -------------------------------------------------------------------------
    # Phase 10: Cross-Site CSRF Withdraw Attempt -> 403 CSRF_ORIGIN_MISMATCH
    # -------------------------------------------------------------------------
    print("\n[Phase 10] Testing cross-site CSRF rejection on application withdrawal...")
    csrf_headers = {
        "Origin": "https://malicious-cross-origin.com",
    }
    p10_status, p10_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/applications/{application_id}/withdraw",
        method="POST",
        data={"reason": "CSRF attack attempt"},
        headers=csrf_headers,
        opener=session_opener,
    )
    print(f"  CSRF Response: {p10_status}, {p10_data}")
    assert p10_status == 403, f"Expected 403 for cross-site origin, got {p10_status}"
    assert p10_data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Unexpected CSRF error: {p10_data}"
    print("  [Phase 10 PASS] Cross-site CSRF withdraw attempt safely blocked with 403.")

    # -------------------------------------------------------------------------
    # Phase 11: Candidate Withdraws Active Application (API-044)
    # -------------------------------------------------------------------------
    print("\n[Phase 11] Candidate withdrawing application via Next.js BFF (API-044)...")
    withdraw_headers = {
        "Origin": FRONTEND_URL,
    }
    p11_status, p11_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/applications/{application_id}/withdraw",
        method="POST",
        data={"reason": "Boshqa amaliyot dasturini tanladim"},
        headers=withdraw_headers,
        opener=session_opener,
    )
    print(f"  Withdraw Response: {p11_status}, {p11_data}")
    assert p11_status == 200, f"Expected 200, got {p11_status}"
    assert p11_data.get("contract_id") == "API-044", f"Contract mismatch: {p11_data}"
    assert p11_data.get("status") == "WITHDRAWN", f"Expected status WITHDRAWN, got {p11_data.get('status')}"
    print("  [Phase 11 PASS] Application successfully withdrawn; status updated to WITHDRAWN.")

    # -------------------------------------------------------------------------
    # Phase 12: Verify Post-Withdrawal Metrics & Status
    # -------------------------------------------------------------------------
    print("\n[Phase 12] Verifying updated summary metrics after withdrawal...")
    p12_status, p12_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/applications/summary",
        method="GET",
        opener=session_opener,
    )
    print(f"  Post-Withdraw Summary: {p12_data}")
    assert p12_status == 200
    assert p12_data.get("withdrawn") == 1, f"Expected withdrawn count 1, got {p12_data.get('withdrawn')}"
    assert p12_data.get("submitted") == 0, f"Expected submitted count 0, got {p12_data.get('submitted')}"

    # Also check list filter status=WITHDRAWN
    p12b_status, p12b_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/applications?status=WITHDRAWN",
        method="GET",
        opener=session_opener,
    )
    print(f"  Filtered List (WITHDRAWN): {p12b_data}")
    assert p12b_status == 200
    withdrawn_items = p12b_data.get("items", [])
    assert len(withdrawn_items) == 1
    assert withdrawn_items[0]["status"] == "WITHDRAWN"
    print("  [Phase 12 PASS] Summary and filtered list accurately reflect WITHDRAWN state.")

    print("\n" + "=" * 80)
    print("ALL 12 PHASES OF CANDIDATE APPLICATIONS TRACKER TEST SUITE PASSED!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_candidate_applications_staging_tests()
    sys.exit(0 if success else 1)
