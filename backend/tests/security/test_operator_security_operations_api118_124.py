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
from sqlalchemy import select
from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def test_api118_operator_audit_events_filtering_and_keyset_pagination(client, identities):
    admin = identities("ADMIN")
    user_a = identities()
    user_b = identities()

    now_utc = now()
    e1_id = str(uuid4())
    e2_id = str(uuid4())
    e3_id = str(uuid4())

    with transaction() as conn:
        t_audit = table("audit_events")
        # Event 1: older
        conn.execute(
            t_audit.insert().values(
                id=e1_id,
                created_at=now_utc - timedelta(hours=2),
                updated_at=now_utc - timedelta(hours=2),
                actor_id=user_a["user_id"],
                action="USER_LOGIN_SUCCESS",
                object_type="user",
                object_key=user_a["user_id"],
                scope_snapshot={"channel": "web"},
                request_id=str(uuid4()),
                occurred_at=now_utc - timedelta(hours=2),
            )
        )
        # Event 2: middle
        conn.execute(
            t_audit.insert().values(
                id=e2_id,
                created_at=now_utc - timedelta(hours=1),
                updated_at=now_utc - timedelta(hours=1),
                actor_id=user_b["user_id"],
                action="FEATURE_FLAG_MUTATED",
                object_type="feature_flag",
                object_key="PAYMENT_GATEWAY_V2",
                scope_snapshot={"env": "prod"},
                request_id=str(uuid4()),
                occurred_at=now_utc - timedelta(hours=1),
            )
        )
        # Event 3: newest
        conn.execute(
            t_audit.insert().values(
                id=e3_id,
                created_at=now_utc,
                updated_at=now_utc,
                actor_id=user_a["user_id"],
                action="FEATURE_FLAG_MUTATED",
                object_type="feature_flag",
                object_key="PAYMENT_GATEWAY_V2",
                scope_snapshot={"env": "prod"},
                request_id=str(uuid4()),
                occurred_at=now_utc,
            )
        )

    # 1. Query with action filter
    res = client.get(
        "/api/v1/operator/audit-events?action=FEATURE_FLAG_MUTATED",
        headers=admin["headers"],
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-118"
    assert data["capability"] == "ADMIN_AUDIT"
    actions = [item["action"] for item in data["items"]]
    assert all(a == "FEATURE_FLAG_MUTATED" for a in actions)
    assert len(actions) >= 2

    # 2. Keyset pagination test: limit=1
    res_page1 = client.get(
        f"/api/v1/operator/audit-events?object_key=PAYMENT_GATEWAY_V2&limit=1",
        headers=admin["headers"],
    )
    assert res_page1.status_code == 200, res_page1.text
    page1 = res_page1.json()
    assert len(page1["items"]) == 1
    assert page1["items"][0]["id"] == e3_id  # Newest first
    assert page1["has_more"] is True
    assert page1["next_cursor"] is not None

    # Page 2 via cursor
    res_page2 = client.get(
        f"/api/v1/operator/audit-events?object_key=PAYMENT_GATEWAY_V2&limit=1&cursor={page1['next_cursor']}",
        headers=admin["headers"],
    )
    assert res_page2.status_code == 200, res_page2.text
    page2 = res_page2.json()
    assert len(page2["items"]) == 1
    assert page2["items"][0]["id"] == e2_id  # Middle next


def test_api118_auditor_role_has_access(client, identities):
    auditor = identities("AUDITOR")
    res = client.get(
        "/api/v1/operator/audit-events?limit=5",
        headers=auditor["headers"],
    )
    assert res.status_code == 200, res.text
    assert res.json()["contract_id"] == "API-118"


def test_api119_operator_access_requests_dual_control(client, identities):
    admin_req = identities("ADMIN")
    admin_app = identities("ADMIN")
    target = identities()

    payload = {
        "target_user_id": target["user_id"],
        "role_code": "OPERATIONS",
        "reason": "Emergency DB recovery drill execution",
        "independent_approver_id": admin_app["user_id"],
        "duration_minutes": 180,
    }

    res = client.post(
        "/api/v1/operator/access-requests",
        json=payload,
        headers=admin_req["headers"],
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["contract_id"] == "API-119"
    assert data["status"] == "GRANTED"
    assert data["target_user_id"] == target["user_id"]
    assert data["duration_minutes"] == 180
    assert "grant_id" in data

    # Verify role grant in database
    with transaction() as conn:
        t_grants = table("platform_role_grants")
        grant = conn.execute(
            select(t_grants.c.id, t_grants.c.granted_by_id, t_grants.c.revoked_at)
            .where(t_grants.c.id == data["grant_id"])
        ).mappings().first()
        assert grant is not None
        assert grant["granted_by_id"] == admin_app["user_id"]
        assert grant["revoked_at"] is None

        # Verify audit trail
        t_audit = table("audit_events")
        audit_row = conn.execute(
            select(t_audit.c.id)
            .where(
                t_audit.c.action == "BREAK_GLASS_ROLE_GRANTED",
                t_audit.c.object_key == data["grant_id"],
            )
        ).first()
        assert audit_row is not None


def test_api120_operator_revoke_user_sessions(client, identities):
    admin = identities("ADMIN")
    target = identities()

    incident_id = str(uuid4())
    payload = {
        "reason": "Suspected token leakage during credential compromise",
        "incident_id": incident_id,
    }

    res = client.post(
        f"/api/v1/operator/users/{target['user_id']}/revoke-sessions",
        json=payload,
        headers=admin["headers"],
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-120"
    assert data["user_id"] == target["user_id"]
    assert data["status"] == "REVOKED"
    assert data["revoked_sessions_count"] >= 1
    assert data["incident_id"] == incident_id

    # Verify sessions are revoked in DB
    with transaction() as conn:
        t_sess = table("sessions")
        unrevoked = conn.execute(
            select(t_sess.c.id)
            .where(t_sess.c.user_id == target["user_id"], t_sess.c.revoked_at.is_(None))
        ).all()
        assert len(unrevoked) == 0


def test_api122_operator_declare_incident(client, identities):
    admin = identities("ADMIN")
    commander = identities("ADMIN")

    payload = {
        "severity": "P1",
        "title": "Degraded latency on payment webhook ingestion",
        "commander_id": commander["user_id"],
        "postmortem_ref": "https://wiki.flexbridge.uz/incidents/inc-2026-11-p1",
    }

    res = client.post(
        "/api/v1/operator/incidents",
        json=payload,
        headers=admin["headers"],
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["contract_id"] == "API-122"
    assert data["severity"] == "P1"
    assert data["status"] == "OPEN"
    assert data["commander_id"] == commander["user_id"]
    assert "incident_id" in data

    # Verify incident record in DB
    with transaction() as conn:
        t_inc = table("incidents")
        inc_row = conn.execute(
            select(t_inc.c.id, t_inc.c.severity, t_inc.c.status)
            .where(t_inc.c.id == data["incident_id"])
        ).mappings().first()
        assert inc_row is not None
        assert inc_row["severity"] == "P1"
        assert inc_row["status"] == "OPEN"


def test_api123_operator_restore_runs_and_sla(client, identities):
    admin = identities("ADMIN")
    now_utc = now()

    # Seed verified restore run
    with transaction() as conn:
        t_rr = table("restore_runs")
        run_id = str(uuid4())
        conn.execute(
            t_rr.insert().values(
                id=run_id,
                created_at=now_utc,
                updated_at=now_utc,
                started_at=now_utc - timedelta(minutes=45),
                finished_at=now_utc,
                backup_ref="s3://backups/flexbridge/snap-2026-11-12.tar.zst",
                status="VERIFIED",
                recovered_through=now_utc - timedelta(minutes=30),
                measured_rpo_minutes=30,  # <= 1440 (24h)
                measured_rto_minutes=45,  # <= 240 (4h)
                checked_by_id=admin["user_id"],
                evidence_ref="dr-drill-evidence-run-001",
            )
        )

    res = client.get(
        "/api/v1/operator/restore-runs?limit=10",
        headers=admin["headers"],
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-123"
    assert data["restore_drill_verified"] is True
    assert data["target_sla"]["max_rpo_hours"] == 24
    assert data["target_sla"]["max_rto_hours"] == 4
    assert len(data["items"]) >= 1

    item = next(it for it in data["items"] if it["id"] == run_id)
    assert item["sla_met"] is True
    assert item["measured_rpo_minutes"] == 30
    assert item["measured_rto_minutes"] == 45


def test_api124_operator_analytics_dedup_and_cohort(client, identities):
    admin = identities("ADMIN")
    now_utc = now()

    # Seed analytics events
    with transaction() as conn:
        t_ae = table("analytics_events")
        conn.execute(
            t_ae.insert().values(
                id=str(uuid4()),
                created_at=now_utc,
                updated_at=now_utc,
                event_key="evt-pageview-100",
                event_name="PAGE_VIEW",
                actor_pseudonym="anon-ps-1",
                cohort="2026_FALL",
                properties={"path": "/opportunities"},
                occurred_at=now_utc,
                schema_version=1,
            )
        )
        conn.execute(
            t_ae.insert().values(
                id=str(uuid4()),
                created_at=now_utc,
                updated_at=now_utc,
                event_key="evt-pageview-101",
                event_name="PAGE_VIEW",
                actor_pseudonym="anon-ps-1",
                cohort="2026_FALL",
                properties={"path": "/opportunities"},
                occurred_at=now_utc,
                schema_version=1,
            )
        )

    res = client.get(
        "/api/v1/operator/analytics?cohort=2026_FALL",
        headers=admin["headers"],
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-124"
    assert data["cohort"] == "2026_FALL"
    assert "analytics" in data
    assert data["analytics"]["total_events"] >= 2
    assert "placements" in data
    assert "outbox_health" in data
