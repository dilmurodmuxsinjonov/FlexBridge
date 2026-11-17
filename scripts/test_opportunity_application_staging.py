#!/usr/bin/env python3
"""FlexBridge 1.4 Candidate Opportunity Detail & Application Workflow Staging Verification Suite (Issue #146).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated opportunity detail fetch (HTTP 200 via BFF, API-005 contract).
Phase 2: Unauthenticated application attempt rejected (HTTP 401 AUTH_REQUIRED).
Phase 3: Cross-site CSRF origin application attempt rejected (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 4: Candidate authentication via BFF HttpOnly cookie and successful application submission (HTTP 201 CREATED, API-006 contract).
Phase 5: Re-application duplicate defense (HTTP 409 ALREADY_APPLIED / APPLICATION_ALREADY_EXISTS).
Phase 6: Employer HR authentication, drafting a new vacancy via BFF, and verifying it in organization dashboard metrics (API-068).

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


def run_opportunity_application_staging_tests() -> bool:
    print("=" * 80)
    print("FLEXBRIDGE 1.4 CANDIDATE OPPORTUNITY APPLICATION & VACANCY SUITE (Issue #146)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Fixture Seeding via PgBouncer (127.0.0.1:5432/flexbridge)
    # -------------------------------------------------------------------------
    print("\n[Setup] Seeding test fixtures in Staging PostgreSQL via PgBouncer...")
    db_url = get_database_url()
    engine = create_engine(db_url, connect_args={"prepare_threshold": None}, pool_pre_ping=True)

    candidate_user_id = str(uuid4())
    candidate_password = f"BffCand_Pass_{uuid4().hex[:10]}!"

    hr_user_id = str(uuid4())
    hr_password = f"BffHR_Pass_{uuid4().hex[:10]}!"

    org_id = str(uuid4())
    opp_id = str(uuid4())
    rev_id = str(uuid4())

    with engine.begin() as conn:
        hr_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'HR'")
        ).scalar()
        if not hr_role_id:
            hr_role_id = str(uuid4())
            conn.execute(
                text("""
                    INSERT INTO flexbridge.role_catalog (id, created_at, updated_at, code, scope_kind, description)
                    VALUES (:id, NOW(), NOW(), 'HR', 'ORG', 'Human resources manager')
                    ON CONFLICT (code) DO NOTHING
                """),
                {"id": hr_role_id},
            )
            hr_role_id = conn.execute(text("SELECT id FROM flexbridge.role_catalog WHERE code = 'HR'")).scalar()

        # 1. Candidate User & Profile
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'Staging Candidate User', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": candidate_user_id, "password_hash": hash_password(candidate_password)},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, experience_months, visibility)
                VALUES (:profile_id, NOW(), NOW(), :user_id, 'Software Engineer Candidate', 'Tashkent', 24, 'PUBLIC')
            """),
            {"profile_id": str(uuid4()), "user_id": candidate_user_id},
        )

        # 2. HR User & Organization
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'Staging HR Manager', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": hr_user_id, "password_hash": hash_password(hr_password)},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, NOW(), NOW(), :tax_id, 'Staging Tech Solutions MCHJ', 'Staging Tech Solutions', 'Tashkent', 'ACTIVE')
            """),
            {"id": org_id, "tax_id": f"TAX_{uuid4().hex[:8]}"},
        )

        # 3. HR Membership & Role Grant
        hr_mem_id = str(uuid4())
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status, accepted_at)
                VALUES (:id, NOW(), NOW(), :org_id, :user_id, 'ACTIVE', NOW())
            """),
            {"id": hr_mem_id, "org_id": org_id, "user_id": hr_user_id},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_role_grants (id, created_at, updated_at, membership_id, role_id, granted_by_id)
                VALUES (:id, NOW(), NOW(), :mem_id, :role_id, :granted_by)
            """),
            {"id": str(uuid4()), "mem_id": hr_mem_id, "role_id": hr_role_id, "granted_by": hr_user_id},
        )

        # 4. Opportunity & Revision 1 (PUBLISHED)
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
                    :id, NOW(), NOW(), :opp_id, 1, :author_id, 'Senior Python Backend Developer',
                    'Exciting part-time opportunity for senior backend developers.',
                    'Tashkent', 'HYBRID', 'OPEN', true, 50000, 75000, 'UZS', 'HOUR', 'GROSS',
                    CURRENT_DATE, 'FLEXIBLE', 'ALL_SHIFTS_IN_GROUP', 1, NOW(), 'LABOR_PART_TIME'
                )
            """),
            {"id": rev_id, "opp_id": opp_id, "author_id": hr_user_id},
        )
        conn.execute(
            text("UPDATE flexbridge.opportunities SET current_revision_id = :rev_id WHERE id = :opp_id"),
            {"rev_id": rev_id, "opp_id": opp_id},
        )

    print(f"  ✓ Seeded candidate ({candidate_user_id[:8]}), HR ({hr_user_id[:8]}), Org ({org_id[:8]}), Opp ({opp_id[:8]}).")

    # -------------------------------------------------------------------------
    # Phase 1: Unauthenticated Opportunity Detail Fetch (HTTP 200 via BFF)
    # -------------------------------------------------------------------------
    print("\n[Phase 1] Testing unauthenticated opportunity detail fetch via BFF...")
    status, body, _ = make_request(f"{FRONTEND_URL}/api/bff/opportunities/{opp_id}")
    assert status == 200, f"Expected 200 for opportunity detail, got {status}: {body}"
    assert body.get("contract_id") == "API-005", f"Expected contract API-005, got {body.get('contract_id')}"
    assert body.get("id") == opp_id, f"Expected opportunity id {opp_id}, got {body.get('id')}"
    assert body.get("status") == "PUBLISHED", f"Expected status PUBLISHED, got {body.get('status')}"
    revision = body.get("revision") or {}
    assert revision.get("title") == "Senior Python Backend Developer", f"Unexpected title: {revision.get('title')}"
    assert revision.get("contract_type") == "LABOR_PART_TIME", f"Unexpected contract: {revision.get('contract_type')}"
    print(f"  ✓ Phase 1 PASSED: GET /api/bff/opportunities/{opp_id[:8]} -> 200 OK (API-005: {revision.get('title')})")

    # -------------------------------------------------------------------------
    # Phase 2: Unauthenticated Application Attempt Rejected (HTTP 401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Testing unauthenticated application attempt rejection...")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/opportunities/{opp_id}/apply",
        method="POST",
        data={"note": "Unauthenticated apply attempt"},
        headers={"Origin": FRONTEND_URL},
    )
    assert status == 401, f"Expected 401 AUTH_REQUIRED for unauth apply, got {status}: {body}"
    assert body.get("error") == "AUTH_REQUIRED", f"Expected error AUTH_REQUIRED, got {body.get('error')}"
    print(f"  ✓ Phase 2 PASSED: POST /api/bff/opportunities/{opp_id[:8]}/apply -> 401 AUTH_REQUIRED")

    # -------------------------------------------------------------------------
    # Phase 3: Cross-site CSRF Origin Application Attempt Rejected (HTTP 403 CSRF_ORIGIN_MISMATCH)
    # -------------------------------------------------------------------------
    print("\n[Phase 3] Testing cross-site CSRF origin mismatch rejection...")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/opportunities/{opp_id}/apply",
        method="POST",
        data={"note": "Malicious CSRF payload"},
        headers={"Origin": "https://malicious-attacker.com"},
    )
    assert status == 403, f"Expected 403 CSRF_ORIGIN_MISMATCH, got {status}: {body}"
    assert body.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got {body.get('error')}"
    print(f"  ✓ Phase 3 PASSED: POST /api/bff/opportunities/{opp_id[:8]}/apply (cross-origin) -> 403 CSRF_ORIGIN_MISMATCH")

    # -------------------------------------------------------------------------
    # Phase 4: Candidate Authentication & Successful Application Submission (HTTP 201, API-006)
    # -------------------------------------------------------------------------
    print("\n[Phase 4] Testing candidate authentication and application submission via BFF...")
    candidate_cj = http.cookiejar.CookieJar()
    candidate_browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(candidate_cj))

    login_status, login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": candidate_user_id, "password": candidate_password},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_browser,
    )
    assert login_status == 200, f"Candidate login failed: {login_status} {login_body}"
    assert login_body.get("ok") is True, f"Candidate login response not ok: {login_body}"
    session_cookies = [c for c in candidate_cj if c.name == "flexbridge_session"]
    assert len(session_cookies) > 0, "flexbridge_session cookie not found in cookie jar!"
    print(f"  ✓ Candidate authenticated successfully. Session cookie established.")

    apply_status, apply_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/opportunities/{opp_id}/apply",
        method="POST",
        data={"note": "Dear hiring manager, I am very interested in this part-time opportunity.", "proposed_slots": []},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_browser,
    )
    assert apply_status == 201, f"Expected 201 CREATED for application submission, got {apply_status}: {apply_body}"
    assert apply_body.get("contract_id") == "API-006", f"Expected contract API-006, got {apply_body.get('contract_id')}"
    assert apply_body.get("status") == "SUBMITTED", f"Expected status SUBMITTED, got {apply_body.get('status')}"
    application_id = apply_body.get("id") or apply_body.get("application_id")
    assert application_id, f"Application ID missing from response: {apply_body}"
    print(f"  ✓ Phase 4 PASSED: POST /api/bff/opportunities/{opp_id[:8]}/apply -> 201 CREATED (API-006: app_id={application_id[:8]}...)")

    # -------------------------------------------------------------------------
    # Phase 5: Re-application Duplicate Defense (HTTP 409 ALREADY_APPLIED / APPLICATION_ALREADY_EXISTS)
    # -------------------------------------------------------------------------
    print("\n[Phase 5] Testing re-application duplicate defense...")
    dup_status, dup_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/opportunities/{opp_id}/apply",
        method="POST",
        data={"note": "Duplicate application attempt"},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_browser,
    )
    assert dup_status == 409, f"Expected 409 CONFLICT for duplicate application, got {dup_status}: {dup_body}"
    err_code = dup_body.get("code") or dup_body.get("error") or dup_body.get("detail", {}).get("code")
    assert err_code in ("APPLICATION_ALREADY_EXISTS", "ALREADY_APPLIED"), f"Unexpected duplicate error code: {dup_body}"
    print(f"  ✓ Phase 5 PASSED: Re-application attempt rejected -> 409 CONFLICT ({err_code})")

    # -------------------------------------------------------------------------
    # Phase 6: Employer HR Authentication, Vacancy Draft & Dashboard Metrics (API-068)
    # -------------------------------------------------------------------------
    print("\n[Phase 6] Testing Employer HR authentication, vacancy drafting & dashboard metrics...")
    hr_cj = http.cookiejar.CookieJar()
    hr_browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(hr_cj))

    hr_login_status, hr_login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": hr_user_id, "password": hr_password},
        headers={"Origin": FRONTEND_URL},
        opener=hr_browser,
    )
    assert hr_login_status == 200, f"HR login failed: {hr_login_status} {hr_login_body}"
    assert hr_login_body.get("ok") is True, f"HR login response not ok: {hr_login_body}"
    print("  ✓ Employer HR logged in successfully via BFF.")

    # 6a. Baseline Dashboard Metrics
    base_dash_status, base_dash_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/dashboard?org={org_id}",
        opener=hr_browser,
    )
    assert base_dash_status == 200, f"Baseline dashboard fetch failed: {base_dash_status} {base_dash_body}"
    assert base_dash_body.get("contract_id") == "API-068", f"Unexpected contract: {base_dash_body}"
    baseline_opps = base_dash_body.get("opportunities") or {}
    baseline_draft = baseline_opps.get("draft", 0)
    baseline_total = baseline_opps.get("total", 0)
    print(f"  ✓ Baseline dashboard metrics: draft={baseline_draft}, total={baseline_total}")

    # 6b. Draft New Vacancy via BFF
    vac_title = f"Staging Frontend Engineer Vacancy {uuid4().hex[:6]}"
    vac_status, vac_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/opportunities/create",
        method="POST",
        data={
            "organization_id": org_id,
            "title": vac_title,
            "opportunity_kind": "PART_TIME_JOB",
            "contract_type": "LABOR_PART_TIME",
            "compensation_type": "HOURLY",
            "hourly_pay": 45000,
            "published": False,
        },
        headers={"Origin": FRONTEND_URL},
        opener=hr_browser,
    )
    assert vac_status in (200, 201), f"Expected 200/201 for vacancy creation, got {vac_status}: {vac_body}"
    new_opp_id = vac_body.get("opportunity_id") or vac_body.get("id")
    assert new_opp_id, f"Opportunity ID missing in creation response: {vac_body}"
    print(f"  ✓ Created draft vacancy revision via BFF -> {vac_status} (opp_id={new_opp_id[:8]}..., title='{vac_title}')")

    # 6c. Verify Updated Dashboard Metrics
    upd_dash_status, upd_dash_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/dashboard?org={org_id}",
        opener=hr_browser,
    )
    assert upd_dash_status == 200, f"Updated dashboard fetch failed: {upd_dash_status} {upd_dash_body}"
    upd_opps = upd_dash_body.get("opportunities") or {}
    upd_draft = upd_opps.get("draft", 0)
    upd_total = upd_opps.get("total", 0)

    assert upd_draft == baseline_draft + 1, f"Expected draft count {baseline_draft + 1}, got {upd_draft}"
    assert upd_total == baseline_total + 1, f"Expected total count {baseline_total + 1}, got {upd_total}"
    print(f"  ✓ Phase 6 PASSED: Metrics updated dynamically (draft: {baseline_draft} -> {upd_draft}, total: {baseline_total} -> {upd_total})")

    print("\n" + "=" * 80)
    print("ALL 6 PHASES PASSED WITH 100% VICTORY (STAGING VERIFICATION COMPLETE)")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        success = run_opportunity_application_staging_tests()
        sys.exit(0 if success else 1)
    except Exception as exc:
        print(f"\n❌ TEST SUITE FAILED WITH EXCEPTION: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
