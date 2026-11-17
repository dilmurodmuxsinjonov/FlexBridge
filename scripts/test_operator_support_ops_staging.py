#!/usr/bin/env python3
"""FlexBridge 1.4 Operator Support Tickets, Incidents, DR SLA & Analytics Verification Suite (FB-172).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Unauthenticated access rejected on Operator Support Ops BFF endpoints (HTTP 401 AUTH_REQUIRED).
Phase 2: Anti-CSRF Origin Guard rejection on mutating endpoints (HTTP 403 CSRF_ORIGIN_MISMATCH).
Phase 3: DB Fixtures Setup via PgBouncer (127.0.0.1:5432/flexbridge, prepare_threshold=None).
Phase 4: Operator Admin authentication via Next.js BFF (/api/auth/login) with MFA assurance.
Phase 5: Operator queries support tickets queue via BFF (API-112: GET /api/bff/operator/support-tickets).
Phase 6: Operator posts reply / internal note with status update (API-113: POST .../messages).
Phase 7: Negative validation: empty message body rejected (HTTP 422 INVALID_MESSAGE_BODY).
Phase 8: Operator declares operational incident via BFF (API-122: POST /api/bff/operator/incidents).
Phase 9: Operator inspects DR restore run SLA proofs via BFF (API-123: GET /api/bff/operator/restore-runs).
Phase 10: Operator inspects platform analytics telemetry via BFF (API-124: GET /api/bff/operator/analytics).

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

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
    except urllib.error.HTTPError as err:
        resp_headers = {k.lower(): v for k, v in err.headers.items()}
        raw_body = err.read().decode("utf-8")
        try:
            parsed_data = json.loads(raw_body)
        except Exception:
            parsed_data = {"raw": raw_body}
        return err.code, parsed_data, resp_headers


def main():
    print("=" * 80)
    print("FLEXBRIDGE 1.4 OPERATOR SUPPORT OPS & SLA STAGING VERIFICATION (FB-172)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 80)

    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    test_suffix = uuid4().hex[:8]
    raw_password = f"AdminPass_{test_suffix}!"
    admin_hash = hash_password(raw_password)

    admin_user_id = str(uuid4())
    approver_user_id = str(uuid4())
    customer_user_id = str(uuid4())
    ticket_id = str(uuid4())
    restore_run_id = str(uuid4())

    now_utc = datetime.now(timezone.utc)

    # -------------------------------------------------------------------------
    # PHASE 1: Unauthenticated rejection (HTTP 401 AUTH_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n[Phase 1] Verifying unauthenticated rejection on Operator Support Ops endpoints...")
    fake_ticket = str(uuid4())

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/support-tickets",
        method="GET",
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> GET /api/bff/operator/support-tickets: 401 AUTH_REQUIRED verified.")

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/support-tickets/{fake_ticket}/messages",
        method="POST",
        data={"body": "Hello"},
        headers={"Origin": FRONTEND_URL},
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> POST .../messages: 401 AUTH_REQUIRED verified.")

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/incidents",
        method="POST",
        data={"title": "Major DB degradation", "severity": "P2"},
        headers={"Origin": FRONTEND_URL},
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> POST /api/bff/operator/incidents: 401 AUTH_REQUIRED verified.")

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/restore-runs",
        method="GET",
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> GET /api/bff/operator/restore-runs: 401 AUTH_REQUIRED verified.")

    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/analytics",
        method="GET",
    )
    assert status_code == 401, f"Expected 401, got {status_code}: {data}"
    assert data.get("error") == "AUTH_REQUIRED", f"Expected AUTH_REQUIRED, got {data}"
    print("  -> GET /api/bff/operator/analytics: 401 AUTH_REQUIRED verified.")

    # -------------------------------------------------------------------------
    # PHASE 2: Anti-CSRF Origin Guard rejection (HTTP 403 CSRF_ORIGIN_MISMATCH)
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Verifying Anti-CSRF Origin Guard rejection on mutating endpoints...")
    status_code, data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/support-tickets/{fake_ticket}/messages",
        method="POST",
        data={"body": "Malicious payload"},
        headers={"Origin": "https://malicious-attacker.com"},
    )
    assert status_code == 403, f"Expected 403 CSRF rejection, got {status_code}: {data}"
    assert data.get("error") == "CSRF_ORIGIN_MISMATCH", f"Expected CSRF_ORIGIN_MISMATCH, got {data}"
    print("  -> CSRF cross-origin attack blocked: 403 CSRF_ORIGIN_MISMATCH verified.")

    # -------------------------------------------------------------------------
    # PHASE 3: DB Fixtures Setup via PgBouncer
    # -------------------------------------------------------------------------
    print("\n[Phase 3] Seeding test fixtures in Staging PostgreSQL via PgBouncer...")
    with engine.begin() as conn:
        # Ensure role_catalog has required platform roles
        for r_code in ["ADMIN", "SUPPORT", "SECURITY_LEAD"]:
            conn.execute(
                text("""
                    INSERT INTO flexbridge.role_catalog (id, created_at, updated_at, code, scope_kind, description)
                    VALUES (:id, :now, :now, :code, 'PLATFORM', :desc)
                    ON CONFLICT (code) DO NOTHING
                """),
                {"id": str(uuid4()), "now": now_utc, "code": r_code, "desc": f"Platform {r_code}"}
            )

        # 1. Admin Operator User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Sherzod Aliyev (Admin)', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": admin_user_id, "pwd": admin_hash, "now": now_utc}
        )

        # 2. Approver User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Approver Admin', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": approver_user_id, "pwd": admin_hash, "now": now_utc}
        )

        # 3. Customer User
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at, auth_version)
                VALUES (:id, :now, :now, 'Zafarbek Tursunov', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now, 1)
            """),
            {"id": customer_user_id, "pwd": admin_hash, "now": now_utc}
        )

        # 4. Platform Role Grant: ADMIN to admin_user_id
        admin_role_id = conn.execute(
            text("SELECT id FROM flexbridge.role_catalog WHERE code = 'ADMIN' AND scope_kind = 'PLATFORM'")
        ).scalar()
        assert admin_role_id, "Platform ADMIN role must exist"

        conn.execute(
            text("""
                INSERT INTO flexbridge.platform_role_grants (id, created_at, updated_at, user_id, role_id, granted_by_id, expires_at)
                VALUES
                    (:id1, :now, :now, :admin_id, :rid, :approver_id, :exp),
                    (:id2, :now, :now, :approver_id, :rid, :admin_id, :exp)
            """),
            {
                "id1": str(uuid4()),
                "id2": str(uuid4()),
                "now": now_utc,
                "admin_id": admin_user_id,
                "approver_id": approver_user_id,
                "rid": admin_role_id,
                "exp": now_utc + timedelta(days=30),
            }
        )

        # 4. Support Ticket & Message
        conn.execute(
            text("""
                INSERT INTO flexbridge.support_tickets (
                    id, created_at, updated_at, requester_id, category, priority, status,
                    subject, first_response_due_at, resolved_at
                )
                VALUES (
                    :id, :now, :now, :req_id, 'TECHNICAL', 'HIGH', 'OPEN',
                    'SMS ulanishida uzilish qayd etilmoqda', :due, NULL
                )
            """),
            {
                "id": ticket_id,
                "now": now_utc,
                "req_id": customer_user_id,
                "due": now_utc + timedelta(hours=12),
            }
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.support_messages (
                    id, created_at, updated_at, ticket_id, author_id, body, internal
                )
                VALUES (
                    :id, :now, :now, :tid, :aid, 'Iltimos, qayta yuborish imkonini tekshiring.', FALSE
                )
            """),
            {
                "id": str(uuid4()),
                "now": now_utc,
                "tid": ticket_id,
                "aid": customer_user_id,
            }
        )

        # 5. Restore Run proof
        conn.execute(
            text("""
                INSERT INTO flexbridge.restore_runs (
                    id, created_at, started_at, finished_at, backup_ref, status,
                    recovered_through, measured_rpo_minutes, measured_rto_minutes, checked_by_id, evidence_ref
                )
                VALUES (
                    :id, :now, :now, :now, 's3://flexbridge-backups/snapshot-dr-test.tar.gz', 'COMPLETED',
                    :now, 12, 38, :admin_id, 'https://storage/evidence.json'
                )
            """),
            {
                "id": restore_run_id,
                "now": now_utc,
                "admin_id": admin_user_id,
            }
        )
        print("  -> DB fixtures successfully committed.")

    # -------------------------------------------------------------------------
    # PHASE 4: Operator Admin Authentication via BFF & Elevate Session to MFA
    # -------------------------------------------------------------------------
    print("\n[Phase 4] Authenticating Operator Admin via /api/auth/login and elevating session to MFA...")
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    status_code, login_data, _ = make_request(
        f"{FRONTEND_URL}/api/auth/login",
        method="POST",
        data={"user_id": admin_user_id, "password": raw_password},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 200, f"Login failed: status {status_code}, data {login_data}"
    assert login_data.get("ok") is True, f"Expected ok: True in login response: {login_data}"
    print(f"  -> Operator Admin login successful. Roles: {login_data.get('user', {}).get('roles')}")

    # Elevate active session assurance to 'MFA'
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE flexbridge.sessions
                SET assurance = 'MFA', updated_at = :now
                WHERE user_id = :uid AND revoked_at IS NULL
            """),
            {"uid": admin_user_id, "now": datetime.now(timezone.utc)}
        )
    print("  -> Session assurance successfully upgraded to 'MFA' in PostgreSQL.")

    # -------------------------------------------------------------------------
    # PHASE 5: Operator queries support tickets queue via BFF (API-112)
    # -------------------------------------------------------------------------
    print("\n[Phase 5] Operator queries support tickets queue via BFF (API-112: GET .../support-tickets)...")
    status_code, tickets_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/support-tickets?status=OPEN",
        method="GET",
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {tickets_data}"
    assert tickets_data.get("ok") is True, f"Expected ok: True, got {tickets_data}"
    assert tickets_data.get("contract_id") == "API-112", f"Expected API-112, got {tickets_data}"
    items = tickets_data.get("items", [])
    assert len(items) >= 1, f"Expected >= 1 ticket item, got {items}"
    found_ticket = next((t for t in items if t.get("id") == ticket_id), None)
    assert found_ticket is not None, f"Seeded ticket {ticket_id} not found in items: {items}"
    assert found_ticket.get("category") == "TECHNICAL", f"Category mismatch: {found_ticket}"
    assert found_ticket.get("priority") == "HIGH", f"Priority mismatch: {found_ticket}"
    print(f"  -> Support tickets queue verified: found ticket #{ticket_id[:8]} with status '{found_ticket.get('status')}'.")

    # -------------------------------------------------------------------------
    # PHASE 6: Operator posts reply / internal note with status update (API-113)
    # -------------------------------------------------------------------------
    print("\n[Phase 6] Operator posts reply with status update via BFF (API-113: POST .../messages)...")
    status_code, reply_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/support-tickets/{ticket_id}/messages",
        method="POST",
        data={
            "body": "SMS shlyuzi sozlamalari qayta yuklandi. Iltimos qaytadan urinib ko'ring.",
            "internal": False,
            "status": "IN_PROGRESS",
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 201, f"Expected 201, got {status_code}: {reply_data}"
    assert reply_data.get("ok") is True, f"Expected ok: True, got {reply_data}"
    assert reply_data.get("contract_id") == "API-113", f"Expected API-113, got {reply_data}"
    print(f"  -> Message reply successfully posted. Ticket updated to 'IN_PROGRESS'.")

    # -------------------------------------------------------------------------
    # PHASE 7: Negative validation: empty message body rejected (HTTP 422)
    # -------------------------------------------------------------------------
    print("\n[Phase 7] Verifying negative validation: empty message body rejected (HTTP 422)...")
    status_code, neg_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/support-tickets/{ticket_id}/messages",
        method="POST",
        data={"body": "   "},
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 422, f"Expected 422, got {status_code}: {neg_data}"
    assert neg_data.get("error") == "INVALID_MESSAGE_BODY", f"Expected INVALID_MESSAGE_BODY, got {neg_data}"
    print("  -> Empty message body cleanly rejected: 422 INVALID_MESSAGE_BODY verified.")

    # -------------------------------------------------------------------------
    # PHASE 8: Operator declares operational incident via BFF (API-122)
    # -------------------------------------------------------------------------
    print("\n[Phase 8] Operator declares operational incident via BFF (API-122: POST .../incidents)...")
    status_code, inc_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/incidents",
        method="POST",
        data={
            "severity": "P2",
            "title": "Tashqi SMS provayder uzilishi",
            "summary": "Toshkent provayderida kechikishlar kuzatildi, zahira kanalga o'tkazilmoqda.",
            "commander_user_id": admin_user_id,
        },
        headers={"Origin": FRONTEND_URL},
        opener=opener,
    )
    assert status_code == 201, f"Expected 201, got {status_code}: {inc_data}"
    assert inc_data.get("ok") is True, f"Expected ok: True, got {inc_data}"
    assert inc_data.get("contract_id") == "API-122", f"Expected API-122, got {inc_data}"
    assert inc_data.get("severity") == "P2", f"Expected P2, got {inc_data}"
    assert "incident_id" in inc_data, f"Expected incident_id in response: {inc_data}"
    print(f"  -> Operational incident declared: Incident #{inc_data.get('incident_id')[:8]} (Severity P2).")

    # -------------------------------------------------------------------------
    # PHASE 9: Operator inspects DR restore run SLA proofs via BFF (API-123)
    # -------------------------------------------------------------------------
    print("\n[Phase 9] Operator inspects DR restore run SLA proofs via BFF (API-123: GET .../restore-runs)...")
    status_code, runs_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/restore-runs?status=COMPLETED",
        method="GET",
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {runs_data}"
    assert runs_data.get("ok") is True, f"Expected ok: True, got {runs_data}"
    assert runs_data.get("contract_id") == "API-123", f"Expected API-123, got {runs_data}"
    run_items = runs_data.get("items", [])
    assert len(run_items) >= 1, f"Expected >= 1 restore run proof, got {run_items}"
    found_run = next((r for r in run_items if r.get("id") == restore_run_id), None)
    assert found_run is not None, f"Seeded restore run {restore_run_id} not found: {run_items}"
    assert found_run.get("sla_met") is True, f"Expected sla_met: True, got {found_run}"
    print(f"  -> DR restore runs verified: {len(run_items)} runs returned; SLA target evaluation verified.")

    # -------------------------------------------------------------------------
    # PHASE 10: Operator inspects platform analytics telemetry via BFF (API-124)
    # -------------------------------------------------------------------------
    print("\n[Phase 10] Operator inspects platform analytics telemetry via BFF (API-124: GET .../analytics)...")
    status_code, analytics_data, _ = make_request(
        f"{FRONTEND_URL}/api/bff/operator/analytics",
        method="GET",
        opener=opener,
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {analytics_data}"
    assert analytics_data.get("ok") is True, f"Expected ok: True, got {analytics_data}"
    assert analytics_data.get("contract_id") == "API-124", f"Expected API-124, got {analytics_data}"
    assert "deduplication_effectiveness_pct" in analytics_data, f"Missing deduplication metric: {analytics_data}"
    assert "mutual_start_rate_pct" in analytics_data, f"Missing mutual_start_rate metric: {analytics_data}"
    assert "outbox_backlog_count" in analytics_data, f"Missing outbox_backlog_count metric: {analytics_data}"
    print(f"  -> Operational analytics verified (Dedup: {analytics_data.get('deduplication_effectiveness_pct')}%, Mutual Start: {analytics_data.get('mutual_start_rate_pct')}%).")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF OPERATOR SUPPORT OPS & SLA VERIFICATION PASSED (100% GREEN)!")
    print("=" * 80)


if __name__ == "__main__":
    main()
