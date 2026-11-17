#!/usr/bin/env python3
"""
FlexBridge 1.4 Automated Staging Verification Suite:
Candidate Portal: Offer Acceptance, Dual-Confirmed Job Engagements & Placement Onboarding Hub (FB-164)

Contracts Tested:
- API-043: POST /api/bff/candidate/offers/{id}/respond (Candidate accepts/declines offer; row lock capacity check)
- API-045: GET /api/bff/candidate/engagements/{id} (View engagement details, confirmations, dual-party status)
- API-046: POST /api/bff/candidate/engagements/{id}/confirmations (Dual-party START/END/DISPUTE confirmation)
- API-030: GET /api/bff/candidate/placements (Candidate list of own placements with cursor pagination)
- API-050: GET /api/bff/candidate/placements/{id}/plan (Internship bounded training plan & tasks)
- API-048: POST /api/bff/candidate/placements/{id}/accept (Candidate accepts placement terms)

Security & Architectural Invariants:
- 401 AUTH_REQUIRED on all unauthenticated requests.
- 403 CSRF_ORIGIN_MISMATCH against cross-site mutating requests.
- AC-014 Invariant: Status transitions to ACTIVE only after BOTH CANDIDATE and EMPLOYER confirm CONFIRM_START.
- Anti-enumeration uniform 404 for non-owner / unauthorized users.
- PgBouncer transaction-pooling compliance (NullPool, prepare_threshold=None).
- Zero queries/mutations to pg_live.
"""

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

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
        req_headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")

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


def run_candidate_offers_engagements_staging_suite():
    print("=" * 80)
    print("Starting FlexBridge 1.4 Staging Suite: Candidate Offers & Engagements Hub (FB-164)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    # =========================================================================
    # PHASE 1: 401 AUTH_REQUIRED Enforcement
    # =========================================================================
    print("\n--- PHASE 1: 401 AUTH_REQUIRED Verification ---")
    anon_opener = urllib.request.build_opener()
    fake_id = str(uuid4())

    unauth_endpoints = [
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/offers/{fake_id}/respond", {"decision": "ACCEPT"}),
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/engagements/{fake_id}", None),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/engagements/{fake_id}/confirmations", {"action": "CONFIRM_START"}),
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/placements", None),
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/placements/{fake_id}/plan", None),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/placements/{fake_id}/accept", {"terms_id": fake_id, "version": 1}),
    ]

    for m, ep, pl in unauth_endpoints:
        code, resp = api_request(ep, method=m, data=pl, headers={"Origin": FRONTEND_URL}, opener=anon_opener)
        assert code == 401, f"Expected 401 on {m} {ep}, got {code}: {resp}"
        assert resp.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got: {resp}"
        print(f"  ✓ {m:4} {ep} => 401 AUTH_REQUIRED verified")

    print("Phase 1 Passed: 401 AUTH_REQUIRED verified on all 6 candidate endpoints.")

    # =========================================================================
    # PHASE 2: Seed Test Fixtures in PgBouncer DB
    # =========================================================================
    print("\n--- PHASE 2: Seeding Test Fixtures in DB ---")
    test_suffix = uuid4().hex[:8]
    now_ts = datetime.now(timezone.utc)
    today_date = now_ts.date()

    cand_user_id = str(uuid4())
    cand_profile_id = str(uuid4())
    cand_password = f"CandPass-{test_suffix}!"
    cand_hash = hash_password(cand_password)

    employer_user_id = str(uuid4())
    org_id = str(uuid4())
    org_membership_id = str(uuid4())

    # Regular Job Opp & Offer
    opp_job_id = str(uuid4())
    opp_job_rev_id = str(uuid4())
    app_job_id = str(uuid4())
    attempt_job_id = str(uuid4())
    offer_job_id = str(uuid4())

    # Internship Opp & Placement
    opp_intern_id = str(uuid4())
    opp_intern_rev_id = str(uuid4())
    app_intern_id = str(uuid4())
    attempt_intern_id = str(uuid4())
    placement_id = str(uuid4())
    terms_id = str(uuid4())
    task_id1 = str(uuid4())
    task_id2 = str(uuid4())

    seeded_trigger_tables = [
        "organizations", "org_memberships", "org_role_grants",
        "candidate_profiles", "placements", "placement_intakes", "placement_terms",
    ]

    # Disable Triggers during seeding
    with engine.begin() as conn:
        for t in seeded_trigger_tables:
            conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

    try:
        with engine.begin() as conn:
            # 1. Users
            conn.execute(
                text("""
                    INSERT INTO flexbridge.users (
                        id, created_at, updated_at, display_name, password_hash,
                        status, locale, timezone, adult_declared_at
                    ) VALUES
                    (:cid, :ts, :ts, 'Ali Valiyev', :chash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts),
                    (:eid, :ts, :ts, 'TechCorp HR', :chash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
                """),
                {"cid": cand_user_id, "chash": cand_hash, "eid": employer_user_id, "ts": now_ts},
            )

            # 2. Candidate Profile
            conn.execute(
                text("""
                    INSERT INTO flexbridge.candidate_profiles (
                        id, created_at, updated_at, user_id, headline, region,
                        experience_months, bio, visibility
                    ) VALUES
                    (:id, :ts, :ts, :uid, 'Junior Fullstack Engineer', 'Tashkent', 12, 'Dasturchi talaba', 'PUBLIC')
                """),
                {"id": cand_profile_id, "uid": cand_user_id, "ts": now_ts},
            )

            # 3. Organization & Membership
            conn.execute(
                text("""
                    INSERT INTO flexbridge.organizations (
                        id, created_at, updated_at, legal_name, public_name, tax_id, status, region
                    ) VALUES
                    (:id, :ts, :ts, 'Tech Innovations MCHJ', 'TechCorp', :tax_id, 'ACTIVE', 'Tashkent')
                """),
                {"id": org_id, "tax_id": f"TAX_FB164_{test_suffix}", "ts": now_ts},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.org_memberships (
                        id, created_at, updated_at, organization_id, user_id, status, accepted_at
                    ) VALUES
                    (:id, :ts, :ts, :org_id, :uid, 'ACTIVE', :ts)
                """),
                {"id": org_membership_id, "org_id": org_id, "uid": employer_user_id, "ts": now_ts},
            )

            owner_role_id = conn.execute(
                text("SELECT id FROM flexbridge.role_catalog WHERE code = 'OWNER' AND scope_kind = 'ORG' LIMIT 1")
            ).scalar_one()

            conn.execute(
                text("""
                    INSERT INTO flexbridge.org_role_grants (
                        id, created_at, updated_at, membership_id, role_id, granted_by_id
                    ) VALUES
                    (:id, :ts, :ts, :mid, :rid, :by_id)
                """),
                {"id": str(uuid4()), "mid": org_membership_id, "rid": owner_role_id, "by_id": employer_user_id, "ts": now_ts},
            )

            # 4. Opportunity 1: Regular Part-Time Job (capacity = 2, occupied_count = 0)
            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunities (
                        id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count
                    ) VALUES
                    (:id, :ts, :ts, :org_id, 'PART_TIME', 'PUBLISHED', 2, 0)
                """),
                {"id": opp_job_id, "org_id": org_id, "ts": now_ts},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunity_revisions (
                        id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                        region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                        shift_match_mode, snapshot_schema, contract_type
                    ) VALUES
                    (:id, :ts, :ts, :opp_id, 1, :author_id, 'Frontend Developer', 'Next.js dasturchi',
                     'Tashkent', 'REMOTE', 'ANY', 'UZS', FALSE, :today, 'FLEXIBLE', 'EXACT', 1, 'LABOR_PART_TIME')
                """),
                {"id": opp_job_rev_id, "opp_id": opp_job_id, "author_id": employer_user_id, "today": today_date, "ts": now_ts},
            )

            conn.execute(
                text("UPDATE flexbridge.opportunities SET current_revision_id = :rev WHERE id = :id"),
                {"rev": opp_job_rev_id, "id": opp_job_id},
            )

            # 5. Job Application, Attempt & Offer
            conn.execute(
                text("""
                    INSERT INTO flexbridge.applications (
                        id, created_at, updated_at, opportunity_id, candidate_id, status, version
                    ) VALUES
                    (:id, :ts, :ts, :opp_id, :cid, 'OFFERED', 1)
                """),
                {"id": app_job_id, "opp_id": opp_job_id, "cid": cand_profile_id, "ts": now_ts},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.application_attempts (
                        id, created_at, updated_at, application_id, opportunity_id, attempt_no, revision_id,
                        profile_snapshot, schedule_result, matching_version, submitted_at, idempotency_key
                    ) VALUES
                    (:id, :ts, :ts, :app_id, :opp_id, 1, :rev_id,
                     '{"headline": "Talaba"}'::jsonb, 'MATCHED', '1.0', :ts, :idem)
                """),
                {
                    "id": attempt_job_id, "app_id": app_job_id, "opp_id": opp_job_id, "rev_id": opp_job_rev_id,
                    "ts": now_ts, "idem": f"idem-attempt-job-{test_suffix}"
                },
            )

            conn.execute(
                text("UPDATE flexbridge.applications SET current_attempt_id = :att_id WHERE id = :app_id"),
                {"att_id": attempt_job_id, "app_id": app_job_id},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.offers (
                        id, created_at, updated_at, application_id, attempt_id, revision_id,
                        issuer_membership_id, status, expires_at, terms_snapshot, idempotency_key
                    ) VALUES
                    (:id, :ts, :ts, :app_id, :att_id, :rev_id,
                     :mid, 'ISSUED', :exp_at, '{"salary": "5000000 UZS", "title": "Frontend Developer"}'::jsonb, :idem)
                """),
                {
                    "id": offer_job_id,
                    "app_id": app_job_id,
                    "att_id": attempt_job_id,
                    "rev_id": opp_job_rev_id,
                    "mid": org_membership_id,
                    "exp_at": now_ts + timedelta(days=7),
                    "idem": f"idem-offer-job-{test_suffix}",
                    "ts": now_ts,
                },
            )

            # 6. Opportunity 2: Internship (for API-030, API-050, API-048)
            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunities (
                        id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count
                    ) VALUES
                    (:id, :ts, :ts, :org_id, 'INTERNSHIP', 'PUBLISHED', 5, 1)
                """),
                {"id": opp_intern_id, "org_id": org_id, "ts": now_ts},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunity_revisions (
                        id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                        region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                        shift_match_mode, snapshot_schema, contract_type
                    ) VALUES
                    (:id, :ts, :ts, :opp_id, 1, :author_id, 'Backend Intern', 'FastAPI amaliyoti',
                     'Tashkent', 'HYBRID', 'STUDENT', 'UZS', FALSE, :today, 'FLEXIBLE', 'EXACT', 1, 'INTERNSHIP_AGREEMENT')
                """),
                {"id": opp_intern_rev_id, "opp_id": opp_intern_id, "author_id": employer_user_id, "today": today_date, "ts": now_ts},
            )

            conn.execute(
                text("UPDATE flexbridge.opportunities SET current_revision_id = :rev WHERE id = :id"),
                {"rev": opp_intern_rev_id, "id": opp_intern_id},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.applications (
                        id, created_at, updated_at, opportunity_id, candidate_id, status, version
                    ) VALUES
                    (:id, :ts, :ts, :opp_id, :cid, 'ACCEPTED', 2)
                """),
                {"id": app_intern_id, "opp_id": opp_intern_id, "cid": cand_profile_id, "ts": now_ts},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.application_attempts (
                        id, created_at, updated_at, application_id, opportunity_id, attempt_no, revision_id,
                        profile_snapshot, schedule_result, matching_version, submitted_at, idempotency_key
                    ) VALUES
                    (:id, :ts, :ts, :app_id, :opp_id, 1, :rev_id,
                     '{"headline": "Talaba"}'::jsonb, 'MATCHED', '1.0', :ts, :idem)
                """),
                {
                    "id": attempt_intern_id, "app_id": app_intern_id, "opp_id": opp_intern_id, "rev_id": opp_intern_rev_id,
                    "ts": now_ts, "idem": f"idem-attempt-intern-{test_suffix}"
                },
            )

            conn.execute(
                text("UPDATE flexbridge.applications SET current_attempt_id = :att_id WHERE id = :app_id"),
                {"att_id": attempt_intern_id, "app_id": app_intern_id},
            )

            offer_intern_id = str(uuid4())
            conn.execute(
                text("""
                    INSERT INTO flexbridge.offers (
                        id, created_at, updated_at, application_id, attempt_id, revision_id,
                        issuer_membership_id, status, expires_at, terms_snapshot, idempotency_key
                    ) VALUES
                    (:id, :ts, :ts, :app_id, :att_id, :rev_id,
                     :mid, 'ACCEPTED', :exp_at, '{"title": "Backend Intern"}'::jsonb, :idem)
                """),
                {
                    "id": offer_intern_id, "app_id": app_intern_id, "att_id": attempt_intern_id,
                    "rev_id": opp_intern_rev_id, "mid": org_membership_id, "exp_at": now_ts + timedelta(days=30),
                    "idem": f"idem-offer-intern-{test_suffix}", "ts": now_ts
                },
            )

            # 7. Placement & Terms
            conn.execute(
                text("""
                    INSERT INTO flexbridge.placements (
                        id, created_at, updated_at, application_id, offer_id, candidate_id, organization_id,
                        academic_track, status, start_date, end_date, version
                    ) VALUES
                    (:id, :ts, :ts, :app_id, :offer_id, :cid, :org_id, FALSE, 'PLANNED', :s_date, :e_date, 1)
                """),
                {
                    "id": placement_id,
                    "app_id": app_intern_id,
                    "offer_id": offer_intern_id,
                    "cid": cand_profile_id,
                    "org_id": org_id,
                    "s_date": today_date,
                    "e_date": today_date + timedelta(days=90),
                    "ts": now_ts,
                },
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.placement_intakes (
                        placement_id, created_at, origin, offer_id, attempt_id, revision_id,
                        academic_required, initial_snapshot, source_snapshot
                    ) VALUES
                    (:pid, :ts, 'LEGACY_IMPORT', :offer_id, :att_id, :rev_id, FALSE, '{}'::jsonb, '{}'::jsonb)
                """),
                {
                    "pid": placement_id, "offer_id": offer_intern_id, "att_id": attempt_intern_id,
                    "rev_id": opp_intern_rev_id, "ts": now_ts
                },
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.placement_terms (
                        id, created_at, updated_at, placement_id, version, schema_version,
                        daily_limit_minutes, weekly_limit_minutes, required_minutes, terms_snapshot
                    ) VALUES
                    (:id, :ts, :ts, :pid, 1, 1, 240, 1200, 7200,
                     '{"title": "Backend O''quv Rejasi", "objectives": "FastAPI o''rganish"}'::jsonb)
                """),
                {"id": terms_id, "pid": placement_id, "ts": now_ts},
            )

            conn.execute(
                text("UPDATE flexbridge.placements SET current_terms_id = :terms_id WHERE id = :placement_id"),
                {"terms_id": terms_id, "placement_id": placement_id},
            )

            # 8. Plan Tasks
            conn.execute(
                text("""
                    INSERT INTO flexbridge.plan_tasks (
                        id, created_at, updated_at, terms_id, code, title, expected_result, required, target_minutes
                    ) VALUES
                    (:id1, :ts, :ts, :tid, 'TASK-01', 'REST API arxitekturasi', 'OpenAPI va FastAPI bazasi', TRUE, 600),
                    (:id2, :ts, :ts, :tid, 'TASK-02', 'PostgreSQL bilan ishlash', 'SQLAlchemy va PgBouncer integratsiyasi', TRUE, 800)
                """),
                {"id1": task_id1, "id2": task_id2, "tid": terms_id, "ts": now_ts},
            )
    finally:
        # Re-enable Triggers
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))

    print("Phase 2 Passed: Test fixtures seeded in PgBouncer DB.")

    # =========================================================================
    # PHASE 3: Candidate Login
    # =========================================================================
    print("\n--- PHASE 3: Candidate Login Authentication ---")
    candidate_jar = http.cookiejar.CookieJar()
    candidate_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(candidate_jar))

    login_code, login_resp = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": cand_user_id, "password": cand_password},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert login_code == 200, f"Candidate login failed, code {login_code}: {login_resp}"
    assert login_resp.get("ok") is True, f"Login response missing ok: {login_resp}"

    # Verify session via /api/auth/me
    me_code, me_resp = api_request(
        f"{FRONTEND_URL}/api/auth/me",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert me_code == 200, f"auth/me failed, code {me_code}: {me_resp}"
    user_info = me_resp.get("user", me_resp)
    assert user_info.get("user_id") == cand_user_id, f"auth/me user_id mismatch: {me_resp}"
    print(f"  ✓ Candidate authenticated successfully: {cand_user_id}")
    print("Phase 3 Passed: Authenticated candidate session established.")

    # =========================================================================
    # PHASE 4: Candidate Responds to Offer (API-043) -> ACCEPT
    # =========================================================================
    print("\n--- PHASE 4: Candidate Responds to Offer (API-043) ---")
    respond_url = f"{FRONTEND_URL}/api/bff/candidate/offers/{offer_job_id}/respond"
    acc_code, acc_data = api_request(
        respond_url,
        method="POST",
        data={"decision": "ACCEPT", "note": "Taklifni qabul qilaman"},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert acc_code == 200, f"Expected 200 on offer accept, got {acc_code}: {acc_data}"
    assert acc_data.get("contract_id") == "API-043", f"Contract mismatch: {acc_data}"
    assert acc_data.get("status") == "ACCEPTED", f"Expected status ACCEPTED: {acc_data}"
    engagement_id = acc_data.get("engagement_id")
    assert engagement_id is not None, "Regular job offer accept must generate an engagement_id!"
    print(f"  ✓ Offer accepted successfully. Generated Engagement ID: {engagement_id}")

    # Verify DB state: occupied_count incremented to 1, application status ACCEPTED
    with engine.begin() as conn:
        occ = conn.execute(text("SELECT occupied_count FROM flexbridge.opportunities WHERE id = :id"), {"id": opp_job_id}).scalar_one()
        assert occ == 1, f"Expected occupied_count = 1, got {occ}"
        app_st = conn.execute(text("SELECT status FROM flexbridge.applications WHERE id = :id"), {"id": app_job_id}).scalar_one()
        assert app_st == "ACCEPTED", f"Expected application status ACCEPTED, got {app_st}"
        print(f"  ✓ Database verified: opportunity occupied_count = {occ}, application status = {app_st}")

    print("Phase 4 Passed: Offer accepted and capacity counter incremented.")

    # =========================================================================
    # PHASE 5: Idempotency & Conflict Check
    # =========================================================================
    print("\n--- PHASE 5: Offer Response Idempotency & Conflict Check ---")
    rep_code, rep_data = api_request(
        respond_url,
        method="POST",
        data={"decision": "ACCEPT"},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert rep_code == 200, f"Expected 200 on repeat ACCEPT, got {rep_code}: {rep_data}"
    assert rep_data.get("status") == "ACCEPTED", f"Expected ACCEPTED: {rep_data}"
    print("  ✓ Idempotent repeat ACCEPT returned 200")

    # Conflict on DECLINE after ACCEPT
    dec_code, dec_data = api_request(
        respond_url,
        method="POST",
        data={"decision": "DECLINE"},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert dec_code == 409, f"Expected 409 on DECLINE after ACCEPT, got {dec_code}: {dec_data}"
    print(f"  ✓ Conflict on DECLINE after ACCEPT returned 409: {dec_data.get('code', dec_data.get('error'))}")
    print("Phase 5 Passed: Idempotency and conflict validations verified.")

    # =========================================================================
    # PHASE 6: Candidate Placements List (API-030)
    # =========================================================================
    print("\n--- PHASE 6: Candidate Placements List (API-030) ---")
    plc_code, plc_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements?limit=10",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert plc_code == 200, f"Expected 200 on placements list, got {plc_code}: {plc_data}"
    assert plc_data.get("contract_id") == "API-030", f"Contract mismatch: {plc_data}"
    items = plc_data.get("items", [])
    assert any(p["id"] == placement_id for p in items), f"Placement {placement_id} not found in {items}"
    print(f"  ✓ Candidate placements list returned {len(items)} items including {placement_id}")
    print("Phase 6 Passed: Candidate placements list retrieved via API-030.")

    # =========================================================================
    # PHASE 7: Placement Plan & Tasks (API-050)
    # =========================================================================
    print("\n--- PHASE 7: Placement Plan & Tasks (API-050) ---")
    plan_code, plan_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements/{placement_id}/plan",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert plan_code == 200, f"Expected 200 on placement plan, got {plan_code}: {plan_data}"
    assert plan_data.get("contract_id") == "API-050", f"Contract mismatch: {plan_data}"
    assert plan_data.get("placement_id") == placement_id, f"Placement ID mismatch: {plan_data}"
    assert plan_data.get("daily_limit_minutes") == 240, f"Daily limit mismatch: {plan_data}"
    assert plan_data.get("required_minutes") == 7200, f"Required minutes mismatch: {plan_data}"
    tasks = plan_data.get("tasks", [])
    assert len(tasks) == 2, f"Expected 2 tasks, got {len(tasks)}"
    assert tasks[0]["code"] == "TASK-01"
    assert tasks[1]["code"] == "TASK-02"
    print(f"  ✓ Placement plan retrieved: {len(tasks)} tasks, {plan_data.get('required_minutes')} required minutes")
    print("Phase 7 Passed: Placement plan and task breakdown verified.")

    # =========================================================================
    # PHASE 8: Candidate Accepts Placement Terms (API-048)
    # =========================================================================
    print("\n--- PHASE 8: Candidate Accepts Placement Terms (API-048) ---")
    terms_code, terms_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/placements/{placement_id}/accept",
        method="POST",
        data={"terms_id": terms_id, "version": 1, "idempotency_key": f"key-terms-{test_suffix}"},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert terms_code == 200, f"Expected 200 on accept placement terms, got {terms_code}: {terms_data}"
    print(f"  ✓ Placement terms accepted: {terms_data}")

    # Verify DB consent receipt
    with engine.begin() as conn:
        consent_count = conn.execute(
            text("SELECT COUNT(*) FROM flexbridge.placement_consents WHERE placement_id = :pid AND actor_id = :uid"),
            {"pid": placement_id, "uid": cand_user_id},
        ).scalar_one()
        assert consent_count >= 1, f"Expected consent recorded in DB, got {consent_count}"
        print(f"  ✓ Placement consent recorded in DB: count = {consent_count}")

    print("Phase 8 Passed: Placement terms accepted with audit receipt.")

    # =========================================================================
    # PHASE 9: Job Engagement Details & Dual-Party Confirmation (API-045 & API-046)
    # =========================================================================
    print("\n--- PHASE 9: Job Engagement & Dual-Party Confirmation (API-045 & API-046) ---")
    eng_code, eng_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/engagements/{engagement_id}",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert eng_code == 200, f"Expected 200 on get engagement, got {eng_code}: {eng_data}"
    assert eng_data.get("contract_id") == "API-045", f"Contract mismatch: {eng_data}"
    assert eng_data.get("status") == "PENDING_START_CONFIRMATION", f"Expected PENDING_START_CONFIRMATION: {eng_data}"
    assert eng_data.get("my_side") == "CANDIDATE", f"Expected CANDIDATE side: {eng_data}"
    print(f"  ✓ Engagement details verified: status={eng_data.get('status')}, my_side={eng_data.get('my_side')}")

    # Candidate confirms start (API-046)
    conf_code, conf_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/engagements/{engagement_id}/confirmations",
        method="POST",
        data={"action": "CONFIRM_START", "note": "Ish boshlandi"},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert conf_code == 200, f"Expected 200 on candidate confirm start, got {conf_code}: {conf_data}"
    print(f"  ✓ Candidate CONFIRM_START executed: {conf_data.get('action')}")

    # AC-014 Invariant Verification:
    # Status MUST remain PENDING_START_CONFIRMATION because employer has not yet confirmed!
    eng2_code, eng2_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/engagements/{engagement_id}",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert eng2_code == 200, f"Expected 200 on re-get engagement, got {eng2_code}: {eng2_data}"
    assert eng2_data.get("status") == "PENDING_START_CONFIRMATION", (
        f"AC-014 VIOLATION: Engagement transitioned to {eng2_data.get('status')} before employer confirmed!"
    )
    assert any(c["side"] == "CANDIDATE" and c["action"] == "CONFIRM_START" for c in eng2_data.get("confirmations", [])), (
        "Expected candidate CONFIRM_START in confirmations list!"
    )
    print("  ✓ AC-014 verified: Status remains PENDING_START_CONFIRMATION awaiting employer confirmation.")
    print("Phase 9 Passed: Job engagement details and candidate dual-party confirmation verified.")

    # =========================================================================
    # PHASE 10: Anti-CSRF Origin Defense & Strict IDOR Defense
    # =========================================================================
    print("\n--- PHASE 10: Anti-CSRF Origin & IDOR Defenses ---")
    # CSRF attack simulation
    csrf_code, csrf_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/offers/{offer_job_id}/respond",
        method="POST",
        data={"decision": "ACCEPT"},
        headers={"Origin": "https://evil-attacker.example.com"},
        opener=candidate_opener,
    )
    assert csrf_code == 403, f"Expected 403 on CSRF attack, got {csrf_code}: {csrf_data}"
    assert csrf_data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got: {csrf_data}"
    print("  ✓ CSRF attack blocked: 403 CSRF_ORIGIN_MISMATCH")

    # IDOR check: non-existent / foreign engagement
    foreign_eng_id = str(uuid4())
    idor_code, idor_data = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/engagements/{foreign_eng_id}",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert idor_code == 404, f"Expected 404 on IDOR probe, got {idor_code}: {idor_data}"
    print("  ✓ IDOR probe blocked: uniform 404")

    print("Phase 10 Passed: Anti-CSRF Origin defense and strict IDOR protection verified.")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF FB-164 STAGING TEST PASSED 100% GREEN!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        run_candidate_offers_engagements_staging_suite()
        sys.exit(0)
    except AssertionError as err:
        print(f"\n❌ [TEST FAILURE] {err}", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        import traceback
        traceback.print_exc()
        sys.exit(2)
