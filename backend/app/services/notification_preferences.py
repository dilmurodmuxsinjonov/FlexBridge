"""Notification preferences management service (API-059 / CAP-031 / DB-085 / DB-011 / AC-030).

Implements canonical `API-059` (`PUT /api/v1/me/notification-preferences`) and `GET /api/v1/me/notification-preferences`:
- Manages channel (`EMAIL`, `SMS`, `PUSH`, `WHATSAPP`) and purpose (`TRANSACTIONAL`, `SECURITY`, `MARKETING`) preferences.
- Enforces strict segregation of transactional and marketing notifications ("Transactional/marketing alohida", AC-030).
- Guarantees critical delivery: prevents disabling transactional or security notices across all channels.
- Persists legal consent events (`DB-011 consent_events`) whenever marketing preferences change.
- Maintains an append-only audit trail (`AppendOnlyAuditStore`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, select

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.services.authority import account_authority
from app.services.placements import PlacementScopeError, insert_row


VALID_CHANNELS = frozenset({"EMAIL", "SMS", "PUSH", "WHATSAPP"})
VALID_PURPOSES = frozenset({"TRANSACTIONAL", "SECURITY", "MARKETING"})

# Default preferences for any user who hasn't explicitly customized them
DEFAULT_PREFERENCES: list[dict[str, Any]] = [
    {"channel": "EMAIL", "purpose": "TRANSACTIONAL", "enabled": True},
    {"channel": "EMAIL", "purpose": "SECURITY", "enabled": True},
    {"channel": "EMAIL", "purpose": "MARKETING", "enabled": False},
    {"channel": "SMS", "purpose": "SECURITY", "enabled": True},
    {"channel": "SMS", "purpose": "TRANSACTIONAL", "enabled": False},
    {"channel": "PUSH", "purpose": "TRANSACTIONAL", "enabled": True},
    {"channel": "PUSH", "purpose": "MARKETING", "enabled": False},
    {"channel": "WHATSAPP", "purpose": "TRANSACTIONAL", "enabled": False},
]


class NotificationScopeError(PlacementScopeError):
    """Scoped exception for notification preference errors."""
    pass


class NotificationPreferencesService:
    """Service managing own notification preferences and consent tracking."""

    def __init__(self, audit_store: AppendOnlyAuditStore | None = None) -> None:
        self.audit_store = audit_store or AppendOnlyAuditStore()

    def get_preferences(self, *, actor: ActorContext) -> dict[str, Any]:
        """Retrieve current effective notification preferences for the authenticated actor."""
        with transaction() as conn:
            account_authority(conn, actor)
            t_pref = table("notification_preferences")

            rows = conn.execute(
                select(
                    t_pref.c.id,
                    t_pref.c.channel,
                    t_pref.c.purpose,
                    t_pref.c.enabled,
                    t_pref.c.consent_event_id,
                    t_pref.c.updated_at,
                )
                .where(t_pref.c.user_id == actor.user_id)
                .order_by(t_pref.c.purpose, t_pref.c.channel)
            ).mappings().all()

            custom_map = {(r["channel"], r["purpose"]): r for r in rows}

            # Build comprehensive effective preferences list
            effective_prefs: list[dict[str, Any]] = []
            seen: set[tuple[str, str]] = set()

            # First add all explicitly stored preferences
            for r in rows:
                key = (r["channel"], r["purpose"])
                seen.add(key)
                effective_prefs.append({
                    "id": str(r["id"]),
                    "channel": r["channel"],
                    "purpose": r["purpose"],
                    "enabled": bool(r["enabled"]),
                    "consent_event_id": str(r["consent_event_id"]) if r["consent_event_id"] else None,
                    "updated_at": r["updated_at"].astimezone(timezone.utc).isoformat() if r["updated_at"] else None,
                })

            # Add defaults for any unset combinations
            for default in DEFAULT_PREFERENCES:
                key = (default["channel"], default["purpose"])
                if key not in seen:
                    effective_prefs.append({
                        "id": None,
                        "channel": default["channel"],
                        "purpose": default["purpose"],
                        "enabled": default["enabled"],
                        "consent_event_id": None,
                        "updated_at": None,
                    })
                    seen.add(key)

            return {
                "contract_id": "API-059",
                "user_id": str(actor.user_id),
                "preferences": effective_prefs,
            }

    def update_preferences_api_059(
        self,
        *,
        actor: ActorContext,
        preferences: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Update notification preferences with transactional delivery safety and consent logging.

        Invariants:
        1. Authenticated actor updates their own preferences (user_id == actor.user_id).
        2. Channel and purpose must be members of VALID_CHANNELS and VALID_PURPOSES.
        3. Transactional and Security notices cannot be completely disabled across all channels (AC-030).
        4. Marketing preference mutations track explicit legal consent events (DB-011).
        5. Atomic upsert updates existing row or inserts new record.
        """
        if not preferences or not isinstance(preferences, list):
            raise NotificationScopeError(
                "PREFERENCES_LIST_REQUIRED",
                "Kamida bitta bildirishnoma sozlamasi talab qilinadi",
                status_code=422,
                sqlstate="22000",
            )

        now_utc = datetime.now(timezone.utc)
        user_id = str(actor.user_id)

        # Validate input items
        sanitized_items: list[dict[str, Any]] = []
        for item in preferences:
            ch = str(item.get("channel", "")).upper().strip()
            pur = str(item.get("purpose", "")).upper().strip()
            en = bool(item.get("enabled"))

            if ch not in VALID_CHANNELS or pur not in VALID_PURPOSES:
                raise NotificationScopeError(
                    "INVALID_NOTIFICATION_CHANNEL_OR_PURPOSE",
                    f"Noma'lum kanal ({ch}) yoki maqsad ({pur}) ko'rsatildi",
                    status_code=422,
                    sqlstate="22000",
                )
            sanitized_items.append({"channel": ch, "purpose": pur, "enabled": en})

        with transaction() as conn:
            account_authority(conn, actor)
            t_pref = table("notification_preferences")
            t_consent = table("consent_events")

            # Load current state from DB
            existing_rows = conn.execute(
                select(t_pref).where(t_pref.c.user_id == user_id)
            ).mappings().all()

            # Build a merged simulation of future state to verify critical channel coverage
            state_map: dict[tuple[str, str], bool] = {
                (d["channel"], d["purpose"]): d["enabled"] for d in DEFAULT_PREFERENCES
            }
            for r in existing_rows:
                state_map[(r["channel"], r["purpose"])] = bool(r["enabled"])
            for s in sanitized_items:
                state_map[(s["channel"], s["purpose"])] = s["enabled"]

            # Critical delivery check: TRANSACTIONAL and SECURITY must have at least one enabled channel
            for required_purpose in ("TRANSACTIONAL", "SECURITY"):
                enabled_channels = [
                    ch for ch in VALID_CHANNELS if state_map.get((ch, required_purpose), False)
                ]
                if not enabled_channels:
                    raise NotificationScopeError(
                        "TRANSACTIONAL_NOTIFICATION_CANNOT_BE_DISABLED",
                        f"Muhim {required_purpose} bildirishnomalarini barcha kanallarda o'chirib bo'lmaydi (AC-030)",
                        status_code=422,
                        sqlstate="22000",
                    )

            # Apply updates with consent tracking
            existing_by_key = {(r["channel"], r["purpose"]): r for r in existing_rows}
            updated_preferences: list[dict[str, Any]] = []

            for item in sanitized_items:
                ch = item["channel"]
                pur = item["purpose"]
                en = item["enabled"]
                consent_event_id: str | None = None

                # AC-030 / DB-011: Track legal consent for marketing changes
                if pur == "MARKETING":
                    consent_id = str(uuid4())
                    action_str = "GRANTED" if en else "REVOKED"
                    insert_row(
                        conn,
                        "consent_events",
                        id=consent_id,
                        user_id=user_id,
                        purpose="MARKETING",
                        policy_version="1.4",
                        action=action_str,
                        legal_basis="User explicit opt-in/opt-out via notification preferences",
                        occurred_at=now_utc,
                    )
                    consent_event_id = consent_id

                key = (ch, pur)
                if key in existing_by_key:
                    row_id = existing_by_key[key]["id"]
                    conn.execute(
                        t_pref.update()
                        .where(t_pref.c.id == row_id)
                        .values(
                            enabled=en,
                            consent_event_id=consent_event_id or existing_by_key[key]["consent_event_id"],
                            updated_at=now_utc,
                        )
                    )
                else:
                    row_id = str(uuid4())
                    insert_row(
                        conn,
                        "notification_preferences",
                        id=row_id,
                        user_id=user_id,
                        channel=ch,
                        purpose=pur,
                        enabled=en,
                        consent_event_id=consent_event_id,
                    )

                updated_preferences.append({
                    "id": str(row_id),
                    "channel": ch,
                    "purpose": pur,
                    "enabled": en,
                    "consent_event_id": consent_event_id,
                    "updated_at": now_utc.astimezone(timezone.utc).isoformat(),
                })

        # Append audit event
        self.audit_store.append_audit_event(
            actor_id=user_id,
            action="NOTIFICATION_PREFERENCES_UPDATED",
            entity_type="notification_preferences",
            entity_id=user_id,
            metadata={
                "items_count": len(sanitized_items),
                "channels": list({s["channel"] for s in sanitized_items}),
                "purposes": list({s["purpose"] for s in sanitized_items}),
            },
        )

        return {
            "contract_id": "API-059",
            "user_id": user_id,
            "preferences": updated_preferences,
            "status": "UPDATED",
        }


notification_preferences_service = NotificationPreferencesService()
