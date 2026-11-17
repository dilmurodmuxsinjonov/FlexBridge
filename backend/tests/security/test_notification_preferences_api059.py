"""Security, contract, and consent tests for Notification Preferences (API-059 / CAP-031 / DB-085 / DB-011 / AC-030).

Verifies:
1. Canonical Contract ID API-059 (PUT /api/v1/me/notification-preferences).
2. GET /api/v1/me/notification-preferences returns current preferences merged with default channels.
3. Updating preferences (EMAIL, SMS, PUSH, WHATSAPP) persists atomically.
4. AC-030: Marketing opt-in/opt-out records explicit legal consent events in consent_events (DB-011).
5. AC-030: Critical delivery safety: Disabling TRANSACTIONAL notifications across all channels rejected (422).
6. AC-030: Critical delivery safety: Disabling SECURITY notifications across all channels rejected (422).
7. Append-only audit store logs NOTIFICATION_PREFERENCES_UPDATED event.
8. Unauthenticated requests strictly rejected (401 Unauthorized).
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.storage import table, transaction


def test_notification_preferences_canonical_contract_and_schema(client, identities):
    """API-059 / CAP-031: PUT /api/v1/me/notification-preferences returns 200 with canonical schema."""
    user = identities()

    payload = {
        "preferences": [
            {"channel": "EMAIL", "purpose": "TRANSACTIONAL", "enabled": True},
            {"channel": "EMAIL", "purpose": "MARKETING", "enabled": True},
            {"channel": "SMS", "purpose": "SECURITY", "enabled": True},
        ]
    }

    res = client.put(
        "/api/v1/me/notification-preferences",
        json=payload,
        headers=user["headers"],
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["contract_id"] == "API-059"
    assert data["user_id"] == user["user_id"]
    assert data["status"] == "UPDATED"
    assert len(data["preferences"]) == 3

    # Verify marketing item received a linked consent_event_id
    marketing_item = next(p for p in data["preferences"] if p["purpose"] == "MARKETING")
    assert marketing_item["consent_event_id"] is not None


def test_get_notification_preferences_returns_defaults_merged(client, identities):
    """GET /api/v1/me/notification-preferences returns effective preferences including system defaults."""
    user = identities()

    res = client.get("/api/v1/me/notification-preferences", headers=user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["contract_id"] == "API-059"
    assert data["user_id"] == user["user_id"]
    assert len(data["preferences"]) >= 5

    # By default, EMAIL + TRANSACTIONAL is enabled, while MARKETING is disabled
    email_trans = next(p for p in data["preferences"] if p["channel"] == "EMAIL" and p["purpose"] == "TRANSACTIONAL")
    assert email_trans["enabled"] is True

    email_mkt = next(p for p in data["preferences"] if p["channel"] == "EMAIL" and p["purpose"] == "MARKETING")
    assert email_mkt["enabled"] is False


def test_marketing_consent_tracking_opt_in_and_opt_out(client, identities):
    """AC-030 / DB-011: Marketing opt-in records GRANTED and opt-out records REVOKED in consent_events."""
    user = identities()

    # 1. Opt-in to marketing
    res1 = client.put(
        "/api/v1/me/notification-preferences",
        json={"preferences": [{"channel": "EMAIL", "purpose": "MARKETING", "enabled": True}]},
        headers=user["headers"],
    )
    assert res1.status_code == 200, res1.text
    consent_id_1 = res1.json()["preferences"][0]["consent_event_id"]
    assert consent_id_1 is not None

    with transaction() as conn:
        t_consent = table("consent_events")
        row1 = conn.execute(
            select(t_consent).where(t_consent.c.id == consent_id_1)
        ).mappings().first()
        assert row1 is not None
        assert row1["purpose"] == "MARKETING"
        assert row1["action"] == "GRANTED"
        assert row1["policy_version"] == "1.4"

    # 2. Opt-out of marketing
    res2 = client.put(
        "/api/v1/me/notification-preferences",
        json={"preferences": [{"channel": "EMAIL", "purpose": "MARKETING", "enabled": False}]},
        headers=user["headers"],
    )
    assert res2.status_code == 200, res2.text
    consent_id_2 = res2.json()["preferences"][0]["consent_event_id"]
    assert consent_id_2 is not None
    assert consent_id_2 != consent_id_1

    with transaction() as conn:
        row2 = conn.execute(
            select(t_consent).where(t_consent.c.id == consent_id_2)
        ).mappings().first()
        assert row2 is not None
        assert row2["purpose"] == "MARKETING"
        assert row2["action"] == "REVOKED"


def test_critical_delivery_guard_cannot_disable_transactional_across_all_channels(client, identities):
    """AC-030: Users cannot disable TRANSACTIONAL notifications across all channels (422)."""
    user = identities()

    # Attempt to disable TRANSACTIONAL notifications on ALL channels
    payload = {
        "preferences": [
            {"channel": "EMAIL", "purpose": "TRANSACTIONAL", "enabled": False},
            {"channel": "SMS", "purpose": "TRANSACTIONAL", "enabled": False},
            {"channel": "PUSH", "purpose": "TRANSACTIONAL", "enabled": False},
            {"channel": "WHATSAPP", "purpose": "TRANSACTIONAL", "enabled": False},
        ]
    }

    res = client.put(
        "/api/v1/me/notification-preferences",
        json=payload,
        headers=user["headers"],
    )
    assert res.status_code == 422, res.text
    assert "TRANSACTIONAL_NOTIFICATION_CANNOT_BE_DISABLED" in res.text or "barcha kanallarda" in res.text.lower()


def test_critical_delivery_guard_cannot_disable_security_across_all_channels(client, identities):
    """AC-030: Users cannot disable SECURITY notifications across all channels (422)."""
    user = identities()

    payload = {
        "preferences": [
            {"channel": "EMAIL", "purpose": "SECURITY", "enabled": False},
            {"channel": "SMS", "purpose": "SECURITY", "enabled": False},
            {"channel": "PUSH", "purpose": "SECURITY", "enabled": False},
            {"channel": "WHATSAPP", "purpose": "SECURITY", "enabled": False},
        ]
    }

    res = client.put(
        "/api/v1/me/notification-preferences",
        json=payload,
        headers=user["headers"],
    )
    assert res.status_code == 422, res.text
    assert "TRANSACTIONAL_NOTIFICATION_CANNOT_BE_DISABLED" in res.text or "xavfsizlik" in res.text.lower()


def test_selective_channel_transactional_disable_allowed_when_one_remains_active(client, identities):
    """AC-030: Disabling TRANSACTIONAL on EMAIL is permitted if PUSH remains enabled."""
    user = identities()

    payload = {
        "preferences": [
            {"channel": "EMAIL", "purpose": "TRANSACTIONAL", "enabled": False},
            {"channel": "PUSH", "purpose": "TRANSACTIONAL", "enabled": True},  # PUSH remains active!
        ]
    }

    res = client.put(
        "/api/v1/me/notification-preferences",
        json=payload,
        headers=user["headers"],
    )
    assert res.status_code == 200, res.text


def test_audit_event_logged_on_preference_update(client, identities):
    """Append-only audit trail records NOTIFICATION_PREFERENCES_UPDATED."""
    user = identities()

    res = client.put(
        "/api/v1/me/notification-preferences",
        json={"preferences": [{"channel": "EMAIL", "purpose": "TRANSACTIONAL", "enabled": True}]},
        headers=user["headers"],
    )
    assert res.status_code == 200, res.text

    with transaction() as conn:
        t_audit = table("audit_events")
        row = conn.execute(
            select(t_audit)
            .where(
                t_audit.c.actor_id == user["user_id"],
                t_audit.c.action == "NOTIFICATION_PREFERENCES_UPDATED",
            )
            .order_by(t_audit.c.created_at.desc())
        ).mappings().first()
        assert row is not None
        assert row["object_type"] == "notification_preferences"


def test_unauthenticated_request_rejected_401(client):
    """Unauthenticated calls to preferences endpoints are rejected with 401 Unauthorized."""
    res_get = client.get("/api/v1/me/notification-preferences")
    assert res_get.status_code == 401, res_get.text

    res_put = client.put(
        "/api/v1/me/notification-preferences",
        json={"preferences": [{"channel": "EMAIL", "purpose": "TRANSACTIONAL", "enabled": True}]},
    )
    assert res_put.status_code == 401, res_put.text
