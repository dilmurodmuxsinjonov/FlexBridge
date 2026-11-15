#!/usr/bin/env python3
"""FlexBridge 1.4 Candidate Saved Opportunities & Notifications Staging Verification Suite (FB-182).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected on all endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Anti-CSRF Origin Guard rejection on mutating endpoints (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 3: Database Fixtures Setup via PgBouncer (Users, Candidates, Opportunities, Notifications).
Phase 4: Candidate authentication via Next.js BFF (/api/auth/login) with MFA assurance.
Phase 5: API-004 Save Opportunity (Initial Save 201 Created).
Phase 6: API-004 Idempotent Repeat (200 OK) and Toggle Unsave (200 OK).
Phase 7: API-037 List Candidate's Saved Opportunities with preserved status.
Phase 8: API-038 Delete Saved Opportunity (204/200) with idempotent repeat.
Phase 9: API-031 Candidate Notifications Stream and Mark-as-Read receipt.
Phase 10: Negative Authorization & Cross-Candidate IDOR Isolation (403/404).

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
    print("FLEXBRIDGE 1.4 FB-182 STAGING VERIFICATION SUITE")
    print("Candidate Saved Opportunities (API-004/037/038) & Notifications (API-031)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Phase 1: Unauthenticated Access Rejections (401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n--- Phase 1: Unauthenticated BFF Endpoint Rejections ---")
    dummy_uuid = "00000000-0000-0000-0000-000000000000"
    endpoints = [
        ("GET", f"{FRONTEND_URL}/api/bff/me/saved-opportunities", None),
        ("POST", f"{FRONTEND_URL}/api/bff/me/saved-opportunities", {"opportunity_id": dummy_uuid}),
        ("DELETE", f"{FRONTEND_URL}/api/bff/me/saved-opportunities/{dummy_uuid}", None),
        ("GET", f"{FRONTEND_URL}/api/bff/me/notifications", None),
        ("POST", f"{FRONTEND_URL}/api/bff/me/notifications/{dummy_uuid}/read", None),
    ]

    for meth, ep, d in endpoints:
        code, data, _ = make_request(ep, method=meth, data=d, headers={"Origin": FRONTEND_URL})
        assert code == 401, f"Expected 401 for unauthenticated {meth} {ep}, got {code}: {data}"
        print(f"  [PASS] 401 on unauthenticated {meth} {ep}")

    # -------------------------------------------------------------------------
    # Phase 2: Anti-CSRF Origin Guard Rejection (403 CSRF_ORIGIN_MISMATCH)
    # -------------------------------------------------------------------------
    print("\n--- Phase 2: Anti-CSRF Origin Guard Rejections ---")
    mutating = [
        ("POST", f"{FRONTEND_URL}/api/bff/me/saved-opportunities", {"opportunity_id": dummy_uuid}),
        ("DELETE", f"{FRONTEND_URL}/api/bff/me/saved-opportunities/{dummy_uuid}", None),
        ("POST", f"{FRONTEND_URL}/api/bff/me/notifications/{dummy_uuid}/read", None),
    ]
    for meth, ep, d in mutating:
        code, data, _ = make_request(
            ep,
            method=meth,
            data=d,
            headers={"Origin": "https://malicious-attacker.com"},
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

    test_suffix = uuid4().hex[:8]
    user_a_id = str(uuid5(NAMESPACE_URL, f"flexbridge:fb182:cand_a:{test_suffix}"))
    user_b_id = str(uuid5(NAMESPACE_URL, f"flexbridge:fb182:cand_b:{test_suffix}"))
    org_id = str(uuid5(NAMESPACE_URL, f"flexbridge:fb182:org:{test_suffix}"))

    cand_a_profile_id = str(uuid4())
    cand_b_profile_id = str(uuid4())

    pwd = "CandidateSecret!2026"
    pwd_hash = hash_password(pwd)

    opp_1_id = str(uuid4())
    opp_2_id = str(uuid4())
    rev_1_id = str(uuid4())
    rev_2_id = str(uuid4())

    notif_1_id = str(uuid4())
    notif_2_id = str(uuid4())
    foreign_notif_id = str(uuid4())

    with engine.begin() as conn:
        now_ts = datetime.now(timezone.utc)
        today_date = now_ts.date()

        # 1. Users
        for uid, dname in [
            (user_a_id, "Nomzod A Saqlanganlar"),
            (user_b_id, "Nomzod B IDOR Himoyasi"),
        ]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                    VALUES (:id, :now, :now, :dname, :phash, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
                    ON CONFLICT (id) DO UPDATE SET password_hash = :phash, status = 'ACTIVE', updated_at = :now
                """),
                {"id": uid, "phash": pwd_hash, "dname": dname, "now": now_ts},
            )

        # 2. Candidate Profiles
        for pid, uid in [(cand_a_profile_id, user_a_id), (cand_b_profile_id, user_b_id)]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.candidate_profiles (
                        id, created_at, updated_at, user_id, headline, region,
                        experience_months, bio, visibility
                    ) VALUES (
                        :pid, :now, :now, :uid, 'Talaba Dasturchi', 'Tashkent',
                        6, 'FB-182 Test Nomzod', 'PUBLIC'
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {"pid": pid, "uid": uid, "now": now_ts},
            )

        # 3. Organization (VERIFIED)
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, legal_name, public_name, tax_id, status, region)
                VALUES (:id, :now, :now, 'FB182 Corp LLC', 'FB182Corp', :tax_id, 'VERIFIED', 'Tashkent')
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": org_id, "tax_id": f"TIN_{test_suffix}", "now": now_ts},
        )

        # 4. Published Opportunities
        for opp_id, rev_id, title in [
            (opp_1_id, rev_1_id, "Frontend React & Next.js Dasturchi (FB-182)"),
            (opp_2_id, rev_2_id, "Python FastAPI Backend Dasturchi (FB-182)"),
        ]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunities (
                        id, created_at, updated_at, organization_id, kind, status, capacity, occupied_count, published_at
                    ) VALUES (
                        :id, :now, :now, :org_id, 'PART_TIME', 'PUBLISHED', 5, 0, :now
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {"id": opp_id, "org_id": org_id, "now": now_ts},
            )

            conn.execute(
                text("""
                    INSERT INTO flexbridge.opportunity_revisions (
                        id, created_at, updated_at, opportunity_id, revision, author_id, title, description,
                        region, work_mode, eligibility, currency, is_paid, start_date, schedule_policy,
                        shift_match_mode, snapshot_schema, contract_type, published_at
                    ) VALUES (
                        :id, :now, :now, :opp_id, 1, :author_id, :title, 'Next.js & Python vazifalari',
                        'Tashkent', 'HYBRID', 'ANY', 'UZS', FALSE, :today, 'FLEXIBLE', 'EXACT', 1, 'LABOR_PART_TIME', :now
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": rev_id,
                    "opp_id": opp_id,
                    "author_id": user_a_id,
                    "title": title,
                    "today": today_date,
                    "now": now_ts,
                },
            )

            conn.execute(
                text("UPDATE flexbridge.opportunities SET current_revision_id = :rev_id WHERE id = :opp_id"),
                {"rev_id": rev_id, "opp_id": opp_id},
            )

        # 5. Outbox Events & Notifications for User A and User B
        evt_1_id = str(uuid4())
        evt_2_id = str(uuid4())
        evt_3_id = str(uuid4())

        for eid, uid in [(evt_1_id, user_a_id), (evt_2_id, user_a_id), (evt_3_id, user_b_id)]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.outbox_events (
                        id, created_at, updated_at, event_type, schema_version, aggregate_key,
                        payload, dedupe_key, available_at, processed_at, attempts
                    ) VALUES (
                        :id, :now, :now, 'NOTICE_EVENT', 1, :agg_key,
                        '{}'::jsonb, :dedupe, :now, :now, 1
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": eid,
                    "agg_key": f"user:{uid}",
                    "dedupe": str(uuid4()),
                    "now": now_ts,
                },
            )

        conn.execute(
            text("""
                INSERT INTO flexbridge.notifications (
                    id, created_at, updated_at, user_id, event_id, template_code, opportunity_id, read_at
                ) VALUES
                (:nid1, :now, :now, :uid_a, :e1, 'OPPORTUNITY_MATCH_ALERT', :opp1, NULL),
                (:nid2, :now, :now, :uid_a, :e2, 'INTERVIEW_SCHEDULED', :opp2, NULL),
                (:nid3, :now, :now, :uid_b, :e3, 'FOREIGN_ALERT', :opp1, NULL)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "nid1": notif_1_id,
                "nid2": notif_2_id,
                "nid3": foreign_notif_id,
                "e1": evt_1_id,
                "e2": evt_2_id,
                "e3": evt_3_id,
                "uid_a": user_a_id,
                "uid_b": user_b_id,
                "opp1": opp_1_id,
                "opp2": opp_2_id,
                "now": now_ts,
            },
        )

    print(f"  [PASS] Candidate User A: {user_a_id}")
    print(f"  [PASS] Candidate User B (Foreign): {user_b_id}")
    print(f"  [PASS] Opportunities: {opp_1_id}, {opp_2_id}")
    print(f"  [PASS] Notifications: {notif_1_id}, {notif_2_id}, {foreign_notif_id}")

    # -------------------------------------------------------------------------
    # Phase 4: Authentication via Next.js BFF (/api/auth/login)
    # -------------------------------------------------------------------------
    print("\n--- Phase 4: Authenticate Candidate Users via BFF ---")

    def login_and_elevate(uid: str, pwd_str: str, name: str) -> urllib.request.OpenerDirector:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        code, data, _ = make_request(
            f"{FRONTEND_URL}/api/auth/login",
            method="POST",
            data={"user_id": uid, "password": pwd_str},
            headers={"Origin": FRONTEND_URL},
            opener=opener,
        )
        assert code == 200, f"Login failed for {name} ({uid}): {code} - {data}"
        print(f"  [PASS] {name} logged in successfully via BFF")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE flexbridge.sessions
                    SET assurance = 'MFA', updated_at = NOW()
                    WHERE user_id = :uid AND revoked_at IS NULL
                    """
                ),
                {"uid": uid},
            )
        print(f"  [PASS] {name} session assurance elevated to MFA")
        return opener

    user_a_opener = login_and_elevate(user_a_id, pwd, "Candidate A")
    user_b_opener = login_and_elevate(user_b_id, pwd, "Candidate B (Foreign)")

    # -------------------------------------------------------------------------
    # Phase 5: API-004 Save Opportunity (Initial Save 201 Created)
    # -------------------------------------------------------------------------
    print("\n--- Phase 5: API-004 Save Opportunity (Initial Save) ---")
    code, save_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/saved-opportunities",
        method="POST",
        data={"opportunity_id": opp_1_id, "toggle": False},
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 201, f"Expected 201 Created on save opportunity, got {code}: {save_resp}"
    assert save_resp.get("ok") is True, f"Expected ok True: {save_resp}"
    assert save_resp.get("saved") is True, f"Expected saved True: {save_resp}"
    saved_1_id = save_resp.get("id")
    assert saved_1_id is not None, f"Expected saved row ID: {save_resp}"
    print(f"  [PASS] API-004 Opportunity {opp_1_id} saved successfully: {saved_1_id}")

    # Verify in DB
    with engine.begin() as conn:
        db_saved = conn.execute(
            text("SELECT id, candidate_id FROM flexbridge.saved_opportunities WHERE id = :id"),
            {"id": saved_1_id},
        ).mappings().first()
        assert db_saved is not None, "Saved opportunity row not found in DB"
        assert str(db_saved["candidate_id"]) == cand_a_profile_id, "Candidate ID mismatch in DB"
    print("  [PASS] DB verified: saved_opportunities row present with correct candidate_id")

    # -------------------------------------------------------------------------
    # Phase 6: API-004 Idempotent Repeat & Toggle Unsave
    # -------------------------------------------------------------------------
    print("\n--- Phase 6: API-004 Idempotent Repeat & Toggle Unsave ---")
    # Idempotent repeat on opp_1_id
    code, repeat_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/saved-opportunities",
        method="POST",
        data={"opportunity_id": opp_1_id, "toggle": False},
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 OK on idempotent save, got {code}: {repeat_resp}"
    assert repeat_resp.get("saved") is True, f"Expected saved True: {repeat_resp}"
    print("  [PASS] API-004 Idempotent repeat returns 200 with saved=True")

    # Save opp_2_id then toggle unsave
    code, save_2, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/saved-opportunities",
        method="POST",
        data={"opportunity_id": opp_2_id, "toggle": False},
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 201, f"Expected 201 on save opp_2: {code}"

    # Toggle unsave on opp_2_id
    code, toggle_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/saved-opportunities",
        method="POST",
        data={"opportunity_id": opp_2_id, "toggle": True},
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 on toggle unsave, got {code}: {toggle_resp}"
    assert toggle_resp.get("saved") is False, f"Expected saved False on toggle: {toggle_resp}"
    print("  [PASS] API-004 Toggle unsave returns 200 with saved=False")

    with engine.begin() as conn:
        opp2_exists = conn.execute(
            text("SELECT count(*) FROM flexbridge.saved_opportunities WHERE candidate_id = :cid AND opportunity_id = :oid"),
            {"cid": cand_a_profile_id, "oid": opp_2_id},
        ).scalar()
        assert opp2_exists == 0, f"Expected Opp 2 to be deleted from DB, found count {opp2_exists}"
    print("  [PASS] DB verified: toggled opportunity removed from saved_opportunities")

    # -------------------------------------------------------------------------
    # Phase 7: API-037 List Candidate's Saved Opportunities
    # -------------------------------------------------------------------------
    print("\n--- Phase 7: API-037 List Candidate's Saved Opportunities ---")
    code, list_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/saved-opportunities?page=1&page_size=20",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 on list saved opportunities, got {code}: {list_resp}"
    assert list_resp.get("ok") is True, f"Expected ok True: {list_resp}"
    assert list_resp.get("contract_id") == "API-037", f"Expected contract_id API-037: {list_resp}"
    items = list_resp.get("items", [])
    assert len(items) == 1, f"Expected exactly 1 saved item, got {len(items)}: {items}"
    assert items[0]["opportunity_id"] == opp_1_id, "Opportunity ID mismatch"
    assert items[0]["opportunity"]["is_closed"] is False, "Expected is_closed False"
    print(f"  [PASS] API-037 Listed 1 saved opportunity: {items[0]['opportunity']['title']}")

    # -------------------------------------------------------------------------
    # Phase 8: API-038 Delete Saved Opportunity
    # -------------------------------------------------------------------------
    print("\n--- Phase 8: API-038 Delete Saved Opportunity ---")
    code, del_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/saved-opportunities/{opp_1_id}",
        method="DELETE",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code in (200, 204), f"Expected 200/204 on delete saved opportunity, got {code}: {del_resp}"
    assert del_resp.get("ok") is True, f"Expected ok True: {del_resp}"
    assert del_resp.get("contract_id") == "API-038", f"Expected contract_id API-038: {del_resp}"
    print("  [PASS] API-038 Opportunity unsaved successfully")

    with engine.begin() as conn:
        rem_count = conn.execute(
            text("SELECT count(*) FROM flexbridge.saved_opportunities WHERE candidate_id = :cid AND opportunity_id = :oid"),
            {"cid": cand_a_profile_id, "oid": opp_1_id},
        ).scalar()
        assert rem_count == 0, f"Expected 0 saved opportunities, found {rem_count}"
    print("  [PASS] DB verified: saved_opportunity row deleted")

    # Repeat delete (Idempotent 204)
    code, repeat_del, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/saved-opportunities/{opp_1_id}",
        method="DELETE",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code in (200, 204), f"Expected 200/204 on repeat delete, got {code}: {repeat_del}"
    print("  [PASS] API-038 Repeat delete is idempotent")

    # -------------------------------------------------------------------------
    # Phase 9: API-031 Candidate Notifications Stream & Mark as Read
    # -------------------------------------------------------------------------
    print("\n--- Phase 9: API-031 Candidate Notifications Stream & Read Receipts ---")
    # Fetch unread notifications
    code, notif_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/notifications?unread_only=true&limit=50",
        method="GET",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 200, f"Expected 200 on fetch notifications, got {code}: {notif_resp}"
    assert notif_resp.get("ok") is True, f"Expected ok True: {notif_resp}"
    assert notif_resp.get("contract_id") == "API-031", f"Expected contract_id API-031: {notif_resp}"
    n_items = notif_resp.get("items", [])
    assert len(n_items) >= 2, f"Expected at least 2 unread notifications for User A, got {len(n_items)}: {n_items}"
    print(f"  [PASS] API-031 Fetched {len(n_items)} unread notifications for User A")

    # Mark first notification as read
    code, read_resp, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/notifications/{notif_1_id}/read",
        method="POST",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code in (200, 201), f"Expected 200 on mark read, got {code}: {read_resp}"
    assert read_resp.get("ok") is True, f"Expected ok True: {read_resp}"
    assert read_resp.get("read_at") is not None, f"Expected read_at timestamp: {read_resp}"
    print(f"  [PASS] API-031 Notification {notif_1_id} marked as read at {read_resp.get('read_at')}")

    # Verify in DB
    with engine.begin() as conn:
        read_ts = conn.execute(
            text("SELECT read_at FROM flexbridge.notifications WHERE id = :id"),
            {"id": notif_1_id},
        ).scalar()
        assert read_ts is not None, "Expected read_at timestamp in notifications table"
    print("  [PASS] DB verified: notification read_at timestamp updated")

    # -------------------------------------------------------------------------
    # Phase 10: Negative Authorization & Cross-Candidate IDOR Isolation
    # -------------------------------------------------------------------------
    print("\n--- Phase 10: Negative Authorization & Cross-Candidate IDOR Isolation ---")
    # 1. Seed a saved opportunity for User B
    with engine.begin() as conn:
        b_saved_id = str(uuid4())
        conn.execute(
            text("""
                INSERT INTO flexbridge.saved_opportunities (id, created_at, updated_at, candidate_id, opportunity_id)
                VALUES (:id, NOW(), NOW(), :cid, :oid)
                ON CONFLICT DO NOTHING
            """),
            {"id": b_saved_id, "cid": cand_b_profile_id, "oid": opp_1_id},
        )

    # User A tries to delete User B's saved opportunity -> Expect 403 SAVED_OPPORTUNITY_ACCESS_DENIED
    code, cross_del, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/saved-opportunities/{b_saved_id}",
        method="DELETE",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 403, f"Expected 403 on cross-candidate delete, got {code}: {cross_del}"
    print(f"  [PASS] Cross-candidate delete rejected with HTTP 403: {cross_del}")

    # 2. User A tries to mark User B's notification as read -> Expect 404 NOTIFICATION_NOT_FOUND (anti-IDOR)
    code, cross_notif, _ = make_request(
        f"{FRONTEND_URL}/api/bff/me/notifications/{foreign_notif_id}/read",
        method="POST",
        headers={"Origin": FRONTEND_URL},
        opener=user_a_opener,
    )
    assert code == 404, f"Expected 404 on cross-candidate notification read, got {code}: {cross_notif}"
    print(f"  [PASS] Cross-candidate notification mark-read rejected with HTTP 404: {cross_notif}")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF SAVED OPPORTUNITIES & NOTIFICATIONS STAGING VERIFICATION PASSED 100% GREEN!")
    print("=" * 80)


if __name__ == "__main__":
    main()
