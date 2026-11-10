"""Adversarial and boundary test suite for Notification Preferences (API-059 / CAP-031 / DB-085 / DB-011 / AC-030).

Tests:
1. Invalid channel names (e.g. TELEGRAM, TIKTOK) rejected with 422.
2. Invalid purpose names (e.g. SPAM, ADVERTISING) rejected with 422.
3. Empty preferences list or missing field rejected with 422.
4. Cross-user isolation: User A's preference changes never alter User B's settings.
5. Sequential updates idempotently upsert without duplicate row violations.
6. Revoked session rejected fail-closed (401 Unauthorized).
"""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.storage import table, transaction


def test_invalid_channel_rejected_422(client, identities):
    """Boundary test: Unrecognized channel string returns 422 Unprocessable Entity."""
    user = identities()

    payload = {
        "preferences": [
            {"channel": "TELEGRAM", "purpose": "TRANSACTIONAL", "enabled": True}
        ]
    }
    res = client.put(
        "/api/v1/me/notification-preferences",
        json=payload,
        headers=user["headers"],
    )
    assert res.status_code == 422, res.text


def test_invalid_purpose_rejected_422(client, identities):
    """Boundary test: Unrecognized purpose string returns 422 Unprocessable Entity."""
    user = identities()

    payload = {
        "preferences": [
            {"channel": "EMAIL", "purpose": "PROMOTIONAL_SPAM", "enabled": True}
        ]
    }
    res = client.put(
        "/api/v1/me/notification-preferences",
        json=payload,
        headers=user["headers"],
    )
    assert res.status_code == 422, res.text


def test_empty_preferences_list_rejected_422(client, identities):
    """Boundary test: Empty list rejected with 422."""
    user = identities()

    res = client.put(
        "/api/v1/me/notification-preferences",
        json={"preferences": []},
        headers=user["headers"],
    )
    assert res.status_code == 422, res.text


def test_cross_user_isolation(client, identities):
    """Isolation test: Updating User A's preferences does not alter User B's preferences."""
    user_a = identities()
    user_b = identities()

    # User A disables MARKETING on EMAIL
    res_a = client.put(
        "/api/v1/me/notification-preferences",
        json={"preferences": [{"channel": "EMAIL", "purpose": "MARKETING", "enabled": False}]},
        headers=user_a["headers"],
    )
    assert res_a.status_code == 200, res_a.text

    # User B enables MARKETING on EMAIL
    res_b = client.put(
        "/api/v1/me/notification-preferences",
        json={"preferences": [{"channel": "EMAIL", "purpose": "MARKETING", "enabled": True}]},
        headers=user_b["headers"],
    )
    assert res_b.status_code == 200, res_b.text

    # Verify User A still has False
    res_a_check = client.get("/api/v1/me/notification-preferences", headers=user_a["headers"])
    pref_a = next(p for p in res_a_check.json()["preferences"] if p["channel"] == "EMAIL" and p["purpose"] == "MARKETING")
    assert pref_a["enabled"] is False

    # Verify User B still has True
    res_b_check = client.get("/api/v1/me/notification-preferences", headers=user_b["headers"])
    pref_b = next(p for p in res_b_check.json()["preferences"] if p["channel"] == "EMAIL" and p["purpose"] == "MARKETING")
    assert pref_b["enabled"] is True


def test_sequential_updates_upsert_no_duplicates(client, identities):
    """DB integrity test: Repeated updates to same (user_id, channel, purpose) do not duplicate rows."""
    user = identities()

    for flag in [True, False, True, False]:
        res = client.put(
            "/api/v1/me/notification-preferences",
            json={"preferences": [{"channel": "WHATSAPP", "purpose": "MARKETING", "enabled": flag}]},
            headers=user["headers"],
        )
        assert res.status_code == 200, res.text

    with transaction() as conn:
        t_pref = table("notification_preferences")
        count = conn.execute(
            select(func.count())
            .select_from(t_pref)
            .where(
                t_pref.c.user_id == user["user_id"],
                t_pref.c.channel == "WHATSAPP",
                t_pref.c.purpose == "MARKETING",
            )
        ).scalar_one()
        assert count == 1  # Exactly 1 row in DB (upsert succeeded)


def test_revoked_session_rejected_fail_closed(client, identities):
    """Security test: Revoked session fails closed with 401."""
    user = identities()

    # Revoke session in database
    with transaction() as conn:
        t_sessions = table("sessions")
        conn.execute(
            t_sessions.update()
            .where(t_sessions.c.id == user["session_id"])
            .values(revoked_at=func.now())
        )

    res = client.get("/api/v1/me/notification-preferences", headers=user["headers"])
    assert res.status_code == 401, res.text
