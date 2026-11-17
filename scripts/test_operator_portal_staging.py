#!/usr/bin/env python3
"""
Staging Verification Suite: Platform Operator Portal, Verification Cases,
Break-Glass Privileged Access & Emergency Session Revocation (FB-156)

Contracts Verified:
- API-118: GET /api/v1/operator/audit-events (CAP-036 / ADMIN_AUDIT)
- API-109: GET /api/v1/operator/verification-cases (CAP-036 / MODERATOR)
- API-110: POST /api/v1/operator/verification-cases/{id}/decide (CAP-036 / MODERATOR)
- API-119: POST /api/v1/operator/access-requests (CAP-036 / ADMIN)
- API-120: POST /api/v1/operator/users/{id}/revoke-sessions (CAP-036 / ADMIN)

Phases:
1. Unauthenticated rejection (401 AUTH_REQUIRED) across all operator BFF endpoints.
2. Fixture seeding via PgBouncer (Admin, Approver, Target user, active session, org case, audit event).
3. Operator authentication via Next.js BFF (/api/auth/login) with MFA assurance.
4. Cryptographic audit event stream query and filtering (API-118).
5. Operator verification queue listing (API-109).
6. Verification case claim & decision with input validation (API-110).
7. Break-glass 4-eyes privileged access request & dual-control validation (API-119).
8. Emergency target user session revocation & invalidation verification (API-120).
9. CSRF origin mismatch rejection on all mutating operator BFF endpoints (403).

Tested against:
- Live Next.js BFF at http://127.0.0.1:3000
- PgBouncer at 127.0.0.1:5432/flexbridge (prepare_threshold=None)
"""

import json
import os
import sys
import secrets
from datetime import datetime, timezone, timedelta
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


def run_operator_staging_suite():
    print("=" * 80)
    print("Starting FlexBridge 1.4 Staging Suite: Operator Portal Workflows (FB-156)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_suffix = uuid4().hex[:8]
    admin_user_id = str(uuid4())
    admin_email = f"operator-{test_suffix}@flexbridge.uz"
    admin_password = "OperatorAdminPass123!"
    admin_hash = hash_password(admin_password)

    approver_user_id = str(uuid4())
    approver_email = f"approver-{test_suffix}@flexbridge.uz"
    approver_password = "ApproverAdminPass123!"
    approver_hash = hash_password(approver_password)

    target_user_id = str(uuid4())
    target_email = f"target-{test_suffix}@flexbridge.uz"
    target_password = "TargetUserPass123!"
    target_hash = hash_password(target_password)

    target_session_id = str(uuid4())
    target_session_token = f"tok_test_{uuid4().hex}"
    import hashlib
    target_token_digest = f"sha256:{hashlib.sha256(target_session_token.encode('utf-8')).hexdigest()}"

    org_id = str(uuid4())
    org_membership_id = str(uuid4())
    case_id = str(uuid4())
    audit_event_id = str(uuid4())

    now_utc = datetime.now(timezone.utc)
    due_at = now_utc + timedelta(days=2)

    # --------------------------------------------------------------------------
    # PHASE 1: Unauthenticated rejection across all operator BFF endpoints
    # --------------------------------------------------------------------------
    print("\n[Phase 1] Verifying unauthenticated rejections (401 AUTH_REQUIRED)...")
    unauth_endpoints = [
        ("GET", f"{FRONTEND_URL}/api/bff/operator/audit-events", None),
        ("GET", f"{FRONTEND_URL}/api/bff/operator/verification-cases", None),
        ("POST", f"{FRONTEND_URL}/api/bff/operator/verification-cases/{case_id}/claim", {}),
        ("POST", f"{FRONTEND_URL}/api/bff/operator/verification-cases/{case_id}/decide", {"decision": "APPROVE", "reason": "Valid reason 15 chars", "expected_revision": 1}),
        ("POST", f"{FRONTEND_URL}/api/bff/operator/access-requests", {"target_user_id": target_user_id, "role_code": "SUPPORT", "reason": "Emergency fix", "independent_approver_id": approver_user_id, "duration_minutes": 60}),
        ("POST", f"{FRONTEND_URL}/api/bff/operator/users/{target_user_id}/revoke-sessions", {"reason": "Security incident"}),
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
        # Ensure role_catalog has required platform roles
        for r_code in ["ADMIN", "MODERATOR", "SUPPORT", "SECURITY_LEAD"]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.role_catalog (id, created_at, updated_at, code, scope_kind, description)
                    VALUES (:id, :now, :now, :code, 'PLATFORM', :desc)
                    ON CONFLICT (code) DO NOTHING
                """),
                {"id": str(uuid4()), "now": now_utc, "code": r_code, "desc": f"Platform {r_code}"}
            )

        # 1. Admin User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Platform Operator Admin', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": admin_user_id, "pwd": admin_hash, "now": now_utc}
        )

        # 2. Approver User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Independent Approver Admin', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": approver_user_id, "pwd": approver_hash, "now": now_utc}
        )

        # 3. Target User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Target Security User', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": target_user_id, "pwd": target_hash, "now": now_utc}
        )

        # Active Session for Target User (to test revocation API-120)
        conn.execute(
            text("""
                INSERT INTO flexbridge.sessions (id, created_at, updated_at, user_id, token_digest, device_key_digest, assurance, expires_at, revoked_at, last_seen_at, auth_version)
                VALUES (:id, :now, :now, :uid, :td, 'sha256:dummy_dev', 'PASSWORD_ONLY', :exp, NULL, :now, 1)
            """),
            {
                "id": target_session_id,
                "now": now_utc,
                "uid": target_user_id,
                "td": target_token_digest,
                "exp": now_utc + timedelta(hours=24),
            }
        )

        # Assign Platform Roles to Admin (ADMIN, MODERATOR) and Approver (ADMIN)
        admin_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'ADMIN' AND scope_kind = 'PLATFORM'")
        ).scalar()
        mod_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'MODERATOR' AND scope_kind = 'PLATFORM'")
        ).scalar()

        conn.execute(
            text("""
                INSERT INTO flexbridge.platform_role_grants (id, created_at, updated_at, user_id, role_id, granted_by_id, expires_at)
                VALUES
                    (:id1, :now, :now, :admin_id, :admin_rid, :approver_id, :exp),
                    (:id2, :now, :now, :admin_id, :mod_rid, :approver_id, :exp),
                    (:id3, :now, :now, :approver_id, :admin_rid, :admin_id, :exp)
            """),
            {
                "id1": str(uuid4()),
                "id2": str(uuid4()),
                "id3": str(uuid4()),
                "now": now_utc,
                "admin_id": admin_user_id,
                "approver_id": approver_user_id,
                "admin_rid": admin_role_id,
                "mod_rid": mod_role_id,
                "exp": now_utc + timedelta(days=30),
            }
        )

        # Seed Organization and Verification Case (for API-109 / API-110)
        org_tax_id = f"TAX-{secrets.token_hex(6)}"
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, status)
                VALUES (:id, :now, :now, :tax, 'Operator Staging Test Org', 'Operator Test Org', 'Tashkent', 'PENDING_VERIFICATION')
            """),
            {"id": org_id, "now": now_utc, "tax": org_tax_id}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status)
                VALUES (:id, :now, :now, :oid, :uid, 'PENDING_VERIFICATION')
            """),
            {"id": org_membership_id, "now": now_utc, "oid": org_id, "uid": target_user_id}
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.verification_cases (id, created_at, updated_at, requester_id, organization_id, kind, status, current_revision, assigned_reviewer_id, due_at)
                VALUES (:id, :now, :now, :req_id, :oid, 'ORG_REPRESENTATIVE', 'PENDING', 1, NULL, :due)
            """),
            {
                "id": case_id,
                "now": now_utc,
                "req_id": target_user_id,
                "oid": org_id,
                "due": due_at,
            }
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_verification_submissions (case_id, revision, organization_id, requester_membership_id, proposed_fields, created_at)
                VALUES (:cid, 1, :oid, :mid, '{"legal_name": "Operator Staging Test Org"}'::jsonb, :now)
            """),
            {
                "cid": case_id,
                "oid": org_id,
                "mid": org_membership_id,
                "now": now_utc,
            }
        )

        # Seed Clean Evidence File & Verification Evidence (Required by API-110 APPROVE)
        evidence_file_id = str(uuid4())
        s3_bucket = os.environ.get("S3_BUCKET", "flexbridge-private")
        f_version = str(uuid4())
        f_etag = f'"{uuid4().hex}"'
        conn.execute(
            text("""
                INSERT INTO flexbridge.files (
                    id, created_at, updated_at, owner_user_id, storage_key, filename, mime_type,
                    byte_size, sha256, scan_status, retention_class, deleted_at, object_version,
                    scanned_at, storage_bucket, storage_version_id, storage_etag
                )
                VALUES (
                    :id, :now, :now, :owner, :key, 'org_evidence.pdf', 'application/pdf',
                    1024, :sha, 'CLEAN', 'VERIFICATION_EVIDENCE', NULL, :ver,
                    :now, :bucket, :ver, :etag
                )
            """),
            {
                "id": evidence_file_id,
                "now": now_utc,
                "owner": target_user_id,
                "key": f"private/verification/{case_id}/{evidence_file_id}.pdf",
                "sha": hashlib.sha256(b"dummy_evidence_pdf").hexdigest(),
                "ver": f_version,
                "bucket": s3_bucket,
                "etag": f_etag,
            }
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.verification_evidence (id, created_at, updated_at, case_id, revision, file_id, note)
                VALUES (:id, :now, :now, :cid, 1, :fid, 'Official state tax registration certificate')
            """),
            {
                "id": str(uuid4()),
                "now": now_utc,
                "cid": case_id,
                "fid": evidence_file_id,
            }
        )

        # Seed Cryptographic Audit Event (API-118)
        conn.execute(
            text("""
                INSERT INTO flexbridge.audit_events (id, created_at, updated_at, actor_id, session_id, action, object_type, object_key, scope_snapshot, before_digest, after_digest, reason, request_id, occurred_at)
                VALUES (:id, :now, :now, :actor, NULL, 'STAGING_TEST_PROBE', 'verification_case', :obj_key, '{"env": "staging"}'::jsonb, NULL, NULL, 'Staging suite audit probe', :req_id, :now)
            """),
            {
                "id": audit_event_id,
                "now": now_utc,
                "actor": admin_user_id,
                "obj_key": f"CASE-{case_id[:8]}",
                "req_id": f"req-op-probe-{test_suffix}",
            }
        )

    print("  ✓ Fixtures seeded successfully via PgBouncer.")

    # --------------------------------------------------------------------------
    # PHASE 3: Operator Authentication via Next.js BFF
    # --------------------------------------------------------------------------
    print("\n[Phase 3] Logging in as Operator Admin via Next.js BFF (/api/auth/login)...")
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))

    login_code, login_resp = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": admin_user_id, "password": admin_password},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert login_code == 200, f"Expected 200 on login, got {login_code}: {login_resp}"
    assert login_resp.get("ok") is True, f"Login failed: {login_resp}"
    print(f"  ✓ Login successful: user_id={login_resp.get('user', {}).get('user_id')} roles={login_resp.get('user', {}).get('roles')}")

    # Elevate session assurance to MFA in DB so sensitive operations (require_mfa) pass
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE flexbridge.sessions
                SET assurance = 'MFA', updated_at = :now
                WHERE user_id = :uid AND revoked_at IS NULL
            """),
            {"now": datetime.now(timezone.utc), "uid": admin_user_id}
        )
    print("  ✓ Admin session assurance elevated to MFA in flexbridge.sessions.")

    # Verify session via /api/auth/me
    me_code, me_resp = api_request(f"{FRONTEND_URL}/api/auth/me", method="GET", opener=opener)
    assert me_code == 200, f"Expected 200 on /api/auth/me, got {me_code}: {me_resp}"
    assert me_resp.get("ok") is True and me_resp.get("user") is not None, f"Not authenticated: {me_resp}"
    print(f"  ✓ Session authenticated and verified via /api/auth/me (roles: {me_resp.get('user', {}).get('roles')}).")

    # --------------------------------------------------------------------------
    # PHASE 4: Cryptographic Audit Events Stream (API-118)
    # --------------------------------------------------------------------------
    print("\n[Phase 4] Querying Cryptographic Audit Events via BFF (API-118)...")
    audit_code, audit_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/audit-events?limit=50",
        method="GET",
        opener=opener,
    )
    assert audit_code == 200, f"Expected 200 on audit events, got {audit_code}: {audit_resp}"
    assert audit_resp.get("contract_id") == "API-118", f"Contract mismatch: {audit_resp}"
    items = audit_resp.get("items", [])
    assert len(items) > 0, "Expected non-empty audit event stream"
    assert any(it.get("action") == "STAGING_TEST_PROBE" for it in items), "Seeded probe event missing from stream"
    print(f"  ✓ API-118 audit stream returned {len(items)} events (seeded probe verified).")

    # Filter by action
    filt_code, filt_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/audit-events?action=STAGING_TEST_PROBE",
        method="GET",
        opener=opener,
    )
    assert filt_code == 200, f"Expected 200 on filtered audit events, got {filt_code}: {filt_resp}"
    filt_items = filt_resp.get("items", [])
    assert all(it.get("action") == "STAGING_TEST_PROBE" for it in filt_items), "Action filter violated"
    print(f"  ✓ API-118 action filter verified ({len(filt_items)} matching events).")

    # --------------------------------------------------------------------------
    # PHASE 5: Verification Queue (API-109)
    # --------------------------------------------------------------------------
    print("\n[Phase 5] Fetching Operator Verification Queue via BFF (API-109)...")
    queue_code, queue_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/verification-cases?unassigned=true",
        method="GET",
        opener=opener,
    )
    assert queue_code == 200, f"Expected 200 on verification cases queue, got {queue_code}: {queue_resp}"
    assert queue_resp.get("contract_id") == "API-109", f"Contract mismatch: {queue_resp}"
    q_items = queue_resp.get("items", [])
    target_case_item = next((c for c in q_items if c.get("id") == case_id), None)
    assert target_case_item is not None, f"Seeded case {case_id} not found in unassigned queue"
    assert target_case_item.get("kind") == "ORG_REPRESENTATIVE", f"Unexpected kind: {target_case_item}"
    print(f"  ✓ API-109 verification queue returned {len(q_items)} cases (case {case_id} confirmed in queue).")

    # --------------------------------------------------------------------------
    # PHASE 6: Verification Case Claim & Decision Workflow (API-110)
    # --------------------------------------------------------------------------
    print("\n[Phase 6] Testing Case Claim and Decision Workflow (API-110)...")
    # Validation 1: Reason too short (< 15 chars) -> 422
    short_code, short_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/verification-cases/{case_id}/decide",
        method="POST",
        data={"decision": "APPROVE", "reason": "Too short", "expected_revision": 1},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert short_code == 422, f"Expected 422 on short reason, got {short_code}: {short_resp}"
    print("  ✓ Short reason (<15 chars) rejected with 422 (INVALID_REASON).")

    # Validation 2: Invalid decision value -> 422
    inv_code, inv_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/verification-cases/{case_id}/decide",
        method="POST",
        data={"decision": "INVALID_VALUE", "reason": "Valid reason length that is at least 15 chars", "expected_revision": 1},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert inv_code == 422, f"Expected 422 on invalid decision, got {inv_code}: {inv_resp}"
    print("  ✓ Invalid decision value rejected with 422 (INVALID_DECISION).")

    # Claim the case via BFF
    claim_code, claim_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/verification-cases/{case_id}/claim",
        method="POST",
        data={},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert claim_code == 200, f"Expected 200 on claim, got {claim_code}: {claim_resp}"
    assert claim_resp.get("status") in ("IN_REVIEW", "PENDING"), f"Claim status unexpected: {claim_resp}"
    print(f"  ✓ Case claimed successfully by operator admin (status={claim_resp.get('status')}).")

    # Submit valid decision: APPROVE
    decide_code, decide_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/verification-cases/{case_id}/decide",
        method="POST",
        data={
            "decision": "APPROVE",
            "reason": "Tashkilot rekvizitlari va hujjatlari to'liq va mustaqil tekshiruvdan o'tdi.",
            "expected_revision": 1,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert decide_code == 200, f"Expected 200 on decide, got {decide_code}: {decide_resp}"
    assert decide_resp.get("contract_id") == "API-110", f"Contract mismatch: {decide_resp}"
    assert decide_resp.get("status") == "APPROVED", f"Expected APPROVED, got {decide_resp}"
    print(f"  ✓ API-110 case decision submitted: status=APPROVED (revision={decide_resp.get('revision')}).")

    # Verify DB state
    with engine.begin() as conn:
        db_case = conn.execute(
            text("SELECT status, assigned_reviewer_id FROM flexbridge.verification_cases WHERE id = :id"),
            {"id": case_id}
        ).mappings().one()
        assert db_case["status"] == "APPROVED", f"DB status mismatch: {db_case}"
        assert str(db_case["assigned_reviewer_id"]) == admin_user_id, "Reviewer ID mismatch"
    print("  ✓ Database verified: verification_cases row marked APPROVED by operator admin.")

    # --------------------------------------------------------------------------
    # PHASE 7: Break-Glass Privileged Access Request (API-119)
    # --------------------------------------------------------------------------
    print("\n[Phase 7] Testing Break-Glass 4-Eyes Privileged Access (API-119)...")
    # Negative 1: Self-approval forbidden (403)
    self_code, self_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/access-requests",
        method="POST",
        data={
            "target_user_id": target_user_id,
            "role_code": "SUPPORT",
            "reason": "Emergency self approval test",
            "independent_approver_id": admin_user_id,  # Same as caller!
            "duration_minutes": 60,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert self_code == 403, f"Expected 403 on self-approval, got {self_code}: {self_resp}"
    print("  ✓ Self-approval rejected with 403 (SELF_APPROVAL_FORBIDDEN - Dual Control enforced).")

    # Negative 2: Duration > 240 minutes forbidden (422)
    dur_code, dur_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/access-requests",
        method="POST",
        data={
            "target_user_id": target_user_id,
            "role_code": "SUPPORT",
            "reason": "Emergency excessive duration test",
            "independent_approver_id": approver_user_id,
            "duration_minutes": 360,  # > 240!
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert dur_code == 422, f"Expected 422 on duration > 240, got {dur_code}: {dur_resp}"
    print("  ✓ Duration > 240 mins rejected with 422 (INVALID_DURATION).")

    # Positive: Valid break-glass request with independent approver
    bg_code, bg_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/access-requests",
        method="POST",
        data={
            "target_user_id": target_user_id,
            "role_code": "SUPPORT",
            "reason": "Emergency production support break-glass required for incident triage",
            "independent_approver_id": approver_user_id,
            "duration_minutes": 120,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert bg_code in (200, 201), f"Expected 200/201 on break-glass, got {bg_code}: {bg_resp}"
    assert bg_resp.get("contract_id") == "API-119", f"Contract mismatch: {bg_resp}"
    assert bg_resp.get("status") == "GRANTED", f"Expected GRANTED, got {bg_resp}"
    assert bg_resp.get("grant_id") is not None, "Missing grant_id"
    print(f"  ✓ API-119 break-glass granted: grant_id={bg_resp.get('grant_id')} role={bg_resp.get('role_code')} duration={bg_resp.get('duration_minutes')}min.")

    # Verify DB grant
    with engine.begin() as conn:
        grant_row = conn.execute(
            text("""
                SELECT g.id, g.user_id, r.code, g.revoked_at
                FROM flexbridge.platform_role_grants g
                JOIN flexbridge.role_catalog r ON g.role_id = r.id
                WHERE g.user_id = :uid AND r.code = 'SUPPORT' AND g.revoked_at IS NULL
            """),
            {"uid": target_user_id}
        ).mappings().first()
        assert grant_row is not None, "DB platform_role_grants missing newly granted role"
    print("  ✓ Database verified: target user active platform role grant confirmed.")

    # --------------------------------------------------------------------------
    # PHASE 8: Emergency User Session Revocation (API-120)
    # --------------------------------------------------------------------------
    print("\n[Phase 8] Testing Emergency User Session Revocation (API-120)...")
    revoke_code, revoke_resp = api_request(
        f"{FRONTEND_URL}/api/bff/operator/users/{target_user_id}/revoke-sessions",
        method="POST",
        data={"reason": "Suspicious compromise detected by automated monitoring"},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert revoke_code == 200, f"Expected 200 on revoke sessions, got {revoke_code}: {revoke_resp}"
    assert revoke_resp.get("contract_id") == "API-120", f"Contract mismatch: {revoke_resp}"
    assert revoke_resp.get("revoked_sessions_count", 0) >= 1, f"Expected at least 1 revoked session: {revoke_resp}"
    print(f"  ✓ API-120 emergency sessions revoked: count={revoke_resp.get('revoked_sessions_count')}.")

    # Verify DB sessions
    with engine.begin() as conn:
        sess_row = conn.execute(
            text("SELECT id, revoked_at FROM flexbridge.sessions WHERE id = :id"),
            {"id": target_session_id}
        ).mappings().one()
        assert sess_row["revoked_at"] is not None, "Session revoked_at was not populated in DB"
    print("  ✓ Database verified: target user session revoked_at timestamp populated.")

    # --------------------------------------------------------------------------
    # PHASE 9: CSRF Origin Mismatch Rejection on Mutating Endpoints (403)
    # --------------------------------------------------------------------------
    print("\n[Phase 9] Testing CSRF Origin Mismatch Rejection on Mutating Endpoints (403)...")
    csrf_tests = [
        ("POST", f"{FRONTEND_URL}/api/bff/operator/verification-cases/{case_id}/claim", {}),
        ("POST", f"{FRONTEND_URL}/api/bff/operator/verification-cases/{case_id}/decide", {"decision": "APPROVE", "reason": "Valid reason 15 chars", "expected_revision": 1}),
        ("POST", f"{FRONTEND_URL}/api/bff/operator/access-requests", {"target_user_id": target_user_id, "role_code": "SUPPORT", "reason": "Emergency fix", "independent_approver_id": approver_user_id, "duration_minutes": 60}),
        ("POST", f"{FRONTEND_URL}/api/bff/operator/users/{target_user_id}/revoke-sessions", {"reason": "Security incident"}),
    ]

    for method, url, body in csrf_tests:
        code, resp = api_request(
            url,
            method=method,
            data=body,
            headers={"Origin": "https://malicious-phishing-attacker.com"},
            opener=opener,
        )
        assert code == 403, f"Expected 403 on CSRF attack {method} {url}, got {code}: {resp}"
        assert resp.get("error") == "CSRF_ORIGIN_MISMATCH", f"Unexpected CSRF error: {resp}"
        print(f"  ✓ CSRF attack rejected on {url.replace(FRONTEND_URL, '')} -> 403 (CSRF_ORIGIN_MISMATCH)")

    print("\n" + "=" * 80)
    print("ALL 9 OPERATOR STAGING VERIFICATION PHASES PASSED 100% GREEN!")
    print("Contracts API-109, API-110, API-118, API-119, API-120 Fully Operational.")
    print("=" * 80)


if __name__ == "__main__":
    run_operator_staging_suite()
