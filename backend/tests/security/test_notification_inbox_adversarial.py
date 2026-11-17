"""Adversarial security and invariant tests for Canonical Notification Inbox (API-031 / CAP-031).

Covers:
- Cross-tenant IDOR protection: User A cannot read, acknowledge, or probe User B's notifications.
- Cursor tampering & SQL injection resistance (keyset pagination boundaries).
- Audit trail atomicity & idempotency under repeated read acknowledgements.
- DoS prevention via strictly validated pagination limits (1..100).
- Bounded database queries (no N+1 query loop when reading notifications).
"""

from uuid import uuid4
from datetime import timedelta
import pytest
from sqlalchemy import select, event

from app.db.storage import get_engine, now, table, transaction
from app.services.placements import insert_row


def make_notification(conn, user_id, template_code="TEST_ALERT", created_at=None, read_at=None, **kwargs):
    stamp = created_at or now()
    evt = insert_row(
        conn,
        "outbox_events",
        event_type="NOTIFICATION_TRIGGERED",
        schema_version=1,
        aggregate_key=f"user:{user_id}",
        payload={},
        dedupe_key=str(uuid4()),
        available_at=stamp,
        processed_at=stamp,
        attempts=1,
    )
    return insert_row(
        conn,
        "notifications",
        user_id=user_id,
        event_id=evt["id"],
        template_code=template_code,
        created_at=stamp,
        read_at=read_at,
        **kwargs,
    )


def test_adversarial_cross_user_read_marking_exploit_blocked(client, identities):
    """API-031: Attacker (User A) targeting victim's (User B) notification ID receives 404, victim unread state unmodified."""
    victim = identities()
    attacker = identities()

    with transaction() as conn:
        victim_notice = make_notification(
            conn,
            user_id=victim["user_id"],
            template_code="SECURE_DOCUMENT_READY",
            read_at=None,
        )

    # Attacker attempts to mark victim's notification as read
    res_exploit = client.post(
        f"/api/v1/me/notifications/{victim_notice['id']}/read",
        headers=attacker["headers"],
    )
    assert res_exploit.status_code == 404, res_exploit.text

    # Verify victim's notification remains unread in database
    with transaction() as conn:
        t_n = table("notifications")
        row = conn.execute(
            select(t_n).where(t_n.c.id == victim_notice["id"])
        ).mappings().one()
        assert row["read_at"] is None

    # Verify victim still sees it in unread inbox
    res_victim = client.get("/api/v1/me/notifications", headers=victim["headers"])
    assert res_victim.status_code == 200
    victim_items = res_victim.json()["items"]
    assert any(i["id"] == victim_notice["id"] for i in victim_items)


def test_adversarial_cursor_tampering_and_sql_injection(client, identities):
    """API-031: Tampered cursor with other tenant ID returns 404; SQL injection returns 422."""
    user_a = identities()
    user_b = identities()

    with transaction() as conn:
        notice_b = make_notification(
            conn,
            user_id=user_b["user_id"],
            template_code="USER_B_PRIVATE",
        )

    # 1. Attacker uses victim's notification ID as cursor -> 404 PAGE_CURSOR_NOT_FOUND
    res_probe = client.get(
        f"/api/v1/me/notifications?after={notice_b['id']}",
        headers=user_a["headers"],
    )
    assert res_probe.status_code == 404

    # 2. SQL injection strings as cursor -> 422
    injections = [
        "123e4567-e89b-12d3-a456-426614174000' OR '1'='1",
        "../../bad/path",
        "; DROP TABLE notifications; --",
        "00000000-0000-0000-0000-000000000000%00",
    ]
    for inj in injections:
        res_inj = client.get(
            f"/api/v1/me/notifications?after={inj}",
            headers=user_a["headers"],
        )
        assert res_inj.status_code == 422


def test_adversarial_dos_pagination_limits(client, identities):
    """API-031: Limit parameters outside 1..100 boundary rejected with 422."""
    user = identities()

    invalid_limits = [-10, 0, 101, 1000, 9999999999, "max", "null"]
    for lim in invalid_limits:
        res = client.get(f"/api/v1/me/notifications?limit={lim}", headers=user["headers"])
        assert res.status_code == 422


def test_adversarial_audit_log_atomicity_on_idempotent_read(client, identities):
    """API-031: Exactly one audit_event record generated even when read acknowledged repeatedly."""
    user = identities()

    with transaction() as conn:
        n = make_notification(
            conn,
            user_id=user["user_id"],
            template_code="IDEMPOTENCY_CHECK",
            read_at=None,
        )

    # First read
    r1 = client.post(f"/api/v1/me/notifications/{n['id']}/read", headers=user["headers"])
    assert r1.status_code == 200
    read_stamp_1 = r1.json()["read_at"]

    # Second read (replay)
    r2 = client.post(f"/api/v1/me/notifications/{n['id']}/read", headers=user["headers"])
    assert r2.status_code == 200
    read_stamp_2 = r2.json()["read_at"]
    assert read_stamp_1 == read_stamp_2

    # Third read (replay)
    r3 = client.post(f"/api/v1/me/notifications/{n['id']}/read", headers=user["headers"])
    assert r3.status_code == 200
    assert r3.json()["read_at"] == read_stamp_1

    # Check audit_events table: exactly ONE NOTIFICATION_READ event
    with transaction() as conn:
        t_audit = table("audit_events")
        audit_records = conn.execute(
            select(t_audit).where(
                t_audit.c.action == "NOTIFICATION_READ",
                t_audit.c.object_type == "notification",
                t_audit.c.object_key == str(n["id"]),
            )
        ).mappings().all()
        assert len(audit_records) == 1
        assert audit_records[0]["actor_id"] == user["user_id"]


def test_adversarial_bounded_queries_no_n_plus_one(client, identities):
    """API-031: Fetching notification page executes bounded single query, not N+1 loop."""
    user = identities()
    base_time = now()

    with transaction() as conn:
        for i in range(10):
            make_notification(
                conn,
                user_id=user["user_id"],
                template_code=f"BATCH_{i}",
                created_at=base_time + timedelta(seconds=i),
            )

    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = get_engine()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        res = client.get("/api/v1/me/notifications?limit=10&unread_only=false", headers=user["headers"])
        assert res.status_code == 200
        assert len(res.json()["items"]) == 10
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    # Filter out transaction / session checks, count notification queries
    notification_queries = [s for s in statements if "flexbridge.notifications" in s.lower() or "notifications" in s.lower()]
    # There should only be 1 query for fetching the notifications page (not 10 individual queries)
    assert len(notification_queries) <= 2, f"Expected <= 2 notification queries, got {len(notification_queries)}"
