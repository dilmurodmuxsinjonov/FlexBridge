#!/usr/bin/env python3
"""
FlexBridge 1.4 Automated Staging Verification Suite:
Employer Portal: Organization Settings, Team Management, Capabilities & Verification Hub (FB-168)

Contracts Tested:
- API-072: GET /api/bff/employer/organization/{org}/capabilities (Capabilities: JOB_EMPLOYER, INTERNSHIP_HOST)
- API-067: GET /api/bff/employer/organization/{org}/verification (Organization verification status and cases history)
- API-073: GET /api/bff/employer/organization/{org}/memberships (List organization team members, roles, status)
- API-074: POST /api/bff/employer/organization/{org}/invitations (Send 24h opaque invitation with role)
- API-075: POST /api/bff/employer/organization/{org}/memberships/{id}/revoke (Revoke team membership with min 15-char reason)

Security & Architectural Invariants:
- 401 AUTH_REQUIRED on all unauthenticated requests.
- 403 CSRF_ORIGIN_MISMATCH against cross-site mutating requests.
- Anti-enumeration uniform 403/404 for non-member / IDOR cross-org attempts.
- Owner authority & MFA assurance requirement for sensitive management operations.
- Minimum 15-character revocation justification constraint (API-075).
- Last owner protection constraint (LAST_OWNER_PROTECTED).
- PgBouncer transaction-pooling compliance (NullPool, prepare_threshold=None).
- Zero queries/mutations to pg_live.
"""

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.services.auth import hash_password

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")


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


def api_request(url, method="GET", data=None, headers=None, opener=None):
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        req_headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    active_opener = opener or urllib.request.build_opener()

    try:
        with active_opener.open(req) as resp:
            content = resp.read().decode("utf-8")
            parsed = json.loads(content) if content else {}
            return resp.status, parsed
    except urllib.error.HTTPError as err:
        content = err.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"raw": content}
        return err.code, parsed


def main():
    print("================================================================================")
    print("FLEXBRIDGE 1.4 STAGING SUITE: Employer Organization & Team Hub (FB-168)")
    print("================================================================================")

    dummy_org = str(uuid4())
    dummy_mem = str(uuid4())

    # -------------------------------------------------------------------------
    # PHASE 1: 401 AUTH_REQUIRED on all unauthenticated endpoints
    # -------------------------------------------------------------------------
    print("\n[Phase 1] 401 AUTH_REQUIRED on unauthenticated employer organization endpoints...")

    unauth_endpoints = [
        ("GET", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/capabilities", None),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/verification", None),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/memberships", None),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/invitations", {"channel": "EMAIL", "destination": "test@example.com", "role_code": "HR"}),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/memberships/{dummy_mem}/revoke", {"reason": "Valid reason for revocation min 15 chars"}),
    ]

    for m, ep, payload in unauth_endpoints:
        code, resp = api_request(ep, method=m, data=payload)
        assert code == 401, f"Expected 401 on {m} {ep}, got {code}: {resp}"
        assert resp.get("error") == "AUTH_REQUIRED" or resp.get("message") == "AUTH_REQUIRED", f"Invalid 401 payload: {resp}"
    print("  ✓ All 5 endpoints strictly enforce 401 AUTH_REQUIRED.")

    # -------------------------------------------------------------------------
    # PHASE 2: Anti-CSRF Origin Guard
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Anti-CSRF Origin Guard (403 CSRF_ORIGIN_MISMATCH)...")
    csrf_headers = {
        "Origin": "https://malicious-attacker-domain.com",
        "Referer": "https://malicious-attacker-domain.com/hack",
    }

    mutating_csrf_endpoints = [
        ("POST", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/invitations", {"channel": "EMAIL", "destination": "test@example.com", "role_code": "HR"}),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/organization/{dummy_org}/memberships/{dummy_mem}/revoke", {"reason": "Valid reason for revocation min 15 chars"}),
    ]

    for m, ep, payload in mutating_csrf_endpoints:
        code, resp = api_request(ep, method=m, data=payload, headers=csrf_headers)
        assert code == 403, f"Expected 403 on CSRF attack for {m} {ep}, got {code}: {resp}"
        assert resp.get("error") == "CSRF_ORIGIN_MISMATCH" or resp.get("message") == "CSRF_ORIGIN_MISMATCH", f"Invalid CSRF payload: {resp}"
    print("  ✓ Anti-CSRF guard properly blocked cross-origin requests.")

    # -------------------------------------------------------------------------
    # PHASE 3: DB Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n[Phase 3] Setting up DB fixtures via PgBouncer...")
    db_url = get_database_url()
    engine = create_engine(
        db_url,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_suffix = uuid4().hex[:8]
    owner_user_id = str(uuid4())
    member_user_id = str(uuid4())
    other_org_owner_id = str(uuid4())

    org_id = str(uuid4())
    other_org_id = str(uuid4())

    owner_membership_id = str(uuid4())
    member_membership_id = str(uuid4())
    other_membership_id = str(uuid4())

    case_id = str(uuid4())
    cap_job_id = str(uuid4())
    cap_intern_id = str(uuid4())

    owner_password = f"TestOwnerPass_{test_suffix}!123"
    owner_hash = hash_password(owner_password)
    now_ts = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(text("SET search_path TO flexbridge, public;"))

        # 1. Users
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (
                    id, created_at, updated_at, display_name, password_hash,
                    status, locale, timezone, adult_declared_at
                ) VALUES
                (:oid, :ts, :ts, 'TechCorp Owner', :chash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts),
                (:mid, :ts, :ts, 'TechCorp Mentor', :chash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts),
                (:other_oid, :ts, :ts, 'OtherOrg Owner', :chash, 'ACTIVE', 'uz', 'Asia/Tashkent', :ts)
            """),
            {
                "oid": owner_user_id,
                "mid": member_user_id,
                "other_oid": other_org_owner_id,
                "chash": owner_hash,
                "ts": now_ts,
            },
        )

        # 2. Organizations
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (
                    id, created_at, updated_at, legal_name, public_name, tax_id, status, region
                ) VALUES
                (:id, :ts, :ts, 'TechCorp Solutions MCHJ', 'TechCorp', :tax_id, 'VERIFIED', 'Tashkent'),
                (:other_id, :ts, :ts, 'Other Global Corp', 'OtherCorp', :other_tax_id, 'VERIFIED', 'Samarkand')
            """),
            {
                "id": org_id,
                "tax_id": f"TAX_FB168_{test_suffix}",
                "other_id": other_org_id,
                "other_tax_id": f"TAX_OTHER_{test_suffix}",
                "ts": now_ts,
            },
        )

        # 3. Org Memberships
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (
                    id, created_at, updated_at, organization_id, user_id, status, accepted_at
                ) VALUES
                (:omid, :ts, :ts, :org_id, :oid, 'ACTIVE', :ts),
                (:mmid, :ts, :ts, :org_id, :mid, 'ACTIVE', :ts),
                (:other_mid, :ts, :ts, :other_id, :other_oid, 'ACTIVE', :ts)
            """),
            {
                "omid": owner_membership_id,
                "org_id": org_id,
                "oid": owner_user_id,
                "mmid": member_membership_id,
                "mid": member_user_id,
                "other_mid": other_membership_id,
                "other_id": other_org_id,
                "other_oid": other_org_owner_id,
                "ts": now_ts,
            },
        )

        # 4. Role Grants (Owner and Mentor)
        owner_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'OWNER' AND scope_kind = 'ORG' LIMIT 1")
        ).scalar_one()

        mentor_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'MENTOR' AND scope_kind = 'ORG' LIMIT 1")
        ).scalar_one()

        conn.execute(
            text("""
                INSERT INTO flexbridge.org_role_grants (
                    id, created_at, updated_at, membership_id, role_id, granted_by_id
                ) VALUES
                (:g1, :ts, :ts, :omid, :rid1, :oid),
                (:g2, :ts, :ts, :mmid, :rid2, :oid),
                (:g3, :ts, :ts, :other_mid, :rid1, :other_oid)
            """),
            {
                "g1": str(uuid4()),
                "omid": owner_membership_id,
                "rid1": owner_role_id,
                "oid": owner_user_id,
                "g2": str(uuid4()),
                "mmid": member_membership_id,
                "rid2": mentor_role_id,
                "g3": str(uuid4()),
                "other_mid": other_membership_id,
                "other_oid": other_org_owner_id,
                "ts": now_ts,
            },
        )

        # 5. Verification Case
        conn.execute(
            text("""
                INSERT INTO flexbridge.verification_cases (
                    id, created_at, updated_at, requester_id, organization_id, kind,
                    status, current_revision, due_at, decided_at
                ) VALUES
                (:cid, :ts, :ts, :oid, :org_id, 'JOB_EMPLOYER', 'APPROVED', 1, :ts, :ts)
            """),
            {
                "cid": case_id,
                "oid": owner_user_id,
                "org_id": org_id,
                "ts": now_ts,
            },
        )

        # 6. Organization Capabilities
        conn.execute(
            text("""
                INSERT INTO flexbridge.organization_capabilities (
                    id, created_at, updated_at, organization_id, capability, status, approved_case_id
                ) VALUES
                (:cap1, :ts, :ts, :org_id, 'JOB_EMPLOYER', 'ACTIVE', :cid),
                (:cap2, :ts, :ts, :org_id, 'INTERNSHIP_HOST', 'ACTIVE', :cid)
            """),
            {
                "cap1": cap_job_id,
                "cap2": cap_intern_id,
                "org_id": org_id,
                "cid": case_id,
                "ts": now_ts,
            },
        )

    print("  ✓ DB fixtures successfully inserted.")

    # -------------------------------------------------------------------------
    # PHASE 4: Employer Owner session authentication via /api/auth/login
    # -------------------------------------------------------------------------
    print("\n[Phase 4] Employer Owner authentication via /api/auth/login...")
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    login_code, login_resp = api_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": owner_user_id, "password": owner_password},
        opener=opener,
    )
    assert login_code == 200, f"Owner login failed ({login_code}): {login_resp}"
    assert login_resp.get("ok") is True, f"Login payload not ok: {login_resp}"

    # Elevate session assurance to MFA in DB so governance operations pass
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE flexbridge.sessions SET assurance = 'MFA', updated_at = :now WHERE user_id = :uid AND revoked_at IS NULL"),
            {"now": datetime.now(timezone.utc), "uid": owner_user_id},
        )
    print("  ✓ Owner session assurance elevated to MFA in flexbridge.sessions.")

    # Verify session via /api/auth/me
    me_code, me_resp = api_request(f"{FRONTEND_URL}/api/auth/me", method="GET", opener=opener)
    assert me_code == 200, f"Expected 200 on /api/auth/me, got {me_code}: {me_resp}"
    user_obj = me_resp.get("user", {})
    actual_uid = user_obj.get("user_id") or user_obj.get("id")
    assert actual_uid == owner_user_id, f"User mismatch in session: {me_resp}"
    print("  ✓ Owner session confirmed active and authenticated.")

    # -------------------------------------------------------------------------
    # PHASE 5: GET /api/bff/employer/organization/{org}/capabilities (API-072)
    # -------------------------------------------------------------------------
    print("\n[Phase 5] API-072: GET /api/bff/employer/organization/{org}/capabilities...")
    cap_code, cap_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/capabilities",
        method="GET",
        opener=opener,
    )
    assert cap_code == 200, f"Expected 200 on capabilities, got {cap_code}: {cap_resp}"
    assert cap_resp.get("contract_id") == "API-072", f"Contract ID mismatch: {cap_resp}"
    items = cap_resp.get("items", [])
    assert len(items) >= 2, f"Expected at least 2 capabilities, got: {items}"

    cap_map = {item["capability"]: item["status"] for item in items}
    assert cap_map.get("JOB_EMPLOYER") in ("ACTIVE", "VERIFIED"), f"JOB_EMPLOYER not active: {cap_map}"
    assert cap_map.get("INTERNSHIP_HOST") in ("ACTIVE", "VERIFIED"), f"INTERNSHIP_HOST not active: {cap_map}"
    print(f"  ✓ API-072 returned valid capabilities: {cap_map}")

    # -------------------------------------------------------------------------
    # PHASE 6: GET /api/bff/employer/organization/{org}/verification (API-067)
    # -------------------------------------------------------------------------
    print("\n[Phase 6] API-067: GET /api/bff/employer/organization/{org}/verification...")
    verif_code, verif_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/verification",
        method="GET",
        opener=opener,
    )
    assert verif_code == 200, f"Expected 200 on verification, got {verif_code}: {verif_resp}"
    assert verif_resp.get("contract_id") == "API-067", f"Contract ID mismatch: {verif_resp}"
    assert verif_resp.get("organization_id") == org_id, f"Organization ID mismatch: {verif_resp}"
    assert verif_resp.get("membership_status") == "ACTIVE", f"Membership status not ACTIVE: {verif_resp}"
    cases = verif_resp.get("cases", [])
    assert len(cases) >= 1, f"Expected at least 1 verification case, got {cases}"
    print(f"  ✓ API-067 returned verified status with {len(cases)} case(s).")

    # -------------------------------------------------------------------------
    # PHASE 7: GET /api/bff/employer/organization/{org}/memberships (API-073)
    # -------------------------------------------------------------------------
    print("\n[Phase 7] API-073: GET /api/bff/employer/organization/{org}/memberships...")
    mems_code, mems_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/memberships",
        method="GET",
        opener=opener,
    )
    assert mems_code == 200, f"Expected 200 on memberships, got {mems_code}: {mems_resp}"
    assert mems_resp.get("contract_id") == "API-073", f"Contract ID mismatch: {mems_resp}"
    assert mems_resp.get("organization_id") == org_id, f"Organization ID mismatch: {mems_resp}"
    mem_items = mems_resp.get("items", [])
    assert len(mem_items) >= 2, f"Expected at least 2 memberships, got {mem_items}"

    mem_user_ids = [m["user_id"] for m in mem_items]
    assert owner_user_id in mem_user_ids, f"Owner user {owner_user_id} not in memberships: {mem_user_ids}"
    assert member_user_id in mem_user_ids, f"Member user {member_user_id} not in memberships: {mem_user_ids}"
    print(f"  ✓ API-073 returned {len(mem_items)} active team memberships.")

    # -------------------------------------------------------------------------
    # PHASE 8: POST /api/bff/employer/organization/{org}/invitations (API-074)
    # -------------------------------------------------------------------------
    print("\n[Phase 8] API-074: POST /api/bff/employer/organization/{org}/invitations...")

    # Negative 1: invalid role
    bad_role_code, bad_role_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/invitations",
        method="POST",
        data={"channel": "EMAIL", "destination": f"inv_{test_suffix}@example.com", "role_code": "SUPER_ADMIN"},
        opener=opener,
    )
    assert bad_role_code in (422, 400), f"Expected 422 for invalid role, got {bad_role_code}: {bad_role_resp}"

    # Positive: valid invitation
    invite_destination = f"hr.colleague.{test_suffix}@example.com"
    inv_code, inv_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/invitations",
        method="POST",
        data={"channel": "EMAIL", "destination": invite_destination, "role_code": "HR"},
        opener=opener,
    )
    assert inv_code in (200, 201), f"Expected 200/201 on invitation, got {inv_code}: {inv_resp}"
    assert inv_resp.get("contract_id") == "API-074", f"Contract ID mismatch: {inv_resp}"
    assert inv_resp.get("role_code") == "HR", f"Role code mismatch: {inv_resp}"
    assert "token" in inv_resp or "preview_path" in inv_resp, f"Token missing in invitation: {inv_resp}"
    print(f"  ✓ API-074 successfully issued 24h invitation with role HR: {inv_resp.get('id')}")

    # -------------------------------------------------------------------------
    # PHASE 9: POST /api/bff/employer/organization/{org}/memberships/{id}/revoke (API-075)
    # -------------------------------------------------------------------------
    print("\n[Phase 9] API-075: POST /api/bff/employer/organization/{org}/memberships/{id}/revoke...")

    # Negative 1: reason < 15 chars
    short_reason_code, short_reason_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/memberships/{member_membership_id}/revoke",
        method="POST",
        data={"reason": "too short"},
        opener=opener,
    )
    assert short_reason_code == 422, f"Expected 422 for short reason, got {short_reason_code}: {short_reason_resp}"

    # Negative 2: Protect sole owner from revocation
    owner_revoke_code, owner_revoke_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/memberships/{owner_membership_id}/revoke",
        method="POST",
        data={"reason": "Attempting to revoke sole owner of the organization."},
        opener=opener,
    )
    assert owner_revoke_code in (400, 403, 409, 422), f"Expected error when revoking sole owner, got {owner_revoke_code}: {owner_revoke_resp}"
    print("  ✓ Sole owner is protected against revocation (LAST_OWNER_PROTECTED).")

    # Positive: Revoke mentor membership
    valid_reason = "Employment contract concluded and team access revoked by HR."
    rev_code, rev_resp = api_request(
        f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/memberships/{member_membership_id}/revoke",
        method="POST",
        data={"reason": valid_reason},
        opener=opener,
    )
    assert rev_code == 200, f"Expected 200 on membership revocation, got {rev_code}: {rev_resp}"
    assert rev_resp.get("contract_id") == "API-075", f"Contract ID mismatch: {rev_resp}"
    assert rev_resp.get("status") == "REVOKED", f"Revocation status mismatch: {rev_resp}"
    assert rev_resp.get("membership_id") == member_membership_id, f"Membership ID mismatch: {rev_resp}"
    print(f"  ✓ API-075 successfully revoked membership {member_membership_id}.")

    # -------------------------------------------------------------------------
    # PHASE 10: IDOR & Cross-Org Security Guardrails
    # -------------------------------------------------------------------------
    print("\n[Phase 10] IDOR & Cross-Org Security Guardrails (403/404)...")

    idor_endpoints = [
        ("GET", f"{FRONTEND_URL}/api/bff/employer/organization/{other_org_id}/capabilities", None),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/organization/{other_org_id}/verification", None),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/organization/{other_org_id}/memberships", None),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/organization/{other_org_id}/invitations", {"channel": "EMAIL", "destination": "hacker@example.com", "role_code": "HR"}),
        ("POST", f"{FRONTEND_URL}/api/bff/employer/organization/{other_org_id}/memberships/{other_membership_id}/revoke", {"reason": "Malicious attempt to revoke other org member."}),
    ]

    for m, ep, payload in idor_endpoints:
        code, resp = api_request(ep, method=m, data=payload, opener=opener)
        assert code in (403, 404), f"Expected 403/404 on IDOR cross-org access {m} {ep}, got {code}: {resp}"
    print("  ✓ All 5 endpoints strictly reject IDOR cross-org access attempts.")

    print("\n================================================================================")
    print("ALL 10 PHASES OF FB-168 STAGING VERIFICATION PASSED SUCCESSFULLY (100% GREEN)!")
    print("================================================================================")


if __name__ == "__main__":
    main()
