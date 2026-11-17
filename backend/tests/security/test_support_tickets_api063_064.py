"""Contract and functional tests for Support Tickets & Messaging (API-063 / API-064 / CAP-033 / AC-032)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.db.storage import table, transaction


def test_create_ticket_canonical_contract_and_sla(client, identities):
    user = identities()
    res = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={
            "subject": "Platform billing reconciliation question",
            "body": "I need assistance verifying placement invoice #1042 for autumn cycle.",
            "category": "BILLING",
            "priority": "HIGH",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["category"] == "BILLING"
    assert data["priority"] == "HIGH"
    assert data["status"] == "OPEN"
    assert data["requester_id"] == user["user_id"]
    assert "first_response_due_at" in data

    # Verify HIGH priority SLA is approximately 12 hours from created_at
    created_dt = datetime.fromisoformat(data["created_at"])
    due_dt = datetime.fromisoformat(data["first_response_due_at"])
    delta_hours = (due_dt - created_dt).total_seconds() / 3600
    assert 11.5 <= delta_hours <= 12.5

    # Verify initial message structure
    initial_msg = data["initial_message"]
    assert initial_msg["author_id"] == user["user_id"]
    assert initial_msg["internal"] is False
    assert "invoice #1042" in initial_msg["body"]


def test_get_my_tickets_api063(client, identities):
    user = identities()

    # Create ticket 1
    t1 = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={
            "subject": "First technical issue ticket",
            "body": "Unable to upload diary log evidence file.",
            "category": "TECHNICAL",
            "priority": "NORMAL",
        },
    ).json()

    # Create ticket 2
    t2 = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={
            "subject": "Second placement query ticket",
            "body": "Question about mentor assignment schedule.",
            "category": "PLACEMENT",
            "priority": "LOW",
        },
    ).json()

    # Query API-063
    res = client.get("/api/v1/me/support-tickets", headers=user["headers"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["contract_id"] == "API-063"
    assert body["total"] >= 2

    ticket_ids = [item["id"] for item in body["items"]]
    assert t1["id"] in ticket_ids
    assert t2["id"] in ticket_ids

    # Verify message count is populated
    item1 = next(item for item in body["items"] if item["id"] == t1["id"])
    assert item1["messages_count"] >= 1


def test_post_user_message_api064(client, identities):
    user = identities()

    # Create ticket
    ticket = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={
            "subject": "Placement contract query",
            "body": "Initial request description for placement mentor.",
        },
    ).json()

    # User posts follow-up message
    msg_res = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=user["headers"],
        json={"body": "Adding additional information: placement mentor is confirmed."},
    )
    assert msg_res.status_code == 201, msg_res.text
    msg_data = msg_res.json()
    assert msg_data["ticket_id"] == ticket["id"]
    assert msg_data["author_id"] == user["user_id"]
    assert msg_data["internal"] is False
    assert msg_data["ticket_status"] == "PENDING_SUPPORT"


def test_post_support_staff_message_flips_to_pending_user(client, identities):
    user = identities()
    support_staff = identities("SUPPORT")

    ticket = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Inquiry about platform fees", "body": "Please explain monthly platform rates."},
    ).json()

    # Support staff replies publicly
    reply_res = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=support_staff["headers"],
        json={"body": "Hello, here is the official platform fee breakdown.", "internal": False},
    )
    assert reply_res.status_code == 201, reply_res.text
    reply_data = reply_res.json()
    assert reply_data["author_id"] == support_staff["user_id"]
    assert reply_data["ticket_status"] == "PENDING_USER"


def test_support_staff_can_post_internal_note(client, identities):
    user = identities()
    support_staff = identities("SUPPORT")

    ticket = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Account security review request", "body": "Need verification of second factor."},
    ).json()

    # Support staff posts an internal note
    note_res = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=support_staff["headers"],
        json={"body": "Operator note: User identity verified against passport registry.", "internal": True},
    )
    assert note_res.status_code == 201, note_res.text
    note_data = note_res.json()
    assert note_data["internal"] is True
    assert note_data["ticket_status"] == ticket["status"]  # Status not changed by internal note


def test_user_cannot_view_internal_notes(client, identities):
    user = identities()
    support_staff = identities("SUPPORT")

    ticket = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Confidential matter inquiry", "body": "My public ticket text."},
    ).json()

    # Staff posts internal note
    client.post(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=support_staff["headers"],
        json={"body": "PRIVATE_SECRET_OPERATOR_LOG: Do not reveal to user", "internal": True},
    )

    # User fetches thread
    user_thread = client.get(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=user["headers"],
    )
    assert user_thread.status_code == 200, user_thread.text
    messages = user_thread.json()["messages"]

    # Ensure no internal messages are delivered to requester (AC-032 / DB-081)
    for m in messages:
        assert m["internal"] is False
        assert "PRIVATE_SECRET_OPERATOR_LOG" not in m["body"]


def test_staff_can_view_all_messages_including_internal(client, identities):
    user = identities()
    support_staff = identities("SUPPORT")

    ticket = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Ticket for internal visibility check", "body": "Initial user text."},
    ).json()

    # Staff posts internal note
    client.post(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=support_staff["headers"],
        json={"body": "INTERNAL_STAFF_NOTE_VISIBLE_TO_SUPPORT", "internal": True},
    )

    # Staff fetches thread
    staff_thread = client.get(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=support_staff["headers"],
    )
    assert staff_thread.status_code == 200, staff_thread.text
    bodies = [m["body"] for m in staff_thread.json()["messages"]]
    assert any("INTERNAL_STAFF_NOTE_VISIBLE_TO_SUPPORT" in b for b in bodies)


def test_closed_ticket_rejects_new_messages_409(client, identities):
    user = identities()

    ticket = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Ticket to be closed", "body": "Text for ticket that will be closed."},
    ).json()

    # Mark ticket as CLOSED directly in database
    with transaction() as conn:
        t_tickets = table("support_tickets")
        conn.execute(
            t_tickets.update()
            .where(t_tickets.c.id == ticket["id"])
            .values(status="CLOSED")
        )

    # Attempt to post reply
    res = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/messages",
        headers=user["headers"],
        json={"body": "Trying to post to a closed ticket."},
    )
    assert res.status_code == 409, res.text
    err = res.json()["detail"]
    assert err["code"] == "TICKET_CLOSED"
