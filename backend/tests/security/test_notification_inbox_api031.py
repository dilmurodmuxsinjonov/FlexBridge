"""Functional tests for Canonical Notification Inbox (API-031 / CAP-031 / DB-085, DB-087, DB-088)."""

from uuid import uuid4
from datetime import timedelta
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def create_notification(conn, *, user_id, template_code, created_at=None, read_at=None,
                        opportunity_id=None, application_id=None, ticket_id=None, placement_id=None):
    stamp = created_at or now()
    event = insert_row(
        conn,
        "outbox_events",
        event_type="NOTICE_EVENT",
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
        event_id=event["id"],
        template_code=template_code,
        opportunity_id=opportunity_id,
        application_id=application_id,
        ticket_id=ticket_id,
        placement_id=placement_id,
        created_at=stamp,
        read_at=read_at,
    )


make_notification = create_notification


def test_unauthenticated_notifications_rejected(client):
    """API-031 / R-01: Requests without Authorization: Bearer token return 401 AUTH_REQUIRED."""
    res = client.get("/api/v1/me/notifications")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_get_notifications_empty_inbox(client, identities):
    """API-031: Fresh user has empty notification inbox with null next_after cursor."""
    user = identities()
    res = client.get("/api/v1/me/notifications", headers=user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["items"] == []
    assert data["next_after"] is None


def test_get_notifications_with_unread_and_read_items(client, identities):
    """API-031: unread_only=True filters out read notifications; unread_only=False returns all."""
    user = identities()
    stamp = now()

    with transaction() as conn:
        # Create unread notification
        n_unread = create_notification(
            conn,
            user_id=user["user_id"],
            template_code="SYSTEM_ALERT",
            created_at=stamp - timedelta(minutes=5),
            read_at=None,
        )
        # Create read notification
        n_read = create_notification(
            conn,
            user_id=user["user_id"],
            template_code="WELCOME_ONBOARDING",
            created_at=stamp - timedelta(minutes=10),
            read_at=stamp - timedelta(minutes=2),
        )

    # 1. Default (unread_only=True)
    res_default = client.get("/api/v1/me/notifications", headers=user["headers"])
    assert res_default.status_code == 200, res_default.text
    items_default = res_default.json()["items"]
    assert len(items_default) == 1
    assert items_default[0]["id"] == n_unread["id"]
    assert items_default[0]["is_read"] is False
    assert items_default[0]["read_at"] is None

    # 2. All notifications (unread_only=False)
    res_all = client.get("/api/v1/me/notifications?unread_only=false", headers=user["headers"])
    assert res_all.status_code == 200, res_all.text
    items_all = res_all.json()["items"]
    assert len(items_all) == 2
    item_ids = {i["id"] for i in items_all}
    assert n_unread["id"] in item_ids
    assert n_read["id"] in item_ids

    read_item = next(i for i in items_all if i["id"] == n_read["id"])
    assert read_item["is_read"] is True
    assert read_item["read_at"] is not None


def test_notification_scope_fields_returned(client, identities, organization):
    """API-031: Notifications expose linked entity scopes (opportunity, ticket)."""
    user = identities()

    # Create real support ticket
    t_res = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={
            "subject": "Notification scope test",
            "body": "Verifying linked entity scopes.",
            "category": "TECHNICAL",
            "priority": "LOW",
        },
    )
    assert t_res.status_code == 201, t_res.text
    ticket_id = t_res.json()["id"]

    with transaction() as conn:
        opp = insert_row(
            conn,
            "opportunities",
            organization_id=organization,
            kind="PART_TIME",
            status="PUBLISHED",
            capacity=1,
            occupied_count=0,
        )
        opp_id = opp["id"]

        n = create_notification(
            conn,
            user_id=user["user_id"],
            template_code="TICKET_REPLY_RECEIVED",
            opportunity_id=opp_id,
            ticket_id=ticket_id,
            created_at=now(),
        )

    res = client.get("/api/v1/me/notifications", headers=user["headers"])
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == n["id"]
    assert item["opportunity_id"] == opp_id
    assert item["ticket_id"] == ticket_id
    assert item["template_code"] == "TICKET_REPLY_RECEIVED"


def test_notification_read_marking_idempotent(client, identities):
    """API-031: POST /me/notifications/{id}/read marks notification read and repeat is idempotent."""
    user = identities()

    with transaction() as conn:
        n = create_notification(
            conn,
            user_id=user["user_id"],
            template_code="APPLICATION_OFFER",
            created_at=now(),
        )

    # Initially in unread inbox
    res1 = client.get("/api/v1/me/notifications", headers=user["headers"])
    assert len(res1.json()["items"]) == 1

    # Mark as read
    res_read = client.post(f"/api/v1/me/notifications/{n['id']}/read", headers=user["headers"])
    assert res_read.status_code == 200, res_read.text
    read_data = res_read.json()
    assert read_data["id"] == n["id"]
    assert read_data["read_at"] is not None

    # Idempotent repeat
    res_repeat = client.post(f"/api/v1/me/notifications/{n['id']}/read", headers=user["headers"])
    assert res_repeat.status_code == 200
    assert res_repeat.json()["read_at"] == read_data["read_at"]

    # Now excluded from unread-only inbox
    res2 = client.get("/api/v1/me/notifications", headers=user["headers"])
    assert len(res2.json()["items"]) == 0

    # Still present in full inbox
    res3 = client.get("/api/v1/me/notifications?unread_only=false", headers=user["headers"])
    assert len(res3.json()["items"]) == 1
    assert res3.json()["items"][0]["is_read"] is True


def test_notification_cross_user_isolation(client, identities):
    """API-031: User A cannot see or mark as read User B's notifications (IDOR protection)."""
    user_a = identities()
    user_b = identities()

    with transaction() as conn:
        n_b = create_notification(
            conn,
            user_id=user_b["user_id"],
            template_code="PRIVATE_USER_B_NOTICE",
            created_at=now(),
        )

    # User A's inbox is empty
    res_a = client.get("/api/v1/me/notifications?unread_only=false", headers=user_a["headers"])
    assert res_a.json()["items"] == []

    # User A tries to mark User B's notification as read -> 404
    res_hack = client.post(f"/api/v1/me/notifications/{n_b['id']}/read", headers=user_a["headers"])
    assert res_hack.status_code == 404


def test_notification_keyset_cursor_pagination(client, identities):
    """API-031: Keyset cursor pagination correctly delivers sequential pages using after and limit."""
    user = identities()
    base_time = now()

    created_ids = []
    with transaction() as conn:
        for i in range(5):
            n = create_notification(
                conn,
                user_id=user["user_id"],
                template_code=f"BATCH_ITEM_{i}",
                created_at=base_time + timedelta(seconds=i * 10),
            )
            created_ids.append(n["id"])

    # Page 1: limit 2
    res_p1 = client.get("/api/v1/me/notifications?limit=2", headers=user["headers"])
    assert res_p1.status_code == 200, res_p1.text
    data_p1 = res_p1.json()
    assert len(data_p1["items"]) == 2
    assert data_p1["next_after"] is not None

    # Page 2: after page 1 cursor
    cursor1 = data_p1["next_after"]
    res_p2 = client.get(f"/api/v1/me/notifications?limit=2&after={cursor1}", headers=user["headers"])
    assert res_p2.status_code == 200, res_p2.text
    data_p2 = res_p2.json()
    assert len(data_p2["items"]) == 2
    assert data_p2["next_after"] is not None

    # Verify no item duplication between page 1 and page 2
    ids_p1 = {i["id"] for i in data_p1["items"]}
    ids_p2 = {i["id"] for i in data_p2["items"]}
    assert ids_p1.isdisjoint(ids_p2)


def test_notification_invalid_cursor_rejected(client, identities):
    """API-031: Foreign cursor returns 404; malformed cursor returns 422."""
    user_a = identities()
    user_b = identities()

    with transaction() as conn:
        n_b = create_notification(
            conn,
            user_id=user_b["user_id"],
            template_code="USER_B_NOTICE",
            created_at=now(),
        )

    # Foreign cursor
    res_foreign = client.get(f"/api/v1/me/notifications?after={n_b['id']}", headers=user_a["headers"])
    assert res_foreign.status_code == 404

    # Malformed cursor
    res_malformed = client.get("/api/v1/me/notifications?after=not-a-valid-uuid", headers=user_a["headers"])
    assert res_malformed.status_code == 422


def test_notification_invalid_limit_rejected(client, identities):
    """API-031: Out-of-bounds limit (< 1 or > 100) returns 422."""
    user = identities()

    res_zero = client.get("/api/v1/me/notifications?limit=0", headers=user["headers"])
    assert res_zero.status_code == 422

    res_too_large = client.get("/api/v1/me/notifications?limit=101", headers=user["headers"])
    assert res_too_large.status_code == 422
