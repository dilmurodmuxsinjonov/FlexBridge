#!/usr/bin/env python3
"""FlexBridge 1.4 University Academic Log Reviews & Evaluation Workflow Verification Suite (Issue #152).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected for University BFF endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Fixture seeding in Staging PostgreSQL via PgBouncer (127.0.0.1:5432/flexbridge).
Phase 3: University Teacher authentication via Next.js BFF (/api/auth/login) with encrypted HttpOnly cookie.
Phase 4: Teacher inspects academic review queue via BFF (API-105: GET /api/bff/university/review-queue).
Phase 5: Teacher inspects log revision detail via BFF (API-106: GET /api/bff/university/log-revisions/[revision]/academic).
Phase 6: Teacher submits review decision via BFF (API-107: POST /api/bff/university/log-revisions/[revision]/academic-reviews).
Phase 7: Cross-site CSRF rejection on review submission (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 8: Review idempotency verification & review queue clearance verification.

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import http.cookiejar
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from dotenv import dotenv_values

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
    call_opener = opener or urllib.request.build_opener()

    try:
        with call_opener.open(req) as response:
            resp_headers = {k.lower(): v for k, v in response.headers.items()}
            raw_body = response.read().decode("utf-8")
            parsed_data = json.loads(raw_body) if raw_body else {}
            return response.status, parsed_data, resp_headers
    except urllib.error.HTTPError as err:
        resp_headers = {k.lower(): v for k, v in err.headers.items()}
        raw_body = err.read().decode("utf-8")
        try:
            parsed_data = json.loads(raw_body)
        except Exception:
            parsed_data = {"raw": raw_body}
        return err.code, parsed_data, resp_headers


def main():
    print("=" * 80)
    print("FLEXBRIDGE 1.4 UNIVERSITY ACADEMIC LOG REVIEWS VERIFICATION (FB-152)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        connect_args={"prepare_threshold": None},
        pool_pre_ping=True,
    )

    test_suffix = uuid4().hex[:8]
    dummy_revision_id = str(uuid4())

    # =========================================================================
    # PHASE 1: Unauthenticated access rejected (HTTP 401 AUTH_REQUIRED)
    # =========================================================================
    print("\n--- PHASE 1: Unauthenticated BFF Endpoint Access Rejection ---")
    anon_opener = urllib.request.build_opener()

    endpoints_to_test = [
        ("GET", f"{FRONTEND_URL}/api/bff/university/review-queue", None),
        ("GET", f"{FRONTEND_URL}/api/bff/university/log-revisions/{dummy_revision_id}/academic", None),
        ("POST", f"{FRONTEND_URL}/api/bff/university/log-revisions/{dummy_revision_id}/academic-reviews", {
            "decision": "REVIEWED",
            "comment": "Unauth attempt",
        }),
    ]

    for method, url, body in endpoints_to_test:
        status, data, _ = make_request(url, method=method, data=body, opener=anon_opener)
        assert status == 401, f"Expected 401 for unauthenticated {method} {url}, got {status}: {data}"
        err_code = data.get("error")
        assert err_code == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {err_code} in {data}"
        print(f"✓ {method} {url} correctly rejected with 401 {err_code}")

    print("Phase 1 Passed: All University BFF endpoints reject unauthenticated requests.")

    # =========================================================================
    # PHASE 2: Fixture Seeding via PgBouncer
    # =========================================================================
    print("\n--- PHASE 2: Seeding Academic Review Fixtures via PgBouncer ---")

    teacher_id = str(uuid4())
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

    file_id = str(uuid4())
    inst_id = str(uuid4())
    inst_agreement_id = str(uuid4())
    enrollment_id = str(uuid4())
    supervision_id = str(uuid4())
    placement_id = str(uuid4())
    terms_id = str(uuid4())
    teacher_membership_id = str(uuid4())
    teacher_appointment_id = str(uuid4())
    teacher_grant_id = str(uuid4())
    academic_assignment_id = str(uuid4())
    academic_consent_id = str(uuid4())

    daily_log_id = str(uuid4())
    revision_id = str(uuid4())
    task_entry_1_id = str(uuid4())
    task_entry_2_id = str(uuid4())

    now_ts = datetime.now(timezone.utc)
    today_date = date.today()
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
        "placement_intakes", "placement_academic_bindings", "academic_assignments",
        "academic_assignment_proofs", "academic_assignment_consents",
        "placements", "placement_terms",
        "daily_logs", "log_revisions", "log_task_entries",
    ]

    with engine.begin() as conn:
        for t in seeded_trigger_tables:
            conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

    try:
        with engine.begin() as conn:
            # 1. Teacher User
            conn.execute(text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :ts, :ts, 'Dotsent Alisher Qodirov', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
            """), {"id": teacher_id, "pwd": teacher_hash, "ts": now_ts})

            # 2. Student User & Candidate Profile
            conn.execute(text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :ts, :ts, 'Jasurbek Oripov', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
            """), {"id": student_user_id, "pwd": student_hash, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, experience_months, visibility)
                VALUES (:id, :ts, :ts, :uid, 'Software Engineering 4-kurs talabasi', 'Tashkent', 24, 'PUBLIC')
            """), {"id": student_profile_id, "uid": student_user_id, "ts": now_ts})

            # 3. Employer User, Organization & Org Membership
            conn.execute(text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :ts, :ts, 'Employer HR Lead', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
            """), {"id": employer_user_id, "pwd": teacher_hash, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, :ts, :ts, :tax_id, 'Texno Mir MCHJ', 'Texno Mir', 'Tashkent', 'ACTIVE')
            """), {"id": org_id, "tax_id": f"TAX_{test_suffix}", "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status)
                VALUES (:id, :ts, :ts, :org_id, :uid, 'ACTIVE')
            """), {"id": org_membership_id, "org_id": org_id, "uid": employer_user_id, "ts": now_ts})

            # 4. Opportunity & Revision 1 (INTERNSHIP / INTERNSHIP_AGREEMENT)
            conn.execute(text("""
                INSERT INTO flexbridge.opportunities (id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count)
                VALUES (:id, :ts, :ts, :org_id, 'INTERNSHIP', 'PUBLISHED', 10, 0)
            """), {"id": opp_id, "org_id": org_id, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.opportunity_revisions (
                    id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                    region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                    shift_match_mode, snapshot_schema, contract_type
                )
                VALUES (
                    :id, :ts, :ts, :opp_id, 1, :author_id, 'Full-Stack Dasturchi Stajyor', 'Amaliyot dasturi',
                    'Tashkent', 'HYBRID', 'STUDENT', 'UZS', FALSE, :today, 'FLEXIBLE',
                    'EXACT', 1, 'INTERNSHIP_AGREEMENT'
                )
            """), {"id": opp_rev_id, "opp_id": opp_id, "author_id": employer_user_id, "today": today_date, "ts": now_ts})

            conn.execute(text("""
                UPDATE flexbridge.opportunities SET current_revision_id = :rev WHERE id = :id
            """), {"rev": opp_rev_id, "id": opp_id})

            # 5. Application, Attempt & Offer
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

            # 6. Institution & Appointment Document File
            clean_file_row = conn.execute(text("SELECT id FROM flexbridge.files WHERE scan_status = 'CLEAN' LIMIT 1")).first()
            assert clean_file_row, "At least one clean scanned file must exist in DB"
            file_id = clean_file_row[0]

            conn.execute(text("""
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                VALUES (:id, :ts, :ts, :reg, 'Toshkent Axborot Texnologiyalari Universiteti', 'Tashkent', 'VERIFIED')
            """), {"id": inst_id, "reg": f"INST_{test_suffix}", "ts": now_ts})

            # 7. Institution Agreement
            conn.execute(text("""
                INSERT INTO flexbridge.institution_agreements (id, created_at, updated_at, institution_id, version, status, valid_from, purposes)
                VALUES (:id, :ts, :ts, :inst_id, 1, 'ACTIVE', :today, jsonb_build_array('ENGINEERING_INTERNSHIP'))
            """), {"id": inst_agreement_id, "inst_id": inst_id, "today": today_date, "ts": now_ts})

            # 8. Enrollment & Enrollment Origin (Legacy Import baseline)
            conn.execute(text("""
                INSERT INTO flexbridge.enrollments (id, created_at, updated_at, candidate_id, institution_id, program, status, start_date)
                VALUES (:id, :ts, :ts, :cand_id, :inst_id, 'Dasturiy Injiniring', 'VERIFIED', :today)
            """), {"id": enrollment_id, "cand_id": student_profile_id, "inst_id": inst_id, "today": today_date, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.enrollment_origins (enrollment_id, created_at, origin, candidate_id, institution_id, actor_user_id, initial_snapshot)
                VALUES (:id, :ts, 'LEGACY_IMPORT', :cand_id, :inst_id, :actor_id, jsonb_build_object('status', 'VERIFIED'))
            """), {"id": enrollment_id, "cand_id": student_profile_id, "inst_id": inst_id, "actor_id": student_user_id, "ts": now_ts})

            # 9. Teacher Appointment, Membership & TEACHER Role Grant
            conn.execute(text("""
                INSERT INTO flexbridge.institution_appointments (id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, accepted_at)
                VALUES (:id, :ts, :ts, :inst_id, :uid, :file_id, 'ACTIVE', :today, :ts)
            """), {"id": teacher_appointment_id, "inst_id": inst_id, "uid": teacher_id, "file_id": file_id, "today": today_date, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.institution_memberships (id, created_at, updated_at, institution_id, user_id, status, accepted_at)
                VALUES (:id, :ts, :ts, :inst_id, :uid, 'ACTIVE', :ts)
            """), {"id": teacher_membership_id, "inst_id": inst_id, "uid": teacher_id, "ts": now_ts})

            teacher_role_row = conn.execute(text("""
                SELECT id FROM flexbridge.role_catalog WHERE code = 'TEACHER' AND scope_kind = 'INSTITUTION'
            """)).first()
            assert teacher_role_row, "TEACHER role must exist in role_catalog"
            teacher_role_id = teacher_role_row[0]

            conn.execute(text("""
                INSERT INTO flexbridge.institution_role_grants (id, created_at, updated_at, membership_id, role_id, appointment_id)
                VALUES (:id, :ts, :ts, :mid, :rid, :aid)
            """), {"id": teacher_grant_id, "mid": teacher_membership_id, "rid": teacher_role_id, "aid": teacher_appointment_id, "ts": now_ts})

            # 10. Student Supervision & Supervision Origin
            conn.execute(text("""
                INSERT INTO flexbridge.student_supervisions (
                    id, created_at, updated_at, enrollment_id, coordinator_membership_id, agreement_id,
                    purpose, status, legal_basis, accepted_at, institution_id
                )
                VALUES (:id, :ts, :ts, :eid, :mid, :aid, :purpose, 'ACTIVE', 'Kafedra bayonnomasi asosida', :ts, :inst_id)
            """), {
                "id": supervision_id, "eid": enrollment_id, "mid": teacher_membership_id,
                "aid": inst_agreement_id, "purpose": purpose, "ts": now_ts, "inst_id": inst_id
            })

            supervision_origin_snapshot = {
                'accepted_at': now_ts.isoformat(),
                'enrollment_id': enrollment_id,
                'coordinator_membership_id': teacher_membership_id,
                'agreement_id': inst_agreement_id,
                'purpose': purpose,
                'legal_basis': 'Kafedra bayonnomasi asosida'
            }
            conn.execute(text("""
                INSERT INTO flexbridge.supervision_origins (supervision_id, created_at, origin, initial_snapshot)
                VALUES (:id, :ts, 'LEGACY_IMPORT', CAST(:snapshot AS jsonb))
            """), {
                "id": supervision_id, "snapshot": json.dumps(supervision_origin_snapshot), "ts": now_ts
            })

            # 11. Placement
            conn.execute(text("""
                INSERT INTO flexbridge.placements (
                    id, created_at, updated_at, application_id, offer_id, candidate_id,
                    organization_id, enrollment_id, academic_track, status, start_date, end_date, version
                )
                VALUES (:id, :ts, :ts, :app_id, :offer_id, :cand_id, :org_id, :eid, TRUE, 'ACTIVE', :today, :end_date, 1)
            """), {
                "id": placement_id, "app_id": app_id, "offer_id": offer_id, "cand_id": student_profile_id,
                "org_id": org_id, "eid": enrollment_id, "today": today_date, "end_date": today_date + timedelta(days=90),
                "ts": now_ts
            })

            # 11b. Placement Intake (needed for placement_academic_bindings FK)
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

            # 12. Placement Terms
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

            # 13. Placement Academic Binding
            conn.execute(text("""
                INSERT INTO flexbridge.placement_academic_bindings (
                    placement_id, created_at, origin, institution_id, enrollment_id,
                    supervision_id, terms_id, initial_snapshot, scope_snapshot
                )
                VALUES (:pid, :ts, 'LEGACY_IMPORT', :inst_id, :eid, :sid, :tid, CAST(:snapshot AS jsonb), CAST(:scope AS jsonb))
            """), {
                "pid": placement_id, "inst_id": inst_id, "eid": enrollment_id, "sid": supervision_id,
                "tid": terms_id, "snapshot": json.dumps(scope_snapshot), "scope": json.dumps(scope_snapshot), "ts": now_ts
            })

            # 14. Academic Assignment & Proof & Consent
            conn.execute(text("""
                INSERT INTO flexbridge.academic_assignments (
                    id, created_at, updated_at, placement_id, teacher_membership_id,
                    supervision_id, assigned_by_id, assigned_at, accepted_at, institution_id
                )
                VALUES (:id, :ts, :ts, :pid, :mid, :sid, :by_id, :ts, :ts, :inst_id)
            """), {
                "id": academic_assignment_id, "pid": placement_id, "mid": teacher_membership_id,
                "sid": supervision_id, "by_id": teacher_id, "ts": now_ts, "inst_id": inst_id
            })

            # Session for teacher consent
            teacher_sess_id = str(uuid4())
            conn.execute(text("""
                INSERT INTO flexbridge.sessions (
                    id, created_at, updated_at, user_id, token_digest, assurance, expires_at, last_seen_at, auth_version
                )
                VALUES (
                    :sess_id, :ts, :ts, :uid, :digest, 'PASSWORD', :expires, :ts, 1
                )
            """), {
                "sess_id": teacher_sess_id, "uid": teacher_id, "digest": hashlib.sha256(uuid4().bytes).hexdigest(),
                "expires": now_ts + timedelta(days=7), "ts": now_ts
            })

            conn.execute(text("""
                INSERT INTO flexbridge.academic_assignment_proofs (
                    assignment_id, created_at, origin, placement_id, teacher_user_id, teacher_grant_id, teacher_appointment_id,
                    initial_snapshot
                )
                VALUES (
                    :aid, :ts, 'LEGACY_IMPORT', :pid, :t_uid, :gid, :app_id,
                    CAST(:snap AS jsonb)
                )
            """), {
                "aid": academic_assignment_id, "pid": placement_id, "t_uid": teacher_id,
                "gid": teacher_grant_id, "app_id": teacher_appointment_id,
                "snap": json.dumps({"id": academic_assignment_id, "accepted_at": now_ts.isoformat()}),
                "ts": now_ts
            })

            conn.execute(text("""
                INSERT INTO flexbridge.academic_assignment_consents (
                    id, created_at, placement_id, assignment_id, terms_id, actor_id, session_id, auth_version,
                    teacher_grant_id, teacher_appointment_id, idempotency_key, request_fingerprint, receipt
                )
                VALUES (
                    :cid, :ts, :pid, :aid, :tid, :uid, :sess_id, 1,
                    :gid, :app_id, :idem, :fingerprint,
                    CAST(:receipt AS jsonb)
                )
            """), {
                "cid": academic_consent_id, "pid": placement_id, "aid": academic_assignment_id,
                "tid": terms_id, "uid": teacher_id, "sess_id": teacher_sess_id, "gid": teacher_grant_id,
                "app_id": teacher_appointment_id, "receipt": json.dumps({"consent_id": academic_consent_id}),
                "idem": f"idem-consent-{uuid4().hex[:12]}", "fingerprint": "0" * 64, "ts": now_ts
            })

            # 15. Daily Log & Submitted Log Revision
            conn.execute(text("""
                INSERT INTO flexbridge.daily_logs (id, created_at, updated_at, placement_id, local_date, version)
                VALUES (:id, :ts, :ts, :pid, :today, 1)
            """), {"id": daily_log_id, "pid": placement_id, "today": today_date, "ts": now_ts})

            conn.execute(text("""
                INSERT INTO flexbridge.log_revisions (
                    id, created_at, updated_at, daily_log_id, revision, terms_id, author_id, day_type, summary,
                    total_minutes, status, submitted_at, idempotency_key
                )
                VALUES (
                    :id, :ts, :ts, :dlid, 1, :tid, :author_id, 'WORKDAY',
                    'Backend mikroservis arxitekturasi va API kontraktlarini ishlab chiqdim.',
                    420, 'SUBMITTED', :ts, :idem
                )
            """), {
                "id": revision_id, "dlid": daily_log_id, "tid": terms_id, "author_id": student_user_id,
                "ts": now_ts, "idem": f"idem-logrev-{uuid4().hex[:12]}"
            })

            conn.execute(text("""
                UPDATE flexbridge.daily_logs SET current_revision_id = :rid WHERE id = :dlid
            """), {"rid": revision_id, "dlid": daily_log_id})

            # 16. Log Task Entries
            conn.execute(text("""
                INSERT INTO flexbridge.log_task_entries (id, created_at, updated_at, revision_id, result_text, minutes, start_minute, end_minute)
                VALUES
                    (:id1, :ts, :ts, :rid, 'FastAPI va SQLAlchemy 2.0 bilan RBAC xavfsizlik qatlamini yaratdim', 240, 540, 780),
                    (:id2, :ts, :ts, :rid, 'Next.js 16 frontend integratsiyasini qildim va integratsion testlarni yozdim', 180, 780, 960)
            """), {"id1": task_entry_1_id, "id2": task_entry_2_id, "rid": revision_id, "ts": now_ts})

    finally:
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))

    print(f"✓ Fixtures successfully created:")
    print(f"  Teacher User ID: {teacher_id}")
    print(f"  Student User ID: {student_user_id}")
    print(f"  Placement ID: {placement_id}")
    print(f"  Log Revision ID: {revision_id}")
    print("Phase 2 Passed: DB fixtures seeded via PgBouncer.")

    # =========================================================================
    # PHASE 3: Teacher Login via Next.js BFF (/api/auth/login)
    # =========================================================================
    print("\n--- PHASE 3: University Teacher Authentication via Next.js BFF ---")
    cookie_jar = http.cookiejar.CookieJar()
    teacher_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    login_status, login_data, login_headers = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": teacher_id, "password": teacher_password},
        headers={"Origin": FRONTEND_URL},
        opener=teacher_opener,
    )

    assert login_status == 200, f"Expected 200 on login, got {login_status}: {login_data}"
    assert login_data.get("ok") is True, f"Login payload should be ok: {login_data}"
    assert login_data.get("user_id") == teacher_id, f"User ID mismatch in {login_data}"
    assert "TEACHER" in login_data.get("roles", []), f"TEACHER role expected in {login_data}"
    print(f"✓ Teacher authenticated: roles={login_data.get('roles')}")

    # =========================================================================
    # PHASE 4: Inspect Academic Review Queue (API-105)
    # =========================================================================
    print("\n--- PHASE 4: Fetch Academic Review Queue via BFF (API-105) ---")
    queue_status, queue_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/review-queue",
        method="GET",
        opener=teacher_opener,
    )

    assert queue_status == 200, f"Expected 200 on review-queue, got {queue_status}: {queue_data}"
    assert queue_data.get("ok") is True, f"Expected ok: true, got {queue_data}"
    items = queue_data.get("items", [])
    assert len(items) >= 1, f"Expected at least 1 item in review queue, got {len(items)}"

    matching_item = next((it for it in items if it.get("id") == revision_id), None)
    assert matching_item is not None, f"Revision {revision_id} not found in queue items: {items}"
    assert matching_item.get("daily_log_id") == daily_log_id
    assert matching_item.get("placement_id") == placement_id
    assert matching_item.get("purpose") == purpose
    assert matching_item.get("student_name") == "Jasurbek Oripov"
    print(f"✓ Queue item verified: Revision ID={revision_id}, Student='{matching_item.get('student_name')}', Date={matching_item.get('local_date')}")
    print("Phase 4 Passed: Review queue contract (API-105) fully satisfied.")

    # =========================================================================
    # PHASE 5: Inspect Academic Revision Detail (API-106)
    # =========================================================================
    print("\n--- PHASE 5: Inspect Academic Revision Detail via BFF (API-106) ---")
    detail_status, detail_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/log-revisions/{revision_id}/academic",
        method="GET",
        opener=teacher_opener,
    )

    assert detail_status == 200, f"Expected 200 on revision detail, got {detail_status}: {detail_data}"
    assert detail_data.get("id") == revision_id
    assert detail_data.get("daily_log_id") == daily_log_id
    assert detail_data.get("placement_id") == placement_id
    assert detail_data.get("total_minutes") == 420
    assert detail_data.get("day_type") == "WORKDAY"
    assert "Backend mikroservis" in detail_data.get("summary", "")

    tasks = detail_data.get("tasks", [])
    assert len(tasks) == 2, f"Expected 2 tasks, got {len(tasks)}: {tasks}"
    task_minutes = sum(t.get("minutes", 0) for t in tasks)
    assert task_minutes == 420, f"Expected 420 total task minutes, got {task_minutes}"
    print(f"✓ Revision detail verified: Total {task_minutes} mins across {len(tasks)} tasks.")
    print("Phase 5 Passed: Academic revision detail contract (API-106) fully satisfied.")

    # =========================================================================
    # PHASE 6: Submit Academic Evaluation Decision (API-107)
    # =========================================================================
    print("\n--- PHASE 6: Submit Academic Evaluation Decision via BFF (API-107) ---")
    review_idem_key = f"rev-idem-{uuid4().hex[:12]}"
    review_comment = "Talaba amaliyot dasturini namunali bajargan. Kundalik to'liq tasdiqlandi."

    review_status, review_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/log-revisions/{revision_id}/academic-reviews",
        method="POST",
        data={
            "academic_assignment_id": academic_assignment_id,
            "decision": "REVIEWED",
            "comment": review_comment,
            "idempotency_key": review_idem_key,
        },
        headers={"Origin": FRONTEND_URL},
        opener=teacher_opener,
    )

    assert review_status in (200, 201), f"Expected 200/201 on academic-review, got {review_status}: {review_data}"
    assert review_data.get("decision") == "REVIEWED"
    assert review_data.get("revision_id") == revision_id
    assert review_data.get("placement_id") == placement_id
    assert review_data.get("comment") == review_comment
    print(f"✓ Academic review decision recorded: Receipt ID={review_data.get('id')}, Decision={review_data.get('decision')}")
    print("Phase 6 Passed: Academic review evaluation contract (API-107) fully satisfied.")

    # =========================================================================
    # PHASE 7: Cross-Site CSRF Rejection
    # =========================================================================
    print("\n--- PHASE 7: Cross-Site CSRF Rejection Verification ---")
    csrf_status, csrf_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/log-revisions/{revision_id}/academic-reviews",
        method="POST",
        data={"decision": "REVIEWED", "comment": "Cross-site exploit"},
        headers={"Sec-Fetch-Site": "cross-site", "Origin": "https://malicious-attacker.com"},
        opener=teacher_opener,
    )

    assert csrf_status == 403, f"Expected 403 CSRF_ORIGIN_MISMATCH, got {csrf_status}: {csrf_data}"
    assert csrf_data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got {csrf_data}"
    print("✓ Cross-site mutating request rejected with 403 CSRF_ORIGIN_MISMATCH")
    print("Phase 7 Passed: Anti-CSRF protection verified.")

    # =========================================================================
    # PHASE 8: Idempotency & Review State Verification
    # =========================================================================
    print("\n--- PHASE 8: Idempotency & Review State Verification ---")
    # Idempotent resubmission with identical key returns identical receipt
    idem_status, idem_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/log-revisions/{revision_id}/academic-reviews",
        method="POST",
        data={
            "academic_assignment_id": academic_assignment_id,
            "decision": "REVIEWED",
            "comment": review_comment,
            "idempotency_key": review_idem_key,
        },
        headers={"Origin": FRONTEND_URL},
        opener=teacher_opener,
    )

    assert idem_status in (200, 201), f"Expected 200/201 on idempotent re-review, got {idem_status}: {idem_data}"
    assert idem_data.get("id") == review_data.get("id"), "Idempotent re-submission must return the identical receipt ID"
    print("✓ Idempotency verified: duplicate review request with same key returns identical receipt.")

    # Re-inspect revision detail via API-106: academic_reviews list must now contain the reviewed entry
    recheck_status, recheck_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/log-revisions/{revision_id}/academic",
        method="GET",
        opener=teacher_opener,
    )
    assert recheck_status == 200, f"Expected 200 on re-inspecting revision, got {recheck_status}: {recheck_data}"
    acad_reviews = recheck_data.get("academic_reviews", [])
    matching_rev = next((ar for ar in acad_reviews if ar.get("id") == review_data.get("id")), None)
    assert matching_rev is not None, f"Expected review {review_data.get('id')} in academic_reviews: {acad_reviews}"
    assert matching_rev.get("decision") == "REVIEWED"
    assert matching_rev.get("comment") == review_comment
    print(f"✓ Revision state verified: academic_reviews contains review receipt {review_data.get('id')} with status REVIEWED.")

    # A different review with new key must be rejected (ACADEMIC_REVISION_ALREADY_REVIEWED)
    dup_status, dup_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/log-revisions/{revision_id}/academic-reviews",
        method="POST",
        data={
            "academic_assignment_id": academic_assignment_id,
            "decision": "NEEDS_REVISION",
            "comment": "Another attempt should be rejected",
            "idempotency_key": f"another-key-{uuid4().hex[:12]}",
        },
        headers={"Origin": FRONTEND_URL},
        opener=teacher_opener,
    )
    assert dup_status in (400, 403, 409, 422), f"Expected rejection on duplicate review attempt, got {dup_status}: {dup_data}"
    print(f"✓ Double-review prevention verified: subsequent review rejected with HTTP {dup_status} ({dup_data.get('error')})")
    print("Phase 8 Passed: Idempotency, detail reflection, and double-review protection confirmed.")

    print("\n" + "=" * 80)
    print("ALL 8 PHASES OF FB-152 VERIFICATION SUITE PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
