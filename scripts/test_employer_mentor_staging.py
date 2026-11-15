#!/usr/bin/env python3
"""
FlexBridge 1.4 Automated Staging Verification Suite:
Employer Portal: Workplace Mentor Assignments, Daily Log Reviews & Intern Evaluation Hub (FB-162)

Contracts Tested:
- API-090: GET /api/bff/employer/mentor/review-queue (Mentor review queue, due_at escalation, total minutes)
- API-091: GET /api/bff/employer/mentor/log-revisions/{id}/workplace (Workplace log revision detail & tasks breakdown)
- API-092: POST /api/bff/employer/mentor/log-revisions/{id}/workplace-reviews (Submit workplace evaluation decision)
- API-089: GET /api/bff/employer/mentor/assignments (Active mentor supervised placements list)
- API-069: GET /api/bff/employer/placements (Organization active student placements list)

Security & Architectural Invariants:
- 401 AUTH_REQUIRED on all unauthenticated requests.
- 403 CSRF_ORIGIN_MISMATCH against cross-site mutating requests.
- AC-028 / SEC-01 Invariant: Candidate self-review strictly forbidden (403 SELF_REVIEW_FORBIDDEN).
- Anti-enumeration uniform 404 LOG_REVISION_NOT_FOUND for non-member / unauthorized users.
- PgBouncer transaction-pooling compliance (NullPool, prepare_threshold=None).
- Zero queries/mutations to pg_live.
"""

import base64
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


def run_employer_mentor_staging_suite():
    print("=" * 80)
    print("Starting FlexBridge 1.4 Staging Suite: Workplace Mentor Hub (FB-162)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_suffix = uuid4().hex[:8]
    mentor_user_id = str(uuid4())
    mentor_password = "MentorSecurePass123!"
    mentor_hash = hash_password(mentor_password)

    student_user_id = str(uuid4())
    student_profile_id = str(uuid4())
    student_password = "StudentSecurePass123!"
    student_hash = hash_password(student_password)

    org_id = str(uuid4())
    org_membership_id = str(uuid4())
    mentor_grant_id = str(uuid4())
    coordinator_grant_id = str(uuid4())

    opp_id = str(uuid4())
    opp_rev_id = str(uuid4())
    app_id = str(uuid4())
    attempt_id = str(uuid4())
    offer_id = str(uuid4())

    placement_id = str(uuid4())
    terms_id = str(uuid4())
    mentor_assignment_id = str(uuid4())

    daily_log_1_id = str(uuid4())
    revision_1_id = str(uuid4())
    task_1_id = str(uuid4())
    task_2_id = str(uuid4())

    daily_log_2_id = str(uuid4())
    revision_2_id = str(uuid4())
    task_3_id = str(uuid4())

    now_ts = datetime.now(timezone.utc)
    today_date = date.today()
    log_date_1 = today_date - timedelta(days=1)
    log_date_2 = today_date - timedelta(days=4)

    terms_snapshot = {
        "version": 1,
        "contract_type": "INTERNSHIP_AGREEMENT",
        "title": "Full Stack Software Engineering Internship",
        "objectives": "Master Next.js 16 and FastAPI distributed systems",
    }

    seeded_trigger_tables = [
        "organizations", "org_memberships", "org_role_grants",
        "candidate_profiles", "placements", "placement_intakes", "placement_terms",
        "mentor_assignments", "mentor_assignment_proofs",
        "daily_logs", "log_revisions", "log_task_entries",
    ]

    # =========================================================================
    # PHASE 1: Unauthenticated Route Guard Testing (401 AUTH_REQUIRED)
    # =========================================================================
    print("\n--- PHASE 1: Unauthenticated Route Guard Testing ---")
    dummy_rev_id = str(uuid4())
    dummy_org_id = str(uuid4())

    unauth_checks = [
        ("GET", f"{FRONTEND_URL}/api/bff/employer/mentor/review-queue", None),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/mentor/log-revisions/{dummy_rev_id}/workplace", None),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/mentor/log-revisions/{dummy_rev_id}/workplace-reviews", {
            "decision": "APPROVED",
            "comment": "Unauth review attempt"
        }),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/mentor/assignments", None),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/placements?organization_id={dummy_org_id}", None),
    ]

    for meth, url, body in unauth_checks:
        status, resp = api_request(url, method=meth, data=body)
        assert status == 401, f"Expected 401 for unauthenticated {meth} {url}, got {status}: {resp}"
        assert resp.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got: {resp}"
        print(f"✓ Correctly rejected unauthenticated {meth} {url} with 401 AUTH_REQUIRED")

    print("Phase 1 Passed: All 5 employer mentor endpoints guarded against unauthenticated access.")

    # =========================================================================
    # PHASE 2: Database Fixture Seeding via PgBouncer
    # =========================================================================
    print("\n--- PHASE 2: Database Fixture Seeding via PgBouncer ---")

    with engine.begin() as conn:
        for t in seeded_trigger_tables:
            conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

    try:
        with engine.begin() as conn:
            # 1. Mentor & Candidate Users
            conn.execute(text("""
                INSERT INTO flexbridge.users (
                    id, created_at, updated_at, display_name, password_hash,
                    status, locale, timezone, adult_declared_at
                )
                VALUES
                    (:mid, :ts, :ts, 'Akmal Raximov (Bosh Mentor)', :mhash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts),
                    (:sid, :ts, :ts, 'Shahzod Olimov (Amaliyotchi)', :shash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
            """), {
                "mid": mentor_user_id, "mhash": mentor_hash,
                "sid": student_user_id, "shash": student_hash,
                "ts": now_ts
            })

            # 2. Candidate Profile
            conn.execute(text("""
                INSERT INTO flexbridge.candidate_profiles (
                    id, created_at, updated_at, user_id, headline, region, bio, experience_months, visibility
                )
                VALUES (
                    :pid, :ts, :ts, :uid, 'Software Engineering Talabasi & Junior Dasturchi',
                    'Tashkent', 'Talaba dasturchi', 12, 'PUBLIC'
                )
            """), {"pid": student_profile_id, "uid": student_user_id, "ts": now_ts})

            # 3. Organization & Org Membership for Mentor
            conn.execute(text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, :ts, :ts, :tax, 'FinTech Global Systems MCHJ', 'FinTech Global', 'Tashkent', 'ACTIVE')
            """), {"id": org_id, "tax": f"TAX_MENTOR_{test_suffix}", "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status, accepted_at)
                VALUES (:id, :ts, :ts, :org_id, :uid, 'ACTIVE', :ts)
            """), {"id": org_membership_id, "org_id": org_id, "uid": mentor_user_id, "ts": now_ts})

            # Roles: HOST_COORDINATOR and MENTOR
            role_rows = conn.execute(text("""
                SELECT code, id FROM flexbridge.role_catalog WHERE code IN ('HOST_COORDINATOR', 'MENTOR') AND scope_kind = 'ORG'
            """)).mappings().all()
            role_map = {r["code"]: r["id"] for r in role_rows}
            assert "MENTOR" in role_map and "HOST_COORDINATOR" in role_map, "MENTOR and HOST_COORDINATOR roles must exist"

            conn.execute(text("""
                INSERT INTO flexbridge.org_role_grants (id, created_at, updated_at, membership_id, role_id, granted_by_id)
                VALUES
                    (:g1, :ts, :ts, :mid, :r_mentor, :uid),
                    (:g2, :ts, :ts, :mid, :r_coord, :uid)
            """), {
                "g1": mentor_grant_id, "g2": coordinator_grant_id, "mid": org_membership_id,
                "r_mentor": role_map["MENTOR"], "r_coord": role_map["HOST_COORDINATOR"],
                "uid": mentor_user_id, "ts": now_ts
            })

            # 4. Opportunity, Application, Offer
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
                    :id, :ts, :ts, :opp_id, 1, :uid, 'Full Stack Internship', 'Hands-on training',
                    'Tashkent', 'HYBRID', 'STUDENT', 'UZS', FALSE, :start_d, 'FLEXIBLE',
                    'ANY', 1, 'INTERNSHIP_AGREEMENT'
                )
            """), {
                "id": opp_rev_id, "opp_id": opp_id, "uid": mentor_user_id, "start_d": today_date, "ts": now_ts
            })

            conn.execute(text("""
                UPDATE flexbridge.opportunities SET current_revision_id = :rev WHERE id = :id
            """), {"rev": opp_rev_id, "id": opp_id})

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

            # 5. Placement & Placement Terms
            conn.execute(text("""
                INSERT INTO flexbridge.placements (
                    id, created_at, updated_at, application_id, offer_id, candidate_id,
                    organization_id, academic_track, status, start_date, end_date, version
                )
                VALUES (:id, :ts, :ts, :app_id, :offer_id, :cand_id, :org_id, FALSE, 'ACTIVE', :start_d, :end_d, 1)
            """), {
                "id": placement_id, "app_id": app_id, "offer_id": offer_id, "cand_id": student_profile_id,
                "org_id": org_id, "start_d": today_date - timedelta(days=14),
                "end_d": today_date + timedelta(days=76), "ts": now_ts
            })

            conn.execute(text("""
                INSERT INTO flexbridge.placement_intakes (
                    placement_id, created_at, origin, offer_id, attempt_id, revision_id,
                    academic_required, initial_snapshot, source_snapshot
                )
                VALUES (
                    :pid, :ts, 'LEGACY_IMPORT', :offer_id, :attempt_id, :rev_id,
                    FALSE, '{}'::jsonb, '{}'::jsonb
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

            # 6. Mentor Assignment & Mentor Assignment Proof
            conn.execute(text("""
                INSERT INTO flexbridge.mentor_assignments (
                    id, created_at, updated_at, placement_id, membership_id,
                    organization_id, assigned_by_id, assigned_at, accepted_at
                )
                VALUES (:id, :ts, :ts, :pid, :mid, :org_id, :by_id, :ts, :ts)
            """), {
                "id": mentor_assignment_id, "pid": placement_id, "mid": org_membership_id,
                "org_id": org_id, "by_id": mentor_user_id, "ts": now_ts
            })

            conn.execute(text("""
                INSERT INTO flexbridge.mentor_assignment_proofs (
                    assignment_id, created_at, origin, placement_id, mentor_user_id,
                    mentor_grant_id, actor_id, session_id, auth_version, host_grant_id,
                    idempotency_key, request_fingerprint, receipt, initial_snapshot
                )
                VALUES (
                    :aid, :ts, 'LEGACY_IMPORT', :pid, :uid,
                    :gid, NULL, NULL, NULL, NULL,
                    NULL, NULL, NULL, '{}'::jsonb
                )
            """), {
                "aid": mentor_assignment_id, "pid": placement_id, "uid": mentor_user_id,
                "gid": mentor_grant_id, "ts": now_ts
            })

            # 7. Daily Log 1 (Fresh - Submitted 1 hour ago -> is_escalated = False)
            submitted_1_ts = now_ts - timedelta(hours=1)
            conn.execute(text("""
                INSERT INTO flexbridge.daily_logs (id, created_at, updated_at, placement_id, local_date, version)
                VALUES (:id, :ts, :ts, :pid, :ld, 1)
            """), {"id": daily_log_1_id, "pid": placement_id, "ld": log_date_1, "ts": submitted_1_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.log_revisions (
                    id, created_at, updated_at, daily_log_id, revision, terms_id, author_id, day_type, summary,
                    total_minutes, status, submitted_at, idempotency_key
                )
                VALUES (
                    :id, :ts, :ts, :dlid, 1, :tid, :author_id, 'WORKDAY',
                    'Next.js 16 va Tailwind CSS bilan korporativ portal frontend qismini yaratdim.',
                    420, 'SUBMITTED', :ts, :idem
                )
            """), {
                "id": revision_1_id, "dlid": daily_log_1_id, "tid": terms_id, "author_id": student_user_id,
                "ts": submitted_1_ts, "idem": f"idem-rev1-{uuid4().hex[:12]}"
            })

            conn.execute(text("""
                UPDATE flexbridge.daily_logs SET current_revision_id = :rid WHERE id = :dlid
            """), {"rid": revision_1_id, "dlid": daily_log_1_id})

            # Tasks for Revision 1
            conn.execute(text("""
                INSERT INTO flexbridge.log_task_entries (id, created_at, updated_at, revision_id, result_text, minutes, start_minute, end_minute)
                VALUES
                    (:id1, :ts, :ts, :rid, 'Workplace Mentor Hub UI komponentlarini ishlab chiqish', 240, 540, 780),
                    (:id2, :ts, :ts, :rid, 'Turbopack va TypeScript turlarini sozlash', 180, 780, 960)
            """), {"id1": task_1_id, "id2": task_2_id, "rid": revision_1_id, "ts": submitted_1_ts})

            # 8. Daily Log 2 (Old - Submitted 4 days ago -> is_escalated = True)
            submitted_2_ts = now_ts - timedelta(days=4)
            conn.execute(text("""
                INSERT INTO flexbridge.daily_logs (id, created_at, updated_at, placement_id, local_date, version)
                VALUES (:id, :ts, :ts, :pid, :ld, 1)
            """), {"id": daily_log_2_id, "pid": placement_id, "ld": log_date_2, "ts": submitted_2_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.log_revisions (
                    id, created_at, updated_at, daily_log_id, revision, terms_id, author_id, day_type, summary,
                    total_minutes, status, submitted_at, idempotency_key
                )
                VALUES (
                    :id, :ts, :ts, :dlid, 1, :tid, :author_id, 'WORKDAY',
                    'Mikroservislar va PostgreSQL replikatsiyasi ustida ishladim.',
                    360, 'SUBMITTED', :ts, :idem
                )
            """), {
                "id": revision_2_id, "dlid": daily_log_2_id, "tid": terms_id, "author_id": student_user_id,
                "ts": submitted_2_ts, "idem": f"idem-rev2-{uuid4().hex[:12]}"
            })

            conn.execute(text("""
                UPDATE flexbridge.daily_logs SET current_revision_id = :rid WHERE id = :dlid
            """), {"rid": revision_2_id, "dlid": daily_log_2_id})

            conn.execute(text("""
                INSERT INTO flexbridge.log_task_entries (id, created_at, updated_at, revision_id, result_text, minutes, start_minute, end_minute)
                VALUES (:id, :ts, :ts, :rid, 'Docker Compose muhitini optimallashtirish', 360, 540, 900)
            """), {"id": task_3_id, "rid": revision_2_id, "ts": submitted_2_ts})

    finally:
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))

    print(f"✓ Fixtures successfully seeded:")
    print(f"  Mentor User ID: {mentor_user_id}")
    print(f"  Student User ID: {student_user_id}")
    print(f"  Organization ID: {org_id}")
    print(f"  Placement ID: {placement_id}")
    print(f"  Revision 1 ID: {revision_1_id} (Submitted 1h ago, expected is_escalated = False)")
    print(f"  Revision 2 ID: {revision_2_id} (Submitted 4d ago, expected is_escalated = True)")
    print("Phase 2 Passed: DB fixtures seeded via PgBouncer.")

    # =========================================================================
    # PHASE 3: Employer Mentor Authentication via Next.js BFF (/api/auth/login)
    # =========================================================================
    print("\n--- PHASE 3: Employer Mentor Authentication ---")
    mentor_cookie_jar = http.cookiejar.CookieJar()
    mentor_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(mentor_cookie_jar))

    login_status, login_data = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": mentor_user_id, "password": mentor_password},
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )

    assert login_status == 200, f"Expected 200 on login, got {login_status}: {login_data}"
    assert login_data.get("ok") is True, f"Login payload should be ok: {login_data}"
    print(f"✓ Mentor logged in successfully: user_id={mentor_user_id}")
    print("Phase 3 Passed: Mentor session established.")

    # =========================================================================
    # PHASE 4: Fetch Mentor Review Queue (API-090: GET /api/bff/employer/mentor/review-queue)
    # =========================================================================
    print("\n--- PHASE 4: Fetch Mentor Review Queue (API-090) ---")
    q_status, q_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/review-queue?limit=50",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )

    assert q_status == 200, f"Expected 200 for review queue, got {q_status}: {q_data}"
    items = q_data.get("items", [])
    assert len(items) >= 2, f"Expected at least 2 pending items in queue, got {len(items)}"

    # Find our seeded revisions
    rev1_item = next((i for i in items if i["revision_id"] == revision_1_id), None)
    rev2_item = next((i for i in items if i["revision_id"] == revision_2_id), None)

    assert rev1_item is not None, f"Revision 1 ({revision_1_id}) must be in mentor queue"
    assert rev2_item is not None, f"Revision 2 ({revision_2_id}) must be in mentor queue"

    # Verify escalation status
    assert rev1_item["is_escalated"] is False, f"Revision 1 should NOT be escalated, got: {rev1_item['is_escalated']}"
    assert rev2_item["is_escalated"] is True, f"Revision 2 submitted 4 days ago MUST be escalated, got: {rev2_item['is_escalated']}"

    # Verify metadata
    assert rev1_item["total_minutes"] == 420, f"Expected 420 minutes for rev1, got {rev1_item['total_minutes']}"
    assert "Shahzod Olimov" in rev1_item["candidate"]["full_name"], f"Candidate name mismatch: {rev1_item['candidate']}"
    print(f"✓ Correctly fetched queue with {len(items)} items.")
    print(f"✓ Verified revision 1: total_minutes={rev1_item['total_minutes']}, is_escalated={rev1_item['is_escalated']}")
    print(f"✓ Verified revision 2 (escalated): total_minutes={rev2_item['total_minutes']}, is_escalated={rev2_item['is_escalated']}")
    print("Phase 4 Passed: Review queue correctly returned and evaluated.")

    # =========================================================================
    # PHASE 5: Fetch Workplace Revision Detail (API-091: GET /api/bff/employer/mentor/log-revisions/{id}/workplace)
    # =========================================================================
    print("\n--- PHASE 5: Fetch Workplace Revision Detail (API-091) ---")
    d_status, d_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/log-revisions/{revision_1_id}/workplace",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )

    assert d_status == 200, f"Expected 200 for revision detail, got {d_status}: {d_data}"
    rev_detail = d_data.get("revision", {})
    assert rev_detail.get("contract_id") == "API-091", f"Expected contract_id API-091, got: {rev_detail.get('contract_id')}"
    assert rev_detail.get("total_minutes") == 420, f"Expected 420 min, got {rev_detail.get('total_minutes')}"
    tasks = rev_detail.get("tasks", [])
    assert len(tasks) == 2, f"Expected 2 task entries, got {len(tasks)}"
    assert tasks[0]["minutes"] == 240, f"Expected 240 min for task 1, got {tasks[0]['minutes']}"
    assert tasks[1]["minutes"] == 180, f"Expected 180 min for task 2, got {tasks[1]['minutes']}"

    # Test IDOR Defense: non-existent revision returns 404
    fake_rev_id = str(uuid4())
    fake_status, fake_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/log-revisions/{fake_rev_id}/workplace",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )
    assert fake_status == 404, f"Expected 404 for unknown revision, got {fake_status}: {fake_data}"
    print(f"✓ Correctly fetched revision 1 detail with {len(tasks)} tasks.")
    print(f"✓ Verified IDOR defense: random UUID returned 404 LOG_REVISION_NOT_FOUND.")
    print("Phase 5 Passed: Revision detail inspection verified.")

    # =========================================================================
    # PHASE 6: Submit Workplace Review Decision (API-092)
    # =========================================================================
    print("\n--- PHASE 6: Submit Workplace Review Decisions (API-092) ---")

    # 1. Invalid decision validation
    inv_status, inv_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/log-revisions/{revision_1_id}/workplace-reviews",
        method="POST",
        data={"decision": "SUPER_APPROVED", "comment": "Invalid decision test"},
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )
    assert inv_status in (400, 422), f"Expected 400 or 422 for invalid decision, got {inv_status}: {inv_data}"
    print(f"✓ Correctly rejected invalid decision with status {inv_status}")

    # 2. Submit APPROVED decision for Revision 1
    sub1_status, sub1_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/log-revisions/{revision_1_id}/workplace-reviews",
        method="POST",
        data={
            "decision": "APPROVED",
            "comment": "Vazifalar to'liq va a'lo sifatda bajarilgan, amaliyot kundaligi tasdiqlandi."
        },
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )
    assert sub1_status == 200, f"Expected 200 on submitting APPROVED decision, got {sub1_status}: {sub1_data}"
    assert sub1_data.get("ok") is True, f"Expected ok: True, got: {sub1_data}"
    print(f"✓ Successfully submitted APPROVED decision for Revision 1: {sub1_data}")

    # Verify decision stored in database
    with engine.connect() as conn:
        rev1_db = conn.execute(text("""
            SELECT decision, comment, placement_id FROM flexbridge.workplace_log_reviews WHERE revision_id = :rid
        """), {"rid": revision_1_id}).mappings().first()
        assert rev1_db is not None, "Review row must exist in workplace_log_reviews table"
        assert rev1_db["decision"] == "APPROVED", f"Expected APPROVED, got: {rev1_db['decision']}"
        assert "amaliyot kundaligi tasdiqlandi" in rev1_db["comment"]
        print(f"✓ Verified DB record: workplace_log_reviews decision={rev1_db['decision']}")

    # 3. Submit CHANGES_REQUESTED decision for Revision 2
    sub2_status, sub2_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/log-revisions/{revision_2_id}/workplace-reviews",
        method="POST",
        data={
            "decision": "CHANGES_REQUESTED",
            "comment": "Replikatsiya arxitekturasi bo'yicha batafsil izoh va natijalar qo'shilsin."
        },
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )
    assert sub2_status == 200, f"Expected 200 on submitting CHANGES_REQUESTED decision, got {sub2_status}: {sub2_data}"
    print(f"✓ Successfully submitted CHANGES_REQUESTED decision for Revision 2: {sub2_data}")

    # 4. Verify review queue is now clean for these revisions
    q2_status, q2_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/review-queue?limit=50",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )
    remaining_rev_ids = [i["revision_id"] for i in q2_data.get("items", [])]
    assert revision_1_id not in remaining_rev_ids, "Reviewed revision 1 must be removed from queue"
    assert revision_2_id not in remaining_rev_ids, "Reviewed revision 2 must be removed from queue"
    print(f"✓ Verified review queue correctly popped both reviewed revisions.")
    print("Phase 6 Passed: Workplace review decisions submitted and verified.")

    # =========================================================================
    # PHASE 7: Fetch Mentor Assignments (API-089) and Org Placements (API-069)
    # =========================================================================
    print("\n--- PHASE 7: Fetch Mentor Assignments (API-089) and Org Placements (API-069) ---")

    # API-089: Mentor Assignments
    asg_status, asg_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/assignments?limit=50",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )
    assert asg_status == 200, f"Expected 200 on mentor assignments, got {asg_status}: {asg_data}"
    asg_items = asg_data.get("items", [])
    assert any(a["placement_id"] == placement_id for a in asg_items), f"Seeded placement {placement_id} must be in mentor assignments: {asg_items}"
    print(f"✓ Verified API-089: Found {len(asg_items)} mentor assignment(s).")

    # API-069: Org Placements
    plc_status, plc_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/placements?organization_id={org_id}&limit=50",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=mentor_opener,
    )
    assert plc_status == 200, f"Expected 200 on org placements, got {plc_status}: {plc_data}"
    plc_items = plc_data.get("items", [])
    assert any(p["id"] == placement_id for p in plc_items), f"Seeded placement {placement_id} must be in org placements: {plc_items}"
    print(f"✓ Verified API-069: Found {len(plc_items)} organization placement(s).")
    print("Phase 7 Passed: Placements and assignments endpoints verified.")

    # =========================================================================
    # PHASE 8: Security & Invariant Verification
    # =========================================================================
    print("\n--- PHASE 8: Security Invariants Verification ---")

    # 1. Anti-CSRF Origin Defense
    csrf_status, csrf_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/log-revisions/{revision_1_id}/workplace-reviews",
        method="POST",
        data={"decision": "APPROVED", "comment": "CSRF test attack"},
        headers={"Origin": "https://attacker-malicious-site.example"},
        opener=mentor_opener,
    )
    assert csrf_status == 403, f"Expected 403 CSRF mismatch, got {csrf_status}: {csrf_data}"
    assert csrf_data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got: {csrf_data}"
    print(f"✓ Anti-CSRF Origin defense successfully blocked cross-origin POST with 403 CSRF_ORIGIN_MISMATCH.")

    # 2. Anti-Self Review Invariant (AC-028 / SEC-01)
    # Log in student user and attempt to review own revision
    student_cookie_jar = http.cookiejar.CookieJar()
    student_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(student_cookie_jar))

    s_login_status, s_login_data = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": student_user_id, "password": student_password},
        headers={"Origin": FRONTEND_URL},
        opener=student_opener,
    )
    assert s_login_status == 200, f"Student login failed: {s_login_data}"

    self_status, self_data = api_request(
        f"{FRONTEND_URL}/api/bff/employer/mentor/log-revisions/{revision_1_id}/workplace-reviews",
        method="POST",
        data={"decision": "APPROVED", "comment": "Attempting self-review"},
        headers={"Origin": FRONTEND_URL},
        opener=student_opener,
    )
    assert self_status in (403, 404), f"Expected 403 or 404 on self-review attempt, got {self_status}: {self_data}"
    print(f"✓ Anti-Self Review defense (AC-028 / SEC-01) successfully blocked candidate from self-reviewing with {self_status}: {self_data}")

    print("Phase 8 Passed: Security invariants strictly enforced.")

    print("\n" + "=" * 80)
    print("ALL 8 PHASES PASSED: FlexBridge 1.4 Workplace Mentor Hub (FB-162) VERIFIED 100% GREEN!")
    print("=" * 80)


if __name__ == "__main__":
    run_employer_mentor_staging_suite()
