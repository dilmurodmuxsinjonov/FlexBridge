#!/usr/bin/env python3
"""FlexBridge 1.4 Employer Isolated Login & Invitation Onboarding Verification Suite.

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: SSR HTML isolation on /korxona/kirish, /korxona/royxatdan-otish, /employer, /kirish, and /.
Phase 2: Employer (OWNER) non-MFA and MFA-enabled login on portal="EMPLOYER" -> HTTP 200 + session cookie.
Phase 3: Cross-role portal isolation (pure CANDIDATE student and PLATFORM OPERATOR rejected with
         403 ROLE_PORTAL_MISMATCH & NO cookie on password login and /api/auth/mfa/verify).
Phase 4: End-to-end Employer invitation onboarding (API-074 -> GET /api/bff/invitations/[token] ->
         POST /api/bff/invitations/[token]/accept -> refreshed HR role -> login with portal="EMPLOYER").

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

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
from app.core.iam_security import decrypt
from app.services.auth import generate_totp_code

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
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
                return status, json.loads(body), resp_headers
            except Exception:
                return status, body, resp_headers
    except urllib.error.HTTPError as exc:
        status = exc.code
        resp_headers = dict(exc.headers)
        body = exc.read().decode("utf-8")
        try:
            return status, json.loads(body), resp_headers
        except Exception:
            return status, body, resp_headers


def issue_and_consume_otp(phone: str | None = None) -> tuple[str, str]:
    if not phone:
        suffix = uuid4().hex[:7]
        phone = f"+99890{int(suffix, 16) % 10000000:07d}"

    status, chal_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"channel": "PHONE", "destination": phone, "purpose": "REGISTER"}).encode(),
    )
    assert status == 202, f"Expected 202 challenge, got {status}: {chal_body}"
    challenge_id = chal_body["challenge_id"]

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT delivery_encrypted FROM flexbridge.auth_challenges WHERE id = :id"),
            {"id": challenge_id},
        ).mappings().first()
        assert row and row["delivery_encrypted"], f"Missing delivery_encrypted for {challenge_id}"
        otp_code = decrypt(row["delivery_encrypted"])["code"]
        conn.execute(
            text("UPDATE flexbridge.auth_challenges SET delivery_status = 'SENT' WHERE id = :id"),
            {"id": challenge_id},
        )

    status, consume_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges/{challenge_id}/consume",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"purpose": "REGISTER", "code": otp_code}).encode(),
    )
    assert status == 200, f"Expected 200 consume, got {status}: {consume_body}"
    return phone, consume_body["verification_token"]


def register_user(display_name: str, phone: str | None = None) -> tuple[dict[str, Any], str, str, http.cookiejar.CookieJar]:
    reg_phone, verification_token = issue_and_consume_otp(phone)
    password = f"FlexBridge!{uuid4().hex[:8]}99"

    jar = http.cookiejar.CookieJar()
    status, reg_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/register",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "verification_token": verification_token,
            "display_name": display_name,
            "password": password,
            "adult_confirmed": True,
            "terms_version": "2026.1",
            "privacy_version": "2026.1",
            "roles": ["CANDIDATE"],
        }).encode(),
        cookie_jar=jar,
    )
    assert status == 201, f"Expected 201 register, got {status}: {reg_body}"
    assert isinstance(reg_body, dict) and reg_body.get("ok") is True
    return reg_body["user"], reg_phone, password, jar


def grant_org_owner_role(user_id: str) -> str:
    suffix = uuid4().hex[:6]
    org_id = str(uuid4())
    mem_id = str(uuid4())
    grant_id = str(uuid4())
    now_ts = datetime.now(timezone.utc)
    with engine.begin() as conn:
        owner_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE scope_kind = 'ORG' AND code = 'OWNER' LIMIT 1")
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, legal_name, public_name, tax_id, status, region)
                VALUES (:id, :ts, :ts, :lname, :pname, :tax, 'VERIFIED', 'Tashkent')
                """
            ),
            {
                "id": org_id,
                "ts": now_ts,
                "lname": f"EmpIso Corp {suffix}",
                "pname": f"EmpIso {suffix}",
                "tax": f"TAX_EMPISO_{suffix}",
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status, accepted_at)
                VALUES (:mid, :ts, :ts, :oid, :uid, 'ACTIVE', :ts)
                """
            ),
            {"mid": mem_id, "ts": now_ts, "oid": org_id, "uid": user_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.org_role_grants (id, created_at, updated_at, membership_id, role_id, granted_by_id)
                VALUES (:gid, :ts, :ts, :mid, :rid, :uid)
                """
            ),
            {"gid": grant_id, "ts": now_ts, "mid": mem_id, "rid": owner_role_id, "uid": user_id},
        )
    return org_id


def grant_platform_operator_role(user_id: str, granter_id: str) -> None:
    now_ts = datetime.now(timezone.utc)
    exp_ts = now_ts + timedelta(days=1)
    with engine.begin() as conn:
        op_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE scope_kind = 'PLATFORM' AND code = 'OPERATOR' LIMIT 1")
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.platform_role_grants (id, created_at, updated_at, user_id, role_id, granted_by_id, expires_at)
                VALUES (:gid, :ts, :ts, :uid, :rid, :granter, :exp)
                """
            ),
            {
                "gid": str(uuid4()),
                "ts": now_ts,
                "uid": user_id,
                "rid": op_role_id,
                "granter": granter_id,
                "exp": exp_ts,
            },
        )


def enroll_totp(cookie_jar: http.cookiejar.CookieJar, password: str) -> str:
    status, sec_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security",
        method="PATCH",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"enable_totp": True, "current_password": password}).encode(),
        cookie_jar=cookie_jar,
    )
    assert status == 200 and isinstance(sec_body, dict) and sec_body.get("secret"), f"Enroll failed: {sec_body}"
    secret = sec_body["secret"]

    status, conf_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/security/totp/confirm",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"code": generate_totp_code(secret)}).encode(),
        cookie_jar=cookie_jar,
    )
    assert status == 200, f"TOTP confirm failed: {conf_body}"
    return secret


def login_with_mfa(
    phone: str,
    password: str,
    totp_secret: str,
    portal: str | None = None,
) -> tuple[int, dict[str, Any] | str, http.cookiejar.CookieJar]:
    jar = http.cookiejar.CookieJar()
    payload: dict[str, Any] = {"destination": phone, "password": password}
    if portal is not None:
        payload["portal"] = portal
    status, chal_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(payload).encode(),
        cookie_jar=jar,
    )
    assert status == 202 and isinstance(chal_body, dict) and chal_body.get("mfa_ticket"), (
        f"Expected 202 MFA challenge, got {status}: {chal_body}"
    )

    mfa_payload: dict[str, Any] = {
        "mfa_ticket": chal_body["mfa_ticket"],
        "code": generate_totp_code(totp_secret),
    }
    if portal is not None:
        mfa_payload["portal"] = portal

    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/mfa/verify",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(mfa_payload).encode(),
        cookie_jar=jar,
    )
    return status, body, jar


def run_phase_1() -> None:
    print("\n--- Phase 1: Employer SSR HTML Isolation Checks ---")
    for path in ("/korxona/kirish", "/korxona/royxatdan-otish", "/employer"):
        status, html, _ = make_request(f"{FRONTEND_URL}{path}")
        assert status == 200, f"Expected 200 for {path}, got {status}"
        assert isinstance(html, str) and len(html) > 500, f"Expected HTML on {path}"
        assert 'href="/nomzod"' not in html, f"Student link leaked into employer SSR on {path}"
        assert 'href="/talaba/kirish"' not in html, f"Student login leaked into employer SSR on {path}"
        assert 'href="/university"' not in html, f"University link leaked into employer SSR on {path}"
        assert 'href="/operator"' not in html, f"Operator link leaked into employer SSR on {path}"
        assert "Verified Skill" not in html, f"Forbidden Skill Badge leaked on {path}"
        assert "Match Coach" not in html, f"Forbidden Match Coach leaked on {path}"
        print(f"  OK: {path} SSR clean ({len(html)} bytes, 0 non-employer portal links).")

    status, kirish_html, _ = make_request(f"{FRONTEND_URL}/kirish")
    assert status == 200 and isinstance(kirish_html, str)
    assert "/korxona/kirish" in kirish_html, "Expected /korxona/kirish shortcut inside /kirish SSR"

    status, home_html, _ = make_request(f"{FRONTEND_URL}/")
    assert status == 200 and isinstance(home_html, str)
    assert "/korxona/kirish" in home_html, "Expected /korxona/kirish entry inside / SSR"
    assert "/employer" in home_html, "Expected /employer entry inside / SSR"
    print("  OK: /kirish and / expose direct /korxona/kirish entry links.")


def run_phase_2() -> tuple[dict[str, Any], str, str, str, http.cookiejar.CookieJar, str]:
    print("\n--- Phase 2: Employer (OWNER) Login & MFA Session Verification ---")
    emp_user, emp_phone, emp_pass, emp_reg_jar = register_user(f"EmployerOwner {uuid4().hex[:5]}")
    org_id = grant_org_owner_role(emp_user["id"])

    # Non-MFA password login on EMPLOYER portal
    emp_jar = http.cookiejar.CookieJar()
    status, login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": emp_phone,
            "password": emp_pass,
            "portal": "EMPLOYER",
        }).encode(),
        cookie_jar=emp_jar,
    )
    assert status == 200, f"Expected 200 on EMPLOYER login, got {status}: {login_body}"
    assert isinstance(login_body, dict) and "OWNER" in login_body.get("roles", [])
    assert len(emp_jar) >= 1, "Expected session cookie on EMPLOYER login"

    me_status, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=emp_jar)
    assert me_status == 200 and isinstance(me_body, dict) and "OWNER" in (me_body.get("user") or {}).get("roles", []), (
        f"Expected OWNER in /api/auth/me user.roles: {me_body}"
    )

    # Enroll TOTP and confirm MFA login on EMPLOYER portal
    emp_secret = enroll_totp(emp_reg_jar, emp_pass)
    mfa_status, mfa_body, emp_mfa_jar = login_with_mfa(emp_phone, emp_pass, emp_secret, portal="EMPLOYER")
    assert mfa_status == 200 and isinstance(mfa_body, dict) and "OWNER" in mfa_body.get("roles", []), (
        f"Expected 200 OWNER on EMPLOYER MFA login, got {mfa_status}: {mfa_body}"
    )
    print(f"  OK: ORG OWNER verified for non-MFA and MFA login on EMPLOYER portal (org_id={org_id}).")
    return emp_user, emp_phone, emp_pass, emp_secret, emp_mfa_jar, org_id


def run_phase_3(granter_id: str) -> None:
    print("\n--- Phase 3: Cross-Role Rejection on EMPLOYER Portal ---")
    # 1. Pure CANDIDATE student (password & MFA) rejected on EMPLOYER portal
    stu_user, stu_phone, stu_pass, stu_reg_jar = register_user(f"PureStudent {uuid4().hex[:5]}")
    bad_stu_jar = http.cookiejar.CookieJar()
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": stu_phone,
            "password": stu_pass,
            "portal": "EMPLOYER",
        }).encode(),
        cookie_jar=bad_stu_jar,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for Student, got {status}: {body}"
    assert isinstance(body, dict) and body.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_stu_jar) == 0, "Expected zero cookies set on rejected Student EMPLOYER login"

    me_status, _, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=bad_stu_jar)
    assert me_status == 401, f"Expected 401 /api/auth/me after rejected Student login, got {me_status}"

    stu_secret = enroll_totp(stu_reg_jar, stu_pass)
    mfa_status, mfa_err, bad_stu_mfa_jar = login_with_mfa(stu_phone, stu_pass, stu_secret, portal="EMPLOYER")
    assert mfa_status == 403, f"Expected 403 on Student MFA verify for EMPLOYER portal, got {mfa_status}: {mfa_err}"
    assert isinstance(mfa_err, dict) and mfa_err.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_stu_mfa_jar) == 0, "Expected zero cookies on rejected Student MFA"

    # 2. PLATFORM OPERATOR rejected on EMPLOYER portal
    op_user, op_phone, op_pass, _ = register_user(f"OpUser {uuid4().hex[:5]}")
    grant_platform_operator_role(op_user["id"], granter_id)
    bad_op_jar = http.cookiejar.CookieJar()
    status, op_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": op_phone,
            "password": op_pass,
            "portal": "EMPLOYER",
        }).encode(),
        cookie_jar=bad_op_jar,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for OPERATOR, got {status}: {op_body}"
    assert isinstance(op_body, dict) and op_body.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_op_jar) == 0, "Expected zero cookies on rejected OPERATOR login"
    print("  OK: Pure Student (password + MFA) & Operator blocked on EMPLOYER portal (403, 0 cookies).")


def run_phase_4(org_id: str, owner_mfa_jar: http.cookiejar.CookieJar) -> None:
    print("\n--- Phase 4: Employer Invitation Onboarding & EMPLOYER Portal Login ---")
    invitee_suffix = uuid4().hex[:7]
    invitee_phone = f"+99890{int(invitee_suffix, 16) % 10000000:07d}"

    # 1. OWNER creates HR invitation via BFF (API-074)
    status, inv_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/invitations",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "channel": "PHONE",
            "destination": invitee_phone,
            "role_code": "HR",
        }).encode(),
        cookie_jar=owner_mfa_jar,
    )
    assert status == 201 and isinstance(inv_body, dict) and inv_body.get("token"), (
        f"Expected 201 invitation creation, got {status}: {inv_body}"
    )
    token = inv_body["token"]
    assert len(token) == 43, f"Expected 43-char invitation token, got len={len(token)}"

    # 2. Preview invitation anonymously via /api/bff/invitations/[token] (API-024)
    status, preview_body, _ = make_request(f"{FRONTEND_URL}/api/bff/invitations/{token}")
    assert status == 200 and isinstance(preview_body, dict), f"Preview failed ({status}): {preview_body}"
    assert preview_body.get("contract_id") == "API-024"
    assert preview_body.get("role_code") == "HR"

    # 3. Invitee registers on exact invited phone, enrolls TOTP, obtains MFA session, accepts invitation (API-025)
    hr_user, _, hr_pass, hr_reg_jar = register_user(f"InvitedHR {uuid4().hex[:5]}", phone=invitee_phone)
    hr_secret = enroll_totp(hr_reg_jar, hr_pass)
    hr_mfa_status, _, hr_mfa_jar = login_with_mfa(invitee_phone, hr_pass, hr_secret)
    assert hr_mfa_status == 200, f"Invitee MFA login before accept failed: {hr_mfa_status}"

    status, acc_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/invitations/{token}/accept",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({}).encode(),
        cookie_jar=hr_mfa_jar,
    )
    assert status == 200 and isinstance(acc_body, dict), f"Invitation accept failed ({status}): {acc_body}"
    assert acc_body.get("status") == "ACTIVE"
    assert "HR" in acc_body.get("roles", []), (
        f"Expected refreshed session response to include HR role: {acc_body}"
    )

    me_status, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=hr_mfa_jar)
    assert me_status == 200 and isinstance(me_body, dict) and "HR" in (me_body.get("user") or {}).get("roles", []), (
        f"Expected /api/auth/me cookie session to include HR role after accept: {me_body}"
    )

    # 4. Invited HR now logs directly into EMPLOYER portal with MFA -> HTTP 200
    emp_login_status, emp_login_body, hr_emp_jar = login_with_mfa(
        invitee_phone, hr_pass, hr_secret, portal="EMPLOYER"
    )
    assert emp_login_status == 200 and isinstance(emp_login_body, dict), (
        f"Expected 200 EMPLOYER portal login for invited HR, got {emp_login_status}: {emp_login_body}"
    )
    assert "HR" in emp_login_body.get("roles", [])
    assert emp_login_body.get("user_id") == hr_user["id"]
    assert len(hr_emp_jar) >= 1
    print("  OK: Invitation preview -> accept -> role refresh -> EMPLOYER portal MFA login passed.")


def main() -> int:
    print("=" * 72)
    print("  FLEXBRIDGE 1.4: EMPLOYER ISOLATED LOGIN & INVITATION VERIFICATION")
    print("=" * 72)
    run_phase_1()
    emp_user, _, _, _, emp_mfa_jar, org_id = run_phase_2()
    run_phase_3(emp_user["id"])
    run_phase_4(org_id, emp_mfa_jar)
    print("\nALL 4 PHASES PASSED SUCCESSFULLY!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
