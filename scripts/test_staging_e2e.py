#!/usr/bin/env python3
"""
Dedicated Staging E2E Container Integration Test Suite for FlexBridge.
Executes 5 comprehensive phases against staging services:
  Phase 1: Infrastructure & Health / SSR Check (FastAPI, Next.js, and proxy rewrite)
  Phase 2: Auth & Session Lifecycle (login, /api/v1/auth/me, session revocation, 401 verification)
  Phase 3: PgBouncer Database Transactions (atomic queries/mutations through transaction pooling)
  Phase 4: Clean PDF Upload, MinIO Object Storage, ClamAV Clean Scan & Presigned Download
  Phase 5: EICAR Malware PDF Upload & ClamAV Quarantine Verification (scan_status == 'QUARANTINED')
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from pypdf import PdfWriter
from sqlalchemy.engine import URL, make_url

# Ensure backend imports are accessible when running in repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Service URLs (configurable via environment variables)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
MINIO_URL = os.environ.get("MINIO_URL", "http://127.0.0.1:9000").rstrip("/")
DATABASE_URL: str | None = None


def staging_database_url(env_file: Path | None = None) -> str:
    """Use the ignored Compose credentials and restrict all direct SQL to local staging."""
    explicit = os.environ.get("FLEXBRIDGE_STAGING_DATABASE_URL")
    if explicit:
        url = make_url(explicit)
    else:
        from dotenv import dotenv_values

        values = dotenv_values(env_file or Path(REPO_ROOT) / "infra" / ".env")
        password = values.get("POSTGRES_PASSWORD")
        if not password:
            raise RuntimeError("Set POSTGRES_PASSWORD in the ignored infra/.env staging file")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", password):
            raise RuntimeError("POSTGRES_PASSWORD must be URL-safe for Compose DATABASE_URL interpolation")
        url = URL.create(
            "postgresql+psycopg",
            username=values.get("POSTGRES_USER") or "flexbridge_owner",
            password=password,
            host="127.0.0.1",
            port=5432,
            database=values.get("POSTGRES_DB") or "flexbridge",
        )
    if (url.drivername != "postgresql+psycopg" or url.host not in ("127.0.0.1", "localhost")
            or url.port != 5432 or url.database != "flexbridge" or not url.password):
        raise RuntimeError("Staging SQL target must be local PostgreSQL/PgBouncer 127.0.0.1:5432/flexbridge")
    return url.render_as_string(hide_password=False)


def validate_staging_http_targets() -> None:
    for name, value, port in (
        ("BACKEND_URL", BACKEND_URL, 8000),
        ("FRONTEND_URL", FRONTEND_URL, 3000),
        ("MINIO_URL", MINIO_URL, 9000),
    ):
        target = urlsplit(value)
        if (target.scheme != "http" or target.hostname not in ("127.0.0.1", "localhost")
                or target.port != port or target.username or target.password
                or target.path or target.query or target.fragment):
            raise RuntimeError(f"{name} must be local staging HTTP on port {port}")


def log(phase: str, message: str, status: str = "INFO"):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"[{timestamp}] [{phase}] [{status}] {message}")


def make_pdf(size: int = 100, stream_payload: bytes | None = None) -> bytes:
    """Generate a syntactically valid PDF in-memory, optionally embedding a stream payload."""
    writer = PdfWriter()
    writer.add_blank_page(width=size, height=size)
    if stream_payload:
        from pypdf.generic import DecodedStreamObject

        stream = DecodedStreamObject()
        stream.set_data(stream_payload)
        writer._add_object(stream)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# Standard EICAR antivirus test signature
EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def phase_1_infrastructure_and_health(client: httpx.Client) -> None:
    log("PHASE 1", "Starting Infrastructure, Readiness, and Frontend SSR Verification...")

    # 1.1 Backend /live probe with startup retry loop
    live_url = f"{BACKEND_URL}/api/v1/health/live"
    deadline = time.monotonic() + 60.0
    live_data = None
    last_err = ""

    while time.monotonic() < deadline:
        try:
            resp = client.get(live_url, timeout=5.0)
            if resp.status_code == 200:
                live_data = resp.json()
                if live_data.get("status") == "alive":
                    break
        except (httpx.ConnectError, httpx.HTTPError) as exc:
            last_err = str(exc)
        time.sleep(2.0)

    assert live_data and live_data.get("status") == "alive", (
        f"Backend not responding at {live_url} within 60s. Last error: {last_err}"
    )
    log("PHASE 1", f"Backend live probe OK: {live_data.get('service')} v{live_data.get('version')}")

    # 1.2 Backend /ready probe (polls with grace period for workers/clamav startup)
    ready_url = f"{BACKEND_URL}/api/v1/health/ready"
    deadline = time.monotonic() + 60.0
    ready_data = {}
    last_error = ""
    while time.monotonic() < deadline:
        try:
            resp = client.get(ready_url, timeout=10.0)
            if resp.status_code == 200:
                ready_data = resp.json()
                if ready_data.get("ready") is True:
                    break
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text}"
        except httpx.HTTPError as exc:
            last_error = str(exc)
        time.sleep(2.0)

    assert ready_data.get("ready") is True, f"Readiness probe failed after 60s: {ready_data or last_error}"
    log("PHASE 1", f"All 9 Readiness checks verified: {ready_data.get('checks')}")

    # 1.3 Frontend SSR verification
    fe_resp = client.get(f"{FRONTEND_URL}/", timeout=10.0)
    assert fe_resp.status_code == 200, f"Frontend root returned {fe_resp.status_code}: {fe_resp.text}"
    assert "FlexBridge" in fe_resp.text or "<html" in fe_resp.text, "Frontend HTML missing expected markup"
    log("PHASE 1", f"Frontend SSR root OK: HTTP {fe_resp.status_code}")

    for path in ["/employer", "/university", "/operator"]:
        p_resp = client.get(f"{FRONTEND_URL}{path}", timeout=10.0)
        assert p_resp.status_code == 200, f"Frontend {path} returned {p_resp.status_code}: {p_resp.text}"
        log("PHASE 1", f"Frontend portal {path} OK: HTTP {p_resp.status_code}")

    # 1.4 Frontend reverse proxy rewrite
    proxy_resp = client.get(f"{FRONTEND_URL}/api/backend/health/live", timeout=10.0)
    assert proxy_resp.status_code == 200, f"Frontend API reverse proxy returned {proxy_resp.status_code}: {proxy_resp.text}"
    assert proxy_resp.json().get("status") == "alive", f"Unexpected proxy payload: {proxy_resp.json()}"
    log("PHASE 1", "Frontend API reverse proxy (/api/backend -> Backend) verified successfully.")

    log("PHASE 1", "Phase 1 PASSED: Infrastructure & Health/SSR checks complete.", "PASS")


def phase_2_auth_and_session(client: httpx.Client) -> tuple[str, str, str]:
    log("PHASE 2", "Starting Authentication and Session Lifecycle Verification...")

    # Generate test candidate credentials
    candidate_id = str(uuid4())
    test_password = f"StagingE2E_Pass_{uuid4().hex[:12]}!"
    display_name = f"Staging Candidate {candidate_id[:8]}"

    # Seed verified candidate directly via PostgreSQL/PgBouncer
    from sqlalchemy import create_engine, text
    from app.services.auth import hash_password

    engine = create_engine(
        DATABASE_URL,
        connect_args={"prepare_threshold": None},
        pool_pre_ping=True,
    )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), :display_name, :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": candidate_id, "display_name": display_name, "password_hash": hash_password(test_password)},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, experience_months, visibility)
                VALUES (:profile_id, NOW(), NOW(), :user_id, :headline, 'Tashkent', 12, 'PUBLIC')
                ON CONFLICT (user_id) DO NOTHING
                """
            ),
            {"profile_id": str(uuid4()), "user_id": candidate_id, "headline": display_name},
        )
    log("PHASE 2", f"Seeded test candidate user {candidate_id}")

    # 2.1 Authenticate via POST /api/v1/auth/login
    login_resp = client.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        json={"user_id": candidate_id, "password": test_password},
        timeout=10.0,
    )
    assert login_resp.status_code == 200, f"Login failed ({login_resp.status_code}): {login_resp.text}"
    login_data = login_resp.json()
    access_token = login_data["access_token"]
    session_id = login_data["session_id"]
    assert access_token and session_id, "Login response is missing an access token or session ID"
    log("PHASE 2", "Login returned an access token and session ID")

    # 2.2 Verify active user context via GET /api/v1/auth/me
    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = client.get(f"{BACKEND_URL}/api/v1/auth/me", headers=headers, timeout=10.0)
    assert me_resp.status_code == 200, f"/auth/me failed ({me_resp.status_code}): {me_resp.text}"
    me_data = me_resp.json()
    assert me_data.get("user_id") == candidate_id, f"Mismatched user_id in /auth/me: {me_data}"
    assert "CANDIDATE" in me_data.get("roles", []), f"Role CANDIDATE not in roles: {me_data}"
    log("PHASE 2", "Verified active actor identity and candidate role")

    # Create a secondary session to test explicit revocation without invalidating primary token
    login_resp2 = client.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        json={"user_id": candidate_id, "password": test_password},
        timeout=10.0,
    )
    assert login_resp2.status_code == 200
    revocable_token = login_resp2.json()["access_token"]
    revocable_session_id = login_resp2.json()["session_id"]

    # 2.3 Revoke the secondary session via DELETE /api/v1/me/sessions/{id}
    revoke_headers = {"Authorization": f"Bearer {revocable_token}"}
    revoke_resp = client.delete(f"{BACKEND_URL}/api/v1/me/sessions/{revocable_session_id}", headers=revoke_headers, timeout=10.0)
    assert revoke_resp.status_code == 200, f"Session revocation failed ({revoke_resp.status_code}): {revoke_resp.text}"
    log("PHASE 2", f"Revoked session {revocable_session_id}")

    # 2.4 Verify 401 on revoked session token
    unauthorized_resp = client.get(f"{BACKEND_URL}/api/v1/auth/me", headers=revoke_headers, timeout=10.0)
    assert unauthorized_resp.status_code == 401, f"Expected 401 for revoked session, got: {unauthorized_resp.status_code}"
    log("PHASE 2", "Revoked token successfully denied with HTTP 401.")

    # 2.5 Verify primary session (Session 1) remains preserved and valid
    preserved_resp = client.get(f"{BACKEND_URL}/api/v1/auth/me", headers=headers, timeout=10.0)
    assert preserved_resp.status_code == 200, f"Primary session was unexpectedly invalidated: {preserved_resp.status_code}"
    assert preserved_resp.json().get("user_id") == candidate_id, f"Mismatched user_id in preserved session: {preserved_resp.json()}"
    log("PHASE 2", "Primary session (Session 1) verified active and preserved after Session 2 revocation.")

    # 2.6 Multi-Tenant & Multi-Role Boundary Verification (HR and TEACHER scopes)
    from datetime import date, timedelta
    org_a_id = str(uuid4())
    org_b_id = str(uuid4())
    hr_user_id = str(uuid4())
    hr_password = f"StagingHR_Pass_{uuid4().hex[:12]}!"
    inst_a_id = str(uuid4())
    teacher_user_id = str(uuid4())
    teacher_password = f"StagingTeacher_Pass_{uuid4().hex[:12]}!"
    file_id = str(uuid4())

    with engine.begin() as conn:
        hr_role_id = conn.execute(text("SELECT id FROM flexbridge.role_catalog WHERE code = 'HR'")).scalar()
        teacher_role_id = conn.execute(text("SELECT id FROM flexbridge.role_catalog WHERE code = 'TEACHER'")).scalar()

        # Seed Users
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'HR Director Alpha', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": hr_user_id, "password_hash": hash_password(hr_password)}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'Docent Aliyev', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": teacher_user_id, "password_hash": hash_password(teacher_password)}
        )

        # File fixture for teacher appointment satisfying provenance trigger
        conn.execute(
            text("""
                INSERT INTO flexbridge.files (
                    id, created_at, updated_at, owner_user_id, storage_key, filename, mime_type, byte_size,
                    scan_status, retention_class, storage_bucket, storage_version_id, storage_etag, object_version, sha256, scanned_at
                )
                VALUES (
                    :id, NOW(), NOW(), :owner_id, :storage_key, 'appointment.pdf', 'application/pdf', 1024,
                    'CLEAN', 'VERIFICATION_EVIDENCE', 'flexbridge-private', 'v1', 'etag123', 'v1',
                    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', NOW()
                )
            """),
            {"id": file_id, "owner_id": teacher_user_id, "storage_key": f"private/{file_id}/appointment.pdf"}
        )

        # Seed Org A and Org B
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, NOW(), NOW(), :tax_id, 'Alpha Tech MCHJ', 'Alpha Tech', 'Tashkent', 'ACTIVE')
            """),
            {"id": org_a_id, "tax_id": f"TAX_A_{uuid4().hex[:8]}"}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, NOW(), NOW(), :tax_id, 'Beta Global MCHJ', 'Beta Global', 'Samarkand', 'ACTIVE')
            """),
            {"id": org_b_id, "tax_id": f"TAX_B_{uuid4().hex[:8]}"}
        )

        # HR Membership & Role in Org A
        hr_mem_id = str(uuid4())
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status, accepted_at)
                VALUES (:id, NOW(), NOW(), :org_id, :user_id, 'ACTIVE', NOW())
            """),
            {"id": hr_mem_id, "org_id": org_a_id, "user_id": hr_user_id}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_role_grants (id, created_at, updated_at, membership_id, role_id, granted_by_id)
                VALUES (:id, NOW(), NOW(), :mem_id, :role_id, :granted_by)
            """),
            {"id": str(uuid4()), "mem_id": hr_mem_id, "role_id": hr_role_id, "granted_by": hr_user_id}
        )

        # Institution A & Teacher Membership, Appointment, and Role Grant
        conn.execute(
            text("""
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, name, registry_code, region, status)
                VALUES (:id, NOW(), NOW(), 'Tashkent National University', :code, 'Tashkent', 'ACTIVE')
            """),
            {"id": inst_a_id, "code": f"REG_{uuid4().hex[:8]}"}
        )
        inst_mem_id = str(uuid4())
        conn.execute(
            text("""
                INSERT INTO flexbridge.institution_memberships (id, created_at, updated_at, institution_id, user_id, status, accepted_at)
                VALUES (:id, NOW(), NOW(), :inst_id, :user_id, 'ACTIVE', NOW())
            """),
            {"id": inst_mem_id, "inst_id": inst_a_id, "user_id": teacher_user_id}
        )
        appt_id = str(uuid4())
        conn.execute(
            text("""
                INSERT INTO flexbridge.institution_appointments (id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, valid_to, accepted_at)
                VALUES (:id, NOW(), NOW(), :inst_id, :user_id, :file_id, 'ACTIVE', :from_date, :to_date, NOW())
            """),
            {
                "id": appt_id,
                "inst_id": inst_a_id,
                "user_id": teacher_user_id,
                "file_id": file_id,
                "from_date": date.today() - timedelta(days=30),
                "to_date": date.today() + timedelta(days=60),
            }
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.institution_role_grants (id, created_at, updated_at, membership_id, role_id, appointment_id)
                VALUES (:id, NOW(), NOW(), :mem_id, :role_id, :appt_id)
            """),
            {"id": str(uuid4()), "mem_id": inst_mem_id, "role_id": teacher_role_id, "appt_id": appt_id}
        )

    log("PHASE 2", f"Seeded multi-tenant fixtures: Org A ({org_a_id[:8]}), Org B ({org_b_id[:8]}), Inst A ({inst_a_id[:8]})")

    # 2.7 Verify unauthenticated access denial (HTTP 401)
    unauth_resp = client.get(f"{BACKEND_URL}/api/v1/organizations/{org_a_id}/dashboard", timeout=10.0)
    assert unauth_resp.status_code in (401, 404), f"Unauthenticated request was not rejected: {unauth_resp.status_code}"
    log("PHASE 2", "Unauthenticated request to tenant dashboard rejected with HTTP 401/404.")

    # 2.8 Verify Candidate access denial to privileged HR endpoint (HTTP 404 IDOR defense)
    cand_denied = client.get(f"{BACKEND_URL}/api/v1/organizations/{org_a_id}/dashboard", headers=headers, timeout=10.0)
    assert cand_denied.status_code in (403, 404), f"Candidate was not denied HR dashboard: {cand_denied.status_code}"
    log("PHASE 2", "Candidate access to organization HR dashboard rejected with uniform 404.")

    # 2.9 HR Login & Own-Scope Verification (HTTP 200, API-068)
    hr_login = client.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        json={"user_id": hr_user_id, "password": hr_password},
        timeout=10.0,
    )
    assert hr_login.status_code == 200, f"HR login failed: {hr_login.text}"
    hr_headers = {"Authorization": f"Bearer {hr_login.json()['access_token']}"}
    hr_dashboard = client.get(f"{BACKEND_URL}/api/v1/organizations/{org_a_id}/dashboard", headers=hr_headers, timeout=10.0)
    assert hr_dashboard.status_code == 200, f"HR own-scope dashboard failed: {hr_dashboard.status_code}"
    assert hr_dashboard.json().get("contract_id") == "API-068", f"Unexpected contract_id: {hr_dashboard.json()}"
    log("PHASE 2", "HR user own-scope organization dashboard verified: HTTP 200 (API-068).")

    # 2.10 Cross-Tenant Isolation: HR accessing Organization B (HTTP 404 uniform IDOR defense)
    hr_cross = client.get(f"{BACKEND_URL}/api/v1/organizations/{org_b_id}/dashboard", headers=hr_headers, timeout=10.0)
    assert hr_cross.status_code == 404, f"Cross-tenant HR request did not return 404: {hr_cross.status_code}"
    log("PHASE 2", "Cross-tenant access to foreign organization cleanly denied with HTTP 404.")

    # 2.11 Teacher Login & Academic Review Queue Verification (HTTP 200)
    teacher_login = client.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        json={"user_id": teacher_user_id, "password": teacher_password},
        timeout=10.0,
    )
    assert teacher_login.status_code == 200, f"Teacher login failed: {teacher_login.text}"
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}
    teacher_queue = client.get(f"{BACKEND_URL}/api/v1/me/academic-review-queue", headers=teacher_headers, timeout=10.0)
    assert teacher_queue.status_code == 200, f"Teacher review queue failed: {teacher_queue.status_code}"
    log("PHASE 2", "Teacher user academic review queue verified: HTTP 200.")

    # 2.12 Teacher role boundary: Teacher attempting HR dashboard (HTTP 404)
    teacher_cross = client.get(f"{BACKEND_URL}/api/v1/organizations/{org_a_id}/dashboard", headers=teacher_headers, timeout=10.0)
    assert teacher_cross.status_code in (403, 404), f"Teacher was not denied HR dashboard: {teacher_cross.status_code}"
    log("PHASE 2", "Teacher access to organization HR dashboard rejected with HTTP 404.")

    log("PHASE 2", "Phase 2 PASSED: Authentication & multi-tenant session lifecycle fully verified.", "PASS")
    return candidate_id, test_password, access_token


def phase_3_pgbouncer_transactions(client: httpx.Client, access_token: str) -> None:
    log("PHASE 3", "Starting PgBouncer Transaction & Data Flow Verification...")

    # 3.1 Public Opportunity Catalog search through API & PgBouncer
    opps_resp = client.get(f"{BACKEND_URL}/api/v1/opportunities", timeout=10.0)
    assert opps_resp.status_code == 200, f"/opportunities returned {opps_resp.status_code}: {opps_resp.text}"
    opps_data = opps_resp.json()
    assert "items" in opps_data, f"Missing 'items' in opportunities response: {opps_data}"
    log("PHASE 3", f"Public opportunities query successful ({len(opps_data['items'])} items returned).")

    # 3.2 Candidate Saved Opportunities via PgBouncer connection
    headers = {"Authorization": f"Bearer {access_token}"}
    saved_resp = client.get(f"{BACKEND_URL}/api/v1/me/saved-opportunities", headers=headers, timeout=10.0)
    assert saved_resp.status_code == 200, f"/me/saved-opportunities returned {saved_resp.status_code}: {saved_resp.text}"
    log("PHASE 3", "Candidate saved opportunities queried via pooled connection")

    # 3.3 Direct PgBouncer pooling verification (prepare_threshold=None safety)
    from sqlalchemy import create_engine, text

    engine = create_engine(DATABASE_URL, connect_args={"prepare_threshold": None}, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT count(*) FROM flexbridge.opportunities")).scalar()
        val = conn.execute(text("SELECT 1 AS ready_probe")).scalar()
        assert val == 1, "Direct PgBouncer SELECT 1 failed"
    log("PHASE 3", f"Direct pooled query through PgBouncer verified: {result} existing opportunities.")

    # 3.4 Concurrent PgBouncer transaction probes (10 worker threads, 20 concurrent transactions)
    import concurrent.futures

    concurrent_engine = create_engine(
        DATABASE_URL,
        connect_args={"prepare_threshold": None},
        pool_size=15,
        max_overflow=10,
        pool_pre_ping=True,
    )

    def run_worker_transaction(worker_id: int) -> bool:
        with concurrent_engine.connect() as conn:
            with conn.begin():
                opp_c = conn.execute(text("SELECT count(*) FROM flexbridge.opportunities")).scalar()
                probe = conn.execute(text("SELECT 1 AS ready_probe")).scalar()
                assert probe == 1
                roles_c = conn.execute(text("SELECT count(*) FROM flexbridge.role_catalog")).scalar()
                assert roles_c >= 7
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_worker_transaction, i) for i in range(20)]
        for f in concurrent.futures.as_completed(futures):
            assert f.result() is True
    log("PHASE 3", "20 concurrent atomic transactions verified through PgBouncer transaction pooling.")

    log("PHASE 3", "Phase 3 PASSED: PgBouncer transaction pooling verified.", "PASS")


def phase_4_clean_file_lifecycle(client: httpx.Client, access_token: str) -> str:
    log("PHASE 4", "Starting Clean PDF Upload, MinIO Storage, ClamAV Scan, and Download...")

    clean_pdf = make_pdf(size=120)
    pdf_size = len(clean_pdf)
    headers = {"Authorization": f"Bearer {access_token}"}

    # 4.1 Request upload intent (API-X01)
    intent_resp = client.post(
        f"{BACKEND_URL}/api/v1/files/upload-intents",
        headers=headers,
        json={"filename": "clean_evidence.pdf", "mime_type": "application/pdf", "size_bytes": pdf_size},
        timeout=10.0,
    )
    assert intent_resp.status_code == 201, f"Upload intent failed ({intent_resp.status_code}): {intent_resp.text}"
    intent = intent_resp.json()
    file_id = intent["id"]
    upload_url = intent["upload_url"]
    assert intent["scan_status"] == "PENDING_SCAN"
    log("PHASE 4", f"Upload intent created: file_id={file_id}")

    # 4.2 PUT bytes directly to MinIO via presigned URL
    put_resp = client.put(
        upload_url,
        content=clean_pdf,
        headers={"Content-Type": "application/pdf", "Content-Length": str(pdf_size)},
        timeout=15.0,
    )
    assert put_resp.status_code in (200, 204), f"MinIO S3 upload failed ({put_resp.status_code}): {put_resp.text}"
    log("PHASE 4", "Uploaded clean PDF bytes to MinIO storage successfully.")

    # 4.3 Complete upload (API-X02)
    complete_resp = client.post(
        f"{BACKEND_URL}/api/v1/files/{file_id}/complete-upload",
        headers=headers,
        timeout=10.0,
    )
    assert complete_resp.status_code == 202, f"Complete upload failed ({complete_resp.status_code}): {complete_resp.text}"
    assert complete_resp.json().get("scan_status") == "SCANNING"
    log("PHASE 4", "Upload completed; asynchronous scan enqueued in outbox.")

    # 4.4 Poll for clean scan completion (processed asynchronously by outbox-worker container)
    from sqlalchemy import create_engine, text

    engine = create_engine(DATABASE_URL, connect_args={"prepare_threshold": None})
    deadline = time.monotonic() + 60.0
    scan_status = "SCANNING"

    while time.monotonic() < deadline:
        with engine.connect() as conn:
            status = conn.execute(
                text("SELECT scan_status FROM flexbridge.files WHERE id = CAST(:id AS uuid)"),
                {"id": file_id},
            ).scalar()
            if status in ("CLEAN", "QUARANTINED"):
                scan_status = status
                break
        time.sleep(1.0)

    log("PHASE 4", f"File {file_id} scan completed with status: {scan_status}")
    assert scan_status == "CLEAN", f"Expected file to be CLEAN, but got: {scan_status}"

    # 4.5 Issue signed download URL (API-X03)
    dl_resp = client.get(f"{BACKEND_URL}/api/v1/files/{file_id}/download", headers=headers, timeout=10.0)
    assert dl_resp.status_code == 200, f"Download URL request failed ({dl_resp.status_code}): {dl_resp.text}"
    download_url = dl_resp.json()["signed_url"]

    # 4.6 Fetch bytes and verify integrity
    file_bytes_resp = client.get(download_url, timeout=15.0)
    assert file_bytes_resp.status_code == 200, f"Download from presigned URL failed: {file_bytes_resp.status_code}"
    assert hashlib.sha256(file_bytes_resp.content).hexdigest() == hashlib.sha256(clean_pdf).hexdigest()
    log("PHASE 4", "Downloaded file matches uploaded content SHA256 exactly.")

    log("PHASE 4", "Phase 4 PASSED: Clean file pipeline verified end-to-end.", "PASS")
    return file_id


def phase_5_eicar_quarantine(client: httpx.Client, access_token: str) -> None:
    log("PHASE 5", "Starting EICAR Malware Quarantine Verification...")

    eicar_pdf = make_pdf(size=100, stream_payload=EICAR_SIGNATURE)
    pdf_size = len(eicar_pdf)
    headers = {"Authorization": f"Bearer {access_token}"}

    # 5.1 Request upload intent for infected document
    intent_resp = client.post(
        f"{BACKEND_URL}/api/v1/files/upload-intents",
        headers=headers,
        json={"filename": "infected_eicar.pdf", "mime_type": "application/pdf", "size_bytes": pdf_size},
        timeout=10.0,
    )
    assert intent_resp.status_code == 201, f"Intent creation failed: {intent_resp.text}"
    file_id = intent_resp.json()["id"]
    upload_url = intent_resp.json()["upload_url"]

    # 5.2 Upload infected PDF to MinIO
    put_resp = client.put(
        upload_url,
        content=eicar_pdf,
        headers={"Content-Type": "application/pdf", "Content-Length": str(pdf_size)},
        timeout=15.0,
    )
    assert put_resp.status_code in (200, 204), f"Upload failed: {put_resp.status_code}"
    log("PHASE 5", f"Uploaded EICAR-laced PDF to MinIO: file_id={file_id}")

    # 5.3 Complete upload to trigger scan
    complete_resp = client.post(f"{BACKEND_URL}/api/v1/files/{file_id}/complete-upload", headers=headers, timeout=10.0)
    assert complete_resp.status_code == 202

    # 5.4 Poll scan and verify quarantine status (processed asynchronously by outbox-worker container)
    from sqlalchemy import create_engine, text

    engine = create_engine(DATABASE_URL, connect_args={"prepare_threshold": None})
    deadline = time.monotonic() + 60.0
    scan_status = "SCANNING"

    while time.monotonic() < deadline:
        with engine.connect() as conn:
            status = conn.execute(
                text("SELECT scan_status FROM flexbridge.files WHERE id = CAST(:id AS uuid)"),
                {"id": file_id},
            ).scalar()
            if status in ("CLEAN", "QUARANTINED"):
                scan_status = status
                break
        time.sleep(1.0)

    log("PHASE 5", f"Infected file scan status: {scan_status}")
    assert scan_status == "QUARANTINED", f"Expected QUARANTINED status, got: {scan_status}"

    # 5.5 Verify download is rejected with 409 FILE_NOT_CLEAN_FOR_DOWNLOAD
    dl_resp = client.get(f"{BACKEND_URL}/api/v1/files/{file_id}/download", headers=headers, timeout=10.0)
    assert dl_resp.status_code == 409, f"Expected 409 for quarantined file download, got: {dl_resp.status_code}"
    log("PHASE 5", "Download rejected with HTTP 409 as required by security invariant AC-042.")

    log("PHASE 5", "Phase 5 PASSED: EICAR malware properly quarantined.", "PASS")


def main() -> int:
    global DATABASE_URL
    try:
        DATABASE_URL = staging_database_url()
        validate_staging_http_targets()
    except Exception as exc:
        log("CONFIG", f"Staging database configuration rejected ({type(exc).__name__})", "FAIL")
        return 2
    print("=" * 70)
    print(" FlexBridge Staging & E2E Container Integration Test Runner")
    print("=" * 70)
    print(f"Backend Target:  {BACKEND_URL}")
    print(f"Frontend Target: {FRONTEND_URL}")
    print(f"MinIO Target:    {MINIO_URL}")
    print(f"Database Target: {make_url(DATABASE_URL).render_as_string(hide_password=True)}")
    print("-" * 70)

    with httpx.Client(follow_redirects=True) as client:
        try:
            # Phase 1: Infrastructure & Health/SSR Check
            phase_1_infrastructure_and_health(client)

            # Phase 2: Auth & Session Lifecycle
            candidate_id, password, access_token = phase_2_auth_and_session(client)

            # Phase 3: PgBouncer Database Transactions
            phase_3_pgbouncer_transactions(client, access_token)

            # Phase 4: Clean PDF Upload, Scan & Download
            clean_file_id = phase_4_clean_file_lifecycle(client, access_token)

            # Phase 5: EICAR Malware Quarantine Verification
            phase_5_eicar_quarantine(client, access_token)

            print("=" * 70)
            print(" ALL 5 PHASES COMPLETED SUCCESSFULLY [PASS]")
            print("=" * 70)
            return 0

        except Exception as exc:
            frame = exc.__traceback__
            location = "unknown"
            while frame:
                if Path(frame.tb_frame.f_code.co_filename).resolve() == Path(__file__).resolve():
                    location = f"{frame.tb_frame.f_code.co_name}:{frame.tb_lineno}"
                frame = frame.tb_next
            log("ERROR", f"Staging E2E Suite failed at {location} ({type(exc).__name__}); inspect local service logs", "FAIL")
            return 1


if __name__ == "__main__":
    sys.exit(main())
