#!/usr/bin/env python3
"""FlexBridge 1.4 Standalone Auth Pages & Onboarding Wizard Staging Verification Suite (FB-190).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Public Auth Options Telemetry (GET /api/bff/auth/options -> HTTP 200, channels & policy versions).
Phase 2: Anti-CSRF Origin Defense on Mutating Auth Routes (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 3: Challenge Issuance Validation (POST /api/bff/auth/challenges -> HTTP 400 vs 202 QUEUED).
Phase 4: Challenge Consumption & Code Verification (POST /api/bff/auth/challenges/[id]/consume -> invalid code 401/422).
Phase 5: Registration Request Schema Validation (missing token, password < 12 chars, unconfirmed adult -> HTTP 400).
Phase 6: End-to-End Candidate Registration via BFF (OTP verification token + POST /api/bff/auth/register -> HTTP 201).
Phase 7: Immediate Authenticated Session Verification (GET /api/auth/me with registration session cookie -> HTTP 200 CANDIDATE).
Phase 8: Standalone Login Workflow Verification (POST /api/auth/login with newly registered user -> HTTP 200 vs 401).
Phase 9: Step-Up MFA Challenge Flow Verification (User with TOTP -> HTTP 202 mfa_required).
Phase 10: SSR HTML Verification (/kirish, /royxatdan-otish, / -> HTTP 200, forms, brand elements, navbar links).

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
from typing import Any
from uuid import uuid4

from pathlib import Path
from dotenv import dotenv_values

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
infra_env = dotenv_values(Path(REPO_ROOT) / "infra" / ".env")
for k, v in infra_env.items():
    if k and v and k not in os.environ:
        os.environ[k] = v

BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from app.services.auth import hash_password, generate_totp_code
from app.core.iam_security import encrypt, decrypt

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
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    cookie_jar: http.cookiejar.CookieJar | None = None,
) -> tuple[int, dict[str, Any] | str, dict[str, str]]:
    req_headers = headers or {}
    if cookie_jar is not None:
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    else:
        opener = urllib.request.build_opener()

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with opener.open(req, timeout=15) as resp:
            status = resp.status
            resp_headers = dict(resp.headers)
            body = resp.read().decode("utf-8")
            try:
                parsed = json.loads(body)
                return status, parsed, resp_headers
            except Exception:
                return status, body, resp_headers
    except urllib.error.HTTPError as exc:
        status = exc.code
        resp_headers = dict(exc.headers)
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
            return status, parsed, resp_headers
        except Exception:
            return status, body, resp_headers


def run_phase_1() -> dict[str, Any]:
    print("\n--- Phase 1: Public Auth Options Telemetry (GET /api/bff/auth/options) ---")
    status, body, _ = make_request(f"{FRONTEND_URL}/api/bff/auth/options")
    assert status == 200, f"Expected 200, got {status}: {body}"
    assert isinstance(body, dict), f"Expected dict body, got {type(body)}"
    assert body.get("ok") is True, f"Expected ok: True, got {body}"
    assert "PHONE" in body.get("channels", []), f"Expected PHONE in channels: {body.get('channels')}"
    assert "EMAIL" in body.get("channels", []), f"Expected EMAIL in channels: {body.get('channels')}"
    assert body.get("terms_version") == "2026.1", f"Expected terms_version 2026.1, got {body.get('terms_version')}"
    assert body.get("privacy_version") == "2026.1", f"Expected privacy_version 2026.1, got {body.get('privacy_version')}"
    print(f"  OK: Auth options telemetry verified (Channels: {body.get('channels')}, Policies: {body.get('terms_version')}).")
    return body


def run_phase_2() -> None:
    print("\n--- Phase 2: Anti-CSRF Origin Defense on Mutating Auth Routes ---")
    mutating_routes = [
        (
            f"{FRONTEND_URL}/api/bff/auth/challenges",
            {"channel": "PHONE", "destination": "+998901234567", "purpose": "REGISTER"},
        ),
        (
            f"{FRONTEND_URL}/api/bff/auth/challenges/{uuid4()}/consume",
            {"purpose": "REGISTER", "code": "123456"},
        ),
        (
            f"{FRONTEND_URL}/api/bff/auth/register",
            {
                "verification_token": "fake_token",
                "display_name": "Test",
                "password": "Password123456!",
                "adult_confirmed": True,
            },
        ),
    ]

    for url, payload in mutating_routes:
        status, body, _ = make_request(
            url,
            method="POST",
            headers={"Content-Type": "application/json", "Origin": "https://malicious-attacker.com"},
            data=json.dumps(payload).encode(),
        )
        assert status == 403, f"Expected 403 for spoofed origin on {url}, got {status}: {body}"
        assert isinstance(body, dict) and body.get("error") in ("CSRF_ORIGIN_MISMATCH", "CSRF_DETECTED"), (
            f"Expected CSRF error, got {body}"
        )
    print("  OK: Anti-CSRF origin guard verified on all mutating auth routes (HTTP 403 CSRF_ORIGIN_MISMATCH).")


def run_phase_3() -> str:
    print("\n--- Phase 3: Challenge Issuance Validation ---")
    # Missing fields
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"channel": "PHONE"}).encode(),
    )
    assert status == 400, f"Expected 400 for missing fields, got {status}: {body}"

    # Valid challenge issuance
    import random
    test_phone = f"+99890{random.randint(1000000, 9999999)}"
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"channel": "PHONE", "destination": test_phone, "purpose": "REGISTER"}).encode(),
    )
    assert status == 202, f"Expected 202 Accepted, got {status}: {body}"
    assert isinstance(body, dict) and body.get("ok") is True, f"Expected ok: True, got {body}"
    challenge_id = body.get("challenge_id")
    assert challenge_id, f"Expected challenge_id, got {body}"
    print(f"  OK: Challenge successfully issued (challenge_id: {challenge_id}, status: {body.get('status')}).")
    return challenge_id


def run_phase_4(challenge_id: str) -> None:
    print("\n--- Phase 4: Challenge Consumption & Code Verification ---")
    # Invalid 6-digit code
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges/{challenge_id}/consume",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"purpose": "REGISTER", "code": "999999"}).encode(),
    )
    assert status in (401, 422), f"Expected 401 or 422 for invalid code, got {status}: {body}"
    print("  OK: Invalid challenge code correctly rejected by backend security.")


def run_phase_5() -> None:
    print("\n--- Phase 5: Registration Request Schema Validation ---")
    # Missing verification token
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/register",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "display_name": "Aziz Rahimov",
            "password": "Password123456!",
            "adult_confirmed": True,
        }).encode(),
    )
    assert status == 400, f"Expected 400 for missing token, got {status}: {body}"

    # Password too short (< 12 chars)
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/register",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "verification_token": "some_token_12345678901234567890",
            "display_name": "Aziz Rahimov",
            "password": "short",
            "adult_confirmed": True,
        }).encode(),
    )
    assert status == 400, f"Expected 400 for short password, got {status}: {body}"
    assert "PASSWORD_TOO_SHORT" in str(body), f"Expected PASSWORD_TOO_SHORT error, got {body}"

    # Unconfirmed adult
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/register",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "verification_token": "some_token_12345678901234567890",
            "display_name": "Aziz Rahimov",
            "password": "ValidPassword123456!",
            "adult_confirmed": False,
        }).encode(),
    )
    assert status == 400, f"Expected 400 for unconfirmed adult, got {status}: {body}"
    assert "ADULT_CONFIRMATION_REQUIRED" in str(body), f"Expected ADULT_CONFIRMATION_REQUIRED, got {body}"
    print("  OK: Registration schema validation guards verified (token, length >= 12, adult confirmation).")


def run_phase_6_and_7() -> tuple[dict[str, Any], str, str, http.cookiejar.CookieJar]:
    print("\n--- Phase 6: End-to-End Candidate Registration via BFF ---")
    import random
    reg_phone = f"+99890{random.randint(1000000, 9999999)}"
    reg_password = f"P@ssw0rd_{uuid4().hex[:8]}!"
    display_name = f"Test Candidate {uuid4().hex[:6]}"

    # Issue challenge & retrieve code directly from DB via PgBouncer
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"channel": "PHONE", "destination": reg_phone, "purpose": "REGISTER"}).encode(),
    )
    assert status == 202, f"Failed to issue challenge: {body}"
    challenge_id = body.get("challenge_id")

    # Read challenge delivery_encrypted via PgBouncer to obtain cleartext OTP code
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT delivery_encrypted FROM flexbridge.auth_challenges WHERE id = :id"),
            {"id": challenge_id},
        ).mappings().first()
        assert row and row["delivery_encrypted"], f"Challenge row or delivery_encrypted missing for {challenge_id}"
        otp_code = decrypt(row["delivery_encrypted"])["code"]
        # Update delivery_status to 'SENT' so consume() succeeds
        conn.execute(
            text("UPDATE flexbridge.auth_challenges SET delivery_status = 'SENT' WHERE id = :id"),
            {"id": challenge_id},
        )

    # Consume challenge to get verification_token
    status, consume_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges/{challenge_id}/consume",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"purpose": "REGISTER", "code": otp_code}).encode(),
    )
    assert status == 200, f"Failed to consume challenge: {consume_body}"
    assert isinstance(consume_body, dict)
    verification_token = consume_body.get("verification_token")
    assert verification_token, f"verification_token missing in {consume_body}"

    # Perform Registration via BFF with cookie jar
    cookie_jar = http.cookiejar.CookieJar()
    status, reg_body, headers = make_request(
        f"{FRONTEND_URL}/api/bff/auth/register",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "verification_token": verification_token,
            "display_name": display_name,
            "password": reg_password,
            "adult_confirmed": True,
            "terms_version": "2026.1",
            "privacy_version": "2026.1",
            "roles": ["CANDIDATE"],
        }).encode(),
        cookie_jar=cookie_jar,
    )
    assert status == 201, f"Expected 201 Created, got {status}: {reg_body}"
    assert isinstance(reg_body, dict) and reg_body.get("ok") is True, f"Expected ok: True, got {reg_body}"
    user = reg_body.get("user", {})
    assert user.get("id"), f"Expected user.id, got {user}"
    assert user.get("roles") == ["CANDIDATE"], f"Expected CANDIDATE role, got {user.get('roles')}"
    assert user.get("adult_declared_at") is not None, f"Expected adult_declared_at, got {user}"
    assert reg_body.get("logged_in") is True, f"Expected logged_in: True, got {reg_body}"
    print(f"  OK: Candidate registered (id: {user.get('id')}, name: {user.get('display_name')}, logged_in: True).")

    print("\n--- Phase 7: Immediate Authenticated Session Verification ---")
    status, me_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/me",
        method="GET",
        cookie_jar=cookie_jar,
    )
    assert status == 200, f"Expected 200 for /api/auth/me, got {status}: {me_body}"
    assert isinstance(me_body, dict) and me_body.get("ok") is True, f"Expected ok: True, got {me_body}"
    me_user = me_body.get("user", {})
    assert me_user.get("user_id") == user.get("id"), f"user_id mismatch: {me_user.get('user_id')} vs {user.get('id')}"
    assert "CANDIDATE" in me_user.get("roles", []), f"Role CANDIDATE missing: {me_user.get('roles')}"
    print(f"  OK: Authenticated session confirmed via HttpOnly cookie (user_id: {me_user.get('user_id')}).")

    return user, reg_phone, reg_password, cookie_jar


def run_phase_8(user_id: str, phone: str, password: str) -> None:
    print("\n--- Phase 8: Standalone Login Workflow Verification ---")
    # Wrong password rejection
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"destination": phone, "password": "WrongPassword123!"}).encode(),
    )
    assert status in (401, 422), f"Expected 401/422 for wrong password, got {status}: {body}"

    # Valid Login
    new_jar = http.cookiejar.CookieJar()
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"destination": phone, "password": password}).encode(),
        cookie_jar=new_jar,
    )
    assert status == 200, f"Expected 200 for valid login, got {status}: {body}"
    assert isinstance(body, dict) and body.get("ok") is True, f"Expected ok: True, got {body}"
    assert body.get("user_id") == user_id, f"user_id mismatch: {body.get('user_id')} vs {user_id}"
    print(f"  OK: Standalone login succeeded for destination {phone} -> session issued.")


def run_phase_9(cookie_jar: http.cookiejar.CookieJar, user_id: str, password: str) -> None:
    print("\n--- Phase 9: Step-Up MFA Challenge Flow Verification ---")
    # Enroll TOTP for this candidate
    status, sec_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security",
        method="PATCH",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"enable_totp": True, "current_password": password}).encode(),
        cookie_jar=cookie_jar,
    )
    assert status == 200, f"Failed to initiate TOTP enrollment: {sec_body}"
    assert isinstance(sec_body, dict)
    secret = sec_body.get("secret")
    assert secret, f"Secret missing in {sec_body}"

    # Confirm enrollment with valid code
    totp_code = generate_totp_code(secret)
    status, confirm_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security/totp/confirm",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"code": totp_code}).encode(),
        cookie_jar=cookie_jar,
    )
    assert status == 200, f"Failed to confirm TOTP: {confirm_body}"

    # Now attempt login without TOTP code -> must return HTTP 202 MFA Challenge Required!
    status, login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"user_id": user_id, "password": password}).encode(),
    )
    assert status == 202, f"Expected 202 MFA Challenge, got {status}: {login_body}"
    assert isinstance(login_body, dict)
    assert login_body.get("mfa_required") is True, f"Expected mfa_required: True, got {login_body}"
    assert login_body.get("mfa_ticket"), f"Expected mfa_ticket in {login_body}"

    # Verify MFA ticket with code
    status, mfa_res, _ = make_request(
        f"{FRONTEND_URL}/api/auth/mfa/verify",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "mfa_ticket": login_body.get("mfa_ticket"),
            "code": generate_totp_code(secret),
        }).encode(),
    )
    assert status == 200, f"Expected 200 for MFA verify, got {status}: {mfa_res}"
    print("  OK: Step-Up MFA Challenge (HTTP 202) and ticket verification verified.")


def run_phase_10() -> None:
    print("\n--- Phase 10: SSR HTML Verification (/kirish, /royxatdan-otish, /) ---")
    # 1. /kirish
    status, html, _ = make_request(f"{FRONTEND_URL}/kirish")
    assert status == 200, f"Expected 200 for /kirish, got {status}"
    assert isinstance(html, str) and len(html) > 500, f"Expected non-empty HTML for /kirish"
    assert "Tizimga Kirish" in html or "kirish" in html.lower(), "Expected Tizimga Kirish in HTML"
    assert "/royxatdan-otish" in html, "Expected link to /royxatdan-otish in /kirish"
    print(f"  OK: /kirish SSR HTML validated ({len(html)} bytes).")

    # 2. /royxatdan-otish
    status, html, _ = make_request(f"{FRONTEND_URL}/royxatdan-otish")
    assert status == 200, f"Expected 200 for /royxatdan-otish, got {status}"
    assert isinstance(html, str) and len(html) > 500, f"Expected non-empty HTML for /royxatdan-otish"
    assert "yxatdan" in html.lower(), "Expected registration elements in HTML"
    assert "/kirish" in html, "Expected link to /kirish in /royxatdan-otish"
    print(f"  OK: /royxatdan-otish SSR HTML validated ({len(html)} bytes).")

    # 3. / (Home) Navbar
    status, html, _ = make_request(f"{FRONTEND_URL}/")
    assert status == 200, f"Expected 200 for /, got {status}"
    assert isinstance(html, str) and len(html) > 500
    assert "/kirish" in html, "Navbar link to /kirish missing on homepage"
    assert "/royxatdan-otish" in html, "Navbar link to /royxatdan-otish missing on homepage"
    print(f"  OK: Homepage navbar contains direct links to /kirish and /royxatdan-otish.")


def main() -> int:
    print("================================================================================")
    print("FlexBridge 1.4 Standalone Auth & Onboarding Staging Suite (FB-190)")
    print("================================================================================")
    try:
        run_phase_1()
        run_phase_2()
        ch_id = run_phase_3()
        run_phase_4(ch_id)
        run_phase_5()
        user, phone, password, jar = run_phase_6_and_7()
        run_phase_8(user["id"], phone, password)
        run_phase_9(jar, user["id"], password)
        run_phase_10()
        print("\n================================================================================")
        print("SUCCESS: ALL 10 PHASES OF FB-190 STANDALONE AUTH SUITE PASSED 100% GREEN!")
        print("================================================================================")
        return 0
    except AssertionError as err:
        print(f"\nFAIL: Verification failed: {err}")
        return 1
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"\nERROR: Unexpected error: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
