"""Functional contract tests for Operator Security & Operations (API-118, API-119, API-120, API-122, API-123, API-124).

Contracts:
- API-118: GET /api/v1/operator/audit-events (CAP-036 / ADMIN_AUDIT / AUDITOR, ADMIN)
- API-119: POST /api/v1/operator/access-requests (CAP-036 / ADMIN_AUDIT / ADMIN)
- API-120: POST /api/v1/operator/users/{id}/revoke-sessions (CAP-036 / ADMIN_AUDIT / ADMIN)
- API-122: POST /api/v1/operator/incidents (CAP-037 / OPERATIONS / ADMIN)
- API-123: GET /api/v1/operator/restore-runs (CAP-037 / OPERATIONS / ADMIN)
- API-124: GET /api/v1/operator/analytics (CAP-038 / OPERATIONS / ADMIN)
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def test_api118_operator_audit_events_query_and_pagination(client, identities):
    admin = identities("ADMIN")
    target_user = identities()

    now_utc = now()
    event_id1 = str(uuid4())
    event_id2 = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn, "audit_events",
            id=event_id1, created_at=now_utc, updated_at=now_utc,
            actor_id=target_user["user_id"], session_id=None,
            action="TEST_ACTION_A", object_type="test_entity",
            object_key="KEY-001", scope_snapshot={"domain": "TEST"},
            before_digest=None, after_digest=None, reason="Integration test A",
            request_id=f"req-118-1-{uuid4().hex[:6]}", occurred_at=now_utc,
        )
        insert_row(
            conn, "audit_events",
            id=event_id2, created_at=now_utc, updated_at=now_utc,
            actor_id=target_user["user_id"], session_id=None,
            action="TEST_ACTION_B", object_type="test_entity",
            object_key="KEY-002", scope_snapshot={"domain": "TEST"},
            before_digest=None, after_digest=None, reason="Integration test B",
            request_id=f"req-118-2-{uuid4().hex[:6]}", occurred_at=now_utc,
        )

    # 1. Query audit events
    res = client.get("/api/v1/operator/audit-events?limit=50", headers=admin["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-118"
    assert data["capability"] == "ADMIN_AUDIT"
    assert data["total_records"] >= 2

    event_ids = [it["id"] for it in data["items"]]
    assert event_id1 in event_ids
    assert event_id2 in event_ids

    # 2. Filter by action
    res_filtered = client.get("/api/v1/operator/audit-events?action=TEST_ACTION_A", headers=admin["headers"])
    assert res_filtered.status_code == 200, res_filtered.text
    filtered_data = res_filtered.json()
    assert all(it["action"] == "TEST_ACTION_A" for it in filtered_data["items"])


def test_api119_operator_break_glass_access_requests(client, identities):
    admin = identities("ADMIN")
    target_user = identities()
    independent_approver = identities("ADMIN")

    payload = {
        "target_user_id": target_user["user_id"],
        "role_code": "SUPPORT",
        "reason": "Emergency production support break-glass required for incident recovery",
        "independent_approver_id": independent_approver["user_id"],
        "duration_minutes": 180,
    }

    res = client.post("/api/v1/operator/access-requests", json=payload, headers=admin["headers"])
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["contract_id"] == "API-119"
    assert data["capability"] == "ADMIN_AUDIT"
    assert data["target_user_id"] == target_user["user_id"]
    assert data["role_code"] == "SUPPORT"
    assert data["granted_by_id"] == independent_approver["user_id"]
    assert data["duration_minutes"] == 180
    assert data["status"] == "GRANTED"
    assert data["grant_id"] is not None


def test_api120_operator_revoke_user_sessions(client, identities):
    admin = identities("ADMIN")
    target_user = identities()

    # Seed active session for target user
    now_utc = now()
    sess_id = str(uuid4())
    with transaction() as conn:
        insert_row(
            conn, "sessions",
            id=sess_id, created_at=now_utc, updated_at=now_utc,
            user_id=target_user["user_id"], token_digest="sha256:dummy_token_digest",
            device_key_digest="sha256:dummy_dev_digest", assurance="PASSWORD_ONLY",
            expires_at=now_utc + timedelta(hours=24), revoked_at=None,
            last_seen_at=now_utc, auth_version=1,
        )

    payload = {
        "reason": "Suspicious login attempt detected by automated SIEM",
    }

    res = client.post(f"/api/v1/operator/users/{target_user['user_id']}/revoke-sessions", json=payload, headers=admin["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-120"
    assert data["capability"] == "ADMIN_AUDIT"
    assert data["user_id"] == target_user["user_id"]
    assert data["revoked_sessions_count"] >= 1
    assert data["status"] == "REVOKED"


def test_api122_operator_declare_incident(client, identities):
    admin = identities("ADMIN")
    commander = identities()

    payload = {
        "severity": "P1",
        "title": "Payment gateway latency degradation during settlement window",
        "summary": "Payment gateway latency degradation during settlement window",
        "commander_id": commander["user_id"],
        "postmortem_ref": "https://wiki.flexbridge.uz/incidents/inc-122",
    }

    res = client.post("/api/v1/operator/incidents", json=payload, headers=admin["headers"])
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["contract_id"] == "API-122"
    assert data["capability"] == "OPERATIONS"
    assert data["severity"] == "P1"
    assert data["status"] == "OPEN"
    assert data["commander_id"] == commander["user_id"]
    assert data["incident_id"] is not None


def test_api123_operator_restore_runs(client, identities):
    admin = identities("ADMIN")
    checker = identities()

    now_utc = now()
    run_id = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn, "restore_runs",
            id=run_id, created_at=now_utc, updated_at=now_utc,
            started_at=now_utc - timedelta(minutes=45), finished_at=now_utc,
            backup_ref="s3://backups/2026-11-12/flexbridge_full.dump",
            status="VERIFIED", recovered_through=now_utc - timedelta(minutes=15),
            measured_rpo_minutes=15, measured_rto_minutes=45,
            checked_by_id=checker["user_id"], evidence_ref="https://evidence.flexbridge.uz/dr-run-001",
        )

    res = client.get("/api/v1/operator/restore-runs", headers=admin["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-123"
    assert data["capability"] == "OPERATIONS"
    assert data["target_sla"]["max_rpo_hours"] == 24
    assert data["target_sla"]["max_rto_hours"] == 4
    assert data["restore_drill_verified"] is True
    assert data["total_runs"] >= 1

    run_ids = [it["id"] for it in data["items"]]
    assert run_id in run_ids
    target_item = next(it for it in data["items"] if it["id"] == run_id)
    assert target_item["sla_met"] is True
    assert target_item["measured_rpo_minutes"] == 15
    assert target_item["measured_rto_minutes"] == 45


def test_api124_operator_analytics(client, identities):
    admin = identities("ADMIN")
    user = identities()

    now_utc = now()
    event_id = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn, "analytics_events",
            id=event_id, created_at=now_utc, updated_at=now_utc,
            event_key=f"event_key_{uuid4().hex[:8]}", event_name="CANDIDATE_SEARCH",
            actor_pseudonym=f"pseudo_{uuid4().hex[:8]}", cohort="2026-Q4",
            properties={"search_term": "python", "filters_count": 2},
            occurred_at=now_utc, schema_version=1,
        )

    res = client.get("/api/v1/operator/analytics?cohort=2026-Q4", headers=admin["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-124"
    assert data["capability"] == "OPERATIONS"
    assert data["cohort"] == "2026-Q4"
    assert "analytics" in data
    assert "placements" in data
    assert "outbox_health" in data
    assert data["analytics"]["total_events"] >= 1
    assert data["analytics"]["dedup_efficiency_pct"] >= 0.0
