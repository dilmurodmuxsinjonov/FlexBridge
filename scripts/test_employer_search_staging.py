#!/usr/bin/env python3
"""FlexBridge 1.4 Staging Verification Suite: Employer Candidate Search Hub (Milestone 2 / API-087).

Verifies the 10 mandatory phases:
Phase 1: Unauthenticated request rejected (401 AUTH_REQUIRED)
Phase 2: Non-employer role rejected (403 EMPLOYER_ROLE_REQUIRED)
Phase 3: Employer role authorized (200 API-087)
Phase 4: Skill filtering with ANY mode
Phase 5: Skill filtering with ALL mode & level constraint
Phase 6: Region filtering
Phase 7: Shift & weekday schedule compatibility matching
Phase 8: Experience range filtering
Phase 9: Composite multi-facet search
Phase 10: Keyset pagination & privacy protection (private profiles excluded, PII masked)

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None.
ZERO queries to pg_live.
"""

from __future__ import annotations

import base64

import hashlib
import json
import os
import secrets
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

# Path resolution
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load infra staging environment variables
infra_env = dotenv_values(REPO_ROOT / "infra" / ".env")
postgres_user = infra_env.get("POSTGRES_USER", "flexbridge_owner")
postgres_pass = infra_env.get("POSTGRES_PASSWORD")
postgres_db = infra_env.get("POSTGRES_DB", "flexbridge")

if not postgres_pass:
    raise RuntimeError("POSTGRES_PASSWORD must be configured in infra/.env")

db_url = URL.create(
    "postgresql+psycopg",
    username=postgres_user,
    password=postgres_pass,
    host="127.0.0.1",
    port=5432,
    database=postgres_db,
).render_as_string(hide_password=False)

os.environ["DATABASE_URL"] = db_url
os.environ["FLEXBRIDGE_DATABASE_URL"] = db_url
for k in ("MFA_ENCRYPTION_KEY", "AUTH_HMAC_KEY", "PAYMENT_WEBHOOK_SECRET"):
    if infra_env.get(k):
        os.environ[k] = infra_env[k]

from fastapi.testclient import TestClient
from app.main import app
from app.services.auth import hash_password


def run_employer_search_staging_suite() -> None:
    print("=" * 80)
    print("FLEXBRIDGE 1.4 STAGING SUITE: Employer Portal Search Hub (M2 / API-087)")
    print("Database: PgBouncer at 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    client = TestClient(app)

    # -------------------------------------------------------------------------
    # PHASE 1: Unauthenticated request rejected (401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n[Phase 1] Testing unauthenticated access guard (401)...")
    res1 = client.get("/api/v1/employer/candidates/search")
    assert res1.status_code == 401, f"Expected 401, got {res1.status_code}: {res1.text}"
    body1 = res1.json()
    assert body1.get("detail", {}).get("code") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED: {body1}"
    print("  ✓ Unauthenticated search request strictly rejected with 401 AUTH_REQUIRED.")

    # -------------------------------------------------------------------------
    # Database Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n[Setup] Seeding test fixtures in PostgreSQL via PgBouncer...")
    engine = create_engine(
        db_url,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_suffix = uuid4().hex[:8]
    now_ts = datetime.now(timezone.utc)
    today = now_ts.date()

    # 1. Employer Organization & HR User
    org_id = str(uuid4())
    hr_user_id = str(uuid4())
    candidate_user_id = str(uuid4())
    hr_membership_id = str(uuid4())

    hr_session_token = secrets.token_urlsafe(32)
    hr_session_digest = hashlib.sha256(hr_session_token.encode()).hexdigest()

    candidate_session_token = secrets.token_urlsafe(32)
    candidate_session_digest = hashlib.sha256(candidate_session_token.encode()).hexdigest()

    # Candidates:
    # Candidate A: Senior Python/FastAPI in Toshkent shahri, 24 mo exp, MORNING shift Mon-Fri, Verified TATU student
    cand_a_user_id = str(uuid4())
    cand_a_profile_id = str(uuid4())

    # Candidate B: Frontend React in Samarqand, 10 mo exp, AFTERNOON shift Tue/Thu, Pending student
    cand_b_user_id = str(uuid4())
    cand_b_profile_id = str(uuid4())

    # Candidate C: Junior Python in Toshkent shahri, 3 mo exp, FULL_DAY shift Sat/Sun
    cand_c_user_id = str(uuid4())
    cand_c_profile_id = str(uuid4())

    # Candidate D: Private profile in Toshkent shahri (MUST BE EXCLUDED)
    cand_d_user_id = str(uuid4())
    cand_d_profile_id = str(uuid4())

    institution_id = str(uuid4())
    case_id = str(uuid4())

    seeded_trigger_tables = ["enrollments", "candidate_skills"]

    try:
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

        with engine.begin() as conn:
            # Get role catalog IDs
            hr_role_id = conn.execute(
                text("SELECT id FROM flexbridge.role_catalog WHERE code = 'HR' AND scope_kind = 'ORG' LIMIT 1")
            ).scalar_one()
    
            # Seed Users
            conn.execute(
                text("""
                    INSERT INTO flexbridge.users (
                        id, created_at, updated_at, display_name, status, password_hash,
                        locale, timezone, adult_declared_at, auth_version
                    ) VALUES
                    (:hr_uid, :ts, :ts, 'Employer HR Manager', 'ACTIVE', :ph, 'uz', 'Asia/Tashkent', :ts, 1),
                    (:c_uid, :ts, :ts, 'Only Candidate User', 'ACTIVE', :ph, 'uz', 'Asia/Tashkent', :ts, 1),
                    (:ca_uid, :ts, :ts, 'Azizbek Rahimov', 'ACTIVE', :ph, 'uz', 'Asia/Tashkent', :ts, 1),
                    (:cb_uid, :ts, :ts, 'Malika Karimova', 'ACTIVE', :ph, 'uz', 'Asia/Tashkent', :ts, 1),
                    (:cc_uid, :ts, :ts, 'Jasur Aliyev', 'ACTIVE', :ph, 'uz', 'Asia/Tashkent', :ts, 1),
                    (:cd_uid, :ts, :ts, 'Secret Person', 'ACTIVE', :ph, 'uz', 'Asia/Tashkent', :ts, 1)
                """),
                {
                    "hr_uid": hr_user_id,
                    "c_uid": candidate_user_id,
                    "ca_uid": cand_a_user_id,
                    "cb_uid": cand_b_user_id,
                    "cc_uid": cand_c_user_id,
                    "cd_uid": cand_d_user_id,
                    "ph": hash_password("SecureStagingPass123!"),
                    "ts": now_ts,
                },
            )
    
            # Seed Organization & HR Membership & Grant
            conn.execute(
                text("""
                    INSERT INTO flexbridge.organizations (
                        id, created_at, updated_at, tax_id, legal_name, public_name, region, status
                    ) VALUES (
                        :org_id, :ts, :ts, :tax_id, :lname, 'TechCorp', 'Toshkent shahri', 'ACTIVE'
                    )
                """),
                {
                    "org_id": org_id,
                    "lname": f"TechCorp Solutions {test_suffix}",
                    "tax_id": f"tin_{test_suffix}",
                    "ts": now_ts,
                },
            )
    
            conn.execute(
                text("""
                    INSERT INTO flexbridge.org_memberships (
                        id, created_at, updated_at, organization_id, user_id, status, accepted_at
                    ) VALUES (:mid, :ts, :ts, :org_id, :uid, 'ACTIVE', :ts)
                """),
                {"mid": hr_membership_id, "org_id": org_id, "uid": hr_user_id, "ts": now_ts},
            )
    
            conn.execute(
                text("""
                    INSERT INTO flexbridge.org_role_grants (
                        id, created_at, updated_at, membership_id, role_id, granted_by_id
                    ) VALUES (:gid, :ts, :ts, :mid, :rid, :uid)
                """),
                {
                    "gid": str(uuid4()),
                    "mid": hr_membership_id,
                    "rid": hr_role_id,
                    "uid": hr_user_id,
                    "ts": now_ts,
                },
            )
    
            # Seed Sessions
            conn.execute(
                text("""
                    INSERT INTO flexbridge.sessions (
                        id, created_at, updated_at, user_id, token_digest, expires_at, last_seen_at, assurance, auth_version
                    ) VALUES
                    (:hr_sid, :ts, :ts, :hr_uid, :hr_dig, :exp, :ts, 'PASSWORD', 1),
                    (:c_sid, :ts, :ts, :c_uid, :c_dig, :exp, :ts, 'PASSWORD', 1)
                """),
                {
                    "hr_sid": str(uuid4()),
                    "hr_uid": hr_user_id,
                    "hr_dig": hr_session_digest,
                    "c_sid": str(uuid4()),
                    "c_uid": candidate_user_id,
                    "c_dig": candidate_session_digest,
                    "exp": now_ts + timedelta(hours=12),
                    "ts": now_ts,
                },
            )
    
            # Seed Candidate Profiles
            conn.execute(
                text("""
                    INSERT INTO flexbridge.candidate_profiles (
                        id, created_at, updated_at, user_id, headline, region, bio,
                        experience_months, visibility
                    ) VALUES
                    (:ca_id, :ts, :ts, :ca_uid, 'Senior Python & FastAPI Engineer', 'Toshkent shahri',
                     'Fullstack and backend architect with Python and FastAPI.', 24, 'PUBLIC'),
                    (:cb_id, :ts - interval '1 hour', :ts - interval '1 hour', :cb_uid, 'Frontend React Developer', 'Samarqand',
                     'Passionate UI/UX specialist with React and TypeScript.', 10, 'PUBLIC'),
                    (:cc_id, :ts - interval '2 hours', :ts - interval '2 hours', :cc_uid, 'Junior Python Developer', 'Toshkent shahri',
                     'Motivated student developer.', 3, 'PUBLIC'),
                    (:cd_id, :ts - interval '3 hours', :ts - interval '3 hours', :cd_uid, 'Private Secret Developer', 'Toshkent shahri',
                     'Stealth candidate.', 36, 'PRIVATE')
                """),
                {
                    "ca_id": cand_a_profile_id,
                    "ca_uid": cand_a_user_id,
                    "cb_id": cand_b_profile_id,
                    "cb_uid": cand_b_user_id,
                    "cc_id": cand_c_profile_id,
                    "cc_uid": cand_c_user_id,
                    "cd_id": cand_d_profile_id,
                    "cd_uid": cand_d_user_id,
                    "ts": now_ts,
                },
            )
    
            # Ensure Skills in catalog
            def get_or_create_skill(code: str, name_uz: str) -> str:
                existing = conn.execute(
                    text("SELECT id FROM flexbridge.skills WHERE code = :code LIMIT 1"),
                    {"code": code},
                ).scalar_one_or_none()
                if existing:
                    return str(existing)
                new_id = str(uuid4())
                conn.execute(
                    text("""
                        INSERT INTO flexbridge.skills (
                            id, created_at, updated_at, code, name_uz, name_ru, aliases, active
                        ) VALUES (:id, :ts, :ts, :code, :uz, :ru, '[]'::jsonb, true)
                    """),
                    {"id": new_id, "code": code, "uz": name_uz, "ru": name_uz, "ts": now_ts},
                )
                return new_id
    
            skill_py_id = get_or_create_skill("python", "Python")
            skill_fa_id = get_or_create_skill("fastapi", "FastAPI")
            skill_pg_id = get_or_create_skill("postgresql", "PostgreSQL")
            skill_react_id = get_or_create_skill("react", "React")
            skill_ts_id = get_or_create_skill("typescript", "TypeScript")
    
            conn.execute(
                text("""
                    INSERT INTO flexbridge.verification_cases (
                        id, created_at, updated_at, requester_id, candidate_id, kind,
                        status, current_revision, due_at, decided_at
                    ) VALUES (
                        :case_id, :ts, :ts, :uid, :cid, 'CANDIDATE_SKILL',
                        'APPROVED', 1, :ts, :ts
                    )
                """),
                {
                    "case_id": case_id,
                    "uid": cand_a_user_id,
                    "cid": cand_a_profile_id,
                    "ts": now_ts,
                },
            )
    
            # Candidate Skills
            # A: python (ADVANCED, verified), fastapi (ADVANCED, verified), postgresql (INTERMEDIATE)
            # B: react (INTERMEDIATE, verified), typescript (BEGINNER)
            # C: python (BEGINNER)
            # D: python (ADVANCED)
            conn.execute(
                text("""
                    INSERT INTO flexbridge.candidate_skills (
                        id, created_at, updated_at, candidate_id, skill_id, level, verification_case_id
                    ) VALUES
                    (:s1, :ts, :ts, :ca_id, :py_id, 'ADVANCED', :case_id),
                    (:s2, :ts, :ts, :ca_id, :fa_id, 'ADVANCED', :case_id),
                    (:s3, :ts, :ts, :ca_id, :pg_id, 'INTERMEDIATE', NULL),
                    (:s4, :ts, :ts, :cb_id, :react_id, 'INTERMEDIATE', :case_id),
                    (:s5, :ts, :ts, :cb_id, :ts_id, 'BEGINNER', NULL),
                    (:s6, :ts, :ts, :cc_id, :py_id, 'BEGINNER', NULL),
                    (:s7, :ts, :ts, :cd_id, :py_id, 'ADVANCED', :case_id)
                """),
                {
                    "s1": str(uuid4()),
                    "s2": str(uuid4()),
                    "s3": str(uuid4()),
                    "s4": str(uuid4()),
                    "s5": str(uuid4()),
                    "s6": str(uuid4()),
                    "s7": str(uuid4()),
                    "ca_id": cand_a_profile_id,
                    "cb_id": cand_b_profile_id,
                    "cc_id": cand_c_profile_id,
                    "cd_id": cand_d_profile_id,
                    "py_id": skill_py_id,
                    "fa_id": skill_fa_id,
                    "pg_id": skill_pg_id,
                    "react_id": skill_react_id,
                    "ts_id": skill_ts_id,
                    "case_id": case_id,
                    "ts": now_ts,
                },
            )
    
            # Seed Availability Rules
            # Cand A: Mon-Fri (1..5), 480-780 (08:00 - 13:00, MORNING) -> 5h/day * 5 = 25h/week
            for day in range(1, 6):
                conn.execute(
                    text("""
                        INSERT INTO flexbridge.availability_rules (
                            id, created_at, updated_at, candidate_id, weekday,
                            start_minute, end_minute, valid_from, timezone, is_active
                        ) VALUES (:id, :ts, :ts, :cid, :w, 480, 780, :vf, 'Asia/Tashkent', true)
                    """),
                    {
                        "id": str(uuid4()),
                        "cid": cand_a_profile_id,
                        "w": day,
                        "vf": today - timedelta(days=30),
                        "ts": now_ts,
                    },
                )
    
            # Cand B: Tue, Thu (2, 4), 780-1080 (13:00 - 18:00, AFTERNOON) -> 5h/day * 2 = 10h/week
            for day in (2, 4):
                conn.execute(
                    text("""
                        INSERT INTO flexbridge.availability_rules (
                            id, created_at, updated_at, candidate_id, weekday,
                            start_minute, end_minute, valid_from, timezone, is_active
                        ) VALUES (:id, :ts, :ts, :cid, :w, 780, 1080, :vf, 'Asia/Tashkent', true)
                    """),
                    {
                        "id": str(uuid4()),
                        "cid": cand_b_profile_id,
                        "w": day,
                        "vf": today - timedelta(days=30),
                        "ts": now_ts,
                    },
                )
    
            # Cand C: Sat, Sun (6, 7), 540-1080 (09:00 - 18:00, FULL_DAY) -> 9h/day * 2 = 18h/week
            for day in (6, 7):
                conn.execute(
                    text("""
                        INSERT INTO flexbridge.availability_rules (
                            id, created_at, updated_at, candidate_id, weekday,
                            start_minute, end_minute, valid_from, timezone, is_active
                        ) VALUES (:id, :ts, :ts, :cid, :w, 540, 1080, :vf, 'Asia/Tashkent', true)
                    """),
                    {
                        "id": str(uuid4()),
                        "cid": cand_c_profile_id,
                        "w": day,
                        "vf": today - timedelta(days=30),
                        "ts": now_ts,
                    },
                )
    
            # Seed Institution and University Enrollment for Cand A
            conn.execute(
                text("""
                    INSERT INTO flexbridge.institutions (
                        id, created_at, updated_at, registry_code, name, region, status
                    ) VALUES (
                        :inst_id, :ts, :ts, :reg, 'TATU - Axborot Texnologiyalari Universiteti', 'Toshkent shahri', 'ACTIVE'
                    ) ON CONFLICT (registry_code) DO NOTHING
                """),
                {
                    "inst_id": institution_id,
                    "reg": f"TATU-{test_suffix}",
                    "ts": now_ts,
                },
            )
    
            real_inst_id = conn.execute(
                text("SELECT id FROM flexbridge.institutions WHERE registry_code = :reg"),
                {"reg": f"TATU-{test_suffix}"},
            ).scalar_one_or_none() or institution_id
    
            conn.execute(
                text("""
                    INSERT INTO flexbridge.enrollments (
                        id, created_at, updated_at, candidate_id, institution_id, program,
                        student_ref_digest, start_date, end_date, status
                    ) VALUES (
                        :eid, :ts, :ts, :cid, :inst_id, 'Dasturiy Injiniring',
                        :sref, :sdate, :edate, 'VERIFIED'
                    )
                """),
                {
                    "eid": str(uuid4()),
                    "cid": cand_a_profile_id,
                    "inst_id": real_inst_id,
                    "sref": f"digest_{test_suffix}",
                    "sdate": today - timedelta(days=365),
                    "edate": today + timedelta(days=365),
                    "ts": now_ts,
                },
            )
    
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))
    
        print("  ✓ Database fixtures seeded successfully via PgBouncer.")
    
        hr_headers = {"Authorization": f"Bearer {hr_session_token}"}
        candidate_headers = {"Authorization": f"Bearer {candidate_session_token}"}
    
        # -------------------------------------------------------------------------
        # PHASE 2: Non-employer role rejected (403 EMPLOYER_ROLE_REQUIRED)
        # -------------------------------------------------------------------------
        print("\n[Phase 2] Testing non-employer authorization rejection (403)...")
        res2 = client.get("/api/v1/employer/candidates/search", headers=candidate_headers)
        assert res2.status_code == 403, f"Expected 403, got {res2.status_code}: {res2.text}"
        body2 = res2.json()
        assert body2.get("detail", {}).get("code") == "EMPLOYER_ROLE_REQUIRED", f"Invalid detail: {body2}"
        print("  ✓ Candidate-only user correctly blocked with 403 EMPLOYER_ROLE_REQUIRED.")
    
        # -------------------------------------------------------------------------
        # PHASE 3: Employer role authorized (200 API-087)
        # -------------------------------------------------------------------------
        print("\n[Phase 3] Testing authorized employer talent search (200)...")
        res3 = client.get("/api/v1/employer/candidates/search", headers=hr_headers)
        assert res3.status_code == 200, f"Expected 200, got {res3.status_code}: {res3.text}"
        body3 = res3.json()
        assert body3.get("contract_id") == "API-087", f"Invalid contract_id: {body3}"
        assert isinstance(body3.get("items"), list), "items must be a list"
        assert body3.get("total") >= 3, f"Expected at least 3 seeded candidates, got {body3.get('total')}"
        print(f"  ✓ Employer search succeeded. Total candidates found: {body3['total']}.")
    
        # -------------------------------------------------------------------------
        # PHASE 4: Skill filtering with ANY mode
        # -------------------------------------------------------------------------
        print("\n[Phase 4] Testing skill filtering with ANY mode...")
        res4 = client.get(
            "/api/v1/employer/candidates/search?skills=python&skills=react&skill_match_mode=ANY",
            headers=hr_headers,
        )
        assert res4.status_code == 200, f"Error: {res4.text}"
        items4 = res4.json().get("items", [])
        found_cids4 = {item["candidate_id"] for item in items4}
        assert cand_a_profile_id in found_cids4, "Candidate A (Python) should match ANY mode"
        assert cand_b_profile_id in found_cids4, "Candidate B (React) should match ANY mode"
        assert cand_c_profile_id in found_cids4, "Candidate C (Python) should match ANY mode"
    
        # Adversarial probe: safe UUID parsing against non-hex 36-char string with hyphens
        res4_fuzz = client.get(
            "/api/v1/employer/candidates/search?skills=12345678-1234-1234-1234-12345678901z&skills=------------------------------------",
            headers=hr_headers,
        )
        assert res4_fuzz.status_code == 200, f"Expected 200 on UUID fuzzing, got {res4_fuzz.status_code}"
        print("  ✓ ANY mode correctly returned candidates matching at least one requested skill.")
    
        # -------------------------------------------------------------------------
        # PHASE 5: Skill filtering with ALL mode & level constraint
        # -------------------------------------------------------------------------
        print("\n[Phase 5] Testing skill filtering with ALL mode & level constraint...")
        res5 = client.get(
            "/api/v1/employer/candidates/search?skills=python&skills=fastapi&skill_match_mode=ALL&min_skill_level=ADVANCED",
            headers=hr_headers,
        )
        assert res5.status_code == 200, f"Error: {res5.text}"
        items5 = res5.json().get("items", [])
        found_cids5 = {item["candidate_id"] for item in items5}
        assert cand_a_profile_id in found_cids5, "Candidate A should match ALL ADVANCED"
        assert cand_b_profile_id not in found_cids5, "Candidate B does not have Python+FastAPI"
        assert cand_c_profile_id not in found_cids5, "Candidate C is BEGINNER, should be filtered by ADVANCED"
    
        # Deduplication test in ALL mode: duplicate skills params should not inflate having threshold
        res5_dedup = client.get(
            "/api/v1/employer/candidates/search?skills=python&skills=python&skill_match_mode=ALL",
            headers=hr_headers,
        )
        assert res5_dedup.status_code == 200, f"Expected 200 on dedup, got {res5_dedup.status_code}"
        found_cids5_dedup = {item["candidate_id"] for item in res5_dedup.json().get("items", [])}
        assert cand_a_profile_id in found_cids5_dedup, "Candidate A should match deduplicated python"
        assert cand_c_profile_id in found_cids5_dedup, "Candidate C should match deduplicated python"
        print("  ✓ ALL mode with ADVANCED level correctly isolated Candidate A.")
    
        # -------------------------------------------------------------------------
        # PHASE 6: Region filtering
        # -------------------------------------------------------------------------
        print("\n[Phase 6] Testing regional territory filtering...")
        # Samarqand search
        res6_sam = client.get("/api/v1/employer/candidates/search?region=Samarqand", headers=hr_headers)
        assert res6_sam.status_code == 200
        items6_sam = res6_sam.json().get("items", [])
        cids_sam = {item["candidate_id"] for item in items6_sam}
        assert cand_b_profile_id in cids_sam, "Candidate B in Samarqand should match"
        assert cand_a_profile_id not in cids_sam, "Candidate A in Toshkent must not match Samarqand"
    
        # Toshkent search (explicit limit=100 for reliable test fixture matching)
        res6_tsh = client.get("/api/v1/employer/candidates/search?region=Toshkent shahri&limit=100", headers=hr_headers)
        assert res6_tsh.status_code == 200
        items6_tsh = res6_tsh.json().get("items", [])
        cids_tsh = {item["candidate_id"] for item in items6_tsh}
        assert cand_a_profile_id in cids_tsh
        assert cand_c_profile_id in cids_tsh
        assert cand_b_profile_id not in cids_tsh
        print("  ✓ Regional filtering accurately partitioned candidates across territories.")
    
        # -------------------------------------------------------------------------
        # PHASE 7: Shift & weekday schedule compatibility matching
        # -------------------------------------------------------------------------
        print("\n[Phase 7] Testing shift preset & weekday schedule matching...")
        res7 = client.get(
            "/api/v1/employer/candidates/search?shift=MORNING&weekdays=1&weekdays=2&weekdays=3",
            headers=hr_headers,
        )
        assert res7.status_code == 200, f"Error: {res7.text}"
        items7 = res7.json().get("items", [])
        cids7 = {item["candidate_id"] for item in items7}
        assert cand_a_profile_id in cids7, "Candidate A has MORNING shift on weekdays 1, 2, 3"
        assert cand_b_profile_id not in cids7, "Candidate B has AFTERNOON shift"
        assert cand_c_profile_id not in cids7, "Candidate C is weekend only"
    
        # Verify schedule compatibility score payload for Candidate A
        cand_a_item = next(item for item in items7 if item["candidate_id"] == cand_a_profile_id)
        assert cand_a_item["schedule_match"]["score_percent"] == 100
        assert cand_a_item["schedule_match"]["labor_code_compliant"] is True
        assert cand_a_item["schedule_summary"]["total_weekly_hours"] == 25.0
    
        # Candidate C O'zR MK 118 daily hour limit check (9h/day > 8h/day statutory cap)
        res7_c = client.get("/api/v1/employer/candidates/search?region=Toshkent shahri&limit=100", headers=hr_headers)
        assert res7_c.status_code == 200
        cand_c_item = next((item for item in res7_c.json().get("items", []) if item["candidate_id"] == cand_c_profile_id), None)
        assert cand_c_item is not None, "Candidate C should be present in search"
        assert cand_c_item["schedule_match"]["labor_code_compliant"] is False, "Candidate C with 9h/day must not be compliant with MK 118"
        assert "Kunlik" in cand_c_item["schedule_match"]["details"], "Details must mention daily limit overrun"
        print("  ✓ Schedule shift and weekday matching evaluated compatibility and O'zR MK 118 compliance.")
    
        # -------------------------------------------------------------------------
        # PHASE 8: Experience range filtering
        # -------------------------------------------------------------------------
        print("\n[Phase 8] Testing experience range filtering (min/max months)...")
        res8_min = client.get("/api/v1/employer/candidates/search?experience_min_months=12", headers=hr_headers)
        assert res8_min.status_code == 200
        cids8_min = {item["candidate_id"] for item in res8_min.json().get("items", [])}
        assert cand_a_profile_id in cids8_min, "Candidate A (24 mo) >= 12 mo"
        assert cand_b_profile_id not in cids8_min, "Candidate B (10 mo) < 12 mo"
        assert cand_c_profile_id not in cids8_min, "Candidate C (3 mo) < 12 mo"
    
        res8_max = client.get("/api/v1/employer/candidates/search?experience_max_months=5", headers=hr_headers)
        assert res8_max.status_code == 200
        cids8_max = {item["candidate_id"] for item in res8_max.json().get("items", [])}
        assert cand_c_profile_id in cids8_max, "Candidate C (3 mo) <= 5 mo"
        assert cand_a_profile_id not in cids8_max, "Candidate A (24 mo) > 5 mo"
        print("  ✓ Experience month range filters functioning correctly.")
    
        # -------------------------------------------------------------------------
        # PHASE 9: Composite multi-facet search
        # -------------------------------------------------------------------------
        print("\n[Phase 9] Testing composite multi-facet search...")
        res9 = client.get(
            "/api/v1/employer/candidates/search?q=FastAPI&region=Toshkent shahri&skills=python",
            headers=hr_headers,
        )
        assert res9.status_code == 200, f"Error: {res9.text}"
        body9 = res9.json()
        assert body9["total"] >= 1
        items9 = body9["items"]
        assert items9[0]["candidate_id"] == cand_a_profile_id
    
        # Verify facets structure
        facets = body9.get("facets", {})
        assert "regions" in facets
        assert "skills" in facets
        assert "shifts" in facets
        assert facets["regions"].get("Toshkent shahri", 0) >= 1
        print("  ✓ Composite search matched candidate and generated facets.")
    
        # -------------------------------------------------------------------------
        # PHASE 10: Keyset pagination & privacy protection
        # -------------------------------------------------------------------------
        print("\n[Phase 10] Testing keyset pagination and privacy protection...")
        # Page 1 with limit=1
        res10_p1 = client.get("/api/v1/employer/candidates/search?limit=1", headers=hr_headers)
        assert res10_p1.status_code == 200
        body10_p1 = res10_p1.json()
        assert len(body10_p1["items"]) == 1
        cursor = body10_p1["next_cursor"]
        assert cursor is not None, "next_cursor should be returned when more items exist"
    
        # Page 2 with cursor
        res10_p2 = client.get(f"/api/v1/employer/candidates/search?limit=1&cursor={cursor}", headers=hr_headers)
        assert res10_p2.status_code == 200
        body10_p2 = res10_p2.json()
        assert len(body10_p2["items"]) == 1
        assert body10_p2["items"][0]["candidate_id"] != body10_p1["items"][0]["candidate_id"], "No overlapping items"
    
        # Privacy Protection Check
        # Candidate D is PRIVATE, must never appear in any search listing
        res10_all = client.get("/api/v1/employer/candidates/search?limit=100", headers=hr_headers)
        all_items = res10_all.json().get("items", [])
        all_cids = {item["candidate_id"] for item in all_items}
        assert cand_d_profile_id not in all_cids, "CRITICAL: Private profile (Candidate D) leaked into search!"
    
        # PII Masking Check: display_name should be formatted with surname initial (e.g. 'Azizbek R.')
        for item in all_items:
            if item["candidate_id"] == cand_a_profile_id:
                assert item["display_name"] == "Azizbek R.", f"Expected masked name, got: {item['display_name']}"
    
        # Candidate Detail API check
        res_detail = client.get(f"/api/v1/employer/candidates/{cand_a_profile_id}", headers=hr_headers)
        assert res_detail.status_code == 200
        detail_body = res_detail.json()
        assert detail_body["candidate_id"] == cand_a_profile_id
        assert detail_body["display_name"] == "Azizbek R."
        assert len(detail_body["skills"]) >= 2
        assert detail_body["university"]["institution_name"].startswith("TATU")
        assert detail_body["availability"]["total_weekly_hours"] == 25.0
    
        # Malformed cursor check (invalid UUID in base64 payload should return 422 INVALID_CURSOR, not 500)
        bad_cursor = base64.urlsafe_b64encode(b"2026-11-15T12:00:00|not-a-valid-uuid").decode("utf-8")
        res10_bad = client.get(f"/api/v1/employer/candidates/search?cursor={bad_cursor}", headers=hr_headers)
        assert res10_bad.status_code == 422, f"Expected 422 on invalid cursor UUID, got {res10_bad.status_code}"
        assert res10_bad.json().get("detail", {}).get("code") == "INVALID_CURSOR"
    
        print("  ✓ Keyset pagination cursor seamless, private profiles excluded, and PII masked.")
    
        print("\n" + "=" * 80)
        print("ALL 10 EMPLOYER SEARCH STAGING PHASES COMPLETED AND VERIFIED GREEN [PASS]")
        print("=" * 80)
    finally:
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

            conn.execute(
                text("DELETE FROM flexbridge.availability_rules WHERE candidate_id = ANY(:cids)"),
                {"cids": [cand_a_profile_id, cand_b_profile_id, cand_c_profile_id, cand_d_profile_id]},
            )
            conn.execute(
                text("DELETE FROM flexbridge.candidate_skills WHERE candidate_id = ANY(:cids)"),
                {"cids": [cand_a_profile_id, cand_b_profile_id, cand_c_profile_id, cand_d_profile_id]},
            )
            conn.execute(
                text("DELETE FROM flexbridge.enrollments WHERE candidate_id = ANY(:cids)"),
                {"cids": [cand_a_profile_id, cand_b_profile_id, cand_c_profile_id, cand_d_profile_id]},
            )
            conn.execute(
                text("DELETE FROM flexbridge.verification_cases WHERE id = :case_id OR candidate_id = ANY(:cids)"),
                {"case_id": case_id, "cids": [cand_a_profile_id, cand_b_profile_id, cand_c_profile_id, cand_d_profile_id]},
            )
            conn.execute(
                text("DELETE FROM flexbridge.candidate_profiles WHERE id = ANY(:cids)"),
                {"cids": [cand_a_profile_id, cand_b_profile_id, cand_c_profile_id, cand_d_profile_id]},
            )
            conn.execute(
                text("DELETE FROM flexbridge.org_role_grants WHERE membership_id = :mid"),
                {"mid": hr_membership_id},
            )
            conn.execute(
                text("DELETE FROM flexbridge.org_memberships WHERE id = :mid"),
                {"mid": hr_membership_id},
            )
            conn.execute(
                text("DELETE FROM flexbridge.organizations WHERE id = :org_id"),
                {"org_id": org_id},
            )
            conn.execute(
                text("DELETE FROM flexbridge.institutions WHERE registry_code = :reg"),
                {"reg": f"TATU-{test_suffix}"},
            )
            conn.execute(
                text("DELETE FROM flexbridge.sessions WHERE user_id = ANY(:uids)"),
                {"uids": [hr_user_id, candidate_user_id, cand_a_user_id, cand_b_user_id, cand_c_user_id, cand_d_user_id]},
            )
            conn.execute(
                text("DELETE FROM flexbridge.users WHERE id = ANY(:uids)"),
                {"uids": [hr_user_id, candidate_user_id, cand_a_user_id, cand_b_user_id, cand_c_user_id, cand_d_user_id]},
            )

            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))


if __name__ == "__main__":
    run_employer_search_staging_suite()
