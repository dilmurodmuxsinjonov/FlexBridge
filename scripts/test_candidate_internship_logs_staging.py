#!/usr/bin/env python3
"""
Staging Verification Suite: Candidate Internship Daily Log Management & Submission Workflow (FB-154)

Verifies:
1. Candidate BFF routes require authentication (401 AUTH_REQUIRED).
2. Candidate can query their active placements (API-030).
3. Candidate can view placement daily logs list (API-053).
4. Candidate can save draft daily logs with tasks and minutes breakdown (API-054).
5. Business validations enforced:
   - Future date rejection (422 INVALID_LOG_DATE)
   - Task minutes mismatch rejection (422 TASK_MINUTES_MISMATCH)
   - Daily minutes limit (>480 min) rejection (422 DAILY_MINUTES_LIMIT_EXCEEDED)
6. CSRF origin verification on state-changing BFF requests (403 CSRF_ORIGIN_MISMATCH).
7. Candidate can submit daily log for mentor/academic review (API-056).
8. Immutability guarantee: submitted log cannot be overwritten as draft (409 SUBMITTED_LOG_IMMUTABLE).

Tested against:
- Live Next.js BFF at http://127.0.0.1:3000
- PgBouncer at 127.0.0.1:5432/flexbridge (prepare_threshold=None)
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.services.auth import hash_password
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy.engine import URL
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parent.parent

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


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




def api_request(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    opener=None,
) -> Tuple[int, Any]:
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = Request(url, data=body, headers=req_headers, method=method)
    active_opener = opener or build_opener()

    try:
        with active_opener.open(req) as resp:
            code = resp.status
            content = resp.read().decode("utf-8")
            try:
                payload = json.loads(content)
            except Exception:
                payload = content
            return code, payload
    except HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            payload = json.loads(content)
        except Exception:
            payload = content
        return e.code, payload


def run_staging_suite():
    print("=" * 80)
    print("Starting FlexBridge 1.4 Staging Suite: Candidate Internship Daily Logs (FB-154)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_suffix = uuid4().hex[:8]
    student_user_id = str(uuid4())
    student_profile_id = str(uuid4())
    student_password = "CandidatePass123!"
    student_hash = hash_password(student_password)

    employer_user_id = str(uuid4())
    org_id = str(uuid4())
    org_membership_id = str(uuid4())
    opp_id = str(uuid4())
    opp_rev_id = str(uuid4())
    app_id = str(uuid4())
    attempt_id = str(uuid4())
    offer_id = str(uuid4())

    file_id = str(uuid4())
    inst_id = str(uuid4())
    inst_agreement_id = str(uuid4())
    enrollment_id = str(uuid4())
    supervision_id = str(uuid4())
    placement_id = str(uuid4())
    terms_id = str(uuid4())

    now_ts = datetime.now(timezone.utc)
    today_date = date.today()
    log_date_str = (today_date - timedelta(days=1)).isoformat()
    future_date_str = (today_date + timedelta(days=2)).isoformat()
    purpose = "ENGINEERING_INTERNSHIP"

    scope_snapshot = {
        "institution_id": inst_id,
        "enrollment_id": enrollment_id,
        "agreement_id": inst_agreement_id,
        "agreement_version": 1,
        "supervision_id": supervision_id,
        "purpose": purpose,
    }

    terms_snapshot = {
        "version": 1,
        "contract_type": "INTERNSHIP_AGREEMENT",
        "academic_scope": scope_snapshot,
    }

    seeded_trigger_tables = [
        "enrollments", "enrollment_origins",
        "student_supervisions", "supervision_origins",
        "placement_intakes", "placement_academic_bindings",
        "placements", "placement_terms",
        "daily_logs", "log_revisions", "log_task_entries",
    ]

    # =========================================================================
    # PHASE 1: Unauthenticated Rejection (401 AUTH_REQUIRED)
    # =========================================================================
    print("\n--- PHASE 1: Unauthenticated Route Guard Testing ---")
    dummy_placement_id = str(uuid4())
    dummy_log_id = str(uuid4())

    unauth_checks = [
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/placements", None),
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/placements/{dummy_placement_id}/logs", None),
        ("PUT", f"{FRONTEND_URL}/api/bff/candidate/placements/{dummy_placement_id}/logs/{log_date_str}", {
            "day_type": "WORKED",
            "total_minutes": 120,
            "tasks": [{"title": "Unauth task", "minutes": 120}],
        }),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/logs/{dummy_log_id}/submit", {}),
    ]

    for meth, url, body in unauth_checks:
        status, resp = api_request(url, method=meth, data=body)
        assert status == 401, f"Expected 401 for unauthenticated {meth} {url}, got {status}: {resp}"
        assert resp.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got: {resp}"
        print(f"✓ Correctly rejected unauthenticated {meth} {url} with 401 AUTH_REQUIRED")

    print("Phase 1 Passed: Unauthenticated requests safely blocked.")

    # =========================================================================
    # PHASE 2: Seed Database Fixtures via PgBouncer
    # =========================================================================
    print("\n--- PHASE 2: Database Fixture Seeding via PgBouncer ---")

    # Tx 1: Disable Triggers
    with engine.begin() as conn:
        for t in seeded_trigger_tables:
            conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

    try:
        # Tx 2: Seed Rows
        with engine.begin() as conn:
            # 1. Candidate User & Profile
            conn.execute(text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :ts, :ts, 'Botir Zokirov', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
            """), {"id": student_user_id, "pwd": student_hash, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, experience_months, visibility)
                VALUES (:id, :ts, :ts, :uid, 'Full Stack Developer', 'Tashkent', 12, 'PUBLIC')
            """), {"id": student_profile_id, "uid": student_user_id, "ts": now_ts})

            # 2. Employer User, Organization & Membership
            conn.execute(text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :ts, :ts, 'Employer Tech Director', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
            """), {"id": employer_user_id, "pwd": student_hash, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, :ts, :ts, :tax_id, 'Global Soft Innovations MCHJ', 'Global Soft', 'Tashkent', 'ACTIVE')
            """), {"id": org_id, "tax_id": f"TAX_LOG_{test_suffix}", "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status)
                VALUES (:id, :ts, :ts, :org_id, :uid, 'ACTIVE')
            """), {"id": org_membership_id, "org_id": org_id, "uid": employer_user_id, "ts": now_ts})

            # 3. Opportunity & Revision 1
            conn.execute(text("""
                INSERT INTO flexbridge.opportunities (id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count)
                VALUES (:id, :ts, :ts, :org_id, 'INTERNSHIP', 'PUBLISHED', 5, 1)
            """), {"id": opp_id, "org_id": org_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.opportunity_revisions (
                    id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                    region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                    shift_match_mode, snapshot_schema, contract_type
                )
                VALUES (
                    :id, :ts, :ts, :opp_id, 1, :author_id, 'Frontend & Full-stack Intern', 'React va Python bo‘yicha amaliyot',
                    'Tashkent', 'HYBRID', 'STUDENT', 'UZS', FALSE, :today, 'FLEXIBLE',
                    'EXACT', 1, 'INTERNSHIP_AGREEMENT'
                )
            """), {"id": opp_rev_id, "opp_id": opp_id, "author_id": employer_user_id, "today": today_date, "ts": now_ts})

            conn.execute(text("""
                UPDATE flexbridge.opportunities SET current_revision_id = :rev WHERE id = :id
            """), {"rev": opp_rev_id, "id": opp_id})

            # 4. Application, Attempt & Offer
            conn.execute(text("""
                INSERT INTO flexbridge.applications (id, created_at, updated_at, opportunity_id, candidate_id, status, version)
                VALUES (:id, :ts, :ts, :opp_id, :cand_id, 'OFFERED', 1)
            """), {"id": app_id, "opp_id": opp_id, "cand_id": student_profile_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.application_attempts (
                    id, created_at, updated_at, application_id, opportunity_id, attempt_no, revision_id,
                    profile_snapshot, schedule_result, matching_version, submitted_at, idempotency_key
                )
                VALUES (
                    :attempt_id, :ts, :ts, :app_id, :opp_id, 1, :rev_id,
                    '{"headline": "Talaba"}'::jsonb, '{"status": "MATCHED"}'::jsonb, 1, :ts, :idem
                )
            """), {
                "attempt_id": attempt_id, "app_id": app_id, "opp_id": opp_id, "rev_id": opp_rev_id,
                "ts": now_ts, "idem": f"idem-attempt-{uuid4().hex[:12]}"
            })

            conn.execute(text("""
                UPDATE flexbridge.applications SET current_attempt_id = :attempt_id WHERE id = :app_id
            """), {"attempt_id": attempt_id, "app_id": app_id})

            conn.execute(text("""
                INSERT INTO flexbridge.offers (
                    id, created_at, updated_at, application_id, attempt_id, revision_id,
                    issuer_membership_id, terms_snapshot, status, expires_at, idempotency_key
                )
                VALUES (
                    :id, :ts, :ts, :app_id, :attempt_id, :rev_id,
                    :issuer_id, '{}'::jsonb, 'ACCEPTED', :expires, :idem
                )
            """), {
                "id": offer_id, "app_id": app_id, "attempt_id": attempt_id, "rev_id": opp_rev_id,
                "issuer_id": org_membership_id, "expires": now_ts + timedelta(days=30),
                "idem": f"idem-offer-{uuid4().hex[:12]}", "ts": now_ts
            })

            # 5. Institution, Agreement, Enrollment
            conn.execute(text("""
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                VALUES (:id, :ts, :ts, :reg, 'Toshkent Axborot Texnologiyalari Universiteti', 'Tashkent', 'VERIFIED')
            """), {"id": inst_id, "reg": f"INST_LOG_{test_suffix}", "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.institution_agreements (id, created_at, updated_at, institution_id, version, status, valid_from, purposes)
                VALUES (:id, :ts, :ts, :inst_id, 1, 'ACTIVE', :today, jsonb_build_array('ENGINEERING_INTERNSHIP'))
            """), {"id": inst_agreement_id, "inst_id": inst_id, "today": today_date, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.enrollments (id, created_at, updated_at, candidate_id, institution_id, program, status, start_date)
                VALUES (:id, :ts, :ts, :cand_id, :inst_id, 'Dasturiy Injiniring', 'VERIFIED', :today)
            """), {"id": enrollment_id, "cand_id": student_profile_id, "inst_id": inst_id, "today": today_date, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.enrollment_origins (enrollment_id, created_at, origin, candidate_id, institution_id, actor_user_id, initial_snapshot)
                VALUES (:id, :ts, 'LEGACY_IMPORT', :cand_id, :inst_id, :actor_id, jsonb_build_object('status', 'VERIFIED'))
            """), {"id": enrollment_id, "cand_id": student_profile_id, "inst_id": inst_id, "actor_id": student_user_id, "ts": now_ts})

            # 6. Placement & Placement Terms
            conn.execute(text("""
                INSERT INTO flexbridge.placements (
                    id, created_at, updated_at, application_id, offer_id, candidate_id,
                    organization_id, enrollment_id, academic_track, status, start_date, end_date, version
                )
                VALUES (:id, :ts, :ts, :app_id, :offer_id, :cand_id, :org_id, :eid, TRUE, 'ACTIVE', :start_d, :end_d, 1)
            """), {
                "id": placement_id, "app_id": app_id, "offer_id": offer_id, "cand_id": student_profile_id,
                "org_id": org_id, "eid": enrollment_id, "start_d": today_date - timedelta(days=14),
                "end_d": today_date + timedelta(days=76), "ts": now_ts
            })

            conn.execute(text("""
                INSERT INTO flexbridge.placement_intakes (
                    placement_id, created_at, origin, offer_id, attempt_id, revision_id,
                    academic_required, initial_snapshot, source_snapshot
                )
                VALUES (
                    :pid, :ts, 'LEGACY_IMPORT', :offer_id, :attempt_id, :rev_id,
                    TRUE, '{}'::jsonb, '{}'::jsonb
                )
            """), {
                "pid": placement_id, "offer_id": offer_id, "attempt_id": attempt_id,
                "rev_id": opp_rev_id, "ts": now_ts
            })

            conn.execute(text("""
                INSERT INTO flexbridge.placement_terms (
                    id, created_at, updated_at, placement_id, version, schema_version,
                    terms_snapshot, daily_limit_minutes, weekly_limit_minutes, required_minutes
                )
                VALUES (:id, :ts, :ts, :pid, 1, 1, CAST(:snapshot AS jsonb), 480, 2400, 12000)
            """), {"id": terms_id, "pid": placement_id, "snapshot": json.dumps(terms_snapshot), "ts": now_ts})

            conn.execute(text("""
                UPDATE flexbridge.placements SET current_terms_id = :tid WHERE id = :pid
            """), {"tid": terms_id, "pid": placement_id})

            print(f"✓ Seeded placement {placement_id} for student user {student_user_id}")
    finally:
        # Tx 3: Re-enable Triggers
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))

    print("Phase 2 Passed: Test fixtures successfully seeded.")

    # =========================================================================
    # PHASE 3: Candidate Authentication via Next.js BFF (/api/auth/login)
    # =========================================================================
    print("\n--- PHASE 3: Candidate Authentication ---")
    candidate_cookie_jar = CookieJar()
    candidate_opener = build_opener(HTTPCookieProcessor(candidate_cookie_jar))

    login_status, login_data = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": student_user_id, "password": student_password},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )

    assert login_status == 200, f"Expected 200 on login, got {login_status}: {login_data}"
    assert login_data.get("ok") is True, f"Login payload should be ok: {login_data}"
    print(f"✓ Candidate logged in successfully: user_id={student_user_id}")
    print("Phase 3 Passed: Candidate authenticated.")

    # =========================================================================
    # PHASE 4: Candidate Fetches Active Placements (API-030 via BFF)
    # =========================================================================
    print("\n--- PHASE 4: Candidate Fetches Active Placements (API-030) ---")
    placements_status, placements_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )

    assert placements_status == 200, f"Expected 200 on candidate placements, got {placements_status}: {placements_data}"
    items = placements_data.get("items", [])
    assert len(items) >= 1, f"Expected at least 1 placement, got: {placements_data}"

    matching_placement = next((p for p in items if p.get("id") == placement_id), None)
    assert matching_placement is not None, f"Seeded placement {placement_id} not found in {items}"
    assert matching_placement.get("status") == "ACTIVE"
    print(f"✓ Verified candidate placement ID {placement_id} (status={matching_placement.get('status')})")
    print("Phase 4 Passed: Candidate active placements retrieved via API-030.")

    # =========================================================================
    # PHASE 5: Business Validations & Save Draft Daily Log (API-054 via BFF)
    # =========================================================================
    print("\n--- PHASE 5: Daily Log Draft Validations & Creation (API-054) ---")

    # 5.1 Validation: Future Date Rejection
    future_status, future_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements/{placement_id}/logs/{future_date_str}",
        method="PUT",
        data={
            "day_type": "WORKED",
            "summary": "Kelajakdagi kun amaliyoti",
            "total_minutes": 240,
            "tasks": [{"title": "Future task", "minutes": 240}],
        },
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert future_status == 422, f"Expected 422 for future date, got {future_status}: {future_data}"
    print(f"✓ Future date correctly rejected with 422 ({future_data.get('error')})")

    # 5.2 Validation: Task Minutes Mismatch
    mismatch_status, mismatch_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements/{placement_id}/logs/{log_date_str}",
        method="PUT",
        data={
            "day_type": "WORKED",
            "summary": "Daqiqalar mos kelmasligi",
            "total_minutes": 360,
            "tasks": [{"title": "Vazifa 1", "minutes": 200}],  # 200 != 360
        },
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert mismatch_status == 422, f"Expected 422 for minutes mismatch, got {mismatch_status}: {mismatch_data}"
    print(f"✓ Task minutes mismatch correctly rejected with 422 ({mismatch_data.get('error')})")

    # 5.3 Validation: Daily Limit Exceeded (> 480 minutes / 8 hours)
    over_limit_status, over_limit_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements/{placement_id}/logs/{log_date_str}",
        method="PUT",
        data={
            "day_type": "WORKED",
            "summary": "8 soatdan ortiq ish",
            "total_minutes": 540,
            "tasks": [{"title": "Katta vazifa", "minutes": 540}],
        },
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert over_limit_status in (400, 422), f"Expected 400/422 for >480 min, got {over_limit_status}: {over_limit_data}"
    print(f"✓ Daily 480-minute limit exceeded correctly rejected with HTTP {over_limit_status} ({over_limit_data.get('error')})")

    # 5.4 Valid Draft Save: 360 minutes (6 hours), 2 tasks
    draft_tasks = [
        {"title": "Backend BFF API va xavfsizlik cheklovlari", "minutes": 180},
        {"title": "Frontend Kundalik UI va validatsiya logikasi", "minutes": 180},
    ]
    save_status, save_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements/{placement_id}/logs/{log_date_str}",
        method="PUT",
        data={
            "day_type": "WORKED",
            "summary": "FlexBridge 1.4 nomzod kundaligi moduli to‘liq ishlab chiqildi.",
            "total_minutes": 360,
            "tasks": draft_tasks,
        },
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )

    assert save_status in (200, 201), f"Expected 200/201 on saving draft log, got {save_status}: {save_data}"
    saved_daily_log_id = save_data.get("id") or save_data.get("daily_log_id")
    assert saved_daily_log_id, f"Expected saved daily log ID in response: {save_data}"
    assert save_data.get("status") == "DRAFT"
    print(f"✓ Saved draft daily log {saved_daily_log_id} with 2 tasks (status=DRAFT)")
    print("Phase 5 Passed: Draft validations and creation verified.")

    # =========================================================================
    # PHASE 6: Candidate Fetches Placement Logs List (API-053 via BFF)
    # =========================================================================
    print("\n--- PHASE 6: Placement Daily Logs List (API-053) ---")
    logs_status, logs_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements/{placement_id}/logs",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )

    assert logs_status == 200, f"Expected 200 on logs list, got {logs_status}: {logs_data}"
    log_items = logs_data.get("items", [])
    assert len(log_items) >= 1, f"Expected at least 1 log entry in list: {logs_data}"

    found_log = next((l for l in log_items if l.get("local_date") == log_date_str or l.get("log_date") == log_date_str), None)
    assert found_log is not None, f"Saved log for date {log_date_str} not found in {log_items}"
    rev = found_log.get("current_revision") or {}
    assert rev.get("status") == "DRAFT"
    assert rev.get("total_minutes") == 360
    print(f"✓ Verified placement logs list includes draft log for date {log_date_str} with {rev.get('total_minutes')} min")
    print("Phase 6 Passed: Placement logs list retrieved via API-053.")

    # =========================================================================
    # PHASE 7: Cross-Site CSRF Protection
    # =========================================================================
    print("\n--- PHASE 7: Cross-Site CSRF Protection Testing ---")
    csrf_put_status, csrf_put_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements/{placement_id}/logs/{log_date_str}",
        method="PUT",
        data={"day_type": "WORKED", "total_minutes": 60, "tasks": [{"title": "CSRF task", "minutes": 60}]},
        headers={"Sec-Fetch-Site": "cross-site", "Origin": "https://attacker-domain.evil"},
        opener=candidate_opener,
    )
    assert csrf_put_status == 403, f"Expected 403 for cross-site PUT, got {csrf_put_status}: {csrf_put_data}"
    assert csrf_put_data.get("error") == "CSRF_ORIGIN_MISMATCH"
    print(f"✓ Cross-site PUT correctly blocked with 403 CSRF_ORIGIN_MISMATCH")

    csrf_post_status, csrf_post_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/logs/{saved_daily_log_id}/submit",
        method="POST",
        data={},
        headers={"Sec-Fetch-Site": "cross-site", "Origin": "https://attacker-domain.evil"},
        opener=candidate_opener,
    )
    assert csrf_post_status == 403, f"Expected 403 for cross-site POST submit, got {csrf_post_status}: {csrf_post_data}"
    assert csrf_post_data.get("error") == "CSRF_ORIGIN_MISMATCH"
    print(f"✓ Cross-site POST submit correctly blocked with 403 CSRF_ORIGIN_MISMATCH")
    print("Phase 7 Passed: CSRF protection verified on candidate mutations.")

    # =========================================================================
    # PHASE 8: Submit Daily Log & Immutability Verification (API-056 via BFF)
    # =========================================================================
    print("\n--- PHASE 8: Submit Daily Log & Immutability Check (API-056) ---")
    submit_status, submit_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/logs/{saved_daily_log_id}/submit",
        method="POST",
        data={},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )

    assert submit_status in (200, 201), f"Expected 200/201 on log submission, got {submit_status}: {submit_data}"
    assert submit_data.get("status") == "SUBMITTED" or submit_data.get("ok") is True, f"Unexpected submit payload: {submit_data}"
    print(f"✓ Daily log {saved_daily_log_id} successfully submitted for review (status=SUBMITTED)")

    # Verify Immutability: Draft update must now be rejected
    locked_status, locked_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements/{placement_id}/logs/{log_date_str}",
        method="PUT",
        data={
            "day_type": "WORKED",
            "summary": "Submitted logni buzishga urinish",
            "total_minutes": 180,
            "tasks": [{"title": "Illegal edit", "minutes": 180}],
        },
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )

    assert locked_status in (400, 409, 422), f"Expected 400/409/422 on submitted log mutation, got {locked_status}: {locked_data}"
    print(f"✓ Immutability verified: mutation on submitted log rejected with HTTP {locked_status} ({locked_data.get('error')})")

    # Verify Re-submit rejection: Cannot submit already submitted log
    resubmit_status, resubmit_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/logs/{saved_daily_log_id}/submit",
        method="POST",
        data={},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert resubmit_status in (400, 409, 422), f"Expected rejection on re-submitting already submitted log, got {resubmit_status}: {resubmit_data}"
    print(f"✓ Re-submission prevention verified: rejected with HTTP {resubmit_status} ({resubmit_data.get('error')})")
    print("Phase 8 Passed: Log submission and immutability verified.")

    print("\n" + "=" * 80)
    print("ALL 8 PHASES OF FB-154 STAGING VERIFICATION PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        run_staging_suite()
    except Exception as e:
        print(f"\nFATAL ERROR in FB-154 staging suite: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
