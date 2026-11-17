"""Tests for User Privacy Requests (API-062 / CAP-032 / DB-082 / DB-084 / AC-031)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.db.storage import now, table, transaction
from app.services.placements import insert_row


def test_privacy_requests_canonical_contract_and_schema(client, identities):
    user = identities()
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT", "reason": "GDPR Article 20 data portability request"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["kind"] == "EXPORT"
    assert data["status"] == "PENDING"
    assert data["user_id"] == user["user_id"]
    assert "id" in data
    assert "due_at" in data
    assert "created_at" in data

    # Verify due_at is approximately 30 days from created_at
    created_dt = datetime.fromisoformat(data["created_at"])
    due_dt = datetime.fromisoformat(data["due_at"])
    delta_days = (due_dt - created_dt).total_seconds() / 86400
    assert 29 <= delta_days <= 31


def test_create_export_privacy_request_success(client, identities):
    user = identities()
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["kind"] == "EXPORT"
    assert data["status"] == "PENDING"


def test_create_delete_privacy_request_success_when_no_legal_hold(client, identities):
    user = identities()
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "DELETE", "reason": "Account closure right to erasure"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["kind"] == "DELETE"
    assert data["status"] == "PENDING"


def test_create_rectify_privacy_request_success(client, identities):
    user = identities()
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "RECTIFY", "reason": "Correction of misspelled legal family name"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["kind"] == "RECTIFY"
    assert data["status"] == "PENDING"


def test_legal_hold_blocks_delete_privacy_request(client, identities):
    user = identities()
    moderator = identities("MODERATOR")

    now_utc = now()
    # Insert an active legal hold on user
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
            reason="Investigation regarding placement contract dispute",
            authorized_by_id=moderator["user_id"],
            expires_at=now_utc + timedelta(days=90),
            released_at=None,
        )

    # Attempt DELETE privacy request
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "DELETE", "reason": "Delete all my data"},
    )
    assert res.status_code == 422, res.text
    err = res.json()["detail"]
    assert err["code"] == "LEGAL_HOLD_ACTIVE"
    assert "Investigation regarding placement contract dispute" in err["message"]


def test_legal_hold_does_not_block_export_privacy_request(client, identities):
    user = identities()
    moderator = identities("MODERATOR")

    now_utc = now()
    # Insert an active legal hold on user
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
            reason="Auditing compliance hold",
            authorized_by_id=moderator["user_id"],
            expires_at=now_utc + timedelta(days=60),
            released_at=None,
        )

    # EXPORT request is allowed even when legal hold is active (access right vs deletion)
    res = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["kind"] == "EXPORT"


def test_anti_duplication_blocks_concurrent_pending_request(client, identities):
    user = identities()

    # First request
    res1 = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT"},
    )
    assert res1.status_code == 201, res1.text

    # Second duplicate request while first is PENDING
    res2 = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT"},
    )
    assert res2.status_code == 409, res2.text
    err = res2.json()["detail"]
    assert err["code"] == "PRIVACY_REQUEST_ALREADY_PENDING"


def test_get_my_privacy_requests_with_filtering_and_pagination(client, identities):
    user = identities()

    # Create EXPORT
    r1 = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "EXPORT"},
    )
    assert r1.status_code == 201

    # Create RECTIFY
    r2 = client.post(
        "/api/v1/me/privacy-requests",
        headers=user["headers"],
        json={"kind": "RECTIFY", "reason": "Fix phone number"},
    )
    assert r2.status_code == 201

    # Get all
    get_res = client.get("/api/v1/me/privacy-requests", headers=user["headers"])
    assert get_res.status_code == 200, get_res.text
    body = get_res.json()
    assert body["total"] >= 2
    kinds = [item["kind"] for item in body["items"]]
    assert "EXPORT" in kinds
    assert "RECTIFY" in kinds

    # Filter by kind
    filtered = client.get("/api/v1/me/privacy-requests?kind=RECTIFY", headers=user["headers"])
    assert filtered.status_code == 200
    f_body = filtered.json()
    assert f_body["total"] == 1
    assert f_body["items"][0]["kind"] == "RECTIFY"
