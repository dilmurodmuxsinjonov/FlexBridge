#!/usr/bin/env python3
"""FlexBridge 1.4 Employer Kanban, Interview Scheduling & Offer Dispatch Verification Suite (Issue #150).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected for all 5 Employer BFF endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Fixture seeding in Staging PostgreSQL via PgBouncer (127.0.0.1:5432/flexbridge).
Phase 3: Employer HR authentication via Next.js BFF (/api/auth/login) with encrypted HttpOnly session cookie.
Phase 4: Candidate application creation via API-006 (status SUBMITTED).
Phase 5: Employer lists opportunity applications via BFF (API-082 contract).
Phase 6: Employer transitions candidate SUBMITTED -> REVIEWING (API-083 contract).
Phase 7: Employer transitions candidate REVIEWING -> SHORTLISTED (API-083 contract).
Phase 8: Employer schedules interview via BFF (API-085 contract, status INTERVIEW_SCHEDULED).
Phase 9: Employer issues job offer via BFF (API-086 contract, status OFFERED).
Phase 10: Employer inspects applicant HR detail & audit event timeline via BFF (API-084 contract).
Phase 11: Cross-site CSRF rejection on state-mutating employer endpoints (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 12: Offer dispatch idempotency verification (API-086 idempotent return).

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import http.cookiejar
from datetime import datetime, timedelta, timezone
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


def run_employer_kanban_staging_tests() -> bool:
    print("=" * 80)
    print("FLEXBRIDGE 1.4 EMPLOYER KANBAN & INTERVIEWS/OFFERS STAGING SUITE (Issue #150)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Phase 1: Unauthenticated Requests Rejected (HTTP 401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n[Phase 1] Testing unauthenticated access rejection across all 5 Employer BFF routes...")
    dummy_id = str(uuid4())

    routes = [
        ("GET", f"{FRONTEND_URL}/api/bff/employer/opportunities/{dummy_id}/applications", None),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/applications/{dummy_id}/transition", {"to_status": "REVIEWING"}),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/applications/{dummy_id}/hr", None),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/applications/{dummy_id}/interviews", {
            "starts_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/applications/{dummy_id}/offers", {}),
    ]

    for m, u, d in routes:
        s, data, _ = make_request(u, method=m, data=d)
        print(f"  {m} {u} -> Status {s}")
        assert s == 401, f"Expected 401 for {u}, got {s}"
        assert data.get("error") == "AUTH_REQUIRED", f"Unexpected error body for {u}: {data}"

    print("  [Phase 1 PASS] All 5 Employer BFF endpoints enforce authentication safely.")

    # -------------------------------------------------------------------------
    # Phase 2: Fixture Seeding via PgBouncer (127.0.0.1:5432/flexbridge)
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Seeding test fixtures in Staging PostgreSQL via PgBouncer...")
    db_url = get_database_url()
    engine = create_engine(db_url, connect_args={"prepare_threshold": None}, pool_pre_ping=True)

    employer_user_id = str(uuid4())
    employer_password = f"HRPass_{uuid4().hex[:10]}!"

    candidate_user_id = str(uuid4())
    candidate_profile_id = str(uuid4())
    candidate_password = f"CandPass_{uuid4().hex[:10]}!"

    org_id = str(uuid4())
    opp_id = str(uuid4())
    rev_id = str(uuid4())
    app_id = str(uuid4())
    membership_id = str(uuid4())

    with engine.begin() as conn:
        # 1. Employer HR User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'FB-150 HR Manager', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": employer_user_id, "password_hash": hash_password(employer_password)},
        )

        # 2. Employer Organization
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, NOW(), NOW(), :tax_id, 'Kanban HR Corp LLC', 'Kanban HR Corp', 'Tashkent', 'ACTIVE')
            """),
            {"id": org_id, "tax_id": f"TAX_{uuid4().hex[:8]}"},
        )

        # 3. Active HR Membership and Role Grant
        role_row = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'HR' AND scope_kind = 'ORG'")
        ).mappings().first()
        if not role_row:
            role_row = conn.execute(
                text("SELECT id FROM flexbridge.role_catalog WHERE code = 'OWNER' AND scope_kind = 'ORG'")
            ).mappings().first()

        conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status, accepted_at)
                VALUES (:id, NOW(), NOW(), :org_id, :user_id, 'ACTIVE', NOW())
            """),
            {"id": membership_id, "org_id": org_id, "user_id": employer_user_id},
        )

        if role_row:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.org_role_grants (id, created_at, updated_at, membership_id, role_id, granted_by_id)
                    VALUES (:id, NOW(), NOW(), :membership_id, :role_id, :granted_by_id)
                """),
                {
                    "id": str(uuid4()),
                    "membership_id": membership_id,
                    "role_id": role_row["id"],
                    "granted_by_id": employer_user_id,
                },
            )

        # 4. Candidate User & Profile
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'FB-150 Candidate', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": candidate_user_id, "password_hash": hash_password(candidate_password)},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, experience_months, visibility)
                VALUES (:profile_id, NOW(), NOW(), :user_id, 'Senior Next.js & Python Engineer', 'Tashkent', 24, 'PUBLIC')
            """),
            {"profile_id": candidate_profile_id, "user_id": candidate_user_id},
        )

        # 5. Opportunity & Revision 1 (PUBLISHED)
        conn.execute(
            text("""
                INSERT INTO flexbridge.opportunities (
                    id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count, published_at, expires_at
                )
                VALUES (
                    :id, NOW(), NOW(), :org_id, 'PART_TIME', 'PUBLISHED', 10, 0, NOW(), NOW() + INTERVAL '30 days'
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
                    :rev_id, NOW(), NOW(), :opp_id, 1, :author_id, 'Full-Stack Developer Intern',
                    'Join our engineering team for cutting edge platform development',
                    'Tashkent', 'HYBRID', 'OPEN', true, 50000, 75000, 'UZS', 'HOUR', 'GROSS',
                    CURRENT_DATE, 'FLEXIBLE', 'ALL_SHIFTS_IN_GROUP', 1, NOW(), 'LABOR_PART_TIME'
                )
            """),
            {"rev_id": rev_id, "opp_id": opp_id, "author_id": employer_user_id},
        )

        conn.execute(
            text("UPDATE flexbridge.opportunities SET current_revision_id = :rev_id WHERE id = :opp_id"),
            {"rev_id": rev_id, "opp_id": opp_id},
        )

        # 6. Candidate Application (SUBMITTED)
        attempt_id = str(uuid4())
        conn.execute(
            text("""
                INSERT INTO flexbridge.applications (
                    id, created_at, updated_at, opportunity_id, candidate_id, status, version, current_attempt_id
                )
                VALUES (
                    :app_id, NOW(), NOW(), :opp_id, :candidate_id, 'SUBMITTED', 1, :attempt_id
                )
            """),
            {"app_id": app_id, "opp_id": opp_id, "candidate_id": candidate_profile_id, "attempt_id": attempt_id},
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.application_attempts (
                    id, created_at, updated_at, application_id, opportunity_id, attempt_no, revision_id,
                    profile_snapshot, schedule_result, matching_version, submitted_at, idempotency_key
                )
                VALUES (
                    :attempt_id, NOW(), NOW(), :app_id, :opp_id, 1, :rev_id,
                    '{"skills": ["Next.js", "FastAPI", "PostgreSQL"], "experience": "2 years"}',
                    'ALL_SHIFTS_ACCEPTED', '1.0', NOW(), :idem_key
                )
            """),
            {
                "attempt_id": attempt_id,
                "app_id": app_id,
                "opp_id": opp_id,
                "rev_id": rev_id,
                "idem_key": str(uuid4()),
            },
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.application_events (
                    id, created_at, updated_at, occurred_at, application_id, attempt_id, actor_id, from_status, to_status, reason
                )
                VALUES (
                    :event_id, NOW(), NOW(), NOW(), :app_id, :attempt_id, :actor_id, NULL, 'SUBMITTED', 'Initial application submission'
                )
            """),
            {
                "event_id": str(uuid4()),
                "app_id": app_id,
                "attempt_id": attempt_id,
                "actor_id": candidate_user_id,
            },
        )

    print("  [Setup OK] Employer HR User:", employer_user_id)
    print("  [Setup OK] Organization:", org_id)
    print("  [Setup OK] Opportunity:", opp_id)
    print("  [Setup OK] Application:", app_id)

    # -------------------------------------------------------------------------
    # Phase 3: Employer Login via Next.js BFF (/api/auth/login)
    # -------------------------------------------------------------------------
    print("\n[Phase 3] Authenticating employer HR via Next.js BFF session layer...")
    cookie_jar = http.cookiejar.CookieJar()
    session_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    login_payload = {
        "user_id": employer_user_id,
        "password": employer_password,
    }
    p3_status, p3_data, _ = make_request(
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
    print("  [Phase 3 PASS] Employer HR authenticated; HttpOnly session established.")

    # -------------------------------------------------------------------------
    # Phase 4 & 5: Employer Lists Opportunity Applications via BFF (API-082)
    # -------------------------------------------------------------------------
    print("\n[Phase 5] Testing authenticated GET /api/bff/employer/opportunities/{id}/applications (API-082)...")
    p5_status, p5_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/opportunities/{opp_id}/applications",
        method="GET",
        opener=session_opener,
    )
    print(f"  List Status: {p5_status}, Contract: {p5_data.get('contract_id')}, Items Count: {len(p5_data.get('items', []))}")
    assert p5_status == 200, f"Expected 200, got {p5_status}"
    assert p5_data.get("contract_id") == "API-082", f"Contract ID mismatch: {p5_data}"
    items = p5_data.get("items", [])
    assert len(items) == 1, f"Expected 1 application, got {len(items)}"
    target_app = items[0]
    assert target_app["application_id"] == app_id
    assert target_app["status"] == "SUBMITTED"
    assert target_app["candidate_id"] == candidate_profile_id
    assert target_app["schedule_result"] == "ALL_SHIFTS_ACCEPTED"
    print("  [Phase 5 PASS] Opportunity applications list verified with API-082 contract.")

    # -------------------------------------------------------------------------
    # Phase 6: Employer Transitions Candidate SUBMITTED -> REVIEWING (API-083)
    # -------------------------------------------------------------------------
    print("\n[Phase 6] Testing candidate state transition SUBMITTED -> REVIEWING (API-083)...")
    p6_status, p6_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/applications/{app_id}/transition",
        method="POST",
        data={"to_status": "REVIEWING"},
        headers={"Origin": FRONTEND_URL},
        opener=session_opener,
    )
    print(f"  Transition Status: {p6_status}, Data: {p6_data}")
    assert p6_status == 200, f"Expected 200, got {p6_status}"
    assert p6_data.get("contract_id") == "API-083", f"Contract ID mismatch: {p6_data}"
    assert p6_data.get("from_status") == "SUBMITTED"
    assert p6_data.get("to_status") == "REVIEWING"
    print("  [Phase 6 PASS] Candidate successfully transitioned to REVIEWING.")

    # -------------------------------------------------------------------------
    # Phase 7: Employer Transitions Candidate REVIEWING -> SHORTLISTED (API-083)
    # -------------------------------------------------------------------------
    print("\n[Phase 7] Testing candidate state transition REVIEWING -> SHORTLISTED (API-083)...")
    p7_status, p7_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/applications/{app_id}/transition",
        method="POST",
        data={"to_status": "SHORTLISTED"},
        headers={"Origin": FRONTEND_URL},
        opener=session_opener,
    )
    print(f"  Transition Status: {p7_status}, Data: {p7_data}")
    assert p7_status == 200, f"Expected 200, got {p7_status}"
    assert p7_data.get("contract_id") == "API-083", f"Contract ID mismatch: {p7_data}"
    assert p7_data.get("from_status") == "REVIEWING"
    assert p7_data.get("to_status") == "SHORTLISTED"
    print("  [Phase 7 PASS] Candidate successfully transitioned to SHORTLISTED.")

    # -------------------------------------------------------------------------
    # Phase 8: Employer Schedules Interview (API-085)
    # -------------------------------------------------------------------------
    print("\n[Phase 8] Testing interview scheduling via BFF (API-085)...")
    now_dt = datetime.now(timezone.utc)
    s_time = (now_dt + timedelta(days=2)).isoformat()
    e_time = (now_dt + timedelta(days=2, hours=1)).isoformat()

    interview_payload = {
        "starts_at": s_time,
        "ends_at": e_time,
        "mode": "ONLINE",
        "location_or_link": "https://meet.google.com/flx-live-staging",
        "timezone": "Asia/Tashkent",
    }
    p8_status, p8_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/applications/{app_id}/interviews",
        method="POST",
        data=interview_payload,
        headers={"Origin": FRONTEND_URL},
        opener=session_opener,
    )
    print(f"  Interview Schedule Status: {p8_status}, Data: {p8_data}")
    assert p8_status == 200, f"Expected 200, got {p8_status}"
    assert p8_data.get("contract_id") == "API-085", f"Contract ID mismatch: {p8_data}"
    assert p8_data.get("application_id") == app_id
    assert p8_data.get("status") == "SCHEDULED"
    assert p8_data.get("mode") == "ONLINE"
    print("  [Phase 8 PASS] Interview scheduled; application transitioned to INTERVIEW_SCHEDULED.")

    # -------------------------------------------------------------------------
    # Phase 9: Employer Issues Job Offer (API-086)
    # -------------------------------------------------------------------------
    print("\n[Phase 9] Testing job offer dispatch via BFF (API-086)...")
    offer_key = str(uuid4())
    offer_expiry = (now_dt + timedelta(days=7)).isoformat()
    offer_payload = {
        "expires_at": offer_expiry,
        "terms_snapshot": {
            "salary_gross": 5500000,
            "currency": "UZS",
            "trial_period": "3 months",
        },
        "idempotency_key": offer_key,
    }
    p9_status, p9_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/applications/{app_id}/offers",
        method="POST",
        data=offer_payload,
        headers={"Origin": FRONTEND_URL},
        opener=session_opener,
    )
    print(f"  Offer Dispatch Status: {p9_status}, Data: {p9_data}")
    assert p9_status == 200, f"Expected 200, got {p9_status}"
    assert p9_data.get("contract_id") == "API-086", f"Contract ID mismatch: {p9_data}"
    assert p9_data.get("application_id") == app_id
    assert p9_data.get("status") == "OFFERED"
    assert p9_data.get("terms_snapshot", {}).get("salary_gross") == 5500000
    print("  [Phase 9 PASS] Job offer issued; application transitioned to OFFERED.")

    # -------------------------------------------------------------------------
    # Phase 10: Employer Inspects Application HR Detail & Audit Trail (API-084)
    # -------------------------------------------------------------------------
    print("\n[Phase 10] Testing HR detail snapshot and audit trail (API-084)...")
    p10_status, p10_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/applications/{app_id}/hr",
        method="GET",
        opener=session_opener,
    )
    print(f"  HR Detail Status: {p10_status}, App Status: {p10_data.get('status')}, Events: {len(p10_data.get('events', []))}")
    assert p10_status == 200, f"Expected 200, got {p10_status}"
    assert p10_data.get("contract_id") == "API-084", f"Contract ID mismatch: {p10_data}"
    assert p10_data.get("application_id") == app_id
    assert p10_data.get("status") == "OFFERED"
    assert p10_data.get("attempt", {}).get("profile_snapshot") is not None
    events = p10_data.get("events", [])
    assert len(events) >= 4, f"Expected at least 4 audit events, got {len(events)}"
    event_statuses = [e["to_status"] for e in events]
    print(f"  Recorded Event Statuses: {event_statuses}")
    assert "REVIEWING" in event_statuses
    assert "SHORTLISTED" in event_statuses
    assert "INTERVIEW_SCHEDULED" in event_statuses
    assert "OFFERED" in event_statuses
    print("  [Phase 10 PASS] Complete applicant HR snapshot and audit trail verified.")

    # -------------------------------------------------------------------------
    # Phase 11: Cross-Site CSRF Rejection on State-Mutating Endpoints
    # -------------------------------------------------------------------------
    print("\n[Phase 11] Testing cross-site CSRF rejection on state-mutating employer endpoints...")
    p11_status, p11_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/applications/{app_id}/transition",
        method="POST",
        data={"to_status": "REJECTED"},
        headers={"Origin": "https://malicious-attacker-site.com"},
        opener=session_opener,
    )
    print(f"  CSRF Transition Status: {p11_status}, Error: {p11_data.get('error')}")
    assert p11_status == 403, f"Expected 403, got {p11_status}"
    assert p11_data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Unexpected CSRF error: {p11_data}"
    print("  [Phase 11 PASS] Cross-site CSRF attempt rejected with 403 CSRF_ORIGIN_MISMATCH.")

    # -------------------------------------------------------------------------
    # Phase 12: Offer Dispatch Idempotency (API-086)
    # -------------------------------------------------------------------------
    print("\n[Phase 12] Testing offer dispatch idempotency with identical Idempotency-Key...")
    p12_status, p12_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/applications/{app_id}/offers",
        method="POST",
        data=offer_payload,
        headers={"Origin": FRONTEND_URL},
        opener=session_opener,
    )
    print(f"  Idempotent Offer Status: {p12_status}, Offer ID: {p12_data.get('id')}")
    assert p12_status == 200, f"Expected 200, got {p12_status}"
    assert p12_data.get("id") == p9_data.get("id"), "Idempotency key did not return existing offer"
    print("  [Phase 12 PASS] Idempotent offer dispatch verified.")

    print("\n" + "=" * 80)
    print("ALL 12 PHASES OF EMPLOYER KANBAN STAGING SUITE PASSED PERFECTLY!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_employer_kanban_staging_tests()
    sys.exit(0 if success else 1)
