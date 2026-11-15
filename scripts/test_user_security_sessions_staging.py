#!/usr/bin/env python3
"""FlexBridge 1.4 Candidate & User Security, MFA & Active Sessions Staging Verification Suite (FB-186).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected on all security endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Anti-CSRF Origin Guard rejection on mutating endpoints (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 3: Database Fixtures Setup via PgBouncer (Candidate User A with known password & Candidate User B).
Phase 4: Candidate Login & Initial Security Overview (GET /api/bff/me/security).
Phase 5: Step-Up Password Verification Guard on API-060 (PATCH /api/bff/me/security with wrong password).
Phase 6: TOTP Enrollment Initiation (API-060) returning base32 secret and pending status.
Phase 7: TOTP Confirmation Verification (invalid code 400/401 vs valid RFC 6238 code 200).
Phase 8: Emergency Recovery Codes Generation (POST /api/bff/me/security/recovery-codes, 8 codes).
Phase 9: Active Sessions Listing & Revocation (API-061 DELETE /api/bff/me/sessions/{id}).
Phase 10: Cross-User IDOR Defense on Session Revocation (User A cannot revoke User B's session -> 403).

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from app.services.auth import hash_password, generate_totp_code

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
STAGING_DB_URL = os.environ.get(
    "STAGING_DB_URL",
    "postgresql+psycopg://flexbridge_owner:stg_secure_pg_pass_2026_flexbridge_isolated@127.0.0.1:5432/flexbridge",
)

engine = create_engine(STAGING_DB_URL, connect_args={"prepare_threshold": None})


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

    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)
    call_opener = opener or urllib.request.build_opener()

    try:
        with call_opener.open(req) as response:
            resp_code = response.getcode()
            raw_body = response.read().decode("utf-8")
            resp_headers = dict(response.info())
            try:
                resp_json = json.loads(raw_body) if raw_body else {}
            except Exception:
                resp_json = {"raw": raw_body}
            return resp_code, resp_json, resp_headers
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        resp_headers = dict(exc.headers)
        try:
            resp_json = json.loads(raw_body) if raw_body else {}
        except Exception:
            resp_json = {"raw": raw_body}
        return exc.code, resp_json, resp_headers


def main() -> int:
    print("=" * 80)
    print("FlexBridge 1.4: User Security, MFA & Sessions Staging Suite (FB-186)")
    print(f"Target Frontend: {FRONTEND_URL} | Backend: {BACKEND_URL}")
    print(f"Target DB: {STAGING_DB_URL.split('@')[-1]} (PgBouncer)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # PHASE 1: Unauthenticated Rejection (HTTP 401)
    # -------------------------------------------------------------------------
    print("\n--- PHASE 1: Unauthenticated Security Requests Rejected (401) ---")
    endpoints = [
        (f"{FRONTEND_URL}/api/bff/me/security", "GET", None),
        (f"{FRONTEND_URL}/api/bff/me/security", "PATCH", {"enable_totp": True, "current_password": "foo"}),
        (f"{FRONTEND_URL}/api/bff/me/security/totp/confirm", "POST", {"code": "123456"}),
        (f"{FRONTEND_URL}/api/bff/me/security/recovery-codes", "POST", {"current_password": "foo"}),
        (f"{FRONTEND_URL}/api/bff/me/sessions/{uuid4()}", "DELETE", None),
    ]

    for url, method, body in endpoints:
        code, resp, _ = make_request(url, method=method, data=body)
        print(f"Unauthenticated {method} {url} -> status {code}")
        assert code == 401, f"Expected 401, got {code}: {resp}"
        assert resp.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {resp}"
    print("[PASS] Phase 1: All 5 unauthenticated endpoints returned 401 AUTH_REQUIRED.")

    # -------------------------------------------------------------------------
    # PHASE 2: Anti-CSRF Origin Rejection (HTTP 403)
    # -------------------------------------------------------------------------
    print("\n--- PHASE 2: Anti-CSRF Origin Defense on Mutating Endpoints (403) ---")
    mutating_endpoints = [
        (f"{FRONTEND_URL}/api/bff/me/security", "PATCH", {"enable_totp": True, "current_password": "foo"}),
        (f"{FRONTEND_URL}/api/bff/me/security/totp/confirm", "POST", {"code": "123456"}),
        (f"{FRONTEND_URL}/api/bff/me/security/recovery-codes", "POST", {"current_password": "foo"}),
        (f"{FRONTEND_URL}/api/bff/me/sessions/{uuid4()}", "DELETE", None),
    ]

    for url, method, body in mutating_endpoints:
        code, resp, _ = make_request(
            url,
            method=method,
            data=body,
            headers={"Origin": "https://malicious-cross-origin.com"},
        )
        print(f"CSRF Spoof {method} {url} -> status {code}")
        assert code == 403, f"Expected 403, got {code}: {resp}"
        assert resp.get("error") == "CSRF_DETECTED", f"Expected CSRF_DETECTED, got {resp}"
    print("[PASS] Phase 2: Anti-CSRF origin guard rejected spoofed origins with 403.")

    # -------------------------------------------------------------------------
    # PHASE 3: Database Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n--- PHASE 3: Database Fixtures Setup via PgBouncer ---")
    tag = uuid4().hex[:8]
    user_a_id = uuid4()
    user_b_id = uuid4()
    candidate_a_password = "CandidateSec2026!Pass"
    candidate_b_password = "CandidateSec2026!UserB"
    user_a_phone = f"+99890{tag[:7]}"
    user_b_phone = f"+99891{tag[:7]}"

    hashed_pw_a = hash_password(candidate_a_password)
    hashed_pw_b = hash_password(candidate_b_password)

    with engine.begin() as conn:
        # Candidate User A
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.users (id, status, auth_version, password_hash, display_name, locale, timezone, adult_declared_at, created_at, updated_at)
                VALUES (:id, 'ACTIVE', 1, :pw, :name, 'uz', 'Asia/Tashkent', NOW(), NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": user_a_id, "pw": hashed_pw_a, "name": f"Sec Candidate A {tag}"},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.user_contacts (id, user_id, channel, normalized_value, verified_at, is_primary, created_at, updated_at)
                VALUES (:id, :user_id, 'PHONE', :phone, NOW(), TRUE, NOW(), NOW())
                """
            ),
            {"id": uuid4(), "user_id": user_a_id, "phone": user_a_phone},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, experience_months, visibility)
                VALUES (:id, NOW(), NOW(), :user_id, 'Security Test Candidate', 'Tashkent', 12, 'PUBLIC')
                ON CONFLICT (user_id) DO NOTHING
                """
            ),
            {"id": uuid4(), "user_id": user_a_id},
        )

        # Candidate User B (for cross-user IDOR isolation test)
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.users (id, status, auth_version, password_hash, display_name, locale, timezone, adult_declared_at, created_at, updated_at)
                VALUES (:id, 'ACTIVE', 1, :pw, :name, 'uz', 'Asia/Tashkent', NOW(), NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": user_b_id, "pw": hashed_pw_b, "name": f"Sec Candidate B {tag}"},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.user_contacts (id, user_id, channel, normalized_value, verified_at, is_primary, created_at, updated_at)
                VALUES (:id, :user_id, 'PHONE', :phone, NOW(), TRUE, NOW(), NOW())
                """
            ),
            {"id": uuid4(), "user_id": user_b_id, "phone": user_b_phone},
        )

    print(f"[PASS] Phase 3: Seeded User A ({user_a_id}, {user_a_phone}) and User B ({user_b_id}, {user_b_phone}).")

    # -------------------------------------------------------------------------
    # PHASE 4: Candidate Login & Initial Security Overview
    # -------------------------------------------------------------------------
    print("\n--- PHASE 4: Candidate Login & Security Overview (GET /api/bff/me/security) ---")
    cj_a = http.cookiejar.CookieJar()
    opener_a = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_a))

    login_code, login_resp, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": str(user_a_id), "password": candidate_a_password},
        headers={"Origin": FRONTEND_URL},
        opener=opener_a,
    )
    print(f"Login User A -> status {login_code}, ok: {login_resp.get('ok')}")
    assert login_code == 200, f"Expected 200 login, got {login_code}: {login_resp}"
    assert login_resp.get("ok") is True, f"Expected ok: true, got {login_resp}"

    sec_code, sec_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security",
        method="GET",
        opener=opener_a,
    )
    print(f"GET /api/bff/me/security -> status {sec_code}, totp_enabled: {sec_data.get('totp_enabled')}")
    assert sec_code == 200, f"Expected 200, got {sec_code}: {sec_data}"
    assert sec_data.get("ok") is True
    assert sec_data.get("totp_enabled") is False, "Expected TOTP initially disabled"
    assert sec_data.get("recovery_codes_count") == 0, "Expected 0 recovery codes initially"
    assert len(sec_data.get("sessions", [])) >= 1, "Expected at least 1 active session"
    current_session = next((s for s in sec_data.get("sessions", []) if s.get("is_current")), None)
    assert current_session is not None, "Expected an active session marked is_current: true"
    print(f"[PASS] Phase 4: Initial security overview verified (TOTP=false, recovery_codes=0, session_id={current_session['id']}).")

    # -------------------------------------------------------------------------
    # PHASE 5: Step-Up Password Verification Guard on API-060
    # -------------------------------------------------------------------------
    print("\n--- PHASE 5: Step-Up Password Verification Guard (API-060) ---")
    wrong_pw_code, wrong_pw_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security",
        method="PATCH",
        data={"enable_totp": True, "current_password": "WrongPassword123!Candidate"},
        headers={"Origin": FRONTEND_URL},
        opener=opener_a,
    )
    print(f"PATCH /api/bff/me/security with invalid password -> status {wrong_pw_code}, error: {wrong_pw_resp.get('error')}")
    assert wrong_pw_code in (400, 401, 403), f"Expected 400/401/403 for wrong password, got {wrong_pw_code}: {wrong_pw_resp}"
    assert "STEP_UP" in str(wrong_pw_resp) or "INVALID" in str(wrong_pw_resp) or "FAILED" in str(wrong_pw_resp)
    print("[PASS] Phase 5: Step-up password verification guard successfully rejected invalid password.")

    # -------------------------------------------------------------------------
    # PHASE 6: TOTP Enrollment Initiation (API-060)
    # -------------------------------------------------------------------------
    print("\n--- PHASE 6: TOTP Enrollment Initiation (API-060) ---")
    enroll_code, enroll_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security",
        method="PATCH",
        data={"enable_totp": True, "current_password": candidate_a_password},
        headers={"Origin": FRONTEND_URL},
        opener=opener_a,
    )
    print(f"PATCH /api/bff/me/security (enable_totp=true) -> status {enroll_code}, pending: {enroll_resp.get('enrollment_pending')}")
    assert enroll_code == 200, f"Expected 200, got {enroll_code}: {enroll_resp}"
    assert enroll_resp.get("enrollment_pending") is True, f"Expected enrollment_pending: true, got {enroll_resp}"
    assert enroll_resp.get("totp_enabled") is False, "Expected totp_enabled to remain False until confirmation"
    totp_secret = enroll_resp.get("secret")
    assert totp_secret and len(totp_secret) >= 16, f"Expected valid base32 TOTP secret, got {totp_secret}"
    print(f"[PASS] Phase 6: TOTP enrollment initiated with secret length {len(totp_secret)}.")

    # -------------------------------------------------------------------------
    # PHASE 7: TOTP Confirmation Verification & DB Credential Activation
    # -------------------------------------------------------------------------
    print("\n--- PHASE 7: TOTP Confirmation Verification ---")
    # Invalid 6-digit code
    bad_code_status, bad_code_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security/totp/confirm",
        method="POST",
        data={"code": "000000"},
        headers={"Origin": FRONTEND_URL},
        opener=opener_a,
    )
    print(f"Confirm TOTP with bad code 000000 -> status {bad_code_status}, error: {bad_code_resp.get('error')}")
    assert bad_code_status in (400, 401), f"Expected 400/401 for invalid code, got {bad_code_status}: {bad_code_resp}"

    # Valid RFC 6238 code
    valid_totp_code = generate_totp_code(totp_secret)
    print(f"Generated RFC 6238 TOTP code: {valid_totp_code} from secret {totp_secret[:6]}...")
    conf_code, conf_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security/totp/confirm",
        method="POST",
        data={"code": valid_totp_code},
        headers={"Origin": FRONTEND_URL},
        opener=opener_a,
    )
    print(f"Confirm TOTP with valid code -> status {conf_code}, totp_enabled: {conf_resp.get('totp_enabled')}")
    assert conf_code == 200, f"Expected 200 for valid code, got {conf_code}: {conf_resp}"
    assert conf_resp.get("totp_enabled") is True, f"Expected totp_enabled: true, got {conf_resp}"
    assert conf_resp.get("reauthentication_required") is True

    # Verify DB state in PgBouncer
    with engine.begin() as conn:
        mfa_row = conn.execute(
            text(
                """
                SELECT id, kind, verified_at, revoked_at FROM flexbridge.mfa_credentials
                WHERE user_id = :uid AND kind = 'TOTP' AND verified_at IS NOT NULL AND revoked_at IS NULL
                """
            ),
            {"uid": user_a_id},
        ).mappings().first()
        assert mfa_row is not None, "Expected verified TOTP credential in mfa_credentials table"
    print(f"[PASS] Phase 7: TOTP confirmed and verified in DB (credential_id={mfa_row['id']}).")

    # -------------------------------------------------------------------------
    # PHASE 8: Emergency Recovery Codes Generation
    # -------------------------------------------------------------------------
    print("\n--- PHASE 8: Emergency Recovery Codes Generation ---")
    # Re-login with password + TOTP code
    re_totp = generate_totp_code(totp_secret)
    cj_a2 = http.cookiejar.CookieJar()
    opener_a2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_a2))

    re_login_code, re_login_resp, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={
            "user_id": str(user_a_id),
            "password": candidate_a_password,
            "totp_code": re_totp,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener_a2,
    )
    assert re_login_code == 200, f"Expected 200 re-login with TOTP, got {re_login_code}: {re_login_resp}"

    # Generate 8 recovery codes
    step_up_code = generate_totp_code(totp_secret)
    rec_code, rec_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security/recovery-codes",
        method="POST",
        data={"current_password": candidate_a_password, "totp_code": step_up_code},
        headers={"Origin": FRONTEND_URL},
        opener=opener_a2,
    )
    print(f"POST /api/bff/me/security/recovery-codes -> status {rec_code}, codes_count: {len(rec_resp.get('recovery_codes', []))}")
    assert rec_code == 200, f"Expected 200, got {rec_code}: {rec_resp}"
    assert rec_resp.get("show_once") is True
    recovery_codes = rec_resp.get("recovery_codes", [])
    assert len(recovery_codes) == 8, f"Expected exactly 8 recovery codes, got {len(recovery_codes)}"

    # Check overview
    sec_code2, sec_data2, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security",
        method="GET",
        opener=opener_a2,
    )
    assert sec_code2 == 200
    assert sec_data2.get("totp_enabled") is True
    assert sec_data2.get("recovery_codes_count") == 8
    print(f"[PASS] Phase 8: 8 recovery codes generated and verified in security overview.")

    # -------------------------------------------------------------------------
    # PHASE 9: Active Sessions Listing & Revocation (API-061)
    # -------------------------------------------------------------------------
    print("\n--- PHASE 9: Active Sessions Listing & Revocation (API-061) ---")
    # Insert secondary active session for User A directly into sessions table
    secondary_session_id = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.sessions (id, user_id, auth_version, token_digest, assurance, expires_at, last_seen_at, created_at, updated_at)
                VALUES (:id, :uid, (SELECT auth_version FROM flexbridge.users WHERE id = :uid),
                        :digest, 'PASSWORD', NOW() + INTERVAL '12 hours', NOW(), NOW(), NOW())
                """
            ),
            {
                "id": secondary_session_id,
                "uid": user_a_id,
                "digest": uuid4().hex,
            },
        )

    # Query overview -> should now have at least 2 active sessions
    sec_code3, sec_data3, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security",
        method="GET",
        opener=opener_a2,
    )
    assert sec_code3 == 200
    sessions_list = sec_data3.get("sessions", [])
    print(f"Active sessions count: {len(sessions_list)}")
    assert len(sessions_list) >= 2, f"Expected >= 2 active sessions, got {len(sessions_list)}"
    found_secondary = any(str(s.get("id")) == str(secondary_session_id) for s in sessions_list)
    assert found_secondary, f"Expected session {secondary_session_id} in sessions list"

    # Revoke secondary session via API-061
    revoke_code, revoke_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/sessions/{secondary_session_id}",
        method="DELETE",
        headers={"Origin": FRONTEND_URL},
        opener=opener_a2,
    )
    print(f"DELETE /api/bff/me/sessions/{secondary_session_id} -> status {revoke_code}, status: {revoke_resp.get('status')}")
    assert revoke_code == 200, f"Expected 200, got {revoke_code}: {revoke_resp}"
    assert revoke_resp.get("status") == "REVOKED"

    # Verify overview no longer includes revoked session
    sec_code4, sec_data4, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security",
        method="GET",
        opener=opener_a2,
    )
    active_ids = [str(s.get("id")) for s in sec_data4.get("sessions", [])]
    assert str(secondary_session_id) not in active_ids, f"Revoked session {secondary_session_id} still present in active sessions"
    print(f"[PASS] Phase 9: Active sessions listed and secondary session revoked via API-061.")

    # -------------------------------------------------------------------------
    # PHASE 10: Cross-User IDOR Defense on Session Revocation
    # -------------------------------------------------------------------------
    print("\n--- PHASE 10: Cross-User IDOR Defense on Session Revocation ---")
    user_b_session_id = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.sessions (id, user_id, auth_version, token_digest, assurance, expires_at, last_seen_at, created_at, updated_at)
                VALUES (:id, :uid, (SELECT auth_version FROM flexbridge.users WHERE id = :uid),
                        :digest, 'PASSWORD', NOW() + INTERVAL '12 hours', NOW(), NOW(), NOW())
                """
            ),
            {
                "id": user_b_session_id,
                "uid": user_b_id,
                "digest": uuid4().hex,
            },
        )

    # User A tries to revoke User B's session
    idor_code, idor_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/sessions/{user_b_session_id}",
        method="DELETE",
        headers={"Origin": FRONTEND_URL},
        opener=opener_a2,
    )
    print(f"User A attempts to revoke User B's session -> status {idor_code}, error: {idor_resp.get('error')}")
    assert idor_code == 403, f"Expected 403 FORBIDDEN_SESSION_SCOPE, got {idor_code}: {idor_resp}"
    assert idor_resp.get("error") == "FORBIDDEN_SESSION_SCOPE" or "FORBIDDEN" in str(idor_resp)

    # Verify User B's session remains active in DB
    with engine.begin() as conn:
        b_sess = conn.execute(
            text("SELECT id, revoked_at FROM flexbridge.sessions WHERE id = :id"),
            {"id": user_b_session_id},
        ).mappings().first()
        assert b_sess is not None
        assert b_sess["revoked_at"] is None, "User B's session should NOT be revoked by User A"
    print("[PASS] Phase 10: Cross-user IDOR attempt defended with 403 FORBIDDEN_SESSION_SCOPE.")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF USER SECURITY & SESSIONS SUITE PASSED 100% GREEN!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
