#!/usr/bin/env python3
"""FlexBridge 1.4 Student Isolated Login & Registration Verification Suite.

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: SSR HTML isolation on /talaba/kirish, /talaba/royxatdan-otish, /nomzod, /kirish, and /.
Phase 2: End-to-end Student (CANDIDATE) registration via OTP challenge & /api/bff/auth/register
         (plus verifying public registration rejects non-student privileged roles).
Phase 3: Student login with portal="CANDIDATE" -> HTTP 200 + session cookie + /api/auth/me.
Phase 4: Cross-role portal isolation (ORG OWNER and PLATFORM OPERATOR rejected with
         403 ROLE_PORTAL_MISMATCH & NO cookie, even though backend roles_for includes CANDIDATE).
Phase 5: Step-up MFA isolation on /api/auth/mfa/verify (ORG OWNER 2FA rejected with 403; CANDIDATE 2FA -> 200).

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


def issue_and_consume_otp() -> tuple[str, str]:
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


def register_candidate_user(display_name: str) -> tuple[dict[str, Any], str, str, http.cookiejar.CookieJar]:
    phone, verification_token = issue_and_consume_otp()
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
    return reg_body["user"], phone, password, jar


def grant_org_owner_role(user_id: str) -> None:
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
                "lname": f"IsoTest Corp {suffix}",
                "pname": f"IsoTest {suffix}",
                "tax": f"TAX_ISO_{suffix}",
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


def run_phase_1() -> None:
    print("\n--- Phase 1: SSR HTML Isolation Checks ---")
    for path in ("/talaba/kirish", "/talaba/royxatdan-otish", "/nomzod"):
        status, html, _ = make_request(f"{FRONTEND_URL}{path}")
        assert status == 200, f"Expected 200 for {path}, got {status}"
        assert isinstance(html, str) and len(html) > 500, f"Expected HTML on {path}"
        assert 'href="/employer"' not in html, f"Employer link leaked into student SSR on {path}"
        assert 'href="/university"' not in html, f"University link leaked into student SSR on {path}"
        assert 'href="/operator"' not in html, f"Operator link leaked into student SSR on {path}"
        assert "Verified Skill" not in html, f"Forbidden Skill Badge leaked on {path}"
        assert "Match Coach" not in html, f"Forbidden Match Coach leaked on {path}"
        print(f"  OK: {path} SSR clean ({len(html)} bytes, 0 non-student links, 0 excluded widgets).")

    status, kirish_html, _ = make_request(f"{FRONTEND_URL}/kirish")
    assert status == 200 and isinstance(kirish_html, str)
    assert "/talaba/kirish" in kirish_html, "Expected /talaba/kirish shortcut inside /kirish SSR"

    status, home_html, _ = make_request(f"{FRONTEND_URL}/")
    assert status == 200 and isinstance(home_html, str)
    assert "/talaba/kirish" in home_html, "Expected /talaba/kirish entry inside / SSR"
    assert "/nomzod" in home_html, "Expected /nomzod entry inside / SSR"
    print("  OK: /kirish and / expose direct /talaba/kirish entry links.")


def run_phase_2_and_3() -> tuple[dict[str, Any], str, str, http.cookiejar.CookieJar]:
    print("\n--- Phase 2 & 3: Student Registration & Isolated Portal Login ---")
    # Verify privileged role signup is blocked publicly
    _, priv_token = issue_and_consume_otp()
    status, priv_err, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/register",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "verification_token": priv_token,
            "display_name": "Forbidden Role Attempt",
            "password": f"FlexBridge!{uuid4().hex[:8]}99",
            "adult_confirmed": True,
            "terms_version": "2026.1",
            "privacy_version": "2026.1",
            "roles": ["EMPLOYER"],
        }).encode(),
    )
    assert status == 403, f"Expected 403 for privileged signup, got {status}: {priv_err}"

    student_user, phone, password, reg_jar = register_candidate_user(f"Talaba {uuid4().hex[:5]}")
    assert student_user["roles"] == ["CANDIDATE"]

    student_jar = http.cookiejar.CookieJar()
    status, login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": phone,
            "password": password,
            "portal": "CANDIDATE",
        }).encode(),
        cookie_jar=student_jar,
    )
    assert status == 200, f"Student login on CANDIDATE portal failed: {status} {login_body}"
    assert isinstance(login_body, dict) and login_body.get("ok") is True
    assert "CANDIDATE" in login_body.get("roles", [])

    status, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=student_jar)
    assert status == 200 and isinstance(me_body, dict) and me_body.get("ok") is True
    assert me_body["user"]["user_id"] == student_user["id"]
    print(f"  OK: Student {student_user['id']} logged into CANDIDATE portal with active session.")
    return student_user, phone, password, reg_jar


def run_phase_4(granter_id: str) -> tuple[dict[str, Any], str, str, http.cookiejar.CookieJar]:
    print("\n--- Phase 4: Cross-Role Portal Rejection (ORG OWNER & PLATFORM OPERATOR) ---")
    emp_user, emp_phone, emp_pass, emp_reg_jar = register_candidate_user(f"Korxona {uuid4().hex[:5]}")
    grant_org_owner_role(emp_user["id"])

    bad_jar_emp = http.cookiejar.CookieJar()
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": emp_phone,
            "password": emp_pass,
            "portal": "CANDIDATE",
        }).encode(),
        cookie_jar=bad_jar_emp,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for ORG OWNER, got {status}: {body}"
    assert isinstance(body, dict) and body.get("error") == "ROLE_PORTAL_MISMATCH", f"Unexpected body: {body}"
    assert len(bad_jar_emp) == 0, "Expected zero cookies set on rejected ORG OWNER login"

    me_status, _, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=bad_jar_emp)
    assert me_status == 401, f"Expected 401 /api/auth/me after rejected login, got {me_status}"

    # Verify ORG OWNER still succeeds on EMPLOYER portal
    ok_emp_jar = http.cookiejar.CookieJar()
    ok_status, ok_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": emp_phone,
            "password": emp_pass,
            "portal": "EMPLOYER",
        }).encode(),
        cookie_jar=ok_emp_jar,
    )
    assert ok_status == 200 and isinstance(ok_body, dict) and "OWNER" in ok_body.get("roles", [])

    op_user, op_phone, op_pass, _ = register_candidate_user(f"Operator {uuid4().hex[:5]}")
    grant_platform_operator_role(op_user["id"], granter_id)

    bad_jar_op = http.cookiejar.CookieJar()
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": op_phone,
            "password": op_pass,
            "portal": "CANDIDATE",
        }).encode(),
        cookie_jar=bad_jar_op,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for OPERATOR, got {status}: {body}"
    assert isinstance(body, dict) and body.get("error") == "ROLE_PORTAL_MISMATCH", f"Unexpected body: {body}"
    assert len(bad_jar_op) == 0, "Expected zero cookies set on rejected OPERATOR login"
    print("  OK: ORG OWNER & PLATFORM OPERATOR blocked on CANDIDATE portal (403, 0 cookies).")
    return emp_user, emp_phone, emp_pass, emp_reg_jar


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


def run_phase_5(
    student_user: dict[str, Any],
    student_phone: str,
    student_pass: str,
    student_reg_jar: http.cookiejar.CookieJar,
    employer_phone: str,
    employer_pass: str,
    employer_reg_jar: http.cookiejar.CookieJar,
) -> None:
    print("\n--- Phase 5: MFA Portal Boundary Enforcement ---")
    emp_secret = enroll_totp(employer_reg_jar, employer_pass)
    emp_mfa_jar = http.cookiejar.CookieJar()
    status, chal_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": employer_phone,
            "password": employer_pass,
            "portal": "CANDIDATE",
        }).encode(),
        cookie_jar=emp_mfa_jar,
    )
    assert status == 202 and isinstance(chal_body, dict) and chal_body.get("mfa_ticket"), f"Expected 202: {chal_body}"

    status, mfa_err, _ = make_request(
        f"{FRONTEND_URL}/api/auth/mfa/verify",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "mfa_ticket": chal_body["mfa_ticket"],
            "code": generate_totp_code(emp_secret),
            "portal": "CANDIDATE",
        }).encode(),
        cookie_jar=emp_mfa_jar,
    )
    assert status == 403, f"Expected 403 on ORG OWNER MFA verify for CANDIDATE portal, got {status}: {mfa_err}"
    assert isinstance(mfa_err, dict) and mfa_err.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(emp_mfa_jar) == 0, "Expected zero cookies set on rejected ORG OWNER MFA"

    stu_secret = enroll_totp(student_reg_jar, student_pass)
    stu_mfa_jar = http.cookiejar.CookieJar()
    status, stu_chal, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": student_phone,
            "password": student_pass,
            "portal": "CANDIDATE",
        }).encode(),
        cookie_jar=stu_mfa_jar,
    )
    assert status == 202 and isinstance(stu_chal, dict) and stu_chal.get("mfa_ticket"), f"Expected 202: {stu_chal}"

    status, stu_ok, _ = make_request(
        f"{FRONTEND_URL}/api/auth/mfa/verify",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "mfa_ticket": stu_chal["mfa_ticket"],
            "code": generate_totp_code(stu_secret),
            "portal": "CANDIDATE",
        }).encode(),
        cookie_jar=stu_mfa_jar,
    )
    assert status == 200, f"Expected 200 for CANDIDATE MFA verify, got {status}: {stu_ok}"
    assert isinstance(stu_ok, dict) and stu_ok.get("user_id") == student_user["id"]
    print("  OK: MFA portal enforcement verified (ORG OWNER 403/0 cookies, CANDIDATE 200/session active).")


def main() -> int:
    print("=" * 72)
    print("  FLEXBRIDGE 1.4: STUDENT ISOLATED LOGIN & REGISTRATION VERIFICATION")
    print("=" * 72)
    run_phase_1()
    student_user, stu_phone, stu_pass, stu_jar = run_phase_2_and_3()
    _, emp_phone, emp_pass, emp_jar = run_phase_4(student_user["id"])
    run_phase_5(student_user, stu_phone, stu_pass, stu_jar, emp_phone, emp_pass, emp_jar)
    print("\nALL 5 PHASES PASSED SUCCESSFULLY!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
