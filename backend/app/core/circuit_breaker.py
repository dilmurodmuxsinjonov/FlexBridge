"""P1 Finance & Security Circuit-Breaker for FlexBridge 1.4 (S2.1.2, FIX-13, REV-002).

Implements section 7 of `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` and `TD-001` (`FIX-13`):
- Shared persistent state across `BillingQuotaService`, `OperationsReadinessService`, and worker processes via SQLAlchemy `circuit_breaker_state` table.
- Importing this module in a new worker process preserves any existing `OPEN` state in SQL storage without resetting it.
- While tripped (`OPEN`), all payment, invoice checkout, and refund execution endpoints fail-closed
  with `503 P1_FINANCE_CIRCUIT_OPEN`, while read-only and non-financial workflows remain available.
- Tripping and resetting the circuit-breaker both emit immutable `audit_events`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from app.core.audit import AppendOnlyAuditStore
from app.db.storage import circuit_breaker_table, get_engine, transaction, now


class FinanceCircuitOpenError(Exception):
    """Raised when a financial operation is attempted while the P1 circuit-breaker is OPEN."""

    def __init__(
        self,
        reason_code: str,
        incident_id: str,
        *,
        invoice_id: str | None = None,
        order_id: str | None = None,
    ) -> None:
        super().__init__(f"P1 finance circuit-breaker is OPEN ({reason_code}, incident={incident_id})")
        self.code = "P1_FINANCE_CIRCUIT_OPEN"
        self.reason_code = reason_code
        self.incident_id = incident_id
        self.invoice_id = invoice_id
        self.order_id = order_id
        self.status_code = 503


def _ensure_breaker_row_initialized() -> None:
    """Insert default CLOSED row only if no row exists yet; never overwrite an existing OPEN state on import."""
    now_iso = now()
    with transaction() as conn:
        existing = conn.execute(
            select(circuit_breaker_table.c.key).where(circuit_breaker_table.c.key == "P1_FINANCE")
        ).first()
        if not existing:
            conn.execute(
                circuit_breaker_table.insert().values(
                    key="P1_FINANCE",
                    state="CLOSED",
                    incident_id=None,
                    reason_code=None,
                    tripped_by=None,
                    tripped_at=None,
                    updated_at=now_iso,
                )
            )


def _read_breaker_row() -> dict[str, Any]:
    with transaction() as conn:
        row = conn.execute(select(circuit_breaker_table).where(circuit_breaker_table.c.key == 'P1_FINANCE').with_for_update(read=True)).mappings().first()
        if row is None:
            raise RuntimeError('Circuit breaker state is missing; apply migrations')
        return dict(row)


def _write_breaker_row(
    *,
    state: str,
    incident_id: str | None,
    reason_code: str | None,
    tripped_by: str | None,
    tripped_at: datetime | None,
) -> None:
    now_iso = now()
    with transaction() as conn:
        existing = conn.execute(
            select(circuit_breaker_table.c.key).where(circuit_breaker_table.c.key == "P1_FINANCE")
        ).first()
        if existing:
            conn.execute(
                update(circuit_breaker_table)
                .where(circuit_breaker_table.c.key == "P1_FINANCE")
                .values(
                    state=state,
                    incident_id=incident_id,
                    reason_code=reason_code,
                    tripped_by=tripped_by,
                    tripped_at=tripped_at,
                    updated_at=now_iso,
                )
            )
        else:
            conn.execute(
                circuit_breaker_table.insert().values(
                    key="P1_FINANCE",
                    state=state,
                    incident_id=incident_id,
                    reason_code=reason_code,
                    tripped_by=tripped_by,
                    tripped_at=tripped_at,
                    updated_at=now_iso,
                )
            )




@dataclass
class FinanceCircuitBreaker:
    """Shared state machine for P1 financial safety circuit-breaker (`FIX-13`, `R-09`)."""

    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)

    @property
    def state(self) -> str:
        return str(_read_breaker_row()["state"])

    @state.setter
    def state(self, value: str) -> None:
        row = _read_breaker_row()
        _write_breaker_row(
            state=value,
            incident_id=row["incident_id"],
            reason_code=row["reason_code"],
            tripped_by=row["tripped_by"],
            tripped_at=row["tripped_at"],
        )

    @property
    def incident_id(self) -> str | None:
        return _read_breaker_row()["incident_id"]

    @property
    def reason_code(self) -> str | None:
        return _read_breaker_row()["reason_code"]

    @property
    def tripped_by(self) -> str | None:
        return _read_breaker_row()["tripped_by"]

    @property
    def tripped_at(self) -> str | None:
        return _read_breaker_row()["tripped_at"]

    def trip(
        self,
        *,
        actor_id: str,
        incident_id: str,
        reason_code: str,
        details: str,
    ) -> dict[str, Any]:
        """Trip the P1 finance circuit-breaker and record an immutable audit event."""
        now_iso = now()
        _write_breaker_row(
            state="OPEN",
            incident_id=incident_id,
            reason_code=reason_code,
            tripped_by=actor_id,
            tripped_at=now_iso,
        )

        return self.audit_store.append_audit_event(
            actor_id=actor_id,
            action="P1_FINANCE_CIRCUIT_TRIPPED",
            entity_type="finance_circuit_breaker",
            entity_id=incident_id,
            metadata={
                "reason_code": reason_code,
                "details": details,
                "state": "OPEN",
            },
        )

    def require_closed(
        self,
        *,
        invoice_id: str | None = None,
        order_id: str | None = None,
    ) -> None:
        """Fail-closed if the P1 finance circuit-breaker is currently OPEN."""
        row = _read_breaker_row()
        if row["state"] != "CLOSED":
            raise FinanceCircuitOpenError(
                reason_code=row["reason_code"] or "UNKNOWN_P1_INCIDENT",
                incident_id=row["incident_id"] or "INC-UNKNOWN",
                invoice_id=invoice_id,
                order_id=order_id,
            )

    def reset(
        self,
        *,
        actor_id: str,
        second_approver_id: str,
        resolution_note: str,
    ) -> dict[str, Any]:
        """Reset the P1 circuit-breaker under dual-control (`actor_id != second_approver_id`)."""
        if actor_id == second_approver_id:
            raise ValueError("SELF_APPROVAL_FORBIDDEN: P1 circuit-breaker reset requires two distinct admins")

        prev_incident = self.incident_id or "INC-NONE"
        _write_breaker_row(
            state="CLOSED",
            incident_id=None,
            reason_code=None,
            tripped_by=None,
            tripped_at=None,
        )

        return self.audit_store.append_audit_event(
            actor_id=actor_id,
            action="P1_FINANCE_CIRCUIT_RESET",
            entity_type="finance_circuit_breaker",
            entity_id=prev_incident,
            metadata={
                "second_approver_id": second_approver_id,
                "resolution_note": resolution_note,
                "state": "CLOSED",
            },
        )


shared_circuit_breaker = FinanceCircuitBreaker()
