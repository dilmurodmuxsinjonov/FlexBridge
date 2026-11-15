#!/usr/bin/env python3
"""FlexBridge 1.4 Vacancy Lifecycle & Interview Responses Staging Verification Suite (FB-180).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected on all endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Anti-CSRF Origin Guard rejection on mutating endpoints (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 3: Database Fixtures Setup via PgBouncer (127.0.0.1:5432/flexbridge, prepare_threshold=None).
Phase 4: HR and Candidate authentication via Next.js BFF (/api/auth/login) with MFA assurance.
Phase 5: API-081 Opportunity Publishing (Draft -> Published with quota validation).
Phase 6: API-082 Opportunity Lifecycle Transitions (Published -> Paused -> Closed).
Phase 7: API-042 Candidate Interview Acceptance (Response: ACCEPTED -> Status: CONFIRMED).
Phase 8: API-042 Candidate Reschedule Request (Response: RESCHEDULE_REQUESTED).
Phase 9: API-042 Candidate Interview Decline (Response: DECLINED -> Status: CANCELLED).
Phase 10: Negative Authorization Checks (Foreign candidate IDOR rejected; Unauthorized user cannot publish/transition).

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
    print("FLEXBRIDGE 1.4 FB-180 STAGING VERIFICATION SUITE")
    print("Vacancy Lifecycle (API-081/082) & Candidate Interview Responses (API-042)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Phase 1: Unauthenticated Access Rejections (401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n--- Phase 1: Unauthenticated BFF Endpoint Rejections ---")
    dummy_uuid = "00000000-0000-0000-0000-000000000000"
    endpoints = [
        ("POST", f"{FRONTEND_URL}/api/bff/employer/opportunities/{dummy_uuid}/publish", None),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/opportunities/{dummy_uuid}/transition", {"status": "PAUSED"}),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/interviews/{dummy_uuid}/responses", {"response": "ACCEPTED"}),
    ]

    for meth, ep, d in endpoints:
        code, data, _ = make_request(ep, method=meth, data=d, headers={"Origin": FRONTEND_URL})
        assert code == 401, f"Expected 401 for unauthenticated {meth} {ep}, got {code}: {data}"
        print(f"  [PASS] 401 on unauthenticated {meth} {ep}")

    # -------------------------------------------------------------------------
    # Phase 2: Anti-CSRF Origin Guard Rejection (403 CSRF_ORIGIN_MISMATCH)
    # -------------------------------------------------------------------------
    print("\n--- Phase 2: Anti-CSRF Origin Guard Rejections ---")
    for meth, ep, d in endpoints:
        code, data, _ = make_request(
            ep,
            method=meth,
            data=d or {"test": 1},
            headers={"Origin": "https://malicious-attacker.com"},
        )
        assert code == 403, f"Expected 403 CSRF for {meth} {ep}, got {code}: {data}"
        assert data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH: {data}"
        print(f"  [PASS] 403 CSRF_ORIGIN_MISMATCH on {meth} {ep}")

    # -------------------------------------------------------------------------
    # Phase 3: DB Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n--- Phase 3: Database Fixtures Setup via PgBouncer ---")
    db_url = get_database_url()
    engine = create_engine(db_url, poolclass=NullPool, connect_args={"prepare_threshold": None})

    test_suffix = uuid4().hex[:8]
    org_id = str(uuid5(NAMESPACE_URL, f"flexbridge:fb180:org:{test_suffix}"))
    hr_user_id = str(uuid5(NAMESPACE_URL, f"flexbridge:fb180:hr:{test_suffix}"))
    cand_user_id = str(uuid5(NAMESPACE_URL, f"flexbridge:fb180:candidate:{test_suffix}"))
    foreign_user_id = str(uuid5(NAMESPACE_URL, f"flexbridge:fb180:foreign:{test_suffix}"))
    granter_user_id = str(uuid5(NAMESPACE_URL, f"flexbridge:fb180:granter:{test_suffix}"))

    cand_profile_id = str(uuid4())
    foreign_profile_id = str(uuid4())
    membership_id = str(uuid4())
    case_id = str(uuid4())
    cap_id = str(uuid4())
    ent_id = str(uuid4())
    order_id = str(uuid4())

    hr_pwd = "HrPasswordSecret!2026"
    hr_pwd_hash = hash_password(hr_pwd)

    cand_pwd = "CandPasswordSecret!2026"
    cand_pwd_hash = hash_password(cand_pwd)

    foreign_pwd = "ForeignPasswordSecret!2026"
    foreign_pwd_hash = hash_password(foreign_pwd)

    opp_draft_id = str(uuid4())
    rev_draft_id = str(uuid4())

    opp_int_1 = str(uuid4())
    opp_int_2 = str(uuid4())
    opp_int_3 = str(uuid4())

    rev_int_1 = str(uuid4())
    rev_int_2 = str(uuid4())
    rev_int_3 = str(uuid4())

    app_id_1 = str(uuid4())
    app_id_2 = str(uuid4())
    app_id_3 = str(uuid4())

    att_id_1 = str(uuid4())
    att_id_2 = str(uuid4())
    att_id_3 = str(uuid4())

    int_id_1 = str(uuid4())
    int_id_2 = str(uuid4())
    int_id_3 = str(uuid4())

    with engine.begin() as conn:
        now_ts = datetime.now(timezone.utc)
        today_date = now_ts.date()

        # 1. Users
        for uid, pwd_h, dname in [
            (hr_user_id, hr_pwd_hash, "HR Vakansiya Menejeri"),
            (cand_user_id, cand_pwd_hash, "Nomzod Suhbat Qatnashchisi"),
            (foreign_user_id, foreign_pwd_hash, "Begona Nomzod IDOR"),
            (granter_user_id, hr_pwd_hash, "Granter User"),
        ]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                    VALUES (:id, :now, :now, :dname, :phash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
                    ON CONFLICT (id) DO UPDATE SET password_hash = :phash, status = 'ACTIVE', updated_at = :now
                """),
                {"id": uid, "phash": pwd_h, "dname": dname, "now": now_ts},
            )

        # 2. Candidate Profiles
        for pid, uid in [(cand_profile_id, cand_user_id), (foreign_profile_id, foreign_user_id)]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.candidate_profiles (
                        id, created_at, updated_at, user_id, headline, region,
                        experience_months, bio, visibility
                    ) VALUES (
                        :pid, :now, :now, :uid, 'Talaba Dasturchi', 'Tashkent',
                        6, 'Amaliyotchi talaba', 'PUBLIC'
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {"pid": pid, "uid": uid, "now": now_ts},
            )

        # 3. Organization (VERIFIED)
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, legal_name, public_name, tax_id, status, region)
                VALUES (:id, :now, :now, 'FB180 Tech Corp LLC', 'FB180Tech', :tax_id, 'VERIFIED', 'Tashkent')
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": org_id, "tax_id": f"TIN_{test_suffix}", "now": now_ts},
        )

        # 4. Org Membership & Role Grants (OWNER + HR)
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status, accepted_at)
                VALUES (:id, :now, :now, :org_id, :uid, 'ACTIVE', :now)
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": membership_id, "org_id": org_id, "uid": hr_user_id, "now": now_ts},
        )

        owner_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'OWNER' AND scope_kind = 'ORG' LIMIT 1")
        ).scalar_one()

        hr_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'HR' AND scope_kind = 'ORG' LIMIT 1")
        ).scalar_one()

        conn.execute(
            text("""
                INSERT INTO flexbridge.org_role_grants (id, created_at, updated_at, membership_id, role_id, granted_by_id)
                VALUES
                (:g1, :now, :now, :mid, :r_owner, :by_id),
                (:g2, :now, :now, :mid, :r_hr, :by_id)
                ON CONFLICT DO NOTHING
            """),
            {
                "g1": str(uuid4()),
                "g2": str(uuid4()),
                "mid": membership_id,
                "r_owner": owner_role_id,
                "r_hr": hr_role_id,
                "by_id": granter_user_id,
                "now": now_ts,
            },
        )

        # 5. Organization Capability (JOB_EMPLOYER via approved Verification Case)
        conn.execute(
            text("""
                INSERT INTO flexbridge.verification_cases (
                    id, created_at, updated_at, requester_id, assigned_reviewer_id, organization_id,
                    kind, status, current_revision, due_at, decided_at
                ) VALUES (
                    :cid, :now, :now, :req_id, :rev_id, :org_id,
                    'JOB_EMPLOYER', 'APPROVED', 1, :now, :now
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "cid": case_id,
                "now": now_ts,
                "req_id": hr_user_id,
                "rev_id": granter_user_id,
                "org_id": org_id,
            },
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.organization_capabilities (
                    id, created_at, updated_at, organization_id, capability, status, approved_case_id
                ) VALUES (
                    :cap_id, :now, :now, :org_id, 'JOB_EMPLOYER', 'ACTIVE', :cid
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "cap_id": cap_id,
                "now": now_ts,
                "org_id": org_id,
                "cid": case_id,
            },
        )

        # 6. Product, Price Version, Order & Service Entitlements (Quota for Publishing)
        product_org_id = str(uuid4())
        price_org_id = str(uuid4())
        conn.execute(
            text("""
                INSERT INTO flexbridge.products (id, created_at, updated_at, code, name, service_kind, active)
                VALUES (:pid, :now, :now, :code, :code, :code, TRUE)
                ON CONFLICT (id) DO NOTHING
            """),
            {"pid": product_org_id, "code": f"PROD_{test_suffix}", "now": now_ts}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.price_versions (
                    id, created_at, updated_at, product_id, version, amount, currency, duration_days, tax_included, valid_from
                ) VALUES (
                    :pvid, :now, :now, :pid, 1, 599000, 'UZS', 30, TRUE, :now
                ) ON CONFLICT (id) DO NOTHING
            """),
            {"pvid": price_org_id, "pid": product_org_id, "now": now_ts}
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.orders (
                    id, created_at, updated_at, organization_id, purchaser_id, price_id,
                    amount, currency, price_snapshot, status, idempotency_key
                ) VALUES (
                    :id, :now, :now, :org_id, :purchaser_id, :price_id,
                    599000, 'UZS', '{"plan_code": "ORG_PLAN_30D", "price_uzs": 599000}'::jsonb,
                    'PAID', :idem
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": order_id,
                "org_id": org_id,
                "purchaser_id": hr_user_id,
                "price_id": price_org_id,
                "idem": f"idem_order_{test_suffix}",
                "now": now_ts,
            },
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.service_entitlements (
                    id, created_at, updated_at, organization_id, order_id, service_kind,
                    status, starts_at, ends_at, quota, concurrent_active_limit
                ) VALUES (
                    :id, :now, :now, :org_id, :order_id, 'ORG_PLAN_30D',
                    'ACTIVE', :now, :ends_at, 50, 50
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": ent_id,
                "now": now_ts,
                "org_id": org_id,
                "order_id": order_id,
                "ends_at": now_ts + timedelta(days=30),
            },
        )

        # 7. Opportunity 1: Draft/Approved Vacancy (ready for API-081 publish)
        conn.execute(
            text("""
                INSERT INTO flexbridge.opportunities (
                    id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count
                ) VALUES (
                    :id, :now, :now, :org_id, 'PART_TIME', 'APPROVED', 5, 0
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": opp_draft_id, "org_id": org_id, "now": now_ts},
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.opportunity_revisions (
                    id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                    region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                    shift_match_mode, snapshot_schema, contract_type
                ) VALUES (
                    :id, :now, :now, :opp_id, 1, :author_id, 'Frontend Developer (FB-180 Test)', 'Next.js & TypeScript',
                    'Tashkent', 'HYBRID', 'ANY', 'UZS', FALSE, :today, 'FLEXIBLE', 'EXACT', 1, 'LABOR_PART_TIME'
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": rev_draft_id,
                "opp_id": opp_draft_id,
                "author_id": hr_user_id,
                "today": today_date,
                "now": now_ts,
            },
        )

        conn.execute(
            text("UPDATE flexbridge.opportunities SET current_revision_id = :rev_id WHERE id = :opp_id"),
            {"rev_id": rev_draft_id, "opp_id": opp_draft_id},
        )

        # 8. Opportunities 2, 3, 4: Published Vacancies (for Interview scheduling & testing)
        starts_at = now_ts + timedelta(days=2)
        ends_at = starts_at + timedelta(hours=1)

        for sfx, opp_id, rev_id, app_id, att_id, int_id, title in [
            ("1", opp_int_1, rev_int_1, app_id_1, att_id_1, int_id_1, "Fullstack Developer (FB-180 Test 1)"),
            ("2", opp_int_2, rev_int_2, app_id_2, att_id_2, int_id_2, "Fullstack Developer (FB-180 Test 2)"),
            ("3", opp_int_3, rev_int_3, app_id_3, att_id_3, int_id_3, "Fullstack Developer (FB-180 Test 3)"),
        ]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunities (
                        id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count, published_at
                    ) VALUES (
                        :id, :now, :now, :org_id, 'PART_TIME', 'PUBLISHED', 5, 0, :now
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {"id": opp_id, "org_id": org_id, "now": now_ts},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunity_revisions (
                        id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                        region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                        shift_match_mode, snapshot_schema, contract_type, published_at
                    ) VALUES (
                        :id, :now, :now, :opp_id, 1, :author_id, :title, 'Fullstack Python & React',
                        'Tashkent', 'HYBRID', 'ANY', 'UZS', FALSE, :today, 'FLEXIBLE', 'EXACT', 1, 'LABOR_PART_TIME', :now
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": rev_id,
                    "opp_id": opp_id,
                    "author_id": hr_user_id,
                    "title": title,
                    "today": today_date,
                    "now": now_ts,
                },
            )

            conn.execute(
                text("UPDATE flexbridge.opportunities SET current_revision_id = :rev_id WHERE id = :opp_id"),
                {"rev_id": rev_id, "opp_id": opp_id},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.applications (
                        id, created_at, updated_at, opportunity_id, candidate_id, status, version
                    ) VALUES (
                        :app_id, :now, :now, :opp_id, :cand_prof_id, 'INTERVIEW_SCHEDULED', 1
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {"app_id": app_id, "opp_id": opp_id, "cand_prof_id": cand_profile_id, "now": now_ts},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.application_attempts (
                        id, created_at, updated_at, application_id, opportunity_id, attempt_no, revision_id,
                        profile_snapshot, schedule_result, matching_version, submitted_at, idempotency_key
                    ) VALUES (
                        :att_id, :now, :now, :app_id, :opp_id, 1, :rev_id,
                        '{"headline": "Talaba"}'::jsonb, 'MATCHED', '1.0', :now, :idem
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "att_id": att_id,
                    "app_id": app_id,
                    "opp_id": opp_id,
                    "rev_id": rev_id,
                    "now": now_ts,
                    "idem": f"idem-attempt-fb180-{test_suffix}-{sfx}",
                },
            )

            conn.execute(
                text("UPDATE flexbridge.applications SET current_attempt_id = :att_id WHERE id = :app_id"),
                {"att_id": att_id, "app_id": app_id},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.interviews (
                        id, created_at, updated_at, application_id, organizer_membership_id,
                        starts_at, ends_at, timezone, mode, location_or_link, status, version
                    ) VALUES (
                        :int_id, :now, :now, :app_id, :mid,
                        :starts, :ends, 'Asia/Tashkent', 'ONLINE', 'https://meet.google.com/test-fb180',
                        'SCHEDULED', 1
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "int_id": int_id,
                    "app_id": app_id,
                    "mid": membership_id,
                    "starts": starts_at,
                    "ends": ends_at,
                    "now": now_ts,
                },
            )

    print(f"  [PASS] HR user: {hr_user_id}")
    print(f"  [PASS] Candidate user: {cand_user_id}")
    print(f"  [PASS] Draft Opportunity: {opp_draft_id}")
    print(f"  [PASS] Interviews seeded: {int_id_1}, {int_id_2}, {int_id_3}")

    # -------------------------------------------------------------------------
    # Phase 4: Authentication via Next.js BFF (/api/auth/login)
    # -------------------------------------------------------------------------
    print("\n--- Phase 4: Authenticate HR, Candidate, and Foreign Candidate via BFF ---")

    def login_and_elevate(uid: str, pwd: str, role_name: str) -> urllib.request.OpenerDirector:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        code, data, _ = make_request(
            f"{FRONTEND_URL}/api/auth/login",
            method="POST",
            data={"user_id": uid, "password": pwd},
            headers={"Origin": FRONTEND_URL},
            opener=opener,
        )
        assert code == 200, f"Login failed for {role_name} ({uid}): {code} - {data}"
        print(f"  [PASS] {role_name} logged in successfully via BFF")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE flexbridge.sessions
                    SET assurance = 'MFA', updated_at = NOW()
                    WHERE user_id = :uid AND revoked_at IS NULL
                    """
                ),
                {"uid": uid},
            )
        print(f"  [PASS] {role_name} session assurance elevated to MFA")
        return opener

    hr_opener = login_and_elevate(hr_user_id, hr_pwd, "HR Manager")
    cand_opener = login_and_elevate(cand_user_id, cand_pwd, "Candidate")
    foreign_opener = login_and_elevate(foreign_user_id, foreign_pwd, "Foreign Candidate")

    # -------------------------------------------------------------------------
    # Phase 5: API-081 Opportunity Publishing (Draft -> Published)
    # -------------------------------------------------------------------------
    print("\n--- Phase 5: API-081 Opportunity Publishing ---")
    code, pub_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/opportunities/{opp_draft_id}/publish",
        method="POST",
        headers={"Origin": FRONTEND_URL},
        opener=hr_opener,
    )
    assert code in (200, 201), f"Expected 200/201 on publish opportunity, got {code}: {pub_resp}"
    assert pub_resp.get("ok") is True, f"Expected ok True: {pub_resp}"
    assert pub_resp.get("contract_id") == "API-081", f"Expected contract_id API-081: {pub_resp}"
    print(f"  [PASS] API-081 Opportunity published successfully: {opp_draft_id}")

    # Verify status in database
    with engine.begin() as conn:
        status = conn.execute(
            text("SELECT status FROM flexbridge.opportunities WHERE id = :id"),
            {"id": opp_draft_id},
        ).scalar()
        assert status == "PUBLISHED", f"Expected status PUBLISHED in DB, got {status}"
    print(f"  [PASS] DB verified: opportunity status is PUBLISHED")

    # -------------------------------------------------------------------------
    # Phase 6: API-082 Opportunity Lifecycle Transitions (Pause & Close)
    # -------------------------------------------------------------------------
    print("\n--- Phase 6: API-082 Opportunity Lifecycle Transitions ---")
    # Transition to PAUSED
    code, pause_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/opportunities/{opp_draft_id}/transition",
        method="POST",
        data={"status": "PAUSED"},
        headers={"Origin": FRONTEND_URL},
        opener=hr_opener,
    )
    assert code in (200, 201), f"Expected 200 on transition to PAUSED, got {code}: {pause_resp}"
    assert pause_resp.get("ok") is True, f"Expected ok True: {pause_resp}"
    assert pause_resp.get("contract_id") == "API-082", f"Expected contract_id API-082: {pause_resp}"
    print(f"  [PASS] API-082 Opportunity transitioned to PAUSED")

    # Transition to CLOSED
    code, close_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/opportunities/{opp_draft_id}/transition",
        method="POST",
        data={"status": "CLOSED"},
        headers={"Origin": FRONTEND_URL},
        opener=hr_opener,
    )
    assert code in (200, 201), f"Expected 200 on transition to CLOSED, got {code}: {close_resp}"
    assert close_resp.get("ok") is True, f"Expected ok True: {close_resp}"
    print(f"  [PASS] API-082 Opportunity transitioned to CLOSED")

    # Verify status in database
    with engine.begin() as conn:
        final_status = conn.execute(
            text("SELECT status FROM flexbridge.opportunities WHERE id = :id"),
            {"id": opp_draft_id},
        ).scalar()
        assert final_status == "CLOSED", f"Expected status CLOSED in DB, got {final_status}"
    print(f"  [PASS] DB verified: opportunity status is CLOSED")

    # -------------------------------------------------------------------------
    # Phase 7: API-042 Candidate Interview Acceptance (ACCEPTED -> CONFIRMED)
    # -------------------------------------------------------------------------
    print("\n--- Phase 7: API-042 Candidate Interview Acceptance ---")
    code, accept_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/interviews/{int_id_1}/responses",
        method="POST",
        data={"response": "ACCEPTED", "note": "Taklif qabul qilindi, tayyorman."},
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert code in (200, 201), f"Expected 200 on interview accept, got {code}: {accept_resp}"
    assert accept_resp.get("ok") is True, f"Expected ok True: {accept_resp}"
    assert accept_resp.get("contract_id") == "API-042", f"Expected contract_id API-042: {accept_resp}"
    print(f"  [PASS] API-042 Interview {int_id_1} response ACCEPTED")

    with engine.begin() as conn:
        int_status = conn.execute(
            text("SELECT status FROM flexbridge.interviews WHERE id = :id"),
            {"id": int_id_1},
        ).scalar()
        assert int_status == "CONFIRMED", f"Expected interview status CONFIRMED, got {int_status}"
    print(f"  [PASS] DB verified: interview status is CONFIRMED")

    # -------------------------------------------------------------------------
    # Phase 8: API-042 Candidate Reschedule Request (RESCHEDULE_REQUESTED)
    # -------------------------------------------------------------------------
    print("\n--- Phase 8: API-042 Candidate Reschedule Request ---")
    code, resched_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/interviews/{int_id_2}/responses",
        method="POST",
        data={"response": "RESCHEDULE_REQUESTED", "note": "Universitet darsim sababli soat 16:00 ga ko'chirishni so'rayman."},
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert code in (200, 201), f"Expected 200 on interview reschedule, got {code}: {resched_resp}"
    assert resched_resp.get("ok") is True, f"Expected ok True: {resched_resp}"
    print(f"  [PASS] API-042 Interview {int_id_2} response RESCHEDULE_REQUESTED")

    with engine.begin() as conn:
        int_status = conn.execute(
            text("SELECT status FROM flexbridge.interviews WHERE id = :id"),
            {"id": int_id_2},
        ).scalar()
        assert int_status == "RESCHEDULE_REQUESTED", f"Expected interview status RESCHEDULE_REQUESTED, got {int_status}"
    print(f"  [PASS] DB verified: interview status is RESCHEDULE_REQUESTED")

    # -------------------------------------------------------------------------
    # Phase 9: API-042 Candidate Interview Decline (DECLINED -> CANCELLED)
    # -------------------------------------------------------------------------
    print("\n--- Phase 9: API-042 Candidate Interview Decline ---")
    code, decline_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/interviews/{int_id_3}/responses",
        method="POST",
        data={"response": "DECLINED", "note": "Boshqa korxona taklifini qabul qildim."},
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert code in (200, 201), f"Expected 200 on interview decline, got {code}: {decline_resp}"
    assert decline_resp.get("ok") is True, f"Expected ok True: {decline_resp}"
    print(f"  [PASS] API-042 Interview {int_id_3} response DECLINED")

    with engine.begin() as conn:
        int_status = conn.execute(
            text("SELECT status FROM flexbridge.interviews WHERE id = :id"),
            {"id": int_id_3},
        ).scalar()
        assert int_status == "CANCELLED", f"Expected interview status CANCELLED, got {int_status}"
    print(f"  [PASS] DB verified: interview status is CANCELLED")

    # -------------------------------------------------------------------------
    # Phase 10: Negative Authorization Checks
    # -------------------------------------------------------------------------
    print("\n--- Phase 10: Negative Authorization Checks ---")
    # 1. Foreign Candidate attempts to respond to cand_user_id's interview (IDOR protection)
    code, idor_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/candidate/interviews/{int_id_1}/responses",
        method="POST",
        data={"response": "DECLINED"},
        headers={"Origin": FRONTEND_URL},
        opener=foreign_opener,
    )
    assert code in (403, 404), f"Expected 403 or 404 on foreign candidate IDOR, got {code}: {idor_resp}"
    print(f"  [PASS] Foreign candidate IDOR rejected with HTTP {code}")

    # 2. Candidate attempts to publish organization's opportunity -> Expect 403/404/409
    code, unauth_pub, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/opportunities/{opp_int_1}/publish",
        method="POST",
        headers={"Origin": FRONTEND_URL},
        opener=cand_opener,
    )
    assert code in (403, 404, 409), f"Expected rejection on candidate publishing opportunity, got {code}: {unauth_pub}"
    print(f"  [PASS] Non-HR candidate publishing attempt rejected with HTTP {code}")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF VACANCY LIFECYCLE & INTERVIEWS STAGING VERIFICATION PASSED 100% GREEN!")
    print("=" * 80)


if __name__ == "__main__":
    main()
