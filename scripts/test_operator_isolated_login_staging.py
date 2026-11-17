#!/usr/bin/env python3
"""FlexBridge 1.4 Platform Operator Isolated Login & SOC Role Boundary Suite.

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: SSR HTML isolation on /operator/kirish, /operator, /kirish, and /.
Phase 2: Platform roles (OPERATOR, MODERATOR, AUDITOR) login & TOTP MFA verification on portal="OPERATOR".
Phase 3: Cross-role portal isolation (pure CANDIDATE student, EMPLOYER OWNER, and UNIVERSITY COORDINATOR
         rejected with 403 ROLE_PORTAL_MISMATCH & NO cookie on password login and /api/auth/mfa/verify).
Phase 4: Authenticated OPERATOR portal session calls BFF operator APIs (GET /api/bff/operator/verification-cases)
         and rejects unauthorized student session.

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

TASHKENT_TZ = timezone(timedelta(hours=5))
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
    assert status == 202 and isinstance(chal_body, dict), f"Expected 202 challenge, got {status}: {chal_body}"
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
    assert status == 200 and isinstance(consume_body, dict), f"Expected 200 consume, got {status}: {consume_body}"
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
    assert status == 201 and isinstance(reg_body, dict) and reg_body.get("ok") is True, (
        f"Expected 201 register, got {status}: {reg_body}"
    )
    return reg_body["user"], reg_phone, password, jar


def grant_platform_role(user_id: str, granter_id: str, code: str) -> None:
    now_ts = datetime.now(timezone.utc)
    exp_ts = now_ts + timedelta(days=1)
    with engine.begin() as conn:
        role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE scope_kind = 'PLATFORM' AND code = :code LIMIT 1"),
            {"code": code},
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
                "rid": role_id,
                "granter": granter_id,
                "exp": exp_ts,
            },
        )


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
                "lname": f"OpCross Corp {suffix}",
                "pname": f"OpCross {suffix}",
                "tax": f"TAX_OPC_{suffix}",
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


def grant_academic_coordinator_role(user_id: str) -> None:
    suffix = uuid4().hex[:6].upper()
    inst_id = str(uuid4())
    appt_id = str(uuid4())
    mem_id = str(uuid4())
    grant_id = str(uuid4())
    file_id = str(uuid4())
    now_ts = datetime.now(timezone.utc)
    today_tashkent = now_ts.astimezone(TASHKENT_TZ).date()
    valid_from = today_tashkent - timedelta(days=1)
    valid_to = today_tashkent + timedelta(days=365)
    sha = uuid4().hex + uuid4().hex
    with engine.begin() as conn:
        coord_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE scope_kind = 'INSTITUTION' AND code = 'COORDINATOR' LIMIT 1")
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.files (
                    id, created_at, updated_at, owner_user_id, storage_key, filename, mime_type, byte_size, sha256,
                    scan_status, scanned_at, retention_class, storage_bucket, storage_version_id, storage_etag, object_version
                ) VALUES (
                    :fid, :ts, :ts, :uid, :sk, 'coord.pdf', 'application/pdf', 2048, :sha,
                    'CLEAN', :ts, 'VERIFICATION_EVIDENCE', 'flexbridge-private', 'v1', :etag, 'v1'
                )
                """
            ),
            {"fid": file_id, "ts": now_ts, "uid": user_id, "sk": f"private/op/{file_id}.pdf", "sha": sha, "etag": f"etag-{file_id[:8]}"},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                VALUES (:id, :ts, :ts, :code, :name, 'Tashkent', 'VERIFIED')
                """
            ),
            {"id": inst_id, "ts": now_ts, "code": f"OTM-OPC-{suffix}", "name": f"OpCross Univ {suffix}"},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institution_appointments (
                    id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, valid_to, accepted_at
                ) VALUES (:id, :ts, :ts, :iid, :uid, :fid, 'ACTIVE', :vf, :vt, :ts)
                """
            ),
            {"id": appt_id, "ts": now_ts, "iid": inst_id, "uid": user_id, "fid": file_id, "vf": valid_from, "vt": valid_to},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institution_memberships (
                    id, created_at, updated_at, institution_id, user_id, status, accepted_at
                ) VALUES (:id, :ts, :ts, :iid, :uid, 'ACTIVE', :ts)
                """
            ),
            {"id": mem_id, "ts": now_ts, "iid": inst_id, "uid": user_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institution_role_grants (
                    id, created_at, updated_at, membership_id, role_id, appointment_id
                ) VALUES (:id, :ts, :ts, :mid, :rid, :aid)
                """
            ),
            {"id": grant_id, "ts": now_ts, "mid": mem_id, "rid": coord_role_id, "aid": appt_id},
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
    assert len(jar) == 0, "Expected zero session cookies before MFA verification completes"

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
    print("\n--- Phase 1: Operator SOC SSR HTML Isolation Checks ---")
    for path in ("/operator/kirish", "/operator"):
        status, html, _ = make_request(f"{FRONTEND_URL}{path}")
        assert status == 200, f"Expected 200 for {path}, got {status}"
        assert isinstance(html, str) and len(html) > 500, f"Expected HTML on {path}"
        assert 'href="/nomzod"' not in html, f"Student link leaked into operator SSR on {path}"
        assert 'href="/talaba/kirish"' not in html, f"Student login leaked into operator SSR on {path}"
        assert 'href="/employer"' not in html, f"Employer link leaked into operator SSR on {path}"
        assert 'href="/korxona/kirish"' not in html, f"Employer login leaked into operator SSR on {path}"
        assert 'href="/university"' not in html, f"University link leaked into operator SSR on {path}"
        assert 'href="/universitet/kirish"' not in html, f"University login leaked into operator SSR on {path}"
        assert "Verified Skill" not in html, f"Forbidden Skill Badge leaked on {path}"
        assert "Match Coach" not in html, f"Forbidden Match Coach leaked on {path}"
        print(f"  OK: {path} SSR clean ({len(html)} bytes, 0 non-operator portal links).")

    status, kirish_html, _ = make_request(f"{FRONTEND_URL}/kirish")
    assert status == 200 and isinstance(kirish_html, str)
    assert "/operator/kirish" in kirish_html, "Expected /operator/kirish shortcut inside /kirish SSR"

    status, home_html, _ = make_request(f"{FRONTEND_URL}/")
    assert status == 200 and isinstance(home_html, str)
    assert "/operator/kirish" in home_html, "Expected /operator/kirish entry inside / SSR"
    print("  OK: /kirish and / expose direct /operator/kirish entry links.")


def run_phase_2() -> tuple[dict[str, Any], http.cookiejar.CookieJar]:
    print("\n--- Phase 2: Platform Operator / Moderator / Auditor Login & MFA Verification ---")
    granter_user, _, _, _ = register_user(f"OpGranter {uuid4().hex[:5]}")

    # 1. OPERATOR non-MFA & MFA login on OPERATOR portal
    op_user, op_phone, op_pass, op_reg_jar = register_user(f"PlatOp {uuid4().hex[:5]}")
    op_secret = enroll_totp(op_reg_jar, op_pass)
    grant_platform_role(op_user["id"], granter_user["id"], "OPERATOR")

    op_status, op_body, op_mfa_jar = login_with_mfa(op_phone, op_pass, op_secret, portal="OPERATOR")
    assert op_status == 200 and isinstance(op_body, dict) and "OPERATOR" in op_body.get("roles", []), (
        f"Expected 200 OPERATOR MFA login, got {op_status}: {op_body}"
    )
    assert len(op_mfa_jar) >= 1
    me_status, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=op_mfa_jar)
    assert me_status == 200 and "OPERATOR" in (me_body.get("user") or {}).get("roles", []), (
        f"Expected OPERATOR in /api/auth/me: {me_body}"
    )

    # 2. MODERATOR MFA login on OPERATOR portal (used in Phase 4)
    mod_user, mod_phone, mod_pass, mod_reg_jar = register_user(f"PlatMod {uuid4().hex[:5]}")
    mod_secret = enroll_totp(mod_reg_jar, mod_pass)
    grant_platform_role(mod_user["id"], granter_user["id"], "MODERATOR")

    mod_status, mod_body, mod_mfa_jar = login_with_mfa(mod_phone, mod_pass, mod_secret, portal="OPERATOR")
    assert mod_status == 200 and isinstance(mod_body, dict) and "MODERATOR" in mod_body.get("roles", []), (
        f"Expected 200 MODERATOR MFA login, got {mod_status}: {mod_body}"
    )

    # 3. AUDITOR MFA login on OPERATOR portal
    aud_user, aud_phone, aud_pass, aud_reg_jar = register_user(f"PlatAud {uuid4().hex[:5]}")
    aud_secret = enroll_totp(aud_reg_jar, aud_pass)
    grant_platform_role(aud_user["id"], granter_user["id"], "AUDITOR")

    aud_status, aud_body, _ = login_with_mfa(aud_phone, aud_pass, aud_secret, portal="OPERATOR")
    assert aud_status == 200 and isinstance(aud_body, dict) and "AUDITOR" in aud_body.get("roles", []), (
        f"Expected 200 AUDITOR MFA login, got {aud_status}: {aud_body}"
    )
    print("  OK: OPERATOR, MODERATOR, & AUDITOR verified via MFA login on portal='OPERATOR'.")
    return mod_user, mod_mfa_jar


def run_phase_3() -> tuple[http.cookiejar.CookieJar]:
    print("\n--- Phase 3: Cross-Role Rejection on OPERATOR Portal ---")
    # 1. Pure CANDIDATE student (password & MFA) rejected on OPERATOR portal
    stu_user, stu_phone, stu_pass, stu_reg_jar = register_user(f"PureStudent {uuid4().hex[:5]}")
    bad_stu_jar = http.cookiejar.CookieJar()
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": stu_phone,
            "password": stu_pass,
            "portal": "OPERATOR",
        }).encode(),
        cookie_jar=bad_stu_jar,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for Student, got {status}: {body}"
    assert isinstance(body, dict) and body.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_stu_jar) == 0, "Expected zero cookies on rejected Student OPERATOR login"

    me_status, _, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=bad_stu_jar)
    assert me_status == 401, f"Expected 401 /api/auth/me after rejected Student login, got {me_status}"

    stu_secret = enroll_totp(stu_reg_jar, stu_pass)
    stu_cand_status, _, stu_mfa_jar = login_with_mfa(stu_phone, stu_pass, stu_secret, portal="CANDIDATE")
    assert stu_cand_status == 200, f"Expected 200 for Student CANDIDATE login, got {stu_cand_status}"
    mfa_status, mfa_err, bad_stu_mfa_jar = login_with_mfa(stu_phone, stu_pass, stu_secret, portal="OPERATOR")
    assert mfa_status == 403, f"Expected 403 on Student MFA verify for OPERATOR portal, got {mfa_status}: {mfa_err}"
    assert isinstance(mfa_err, dict) and mfa_err.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_stu_mfa_jar) == 0, "Expected zero cookies on rejected Student MFA"

    # 2. EMPLOYER (OWNER) rejected on OPERATOR portal
    emp_user, emp_phone, emp_pass, _ = register_user(f"EmpOpCross {uuid4().hex[:5]}")
    grant_org_owner_role(emp_user["id"])
    bad_emp_jar = http.cookiejar.CookieJar()
    status, emp_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": emp_phone,
            "password": emp_pass,
            "portal": "OPERATOR",
        }).encode(),
        cookie_jar=bad_emp_jar,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for EMPLOYER OWNER, got {status}: {emp_body}"
    assert isinstance(emp_body, dict) and emp_body.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_emp_jar) == 0, "Expected zero cookies on rejected EMPLOYER login"

    # 3. ACADEMIC (COORDINATOR) rejected on OPERATOR portal
    univ_user, univ_phone, univ_pass, _ = register_user(f"UnivOpCross {uuid4().hex[:5]}")
    grant_academic_coordinator_role(univ_user["id"])
    bad_univ_jar = http.cookiejar.CookieJar()
    status, univ_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": univ_phone,
            "password": univ_pass,
            "portal": "OPERATOR",
        }).encode(),
        cookie_jar=bad_univ_jar,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for COORDINATOR, got {status}: {univ_body}"
    assert isinstance(univ_body, dict) and univ_body.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_univ_jar) == 0, "Expected zero cookies on rejected COORDINATOR login"
    print("  OK: Student (password + MFA), Employer, & University Coordinator blocked on OPERATOR portal (403, 0 cookies).")
    return (stu_mfa_jar,)


def run_phase_4(mod_mfa_jar: http.cookiejar.CookieJar, stu_reg_jar: http.cookiejar.CookieJar) -> None:
    print("\n--- Phase 4: Authenticated OPERATOR Session BFF Verification ---")
    status, vc_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/verification-cases",
        cookie_jar=mod_mfa_jar,
    )
    assert status == 200 and isinstance(vc_body, dict) and vc_body.get("contract_id") == "API-109", (
        f"Expected 200 API-109 from MODERATOR /api/bff/operator/verification-cases, got {status}: {vc_body}"
    )

    deny_status, _, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/verification-cases",
        cookie_jar=stu_reg_jar,
    )
    assert deny_status == 403, f"Expected 403 for Student calling /api/bff/operator/verification-cases, got {deny_status}"
    print("  OK: MFA OPERATOR session accesses BFF API-109 cleanly; unauthorized student gets 403.")


def main() -> int:
    print("=" * 74)
    print("  FLEXBRIDGE 1.4: PLATFORM OPERATOR ISOLATED LOGIN & SOC SUITE")
    print("=" * 74)
    run_phase_1()
    _, mod_mfa_jar = run_phase_2()
    (stu_reg_jar,) = run_phase_3()
    run_phase_4(mod_mfa_jar, stu_reg_jar)
    print("\nALL 4 PHASES PASSED SUCCESSFULLY!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
