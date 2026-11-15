#!/usr/bin/env python3
"""FlexBridge 1.4 University / OTM Isolated Login & Appointment Onboarding Suite.

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: SSR HTML isolation on /universitet/kirish, /universitet/royxatdan-otish, /university, /kirish, and /.
Phase 2: University (COORDINATOR) non-MFA and MFA-enabled login on portal="ACADEMIC" -> HTTP 200 + session cookie.
Phase 3: Cross-role portal isolation (pure CANDIDATE student, EMPLOYER OWNER, and PLATFORM OPERATOR rejected with
         403 ROLE_PORTAL_MISMATCH & NO cookie on password login and /api/auth/mfa/verify).
Phase 4: End-to-end Institution STAFF_TEACHER Appointment onboarding (API-096 -> Moderator approve ->
         GET /api/bff/university/appointments -> POST /api/bff/university/appointments/[id]/consent ->
         refreshed TEACHER role -> MFA login with portal="ACADEMIC").

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
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
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


def insert_clean_pdf(owner_user_id: str, filename: str) -> str:
    file_id = str(uuid4())
    now_ts = datetime.now(timezone.utc)
    sha = uuid4().hex + uuid4().hex
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.files (
                    id, created_at, updated_at, owner_user_id, storage_key, filename, mime_type, byte_size, sha256,
                    scan_status, scanned_at, retention_class, storage_bucket, storage_version_id, storage_etag, object_version
                ) VALUES (
                    :fid, :ts, :ts, :uid, :sk, :fname, 'application/pdf', 2048, :sha,
                    'CLEAN', :ts, 'VERIFICATION_EVIDENCE', 'flexbridge-private', 'v1', :etag, 'v1'
                )
                """
            ),
            {
                "fid": file_id,
                "ts": now_ts,
                "uid": owner_user_id,
                "sk": f"private/institutions/{file_id}.pdf",
                "fname": filename,
                "sha": sha,
                "etag": f"etag-{file_id[:8]}",
            },
        )
    return file_id


def seed_verified_institution_coordinator(user_id: str) -> tuple[str, str, str, str]:
    suffix = uuid4().hex[:6].upper()
    inst_id = str(uuid4())
    agr_id = str(uuid4())
    appt_id = str(uuid4())
    mem_id = str(uuid4())
    grant_id = str(uuid4())
    reg_code = f"OTM-{suffix}"
    agr_file_id = insert_clean_pdf(user_id, f"agreement_{suffix}.pdf")
    appt_file_id = insert_clean_pdf(user_id, f"coordinator_appt_{suffix}.pdf")

    now_ts = datetime.now(timezone.utc)
    today_tashkent = now_ts.astimezone(TASHKENT_TZ).date()
    valid_from = today_tashkent - timedelta(days=1)
    valid_to = today_tashkent + timedelta(days=365)

    with engine.begin() as conn:
        coord_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE scope_kind = 'INSTITUTION' AND code = 'COORDINATOR' LIMIT 1")
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                VALUES (:id, :ts, :ts, :code, :name, 'Tashkent', 'VERIFIED')
                """
            ),
            {"id": inst_id, "ts": now_ts, "code": reg_code, "name": f"UnivIso {suffix} Institute"},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institution_agreements (
                    id, created_at, updated_at, institution_id, version, status, valid_from, valid_to, purposes, signed_file_id
                ) VALUES (
                    :id, :ts, :ts, :iid, 1, 'ACTIVE', :vfrom, :vto, CAST(:purposes AS jsonb), :fid
                )
                """
            ),
            {
                "id": agr_id,
                "ts": now_ts,
                "iid": inst_id,
                "vfrom": valid_from,
                "vto": valid_to,
                "purposes": json.dumps(["ACADEMIC_VIEW"]),
                "fid": agr_file_id,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institution_appointments (
                    id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, valid_to, accepted_at
                ) VALUES (
                    :id, :ts, :ts, :iid, :uid, :fid, 'ACTIVE', :vfrom, :vto, :ts
                )
                """
            ),
            {
                "id": appt_id,
                "ts": now_ts,
                "iid": inst_id,
                "uid": user_id,
                "fid": appt_file_id,
                "vfrom": valid_from,
                "vto": valid_to,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institution_memberships (
                    id, created_at, updated_at, institution_id, user_id, status, accepted_at
                ) VALUES (
                    :id, :ts, :ts, :iid, :uid, 'ACTIVE', :ts
                )
                """
            ),
            {"id": mem_id, "ts": now_ts, "iid": inst_id, "uid": user_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institution_role_grants (
                    id, created_at, updated_at, membership_id, role_id, appointment_id
                ) VALUES (
                    :id, :ts, :ts, :mid, :rid, :aid
                )
                """
            ),
            {"id": grant_id, "ts": now_ts, "mid": mem_id, "rid": coord_role_id, "aid": appt_id},
        )
    return inst_id, reg_code, agr_id, agr_file_id


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
                "lname": f"UnivCross Corp {suffix}",
                "pname": f"UnivCross {suffix}",
                "tax": f"TAX_UC_{suffix}",
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


def backend_mfa_token(phone: str, password: str, totp_secret: str) -> str:
    status, chal_body, _ = make_request(
        f"{BACKEND_URL}/api/v1/auth/login",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"channel": "PHONE", "destination": phone, "password": password}).encode(),
    )
    assert status == 202 and isinstance(chal_body, dict) and chal_body.get("mfa_ticket"), (
        f"Expected backend 202 MFA challenge, got {status}: {chal_body}"
    )
    status, ver_body, _ = make_request(
        f"{BACKEND_URL}/api/v1/auth/mfa/verify",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"mfa_ticket": chal_body["mfa_ticket"], "code": generate_totp_code(totp_secret)}).encode(),
    )
    assert status == 200 and isinstance(ver_body, dict) and ver_body.get("access_token"), (
        f"Expected backend 200 access_token, got {status}: {ver_body}"
    )
    return str(ver_body["access_token"])


def run_phase_1() -> None:
    print("\n--- Phase 1: University / OTM SSR HTML Isolation Checks ---")
    for path in ("/universitet/kirish", "/universitet/royxatdan-otish", "/university"):
        status, html, _ = make_request(f"{FRONTEND_URL}{path}")
        assert status == 200, f"Expected 200 for {path}, got {status}"
        assert isinstance(html, str) and len(html) > 500, f"Expected HTML on {path}"
        assert 'href="/nomzod"' not in html, f"Student link leaked into university SSR on {path}"
        assert 'href="/talaba/kirish"' not in html, f"Student login leaked into university SSR on {path}"
        assert 'href="/employer"' not in html, f"Employer link leaked into university SSR on {path}"
        assert 'href="/korxona/kirish"' not in html, f"Employer login leaked into university SSR on {path}"
        assert 'href="/operator"' not in html, f"Operator link leaked into university SSR on {path}"
        assert "Verified Skill" not in html, f"Forbidden Skill Badge leaked on {path}"
        assert "Match Coach" not in html, f"Forbidden Match Coach leaked on {path}"
        print(f"  OK: {path} SSR clean ({len(html)} bytes, 0 non-university portal links).")

    status, kirish_html, _ = make_request(f"{FRONTEND_URL}/kirish")
    assert status == 200 and isinstance(kirish_html, str)
    assert "/universitet/kirish" in kirish_html, "Expected /universitet/kirish shortcut inside /kirish SSR"

    status, home_html, _ = make_request(f"{FRONTEND_URL}/")
    assert status == 200 and isinstance(home_html, str)
    assert "/universitet/kirish" in home_html, "Expected /universitet/kirish entry inside / SSR"
    assert "/university" in home_html, "Expected /university entry inside / SSR"
    print("  OK: /kirish and / expose direct /universitet/kirish entry links.")


def run_phase_2() -> tuple[dict[str, Any], str, str, str, str, str, str]:
    print("\n--- Phase 2: University (COORDINATOR) Login & MFA Session Verification ---")
    coord_user, coord_phone, coord_pass, coord_reg_jar = register_user(f"UnivCoord {uuid4().hex[:5]}")
    inst_id, reg_code, agr_id, _ = seed_verified_institution_coordinator(coord_user["id"])

    # Non-MFA password login on ACADEMIC portal
    coord_jar = http.cookiejar.CookieJar()
    status, login_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": coord_phone,
            "password": coord_pass,
            "portal": "ACADEMIC",
        }).encode(),
        cookie_jar=coord_jar,
    )
    assert status == 200, f"Expected 200 on ACADEMIC login, got {status}: {login_body}"
    assert isinstance(login_body, dict) and "COORDINATOR" in login_body.get("roles", [])
    assert len(coord_jar) >= 1, "Expected session cookie on ACADEMIC login"

    me_status, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=coord_jar)
    assert me_status == 200 and isinstance(me_body, dict) and "COORDINATOR" in (me_body.get("user") or {}).get("roles", []), (
        f"Expected COORDINATOR in /api/auth/me user.roles: {me_body}"
    )

    # Enroll TOTP and confirm MFA login on ACADEMIC portal
    coord_secret = enroll_totp(coord_reg_jar, coord_pass)
    mfa_status, mfa_body, _ = login_with_mfa(coord_phone, coord_pass, coord_secret, portal="ACADEMIC")
    assert mfa_status == 200 and isinstance(mfa_body, dict) and "COORDINATOR" in mfa_body.get("roles", []), (
        f"Expected 200 COORDINATOR on ACADEMIC MFA login, got {mfa_status}: {mfa_body}"
    )
    print(f"  OK: INSTITUTION COORDINATOR verified for non-MFA and MFA login on ACADEMIC portal (inst_id={inst_id}).")
    return coord_user, coord_phone, coord_pass, coord_secret, inst_id, reg_code, agr_id


def run_phase_3(granter_id: str) -> None:
    print("\n--- Phase 3: Cross-Role Rejection on ACADEMIC Portal ---")
    # 1. Pure CANDIDATE student (password & MFA) rejected on ACADEMIC portal
    stu_user, stu_phone, stu_pass, stu_reg_jar = register_user(f"PureStudent {uuid4().hex[:5]}")
    bad_stu_jar = http.cookiejar.CookieJar()
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": stu_phone,
            "password": stu_pass,
            "portal": "ACADEMIC",
        }).encode(),
        cookie_jar=bad_stu_jar,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for Student, got {status}: {body}"
    assert isinstance(body, dict) and body.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_stu_jar) == 0, "Expected zero cookies set on rejected Student ACADEMIC login"

    me_status, _, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=bad_stu_jar)
    assert me_status == 401, f"Expected 401 /api/auth/me after rejected Student login, got {me_status}"

    stu_secret = enroll_totp(stu_reg_jar, stu_pass)
    mfa_status, mfa_err, bad_stu_mfa_jar = login_with_mfa(stu_phone, stu_pass, stu_secret, portal="ACADEMIC")
    assert mfa_status == 403, f"Expected 403 on Student MFA verify for ACADEMIC portal, got {mfa_status}: {mfa_err}"
    assert isinstance(mfa_err, dict) and mfa_err.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_stu_mfa_jar) == 0, "Expected zero cookies on rejected Student MFA"

    # 2. EMPLOYER (OWNER) rejected on ACADEMIC portal
    emp_user, emp_phone, emp_pass, _ = register_user(f"EmpCross {uuid4().hex[:5]}")
    grant_org_owner_role(emp_user["id"])
    bad_emp_jar = http.cookiejar.CookieJar()
    status, emp_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": emp_phone,
            "password": emp_pass,
            "portal": "ACADEMIC",
        }).encode(),
        cookie_jar=bad_emp_jar,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for EMPLOYER OWNER, got {status}: {emp_body}"
    assert isinstance(emp_body, dict) and emp_body.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_emp_jar) == 0, "Expected zero cookies on rejected EMPLOYER login"

    # 3. PLATFORM OPERATOR rejected on ACADEMIC portal
    op_user, op_phone, op_pass, _ = register_user(f"OpUser {uuid4().hex[:5]}")
    grant_platform_role(op_user["id"], granter_id, "OPERATOR")
    bad_op_jar = http.cookiejar.CookieJar()
    status, op_body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "destination": op_phone,
            "password": op_pass,
            "portal": "ACADEMIC",
        }).encode(),
        cookie_jar=bad_op_jar,
    )
    assert status == 403, f"Expected 403 ROLE_PORTAL_MISMATCH for OPERATOR, got {status}: {op_body}"
    assert isinstance(op_body, dict) and op_body.get("error") == "ROLE_PORTAL_MISMATCH"
    assert len(bad_op_jar) == 0, "Expected zero cookies on rejected OPERATOR login"
    print("  OK: Pure Student (password + MFA), Employer, & Operator blocked on ACADEMIC portal (403, 0 cookies).")


def run_phase_4(
    coord_user: dict[str, Any],
    coord_phone: str,
    coord_pass: str,
    coord_secret: str,
    reg_code: str,
    agr_id: str,
) -> None:
    print("\n--- Phase 4: Institution Appointment Consent via BFF & ACADEMIC Login ---")
    # 1. Teacher registers fresh account (verified phone contact automatically created)
    teacher_user, teacher_phone, teacher_pass, teacher_reg_jar = register_user(f"NamedTeacher {uuid4().hex[:5]}")

    # 2. Seed an independent Moderator and obtain MFA tokens for Moderator & Coordinator
    mod_user, mod_phone, mod_pass, mod_reg_jar = register_user(f"InstMod {uuid4().hex[:5]}")
    grant_platform_role(mod_user["id"], coord_user["id"], "MODERATOR")
    mod_secret = enroll_totp(mod_reg_jar, mod_pass)

    coord_token = backend_mfa_token(coord_phone, coord_pass, coord_secret)
    mod_token = backend_mfa_token(mod_phone, mod_pass, mod_secret)

    # 3. Coordinator reads own verified contact via GET /api/v1/me/contacts & uploads CLEAN PDF appointment order
    status, contacts_body, _ = make_request(
        f"{BACKEND_URL}/api/v1/me/contacts",
        headers={"Authorization": f"Bearer {coord_token}"},
    )
    assert status == 200 and isinstance(contacts_body, dict) and contacts_body.get("items"), (
        f"Expected Coordinator contacts list, got {status}: {contacts_body}"
    )
    coord_contact_id = contacts_body["items"][0]["id"]
    doc_file_id = insert_clean_pdf(coord_user["id"], "teacher_appointment_order.pdf")
    today_tashkent = datetime.now(TASHKENT_TZ).date()

    # 4. Coordinator submits STAFF_TEACHER appointment (API-096)
    status, submit_body, _ = make_request(
        f"{BACKEND_URL}/api/v1/institution-appointments",
        method="POST",
        headers={
            "Authorization": f"Bearer {coord_token}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"appt-{uuid4().hex}",
        },
        data=json.dumps({
            "registry_code": reg_code,
            "document_file_id": doc_file_id,
            "contact_id": coord_contact_id,
            "valid_from": today_tashkent.isoformat(),
            "valid_to": (today_tashkent + timedelta(days=180)).isoformat(),
            "legal_basis": "Kafedra buyrugi asosida amaliyot rahbari etib tayinlandi.",
            "file_ids": [doc_file_id],
            "evidence_note": "OTM dekanati tasdiqlagan rasmiy kafedra tayinlov buyrugi ilova qilindi.",
            "agreement_id": agr_id,
            "target_channel": "PHONE",
            "target_destination": teacher_phone,
        }).encode(),
    )
    assert status == 202 and isinstance(submit_body, dict), (
        f"Expected 202 appointment submit, got {status}: {submit_body}"
    )
    assert submit_body.get("contract_id") == "API-096"
    appointment_id = submit_body["id"]
    case_id = submit_body["case_id"]

    # 5. Moderator claims & approves the institution appointment verification case
    status, claim_body, _ = make_request(
        f"{BACKEND_URL}/api/v1/operator/verification-cases/{case_id}/claim",
        method="POST",
        headers={"Authorization": f"Bearer {mod_token}"},
    )
    assert status == 200, f"Moderator claim failed ({status}): {claim_body}"

    status, decide_body, _ = make_request(
        f"{BACKEND_URL}/api/v1/operator/verification-cases/{case_id}/decide",
        method="POST",
        headers={"Authorization": f"Bearer {mod_token}", "Content-Type": "application/json"},
        data=json.dumps({
            "expected_revision": 1,
            "decision": "APPROVE",
            "reason": "OTM kafedra oqituvchisi tayinlov buyrugi va shartnoma tekshirildi.",
        }).encode(),
    )
    assert status == 200 and isinstance(decide_body, dict), f"Moderator approve failed ({status}): {decide_body}"
    assert decide_body.get("status") == "APPROVED_PENDING_ACCEPT"

    # 6. Teacher checks inbox + contacts via Next.js BFF: GET /api/bff/university/appointments
    status, inbox_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/appointments",
        cookie_jar=teacher_reg_jar,
    )
    assert status == 200 and isinstance(inbox_body, dict), f"BFF inbox failed ({status}): {inbox_body}"
    items = inbox_body.get("items") or []
    contacts = inbox_body.get("contacts") or []
    matching = [item for item in items if item.get("id") == appointment_id]
    assert matching, f"Expected appointment {appointment_id} in teacher BFF inbox: {inbox_body}"
    assert contacts, f"Expected verified contact in teacher BFF response: {inbox_body}"
    appt_row = matching[0]
    assert appt_row.get("case_status") == "APPROVED"
    teacher_contact_id = contacts[0]["id"]

    # 7. Teacher accepts consent via Next.js BFF: POST /api/bff/university/appointments/[id]/consent
    status, consent_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/appointments/{appointment_id}/consent",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "expected_revision": appt_row["current_revision"],
            "decision": "ACCEPT",
            "contact_id": teacher_contact_id,
        }).encode(),
        cookie_jar=teacher_reg_jar,
    )
    assert status == 200 and isinstance(consent_body, dict), f"BFF consent failed ({status}): {consent_body}"
    assert consent_body.get("ok") is True and (consent_body.get("appointment") or {}).get("status") == "ACTIVE", (
        f"Expected ACTIVE appointment after consent: {consent_body}"
    )
    assert "TEACHER" in consent_body.get("roles", []), (
        f"Expected refreshed session response to include TEACHER role: {consent_body}"
    )

    me_status, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=teacher_reg_jar)
    assert me_status == 200 and isinstance(me_body, dict) and "TEACHER" in (me_body.get("user") or {}).get("roles", []), (
        f"Expected /api/auth/me cookie session to include TEACHER role after consent: {me_body}"
    )

    # 8. Teacher enrolls TOTP & logs directly into ACADEMIC portal with MFA -> HTTP 200
    teacher_secret = enroll_totp(teacher_reg_jar, teacher_pass)
    acad_status, acad_body, acad_jar = login_with_mfa(
        teacher_phone, teacher_pass, teacher_secret, portal="ACADEMIC"
    )
    assert acad_status == 200 and isinstance(acad_body, dict), (
        f"Expected 200 ACADEMIC portal login for accepted TEACHER, got {acad_status}: {acad_body}"
    )
    assert "TEACHER" in acad_body.get("roles", [])
    assert acad_body.get("user_id") == teacher_user["id"]
    assert len(acad_jar) >= 1
    print("  OK: API-096 -> Moderator approve -> BFF consent -> role refresh -> ACADEMIC MFA login passed.")


def main() -> int:
    print("=" * 74)
    print("  FLEXBRIDGE 1.4: UNIVERSITY / OTM ISOLATED LOGIN & APPOINTMENT SUITE")
    print("=" * 74)
    run_phase_1()
    coord_user, coord_phone, coord_pass, coord_secret, _, reg_code, agr_id = run_phase_2()
    run_phase_3(coord_user["id"])
    run_phase_4(coord_user, coord_phone, coord_pass, coord_secret, reg_code, agr_id)
    print("\nALL 4 PHASES PASSED SUCCESSFULLY!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
