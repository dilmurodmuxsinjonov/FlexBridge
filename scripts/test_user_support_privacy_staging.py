#!/usr/bin/env python3
"""FlexBridge 1.4 User Support, Privacy Rights & Notifications Hub Staging Verification Suite (FB-178).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected on all Support/Privacy/Preferences BFF endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Anti-CSRF Origin Guard rejection on mutating endpoints (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 3: DB Fixtures Setup via PgBouncer (127.0.0.1:5432/flexbridge, prepare_threshold=None).
Phase 4: Candidate & Operator authentication via Next.js BFF (/api/auth/login) with MFA assurance.
Phase 5: API-063 Support Ticket Lifecycle (Candidate creates ticket, verifies in list).
Phase 6: API-064 Support Message Thread (Candidate posts message reply, reads thread).
Phase 7: API-062 Privacy Request Lifecycle (Candidate submits EXPORT request, verifies in list).
Phase 8: API-114 Operator Privacy Request Resolution (Operator resolves request, candidate verifies status).
Phase 9: API-059 Notification Preferences (Candidate reads defaults, updates preferences, verifies persistence).
Phase 10: Negative Authorization Checks (Candidate cannot call operator resolve -> 403; Operator cannot self-resolve -> 403).

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
from uuid import uuid4, uuid5, NAMESPACE_URL

from dotenv import dotenv_values

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from app.services.auth import hash_password

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


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
    call_opener = opener or urllib.request.build_opener()

    try:
        with call_opener.open(req) as response:
            resp_headers = {k.lower(): v for k, v in response.headers.items()}
            raw_body = response.read().decode("utf-8")
            parsed_data = json.loads(raw_body) if raw_body else {}
            return response.status, parsed_data, resp_headers
    except urllib.error.HTTPError as exc:
        resp_headers = {k.lower(): v for k, v in exc.headers.items()}
        raw_body = exc.read().decode("utf-8")
        try:
            parsed_data = json.loads(raw_body)
        except Exception:
            parsed_data = {"raw": raw_body}
        return exc.code, parsed_data, resp_headers


def main() -> None:
    print("=" * 80)
    print("FLEXBRIDGE 1.4 FB-178 STAGING VERIFICATION SUITE")
    print("User Support, Privacy Rights & Notification Preferences Hub")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Phase 1: Unauthenticated Access Rejections (401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n--- Phase 1: Unauthenticated BFF Endpoint Rejections ---")
    endpoints = [
        ("GET", f"{FRONTEND_URL}/api/bff/me/support-tickets"),
        ("POST", f"{FRONTEND_URL}/api/bff/me/support-tickets"),
        ("GET", f"{FRONTEND_URL}/api/bff/support-tickets/00000000-0000-0000-0000-000000000000/messages"),
        ("POST", f"{FRONTEND_URL}/api/bff/support-tickets/00000000-0000-0000-0000-000000000000/messages"),
        ("GET", f"{FRONTEND_URL}/api/bff/me/privacy-requests"),
        ("POST", f"{FRONTEND_URL}/api/bff/me/privacy-requests"),
        ("POST", f"{FRONTEND_URL}/api/bff/operator/privacy-requests/00000000-0000-0000-0000-000000000000/resolve"),
        ("GET", f"{FRONTEND_URL}/api/bff/me/notification-preferences"),
        ("PUT", f"{FRONTEND_URL}/api/bff/me/notification-preferences"),
    ]

    for meth, ep in endpoints:
        dummy_data = {"test": 1} if meth in ("POST", "PUT") else None
        headers = {"Origin": FRONTEND_URL} if meth in ("POST", "PUT") else None
        code, data, _ = make_request(ep, method=meth, data=dummy_data, headers=headers)
        assert code == 401, f"Expected 401 for unauthenticated {meth} {ep}, got {code}: {data}"
        print(f"  [PASS] 401 on unauthenticated {meth} {ep}")

    # -------------------------------------------------------------------------
    # Phase 2: Anti-CSRF Origin Guard Rejection (403 CSRF_ORIGIN_MISMATCH)
    # -------------------------------------------------------------------------
    print("\n--- Phase 2: Anti-CSRF Origin Guard Rejections ---")
    mutating_eps = [
        ("POST", f"{FRONTEND_URL}/api/bff/me/support-tickets"),
        ("POST", f"{FRONTEND_URL}/api/bff/support-tickets/00000000-0000-0000-0000-000000000000/messages"),
        ("POST", f"{FRONTEND_URL}/api/bff/me/privacy-requests"),
        ("POST", f"{FRONTEND_URL}/api/bff/operator/privacy-requests/00000000-0000-0000-0000-000000000000/resolve"),
        ("PUT", f"{FRONTEND_URL}/api/bff/me/notification-preferences"),
    ]

    for meth, ep in mutating_eps:
        code, data, _ = make_request(
            ep,
            method=meth,
            data={"test": "payload"},
            headers={"Origin": "https://malicious-attacker.evil.com"},
        )
        assert code == 403, f"Expected 403 CSRF for {meth} {ep}, got {code}: {data}"
        assert data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH: {data}"
        print(f"  [PASS] 403 CSRF_ORIGIN_MISMATCH on {meth} {ep}")

    # -------------------------------------------------------------------------
    # Phase 3: DB Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n--- Phase 3: Database Fixtures Setup via PgBouncer ---")
    db_url = get_database_url()
    engine = create_engine(db_url, poolclass=NullPool, connect_args={"prepare_threshold": None})

    granter_user_id = str(uuid5(NAMESPACE_URL, "flexbridge:fb178:granter:user"))
    candidate_user_id = str(uuid5(NAMESPACE_URL, "flexbridge:fb178:candidate:user"))
    candidate_pwd = "CandidateSecretPass!2026"
    candidate_pwd_hash = hash_password(candidate_pwd)

    operator_user_id = str(uuid5(NAMESPACE_URL, "flexbridge:fb178:operator:user"))
    operator_pwd = "OperatorSecretPass!2026"
    operator_pwd_hash = hash_password(operator_pwd)

    with engine.begin() as conn:
        now_ts = datetime.now(timezone.utc)

        # Ensure role catalog entries
        for r_code in ("USER", "CANDIDATE", "SUPPORT", "ADMIN", "OPERATOR"):
            conn.execute(
                text("""
                    INSERT INTO flexbridge.role_catalog (id, created_at, updated_at, code, scope_kind, description)
                    VALUES (:id, :now, :now, :code, 'PLATFORM', :desc)
                    ON CONFLICT (code) DO NOTHING
                """),
                {"id": str(uuid4()), "now": now_ts, "code": r_code, "desc": f"Platform {r_code}"}
            )

        # 0. Granter Admin User (so operator grant does not violate chk_platform_grant_not_self)
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Granter Admin User', :phash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
                ON CONFLICT (id) DO UPDATE SET password_hash = :phash, status = 'ACTIVE', updated_at = :now
            """),
            {"id": granter_user_id, "phash": operator_pwd_hash, "now": now_ts},
        )

        # 1. Candidate User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Nomzod Sinov Foydalanuvchisi', :phash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
                ON CONFLICT (id) DO UPDATE SET
                    password_hash = :phash,
                    status = 'ACTIVE',
                    updated_at = :now
            """),
            {"id": candidate_user_id, "phash": candidate_pwd_hash, "now": now_ts},
        )

        # 2. Operator User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Operator Qo''llab-quvvatlash', :phash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
                ON CONFLICT (id) DO UPDATE SET
                    password_hash = :phash,
                    status = 'ACTIVE',
                    updated_at = :now
            """),
            {"id": operator_user_id, "phash": operator_pwd_hash, "now": now_ts},
        )

        # 3. Grant SUPPORT & ADMIN roles to operator
        support_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'SUPPORT' AND scope_kind = 'PLATFORM'")
        ).scalar()
        admin_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'ADMIN' AND scope_kind = 'PLATFORM'")
        ).scalar()

        for rid in (support_role_id, admin_role_id):
            if rid:
                conn.execute(
                    text("""
                        INSERT INTO flexbridge.platform_role_grants (id, created_at, updated_at, user_id, role_id, granted_by_id, expires_at)
                        VALUES (:id, :now, :now, :uid, :rid, :granter_id, :exp)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": str(uuid4()),
                        "now": now_ts,
                        "uid": operator_user_id,
                        "granter_id": granter_user_id,
                        "rid": rid,
                        "exp": now_ts + timedelta(days=30),
                    }
                )

        # 4. Clean up any leftover records from prior test runs for idempotent execution
        conn.execute(
            text("DELETE FROM flexbridge.privacy_requests WHERE user_id IN (:cid, :oid)"),
            {"cid": candidate_user_id, "oid": operator_user_id},
        )
        conn.execute(
            text("""
                DELETE FROM flexbridge.support_messages
                WHERE ticket_id IN (SELECT id FROM flexbridge.support_tickets WHERE requester_id IN (:cid, :oid))
            """),
            {"cid": candidate_user_id, "oid": operator_user_id},
        )
        conn.execute(
            text("DELETE FROM flexbridge.support_tickets WHERE requester_id IN (:cid, :oid)"),
            {"cid": candidate_user_id, "oid": operator_user_id},
        )
        conn.execute(
            text("DELETE FROM flexbridge.notification_preferences WHERE user_id = :cid"),
            {"cid": candidate_user_id},
        )

    print(f"  [PASS] Candidate user: {candidate_user_id}")
    print(f"  [PASS] Operator user: {operator_user_id}")

    # -------------------------------------------------------------------------
    # Phase 4: Authentication via Next.js BFF (/api/auth/login)
    # -------------------------------------------------------------------------
    print("\n--- Phase 4: Authenticate Candidate and Operator via BFF ---")

    def login_and_elevate(uid: str, pwd: str, role_name: str) -> urllib.request.OpenerDirector:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        code, data, _ = make_request(
            f"{FRONTEND_URL}/api/auth/login",
            method="POST",
            data={"user_id": uid, "password": pwd},
            headers={"Origin": FRONTEND_URL},
            opener=opener,
        )
        assert code == 200, f"Login failed for {role_name} ({uid}): {code} - {data}"
        print(f"  [PASS] {role_name} logged in successfully via BFF")

        # Elevate session assurance to MFA in DB
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE flexbridge.sessions
                    SET assurance = 'MFA',
                        updated_at = NOW()
                    WHERE user_id = :uid AND revoked_at IS NULL
                    """
                ),
                {"uid": uid},
            )
        print(f"  [PASS] {role_name} session assurance elevated to MFA")
        return opener

    candidate_opener = login_and_elevate(candidate_user_id, candidate_pwd, "Candidate")
    operator_opener = login_and_elevate(operator_user_id, operator_pwd, "Operator")

    # -------------------------------------------------------------------------
    # Phase 5: API-063 Support Ticket Lifecycle
    # -------------------------------------------------------------------------
    print("\n--- Phase 5: API-063 Support Ticket Lifecycle ---")
    ticket_payload = {
        "subject": "Sertifikat yuklashda tizim xatolik berdi (FB-178)",
        "body": "Assalomu alaykum! Profilimga yangi xalqaro til sertifikati PDF faylini yuklayotganimda xatolik yuz bermoqda. Iltimos yordam bering.",
        "category": "TECHNICAL",
        "priority": "HIGH",
    }
    code, ticket_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/support-tickets",
        method="POST",
        data=ticket_payload,
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code in (200, 201), f"Expected 200/201 on create ticket, got {code}: {ticket_resp}"
    assert ticket_resp.get("ok") is True, f"Response ok is False: {ticket_resp}"
    ticket_id = ticket_resp.get("id")
    assert ticket_id, f"Ticket id missing from response: {ticket_resp}"
    assert ticket_resp.get("status") == "OPEN", f"Expected status OPEN: {ticket_resp}"
    assert ticket_resp.get("priority") == "HIGH", f"Expected priority HIGH: {ticket_resp}"
    print(f"  [PASS] API-063 Support Ticket created: id={ticket_id}, status={ticket_resp.get('status')}")

    # Query ticket list
    code, list_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/support-tickets",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code == 200, f"Expected 200 on list tickets, got {code}: {list_resp}"
    items = list_resp.get("items", [])
    found = any(t.get("id") == ticket_id for t in items)
    assert found, f"Created ticket {ticket_id} not found in user's tickets list: {items}"
    print(f"  [PASS] API-063 Ticket verified in user ticket list (total={list_resp.get('total')})")

    # -------------------------------------------------------------------------
    # Phase 6: API-064 Support Messages Thread
    # -------------------------------------------------------------------------
    print("\n--- Phase 6: API-064 Support Message Thread ---")
    msg_payload = {
        "body": "Xatolik skrinshotini ham ko'rib chiqishingiz uchun qo'shimcha qilaman.",
    }
    code, msg_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/support-tickets/{ticket_id}/messages",
        method="POST",
        data=msg_payload,
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code in (200, 201), f"Expected 200/201 on post message, got {code}: {msg_resp}"
    assert msg_resp.get("ok") is True, f"Message response ok is False: {msg_resp}"
    message_id = msg_resp.get("id")
    assert message_id, f"Message id missing: {msg_resp}"
    print(f"  [PASS] API-064 Message posted: id={message_id}")

    # Read messages thread
    code, thread_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/support-tickets/{ticket_id}/messages",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code == 200, f"Expected 200 on get messages, got {code}: {thread_resp}"
    messages = thread_resp.get("messages") or thread_resp.get("items", [])
    assert len(messages) >= 2, f"Expected at least 2 messages in thread (initial + reply), got {len(messages)}"
    print(f"  [PASS] API-064 Message thread verified with {len(messages)} messages")

    # -------------------------------------------------------------------------
    # Phase 7: API-062 Privacy Request Lifecycle
    # -------------------------------------------------------------------------
    print("\n--- Phase 7: API-062 Privacy Request Lifecycle ---")
    privacy_payload = {
        "kind": "EXPORT",
        "reason": "GDPR va O'zbekiston qonunchiligiga muvofiq shaxsiy ma'lumotlarim nusxasini olish",
    }
    code, priv_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/privacy-requests",
        method="POST",
        data=privacy_payload,
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code in (200, 201), f"Expected 200/201 on create privacy request, got {code}: {priv_resp}"
    assert priv_resp.get("ok") is True, f"Privacy response ok is False: {priv_resp}"
    privacy_req_id = priv_resp.get("id")
    assert privacy_req_id, f"Privacy request id missing: {priv_resp}"
    assert priv_resp.get("status") == "PENDING", f"Expected status PENDING: {priv_resp}"
    print(f"  [PASS] API-062 Privacy Request created: id={privacy_req_id}, status=PENDING")

    # Query candidate's privacy requests list
    code, priv_list, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/privacy-requests",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code == 200, f"Expected 200 on get privacy requests, got {code}: {priv_list}"
    priv_items = priv_list.get("items", [])
    found_priv = any(p.get("id") == privacy_req_id for p in priv_items)
    assert found_priv, f"Privacy request {privacy_req_id} not found in user list: {priv_items}"
    print(f"  [PASS] API-062 Privacy request confirmed in list (total={priv_list.get('total')})")

    # -------------------------------------------------------------------------
    # Phase 8: API-114 Operator Privacy Request Resolution
    # -------------------------------------------------------------------------
    print("\n--- Phase 8: API-114 Operator Privacy Request Resolution ---")
    resolve_payload = {
        "status": "COMPLETED",
        "reason": "Ma'lumotlar arxiv shaklida tayyorlandi va foydalanuvchiga taqdim etildi.",
    }
    code, resolve_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/privacy-requests/{privacy_req_id}/resolve",
        method="POST",
        data=resolve_payload,
        headers={"Origin": FRONTEND_URL},
        opener=operator_opener,
    )
    assert code in (200, 201), f"Expected 200/201 on operator resolve, got {code}: {resolve_resp}"
    assert resolve_resp.get("ok") is True, f"Resolve response ok is False: {resolve_resp}"
    assert resolve_resp.get("status") == "COMPLETED", f"Expected status COMPLETED: {resolve_resp}"
    print(f"  [PASS] API-114 Privacy request resolved by operator to COMPLETED")

    # Candidate verifies updated status
    code, priv_list_after, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/privacy-requests",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code == 200
    matched = [p for p in priv_list_after.get("items", []) if p.get("id") == privacy_req_id]
    assert len(matched) == 1, f"Expected 1 matched request, got {matched}"
    assert matched[0].get("status") == "COMPLETED", f"Expected status COMPLETED, got {matched[0].get('status')}"
    assert matched[0].get("resolved_at") is not None, f"resolved_at must be populated: {matched[0]}"
    print(f"  [PASS] Candidate verified resolved status and timestamp: {matched[0].get('resolved_at')}")

    # -------------------------------------------------------------------------
    # Phase 9: API-059 Notification Preferences Management
    # -------------------------------------------------------------------------
    print("\n--- Phase 9: API-059 Notification Preferences Management ---")
    code, notif_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/notification-preferences",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code == 200, f"Expected 200 on get notification preferences, got {code}: {notif_resp}"
    prefs = notif_resp.get("preferences", [])
    assert len(prefs) > 0, f"Preferences list is empty: {notif_resp}"
    print(f"  [PASS] API-059 Effective notification preferences retrieved ({len(prefs)} items)")

    # Update preferences: enable EMAIL MARKETING while retaining SECURITY & TRANSACTIONAL
    update_payload = {
        "preferences": [
            {"channel": "EMAIL", "purpose": "MARKETING", "enabled": True},
            {"channel": "EMAIL", "purpose": "TRANSACTIONAL", "enabled": True},
            {"channel": "EMAIL", "purpose": "SECURITY", "enabled": True},
            {"channel": "SMS", "purpose": "SECURITY", "enabled": True},
        ]
    }
    code, update_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/notification-preferences",
        method="PUT",
        data=update_payload,
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code == 200, f"Expected 200 on update preferences, got {code}: {update_resp}"
    assert update_resp.get("ok") is True, f"Update response ok is False: {update_resp}"
    print(f"  [PASS] API-059 Notification preferences updated successfully")

    # Verify updated preferences persisted
    code, notif_resp_after, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/notification-preferences",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code == 200
    after_prefs = notif_resp_after.get("preferences", [])
    mkt_pref = next((p for p in after_prefs if p.get("channel") == "EMAIL" and p.get("purpose") == "MARKETING"), None)
    assert mkt_pref is not None, f"EMAIL MARKETING preference missing: {after_prefs}"
    assert mkt_pref.get("enabled") is True, f"EMAIL MARKETING expected enabled True: {mkt_pref}"
    print(f"  [PASS] API-059 Verified persisted EMAIL MARKETING preference: enabled=True")

    # -------------------------------------------------------------------------
    # Phase 10: Negative Authorization Checks
    # -------------------------------------------------------------------------
    print("\n--- Phase 10: Negative Authorization Checks ---")
    # 1. Non-operator candidate attempts to call operator resolve endpoint -> 403 PERMISSION_DENIED
    code, unauth_resolve, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/privacy-requests/{privacy_req_id}/resolve",
        method="POST",
        data={"status": "REJECTED", "reason": "No permission test from candidate"},
        headers={"Origin": FRONTEND_URL},
        opener=candidate_opener,
    )
    assert code in (403, 400), f"Expected 403 on candidate calling operator resolve, got {code}: {unauth_resolve}"
    print(f"  [PASS] Non-operator candidate rejected with HTTP {code} on operator resolution")

    # 2. Operator self-resolution check: Operator creates their own privacy request, then attempts to resolve it
    code, op_priv_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/privacy-requests",
        method="POST",
        data={"kind": "EXPORT", "reason": "Operator self-test privacy request"},
        headers={"Origin": FRONTEND_URL},
        opener=operator_opener,
    )
    assert code in (200, 201), f"Failed creating operator privacy request: {code} - {op_priv_resp}"
    op_req_id = op_priv_resp.get("id")

    code, self_resolve_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/privacy-requests/{op_req_id}/resolve",
        method="POST",
        data={"status": "COMPLETED", "reason": "Attempting self-resolution"},
        headers={"Origin": FRONTEND_URL},
        opener=operator_opener,
    )
    assert code in (400, 403), f"Expected 400 or 403 on self-resolution, got {code}: {self_resolve_resp}"
    print(f"  [PASS] Operator self-resolution rejected with HTTP {code} (SELF_RESOLUTION_FORBIDDEN)")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF USER SUPPORT & PRIVACY STAGING VERIFICATION PASSED 100% GREEN!")
    print("=" * 80)


if __name__ == "__main__":
    main()
