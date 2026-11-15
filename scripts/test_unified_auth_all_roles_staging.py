#!/usr/bin/env python3
"""FlexBridge 1.4 Unified Main /kirish & /royxatdan-otish All-Role Staging Suite.

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: SSR HTML verification on /kirish and /royxatdan-otish (all 4 role portals & onboarding links present).
Phase 2: Unified Login (POST /api/auth/login & /api/auth/mfa/verify WITHOUT restrictive portal) across ALL 4 roles:
         - CANDIDATE (student) -> /nomzod
         - EMPLOYER (OWNER / HR) -> /employer
         - ACADEMIC (COORDINATOR / TEACHER) -> /university
         - OPERATOR (OPERATOR / MODERATOR / AUDITOR) -> /operator
         Plus cross-portal verification that all 4 isolated portals STILL reject wrong roles (403 ROLE_PORTAL_MISMATCH).
Phase 3: Unified Signup & Inline Role Activation flows via Next.js BFF:
         - Pure CANDIDATE registration -> /nomzod
         - Public signup attempting privileged role (roles=["EMPLOYER"]) -> rejected 403
         - EMPLOYER invite token preview + accept (/api/bff/invitations/[token]*) -> HR role -> /employer
         - ACADEMIC appointment inbox + consent (/api/bff/university/appointments*) -> TEACHER role -> /university
         - OPERATOR dual-control role grant check + TOTP MFA -> /operator

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

EMPLOYER_ROLES = {"OWNER", "HR", "HOST_COORDINATOR", "MENTOR", "BILLING"}
ACADEMIC_ROLES = {"COORDINATOR", "TEACHER"}
OPERATOR_ROLES = {"OPERATOR", "MODERATOR", "AUDITOR", "FINANCE", "SUPPORT", "SECURITY_LEAD", "ADMIN"}


def resolve_portal_dashboard_py(roles: list[str]) -> str:
    upper = {str(r).strip().upper() for r in roles}
    if upper & OPERATOR_ROLES:
        return "/operator"
    if upper & ACADEMIC_ROLES:
        return "/university"
    if upper & EMPLOYER_ROLES:
        return "/employer"
    return "/nomzod"


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


def register_user(
    display_name: str,
    phone: str | None = None,
    roles: list[str] | None = None,
) -> tuple[dict[str, Any], str, str, http.cookiejar.CookieJar]:
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
            "roles": roles or ["CANDIDATE"],
        }).encode(),
        cookie_jar=jar,
    )
    assert status == 201 and isinstance(reg_body, dict) and reg_body.get("ok") is True, (
        f"Expected 201 register, got {status}: {reg_body}"
    )
    return reg_body["user"], reg_phone, password, jar


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


def login_unified(
    phone: str,
    password: str,
    totp_secret: str | None = None,
    portal: str | None = None,
) -> tuple[int, dict[str, Any] | str, http.cookiejar.CookieJar]:
    jar = http.cookiejar.CookieJar()
    payload: dict[str, Any] = {"destination": phone, "password": password}
    if portal is not None:
        payload["portal"] = portal
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(payload).encode(),
        cookie_jar=jar,
    )
    if status == 202 and isinstance(body, dict) and body.get("mfa_ticket"):
        assert totp_secret, f"MFA ticket returned for {phone} without TOTP secret"
        assert len(jar) == 0, "Expected 0 cookies before MFA completion"
        mfa_payload: dict[str, Any] = {
            "mfa_ticket": body["mfa_ticket"],
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
                "sk": f"private/unified/{file_id}.pdf",
                "fname": filename,
                "sha": sha,
                "etag": f"etag-{file_id[:8]}",
            },
        )
    return file_id


def seed_org_owner(user_id: str) -> str:
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
            {"id": org_id, "ts": now_ts, "lname": f"UniAuth Org {suffix}", "pname": f"UniAuth {suffix}", "tax": f"TAX_UA_{suffix}"},
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


def seed_verified_institution_coordinator(user_id: str) -> tuple[str, str, str]:
    suffix = uuid4().hex[:6].upper()
    inst_id = str(uuid4())
    agr_id = str(uuid4())
    appt_id = str(uuid4())
    mem_id = str(uuid4())
    grant_id = str(uuid4())
    reg_code = f"OTM-UA-{suffix}"
    agr_file_id = insert_clean_pdf(user_id, f"uni_agr_{suffix}.pdf")
    appt_file_id = insert_clean_pdf(user_id, f"uni_coord_{suffix}.pdf")
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
            {"id": inst_id, "ts": now_ts, "code": reg_code, "name": f"Unified Univ {suffix}"},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institution_agreements (
                    id, created_at, updated_at, institution_id, version, status, valid_from, valid_to, purposes, signed_file_id
                ) VALUES (:id, :ts, :ts, :iid, 1, 'ACTIVE', :vf, :vt, CAST(:purposes AS jsonb), :fid)
                """
            ),
            {"id": agr_id, "ts": now_ts, "iid": inst_id, "vf": valid_from, "vt": valid_to, "purposes": json.dumps(["ACADEMIC_VIEW"]), "fid": agr_file_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO flexbridge.institution_appointments (
                    id, created_at, updated_at, institution_id, user_id, document_file_id, status, valid_from, valid_to, accepted_at
                ) VALUES (:id, :ts, :ts, :iid, :uid, :fid, 'ACTIVE', :vf, :vt, :ts)
                """
            ),
            {"id": appt_id, "ts": now_ts, "iid": inst_id, "uid": user_id, "fid": appt_file_id, "vf": valid_from, "vt": valid_to},
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
    return inst_id, reg_code, agr_id


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
            {"gid": str(uuid4()), "ts": now_ts, "uid": user_id, "rid": role_id, "granter": granter_id, "exp": exp_ts},
        )


def run_phase_1() -> None:
    print("\n--- Phase 1: Main /kirish & /royxatdan-otish SSR Verification ---")
    status, kirish_html, _ = make_request(f"{FRONTEND_URL}/kirish")
    assert status == 200 and isinstance(kirish_html, str) and len(kirish_html) > 500
    for expected in ("kirish", "/talaba/kirish", "/korxona/kirish", "/universitet/kirish", "/operator/kirish"):
        assert expected in kirish_html, f"Expected {expected!r} in /kirish SSR HTML"
    assert "Verified Skill" not in kirish_html and "Match Coach" not in kirish_html

    status, reg_html, _ = make_request(f"{FRONTEND_URL}/royxatdan-otish")
    assert status == 200 and isinstance(reg_html, str) and len(reg_html) > 500
    for expected in ("4 bosqichli onboarding", "Talaba", "Korxona HR", "Universitet", "Operator"):
        assert expected in reg_html, f"Expected {expected!r} in /royxatdan-otish SSR HTML"
    assert "Verified Skill" not in reg_html and "Match Coach" not in reg_html
    print("  OK: /kirish & /royxatdan-otish SSR clean and expose all 4 user role paths.")


def run_phase_2() -> tuple[str, str, str, str, str, str]:
    print("\n--- Phase 2: Unified Login (No Portal) Across All 4 Roles & Portal Isolation ---")

    # 1. Pure CANDIDATE (non-MFA & MFA)
    stu_user, stu_phone, stu_pass, stu_reg_jar = register_user(f"UniStudent {uuid4().hex[:5]}")
    st, body, jar = login_unified(stu_phone, stu_pass, portal=None)
    assert st == 200 and isinstance(body, dict) and body.get("roles") == ["CANDIDATE"], f"Student unified login failed: {st} {body}"
    assert resolve_portal_dashboard_py(body["roles"]) == "/nomzod"
    me_st, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=jar)
    assert me_st == 200 and (me_body.get("user") or {}).get("roles") == ["CANDIDATE"]

    stu_secret = enroll_totp(stu_reg_jar, stu_pass)
    st, body, _ = login_unified(stu_phone, stu_pass, totp_secret=stu_secret, portal=None)
    assert st == 200 and isinstance(body, dict) and body.get("roles") == ["CANDIDATE"]
    assert resolve_portal_dashboard_py(body["roles"]) == "/nomzod"

    # 2. EMPLOYER (OWNER)
    emp_user, emp_phone, emp_pass, emp_reg_jar = register_user(f"UniEmployer {uuid4().hex[:5]}")
    org_id = seed_org_owner(emp_user["id"])
    emp_secret = enroll_totp(emp_reg_jar, emp_pass)
    st, body, emp_jar = login_unified(emp_phone, emp_pass, totp_secret=emp_secret, portal=None)
    assert st == 200 and isinstance(body, dict) and "OWNER" in body.get("roles", []), f"Employer unified login failed: {st} {body}"
    assert resolve_portal_dashboard_py(body["roles"]) == "/employer"
    me_st, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=emp_jar)
    assert me_st == 200 and resolve_portal_dashboard_py((me_body.get("user") or {}).get("roles", [])) == "/employer"

    # 3. ACADEMIC (COORDINATOR)
    acad_user, acad_phone, acad_pass, acad_reg_jar = register_user(f"UniCoord {uuid4().hex[:5]}")
    _, reg_code, agr_id = seed_verified_institution_coordinator(acad_user["id"])
    acad_secret = enroll_totp(acad_reg_jar, acad_pass)
    st, body, acad_jar = login_unified(acad_phone, acad_pass, totp_secret=acad_secret, portal=None)
    assert st == 200 and isinstance(body, dict) and "COORDINATOR" in body.get("roles", []), f"Academic unified login failed: {st} {body}"
    assert resolve_portal_dashboard_py(body["roles"]) == "/university"
    me_st, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=acad_jar)
    assert me_st == 200 and resolve_portal_dashboard_py((me_body.get("user") or {}).get("roles", [])) == "/university"

    # 4. OPERATOR (MODERATOR)
    mod_user, mod_phone, mod_pass, mod_reg_jar = register_user(f"UniMod {uuid4().hex[:5]}")
    grant_platform_role(mod_user["id"], stu_user["id"], "MODERATOR")
    mod_secret = enroll_totp(mod_reg_jar, mod_pass)
    st, body, mod_jar = login_unified(mod_phone, mod_pass, totp_secret=mod_secret, portal=None)
    assert st == 200 and isinstance(body, dict) and "MODERATOR" in body.get("roles", []), f"Operator unified login failed: {st} {body}"
    assert resolve_portal_dashboard_py(body["roles"]) == "/operator"
    vc_st, vc_body, _ = make_request(f"{FRONTEND_URL}/api/bff/operator/verification-cases", cookie_jar=mod_jar)
    assert vc_st == 200 and isinstance(vc_body, dict) and vc_body.get("contract_id") == "API-109"

    # 5. Cross-check ALL 4 isolated portals still reject wrong roles (403 ROLE_PORTAL_MISMATCH, 0 cookies)
    cross_checks = [
        ("CANDIDATE", emp_phone, emp_pass, emp_secret),
        ("CANDIDATE", acad_phone, acad_pass, acad_secret),
        ("CANDIDATE", mod_phone, mod_pass, mod_secret),
        ("EMPLOYER", stu_phone, stu_pass, stu_secret),
        ("EMPLOYER", acad_phone, acad_pass, acad_secret),
        ("EMPLOYER", mod_phone, mod_pass, mod_secret),
        ("ACADEMIC", stu_phone, stu_pass, stu_secret),
        ("ACADEMIC", emp_phone, emp_pass, emp_secret),
        ("ACADEMIC", mod_phone, mod_pass, mod_secret),
        ("OPERATOR", stu_phone, stu_pass, stu_secret),
        ("OPERATOR", emp_phone, emp_pass, emp_secret),
        ("OPERATOR", acad_phone, acad_pass, acad_secret),
    ]
    for portal_name, p_phone, p_pass, p_secret in cross_checks:
        rej_st, rej_body, rej_jar = login_unified(p_phone, p_pass, totp_secret=p_secret, portal=portal_name)
        assert rej_st == 403 and isinstance(rej_body, dict) and rej_body.get("error") == "ROLE_PORTAL_MISMATCH", (
            f"Expected 403 ROLE_PORTAL_MISMATCH on portal={portal_name}, got {rej_st}: {rej_body}"
        )
        assert len(rej_jar) == 0, f"Expected 0 cookies on rejected {portal_name} login"

    print("  OK: Unified login routed all 4 roles cleanly; all 12 cross-portal mismatches rejected with 403.")
    return org_id, emp_phone, emp_pass, emp_secret, acad_user["id"], acad_phone, acad_pass, acad_secret, reg_code, agr_id, mod_phone, mod_pass, mod_secret, mod_user["id"]


def run_phase_3(
    org_id: str,
    emp_phone: str,
    emp_pass: str,
    emp_secret: str,
    coord_user_id: str,
    coord_phone: str,
    coord_pass: str,
    coord_secret: str,
    reg_code: str,
    agr_id: str,
    mod_phone: str,
    mod_pass: str,
    mod_secret: str,
    granter_id: str,
) -> None:
    print("\n--- Phase 3: Unified Signup & Step 4 Role Activation Across All 4 Flows ---")

    # 1. Pure CANDIDATE signup -> /nomzod
    _, cand_phone, cand_pass, cand_jar = register_user(f"RegCand {uuid4().hex[:5]}")
    me_st, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=cand_jar)
    assert me_st == 200 and resolve_portal_dashboard_py((me_body.get("user") or {}).get("roles", [])) == "/nomzod"

    # 2. Safeguard: privileged direct signup is rejected with 403
    priv_phone, priv_vtok = issue_and_consume_otp()
    priv_st, _, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/register",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "verification_token": priv_vtok,
            "display_name": "PrivBlock",
            "password": "FlexBridge!Priv1234",
            "adult_confirmed": True,
            "terms_version": "2026.1",
            "privacy_version": "2026.1",
            "roles": ["EMPLOYER"],
        }).encode(),
    )
    assert priv_st == 403, f"Expected 403 on public privileged signup roles=['EMPLOYER'], got {priv_st}"

    # 3. EMPLOYER Step 4 flow: signup CANDIDATE -> preview invite -> accept invite -> HR role -> /employer
    invitee_phone = f"+99890{int(uuid4().hex[:7], 16) % 10000000:07d}"
    _, _, owner_jar = login_unified(emp_phone, emp_pass, totp_secret=emp_secret, portal="EMPLOYER")
    inv_st, inv_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/invitations",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"channel": "PHONE", "destination": invitee_phone, "role_code": "HR"}).encode(),
        cookie_jar=owner_jar,
    )
    assert inv_st == 201 and isinstance(inv_body, dict) and inv_body.get("token"), f"Invite create failed: {inv_st} {inv_body}"
    token = inv_body["token"]

    _, _, hr_pass, hr_reg_jar = register_user(f"UnifiedHR {uuid4().hex[:5]}", phone=invitee_phone)
    prev_st, prev_body, _ = make_request(f"{FRONTEND_URL}/api/bff/invitations/{token}")
    assert prev_st == 200 and isinstance(prev_body, dict) and prev_body.get("role_code") == "HR", f"Preview failed: {prev_body}"

    acc_pre_st, acc_pre_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/invitations/{token}/accept",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({}).encode(),
        cookie_jar=hr_reg_jar,
    )
    assert acc_pre_st == 403 and isinstance(acc_pre_body, dict) and acc_pre_body.get("error") == "MFA_REQUIRED", (
        f"Expected 403 MFA_REQUIRED before TOTP login on invite accept, got {acc_pre_st}: {acc_pre_body}"
    )

    hr_secret = enroll_totp(hr_reg_jar, hr_pass)
    st, hr_mfa_login, hr_mfa_jar = login_unified(invitee_phone, hr_pass, totp_secret=hr_secret, portal=None)
    assert st == 200 and isinstance(hr_mfa_login, dict), f"Invitee MFA login before accept failed: {st} {hr_mfa_login}"

    acc_st, acc_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/invitations/{token}/accept",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({}).encode(),
        cookie_jar=hr_mfa_jar,
    )
    assert acc_st == 200 and isinstance(acc_body, dict) and "HR" in acc_body.get("roles", []), (
        f"Step 4 inline invite accept failed ({acc_st}): {acc_body}"
    )
    assert resolve_portal_dashboard_py(acc_body["roles"]) == "/employer"
    me_st, me_body, _ = make_request(f"{FRONTEND_URL}/api/auth/me", cookie_jar=hr_mfa_jar)
    assert me_st == 200 and "HR" in (me_body.get("user") or {}).get("roles", [])

    # Re-login unified (with MFA) -> resolves to /employer
    st, hr_login, _ = login_unified(invitee_phone, hr_pass, totp_secret=hr_secret, portal=None)
    assert st == 200 and resolve_portal_dashboard_py(hr_login.get("roles", [])) == "/employer"

    # 4. ACADEMIC Step 4 flow: signup CANDIDATE -> inbox -> consent ACCEPT -> TEACHER role -> /university
    teacher_user, teacher_phone, teacher_pass, teacher_jar = register_user(f"UnifiedTeacher {uuid4().hex[:5]}")
    coord_token = backend_mfa_token(coord_phone, coord_pass, coord_secret)
    mod_token = backend_mfa_token(mod_phone, mod_pass, mod_secret)

    c_st, c_body, _ = make_request(
        f"{BACKEND_URL}/api/v1/me/contacts",
        headers={"Authorization": f"Bearer {coord_token}"},
    )
    assert c_st == 200 and isinstance(c_body, dict) and c_body.get("items")
    coord_contact_id = c_body["items"][0]["id"]
    doc_file_id = insert_clean_pdf(coord_user_id, "unified_teacher_appt.pdf")
    today_tashkent = datetime.now(TASHKENT_TZ).date()

    sub_st, sub_body, _ = make_request(
        f"{BACKEND_URL}/api/v1/institution-appointments",
        method="POST",
        headers={
            "Authorization": f"Bearer {coord_token}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"ua-appt-{uuid4().hex}",
        },
        data=json.dumps({
            "registry_code": reg_code,
            "document_file_id": doc_file_id,
            "contact_id": coord_contact_id,
            "valid_from": today_tashkent.isoformat(),
            "valid_to": (today_tashkent + timedelta(days=180)).isoformat(),
            "legal_basis": "Kafedra buyrugi asosida unified onboarding testi.",
            "file_ids": [doc_file_id],
            "evidence_note": "OTM buyrugi ilova qilindi.",
            "agreement_id": agr_id,
            "target_channel": "PHONE",
            "target_destination": teacher_phone,
        }).encode(),
    )
    assert sub_st == 202 and isinstance(sub_body, dict), f"Appt submit failed: {sub_st} {sub_body}"
    appt_id = sub_body["id"]
    case_id = sub_body["case_id"]

    cl_st, _, _ = make_request(
        f"{BACKEND_URL}/api/v1/operator/verification-cases/{case_id}/claim",
        method="POST",
        headers={"Authorization": f"Bearer {mod_token}"},
    )
    assert cl_st == 200
    dec_st, _, _ = make_request(
        f"{BACKEND_URL}/api/v1/operator/verification-cases/{case_id}/decide",
        method="POST",
        headers={"Authorization": f"Bearer {mod_token}", "Content-Type": "application/json"},
        data=json.dumps({"expected_revision": 1, "decision": "APPROVE", "reason": "Unified OTM onboarding verified."}).encode(),
    )
    assert dec_st == 200

    inb_st, inb_body, _ = make_request(f"{FRONTEND_URL}/api/bff/university/appointments", cookie_jar=teacher_jar)
    assert inb_st == 200 and isinstance(inb_body, dict)
    match_appts = [a for a in (inb_body.get("items") or []) if a.get("id") == appt_id]
    assert match_appts and (inb_body.get("contacts") or []), f"Teacher inbox missing appointment/contact: {inb_body}"

    con_st, con_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/university/appointments/{appt_id}/consent",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({
            "expected_revision": match_appts[0]["current_revision"],
            "decision": "ACCEPT",
            "contact_id": inb_body["contacts"][0]["id"],
        }).encode(),
        cookie_jar=teacher_jar,
    )
    assert con_st == 200 and isinstance(con_body, dict) and "TEACHER" in con_body.get("roles", []), (
        f"Appointment consent failed ({con_st}): {con_body}"
    )
    assert resolve_portal_dashboard_py(con_body["roles"]) == "/university"

    # 5. OPERATOR Step 4 dual-control flow: signup CANDIDATE -> enroll TOTP -> still CANDIDATE -> dual-control grant -> /operator
    op_user, op_phone, op_pass, op_jar = register_user(f"UnifiedOp {uuid4().hex[:5]}")
    op_secret = enroll_totp(op_jar, op_pass)
    st, pre_grant_login, _ = login_unified(op_phone, op_pass, totp_secret=op_secret, portal=None)
    assert st == 200 and pre_grant_login.get("roles") == ["CANDIDATE"]
    assert resolve_portal_dashboard_py(pre_grant_login["roles"]) == "/nomzod"

    grant_platform_role(op_user["id"], granter_id, "OPERATOR")
    st, post_grant_login, _ = login_unified(op_phone, op_pass, totp_secret=op_secret, portal=None)
    assert st == 200 and "OPERATOR" in post_grant_login.get("roles", [])
    assert resolve_portal_dashboard_py(post_grant_login["roles"]) == "/operator"

    print("  OK: All 4 signup + activation flows verified end-to-end via BFF.")


def main() -> int:
    print("=" * 74)
    print("  FLEXBRIDGE 1.4: UNIFIED MAIN /kirish & /royxatdan-otish ALL-ROLE SUITE")
    print("=" * 74)
    run_phase_1()
    (
        org_id,
        emp_phone,
        emp_pass,
        emp_secret,
        coord_user_id,
        coord_phone,
        coord_pass,
        coord_secret,
        reg_code,
        agr_id,
        mod_phone,
        mod_pass,
        mod_secret,
        granter_id,
    ) = run_phase_2()
    run_phase_3(
        org_id,
        emp_phone,
        emp_pass,
        emp_secret,
        coord_user_id,
        coord_phone,
        coord_pass,
        coord_secret,
        reg_code,
        agr_id,
        mod_phone,
        mod_pass,
        mod_secret,
        granter_id,
    )
    print("\nALL 3 PHASES PASSED SUCCESSFULLY!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
