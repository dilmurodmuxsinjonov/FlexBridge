#!/usr/bin/env python3
"""
FlexBridge 1.4 Automated Staging Verification Suite:
University Portal: Academic Teacher Assignments, Placement Conclusions & Institution Nomination Queue (FB-160)

Contracts Tested:
- API-104: GET /api/bff/university/assignments (Teacher's own active supervision assignments)
- API-108: GET /api/bff/university/placements/{id}/conclusion-context (Placement conclusion context)
- API-108: POST /api/bff/university/placements/{id}/conclude (Final whole-placement academic decision)
- API-103: GET /api/bff/university/assignment-queue (Coordinator assignment queue & teachers catalog)
- API-102: POST /api/bff/university/placements/{id}/assign-teacher (Nominate supervisor to placement)

Security & Architectural Invariants:
- 401 AUTH_REQUIRED enforced on all unauthenticated requests.
- 403 CSRF_ORIGIN_MISMATCH enforced against cross-site mutating requests.
- PgBouncer transaction-pooling compliance (prepare_threshold=None).
- Zero queries/mutations to pg_live.
"""

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta, date
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor, build_opener
from uuid import uuid4

from sqlalchemy import create_engine, text

from pathlib import Path
from dotenv import dotenv_values
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
    active_opener = opener or build_opener()

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

def run_university_placements_staging_suite():
    print("=" * 80)
    print("Starting FlexBridge 1.4 Staging Suite: University Placements & Conclusions (FB-160)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_suffix = uuid4().hex[:8]
    dummy_uuid = str(uuid4())

    # --------------------------------------------------------------------------
    # PHASE 1: Unauthenticated Rejections (401 AUTH_REQUIRED)
    # --------------------------------------------------------------------------
    print("\n[Phase 1] Verifying unauthenticated rejections (401 AUTH_REQUIRED)...")
    unauth_tests = [
        ("GET", f"{FRONTEND_URL}/api/bff/university/assignments", None),
        ("GET", f"{FRONTEND_URL}/api/bff/university/placements/{dummy_uuid}/conclusion-context", None),
        ("POST", f"{FRONTEND_URL}/api/bff/university/placements/{dummy_uuid}/conclude", {
            "decision": "ACADEMIC_REVIEW_COMPLETE",
            "reason": "Test conclusion unauth",
        }),
        ("GET", f"{FRONTEND_URL}/api/bff/university/assignment-queue", None),
        ("POST", f"{FRONTEND_URL}/api/bff/university/placements/{dummy_uuid}/assign-teacher", {
            "institution_id": dummy_uuid,
            "supervisor_id": dummy_uuid,
            "supervision_id": dummy_uuid,
        }),
    ]

    for method, endpoint, body in unauth_tests:
        code, resp = api_request(endpoint, method=method, data=body)
        assert code == 401, f"Expected 401 for unauth {method} {endpoint}, got {code}: {resp}"
        assert resp.get("error") == "AUTH_REQUIRED", f"Expected error AUTH_REQUIRED, got {resp.get('error')}"
        print(f"  ✓ {method} {endpoint.replace(FRONTEND_URL, '')} -> 401 (Auth required enforced)")

    # --------------------------------------------------------------------------
    # PHASE 2: Database Fixture Seeding via PgBouncer
    # --------------------------------------------------------------------------
    print("\n[Phase 2] Seeding test fixtures into staging database via PgBouncer...")
    now_utc = datetime.now(timezone.utc)
    today_date = now_utc.date()

    # User IDs
    teacher_user_id = str(uuid4())
    teacher_password = "TeacherPass123!"
    teacher_hash = hash_password(teacher_password)

    student_user_id = str(uuid4())
    student_profile_id = str(uuid4())
    student_password = "StudentPass123!"
    student_hash = hash_password(student_password)

    employer_user_id = str(uuid4())
    org_id = str(uuid4())
    org_membership_id = str(uuid4())
    opp_id = str(uuid4())
    opp_rev_id = str(uuid4())
    app_id = str(uuid4())
    attempt_id = str(uuid4())
    offer_id = str(uuid4())

    # Academic Placements
    placement_id = str(uuid4())
    unassigned_placement_id = str(uuid4())
    terms_id = str(uuid4())
    unassigned_terms_id = str(uuid4())
    inst_id = str(uuid4())
    inst_agreement_id = str(uuid4())
    enrollment_id = str(uuid4())
    supervision_id = str(uuid4())
    academic_assignment_id = str(uuid4())
    academic_consent_id = str(uuid4())
    teacher_appointment_id = str(uuid4())
    teacher_membership_id = str(uuid4())
    teacher_grant_id = str(uuid4())
    coordinator_grant_id = str(uuid4())

    purpose = "ENGINEERING_INTERNSHIP"
    scope_snapshot = {
        'institution_id': inst_id,
        'agreement_id': inst_agreement_id,
        'agreement_version': 1,
        'purpose': purpose
    }
    terms_snapshot = {
        'organization_id': org_id,
        'opportunity_id': opp_id,
        'academic_scope': scope_snapshot
    }

    seeded_trigger_tables = [
        "enrollments", "enrollment_origins",
        "student_supervisions", "supervision_origins",
        "placement_intakes", "placement_academic_bindings", "academic_assignments",
        "academic_assignment_proofs", "academic_assignment_consents",
        "placements", "placement_terms", "student_academic_requests",
    ]

    with engine.begin() as conn:
        for t in seeded_trigger_tables:
            conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

    seed_conn = engine.connect()
    seed_trans = seed_conn.begin()
    try:
        clean_file_row = seed_conn.execute(text("SELECT id FROM flexbridge.files WHERE scan_status = 'CLEAN' LIMIT 1")).first()
        assert clean_file_row, "Clean file required in DB"
        file_id = clean_file_row[0]

        # 1. Teacher User
        seed_conn.execute(
                text("""
                    INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                    VALUES (:id, :now, :now, 'Prof. Dilshod Karimov', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
                """),
                {"id": teacher_user_id, "pwd": teacher_hash, "now": now_utc}
            )

        # 2. Student User & Candidate Profile
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Nodirbek Alimov', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": student_user_id, "pwd": student_hash, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, bio, experience_months, visibility)
                VALUES (:id, :now, :now, :uid, 'Talaba Dasturchi', 'Tashkent', 'Dasturiy injiniring talabasi', 8, 'PUBLIC')
            """),
            {"id": student_profile_id, "uid": student_user_id, "now": now_utc}
        )

        # 2b. Second Student for Unassigned Placement Queue
        student_2_user_id = str(uuid4())
        student_2_profile_id = str(uuid4())
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Shaxzod Bekmirzayev', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": student_2_user_id, "pwd": student_hash, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, bio, experience_months, visibility)
                VALUES (:id, :now, :now, :uid, 'Talaba Kiberxavfsizlik', 'Samarkand', 'Kiberxavfsizlik talabasi', 4, 'PUBLIC')
            """),
            {"id": student_2_profile_id, "uid": student_2_user_id, "now": now_utc}
        )

        # 3. Employer & Org
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'HR Lead Tech', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": employer_user_id, "pwd": teacher_hash, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, :now, :now, :tax, 'Univ Partner Org LLC', 'Univ Partner Org', 'Tashkent', 'ACTIVE')
            """),
            {"id": org_id, "tax": f"TAX_{test_suffix}", "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status)
                VALUES (:id, :now, :now, :org_id, :uid, 'ACTIVE')
            """),
            {"id": org_membership_id, "org_id": org_id, "uid": employer_user_id, "now": now_utc}
        )

        # 4. Opportunity
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.opportunities (id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count)
                VALUES (:id, :now, :now, :org_id, 'INTERNSHIP', 'PUBLISHED', 10, 0)
            """),
            {"id": opp_id, "org_id": org_id, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.opportunity_revisions (
                    id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                    region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                    shift_match_mode, snapshot_schema, contract_type
                )
                VALUES (
                    :id, :now, :now, :opp_id, 1, :author_id, 'Software Engineer Intern', 'Amaliyot',
                    'Tashkent', 'HYBRID', 'STUDENT', 'UZS', FALSE, :today, 'FLEXIBLE', 'EXACT', 1, 'INTERNSHIP_AGREEMENT'
                )
            """),
            {"id": opp_rev_id, "opp_id": opp_id, "author_id": employer_user_id, "today": today_date, "now": now_utc}
        )
        seed_conn.execute(
            text("UPDATE flexbridge.opportunities SET current_revision_id = :rev WHERE id = :id"),
            {"rev": opp_rev_id, "id": opp_id}
        )

        # 5. Application & Offer
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.applications (id, created_at, updated_at, opportunity_id, candidate_id, status, version)
                VALUES (:id, :now, :now, :opp_id, :cand_id, 'OFFERED', 1)
            """),
            {"id": app_id, "opp_id": opp_id, "cand_id": student_profile_id, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.application_attempts (
                    id, created_at, updated_at, application_id, opportunity_id, attempt_no, revision_id,
                    profile_snapshot, schedule_result, matching_version, submitted_at, idempotency_key
                )
                VALUES (
                    :attempt_id, :now, :now, :app_id, :opp_id, 1, :rev_id,
                    '{}'::jsonb, '{}'::jsonb, 1, :now, :idem
                )
            """),
            {"attempt_id": attempt_id, "app_id": app_id, "opp_id": opp_id, "rev_id": opp_rev_id, "now": now_utc, "idem": f"idem-{uuid4().hex}"}
        )
        seed_conn.execute(
            text("UPDATE flexbridge.applications SET current_attempt_id = :aid WHERE id = :id"),
            {"aid": attempt_id, "id": app_id}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.offers (
                    id, created_at, updated_at, application_id, attempt_id, revision_id,
                    issuer_membership_id, terms_snapshot, status, expires_at, idempotency_key
                )
                VALUES (:id, :now, :now, :app_id, :attempt_id, :rev_id, :issuer_id, '{}'::jsonb, 'ACCEPTED', :expires, :idem)
            """),
            {
                "id": offer_id, "app_id": app_id, "attempt_id": attempt_id, "rev_id": opp_rev_id,
                "issuer_id": org_membership_id, "expires": now_utc + timedelta(days=30),
                "idem": f"idem-offer-{uuid4().hex}", "now": now_utc
            }
        )

        # 6. Institution & Agreement
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                VALUES (:id, :now, :now, :code, 'Samarqand Davlat Universiteti', 'Samarkand', 'VERIFIED')
            """),
            {"id": inst_id, "code": f"INST_{test_suffix}", "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_agreements (id, created_at, updated_at, institution_id, version, status, valid_from, purposes)
                VALUES (:id, :now, :now, :inst_id, 1, 'ACTIVE', :today, jsonb_build_array('ENGINEERING_INTERNSHIP'))
            """),
            {"id": inst_agreement_id, "inst_id": inst_id, "today": today_date, "now": now_utc}
        )

        # 7. Student Enrollment
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.enrollments (id, created_at, updated_at, candidate_id, institution_id, program, status, start_date)
                VALUES (:id, :now, :now, :cand_id, :inst_id, 'Kiberxavfsizlik', 'VERIFIED', :today)
            """),
            {"id": enrollment_id, "cand_id": student_profile_id, "inst_id": inst_id, "today": today_date, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.enrollment_origins (enrollment_id, created_at, origin, candidate_id, institution_id, actor_user_id, initial_snapshot)
                VALUES (:id, :now, 'LEGACY_IMPORT', :cand_id, :inst_id, :uid, jsonb_build_object('status', 'VERIFIED'))
            """),
            {"id": enrollment_id, "cand_id": student_profile_id, "inst_id": inst_id, "uid": student_user_id, "now": now_utc}
        )

        enrollment_2_id = str(uuid4())
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.enrollments (id, created_at, updated_at, candidate_id, institution_id, program, status, start_date)
                VALUES (:id, :now, :now, :cand_id, :inst_id, 'Kiberxavfsizlik', 'VERIFIED', :today)
            """),
            {"id": enrollment_2_id, "cand_id": student_2_profile_id, "inst_id": inst_id, "today": today_date, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.enrollment_origins (enrollment_id, created_at, origin, candidate_id, institution_id, actor_user_id, initial_snapshot)
                VALUES (:id, :now, 'LEGACY_IMPORT', :cand_id, :inst_id, :uid, jsonb_build_object('status', 'VERIFIED'))
            """),
            {"id": enrollment_2_id, "cand_id": student_2_profile_id, "inst_id": inst_id, "uid": student_2_user_id, "now": now_utc}
        )

        # 8. Teacher Appointment, Membership, TEACHER and COORDINATOR Role Grants
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_appointments (id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, accepted_at)
                VALUES (:id, :now, :now, :inst_id, :uid, :file_id, 'ACTIVE', :today, :now)
            """),
            {"id": teacher_appointment_id, "inst_id": inst_id, "uid": teacher_user_id, "file_id": file_id, "today": today_date, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_memberships (id, created_at, updated_at, institution_id, user_id, status, accepted_at)
                VALUES (:id, :now, :now, :inst_id, :uid, 'ACTIVE', :now)
            """),
            {"id": teacher_membership_id, "inst_id": inst_id, "uid": teacher_user_id, "now": now_utc}
        )

        teacher_role_id = seed_conn.execute(text("SELECT id FROM flexbridge.role_catalog WHERE code = 'TEACHER' AND scope_kind = 'INSTITUTION'")).scalar_one()
        coordinator_role_id = seed_conn.execute(text("SELECT id FROM flexbridge.role_catalog WHERE code = 'COORDINATOR' AND scope_kind = 'INSTITUTION'")).scalar_one()

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_role_grants (id, created_at, updated_at, membership_id, role_id, appointment_id)
                VALUES (:id, :now, :now, :mid, :rid, :aid)
            """),
            {"id": teacher_grant_id, "mid": teacher_membership_id, "rid": teacher_role_id, "aid": teacher_appointment_id, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_role_grants (id, created_at, updated_at, membership_id, role_id, appointment_id)
                VALUES (:id, :now, :now, :mid, :rid, :aid)
            """),
            {"id": coordinator_grant_id, "mid": teacher_membership_id, "rid": coordinator_role_id, "aid": teacher_appointment_id, "now": now_utc}
        )

        # 8b. Teacher 2 for Nomination (Dual-Control)
        teacher_2_user_id = str(uuid4())
        teacher_2_appointment_id = str(uuid4())
        teacher_2_membership_id = str(uuid4())
        teacher_2_grant_id = str(uuid4())

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Katta O''qituvchi Rustam Ergashev', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": teacher_2_user_id, "pwd": teacher_hash, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_appointments (id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, accepted_at)
                VALUES (:id, :now, :now, :inst_id, :uid, :file_id, 'ACTIVE', :today, :now)
            """),
            {"id": teacher_2_appointment_id, "inst_id": inst_id, "uid": teacher_2_user_id, "file_id": file_id, "today": today_date, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_memberships (id, created_at, updated_at, institution_id, user_id, status, accepted_at)
                VALUES (:id, :now, :now, :inst_id, :uid, 'ACTIVE', :now)
            """),
            {"id": teacher_2_membership_id, "inst_id": inst_id, "uid": teacher_2_user_id, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_role_grants (id, created_at, updated_at, membership_id, role_id, appointment_id)
                VALUES (:id, :now, :now, :mid, :rid, :aid)
            """),
            {"id": teacher_2_grant_id, "mid": teacher_2_membership_id, "rid": teacher_role_id, "aid": teacher_2_appointment_id, "now": now_utc}
        )

        # 9. Student Supervision & Origin
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.student_supervisions (
                    id, created_at, updated_at, enrollment_id, coordinator_membership_id, agreement_id,
                    purpose, status, legal_basis, accepted_at, institution_id
                )
                VALUES (:id, :now, :now, :eid, :mid, :aid, :purpose, 'ACTIVE', 'Kafedra qarori', :now, :inst_id)
            """),
            {
                "id": supervision_id, "eid": enrollment_id, "mid": teacher_membership_id,
                "aid": inst_agreement_id, "purpose": purpose, "now": now_utc, "inst_id": inst_id
            }
        )
        supervision_origin_snapshot = {
            "accepted_at": now_utc.isoformat(),
            "enrollment_id": enrollment_id,
            "coordinator_membership_id": teacher_membership_id,
            "agreement_id": inst_agreement_id,
            "purpose": purpose,
            "legal_basis": "Kafedra qarori"
        }
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.supervision_origins (supervision_id, created_at, origin, initial_snapshot)
                VALUES (:id, :now, 'LEGACY_IMPORT', CAST(:snapshot AS jsonb))
            """),
            {
                "id": supervision_id, "now": now_utc,
                "snapshot": json.dumps(supervision_origin_snapshot)
            }
        )

        supervision_2_id = str(uuid4())
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.student_supervisions (
                    id, created_at, updated_at, enrollment_id, coordinator_membership_id, agreement_id,
                    purpose, status, legal_basis, accepted_at, institution_id
                )
                VALUES (:id, :now, :now, :eid, :mid, :aid, :purpose, 'ACTIVE', 'Kafedra qarori 2', :now, :inst_id)
            """),
            {
                "id": supervision_2_id, "eid": enrollment_2_id, "mid": teacher_membership_id,
                "aid": inst_agreement_id, "purpose": purpose, "now": now_utc, "inst_id": inst_id
            }
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.supervision_origins (supervision_id, created_at, origin, initial_snapshot)
                VALUES (:id, :now, 'LEGACY_IMPORT', CAST(:snapshot AS jsonb))
            """),
            {
                "id": supervision_2_id, "now": now_utc,
                "snapshot": json.dumps({
                    "accepted_at": now_utc.isoformat(),
                    "enrollment_id": enrollment_2_id,
                    "coordinator_membership_id": teacher_membership_id,
                    "agreement_id": inst_agreement_id,
                    "purpose": purpose,
                    "legal_basis": "Kafedra qarori 2"
                })
            }
        )

        # 10. Placement (Assigned)
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placements (
                    id, created_at, updated_at, application_id, offer_id, candidate_id,
                    organization_id, enrollment_id, academic_track, status, start_date, end_date, version
                )
                VALUES (:id, :now, :now, :app_id, :offer_id, :cand_id, :org_id, :eid, TRUE, 'ACTIVE', :today, :end_date, 1)
            """),
            {
                "id": placement_id, "app_id": app_id, "offer_id": offer_id, "cand_id": student_profile_id,
                "org_id": org_id, "eid": enrollment_id, "today": today_date, "end_date": today_date + timedelta(days=90),
                "now": now_utc
            }
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_intakes (
                    placement_id, created_at, origin, offer_id, attempt_id, revision_id,
                    academic_required, initial_snapshot, source_snapshot
                )
                VALUES (:pid, :now, 'LEGACY_IMPORT', :offer_id, :attempt_id, :rev_id, TRUE, '{}'::jsonb, '{}'::jsonb)
            """),
            {"pid": placement_id, "offer_id": offer_id, "attempt_id": attempt_id, "rev_id": opp_rev_id, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_terms (
                    id, created_at, updated_at, placement_id, version, schema_version,
                    terms_snapshot, daily_limit_minutes, weekly_limit_minutes, required_minutes
                )
                VALUES (:id, :now, :now, :pid, 1, 1, CAST(:snapshot AS jsonb), 480, 2400, 12000)
            """),
            {"id": terms_id, "pid": placement_id, "snapshot": json.dumps(terms_snapshot), "now": now_utc}
        )
        seed_conn.execute(
            text("UPDATE flexbridge.placements SET current_terms_id = :tid WHERE id = :pid"),
            {"tid": terms_id, "pid": placement_id}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_academic_bindings (
                    placement_id, created_at, origin, institution_id, enrollment_id,
                    supervision_id, terms_id, initial_snapshot, scope_snapshot
                )
                VALUES (:pid, :now, 'LEGACY_IMPORT', :inst_id, :eid, :sid, :tid, CAST(:snapshot AS jsonb), CAST(:scope AS jsonb))
            """),
            {
                "pid": placement_id, "inst_id": inst_id, "eid": enrollment_id, "sid": supervision_id,
                "tid": terms_id, "snapshot": json.dumps(scope_snapshot), "scope": json.dumps(scope_snapshot), "now": now_utc
            }
        )

        # 11. Academic Assignment & Proof & Consent
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.academic_assignments (
                    id, created_at, updated_at, placement_id, teacher_membership_id,
                    supervision_id, assigned_by_id, assigned_at, accepted_at, institution_id
                )
                VALUES (:id, :now, :now, :pid, :mid, :sid, :by_id, :now, :now, :inst_id)
            """),
            {
                "id": academic_assignment_id, "pid": placement_id, "mid": teacher_membership_id,
                "sid": supervision_id, "by_id": teacher_user_id, "now": now_utc, "inst_id": inst_id
            }
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.academic_assignment_proofs (
                    assignment_id, created_at, origin, placement_id, teacher_user_id, teacher_grant_id, teacher_appointment_id,
                    initial_snapshot
                )
                VALUES (:aid, :now, 'LEGACY_IMPORT', :pid, :t_uid, :gid, :app_id, CAST(:snap AS jsonb))
            """),
            {
                "aid": academic_assignment_id, "pid": placement_id, "t_uid": teacher_user_id,
                "gid": teacher_grant_id, "app_id": teacher_appointment_id,
                "snap": json.dumps({"id": academic_assignment_id, "accepted_at": now_utc.isoformat()}),
                "now": now_utc
            }
        )

        teacher_sess_id = str(uuid4())
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.sessions (
                    id, created_at, updated_at, user_id, token_digest, assurance, expires_at, last_seen_at, auth_version
                )
                VALUES (:sess_id, :now, :now, :uid, :digest, 'PASSWORD', :expires, :now, 1)
            """),
            {
                "sess_id": teacher_sess_id, "uid": teacher_user_id, "digest": hashlib.sha256(uuid4().bytes).hexdigest(),
                "expires": now_utc + timedelta(days=7), "now": now_utc
            }
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.academic_assignment_consents (
                    id, created_at, placement_id, assignment_id, terms_id, actor_id, session_id, auth_version,
                    teacher_grant_id, teacher_appointment_id, idempotency_key, request_fingerprint, receipt
                )
                VALUES (
                    :cid, :now, :pid, :aid, :tid, :uid, :sess_id, 1,
                    :gid, :app_id, :idem, :fingerprint, CAST(:receipt AS jsonb)
                )
            """),
            {
                "cid": academic_consent_id, "pid": placement_id, "aid": academic_assignment_id,
                "tid": terms_id, "uid": teacher_user_id, "sess_id": teacher_sess_id, "gid": teacher_grant_id,
                "app_id": teacher_appointment_id, "receipt": json.dumps({"consent_id": academic_consent_id}),
                "idem": f"idem-consent-{uuid4().hex}", "fingerprint": "0" * 64, "now": now_utc
            }
        )

        # 12. Seed Second Unassigned Placement in Assignment Queue (PLANNED status, no binding)
        unassigned_app_id = str(uuid4())
        unassigned_offer_id = str(uuid4())
        request_id = str(uuid4())

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.applications (id, created_at, updated_at, opportunity_id, candidate_id, status, version)
                VALUES (:id, :now, :now, :opp_id, :cand_id, 'OFFERED', 1)
            """),
            {"id": unassigned_app_id, "opp_id": opp_id, "cand_id": student_2_profile_id, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.offers (
                    id, created_at, updated_at, application_id, attempt_id, revision_id,
                    issuer_membership_id, terms_snapshot, status, expires_at, idempotency_key
                )
                VALUES (:id, :now, :now, :app_id, :attempt_id, :rev_id, :issuer_id, '{}'::jsonb, 'ACCEPTED', :expires, :idem)
            """),
            {
                "id": unassigned_offer_id, "app_id": unassigned_app_id, "attempt_id": attempt_id, "rev_id": opp_rev_id,
                "issuer_id": org_membership_id, "expires": now_utc + timedelta(days=30),
                "idem": f"idem-unassigned-{uuid4().hex}", "now": now_utc
            }
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placements (
                    id, created_at, updated_at, application_id, offer_id, candidate_id,
                    organization_id, enrollment_id, academic_track, status, start_date, end_date, version
                )
                VALUES (:id, :now, :now, :app_id, :offer_id, :cand_id, :org_id, NULL, FALSE, 'PLANNED', :today, :end_date, 1)
            """),
            {
                "id": unassigned_placement_id, "app_id": unassigned_app_id, "offer_id": unassigned_offer_id, "cand_id": student_2_profile_id,
                "org_id": org_id, "today": today_date, "end_date": today_date + timedelta(days=90),
                "now": now_utc
            }
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_intakes (
                    placement_id, created_at, origin, offer_id, attempt_id, revision_id,
                    academic_required, initial_snapshot, source_snapshot
                )
                VALUES (:pid, :now, 'LEGACY_IMPORT', :offer_id, :attempt_id, :rev_id, TRUE, '{}'::jsonb, '{}'::jsonb)
            """),
            {"pid": unassigned_placement_id, "offer_id": unassigned_offer_id, "attempt_id": attempt_id, "rev_id": opp_rev_id, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_terms (
                    id, created_at, updated_at, placement_id, version, schema_version,
                    terms_snapshot, daily_limit_minutes, weekly_limit_minutes, required_minutes
                )
                VALUES (:id, :now, :now, :pid, 1, 1, CAST(:snapshot AS jsonb), 480, 2400, 12000)
            """),
            {"id": unassigned_terms_id, "pid": unassigned_placement_id, "snapshot": json.dumps(terms_snapshot), "now": now_utc}
        )
        seed_conn.execute(
            text("UPDATE flexbridge.placements SET current_terms_id = :tid WHERE id = :pid"),
            {"tid": unassigned_terms_id, "pid": unassigned_placement_id}
        )

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.student_academic_requests (
                    id, created_at, placement_id, revision, institution_id, enrollment_id, terms_id,
                    actor_id, session_id, auth_version, idempotency_key, request_fingerprint, receipt
                )
                VALUES (
                    :id, :now, :pid, 1, :inst_id, :eid, :tid,
                    :uid, :sess_id, 1, :idem, :fingerprint, '{}'::jsonb
                )
            """),
            {
                "id": request_id, "now": now_utc, "pid": unassigned_placement_id, "inst_id": inst_id,
                "eid": enrollment_2_id, "tid": unassigned_terms_id, "uid": student_2_user_id,
                "sess_id": teacher_sess_id, "idem": f"idem-req-{uuid4().hex}", "fingerprint": "0" * 64
            }
        )
        seed_trans.commit()
    except Exception:
        seed_trans.rollback()
        raise
    finally:
        seed_conn.close()

        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))

    print("  ✓ Fixtures successfully seeded via PgBouncer.")

    # --------------------------------------------------------------------------
    # PHASE 3: Teacher Authentication & Assignments Listing (API-104)
    # --------------------------------------------------------------------------
    print("\n[Phase 3] Authenticating Teacher & Testing Assignments Listing (API-104)...")
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))

    login_code, login_resp = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": teacher_user_id, "password": teacher_password},
        headers={"Origin": FRONTEND_URL},
        opener=opener
    )
    assert login_code == 200, f"Expected 200 login, got {login_code}: {login_resp}"
    print(f"  ✓ Teacher logged in successfully: roles={login_resp.get('roles')}")

    # Elevate session assurance in flexbridge.sessions to MFA (required by academic coordinator/governance authority)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE flexbridge.sessions SET assurance = 'MFA' WHERE user_id = :uid"),
            {"uid": teacher_user_id}
        )
    print("  ✓ Teacher session assurance elevated to MFA in flexbridge.sessions.")

    # Call API-104: GET /api/bff/university/assignments
    assign_code, assign_resp = api_request(
        f"{FRONTEND_URL}/api/bff/university/assignments",
        method="GET",
        opener=opener
    )
    assert assign_code == 200, f"Expected 200 for assignments, got {assign_code}: {assign_resp}"
    assert assign_resp.get("contract_id") == "API-104", f"Expected contract_id API-104, got {assign_resp.get('contract_id')}"
    items = assign_resp.get("items", [])
    found_assignment = next((a for a in items if a.get("id") == academic_assignment_id), None)
    assert found_assignment, f"Seeded assignment {academic_assignment_id} not found in {items}"
    print(f"  ✓ API-104 returned {len(items)} assignments (seeded assignment {academic_assignment_id} verified).")

    # --------------------------------------------------------------------------
    # PHASE 4: Placement Academic Conclusion Context (API-108-CONTEXT)
    # --------------------------------------------------------------------------
    print("\n[Phase 4] Fetching Academic Decision Context via BFF (API-108-CONTEXT)...")
    ctx_code, ctx_resp = api_request(
        f"{FRONTEND_URL}/api/bff/university/placements/{placement_id}/conclusion-context?academic_assignment_id={academic_assignment_id}",
        method="GET",
        opener=opener
    )
    assert ctx_code == 200, f"Expected 200 for conclusion context, got {ctx_code}: {ctx_resp}"
    assert ctx_resp.get("contract_id") == "API-108-CONTEXT", f"Expected API-108-CONTEXT, got {ctx_resp.get('contract_id')}"
    assert ctx_resp.get("placement_id") == placement_id
    assert ctx_resp.get("academic_assignment_id") == academic_assignment_id
    assert ctx_resp.get("terms_id") == terms_id
    assert ctx_resp.get("version") == 1
    assert "basis_digest" in ctx_resp
    basis_digest = ctx_resp["basis_digest"]
    print(f"  ✓ API-108 context retrieved: terms_id={terms_id} version=1 basis_digest={basis_digest[:16]}...")

    # --------------------------------------------------------------------------
    # PHASE 5: Conclude Placement Decision Workflow (API-108)
    # --------------------------------------------------------------------------
    print("\n[Phase 5] Testing Whole-Placement Academic Conclusion (API-108)...")

    # 1. Validation check: Invalid decision value rejected with 422
    bad_dec_code, bad_dec_resp = api_request(
        f"{FRONTEND_URL}/api/bff/university/placements/{placement_id}/conclude",
        method="POST",
        data={
            "academic_assignment_id": academic_assignment_id,
            "terms_id": terms_id,
            "version": 1,
            "expected_basis_digest": basis_digest,
            "decision": "INVALID_VALUE",
            "reason": "Test conclusion invalid decision",
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener
    )
    assert bad_dec_code == 422, f"Expected 422 for invalid decision, got {bad_dec_code}: {bad_dec_resp}"
    print(f"  ✓ Invalid decision value rejected with 422 ({bad_dec_resp.get('error')})")

    # 2. Validation check: Empty reason rejected with 422
    bad_reason_code, bad_reason_resp = api_request(
        f"{FRONTEND_URL}/api/bff/university/placements/{placement_id}/conclude",
        method="POST",
        data={
            "academic_assignment_id": academic_assignment_id,
            "terms_id": terms_id,
            "version": 1,
            "expected_basis_digest": basis_digest,
            "decision": "ACADEMIC_REVIEW_COMPLETE",
            "reason": "   ",
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener
    )
    assert bad_reason_code == 422, f"Expected 422 for empty reason, got {bad_reason_code}: {bad_reason_resp}"
    print(f"  ✓ Empty reason rejected with 422 ({bad_reason_resp.get('error')})")

    # 3. Valid Decision Submission (ACADEMIC_REVISION_REQUIRED)
    conclude_code, conclude_resp = api_request(
        f"{FRONTEND_URL}/api/bff/university/placements/{placement_id}/conclude",
        method="POST",
        data={
            "academic_assignment_id": academic_assignment_id,
            "terms_id": terms_id,
            "version": 1,
            "expected_basis_digest": basis_digest,
            "decision": "ACADEMIC_REVISION_REQUIRED",
            "reason": "Talabaning kundalik hisobotlari va amaliyot dasturi bo'yicha qayta ko'rib chiqish talab etiladi.",
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener
    )
    assert conclude_code in (200, 201), f"Expected 200/201 for conclusion, got {conclude_code}: {conclude_resp}"
    assert conclude_resp.get("contract_id") == "API-108", f"Expected contract_id API-108, got {conclude_resp.get('contract_id')}"
    print(f"  ✓ API-108 conclusion successfully submitted: decision=ACADEMIC_REVISION_REQUIRED.")

    # 4. Verify in Database
    with engine.connect() as conn:
        proof_row = conn.execute(
            text("""
                SELECT decision_id, basis_digest, receipt FROM flexbridge.academic_decision_proofs
                WHERE assignment_id = :aid
            """),
            {"aid": academic_assignment_id}
        ).mappings().first()
        assert proof_row, "academic_decision_proofs row must exist in DB"
        receipt = proof_row["receipt"] or {}
        assert receipt.get("decision") == "ACADEMIC_REVISION_REQUIRED"
        assert proof_row["basis_digest"] == basis_digest
        print(f"  ✓ Database verified: academic_decision_proofs records decision={receipt.get('decision')}.")

    # --------------------------------------------------------------------------
    # PHASE 6: Coordinator Assignment Queue & Teacher Nomination (API-103 & API-102)
    # --------------------------------------------------------------------------
    print("\n[Phase 6] Testing Coordinator Assignment Queue & Teacher Nomination (API-103 & API-102)...")
    queue_code, queue_resp = api_request(
        f"{FRONTEND_URL}/api/bff/university/assignment-queue?institution_id={inst_id}",
        method="GET",
        opener=opener
    )
    assert queue_code == 200, f"Expected 200 for assignment queue, got {queue_code}: {queue_resp}"
    assert queue_resp.get("contract_id") == "API-103", f"Expected API-103, got {queue_resp.get('contract_id')}"
    q_items = queue_resp.get("items", [])
    teachers = queue_resp.get("teachers", [])
    assert len(teachers) > 0, f"Expected active teachers list, got {teachers}"
    unassigned_item = next((i for i in q_items if i.get("placement_id") == unassigned_placement_id), None)
    assert unassigned_item, f"Unassigned placement {unassigned_placement_id} not found in queue: {q_items}"
    print(f"  ✓ API-103 queue returned {len(q_items)} items and {len(teachers)} teachers.")

    # 1. Self-assignment rejection check (Dual-Control 4-Eyes)
    self_assign_code, self_assign_resp = api_request(
        f"{FRONTEND_URL}/api/bff/university/placements/{unassigned_placement_id}/assign-teacher",
        method="POST",
        data={
            "institution_id": inst_id,
            "supervisor_id": teacher_membership_id,
            "supervision_id": supervision_2_id,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener
    )
    assert self_assign_code == 403, f"Expected 403 for self-assignment, got {self_assign_code}: {self_assign_resp}"
    print(f"  ✓ Self-assignment rejected with 403 ({self_assign_resp.get('error')}) - Dual-Control enforced.")

    # 2. Nominate teacher 2 to unassigned placement (API-102)
    nom_code, nom_resp = api_request(
        f"{FRONTEND_URL}/api/bff/university/placements/{unassigned_placement_id}/assign-teacher",
        method="POST",
        data={
            "institution_id": inst_id,
            "supervisor_id": teacher_2_membership_id,
            "supervision_id": supervision_2_id,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener
    )
    assert nom_code in (200, 201), f"Expected 200/201 for teacher nomination, got {nom_code}: {nom_resp}"
    assert nom_resp.get("contract_id") == "API-102", f"Expected contract_id API-102, got {nom_resp.get('contract_id')}"
    print(f"  ✓ API-102 teacher nominated successfully for placement {unassigned_placement_id}.")

    # --------------------------------------------------------------------------
    # PHASE 7: Anti-CSRF Origin Defense on Mutating Endpoints (403)
    # --------------------------------------------------------------------------
    print("\n[Phase 7] Testing Anti-CSRF Origin Defense on Mutating University Endpoints (403)...")
    csrf_tests = [
        ("POST", f"{FRONTEND_URL}/api/bff/university/placements/{placement_id}/conclude", {
            "academic_assignment_id": academic_assignment_id,
            "terms_id": terms_id,
            "version": 1,
            "expected_basis_digest": basis_digest,
            "decision": "ACADEMIC_REVISION_REQUIRED",
            "reason": "CSRF attack attempt",
        }),
        ("POST", f"{FRONTEND_URL}/api/bff/university/placements/{unassigned_placement_id}/assign-teacher", {
            "institution_id": inst_id,
            "supervisor_id": teacher_2_membership_id,
            "supervision_id": supervision_2_id,
        }),
    ]

    for method, endpoint, body in csrf_tests:
        code, resp = api_request(
            endpoint,
            method=method,
            data=body,
            headers={"Origin": "https://attacker-malicious-domain.com"},
            opener=opener
        )
        assert code == 403, f"Expected 403 CSRF rejection for {method} {endpoint}, got {code}: {resp}"
        assert resp.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got {resp.get('error')}"
        print(f"  ✓ CSRF attack rejected on {endpoint.replace(FRONTEND_URL, '')} -> 403 (CSRF_ORIGIN_MISMATCH)")

    print("\n" + "=" * 80)
    print("ALL 7 UNIVERSITY PLACEMENTS & CONCLUSIONS STAGING PHASES PASSED 100% GREEN!")
    print("Contracts API-102, API-103, API-104, API-108 Fully Operational.")
    print("=" * 80)

if __name__ == "__main__":
    try:
        run_university_placements_staging_suite()
    except Exception as exc:
        print(f"\n[FATAL ERROR] {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
