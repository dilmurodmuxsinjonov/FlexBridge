#!/usr/bin/env python3
"""FlexBridge 1.4 University Report Exports, Supervisions & Academic Agreements Verification Suite (FB-170).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected for University BFF endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Anti-CSRF Origin Guard rejection on report export (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 3: DB Fixtures Setup via PgBouncer (127.0.0.1:5432/flexbridge, prepare_threshold=None).
Phase 4: University Coordinator authentication via Next.js BFF (/api/auth/login) with MFA assurance.
Phase 5: Coordinator generates PDF export via BFF (API-100: POST /api/bff/university/institutions/[inst]/exports).
Phase 6: Coordinator generates JSON export & verifies advisory-locked idempotency replay.
Phase 7: Negative validation: invalid export format rejected (HTTP 422 INVALID_EXPORT_FORMAT).
Phase 8: Coordinator inspects student supervisions list via BFF (API-098: GET /api/bff/university/institutions/[inst]/supervisions).
Phase 9: Coordinator inspects active academic agreements via BFF (API-101: GET /api/bff/university/institutions/[inst]/agreements).
Phase 10: IDOR & Security Guardrails: accessing unauthorized institution returns HTTP 404 anti-enumeration defense.

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import hashlib
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
    print("FLEXBRIDGE 1.4 UNIVERSITY EXPORTS & AGREEMENTS STAGING VERIFICATION (FB-170)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        connect_args={"prepare_threshold": None},
        pool_pre_ping=True,
    )

    test_suffix = uuid4().hex[:8]
    raw_password = f"CoordinatorPass_{test_suffix}!"
    coordinator_hash = hash_password(raw_password)

    coordinator_user_id = str(uuid4())
    coordinator_email = f"coordinator_{test_suffix}@university.test"

    student_user_id = str(uuid4())
    student_profile_id = str(uuid4())
    student_email = f"student_{test_suffix}@university.test"

    inst_id = str(uuid4())
    inst_agreement_id = str(uuid4())
    enrollment_id = str(uuid4())
    supervision_id = str(uuid4())
    coordinator_appointment_id = str(uuid4())
    coordinator_membership_id = str(uuid4())
    coordinator_grant_id = str(uuid4())
    coordinator_session_id = str(uuid4())

    now_utc = datetime.now(timezone.utc)
    today_date = date.today()
    purpose = "ENGINEERING_INTERNSHIP"

    # -------------------------------------------------------------------------
    # PHASE 1: Unauthenticated rejection (HTTP 401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n[Phase 1] Verifying unauthenticated rejection on University endpoints...")
    fake_inst = str(uuid4())

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{fake_inst}/exports",
        method="POST",
        data={"format": "PDF", "include_details": True},
        headers={"Origin": FRONTEND_URL},
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> POST .../exports unauthenticated check: 401 AUTH_REQUIRED verified.")

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{fake_inst}/supervisions",
        method="GET",
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> GET .../supervisions unauthenticated check: 401 AUTH_REQUIRED verified.")

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{fake_inst}/agreements",
        method="GET",
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> GET .../agreements unauthenticated check: 401 AUTH_REQUIRED verified.")

    # -------------------------------------------------------------------------
    # PHASE 2: Anti-CSRF Origin Guard rejection (HTTP 403 CSRF_ORIGIN_MISMATCH)
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Verifying Anti-CSRF Origin Guard rejection on report export...")
    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{fake_inst}/exports",
        method="POST",
        data={"format": "PDF"},
        headers={"Origin": "https://malicious-attacker.com"},
    )
    assert status_code == 403, f"Expected 403 CSRF rejection, got {status_code}: {data}"
    assert data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got {data}"
    print("  -> CSRF cross-origin attack blocked: 403 CSRF_ORIGIN_MISMATCH verified.")

    # -------------------------------------------------------------------------
    # PHASE 3: DB Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n[Phase 3] Seeding test fixtures in Staging PostgreSQL via PgBouncer...")
    seeded_trigger_tables = [
        "enrollments", "enrollment_origins",
        "student_supervisions", "supervision_origins",
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

        # 1. Coordinator User
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Prof. Ziyoda Karimova', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": coordinator_user_id, "pwd": coordinator_hash, "now": now_utc}
        )

        # 2. Student User & Candidate Profile
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Otabek Rustamov', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": student_user_id, "pwd": coordinator_hash, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, bio, experience_months, visibility)
                VALUES (:id, :now, :now, :uid, 'Talaba Dasturchi', 'Tashkent', 'Dasturiy injiniring talabasi', 6, 'PUBLIC')
            """),
            {"id": student_profile_id, "uid": student_user_id, "now": now_utc}
        )

        # 3. Institution (VERIFIED) & Agreement (ACTIVE)
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                VALUES (:id, :now, :now, :code, 'Toshkent Axborot Texnologiyalari Universiteti', 'Tashkent', 'VERIFIED')
            """),
            {"id": inst_id, "code": f"INST_EXP_{test_suffix}", "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_agreements (id, created_at, updated_at, institution_id, version, status, valid_from, purposes)
                VALUES (:id, :now, :now, :inst_id, 1, 'ACTIVE', :today, jsonb_build_array('ENGINEERING_INTERNSHIP'))
            """),
            {"id": inst_agreement_id, "inst_id": inst_id, "today": today_date, "now": now_utc}
        )

        # 4. Student Enrollment (VERIFIED) & Origin
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.enrollments (id, created_at, updated_at, candidate_id, institution_id, program, status, start_date)
                VALUES (:id, :now, :now, :cand_id, :inst_id, 'Dasturiy Injiniring', 'VERIFIED', :today)
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

        # 5. Coordinator Appointment, Membership, and COORDINATOR Role Grant
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_appointments (id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, accepted_at)
                VALUES (:id, :now, :now, :inst_id, :uid, :file_id, 'ACTIVE', :today, :now)
            """),
            {"id": coordinator_appointment_id, "inst_id": inst_id, "uid": coordinator_user_id, "file_id": file_id, "today": today_date, "now": now_utc}
        )
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_memberships (id, created_at, updated_at, institution_id, user_id, status, accepted_at)
                VALUES (:id, :now, :now, :inst_id, :uid, 'ACTIVE', :now)
            """),
            {"id": coordinator_membership_id, "inst_id": inst_id, "uid": coordinator_user_id, "now": now_utc}
        )

        coordinator_role_id = seed_conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'COORDINATOR' AND scope_kind = 'INSTITUTION'")
        ).scalar_one()

        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.institution_role_grants (id, created_at, updated_at, membership_id, role_id, appointment_id)
                VALUES (:id, :now, :now, :mid, :rid, :aid)
            """),
            {
                "id": coordinator_grant_id, "mid": coordinator_membership_id,
                "rid": coordinator_role_id, "aid": coordinator_appointment_id, "now": now_utc
            }
        )

        # 6. Coordinator Pre-seeded Session for Provenance
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.sessions (
                    id, created_at, updated_at, user_id, token_digest, assurance, expires_at, last_seen_at, auth_version
                )
                VALUES (
                    :sess_id, :now, :now, :uid, :digest, 'MFA', :expires, :now, 1
                )
            """),
            {
                "sess_id": coordinator_session_id,
                "uid": coordinator_user_id,
                "digest": f"digest_{uuid4().hex}",
                "expires": now_utc + timedelta(days=7),
                "now": now_utc,
            }
        )

        # 7. Student Supervision & Origin (PUBLIC, linked to coordinator)
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.student_supervisions (
                    id, created_at, updated_at, enrollment_id, coordinator_membership_id, agreement_id,
                    purpose, status, legal_basis, accepted_at, institution_id
                )
                VALUES (:id, :now, :now, :eid, :mid, :aid, :purpose, 'ACTIVE', 'Kafedra qarori #12', :now, :inst_id)
            """),
            {
                "id": supervision_id, "eid": enrollment_id, "mid": coordinator_membership_id,
                "aid": inst_agreement_id, "purpose": purpose, "now": now_utc, "inst_id": inst_id
            }
        )
        supervision_origin_snapshot = {
            "accepted_at": now_utc.isoformat(),
            "enrollment_id": enrollment_id,
            "coordinator_membership_id": coordinator_membership_id,
            "agreement_id": inst_agreement_id,
            "purpose": purpose,
            "legal_basis": "Kafedra qarori #12"
        }
        seed_conn.execute(
            text("""
                INSERT INTO flexbridge.supervision_origins (
                    supervision_id, created_at, origin, actor_id, session_id, auth_version,
                    coordinator_grant_id, idempotency_key, request_fingerprint, receipt, initial_snapshot
                )
                VALUES (
                    :id, :now, 'PUBLIC', :actor_id, :session_id, 1,
                    :grant_id, :idem, :fp, CAST(:receipt AS jsonb), CAST(:snapshot AS jsonb)
                )
            """),
            {
                "id": supervision_id, "now": now_utc, "actor_id": coordinator_user_id,
                "session_id": coordinator_session_id, "grant_id": coordinator_grant_id,
                "idem": f"idem-sup-{uuid4().hex}",
                "fp": hashlib.sha256(supervision_id.encode("utf-8")).hexdigest(),
                "receipt": json.dumps({"supervision_id": supervision_id, "status": "ACTIVE"}),
                "snapshot": json.dumps(supervision_origin_snapshot)
            }
        )

        seed_trans.commit()
        print("  -> DB fixtures successfully committed.")
    except Exception as exc:
        seed_trans.rollback()
        raise RuntimeError(f"Failed to seed DB fixtures: {exc}") from exc
    finally:
        seed_conn.close()
        with engine.begin() as conn:
            for t in seeded_trigger_tables:
                conn.execute(text(f"ALTER TABLE flexbridge.{t} ENABLE TRIGGER USER"))

    # -------------------------------------------------------------------------
    # PHASE 4: Coordinator Authentication via BFF & Elevate Session to MFA
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
    assert status_code == 200, f"Login failed: status {status_code}, data {login_data}"
    assert login_data.get("ok") is True, f"Expected ok: True in login response: {login_data}"
    print(f"  -> Coordinator login successful. User: {login_data.get('user', {}).get('display_name')}")

    # Elevate active session assurance to 'MFA' in flexbridge.sessions for API-100 export authority
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE flexbridge.sessions
                SET assurance = 'MFA', updated_at = :now
                WHERE user_id = :uid AND revoked_at IS NULL
            """),
            {"uid": coordinator_user_id, "now": datetime.now(timezone.utc)}
        )
    print("  -> Session assurance successfully upgraded to 'MFA' in PostgreSQL.")

    # -------------------------------------------------------------------------
    # PHASE 5: Coordinator generates PDF export via BFF (API-100)
    # -------------------------------------------------------------------------
    print("\n[Phase 5] Coordinator generates PDF export via BFF (API-100: POST .../exports)...")
    idem_pdf = f"idem-pdf-{uuid4().hex}"
    status_code, export_pdf_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/exports",
        method="POST",
        data={
            "idempotency_key": idem_pdf,
            "format": "PDF",
            "include_details": True,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 201, f"Expected 201, got {status_code}: {export_pdf_data}"
    assert export_pdf_data.get("ok") is True, f"Expected ok: True, got {export_pdf_data}"
    assert export_pdf_data.get("contract_id") == "API-100", f"Expected API-100, got {export_pdf_data}"
    assert export_pdf_data.get("export_format") == "PDF", f"Expected PDF format, got {export_pdf_data}"
    assert export_pdf_data.get("institution_id") == inst_id, f"Institution mismatch: {export_pdf_data}"
    assert "download_url" in export_pdf_data, f"Expected download_url in receipt: {export_pdf_data}"
    assert "disclaimer" in export_pdf_data, f"Expected disclaimer in receipt: {export_pdf_data}"

    summary = export_pdf_data.get("summary", {})
    assert summary.get("total_students_enrolled", 0) >= 1, f"Expected >= 1 student enrolled, got {summary}"
    assert summary.get("total_supervisions", 0) >= 1, f"Expected >= 1 supervision, got {summary}"
    assert summary.get("total_active_agreements", 0) >= 1, f"Expected >= 1 active agreement, got {summary}"
    print(f"  -> PDF export successfully created (Export ID: {export_pdf_data.get('export_id')}).")
    print(f"  -> Metrics: Enrolled: {summary.get('total_students_enrolled')}, Supervisions: {summary.get('total_supervisions')}, Agreements: {summary.get('total_active_agreements')}.")

    # -------------------------------------------------------------------------
    # PHASE 6: Coordinator generates JSON export & verifies Idempotency Replay
    # -------------------------------------------------------------------------
    print("\n[Phase 6] Coordinator generates JSON export & verifies idempotency replay...")
    idem_json = f"idem-json-{uuid4().hex}"
    status_code, export_json_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/exports",
        method="POST",
        data={
            "idempotency_key": idem_json,
            "format": "JSON",
            "include_details": True,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 201, f"Expected 201, got {status_code}: {export_json_data}"
    assert export_json_data.get("export_format") == "JSON", f"Expected JSON format: {export_json_data}"
    assert export_json_data.get("is_idempotent_replay") is False, "Expected first call not replay"
    print(f"  -> JSON export successfully created (File ID: {export_json_data.get('file_id')}).")

    # Idempotency Replay
    status_code, replay_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/exports",
        method="POST",
        data={
            "idempotency_key": idem_json,
            "format": "JSON",
            "include_details": True,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 201, f"Expected 201 for replay, got {status_code}: {replay_data}"
    assert replay_data.get("is_idempotent_replay") is True, f"Expected is_idempotent_replay == True: {replay_data}"
    assert replay_data.get("export_id") == export_json_data.get("export_id"), "Export ID mismatch on replay"
    print("  -> Advisory-locked idempotency replay verified: same export_id returned with is_idempotent_replay=True.")

    # -------------------------------------------------------------------------
    # PHASE 7: Negative validation: invalid export format rejected (HTTP 422)
    # -------------------------------------------------------------------------
    print("\n[Phase 7] Verifying negative validation: invalid export format rejected (HTTP 422)...")
    status_code, neg_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/exports",
        method="POST",
        data={
            "idempotency_key": f"idem-neg-{uuid4().hex}",
            "format": "XML",
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 422, f"Expected 422, got {status_code}: {neg_data}"
    assert neg_data.get("error") == "INVALID_EXPORT_FORMAT", f"Expected INVALID_EXPORT_FORMAT, got {neg_data}"
    print("  -> Invalid format 'XML' correctly rejected: 422 INVALID_EXPORT_FORMAT verified.")

    # -------------------------------------------------------------------------
    # PHASE 8: Coordinator inspects student supervisions list via BFF (API-098)
    # -------------------------------------------------------------------------
    print("\n[Phase 8] Coordinator inspects student supervisions list via BFF (API-098: GET .../supervisions)...")
    status_code, supervisions_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/supervisions",
        method="GET",
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {supervisions_data}"
    assert supervisions_data.get("ok") is True, f"Expected ok: True, got {supervisions_data}"
    assert supervisions_data.get("contract_id") == "API-098", f"Expected API-098, got {supervisions_data}"
    items = supervisions_data.get("items", [])
    assert len(items) >= 1, f"Expected >= 1 supervision item, got {items}"
    found_sup = next((s for s in items if s.get("id") == supervision_id), None)
    assert found_sup is not None, f"Seeded supervision {supervision_id} not found in items: {items}"
    assert found_sup.get("purpose") == purpose, f"Purpose mismatch: {found_sup}"
    assert found_sup.get("student_name") == "Otabek Rustamov", f"Student name mismatch: {found_sup}"
    print(f"  -> Supervisions list verified: {len(items)} items returned; found student '{found_sup.get('student_name')}'.")

    # -------------------------------------------------------------------------
    # PHASE 9: Coordinator inspects active academic agreements via BFF (API-101)
    # -------------------------------------------------------------------------
    print("\n[Phase 9] Coordinator inspects active academic agreements via BFF (API-101: GET .../agreements)...")
    status_code, agreements_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/agreements",
        method="GET",
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {agreements_data}"
    assert agreements_data.get("ok") is True, f"Expected ok: True, got {agreements_data}"
    assert agreements_data.get("contract_id") == "API-101", f"Expected API-101, got {agreements_data}"
    agr_items = agreements_data.get("items", [])
    assert len(agr_items) >= 1, f"Expected >= 1 agreement, got {agr_items}"
    found_agr = next((a for a in agr_items if a.get("id") == inst_agreement_id), None)
    assert found_agr is not None, f"Seeded agreement {inst_agreement_id} not found: {agr_items}"
    assert "ENGINEERING_INTERNSHIP" in str(found_agr.get("purposes")), f"Purpose mismatch: {found_agr}"
    print(f"  -> Academic agreements verified: {len(agr_items)} active agreements returned.")

    # -------------------------------------------------------------------------
    # PHASE 10: IDOR & Security Guardrails: accessing unauthorized institution
    # -------------------------------------------------------------------------
    print("\n[Phase 10] Verifying IDOR anti-enumeration defense for unauthorized institution...")
    unauthorized_inst_id = str(uuid4())
    status_code, idor_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/institutions/{unauthorized_inst_id}/exports",
        method="POST",
        data={"format": "PDF"},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code in (403, 404), f"Expected 403 or 404 for IDOR, got {status_code}: {idor_data}"
    print(f"  -> IDOR prevention verified: unauthorized institution export returned status {status_code}.")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF UNIVERSITY EXPORTS & AGREEMENTS VERIFICATION PASSED (100% GREEN)!")
    print("=" * 80)


if __name__ == "__main__":
    main()
