#!/usr/bin/env python3
"""
Staging Verification Suite: Candidate Profile Management, Skills Catalog & Weekly Availability Schedule (FB-158)

Contracts Verified:
- API-026: PATCH /api/v1/me/candidate (CAP-002 / CANDIDATE)
- API-032: PATCH /api/v1/me/candidate/skills (CAP-002 / CANDIDATE)
- API-035: GET /api/v1/me/availability (CAP-005 / CANDIDATE)
- API-028: PUT /api/v1/me/availability (CAP-005 / CANDIDATE)

Phases:
1. Unauthenticated route guard rejection (401 AUTH_REQUIRED) across all candidate profile endpoints.
2. Fixture seeding via PgBouncer (Candidate user, profile, catalog skills).
3. Candidate authentication via Next.js BFF (/api/auth/login).
4. Candidate profile fetch & update with validation checks (API-026).
5. Skills catalog search & candidate skills add/remove (API-032).
6. Candidate weekly availability schedule management with interval validation (API-035 / API-028).
7. Anti-CSRF origin mismatch rejection on all mutating endpoints (403).

Tested against:
- Live Next.js BFF at http://127.0.0.1:3000
- PgBouncer at 127.0.0.1:5432/flexbridge (prepare_threshold=None)
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta, date
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


def run_candidate_profile_staging_suite():
    print("=" * 80)
    print("Starting FlexBridge 1.4 Staging Suite: Candidate Profile & Availability (FB-158)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_suffix = uuid4().hex[:8]
    candidate_user_id = str(uuid4())
    candidate_profile_id = str(uuid4())
    candidate_password = "CandidateProfilePass123!"
    candidate_hash = hash_password(candidate_password)

    skill_python_id = str(uuid4())
    skill_react_id = str(uuid4())
    skill_postgres_id = str(uuid4())

    now_utc = datetime.now(timezone.utc)
    today_str = date.today().isoformat()

    # --------------------------------------------------------------------------
    # PHASE 1: Unauthenticated rejection across all candidate profile BFF endpoints
    # --------------------------------------------------------------------------
    print("\n[Phase 1] Verifying unauthenticated rejections (401 AUTH_REQUIRED)...")
    unauth_endpoints = [
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/profile", None),
        ("PATCH", f"{FRONTEND_URL}/api/bff/candidate/profile", {"headline": "Senior Dev"}),
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/skills", None),
        ("PATCH", f"{FRONTEND_URL}/api/bff/candidate/skills", {"skills": []}),
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/availability", None),
        ("PUT", f"{FRONTEND_URL}/api/bff/candidate/availability", {"rules": []}),
    ]

    for method, url, body in unauth_endpoints:
        code, resp = api_request(url, method=method, data=body, headers={"Origin": FRONTEND_URL})
        assert code == 401, f"Expected 401 on {method} {url}, got {code}: {resp}"
        print(f"  ✓ {method} {url.replace(FRONTEND_URL, '')} -> 401 (Auth required enforced)")

    # --------------------------------------------------------------------------
    # PHASE 2: Fixture seeding via PgBouncer
    # --------------------------------------------------------------------------
    print("\n[Phase 2] Seeding test fixtures into staging database via PgBouncer...")
    with engine.begin() as conn:
        # 1. Candidate User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Sardor Qodirov', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": candidate_user_id, "pwd": candidate_hash, "now": now_utc}
        )

        # 2. Candidate Profile
        conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, bio, experience_months, visibility)
                VALUES (:id, :now, :now, :uid, 'Junior Backend Developer', 'Toshkent shahri', 'Talaba dasturchi', 6, 'PUBLIC')
            """),
            {"id": candidate_profile_id, "uid": candidate_user_id, "now": now_utc}
        )

        # 3. Seed Catalog Skills (with ON CONFLICT on code)
        skills_data = [
            (skill_python_id, f"PYTHON_{test_suffix}", "Python Dasturlash", "Программирование на Python"),
            (skill_react_id, f"REACT_{test_suffix}", "React & Next.js", "React и Next.js"),
            (skill_postgres_id, f"POSTGRES_{test_suffix}", "PostgreSQL & SQL", "PostgreSQL и SQL"),
        ]
        for s_id, s_code, s_uz, s_ru in skills_data:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.skills (id, created_at, updated_at, code, name_uz, name_ru, aliases, active)
                    VALUES (:id, :now, :now, :code, :uz, :ru, '[]'::jsonb, true)
                """),
                {"id": s_id, "now": now_utc, "code": s_code, "uz": s_uz, "ru": s_ru}
            )

    print("  ✓ Fixtures seeded successfully via PgBouncer.")

    # --------------------------------------------------------------------------
    # PHASE 3: Candidate Authentication via Next.js BFF
    # --------------------------------------------------------------------------
    print("\n[Phase 3] Logging in as Candidate via Next.js BFF (/api/auth/login)...")
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))

    login_code, login_resp = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": candidate_user_id, "password": candidate_password},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert login_code == 200, f"Expected 200 on login, got {login_code}: {login_resp}"
    assert login_resp.get("ok") is True, f"Login failed: {login_resp}"
    print(f"  ✓ Candidate logged in successfully: user_id={candidate_user_id}")

    # Verify session via /api/auth/me
    me_code, me_resp = api_request(f"{FRONTEND_URL}/api/auth/me", method="GET", opener=opener)
    assert me_code == 200, f"Expected 200 on /api/auth/me, got {me_code}: {me_resp}"
    assert me_resp.get("ok") is True, f"Not authenticated: {me_resp}"
    print("  ✓ Candidate session authenticated and verified via /api/auth/me.")

    # --------------------------------------------------------------------------
    # PHASE 4: Candidate Profile Fetch & Update (API-026)
    # --------------------------------------------------------------------------
    print("\n[Phase 4] Testing Candidate Profile Fetch & Update (API-026)...")
    # Fetch initial profile
    get_prof_code, get_prof_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/profile",
        method="GET",
        opener=opener,
    )
    assert get_prof_code == 200, f"Expected 200 on profile fetch, got {get_prof_code}: {get_prof_resp}"
    assert get_prof_resp.get("ok") is True, f"Profile fetch not ok: {get_prof_resp}"
    prof_data = get_prof_resp.get("profile", {})
    assert prof_data.get("headline") == "Junior Backend Developer"
    assert prof_data.get("experience_months") == 6
    print(f"  ✓ Initial profile retrieved: headline='{prof_data.get('headline')}' exp={prof_data.get('experience_months')}m.")

    # Validation: empty headline -> 422
    inv_head_code, inv_head_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/profile",
        method="PATCH",
        data={"headline": ""},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert inv_head_code == 422, f"Expected 422 on empty headline, got {inv_head_code}: {inv_head_resp}"
    print("  ✓ Empty headline rejected with 422 (INVALID_HEADLINE).")

    # Validation: invalid experience -> 422
    inv_exp_code, inv_exp_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/profile",
        method="PATCH",
        data={"experience_months": -5},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert inv_exp_code == 422, f"Expected 422 on negative experience, got {inv_exp_code}: {inv_exp_resp}"
    print("  ✓ Negative experience rejected with 422 (INVALID_EXPERIENCE).")

    # Valid update: Senior Full-Stack Engineer, Tashkent, 24m exp, updated bio
    patch_code, patch_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/profile",
        method="PATCH",
        data={
            "headline": "Senior Full-Stack Engineer & Async Systems Architect",
            "region": "Samarqand",
            "experience_months": 24,
            "bio": "High-throughput asynchronous Python and React enterprise developer.",
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert patch_code == 200, f"Expected 200 on profile update, got {patch_code}: {patch_resp}"
    assert patch_resp.get("contract_id") == "API-026", f"Contract mismatch: {patch_resp}"
    print(f"  ✓ API-026 profile updated: contract_id={patch_resp.get('contract_id')}")

    # Verify DB state
    with engine.begin() as conn:
        db_prof = conn.execute(
            text("SELECT headline, region, experience_months, bio FROM flexbridge.candidate_profiles WHERE id = :id"),
            {"id": candidate_profile_id}
        ).mappings().one()
        assert db_prof["headline"] == "Senior Full-Stack Engineer & Async Systems Architect"
        assert db_prof["region"] == "Samarqand"
        assert db_prof["experience_months"] == 24
    print("  ✓ Database verified: candidate_profiles row reflects updated values.")

    # --------------------------------------------------------------------------
    # PHASE 5: Skills Catalog Query & Profile Skills Update (API-032)
    # --------------------------------------------------------------------------
    print("\n[Phase 5] Testing Skills Catalog Query & Candidate Skills Update (API-032)...")
    # Catalog query
    skills_cat_code, skills_cat_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/skills?q=PYTHON_{test_suffix}",
        method="GET",
        opener=opener,
    )
    assert skills_cat_code == 200, f"Expected 200 on skills catalog, got {skills_cat_code}: {skills_cat_resp}"
    cat_items = skills_cat_resp.get("items", [])
    assert any(c.get("id") == skill_python_id for c in cat_items), "Seeded Python skill not returned in catalog"
    print(f"  ✓ Skills catalog queried successfully: found {len(cat_items)} matching skills.")

    # Add 2 skills: Python (ADVANCED) and React (INTERMEDIATE)
    add_skills_code, add_skills_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/skills",
        method="PATCH",
        data={
            "skills": [
                {"skill_id": skill_python_id, "level": "ADVANCED"},
                {"skill_id": skill_react_id, "level": "INTERMEDIATE"},
            ],
            "remove_skill_ids": [],
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert add_skills_code == 200, f"Expected 200 on skills update, got {add_skills_code}: {add_skills_resp}"
    assert add_skills_resp.get("contract_id") == "API-032", f"Contract mismatch: {add_skills_resp}"
    print(f"  ✓ API-032 candidate skills added: Python (ADVANCED), React (INTERMEDIATE).")

    # Verify DB candidate_skills
    with engine.begin() as conn:
        db_skills = conn.execute(
            text("SELECT skill_id, level FROM flexbridge.candidate_skills WHERE candidate_id = :cid"),
            {"cid": candidate_profile_id}
        ).mappings().all()
        assert len(db_skills) == 2, f"Expected 2 skills, got {len(db_skills)}"
    print(f"  ✓ Database verified: 2 candidate_skills rows active.")

    # Remove 1 skill: React
    rem_code, rem_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/skills",
        method="PATCH",
        data={
            "skills": [{"skill_id": skill_python_id, "level": "ADVANCED"}],
            "remove_skill_ids": [skill_react_id],
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert rem_code == 200, f"Expected 200 on skill removal, got {rem_code}: {rem_resp}"

    # Verify DB skill removal
    with engine.begin() as conn:
        db_skills_after = conn.execute(
            text("SELECT skill_id, level FROM flexbridge.candidate_skills WHERE candidate_id = :cid"),
            {"cid": candidate_profile_id}
        ).mappings().all()
        assert len(db_skills_after) == 1, f"Expected 1 skill remaining, got {len(db_skills_after)}"
        assert str(db_skills_after[0]["skill_id"]) == skill_python_id
    print("  ✓ Database verified: React skill removed, Python skill retained.")

    # --------------------------------------------------------------------------
    # PHASE 6: Candidate Availability Schedule (API-035 & API-028)
    # --------------------------------------------------------------------------
    print("\n[Phase 6] Testing Candidate Weekly Availability Schedule (API-035 & API-028)...")
    # Fetch initial schedule
    get_sched_code, get_sched_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/availability",
        method="GET",
        opener=opener,
    )
    assert get_sched_code == 200, f"Expected 200 on availability fetch, got {get_sched_code}: {get_sched_resp}"
    assert get_sched_resp.get("contract_id") == "API-035", f"Contract mismatch: {get_sched_resp}"
    print(f"  ✓ API-035 schedule retrieved: contract_id={get_sched_resp.get('contract_id')}")

    # Validation: start_minute >= end_minute -> 422
    inv_min_code, inv_min_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/availability",
        method="PUT",
        data={"rules": [{"weekday": 1, "start_minute": 600, "end_minute": 500}]},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert inv_min_code == 422, f"Expected 422 on invalid minutes, got {inv_min_code}: {inv_min_resp}"
    print("  ✓ Invalid minutes (start >= end) rejected with 422 (INVALID_MINUTES).")

    # Validation: invalid weekday -> 422
    inv_day_code, inv_day_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/availability",
        method="PUT",
        data={"rules": [{"weekday": 9, "start_minute": 540, "end_minute": 1080}]},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert inv_day_code == 422, f"Expected 422 on invalid weekday, got {inv_day_code}: {inv_day_resp}"
    print("  ✓ Invalid weekday (9) rejected with 422 (INVALID_WEEKDAY).")

    # Valid weekly availability schedule:
    # Monday: 09:00 - 14:00 (540..840)
    # Wednesday: 14:00 - 18:00 (840..1080)
    # Friday: 10:00 - 16:00 (600..960)
    put_sched_code, put_sched_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/availability",
        method="PUT",
        data={
            "rules": [
                {"weekday": 1, "start_minute": 540, "end_minute": 840, "valid_from": today_str},
                {"weekday": 3, "start_minute": 840, "end_minute": 1080, "valid_from": today_str},
                {"weekday": 5, "start_minute": 600, "end_minute": 960, "valid_from": today_str},
            ]
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert put_sched_code == 200, f"Expected 200 on put availability, got {put_sched_code}: {put_sched_resp}"
    assert put_sched_resp.get("contract_id") == "API-028", f"Contract mismatch: {put_sched_resp}"
    print(f"  ✓ API-028 availability rules replaced: contract_id={put_sched_resp.get('contract_id')}")

    # Re-query availability via API-035
    verify_sched_code, verify_sched_resp = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/availability",
        method="GET",
        opener=opener,
    )
    assert verify_sched_code == 200, f"Expected 200 on re-fetch, got {verify_sched_code}: {verify_sched_resp}"
    rules_returned = verify_sched_resp.get("rules", [])
    assert len(rules_returned) == 3, f"Expected 3 active rules, got {len(rules_returned)}"
    print(f"  ✓ Re-query verified: all 3 weekly availability rules confirmed active.")

    # --------------------------------------------------------------------------
    # PHASE 7: Anti-CSRF Origin Defense (403)
    # --------------------------------------------------------------------------
    print("\n[Phase 7] Testing Anti-CSRF Origin Defense on Mutating Candidate Endpoints (403)...")
    csrf_tests = [
        ("PATCH", f"{FRONTEND_URL}/api/bff/candidate/profile", {"headline": "Hacked"}),
        ("PATCH", f"{FRONTEND_URL}/api/bff/candidate/skills", {"skills": []}),
        ("PUT", f"{FRONTEND_URL}/api/bff/candidate/availability", {"rules": []}),
    ]

    for method, url, body in csrf_tests:
        code, resp = api_request(
            url,
            method=method,
            data=body,
            headers={"Origin": "https://malicious-phishing-site.com"},
            opener=opener,
        )
        assert code == 403, f"Expected 403 on CSRF attack {method} {url}, got {code}: {resp}"
        assert resp.get("error") == "CSRF_ORIGIN_MISMATCH", f"Unexpected CSRF error: {resp}"
        print(f"  ✓ CSRF attack rejected on {url.replace(FRONTEND_URL, '')} -> 403 (CSRF_ORIGIN_MISMATCH)")

    print("\n" + "=" * 80)
    print("ALL 7 CANDIDATE PROFILE STAGING VERIFICATION PHASES PASSED 100% GREEN!")
    print("Contracts API-026, API-028, API-032, API-035 Fully Operational.")
    print("=" * 80)


if __name__ == "__main__":
    run_candidate_profile_staging_suite()
