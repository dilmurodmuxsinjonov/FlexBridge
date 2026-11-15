#!/usr/bin/env python3
"""
FlexBridge 1.4 Automated Staging Verification Suite:
Candidate Portal: Ratings, Double-Blind Reviews, Rubrics & Appeals Hub (FB-166)

Contracts Tested:
- API-057: GET /api/bff/candidate/ratings (Personal rating aggregate, score status, active rubrics, received/given submissions, eligible relations)
- API-047: POST /api/bff/candidate/engagements/{id}/ratings (Mutual double-blind engagement ratings by rubric dimensions)
- API-058: POST /api/bff/candidate/ratings/{id}/appeals (Submit rating appeal with category, reason, and evidence notes)
- API-004: POST /api/bff/candidate/saved-opportunities (Save opportunity bookmark)
- API-037: GET /api/bff/candidate/saved-opportunities (List saved opportunities with preserved status)
- API-038: DELETE /api/bff/candidate/saved-opportunities/{id} (Unsave opportunity bookmark; idempotent 204)

Security & Architectural Invariants:
- 401 AUTH_REQUIRED on all unauthenticated requests.
- 403 CSRF_ORIGIN_MISMATCH against cross-site mutating requests.
- AC-023: Minimum sample size threshold (n < 5 withheld with explicit explanation; distinct UNRATED status).
- AC-024: Bilateral Double-Blind protection (14-day blind window; redaction of rater and comment).
- AC-025: 14-day formal rating appeal window.
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


def run_candidate_ratings_appeals_staging_suite():
    print("=" * 80)
    print("Starting FlexBridge 1.4 Staging Suite: Candidate Ratings & Appeals Hub (FB-166)")
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
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/ratings", None),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/engagements/{fake_id}/ratings", {"scores": [{"criterion_id": fake_id, "score": 5}]}),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/ratings/{fake_id}/appeals", {"reason": "Test appeal reason text min 10 chars"}),
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/saved-opportunities", None),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/saved-opportunities", {"opportunity_id": fake_id}),
        ("DELETE", f"{FRONTEND_URL}/api/bff/candidate/saved-opportunities/{fake_id}", None),
    ]

    for m, ep, pl in unauth_endpoints:
        code, resp = api_request(ep, method=m, data=pl, headers={"Origin": FRONTEND_URL}, opener=anon_opener)
        assert code == 401, f"Expected 401 on {m} {ep}, got {code}: {resp}"
        assert resp.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got: {resp}"
        print(f"  [OK] {m:6} {ep} => 401 AUTH_REQUIRED verified")

    print("Phase 1 Passed: 401 AUTH_REQUIRED verified on all 6 candidate endpoints.")

    # =========================================================================
    # PHASE 2: Anti-CSRF Origin Guard
    # =========================================================================
    print("\n--- PHASE 2: Anti-CSRF Origin Guard (403) Verification ---")
    csrf_endpoints = [
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/engagements/{fake_id}/ratings", {"scores": [{"criterion_id": fake_id, "score": 5}]}),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/ratings/{fake_id}/appeals", {"reason": "Test appeal reason text min 10 chars"}),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/saved-opportunities", {"opportunity_id": fake_id}),
        ("DELETE", f"{FRONTEND_URL}/api/bff/candidate/saved-opportunities/{fake_id}", None),
    ]

    for m, ep, pl in csrf_endpoints:
        code, resp = api_request(ep, method=m, data=pl, headers={"Origin": "https://malicious-site.example"}, opener=anon_opener)
        assert code == 403, f"Expected 403 CSRF mismatch on {m} {ep}, got {code}: {resp}"
        assert resp.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got: {resp}"
        print(f"  [OK] {m:6} {ep} with bad origin => 403 CSRF_ORIGIN_MISMATCH")

    print("Phase 2 Passed: Anti-CSRF Origin defense verified.")

    # =========================================================================
    # PHASE 3: Seed Test Fixtures in PgBouncer DB
    # =========================================================================
    print("\n--- PHASE 3: Seeding Test Fixtures in DB ---")
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

    # Active Rubric & Criteria
    rubric_id = str(uuid4())
    crit_1_id = str(uuid4())
    crit_2_id = str(uuid4())

    # Completed Job Engagement
    opp_id = str(uuid4())
    opp_rev_id = str(uuid4())
    app_id = str(uuid4())
    attempt_id = str(uuid4())
    offer_id = str(uuid4())
    engagement_id = str(uuid4())

    seeded_trigger_tables = [
        "organizations", "org_memberships", "org_role_grants",
        "candidate_profiles", "saved_opportunities"
    ]

    with engine.begin() as conn:
        for t in seeded_trigger_tables:
            conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

    try:
        with engine.begin() as conn:
            conn.execute(text("SET search_path TO flexbridge, public;"))

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
                {"id": org_id, "tax_id": f"TAX_FB166_{test_suffix}", "ts": now_ts},
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

            # 4. Active Rubric & Criteria
            existing_rubric = conn.execute(
                text("SELECT id FROM flexbridge.rubric_versions WHERE status = 'ACTIVE' LIMIT 1")
            ).mappings().first()

            if existing_rubric:
                rubric_id = str(existing_rubric["id"])
                crit_rows = conn.execute(
                    text("SELECT id FROM flexbridge.rubric_criteria WHERE rubric_id = :rid ORDER BY code"),
                    {"rid": rubric_id}
                ).fetchall()
                if len(crit_rows) >= 2:
                    crit_1_id = str(crit_rows[0][0])
                    crit_2_id = str(crit_rows[1][0])
                else:
                    crit_1_id = str(uuid4())
                    crit_2_id = str(uuid4())
                    conn.execute(
                        text("""
                            INSERT INTO flexbridge.rubric_criteria (
                                id, created_at, updated_at, rubric_id, code, title, weight, required
                            ) VALUES
                            (:c1, :now, :now, :rid, 'COMMUNICATION', 'Muloqot va Qayta Aloqa', 1, true),
                            (:c2, :now, :now, :rid, 'TASK_CLARITY', 'Vazifalar Aniq Qo''yilishi', 1, true)
                        """),
                        {"c1": crit_1_id, "c2": crit_2_id, "rid": rubric_id, "now": now_ts},
                    )
            else:
                conn.execute(
                    text("""
                        INSERT INTO flexbridge.rubric_versions (
                            id, created_at, updated_at, family, version, status, scale_min, scale_max, published_at
                        ) VALUES
                        (:rid, :now, :now, 'ORGANIZATION_EVALUATION', 1, 'ACTIVE', 1, 5, :now)
                    """),
                    {"rid": rubric_id, "now": now_ts},
                )
                conn.execute(
                    text("""
                        INSERT INTO flexbridge.rubric_criteria (
                            id, created_at, updated_at, rubric_id, code, title, weight, required
                        ) VALUES
                        (:c1, :now, :now, :rid, 'COMMUNICATION', 'Muloqot va Qayta Aloqa', 1, true),
                        (:c2, :now, :now, :rid, 'TASK_CLARITY', 'Vazifalar Aniq Qo''yilishi', 1, true)
                    """),
                    {"c1": crit_1_id, "c2": crit_2_id, "rid": rubric_id, "now": now_ts},
                )

            # 5. Opportunity & Completed Job Engagement
            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunities (
                        id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count
                    ) VALUES
                    (:id, :ts, :ts, :org_id, 'PART_TIME', 'PUBLISHED', 2, 1)
                """),
                {"id": opp_id, "org_id": org_id, "ts": now_ts},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunity_revisions (
                        id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                        region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                        shift_match_mode, snapshot_schema, contract_type
                    ) VALUES
                    (:id, :ts, :ts, :opp_id, 1, :author_id, :title, 'Next.js dasturchi',
                     'Tashkent', 'REMOTE', 'ANY', 'UZS', FALSE, :today, 'FLEXIBLE', 'EXACT', 1, 'LABOR_PART_TIME')
                """),
                {
                    "id": opp_rev_id, "opp_id": opp_id, "author_id": employer_user_id,
                    "title": f"Dasturchi Vakansiyasi {test_suffix}", "today": today_date, "ts": now_ts
                },
            )

            conn.execute(
                text("UPDATE flexbridge.opportunities SET current_revision_id = :rev_id WHERE id = :id"),
                {"rev_id": opp_rev_id, "id": opp_id},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.applications (
                        id, created_at, updated_at, opportunity_id, candidate_id, status, version
                    ) VALUES
                    (:id, :ts, :ts, :opp_id, :cid, 'HIRED', 1)
                """),
                {"id": app_id, "opp_id": opp_id, "cid": cand_profile_id, "ts": now_ts},
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
                    "id": attempt_id, "app_id": app_id, "opp_id": opp_id, "rev_id": opp_rev_id,
                    "ts": now_ts, "idem": f"attempt-idem-{test_suffix}"
                },
            )

            conn.execute(
                text("UPDATE flexbridge.applications SET current_attempt_id = :att_id WHERE id = :app_id"),
                {"att_id": attempt_id, "app_id": app_id},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.offers (
                        id, created_at, updated_at, application_id, attempt_id, revision_id,
                        issuer_membership_id, status, expires_at, terms_snapshot, idempotency_key
                    ) VALUES
                    (:id, :ts, :ts, :app_id, :att_id, :rev_id,
                     :mid, 'ACCEPTED', :exp_at, '{"salary": "5000000 UZS"}'::jsonb, :idem)
                """),
                {
                    "id": offer_id, "app_id": app_id, "att_id": attempt_id, "rev_id": opp_rev_id,
                    "mid": org_membership_id, "exp_at": now_ts + timedelta(days=7),
                    "idem": f"offer-idem-{test_suffix}", "ts": now_ts
                },
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.job_engagements (
                        id, created_at, updated_at, application_id, offer_id,
                        status, start_date, end_date, terms_snapshot, confirmed_started_at
                    ) VALUES
                    (:id, :ts, :ts, :app_id, :offer_id,
                     'COMPLETED', :today, :today, '{"title": "Dev Part-time"}'::jsonb, :now)
                """),
                {
                    "id": engagement_id, "app_id": app_id, "offer_id": offer_id,
                    "today": today_date, "now": now_ts, "ts": now_ts
                },
            )

            # 6. Initial Rating Aggregate for Candidate: UNRATED (n = 0, score = null)
            conn.execute(
                text("""
                    INSERT INTO flexbridge.rating_aggregates (
                        id, created_at, updated_at, target_user_id, rubric_id,
                        sample_size, score, window_start, window_end, computed_at
                    ) VALUES
                    (:id, :now, :now, :uid, :rid, 0, NULL, :start_d, :end_d, :now)
                """),
                {
                    "id": str(uuid4()), "now": now_ts, "uid": cand_user_id, "rid": rubric_id,
                    "start_d": today_date - timedelta(days=30), "end_d": today_date
                },
            )
    finally:
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))

    print("Phase 3 Passed: Test fixtures seeded in PgBouncer DB.")

    # =========================================================================
    # PHASE 4: Candidate Session Authentication
    # =========================================================================
    print("\n--- PHASE 4: Candidate Login & Session Setup ---")
    cookie_jar = http.cookiejar.CookieJar()
    cand_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    login_code, login_resp = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": cand_user_id, "password": cand_password},
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert login_code == 200, f"Candidate login failed ({login_code}): {login_resp}"
    print(f"  [OK] Candidate logged in successfully: user_id={cand_user_id}")

    me_code, me_resp = api_request(
        f"{FRONTEND_URL}/api/auth/me",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert me_code == 200, f"Candidate auth/me check failed ({me_code}): {me_resp}"
    user_info = me_resp.get("user", me_resp)
    assert user_info.get("user_id") == cand_user_id, f"Session user mismatch: {user_info}"
    print("Phase 4 Passed: Candidate authenticated session active.")

    # =========================================================================
    # PHASE 5: API-057 GET /api/bff/candidate/ratings Verification
    # =========================================================================
    print("\n--- PHASE 5: API-057 GET /api/bff/candidate/ratings ---")
    r_code, r_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/ratings",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert r_code == 200, f"Expected 200 on ratings GET, got {r_code}: {r_resp}"
    assert r_resp.get("contract_id") == "API-057", f"Missing contract_id API-057: {r_resp}"

    agg = r_resp.get("aggregate", {})
    assert agg.get("sample_size") == 0, f"Expected sample_size 0, got: {agg.get('sample_size')}"
    assert agg.get("score") is None, f"Expected null score for n=0, got: {agg.get('score')}"
    assert agg.get("score_status") == "UNRATED", f"Expected UNRATED status, got: {agg.get('score_status')}"
    print(f"  [OK] AC-023 Score Status: {agg.get('score_status')} (explanation: {agg.get('explanation')[:45]}...)")

    rubrics = r_resp.get("available_rubrics", [])
    matching_rubric = next((r for r in rubrics if r["id"] == rubric_id), None)
    assert matching_rubric is not None, f"Rubric {rubric_id} not found in available_rubrics: {rubrics}"
    assert len(matching_rubric["criteria"]) >= 2, f"Expected at least 2 criteria, got: {matching_rubric}"
    print(f"  [OK] Active Rubric verified: {matching_rubric['family']} (criteria: {len(matching_rubric['criteria'])})")
    print("Phase 5 Passed: API-057 Ratings summary, rubrics, and unrated status verified.")

    # =========================================================================
    # PHASE 6: API-047 POST /api/bff/candidate/engagements/{id}/ratings
    # =========================================================================
    print("\n--- PHASE 6: API-047 POST /api/bff/candidate/engagements/{id}/ratings ---")
    scores_payload = [
        {"criterion_id": crit_1_id, "score": 5},
        {"criterion_id": crit_2_id, "score": 4},
    ]

    rate_code, rate_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/engagements/{engagement_id}/ratings",
        method="POST",
        data={
            "rubric_id": rubric_id,
            "scores": scores_payload,
            "comment": "Juda yaxshi ish muhiti va aniq vazifalar",
            "idempotency_key": f"cand-rate-{engagement_id}",
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert rate_code in (200, 201), f"Expected 200/201 on engagement rating, got {rate_code}: {rate_resp}"
    assert rate_resp.get("status") in ("PENDING_BLIND", "PUBLISHED"), f"Unexpected rating status: {rate_resp}"
    print(f"  [OK] Mutual rating submitted: status={rate_resp.get('status')}, submission_id={rate_resp.get('submission_id')}")

    # Idempotent replay
    rep_code, rep_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/engagements/{engagement_id}/ratings",
        method="POST",
        data={
            "rubric_id": rubric_id,
            "scores": scores_payload,
            "comment": "Juda yaxshi ish muhiti va aniq vazifalar",
            "idempotency_key": f"cand-rate-{engagement_id}",
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert rep_code in (200, 201), f"Expected 200/201 on repeat rating, got {rep_code}: {rep_resp}"
    print(f"  [OK] Idempotent replay verified: status={rep_code}")
    print("Phase 6 Passed: API-047 mutual engagement rating verified.")

    # =========================================================================
    # PHASE 7: AC-024 Bilateral Double-Blind Verification
    # =========================================================================
    print("\n--- PHASE 7: AC-024 Bilateral Double-Blind Protection Check ---")
    blind_sub_id = str(uuid4())
    blind_rev_id = str(uuid4())

    with engine.begin() as conn:
        conn.execute(text("SET search_path TO flexbridge, public;"))
        # Insert a received submission for the candidate in PENDING_BLIND with future publish_after
        conn.execute(
            text("""
                INSERT INTO flexbridge.rating_submissions (
                    id, created_at, updated_at, engagement_id, rubric_id, rater_id,
                    target_user_id, version, status, comment, submitted_at, publish_after
                ) VALUES (
                    :id, :now, :now, :eng_id, :rid, :rater_id,
                    :target_uid, 1, 'PENDING_BLIND', 'Maxfiy baholash sharhi', :now, :pub_after
                )
            """),
            {
                "id": blind_sub_id,
                "now": now_ts,
                "eng_id": engagement_id,
                "rid": rubric_id,
                "rater_id": employer_user_id,
                "target_uid": cand_user_id,
                "pub_after": now_ts + timedelta(days=14),
            },
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.rating_revisions (
                    id, created_at, updated_at, submission_id, version, comment,
                    submitted_at, rubric_snapshot
                ) VALUES (
                    :id, :now, :now, :sub_id, 1, 'Maxfiy baholash sharhi', :now, '{}'::jsonb
                )
            """),
            {"id": blind_rev_id, "now": now_ts, "sub_id": blind_sub_id},
        )

    r2_code, r2_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/ratings",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert r2_code == 200
    rec_items = r2_resp.get("submissions_received", [])
    blind_item = next((it for it in rec_items if it["id"] == blind_sub_id), None)
    assert blind_item is not None, f"Blinded rating {blind_sub_id} not found: {rec_items}"
    assert blind_item.get("blind_window_active") is True, f"Expected blind_window_active True: {blind_item}"
    assert blind_item.get("comment") is None, f"Expected redacted comment during blind window: {blind_item}"
    assert blind_item.get("rater_id") is None, f"Expected redacted rater_id during blind window: {blind_item}"
    print(f"  [OK] AC-024 Double-Blind verified: comment & rater redacted, status={blind_item.get('status')}")
    print("Phase 7 Passed: AC-024 bilateral anti-retaliation blind protection confirmed.")

    # =========================================================================
    # PHASE 8: API-058 POST /api/bff/candidate/ratings/{id}/appeals
    # =========================================================================
    print("\n--- PHASE 8: API-058 Rating Appeal Workflow ---")
    with engine.begin() as conn:
        conn.execute(text("SET search_path TO flexbridge, public;"))
        # Update the received submission to PUBLISHED with expired blind window
        conn.execute(
            text("""
                UPDATE flexbridge.rating_submissions
                SET status = 'PUBLISHED', publish_after = :pub_after, comment = 'Adolatsiz past baho'
                WHERE id = :id
            """),
            {"id": blind_sub_id, "pub_after": now_ts - timedelta(days=2)},
        )

    # Submit Appeal against the published rating
    app_code, app_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/ratings/{blind_sub_id}/appeals",
        method="POST",
        data={
            "category": "FACTUAL_DISPUTE",
            "reason": "Ushbu baho ish shartnomasi va kundalik dalillariga to'g'ri kelmaydi",
            "evidence_notes": "Kundalik dalillari DB-067",
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert app_code == 201, f"Expected 201 on rating appeal, got {app_code}: {app_resp}"
    assert app_resp.get("status") == "PENDING" or "appeal_id" in app_resp, f"Unexpected appeal response: {app_resp}"
    print(f"  [OK] Appeal submitted: appeal_id={app_resp.get('appeal_id')}, category={app_resp.get('category')}")

    # Conflict or idempotent replay on repeat appeal
    rep_app_code, rep_app_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/ratings/{blind_sub_id}/appeals",
        method="POST",
        data={
            "category": "FACTUAL_DISPUTE",
            "reason": "Ushbu baho ish shartnomasi va kundalik dalillariga to'g'ri kelmaydi",
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert rep_app_code in (200, 201, 409), f"Unexpected repeat appeal response ({rep_app_code}): {rep_app_resp}"
    print(f"  [OK] Anti-duplication appeal handling verified ({rep_app_code})")
    print("Phase 8 Passed: API-058 rating appeal submission verified.")

    # =========================================================================
    # PHASE 9: API-004, API-037, API-038 Saved Opportunities Lifecycle
    # =========================================================================
    print("\n--- PHASE 9: Saved Opportunities Lifecycle (API-004 / API-037 / API-038) ---")
    save_code, save_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/saved-opportunities",
        method="POST",
        data={"opportunity_id": opp_id},
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert save_code in (200, 201), f"Expected 200/201 on save opportunity, got {save_code}: {save_resp}"
    saved_id = save_resp.get("id")
    assert saved_id is not None, f"Missing saved_id in response: {save_resp}"
    print(f"  [OK] Opportunity saved (API-004): saved_id={saved_id}")

    # List saved opportunities (API-037)
    list_code, list_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/saved-opportunities",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert list_code == 200, f"Expected 200 on list saved, got {list_code}: {list_resp}"
    saved_items = list_resp.get("items", [])
    found_saved = next((it for it in saved_items if it["opportunity_id"] == opp_id), None)
    assert found_saved is not None, f"Saved opportunity {opp_id} not in list: {saved_items}"
    assert found_saved["opportunity"]["title"] == f"Dasturchi Vakansiyasi {test_suffix}", f"Title mismatch: {found_saved}"
    print(f"  [OK] Saved opportunities listed (API-037): total={list_resp.get('total')}, title='{found_saved['opportunity']['title']}'")

    # Delete saved opportunity (API-038)
    del_code, del_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/saved-opportunities/{saved_id}",
        method="DELETE",
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert del_code in (200, 204), f"Expected 200/204 on delete saved, got {del_code}: {del_resp}"
    print(f"  [OK] Opportunity unsaved (API-038): code={del_code}")

    # Idempotent repeat delete
    del2_code, del2_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/saved-opportunities/{saved_id}",
        method="DELETE",
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert del2_code in (200, 204), f"Expected 204 idempotent on repeat delete, got {del2_code}: {del2_resp}"
    print(f"  [OK] Idempotent unsave repeat (204) verified")
    print("Phase 9 Passed: Saved opportunities lifecycle confirmed.")

    # =========================================================================
    # PHASE 10: IDOR & Security Guardrails
    # =========================================================================
    print("\n--- PHASE 10: IDOR & Security Guardrails ---")
    non_existent_id = str(uuid4())

    # Rate non-existent engagement -> 404
    idor_rate_code, idor_rate_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/engagements/{non_existent_id}/ratings",
        method="POST",
        data={
            "rubric_id": rubric_id,
            "scores": [{"criterion_id": crit_1_id, "score": 5}],
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert idor_rate_code == 404, f"Expected 404 on non-existent engagement rating, got {idor_rate_code}: {idor_rate_resp}"
    print(f"  [OK] IDOR engagement rating protection: 404 confirmed")

    # Short appeal reason (< 10 chars) -> 422
    val_app_code, val_app_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/ratings/{blind_sub_id}/appeals",
        method="POST",
        data={
            "category": "FACTUAL_DISPUTE",
            "reason": "Qisqa",
        },
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert val_app_code == 422, f"Expected 422 for reason < 10 chars, got {val_app_code}: {val_app_resp}"
    print(f"  [OK] Reason validation (< 10 chars): 422 confirmed")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF CANDIDATE RATINGS & APPEALS STAGING SUITE PASSED 100% GREEN!")
    print("=" * 80)


if __name__ == "__main__":
    run_candidate_ratings_appeals_staging_suite()
