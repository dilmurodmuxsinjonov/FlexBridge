"""Append-only audit and revision immutability guards for FlexBridge 1.4 (S2.1.2).

Enforces:
- `INV-13`: `audit_events`, `consent_events`, and `billing_ledger` are strictly append-only
  (`UPDATE` and `DELETE` raise `ImmutableRecordError` with SQLSTATE `23514`).
- `INV-16`: Published `opportunity_revisions` (`published_at IS NOT NULL`) and submitted
  `log_revisions` (`status != 'DRAFT'`) cannot be modified or deleted; new revisions must be created.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class ImmutableRecordError(Exception):
    """Raised when an UPDATE or DELETE is attempted on an append-only or locked revision record."""

    def __init__(self, table: str, message: str, sqlstate: str = "23514") -> None:
        super().__init__(message)
        self.table = table
        self.sqlstate = sqlstate


@dataclass
class AppendOnlyAuditStore:
    """Append-only store for `audit_events`, `consent_events`, and `billing_ledger` (`INV-13`)."""

    _audit_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    _consent_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    _billing_ledger: dict[str, dict[str, Any]] = field(default_factory=dict)

    def append_audit_event(
        self,
        *,
        actor_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event_id = str(uuid4())
        record = {
            "id": event_id,
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": dict(metadata or {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._audit_events[event_id] = record
        return dict(record)

    def append_consent_event(
        self,
        *,
        user_id: str,
        consent_type: str,
        policy_version: str,
        granted: bool,
    ) -> dict[str, Any]:
        event_id = str(uuid4())
        record = {
            "id": event_id,
            "user_id": user_id,
            "consent_type": consent_type,
            "policy_version": policy_version,
            "granted": granted,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._consent_events[event_id] = record
        return dict(record)

    def append_billing_ledger_entry(
        self,
        *,
        organization_id: str,
        entry_type: str,
        amount_uzs: int,
        reference_id: str,
    ) -> dict[str, Any]:
        entry_id = str(uuid4())
        record = {
            "id": entry_id,
            "organization_id": organization_id,
            "entry_type": entry_type,
            "amount_uzs": amount_uzs,
            "currency": "UZS",
            "reference_id": reference_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._billing_ledger[entry_id] = record
        return dict(record)

    def update_record(self, table: str, record_id: str, **updates: Any) -> None:
        """Always reject updates on append-only tables (`trg_immutable_*`)."""
        raise ImmutableRecordError(
            table=table,
            message=f"{table} jadvali append-only; UPDATE va DELETE taqiqlangan (INV-16)",
        )

    def delete_record(self, table: str, record_id: str) -> None:
        """Always reject deletes on append-only tables (`trg_immutable_*`)."""
        raise ImmutableRecordError(
            table=table,
            message=f"{table} jadvali append-only; UPDATE va DELETE taqiqlangan (INV-16)",
        )

    def list_audit_events(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._audit_events.values()]


def guard_opportunity_revision_update(existing: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Enforce `fn_guard_opportunity_revisions`: published revisions cannot be mutated (`INV-16`)."""
    if existing.get("published_at") is not None:
        raise ImmutableRecordError(
            table="opportunity_revisions",
            message="Nashr qilingan opportunity_revisions yozuvini tahrirlash taqiqlangan (INV-16)",
        )
    merged = dict(existing)
    merged.update(updates)
    return merged


def guard_log_revision_update(existing: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Enforce `fn_guard_log_revisions`: submitted (`status != 'DRAFT'`) log content cannot be mutated."""
    if existing.get("status", "DRAFT") != "DRAFT":
        protected_fields = (
            "daily_log_id",
            "revision",
            "terms_id",
            "author_id",
            "day_type",
            "total_minutes",
        )
        for field_name in protected_fields:
            if field_name in updates and updates[field_name] != existing.get(field_name):
                raise ImmutableRecordError(
                    table="log_revisions",
                    message="Topshirilgan log_revisions tarkibini o'zgartirish taqiqlangan; yangi revision yarating (INV-16)",
                )
    merged = dict(existing)
    merged.update(updates)
    return merged
