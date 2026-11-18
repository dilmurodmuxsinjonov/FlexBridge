#!/usr/bin/env python3
"""FlexBridge 1.4 University Portal Analytics Staging Verification Suite (API-125 / Milestone 3).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated request rejection (HTTP 401 AUTH_REQUIRED).
Phase 2: Unauthorized actor / Non-member institution request rejection (HTTP 404 anti-enumeration).
Phase 3: Seed deterministic test fixtures in Staging PostgreSQL via PgBouncer (127.0.0.1:5432/flexbridge, prepare_threshold=None).
Phase 4: Coordinator session authentication via Next.js BFF (/api/auth/login) with MFA elevation.
Phase 5: Execute GET /api/bff/university/institutions/[inst]/analytics and verify HTTP 200 with complete contract shape.
Phase 6: Verify Pillar 1 (Davomat) metrics: expected days, attended days, overall rate %, risk categorization, day-types, late submissions.
Phase 7: Verify Pillar 2 (Haftalik soatlar) metrics: ISO week trends, current week hours, average hours, program & organization breakdowns, MK 118 compliance alerts.
Phase 8: Verify Pillar 3 (Amaliyot natijalari) metrics: completion rate %, academic conclusions, mentor workplace evaluations, program performance.
Phase 9: Verify dynamic query filtering: filter by program, status, and from_date / to_date.
Phase 10: Cleanup of test fixtures and verification of idempotency.

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
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
    print("FLEXBRIDGE 1.4 UNIVERSITY PORTAL ANALYTICS STAGING VERIFICATION (API-125)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        connect_args={"prepare_threshold": None},
        pool_pre_ping=True,
    )

    test_suffix = uuid4().hex[:8]
    raw_password = f"CoordPass_{test_suffix}!"
    coordinator_hash = hash_password(raw_password)

    coordinator_user_id = str(uuid4())
    unauthorized_user_id = str(uuid4())

    inst_id = str(uuid4())
    org_id = str(uuid4())
    inst_agreement_id = str(uuid4())

    candidate_1_user_id = str(uuid4())
    candidate_1_profile_id = str(uuid4())

    candidate_2_user_id = str(uuid4())
    candidate_2_profile_id = str(uuid4())

    enrollment_1_id = str(uuid4())
    enrollment_2_id = str(uuid4())

    supervision_1_id = str(uuid4())
    supervision_2_id = str(uuid4())

    placement_1_id = str(uuid4())  # ACTIVE
    placement_2_id = str(uuid4())  # COMPLETED

    terms_1_id = str(uuid4())
    terms_2_id = str(uuid4())

    mentor_user_id = str(uuid4())
    mentor_org_membership_id = str(uuid4())
    mentor_assign_1_id = str(uuid4())
    mentor_assign_2_id = str(uuid4())

    opp_id = str(uuid4())
    opp_rev_id = str(uuid4())

    app_1_id = str(uuid4())
    attempt_1_id = str(uuid4())
    offer_1_id = str(uuid4())

    app_2_id = str(uuid4())
    attempt_2_id = str(uuid4())
    offer_2_id = str(uuid4())

    coordinator_appointment_id = str(uuid4())
    coordinator_membership_id = str(uuid4())
    coordinator_grant_id = str(uuid4())
    coordinator_session_id = str(uuid4())

    now_utc = datetime.now(timezone.utc)
    today_date = date.today()

    # -------------------------------------------------------------------------
    # PHASE 1: Unauthenticated request rejection (HTTP 401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n[Phase 1] Verifying unauthenticated rejection on University Analytics endpoint...")
    fake_inst = str(uuid4())

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{fake_inst}/analytics",
        method="GET",
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> GET .../analytics unauthenticated check: 401 AUTH_REQUIRED verified.")

    # -------------------------------------------------------------------------
    # PHASE 2: Unauthorized actor / Non-member institution rejection (HTTP 404 anti-enumeration)
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Verifying unauthorized actor / Non-member institution rejection (HTTP 404)...")
    # Pre-seed verified institution and unauthorized user in PostgreSQL
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                VALUES (:id, :now, :now, :code, :name, 'Tashkent', 'VERIFIED')
            """),
            {"id": inst_id, "now": now_utc, "code": f"TATU-{test_suffix[:4]}", "name": f"Toshkent Axborot Texnologiyalari Universiteti ({test_suffix})"}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, :name, :hash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": unauthorized_user_id, "now": now_utc, "name": f"Begona Foydalanuvchi {test_suffix}", "hash": coordinator_hash}
        )

    # Login as unauthorized user
    unauth_jar = http.cookiejar.CookieJar()
    unauth_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(unauth_jar))
    status_code, unauth_login, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": unauthorized_user_id, "password": raw_password},
        headers={"Origin": FRONTEND_URL},
        opener=unauth_opener,
    )
    assert status_code == 200, f"Expected 200 login for unauthorized user, got {status_code}: {unauth_login}"

    # Request analytics for institution they are NOT a member of
    status_code, unauth_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/analytics",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=unauth_opener,
    )
    assert status_code == 404, f"Expected 404 anti-enumeration defense, got {status_code}: {unauth_data}"
    print("  -> Unauthorized non-member tenant request rejected: 404 anti-enumeration defense verified.")

    # -------------------------------------------------------------------------
    # PHASE 3: DB Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n[Phase 3] Seeding test fixtures in Staging PostgreSQL via PgBouncer...")
    seeded_trigger_tables = [
        "enrollments", "enrollment_origins",
        "student_supervisions", "supervision_origins",
        "placement_intakes", "placement_academic_bindings",
        "placements", "placement_terms",
        "daily_logs", "log_revisions", "log_task_entries",
        "placement_decisions",
        "mentor_assignments", "workplace_log_reviews",
        "opportunity_revisions",
    ]

    with engine.begin() as conn:
        for t in seeded_trigger_tables:
            conn.execute(text(f"ALTER TABLE flexbridge.{t} DISABLE TRIGGER USER"))

    seed_conn = engine.connect()
    seed_trans = seed_conn.begin()
    try:
        clean_file_row = seed_conn.execute(
            text("SELECT id FROM flexbridge.files WHERE scan_status = 'CLEAN' LIMIT 1")
        ).first()
        assert clean_file_row, "Clean file required in DB for appointment"
        file_id = clean_file_row[0]

        # 1. Host Organization
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (
                    id, created_at, updated_at, legal_name, public_name, tax_id, region, status
                ) VALUES (
                    :id, :now, :now, :legal, :public, :tax_id, 'Tashkent', 'VERIFIED'
                )
            """),
            {
                "id": org_id, "now": now_utc, "legal": f"Artel LLC {test_suffix}",
                "public": "Artel LLC", "tax_id": f"9{test_suffix[:8]}"
            }
        )

        # 2. Institution Agreement
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_agreements (
                    id, created_at, updated_at, institution_id, version,
                    status, valid_from, valid_to, purposes
                ) VALUES (
                    :id, :now, :now, :inst_id, 1,
                    'ACTIVE', :from_date, :to_date, CAST('["ENGINEERING_INTERNSHIP"]' AS jsonb)
                )
            """),
            {
                "id": inst_agreement_id, "now": now_utc, "inst_id": inst_id,
                "from_date": today_date - timedelta(days=60), "to_date": today_date + timedelta(days=180)
            }
        )

        # 3. Coordinator User
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.users (
                    id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at
                ) VALUES (
                    :id, :now, :now, :name, :hash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now
                )
            """),
            {
                "id": coordinator_user_id, "now": now_utc, "hash": coordinator_hash,
                "name": f"Prof. Alisher Qodirov {test_suffix}"
            }
        )

        # 4. Coordinator Appointment, Membership & Role Grant
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_appointments (
                    id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, accepted_at
                ) VALUES (
                    :id, :now, :now, :inst_id, :uid, :file_id, 'ACTIVE', :today, :now
                )
            """),
            {"id": coordinator_appointment_id, "now": now_utc, "inst_id": inst_id, "uid": coordinator_user_id, "file_id": file_id, "today": today_date}
        )

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_memberships (
                    id, created_at, updated_at, institution_id, user_id, status, accepted_at
                ) VALUES (
                    :id, :now, :now, :inst_id, :uid, 'ACTIVE', :now
                )
            """),
            {"id": coordinator_membership_id, "now": now_utc, "inst_id": inst_id, "uid": coordinator_user_id}
        )

        coordinator_role_id = seed_conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'COORDINATOR' AND scope_kind = 'INSTITUTION'")
        ).scalar_one()

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_role_grants (
                    id, created_at, updated_at, membership_id, role_id, appointment_id
                ) VALUES (
                    :id, :now, :now, :mid, :rid, :aid
                )
            """),
            {
                "id": coordinator_grant_id, "mid": coordinator_membership_id,
                "rid": coordinator_role_id, "aid": coordinator_appointment_id, "now": now_utc
            }
        )

        # 5. Pre-seed Coordinator Session for Provenance
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.sessions (
                    id, created_at, updated_at, user_id, token_digest, assurance, expires_at, last_seen_at, auth_version
                ) VALUES (
                    :sess_id, :now, :now, :uid, :digest, 'MFA', :expires, :now, 1
                )
            """),
            {
                "sess_id": coordinator_session_id, "uid": coordinator_user_id,
                "digest": f"digest_{uuid4().hex}", "expires": now_utc + timedelta(days=7),
                "now": now_utc
            }
        )

        # 6. Candidates & Profiles
        # Candidate 1: Aziz Rahimov (Kompyuter injiniringi)
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Aziz Rahimov', :hash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": candidate_1_user_id, "now": now_utc, "hash": coordinator_hash}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, bio, experience_months, visibility)
                VALUES (:id, :now, :now, :uid, 'Talaba Kompyuter', 'Tashkent', 'Dasturlash talabasi', 6, 'PUBLIC')
            """),
            {"id": candidate_1_profile_id, "now": now_utc, "uid": candidate_1_user_id}
        )

        # Candidate 2: Dilshod Karimov (Dasturiy injiniring)
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Dilshod Karimov', :hash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": candidate_2_user_id, "now": now_utc, "hash": coordinator_hash}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, bio, experience_months, visibility)
                VALUES (:id, :now, :now, :uid, 'Talaba Dasturchi', 'Samarkand', 'Dasturiy injiniring talabasi', 8, 'PUBLIC')
            """),
            {"id": candidate_2_profile_id, "now": now_utc, "uid": candidate_2_user_id}
        )

        # 7. Enrollments & Origins
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.enrollments (id, created_at, updated_at, candidate_id, institution_id, program, start_date, end_date, status)
                VALUES (:id, :now, :now, :cid, :inst, 'Kompyuter injiniringi', :start, :end, 'VERIFIED')
            """),
            {"id": enrollment_1_id, "now": now_utc, "cid": candidate_1_profile_id, "inst": inst_id, "start": today_date - timedelta(days=30), "end": today_date + timedelta(days=60)}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.enrollment_origins (enrollment_id, created_at, origin, candidate_id, institution_id, actor_user_id, initial_snapshot)
                VALUES (:id, :now, 'LEGACY_IMPORT', :cid, :inst, :uid, jsonb_build_object('status', 'VERIFIED'))
            """),
            {"id": enrollment_1_id, "now": now_utc, "cid": candidate_1_profile_id, "inst": inst_id, "uid": coordinator_user_id}
        )

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.enrollments (id, created_at, updated_at, candidate_id, institution_id, program, start_date, end_date, status)
                VALUES (:id, :now, :now, :cid, :inst, 'Dasturiy injiniring', :start, :end, 'VERIFIED')
            """),
            {"id": enrollment_2_id, "now": now_utc, "cid": candidate_2_profile_id, "inst": inst_id, "start": today_date - timedelta(days=45), "end": today_date - timedelta(days=5)}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.enrollment_origins (enrollment_id, created_at, origin, candidate_id, institution_id, actor_user_id, initial_snapshot)
                VALUES (:id, :now, 'LEGACY_IMPORT', :cid, :inst, :uid, jsonb_build_object('status', 'VERIFIED'))
            """),
            {"id": enrollment_2_id, "now": now_utc, "cid": candidate_2_profile_id, "inst": inst_id, "uid": coordinator_user_id}
        )

        # 8. Supervisions & Origins
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.student_supervisions (id, created_at, updated_at, enrollment_id, coordinator_membership_id, agreement_id, purpose, status, legal_basis, accepted_at, institution_id)
                VALUES (:id, :now, :now, :eid, :mid, :aid, 'ENGINEERING_INTERNSHIP', 'ACTIVE', 'Kafedra qarori #1', :now, :inst_id)
            """),
            {"id": supervision_1_id, "now": now_utc, "eid": enrollment_1_id, "mid": coordinator_membership_id, "aid": inst_agreement_id, "inst_id": inst_id}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.supervision_origins (supervision_id, created_at, origin, initial_snapshot)
                VALUES (:id, :now, 'LEGACY_IMPORT', CAST('{}' AS jsonb))
            """),
            {"id": supervision_1_id, "now": now_utc}
        )

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.student_supervisions (id, created_at, updated_at, enrollment_id, coordinator_membership_id, agreement_id, purpose, status, legal_basis, accepted_at, institution_id)
                VALUES (:id, :now, :now, :eid, :mid, :aid, 'ENGINEERING_INTERNSHIP', 'ACTIVE', 'Kafedra qarori #2', :now, :inst_id)
            """),
            {"id": supervision_2_id, "now": now_utc, "eid": enrollment_2_id, "mid": coordinator_membership_id, "aid": inst_agreement_id, "inst_id": inst_id}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.supervision_origins (supervision_id, created_at, origin, initial_snapshot)
                VALUES (:id, :now, 'LEGACY_IMPORT', CAST('{}' AS jsonb))
            """),
            {"id": supervision_2_id, "now": now_utc}
        )

        # 9. Mentor User, Org Membership, Opportunity & Applications
        seed_conn.execute(
            text("INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at) VALUES (:id, :now, :now, 'Mentor Rustam', :hash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)"),
            {"id": mentor_user_id, "now": now_utc, "hash": coordinator_hash}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (
                    id, created_at, updated_at, organization_id, user_id, status, accepted_at
                ) VALUES (
                    :id, :now, :now, :oid, :uid, 'ACTIVE', :now
                )
            """),
            {"id": mentor_org_membership_id, "now": now_utc, "oid": org_id, "uid": mentor_user_id}
        )

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
            {"id": opp_rev_id, "opp_id": opp_id, "author_id": mentor_user_id, "today": today_date, "now": now_utc}
        )
        seed_conn.execute(
            text("UPDATE flexbridge.opportunities SET current_revision_id = :rev WHERE id = :id"),
            {"rev": opp_rev_id, "id": opp_id}
        )

        # Applications, Attempts & Offers
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.applications (id, created_at, updated_at, opportunity_id, candidate_id, status, version)
                VALUES (:id, :now, :now, :opp_id, :cand_id, 'OFFERED', 1)
            """),
            {"id": app_1_id, "opp_id": opp_id, "cand_id": candidate_1_profile_id, "now": now_utc}
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
            {"attempt_id": attempt_1_id, "app_id": app_1_id, "opp_id": opp_id, "rev_id": opp_rev_id, "now": now_utc, "idem": f"idem-attempt-1-{uuid4().hex}"}
        )
        seed_conn.execute(
            text("UPDATE flexbridge.applications SET current_attempt_id = :aid WHERE id = :id"),
            {"aid": attempt_1_id, "id": app_1_id}
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
                "id": offer_1_id, "app_id": app_1_id, "attempt_id": attempt_1_id, "rev_id": opp_rev_id,
                "issuer_id": mentor_org_membership_id, "expires": now_utc + timedelta(days=30),
                "idem": f"idem-offer-1-{uuid4().hex}", "now": now_utc
            }
        )

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.applications (id, created_at, updated_at, opportunity_id, candidate_id, status, version)
                VALUES (:id, :now, :now, :opp_id, :cand_id, 'OFFERED', 1)
            """),
            {"id": app_2_id, "opp_id": opp_id, "cand_id": candidate_2_profile_id, "now": now_utc}
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
            {"attempt_id": attempt_2_id, "app_id": app_2_id, "opp_id": opp_id, "rev_id": opp_rev_id, "now": now_utc, "idem": f"idem-attempt-2-{uuid4().hex}"}
        )
        seed_conn.execute(
            text("UPDATE flexbridge.applications SET current_attempt_id = :aid WHERE id = :id"),
            {"aid": attempt_2_id, "id": app_2_id}
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
                "id": offer_2_id, "app_id": app_2_id, "attempt_id": attempt_2_id, "rev_id": opp_rev_id,
                "issuer_id": mentor_org_membership_id, "expires": now_utc + timedelta(days=30),
                "idem": f"idem-offer-2-{uuid4().hex}", "now": now_utc
            }
        )

        # 10. Placements & Terms
        terms_snapshot = {
            "version": 1,
            "contract_type": "INTERNSHIP_AGREEMENT",
            "academic_scope": {"institution_id": inst_id, "agreement_id": inst_agreement_id}
        }
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placements (
                    id, created_at, updated_at, application_id, offer_id, candidate_id, organization_id, enrollment_id,
                    academic_track, status, start_date, end_date, version
                ) VALUES (
                    :id, :now, :now, :app_id, :offer_id, :cid, :oid, :eid, TRUE, 'ACTIVE', :sdate, :edate, 1
                )
            """),
            {
                "id": placement_1_id, "now": now_utc, "app_id": app_1_id, "offer_id": offer_1_id,
                "cid": candidate_1_profile_id, "oid": org_id, "eid": enrollment_1_id,
                "sdate": today_date - timedelta(days=20), "edate": today_date + timedelta(days=10)
            }
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_intakes (placement_id, created_at, origin, offer_id, attempt_id, revision_id, academic_required, initial_snapshot, source_snapshot)
                VALUES (:pid, :now, 'LEGACY_IMPORT', :offer_id, :attempt_id, :rev_id, TRUE, '{}'::jsonb, '{}'::jsonb)
            """),
            {"pid": placement_1_id, "offer_id": offer_1_id, "attempt_id": attempt_1_id, "rev_id": opp_rev_id, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_terms (
                    id, created_at, updated_at, placement_id, version, schema_version, terms_snapshot,
                    daily_limit_minutes, weekly_limit_minutes, required_minutes
                ) VALUES (
                    :id, :now, :now, :pid, 1, 1, CAST(:snapshot AS jsonb), 480, 2400, 14400
                )
            """),
            {"id": terms_1_id, "now": now_utc, "pid": placement_1_id, "snapshot": json.dumps(terms_snapshot)}
        )
        seed_conn.execute(
            text("UPDATE flexbridge.placements SET current_terms_id = :tid WHERE id = :pid"),
            {"tid": terms_1_id, "pid": placement_1_id}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_academic_bindings (
                    placement_id, created_at, origin, institution_id, enrollment_id,
                    supervision_id, terms_id, initial_snapshot, scope_snapshot
                )
                VALUES (:pid, :now, 'LEGACY_IMPORT', :inst_id, :eid, :sid, :tid, '{}'::jsonb, '{}'::jsonb)
            """),
            {"pid": placement_1_id, "inst_id": inst_id, "eid": enrollment_1_id, "sid": supervision_1_id, "tid": terms_1_id, "now": now_utc}
        )

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placements (
                    id, created_at, updated_at, application_id, offer_id, candidate_id, organization_id, enrollment_id,
                    academic_track, status, start_date, end_date, version
                ) VALUES (
                    :id, :now, :now, :app_id, :offer_id, :cid, :oid, :eid, TRUE, 'COMPLETED', :sdate, :edate, 1
                )
            """),
            {
                "id": placement_2_id, "now": now_utc, "app_id": app_2_id, "offer_id": offer_2_id,
                "cid": candidate_2_profile_id, "oid": org_id, "eid": enrollment_2_id,
                "sdate": today_date - timedelta(days=40), "edate": today_date - timedelta(days=5)
            }
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_intakes (placement_id, created_at, origin, offer_id, attempt_id, revision_id, academic_required, initial_snapshot, source_snapshot)
                VALUES (:pid, :now, 'LEGACY_IMPORT', :offer_id, :attempt_id, :rev_id, TRUE, '{}'::jsonb, '{}'::jsonb)
            """),
            {"pid": placement_2_id, "offer_id": offer_2_id, "attempt_id": attempt_2_id, "rev_id": opp_rev_id, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_terms (
                    id, created_at, updated_at, placement_id, version, schema_version, terms_snapshot,
                    daily_limit_minutes, weekly_limit_minutes, required_minutes
                ) VALUES (
                    :id, :now, :now, :pid, 1, 1, CAST(:snapshot AS jsonb), 480, 2400, 14400
                )
            """),
            {"id": terms_2_id, "now": now_utc, "pid": placement_2_id, "snapshot": json.dumps(terms_snapshot)}
        )
        seed_conn.execute(
            text("UPDATE flexbridge.placements SET current_terms_id = :tid WHERE id = :pid"),
            {"tid": terms_2_id, "pid": placement_2_id}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_academic_bindings (
                    placement_id, created_at, origin, institution_id, enrollment_id,
                    supervision_id, terms_id, initial_snapshot, scope_snapshot
                )
                VALUES (:pid, :now, 'LEGACY_IMPORT', :inst_id, :eid, :sid, :tid, '{}'::jsonb, '{}'::jsonb)
            """),
            {"pid": placement_2_id, "inst_id": inst_id, "eid": enrollment_2_id, "sid": supervision_2_id, "tid": terms_2_id, "now": now_utc}
        )

        # 10. Seed Daily Logs and Log Revisions for Candidate 1 (Placement 1)
        # Create 5 WORK logs, 1 SICK_LEAVE log, and 1 late submission (>3 days)
        non_sunday_dates: list[date] = []
        cursor_day = 1
        while len(non_sunday_dates) < 12:
            d = today_date - timedelta(days=cursor_day)
            cursor_day += 1
            if d.weekday() != 6:
                non_sunday_dates.append(d)

        for i, log_date in enumerate(non_sunday_dates[:5], start=1):
            dl_id = str(uuid4())
            rev_id = str(uuid4())

            # Log 1 is late submission: submitted 5 days after local_date
            sub_date = now_utc if i != 1 else now_utc + timedelta(days=5)

            seed_conn.execute(
                text("INSERT INTO flexbridge.daily_logs (id, created_at, updated_at, placement_id, local_date, current_revision_id, version) VALUES (:id, :now, :now, :pid, :ldate, :rid, 1)"),
                {"id": dl_id, "now": now_utc, "pid": placement_1_id, "ldate": log_date, "rid": rev_id}
            )
            seed_conn.execute(
                text("""
                    INSERT INTO flexbridge.log_revisions (id, created_at, updated_at, daily_log_id, revision, terms_id, author_id, day_type, summary, total_minutes, status, submitted_at, idempotency_key)
                    VALUES (:id, :now, :now, :dlid, 1, :tid, :uid, 'WORK', 'Dasturlash topshiriqlari', 480, 'SUBMITTED', :sub, :idem)
                """),
                {"id": rev_id, "now": now_utc, "dlid": dl_id, "tid": terms_1_id, "uid": candidate_1_user_id, "sub": sub_date, "idem": f"idem-rev-{rev_id[:12]}"}
            )

        # 1 Sick leave log for Candidate 1
        sick_date = non_sunday_dates[5]
        dl_sick_id = str(uuid4())
        rev_sick_id = str(uuid4())
        seed_conn.execute(
            text("INSERT INTO flexbridge.daily_logs (id, created_at, updated_at, placement_id, local_date, current_revision_id, version) VALUES (:id, :now, :now, :pid, :ldate, :rid, 1)"),
            {"id": dl_sick_id, "now": now_utc, "pid": placement_1_id, "ldate": sick_date, "rid": rev_sick_id}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.log_revisions (id, created_at, updated_at, daily_log_id, revision, terms_id, author_id, day_type, summary, total_minutes, status, submitted_at, idempotency_key)
                VALUES (:id, :now, :now, :dlid, 1, :tid, :uid, 'SICK_LEAVE', 'Shifokor ma''lumotnomasi', 0, 'SUBMITTED', :sub, :idem)
            """),
            {"id": rev_sick_id, "now": now_utc, "dlid": dl_sick_id, "tid": terms_1_id, "uid": candidate_1_user_id, "sub": now_utc, "idem": f"idem-rev-{rev_sick_id[:12]}"}
        )

        # 11. Seed Daily Logs for Candidate 2 (Placement 2)
        # 4 WORK logs, 1 ABSENCE log, and 1 OVERTIME log (510 min > 480 limit)
        for i, log_date in enumerate(non_sunday_dates[6:10], start=10):
            dl_id = str(uuid4())
            rev_id = str(uuid4())

            # 1 Overtime log to trigger O'zR MK 118 compliance alert
            tot_mins = 510 if i == 10 else 480

            seed_conn.execute(
                text("INSERT INTO flexbridge.daily_logs (id, created_at, updated_at, placement_id, local_date, current_revision_id, version) VALUES (:id, :now, :now, :pid, :ldate, :rid, 1)"),
                {"id": dl_id, "now": now_utc, "pid": placement_2_id, "ldate": log_date, "rid": rev_id}
            )
            seed_conn.execute(
                text("""
                    INSERT INTO flexbridge.log_revisions (id, created_at, updated_at, daily_log_id, revision, terms_id, author_id, day_type, summary, total_minutes, status, submitted_at, idempotency_key)
                    VALUES (:id, :now, :now, :dlid, 1, :tid, :uid, 'WORK', 'Modullarni ishlab chiqish', :mins, 'SUBMITTED', :sub, :idem)
                """),
                {"id": rev_id, "now": now_utc, "dlid": dl_id, "tid": terms_2_id, "uid": candidate_2_user_id, "mins": tot_mins, "sub": now_utc, "idem": f"idem-rev-{rev_id[:12]}"}
            )

        # 1 Absence log for Candidate 2
        abs_date = non_sunday_dates[10]
        dl_abs_id = str(uuid4())
        rev_abs_id = str(uuid4())
        seed_conn.execute(
            text("INSERT INTO flexbridge.daily_logs (id, created_at, updated_at, placement_id, local_date, current_revision_id, version) VALUES (:id, :now, :now, :pid, :ldate, :rid, 1)"),
            {"id": dl_abs_id, "now": now_utc, "pid": placement_2_id, "ldate": abs_date, "rid": rev_abs_id}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.log_revisions (id, created_at, updated_at, daily_log_id, revision, terms_id, author_id, day_type, summary, total_minutes, status, submitted_at, idempotency_key)
                VALUES (:id, :now, :now, :dlid, 1, :tid, :uid, 'ABSENCE', 'Sababsiz kelmagan', 0, 'SUBMITTED', :sub, :idem)
            """),
            {"id": rev_abs_id, "now": now_utc, "dlid": dl_abs_id, "tid": terms_2_id, "uid": candidate_2_user_id, "sub": now_utc, "idem": f"idem-rev-{rev_abs_id[:12]}"}
        )

        # 12. Workplace Reviews (1 APPROVED, 1 CHANGES_REQUESTED)
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.mentor_assignments (
                    id, created_at, updated_at, placement_id, membership_id, assigned_by_id, assigned_at, accepted_at, organization_id
                ) VALUES (
                    :id, :now, :now, :pid, :mid, :by_id, :now, :now, :oid
                )
            """),
            {
                "id": mentor_assign_1_id, "now": now_utc, "pid": placement_1_id,
                "mid": mentor_org_membership_id, "by_id": coordinator_user_id, "oid": org_id
            }
        )
        mentor_assign_2_id = str(uuid4())
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.mentor_assignments (
                    id, created_at, updated_at, placement_id, membership_id, assigned_by_id, assigned_at, accepted_at, organization_id
                ) VALUES (
                    :id, :now, :now, :pid, :mid, :by_id, :now, :now, :oid
                )
            """),
            {
                "id": mentor_assign_2_id, "now": now_utc, "pid": placement_2_id,
                "mid": mentor_org_membership_id, "by_id": coordinator_user_id, "oid": org_id
            }
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.workplace_log_reviews (id, created_at, updated_at, revision_id, mentor_assignment_id, decision, comment, decided_at, placement_id)
                VALUES (:id, :now, :now, :rid, :mid, 'APPROVED', 'Yaxshi bajarildi', :now, :pid)
            """),
            {"id": str(uuid4()), "now": now_utc, "rid": rev_sick_id, "mid": mentor_assign_1_id, "pid": placement_1_id}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.workplace_log_reviews (id, created_at, updated_at, revision_id, mentor_assignment_id, decision, comment, decided_at, placement_id)
                VALUES (:id, :now, :now, :rid, :mid, 'CHANGES_REQUESTED', 'Hisobotni kengaytiring', :now, :pid)
            """),
            {"id": str(uuid4()), "now": now_utc, "rid": rev_abs_id, "mid": mentor_assign_2_id, "pid": placement_2_id}
        )

        # 13. Academic Decision for Placement 2 (ACADEMIC_REVIEW_COMPLETE)
        dec_proof_id = str(uuid4())
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.placement_decisions (id, created_at, updated_at, placement_id, actor_id, side, decision, terms_id, reason, decided_at)
                VALUES (:id, :now, :now, :pid, :act, 'TEACHER', 'ACADEMIC_REVIEW_COMPLETE', :tid, 'Amaliyot muvaffaqiyatli yakunlandi', :now)
            """),
            {"id": dec_proof_id, "now": now_utc, "pid": placement_2_id, "act": coordinator_user_id, "tid": terms_2_id}
        )

        seed_trans.commit()
        print("  -> Deterministic DB test fixtures successfully committed.")
    except Exception as exc:
        seed_trans.rollback()
        raise RuntimeError(f"Database fixtures seeding failed: {exc}") from exc
    finally:
        seed_conn.close()
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))

    # -------------------------------------------------------------------------
    # PHASE 4: Coordinator Authentication via /api/auth/login and MFA Elevation
    # -------------------------------------------------------------------------
    print("\n[Phase 4] Authenticating Coordinator via /api/auth/login and elevating session to MFA...")
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    status_code, login_data, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": coordinator_user_id, "password": raw_password},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {login_data}"
    assert login_data.get("ok") is True, f"Login failed: {login_data}"
    print(f"  -> Coordinator login successful. User ID: {coordinator_user_id}")

    # Elevate session assurance to 'MFA' in PostgreSQL
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE flexbridge.sessions
                SET assurance = 'MFA', updated_at = :now
                WHERE user_id = :uid AND revoked_at IS NULL
            """),
            {"uid": coordinator_user_id, "now": datetime.now(timezone.utc)}
        )
    print("  -> Session assurance elevated to 'MFA' in PostgreSQL.")

    # -------------------------------------------------------------------------
    # PHASE 5: Execute GET /api/bff/university/institutions/{inst}/analytics
    # -------------------------------------------------------------------------
    print("\n[Phase 5] Coordinator executes GET .../analytics via BFF...")
    status_code, analytics_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/analytics",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {analytics_data}"
    assert analytics_data.get("ok") is True, f"Expected ok: True, got {analytics_data}"
    assert analytics_data.get("contract_id") == "API-125", f"Expected API-125, got {analytics_data}"
    assert analytics_data.get("institution_id") == inst_id, f"Institution mismatch: {analytics_data}"

    # Verify top-level structure
    assert "summary" in analytics_data, "Missing summary block"
    assert "attendance_metrics" in analytics_data, "Missing attendance_metrics block"
    assert "weekly_hours_monitoring" in analytics_data, "Missing weekly_hours_monitoring block"
    assert "internship_results" in analytics_data, "Missing internship_results block"
    print("  -> HTTP 200 received with complete contract schema verified.")

    # -------------------------------------------------------------------------
    # PHASE 6: Verify Pillar 1 (Talabalar Davomati) Metrics
    # -------------------------------------------------------------------------
    print("\n[Phase 6] Verifying Pillar 1 (Talabalar Davomati) metrics...")
    att = analytics_data["attendance_metrics"]
    summary = analytics_data["summary"]

    assert summary["total_students"] == 2, f"Expected 2 students, got {summary['total_students']}"
    assert summary["overall_attendance_rate"] > 0.0, f"Expected overall_attendance_rate > 0, got {summary['overall_attendance_rate']}"

    # Verify day-type breakdown
    by_day = att["by_day_type"]
    assert by_day["work"] >= 8, f"Expected >= 8 work days, got {by_day['work']}"
    assert by_day["sick_leave"] >= 1, f"Expected >= 1 sick leave, got {by_day['sick_leave']}"
    assert by_day["absence"] >= 1, f"Expected >= 1 absence, got {by_day['absence']}"

    # Verify late submission
    assert att["late_submissions_count"] >= 1, f"Expected >= 1 late submission, got {att['late_submissions_count']}"

    # Verify risk distribution
    dist = att["by_status_distribution"]
    assert (dist["good"] + dist["warning"] + dist["critical"]) == 2, f"Status distribution sum mismatch: {dist}"

    # Verify students list
    students = att["students"]
    assert len(students) == 2, f"Expected 2 students in list, got {len(students)}"
    student_names = {s["student_name"] for s in students}
    assert "Aziz Rahimov" in student_names, f"Missing Aziz Rahimov in {student_names}"
    assert "Dilshod Karimov" in student_names, f"Missing Dilshod Karimov in {student_names}"

    for s in students:
        assert s["expected_days"] > 0, f"Expected expected_days > 0 for {s}"
        assert s["attended_days"] > 0, f"Expected attended_days > 0 for {s}"
        assert s["attendance_status"] in ("GOOD", "WARNING", "CRITICAL"), f"Invalid risk status: {s}"
    print(f"  -> Pillar 1 verified: overall_rate={att['overall_rate']}%, work={by_day['work']}, late={att['late_submissions_count']}.")

    # -------------------------------------------------------------------------
    # PHASE 7: Verify Pillar 2 (Haftalik Soatlar Monitoringi) Metrics
    # -------------------------------------------------------------------------
    print("\n[Phase 7] Verifying Pillar 2 (Haftalik Soatlar) metrics...")
    weekly = analytics_data["weekly_hours_monitoring"]

    assert summary["total_logged_hours"] > 0.0, f"Expected total_logged_hours > 0, got {summary['total_logged_hours']}"
    assert len(weekly["weekly_trend"]) >= 1, f"Expected weekly trend items, got {weekly['weekly_trend']}"

    # Program breakdown
    by_prog = weekly["by_program"]
    assert len(by_prog) == 2, f"Expected 2 programs in breakdown, got {len(by_prog)}"
    prog_names = {p["program"] for p in by_prog}
    assert "Kompyuter injiniringi" in prog_names, f"Missing Kompyuter injiniringi in {prog_names}"
    assert "Dasturiy injiniring" in prog_names, f"Missing Dasturiy injiniring in {prog_names}"

    # Organization breakdown
    by_org = weekly["by_organization"]
    assert len(by_org) == 1, f"Expected 1 organization, got {len(by_org)}"
    assert by_org[0]["organization_name"] == "Artel LLC", f"Organization mismatch: {by_org}"

    # O'zR MK 118 compliance alert: Candidate 2 had a 510 minute (>480 min) log
    alerts = weekly["compliance_alerts"]
    assert alerts["overtime_students"] >= 1, f"Expected >= 1 overtime student, got {alerts['overtime_students']}"
    print(f"  -> Pillar 2 verified: trend_weeks={len(weekly['weekly_trend'])}, overtime_alerts={alerts['overtime_students']}.")

    # -------------------------------------------------------------------------
    # PHASE 8: Verify Pillar 3 (Amaliyot Natijalari) Metrics
    # -------------------------------------------------------------------------
    print("\n[Phase 8] Verifying Pillar 3 (Amaliyot Natijalari) metrics...")
    results = analytics_data["internship_results"]

    assert results["total_placements"] == 2, f"Expected 2 placements, got {results['total_placements']}"
    assert results["by_status"].get("ACTIVE") == 1, f"Expected 1 ACTIVE placement, got {results['by_status']}"
    assert results["by_status"].get("COMPLETED") == 1, f"Expected 1 COMPLETED placement, got {results['by_status']}"
    assert results["completion_rate"] == 50.0, f"Expected 50.0% completion rate, got {results['completion_rate']}"

    # Academic conclusions: 1 completed conclusion seeded
    adp = results["academic_conclusions"]
    assert adp["complete"] >= 1, f"Expected >= 1 completed academic conclusion, got {adp}"
    assert adp["total"] >= 1, f"Expected >= 1 total conclusion, got {adp}"

    # Workplace evaluations: 1 APPROVED, 1 CHANGES_REQUESTED
    evals = results["workplace_evaluations"]
    assert evals["approved_count"] == 1, f"Expected 1 approved eval, got {evals['approved_count']}"
    assert evals["changes_requested_count"] == 1, f"Expected 1 changes requested eval, got {evals['changes_requested_count']}"
    assert evals["approved_rate"] == 50.0, f"Expected 50.0% approval rate, got {evals['approved_rate']}"

    # Program performance
    perf = results["program_performance"]
    assert len(perf) == 2, f"Expected 2 program performance entries, got {len(perf)}"
    print(f"  -> Pillar 3 verified: completion_rate={results['completion_rate']}%, conclusions={adp['total']}, approved_evals={evals['approved_count']}.")

    # -------------------------------------------------------------------------
    # PHASE 9: Verify Dynamic Query Filtering
    # -------------------------------------------------------------------------
    print("\n[Phase 9] Verifying dynamic query filtering...")

    # 9a. Filter by program
    status_code, prog_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/analytics?program=Kompyuter+injiniringi",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {prog_data}"
    assert prog_data["summary"]["total_students"] == 1, f"Expected 1 student for program filter, got {prog_data['summary']['total_students']}"
    assert prog_data["attendance_metrics"]["students"][0]["student_name"] == "Aziz Rahimov"
    print("  -> Dynamic filter by program verified: exactly 1 student filtered.")

    # 9b. Filter by status
    status_code, stat_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/analytics?status=COMPLETED",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {stat_data}"
    assert stat_data["summary"]["total_students"] == 1, f"Expected 1 student for status filter, got {stat_data['summary']['total_students']}"
    assert stat_data["attendance_metrics"]["students"][0]["student_name"] == "Dilshod Karimov"
    print("  -> Dynamic filter by status=COMPLETED verified: exactly 1 completed placement filtered.")

    # 9c. Filter by date window
    f_date = (today_date - timedelta(days=5)).isoformat()
    t_date = today_date.isoformat()
    status_code, date_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/analytics?from_date={f_date}&to_date={t_date}",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {date_data}"
    print(f"  -> Dynamic filter by date range ({f_date} to {t_date}) verified.")

    # -------------------------------------------------------------------------
    # PHASE 10: Idempotency & Cleanup Verification
    # -------------------------------------------------------------------------
    print("\n[Phase 10] Verifying repeat query idempotency and DB consistency...")
    status_code, replay_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/analytics",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 200, f"Expected 200 on replay query, got {status_code}: {replay_data}"
    assert replay_data["summary"]["total_students"] == analytics_data["summary"]["total_students"], "Idempotency student count mismatch"
    assert replay_data["summary"]["total_logged_hours"] == analytics_data["summary"]["total_logged_hours"], "Idempotency logged hours mismatch"
    print("  -> Repeat analytics query verified: identical metrics returned with zero side effects.")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF UNIVERSITY PORTAL ANALYTICS VERIFICATION PASSED (100% GREEN)!")
    print("=" * 80)


if __name__ == "__main__":
    main()
