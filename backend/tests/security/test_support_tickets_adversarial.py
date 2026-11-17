"""Adversarial and boundary tests for Support Tickets (API-063 / API-064 / DB-080 / DB-081)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.db.storage import table, transaction


def test_unauthenticated_requests_rejected_401(client):
    # GET tickets without auth
    assert client.get("/api/v1/me/support-tickets").status_code == 401
    # POST ticket without auth
    assert client.post("/api/v1/me/support-tickets", json={"subject": "Test", "body": "Test body"}).status_code == 401
    # POST message without auth
    assert client.post(f"/api/v1/support-tickets/{uuid4()}/messages", json={"body": "Hello"}).status_code == 401


def test_user_cannot_post_internal_note_403(client, identities):
    user = identities()

    # Create ticket
    ticket = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Regular user ticket", "body": "Need standard account help."},
    ).json()

    # User attempts to post an internal note
    res = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=user["headers"],
        json={"body": "Attempting unauthorized internal note", "internal": True},
    )
    assert res.status_code == 403, res.text
    err = res.json()["detail"]
    assert err["code"] == "SUPPORT_TICKET_FORBIDDEN"


def test_cross_user_ticket_isolation_403(client, identities):
    user_a = identities()
    user_b = identities()

    # User A creates ticket
    ticket = client.post(
        "/api/v1/me/support-tickets",
        headers=user_a["headers"],
        json={"subject": "User A private ticket", "body": "User A private details."},
    ).json()

    # User B attempts to read messages
    get_res = client.get(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=user_b["headers"],
    )
    assert get_res.status_code == 403, get_res.text

    # User B attempts to post message
    post_res = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=user_b["headers"],
        json={"body": "User B intrusive message."},
    )
    assert post_res.status_code == 403, post_res.text


def test_invalid_category_or_priority_rejected_422(client, identities):
    user = identities()

    # Invalid category
    res1 = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={
            "subject": "Ticket with bad category",
            "body": "Body text here for validation test.",
            "category": "INVALID_CAT",
        },
    )
    assert res1.status_code == 422, res1.text
    assert res1.json()["detail"]["code"] == "INVALID_CATEGORY"

    # Invalid priority
    res2 = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={
            "subject": "Ticket with bad priority",
            "body": "Body text here for validation test.",
            "priority": "CRITICAL_SUPER",
        },
    )
    assert res2.status_code == 422, res2.text
    assert res2.json()["detail"]["code"] == "INVALID_PRIORITY"


def test_empty_subject_or_body_rejected_422(client, identities):
    user = identities()

    # Empty subject
    res1 = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "a", "body": "Valid body text here."},
    )
    assert res1.status_code == 422, res1.text

    # Empty body
    res2 = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Valid subject line", "body": "no"},
    )
    assert res2.status_code == 422, res2.text


def test_audit_event_logged_on_ticket_and_message_actions(client, identities):
    user = identities()

    ticket_res = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Audit check ticket", "body": "Body text for audit test."},
    )
    assert ticket_res.status_code == 201
    ticket_id = ticket_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/support-tickets/{ticket_id}/messages",
        headers=user["headers"],
        json={"body": "Follow-up message for audit test."},
    )
    assert msg_res.status_code == 201

    # Verify audit events table
    with transaction() as conn:
        t_audit = table("audit_events")

        # 1. Ticket created audit
        row1 = conn.execute(
            t_audit.select().where(
                t_audit.c.object_type == "support_ticket",
                t_audit.c.object_key == ticket_id,
                t_audit.c.action == "SUPPORT_TICKET_CREATED",
            )
        ).mappings().first()
        assert row1 is not None
        assert str(row1["actor_id"]) == user["user_id"]

        # 2. Message posted audit
        row2 = conn.execute(
            t_audit.select().where(
                t_audit.c.object_type == "support_ticket",
                t_audit.c.object_key == ticket_id,
                t_audit.c.action == "SUPPORT_MESSAGE_POSTED",
            )
        ).mappings().first()
        assert row2 is not None
        assert str(row2["actor_id"]) == user["user_id"]
