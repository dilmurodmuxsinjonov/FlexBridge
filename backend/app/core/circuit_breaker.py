"""P1 Finance & Security Circuit-Breaker for FlexBridge 1.4 (S2.1.2).

Implements section 7 of `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf`:
- When a P1 incident (financial ledger discrepancy, unauthorized scope access, or double-charge risk)
  occurs, the finance circuit-breaker trips immediately.
- While tripped (`OPEN`), all payment, invoice checkout, and refund execution endpoints fail-closed
  with `503 P1_FINANCE_CIRCUIT_OPEN`, while read-only and non-financial workflows remain available.
- Tripping and resetting the circuit-breaker both emit immutable `audit_events`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.audit import AppendOnlyAuditStore


class FinanceCircuitOpenError(Exception):
    """Raised when a financial operation is attempted while the P1 circuit-breaker is OPEN."""

    def __init__(self, reason_code: str, incident_id: str) -> None:
        super().__init__(f"P1 finance circuit-breaker is OPEN ({reason_code}, incident={incident_id})")
        self.code = "P1_FINANCE_CIRCUIT_OPEN"
        self.reason_code = reason_code
        self.incident_id = incident_id


@dataclass
class FinanceCircuitBreaker:
    """State machine for P1 financial safety circuit-breaker."""

    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)
    state: str = "CLOSED"  # CLOSED (normal) | OPEN (frozen)
    incident_id: str | None = None
    reason_code: str | None = None
    tripped_by: str | None = None
    tripped_at: str | None = None

    def trip(
        self,
        *,
        actor_id: str,
        incident_id: str,
        reason_code: str,
        details: str,
    ) -> dict[str, Any]:
        """Trip the P1 finance circuit-breaker and record an immutable audit event."""
        self.state = "OPEN"
        self.incident_id = incident_id
        self.reason_code = reason_code
        self.tripped_by = actor_id
        self.tripped_at = datetime.now(timezone.utc).isoformat()

        return self.audit_store.append_audit_event(
            actor_id=actor_id,
            action="P1_FINANCE_CIRCUIT_TRIPPED",
            entity_type="finance_circuit_breaker",
            entity_id=incident_id,
            metadata={
                "reason_code": reason_code,
                "details": details,
                "state": self.state,
            },
        )

    def require_closed(self) -> None:
        """Fail-closed if the P1 finance circuit-breaker is currently OPEN."""
        if self.state != "CLOSED":
            raise FinanceCircuitOpenError(
                reason_code=self.reason_code or "UNKNOWN_P1_INCIDENT",
                incident_id=self.incident_id or "INC-UNKNOWN",
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
        self.state = "CLOSED"
        self.incident_id = None
        self.reason_code = None
        self.tripped_by = None
        self.tripped_at = None

        return self.audit_store.append_audit_event(
            actor_id=actor_id,
            action="P1_FINANCE_CIRCUIT_RESET",
            entity_type="finance_circuit_breaker",
            entity_id=prev_incident,
            metadata={
                "second_approver_id": second_approver_id,
                "resolution_note": resolution_note,
                "state": self.state,
            },
        )
