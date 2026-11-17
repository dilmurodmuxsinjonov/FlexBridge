"""Functional contract tests for Operator Support Queue & Privacy Request Resolution.

Contracts:
- API-112: GET /api/v1/operator/support-tickets (CAP-034 / SUPPORT)
- API-113: POST /api/v1/operator/support-tickets/{id}/messages (CAP-034 / SUPPORT)
- API-114: POST /api/v1/operator/privacy-requests/{id}/resolve (CAP-035 / PRIVACY)
"""
from uuid import uuid4
import pytest
from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def test_api112_operator_support_tickets_queue_and_keyset_cursor(client, identities):
    operator = identities("SUPPORT")
    user = identities()

    # Create several tickets with different categories and priorities
    t1 = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Queue ticket 1", "body": "Body for ticket 1", "category": "TECHNICAL", "priority": "URGENT"},
    ).json()

    t2 = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Queue ticket 2", "body": "Body for ticket 2", "category": "BILLING", "priority": "NORMAL"},
    ).json()

    t3 = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Queue ticket 3", "body": "Body for ticket 3", "category": "TECHNICAL", "priority": "LOW"},
    ).json()

    # Query queue without filter
    res = client.get("/api/v1/operator/support-tickets?limit=100", headers=operator["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["contract_id"] == "API-112"
    assert data["capability"] == "SUPPORT"
    assert data["total"] >= 3
    ticket_ids = [item["id"] for item in data["items"]]
    assert t1["id"] in ticket_ids
    assert t2["id"] in ticket_ids
    assert t3["id"] in ticket_ids

    # Query with category filter
    res_tech = client.get("/api/v1/operator/support-tickets?category=TECHNICAL", headers=operator["headers"])
    assert res_tech.status_code == 200, res_tech.text
    data_tech = res_tech.json()
    for item in data_tech["items"]:
        assert item["category"] == "TECHNICAL"

    # Query with priority filter
    res_urg = client.get("/api/v1/operator/support-tickets?priority=URGENT", headers=operator["headers"])
    assert res_urg.status_code == 200, res_urg.text
    data_urg = res_urg.json()
    for item in data_urg["items"]:
        assert item["priority"] == "URGENT"

    # Keyset cursor pagination: limit=2
    res_p1 = client.get("/api/v1/operator/support-tickets?limit=2", headers=operator["headers"])
    assert res_p1.status_code == 200, res_p1.text
    p1 = res_p1.json()
    assert len(p1["items"]) == 2
    assert p1["has_more"] is True
    assert p1["next_cursor"] is not None

    # Fetch second page with cursor
    res_p2 = client.get(f"/api/v1/operator/support-tickets?limit=2&cursor={p1['next_cursor']}", headers=operator["headers"])
    assert res_p2.status_code == 200, res_p2.text
    p2 = res_p2.json()
    assert len(p2["items"]) >= 1

    p1_ids = {it["id"] for it in p1["items"]}
    p2_ids = {it["id"] for it in p2["items"]}
    assert p1_ids.isdisjoint(p2_ids)


def test_api113_operator_support_ticket_public_message_and_status_update(client, identities):
    operator = identities("SUPPORT")
    user = identities()

    # User creates ticket
    t = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Inquiry about interview slot", "body": "Can I reschedule my interview slot?"},
    ).json()

    # Operator replies publicly (internal=False), flips status to PENDING_USER
    reply_res = client.post(
        f"/api/v1/operator/support-tickets/{t['id']}/messages",
        headers=operator["headers"],
        json={"body": "Yes, you can reschedule via your application dashboard.", "internal": False},
    )
    assert reply_res.status_code == 201, reply_res.text
    reply_data = reply_res.json()
    assert reply_data["contract_id"] == "API-113"
    assert reply_data["capability"] == "SUPPORT"
    assert reply_data["ticket_id"] == t["id"]
    assert reply_data["author_id"] == operator["user_id"]
    assert reply_data["internal"] is False
    assert reply_data["ticket_status"] == "PENDING_USER"

    # Operator explicitly resolves ticket
    resolve_res = client.post(
        f"/api/v1/operator/support-tickets/{t['id']}/messages",
        headers=operator["headers"],
        json={"body": "Closing ticket upon confirmation.", "status": "RESOLVED"},
    )
    assert resolve_res.status_code == 201, resolve_res.text
    resolve_data = resolve_res.json()
    assert resolve_data["ticket_status"] == "RESOLVED"


def test_api113_operator_internal_note_and_concealment(client, identities):
    operator = identities("SUPPORT")
    user = identities()

    t = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Sensitive verification question", "body": "Please verify passport upload."},
    ).json()

    # Operator writes internal note
    note_res = client.post(
        f"/api/v1/operator/support-tickets/{t['id']}/messages",
        headers=operator["headers"],
        json={"body": "INTERNAL NOTE: Document verified against national database.", "internal": True},
    )
    assert note_res.status_code == 201, note_res.text
    note_data = note_res.json()
    assert note_data["contract_id"] == "API-113"
    assert note_data["internal"] is True

    # User views messages: internal note MUST NOT be visible
    user_thread = client.get(f"/api/v1/support-tickets/{t['id']}/messages", headers=user["headers"]).json()
    user_bodies = [m["body"] for m in user_thread["messages"]]
    assert not any("INTERNAL NOTE" in b for b in user_bodies)

    # Operator views messages: internal note IS visible
    staff_thread = client.get(f"/api/v1/support-tickets/{t['id']}/messages", headers=operator["headers"]).json()
    staff_bodies = [m["body"] for m in staff_thread["messages"]]
    assert any("INTERNAL NOTE" in b for b in staff_bodies)


def test_api114_operator_privacy_request_resolve_success(client, identities):
    operator = identities("SUPPORT")
    user = identities()

    # User submits EXPORT privacy request
    req = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT", "reason": "Data export request under privacy laws"},
    ).json()

    # Operator resolves the request
    resolve_res = client.post(
        f"/api/v1/operator/privacy-requests/{req['id']}/resolve",
        headers=operator["headers"],
        json={"status": "RESOLVED", "reason": "Export archive produced and delivered via secure storage."},
    )
    assert resolve_res.status_code == 200, resolve_res.text
    res_data = resolve_res.json()
    assert res_data["contract_id"] == "API-114"
    assert res_data["capability"] == "PRIVACY"
    assert res_data["id"] == req["id"]
    assert res_data["status"] == "RESOLVED"
    assert res_data["resolved_at"] is not None
    assert "Export archive produced" in res_data["reason"]


def test_api114_operator_privacy_request_reject_success(client, identities):
    operator = identities("SUPPORT")
    user = identities()

    req = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "RECTIFY", "reason": "Please alter log audit timestamps"},
    ).json()

    # Operator rejects request
    reject_res = client.post(
        f"/api/v1/operator/privacy-requests/{req['id']}/resolve",
        headers=operator["headers"],
        json={"status": "REJECTED", "reason": "Audit timestamps are append-only immutable legal records."},
    )
    assert reject_res.status_code == 200, reject_res.text
    res_data = reject_res.json()
    assert res_data["contract_id"] == "API-114"
    assert res_data["status"] == "REJECTED"
    assert "immutable legal records" in res_data["reason"]
