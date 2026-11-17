"""Adversarial and security tests for Privacy Requests (API-062 / DB-082 / DB-084)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def test_invalid_kind_rejected_422(client, identities):
    user = identities()
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "DESTROY_EVERYTHING"},
    )
    assert res.status_code == 422, res.text
    err = res.json()["detail"]
    assert err["code"] == "INVALID_PRIVACY_REQUEST_KIND"


def test_unauthenticated_request_rejected_401(client):
    res = client.post(
        "/api/v1/me/privacy-requests",
        json={"kind": "EXPORT"},
    )
    assert res.status_code == 401, res.text


def test_revoked_session_rejected_fail_closed(client, identities):
    user = identities()

    # Revoke session
    revoke_res = client.delete(
        f"/api/v1/me/sessions/{user['session_id']}",
        headers=user["headers"],
    )
    assert revoke_res.status_code == 200

    # Attempt request with revoked session
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT"},
    )
    assert res.status_code == 401, res.text


def test_cross_user_isolation(client, identities):
    user1 = identities()
    user2 = identities()

    # User 1 creates EXPORT request
    r1 = client.post(
        "/api/v1/me/privacy-requests",
        headers=user1["headers"],
        json={"kind": "EXPORT", "reason": "User 1 personal export"},
    )
    assert r1.status_code == 201
    req1_id = r1.json()["id"]

    # User 2 lists their privacy requests
    r2 = client.get(
        "/api/v1/me/privacy-requests",
        headers=user2["headers"],
    )
    assert r2.status_code == 200
    user2_items = r2.json()["items"]
    user2_ids = [item["id"] for item in user2_items]
    assert req1_id not in user2_ids


def test_released_or_expired_legal_hold_allows_deletion(client, identities):
    user = identities()
    moderator = identities("MODERATOR")

    now_utc = now()
    # Insert a legal hold that is already RELEASED
    with transaction() as conn:
        insert_row(
            conn,
            "legal_holds",
            id=str(uuid4()),
            created_at=now_utc - timedelta(days=60),
            updated_at=now_utc - timedelta(days=10),
            user_id=user["user_id"],
            organization_id=None,
            case_id=None,
            reason="Past resolved audit hold",
            authorized_by_id=moderator["user_id"],
            expires_at=now_utc + timedelta(days=30),
            released_at=now_utc - timedelta(days=10),  # Released!
        )

    # DELETE request succeeds because hold is released
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "DELETE"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["kind"] == "DELETE"


def test_audit_event_logged_on_privacy_request_creation(client, identities):
    user = identities()
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT", "reason": "Verification of audit logging"},
    )
    assert res.status_code == 201, res.text
    req_id = res.json()["id"]

    # Verify audit row exists in audit_events table
    with transaction() as conn:
        t_audit = table("audit_events")
        row = conn.execute(
            t_audit.select().where(
                t_audit.c.object_type == "privacy_request",
                t_audit.c.object_key == req_id,
                t_audit.c.action == "PRIVACY_REQUEST_CREATED",
            )
        ).mappings().first()

        assert row is not None
        assert str(row["actor_id"]) == user["user_id"]
