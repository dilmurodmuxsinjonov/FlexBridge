"""Adversarial and security boundary tests for Operator Support & Privacy (API-112, API-113, API-114)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def test_adversarial_unauthenticated_requests_denied_401(client):
    random_uuid = str(uuid4())
    # API-112
    res = client.get("/api/v1/operator/support-tickets")
    assert res.status_code == 401, res.text

    # API-113
    res = client.post(f"/api/v1/operator/support-tickets/{random_uuid}/messages", json={"body": "Hello"})
    assert res.status_code == 401, res.text

    # API-114
    res = client.post(f"/api/v1/operator/privacy-requests/{random_uuid}/resolve", json={"status": "RESOLVED", "reason": "Test reason"})
    assert res.status_code == 401, res.text


def test_adversarial_non_staff_actors_forbidden_403(client, identities):
    user = identities()  # regular candidate
    random_uuid = str(uuid4())

    # API-112
    res = client.get("/api/v1/operator/support-tickets", headers=user["headers"])
    assert res.status_code == 403, res.text
    err = res.json()["detail"]
    assert err["code"] == "PERMISSION_DENIED"

    # API-113
    res = client.post(
        f"/api/v1/operator/support-tickets/{random_uuid}/messages",
        headers=user["headers"],
        json={"body": "Unauthorized message"},
    )
    assert res.status_code == 403, res.text
    err = res.json()["detail"]
    assert err["code"] == "PERMISSION_DENIED"

    # API-114
    res = client.post(
        f"/api/v1/operator/privacy-requests/{random_uuid}/resolve",
        headers=user["headers"],
        json={"status": "RESOLVED", "reason": "Unauthorized resolution attempt"},
    )
    assert res.status_code == 403, res.text
    err = res.json()["detail"]
    assert err["code"] == "PERMISSION_DENIED"


def test_adversarial_self_resolution_forbidden_403(client, identities):
    operator = identities("SUPPORT")

    # Operator creates a personal privacy request
    req = client.post(
        "/api/v1/me/privacy-requests",
        headers=operator["headers"],
        json={"kind": "EXPORT", "reason": "Operator personal data export"},
    ).json()

    # Operator attempts to resolve own privacy request
    res = client.post(
        f"/api/v1/operator/privacy-requests/{req['id']}/resolve",
        headers=operator["headers"],
        json={"status": "RESOLVED", "reason": "Self-approving my personal privacy export"},
    )
    assert res.status_code == 403, res.text
    err = res.json()["detail"]
    assert err["code"] == "SELF_RESOLUTION_FORBIDDEN"


def test_adversarial_nonexistent_uniform_404(client, identities):
    operator = identities("SUPPORT")
    random_uuid = str(uuid4())

    # API-113 nonexistent ticket
    res = client.post(
        f"/api/v1/operator/support-tickets/{random_uuid}/messages",
        headers=operator["headers"],
        json={"body": "Message to void"},
    )
    assert res.status_code == 404, res.text
    err = res.json()["detail"]
    assert err["code"] == "TICKET_NOT_FOUND"

    # API-114 nonexistent privacy request
    res = client.post(
        f"/api/v1/operator/privacy-requests/{random_uuid}/resolve",
        headers=operator["headers"],
        json={"status": "RESOLVED", "reason": "Resolving void"},
    )
    assert res.status_code == 404, res.text
    err = res.json()["detail"]
    assert err["code"] == "PRIVACY_REQUEST_NOT_FOUND"


def test_adversarial_already_resolved_privacy_request_conflict_409(client, identities):
    operator = identities("SUPPORT")
    user = identities()

    req = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT", "reason": "Initial request"},
    ).json()

    # First resolution: success
    res1 = client.post(
        f"/api/v1/operator/privacy-requests/{req['id']}/resolve",
        headers=operator["headers"],
        json={"status": "RESOLVED", "reason": "Properly resolved"},
    )
    assert res1.status_code == 200, res1.text

    # Second resolution attempt on resolved request: 409 Conflict
    res2 = client.post(
        f"/api/v1/operator/privacy-requests/{req['id']}/resolve",
        headers=operator["headers"],
        json={"status": "REJECTED", "reason": "Trying to reject after resolving"},
    )
    assert res2.status_code == 409, res2.text
    err = res2.json()["detail"]
    assert err["code"] == "PRIVACY_REQUEST_ALREADY_RESOLVED"


def test_adversarial_legal_hold_blocks_privacy_request_deletion_resolution_409(client, identities):
    operator = identities("SUPPORT")
    moderator = identities("MODERATOR")
    user = identities()

    # User submits DELETE privacy request
    req = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "DELETE", "reason": "Account erasure request"},
    ).json()

    # Now, an active legal hold is placed on user
    now_utc = now()
    with transaction() as conn:
        insert_row(
            conn,
            "legal_holds",
            id=str(uuid4()),
            created_at=now_utc,
            updated_at=now_utc,
            user_id=user["user_id"],
            organization_id=None,
            case_id=None,
            reason="Court litigation hold against user records",
            authorized_by_id=moderator["user_id"],
            expires_at=now_utc + timedelta(days=90),
            released_at=None,
        )

    # Operator attempts to RESOLVE the deletion request -> blocked by legal hold
    res = client.post(
        f"/api/v1/operator/privacy-requests/{req['id']}/resolve",
        headers=operator["headers"],
        json={"status": "RESOLVED", "reason": "Attempting to erase data subject"},
    )
    assert res.status_code == 409, res.text
    err = res.json()["detail"]
    assert err["code"] == "LEGAL_HOLD_ACTIVE"
    assert "Court litigation hold" in err["message"]


def test_adversarial_closed_ticket_rejects_messages_unless_reopened_409(client, identities):
    operator = identities("SUPPORT")
    user = identities()

    t = client.post(
        "/api/v1/me/support-tickets",
        headers=user["headers"],
        json={"subject": "Short-lived inquiry", "body": "Close this ticket please."},
    ).json()

    # Operator closes ticket
    res_close = client.post(
        f"/api/v1/operator/support-tickets/{t['id']}/messages",
        headers=operator["headers"],
        json={"body": "Closing ticket now.", "status": "CLOSED"},
    )
    assert res_close.status_code == 201, res_close.text

    # Attempting to post message without reopening -> 409 TICKET_CLOSED
    res_fail = client.post(
        f"/api/v1/operator/support-tickets/{t['id']}/messages",
        headers=operator["headers"],
        json={"body": "New message on closed ticket without status change"},
    )
    assert res_fail.status_code == 409, res_fail.text
    err = res_fail.json()["detail"]
    assert err["code"] == "TICKET_CLOSED"

    # Reopening ticket with status=IN_PROGRESS succeeds
    res_reopen = client.post(
        f"/api/v1/operator/support-tickets/{t['id']}/messages",
        headers=operator["headers"],
        json={"body": "Reopening ticket for further investigation.", "status": "IN_PROGRESS"},
    )
    assert res_reopen.status_code == 201, res_reopen.text
    assert res_reopen.json()["ticket_status"] == "IN_PROGRESS"


def test_adversarial_invalid_input_payloads_422(client, identities):
    operator = identities("SUPPORT")
    random_uuid = str(uuid4())

    # Invalid cursor
    res_cursor = client.get("/api/v1/operator/support-tickets?cursor=NOT_BASE64_GARBAGE!@", headers=operator["headers"])
    assert res_cursor.status_code == 422, res_cursor.text
    assert res_cursor.json()["detail"]["code"] == "INVALID_CURSOR"

    # Empty body
    res_body = client.post(
        f"/api/v1/operator/support-tickets/{random_uuid}/messages",
        headers=operator["headers"],
        json={"body": "   "},
    )
    assert res_body.status_code in (422,), res_body.text

    # Short reason for privacy resolution
    res_reason = client.post(
        f"/api/v1/operator/privacy-requests/{random_uuid}/resolve",
        headers=operator["headers"],
        json={"status": "RESOLVED", "reason": "abc"},
    )
    assert res_reason.status_code == 422, res_reason.text
