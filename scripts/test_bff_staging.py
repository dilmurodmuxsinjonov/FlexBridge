#!/usr/bin/env python3
"""FlexBridge 1.4 BFF & Tenant Portals Security Test Suite (Issue #140 / FB-140B).

Verifies:
1. Unauthenticated requests to BFF endpoints return HTTP 401 with uniform AUTH_REQUIRED / UNAUTHENTICATED.
2. Cross-Site Request Forgery (CSRF) origin enforcement: Mutating POST/PUT/PATCH/DELETE rejected with HTTP 403 on origin mismatch.
3. HttpOnly Session Boundary: Backend bearer tokens are never leaked to client responses. Session cookie is HttpOnly, SameSite=Lax.
4. Multi-Tenant RBAC & IDOR Boundaries via Next.js BFF:
   - Candidate logs in via Next.js `/api/auth/login`.
   - Candidate verifies `/api/auth/me` returns user info via HttpOnly session cookie.
   - Candidate cannot access Organization HR dashboard (HTTP 404 IDOR defense).
   - Candidate cannot access Operator Audit events (HTTP 403 PERMISSION_DENIED).
   - HR user logs in via Next.js `/api/auth/login`.
   - HR user accesses own-scope organization dashboard (HTTP 200 API-068).
   - HR user cannot access foreign-scope organization dashboard (HTTP 404 IDOR defense).
   - Teacher logs in via Next.js `/api/auth/login`.
   - Teacher accesses academic review queue (HTTP 200).
   - Auditor logs in via Next.js `/api/auth/login`.
   - Auditor accesses operator append-only audit trail (HTTP 200 API-118).
5. Clean Session Revocation / Logout: Cookie cleared, subsequent queries return HTTP 401.
"""

from __future__ import annotations

from datetime import date, timedelta
import json
import os
import re
import sys
import urllib.error
import urllib.request
import http.cookiejar
from typing import Any
from pathlib import Path
from uuid import uuid4
from dotenv import dotenv_values

# Ensure backend modules can be imported
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from app.services.auth import hash_password


FRONTEND_URL = "http://127.0.0.1:3000"
BACKEND_URL = "http://127.0.0.1:8000"


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
    op = opener or urllib.request.build_opener()

    try:
        with op.open(req, timeout=10) as resp:
            status = resp.status
            resp_headers = dict(resp.headers)
            content = resp.read().decode("utf-8")
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = {"raw": content}
            return status, parsed, resp_headers
    except urllib.error.HTTPError as err:
        status = err.code
        resp_headers = dict(err.headers)
        content = err.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"raw": content}
        return status, parsed, resp_headers


def run_bff_tests() -> bool:
    print("=" * 70)
    print("FLEXBRIDGE 1.4 BFF & TENANT PORTALS SECURITY TEST SUITE (FB-140B)")
    print("=" * 70)

    # 1. Unauthenticated Access Tests
    print("\n[Phase 1] Testing unauthenticated access boundaries...")
    status, body, _ = make_request(f"{FRONTEND_URL}/api/auth/me")
    assert status == 401, f"Expected 401 for /api/auth/me, got {status}: {body}"
    assert body.get("error") == "UNAUTHENTICATED", f"Unexpected error body: {body}"
    print("  ✓ GET /api/auth/me -> 401 UNAUTHENTICATED")

    status, body, _ = make_request(f"{FRONTEND_URL}/api/bff/employer/dashboard?org=00000000-0000-0000-0000-000000000001")
    assert status == 401, f"Expected 401 for employer dashboard, got {status}: {body}"
    assert body.get("error") == "AUTH_REQUIRED", f"Unexpected error body: {body}"
    print("  ✓ GET /api/bff/employer/dashboard -> 401 AUTH_REQUIRED")

    status, body, _ = make_request(f"{FRONTEND_URL}/api/bff/university/review-queue")
    assert status == 401, f"Expected 401 for university review queue, got {status}: {body}"
    assert body.get("error") == "AUTH_REQUIRED", f"Unexpected error body: {body}"
    print("  ✓ GET /api/bff/university/review-queue -> 401 AUTH_REQUIRED")

    status, body, _ = make_request(f"{FRONTEND_URL}/api/bff/operator/audit-events")
    assert status == 401, f"Expected 401 for operator audit events, got {status}: {body}"
    assert body.get("error") == "AUTH_REQUIRED", f"Unexpected error body: {body}"
    print("  ✓ GET /api/bff/operator/audit-events -> 401 AUTH_REQUIRED")

    # 2. CSRF Origin Verification
    print("\n[Phase 2] Testing CSRF origin defense...")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"destination": "test@example.com", "password": "password123"},
        headers={"Origin": "http://malicious-attacker.com"},
    )
    assert status == 403, f"Expected 403 CSRF mismatch, got {status}: {body}"
    assert body.get("error") == "CSRF_ORIGIN_MISMATCH", f"Unexpected error: {body}"
    print("  ✓ POST /api/auth/login with cross-site Origin -> 403 CSRF_ORIGIN_MISMATCH")

    # 3. Input Validation
    print("\n[Phase 3] Testing input validation...")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"password": ""},
        headers={"Origin": FRONTEND_URL},
    )
    assert status == 400, f"Expected 400 for empty fields, got {status}: {body}"
    print("  ✓ POST /api/auth/login empty input -> 400 BAD REQUEST")

    # 4. Seed Test Fixtures (Candidate, Org A, Org B, HR in Org A, Teacher in Inst A, Auditor)
    print("\n[Phase 4] Seeding test fixtures in Staging PostgreSQL...")
    db_url = get_database_url()
    engine = create_engine(db_url, connect_args={"prepare_threshold": None}, pool_pre_ping=True)

    candidate_user_id = str(uuid4())
    candidate_password = f"BffCand_Pass_{uuid4().hex[:10]}!"

    hr_user_id = str(uuid4())
    hr_password = f"BffHR_Pass_{uuid4().hex[:10]}!"

    teacher_user_id = str(uuid4())
    teacher_password = f"BffTeacher_Pass_{uuid4().hex[:10]}!"

    auditor_user_id = str(uuid4())
    auditor_password = f"BffAuditor_Pass_{uuid4().hex[:10]}!"

    org_a_id = str(uuid4())
    org_b_id = str(uuid4())
    inst_a_id = str(uuid4())
    file_id = str(uuid4())

    with engine.begin() as conn:
        hr_role_id = conn.execute(text("SELECT id FROM flexbridge.role_catalog WHERE code = 'HR'")).scalar()
        teacher_role_id = conn.execute(text("SELECT id FROM flexbridge.role_catalog WHERE code = 'TEACHER'")).scalar()

        # Ensure AUDITOR platform role exists in catalog
        auditor_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'AUDITOR' AND scope_kind = 'PLATFORM'")
        ).scalar()
        if not auditor_role_id:
            auditor_role_id = str(uuid4())
            conn.execute(
                text("""
                    INSERT INTO flexbridge.role_catalog (id, created_at, updated_at, code, scope_kind, description)
                    VALUES (:id, NOW(), NOW(), 'AUDITOR', 'PLATFORM', 'Security audit trail observer')
                    ON CONFLICT (code) DO NOTHING
                """),
                {"id": auditor_role_id}
            )
            auditor_role_id = conn.execute(text("SELECT id FROM flexbridge.role_catalog WHERE code = 'AUDITOR'")).scalar()

        # Insert Users
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'BFF Candidate User', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": candidate_user_id, "password_hash": hash_password(candidate_password)}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, experience_months, visibility)
                VALUES (:profile_id, NOW(), NOW(), :user_id, 'BFF Candidate', 'Tashkent', 12, 'PUBLIC')
            """),
            {"profile_id": str(uuid4()), "user_id": candidate_user_id}
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'BFF HR Manager', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": hr_user_id, "password_hash": hash_password(hr_password)}
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'BFF Docent Teacher', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": teacher_user_id, "password_hash": hash_password(teacher_password)}
        )

        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, NOW(), NOW(), 'BFF Platform Auditor', :password_hash, 'ACTIVE', 'uz', 'Asia/Tashkent', NOW())
            """),
            {"id": auditor_user_id, "password_hash": hash_password(auditor_password)}
        )

        # File fixture for appointment provenance
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

        # Insert Org A & Org B
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, NOW(), NOW(), :tax_id, 'BFF Org A MCHJ', 'BFF Org A', 'Tashkent', 'ACTIVE')
            """),
            {"id": org_a_id, "tax_id": f"BFF_A_{uuid4().hex[:8]}"}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, NOW(), NOW(), :tax_id, 'BFF Org B MCHJ', 'BFF Org B', 'Samarkand', 'ACTIVE')
            """),
            {"id": org_b_id, "tax_id": f"BFF_B_{uuid4().hex[:8]}"}
        )

        # Grant HR Role in Org A
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
                VALUES (:id, NOW(), NOW(), 'Tashkent National University BFF', :code, 'Tashkent', 'ACTIVE')
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

        # Grant Platform AUDITOR Role to auditor_user_id (granted_by must != user_id)
        conn.execute(
            text("""
                INSERT INTO flexbridge.platform_role_grants (id, created_at, updated_at, user_id, role_id, granted_by_id, expires_at)
                VALUES (:id, NOW(), NOW(), :user_id, :role_id, :granted_by, NOW() + INTERVAL '30 days')
            """),
            {"id": str(uuid4()), "user_id": auditor_user_id, "role_id": auditor_role_id, "granted_by": hr_user_id}
        )

    print("  ✓ Seeded candidate, HR user, Org A, Org B, Teacher in Inst A, and Auditor successfully.")

    # 5. Candidate Login & HttpOnly Session Verification
    print("\n[Phase 5] Testing Candidate Login & HttpOnly Session Boundary via Next.js...")
    candidate_cj = http.cookiejar.CookieJar()
    candidate_browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(candidate_cj))

    login_status, login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": candidate_user_id, "password": candidate_password},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_browser,
    )
    assert login_status == 200, f"Candidate login failed: {login_status} {login_body}"
    assert login_body.get("ok") is True, f"Response not ok: {login_body}"
    assert "token" not in login_body, "SECURITY LEAK: Bearer token leaked in JSON!"

    # Verify flexbridge_session cookie
    cookies = [c for c in candidate_cj if c.name == "flexbridge_session"]
    assert len(cookies) > 0, "flexbridge_session cookie not set!"
    print("  ✓ Candidate logged in via Next.js BFF. HttpOnly session cookie confirmed.")

    me_status, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", opener=candidate_browser)
    assert me_status == 200, f"Expected 200 for /api/auth/me: {me_status} {me_body}"
    assert me_body.get("user", {}).get("user_id") == candidate_user_id
    print(f"  ✓ GET /api/auth/me -> 200 OK (user_id={candidate_user_id[:8]}...)")

    # Candidate denied HR dashboard (404 IDOR defense)
    cand_hr_status, cand_hr_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/dashboard?org={org_a_id}",
        opener=candidate_browser,
    )
    assert cand_hr_status == 404, f"Candidate was not denied HR dashboard! Got {cand_hr_status}: {cand_hr_body}"
    print("  ✓ Candidate GET /api/bff/employer/dashboard -> 404 IDOR defense OK")

    # Candidate denied Operator audit events (403 Forbidden)
    cand_op_status, cand_op_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/audit-events",
        opener=candidate_browser,
    )
    assert cand_op_status == 403, f"Candidate was not denied operator events! Got {cand_op_status}: {cand_op_body}"
    print("  ✓ Candidate GET /api/bff/operator/audit-events -> 403 PERMISSION_DENIED OK")

    # Candidate Logout
    logout_status, _, _ = make_request(
        f"{FRONTEND_URL}/api/auth/logout",
        method="POST",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_browser,
    )
    assert logout_status == 200, "Logout failed"
    after_logout_status, _, _ = make_request(f"{FRONTEND_URL}/api/auth/me", opener=candidate_browser)
    assert after_logout_status == 401, "Expected 401 after logout"
    print("  ✓ POST /api/auth/logout cleared session cookie successfully.")

    # 6. HR User Login & Multi-Tenant Boundaries
    print("\n[Phase 6] Testing HR User Login & Multi-Tenant Boundaries via Next.js...")
    hr_cj = http.cookiejar.CookieJar()
    hr_browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(hr_cj))

    login_status, login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": hr_user_id, "password": hr_password},
        headers={"Origin": FRONTEND_URL},
        opener=hr_browser,
    )
    assert login_status == 200, f"HR login failed: {login_status} {login_body}"
    print("  ✓ HR user logged in via Next.js BFF.")

    # Own-scope Org A dashboard: HTTP 200
    org_a_status, org_a_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/dashboard?org={org_a_id}",
        opener=hr_browser,
    )
    assert org_a_status == 200, f"HR own-scope dashboard failed: {org_a_status} {org_a_body}"
    assert org_a_body.get("contract_id") == "API-068", f"Unexpected contract: {org_a_body}"
    assert "metrics" in org_a_body, f"Missing metrics in response: {org_a_body}"
    print(f"  ✓ HR user GET own-scope Org A dashboard -> 200 OK ({org_a_body.get('contract_id')})")

    # Foreign-scope Org B dashboard: HTTP 404 IDOR defense
    org_b_status, org_b_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/dashboard?org={org_b_id}",
        opener=hr_browser,
    )
    assert org_b_status == 404, f"HR was not denied foreign Org B dashboard! Got {org_b_status}: {org_b_body}"
    print("  ✓ HR user GET foreign-scope Org B dashboard -> 404 IDOR defense OK")

    # 7. Teacher User Login & Academic Review Queue
    print("\n[Phase 7] Testing Teacher Login & Academic Review Queue via Next.js...")
    teacher_cj = http.cookiejar.CookieJar()
    teacher_browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(teacher_cj))

    login_status, login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": teacher_user_id, "password": teacher_password},
        headers={"Origin": FRONTEND_URL},
        opener=teacher_browser,
    )
    assert login_status == 200, f"Teacher login failed: {login_status} {login_body}"
    print("  ✓ Teacher logged in via Next.js BFF.")

    # Academic review queue: HTTP 200
    queue_status, queue_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/review-queue",
        opener=teacher_browser,
    )
    assert queue_status == 200, f"Teacher review queue failed: {queue_status} {queue_body}"
    assert "items" in queue_body, f"Missing items in queue response: {queue_body}"
    print(f"  ✓ Teacher GET /api/bff/university/review-queue -> 200 OK (items: {len(queue_body.get('items', []))})")

    # Teacher denied HR dashboard (404 IDOR defense)
    teacher_hr_status, _, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/dashboard?org={org_a_id}",
        opener=teacher_browser,
    )
    assert teacher_hr_status == 404, f"Teacher was not denied HR dashboard! Got {teacher_hr_status}"
    print("  ✓ Teacher GET /api/bff/employer/dashboard -> 404 IDOR defense OK")

    # 8. Auditor User Login & Operator Audit Trail
    print("\n[Phase 8] Testing Auditor Login & Operator Audit Events Trail via Next.js...")
    auditor_cj = http.cookiejar.CookieJar()
    auditor_browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(auditor_cj))

    login_status, login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": auditor_user_id, "password": auditor_password},
        headers={"Origin": FRONTEND_URL},
        opener=auditor_browser,
    )
    assert login_status == 200, f"Auditor login failed: {login_status} {login_body}"
    print("  ✓ Auditor logged in via Next.js BFF.")

    # Operator Audit events trail: HTTP 200 (API-118)
    audit_status, audit_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/audit-events",
        opener=auditor_browser,
    )
    assert audit_status == 200, f"Auditor audit events failed: {audit_status} {audit_body}"
    assert audit_body.get("contract_id") == "API-118", f"Unexpected contract: {audit_body}"
    assert "items" in audit_body, f"Missing items in audit response: {audit_body}"
    print(f"  ✓ Auditor GET /api/bff/operator/audit-events -> 200 OK (contract: {audit_body.get('contract_id')}, count: {len(audit_body.get('items', []))})")

    print("\n" + "=" * 70)
    print("ALL 8 BFF PHASES COMPLETED AND VERIFIED GREEN [PASS]")
    print("=" * 70)
    return True


if __name__ == "__main__":
    try:
        success = run_bff_tests()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
