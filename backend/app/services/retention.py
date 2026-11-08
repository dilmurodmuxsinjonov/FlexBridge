"""Retention Policy v1 service (`DB-083`, `DB-084`) for FlexBridge 1.4 (S2.1.3).

Enforces section 6 of `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf`:
- 8 mandatory data classes with explicit `active_days`, `backup_expiry_days`, and `legal_basis`.
- `chk_retention_legal_basis`: `length(btrim(legal_basis)) >= 10` and `active_days > 0`.
- `UNPUBLISHED_DRAFT` 23-day warning and 30-day purge schedule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.db.schema import RETENTION_POLICIES_V1


class RetentionPolicyValidationError(ValueError):
    """Raised when a retention policy violates 1.4 PDF section 6 constraints."""


@dataclass
class RetentionPolicyService:
    """Read-only reference-policy evaluator; no legal approval or deletion is performed."""

    _policies: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {item["data_class"]: dict(item) for item in RETENTION_POLICIES_V1}
    )

    def list_policies(self) -> list[dict[str, Any]]:
        return [dict(p) for p in self._policies.values()]

    def get_policy(self, data_class: str) -> dict[str, Any]:
        if data_class not in self._policies:
            raise KeyError(f"Unknown retention data_class: {data_class}")
        return dict(self._policies[data_class])

    def register_custom_policy(
        self,
        *,
        data_class: str,
        policy_version: int,
        active_days: int,
        backup_expiry_days: int,
        legal_basis: str,
    ) -> dict[str, Any]:
        """Validate inputs, then fail closed until a legal-review workflow exists."""
        if active_days <= 0 or backup_expiry_days < 0:
            raise RetentionPolicyValidationError("active_days must be > 0 and backup_expiry_days >= 0")
        if len(legal_basis.strip()) < 10:
            raise RetentionPolicyValidationError(
                "legal_basis must be at least 10 characters (`chk_retention_legal_basis`)"
            )
        raise RetentionPolicyValidationError('Custom policies require a separately authorized legal-review workflow')

    def evaluate_age_days(self, data_class: str, age_days: int) -> dict[str, Any]:
        """Evaluate whether a record of `data_class` is `RETAIN`, `WARN_EXPIRING`, or `PURGE_DUE`."""
        if age_days < 0:
            raise RetentionPolicyValidationError('age_days must be nonnegative')
        policy = self.get_policy(data_class)
        active_days = int(policy["active_days"])

        if age_days >= active_days:
            action = (
                "ANONYMIZE_PII"
                if data_class == "APPLICATION_AND_SNAPSHOT"
                else "PURGE_ACTIVE_STORAGE"
            )
            return {
                "data_class": data_class,
                "age_days": age_days,
                "active_days": active_days,
                "decision": "PURGE_DUE",
                "action": action,
            }

        if data_class == "UNPUBLISHED_DRAFT" and age_days >= 23:
            return {
                "data_class": data_class,
                "age_days": age_days,
                "active_days": active_days,
                "decision": "WARN_EXPIRING",
                "action": "SEND_23_DAY_DRAFT_EXPIRY_WARNING",
            }

        return {
            "data_class": data_class,
            "age_days": age_days,
            "active_days": active_days,
            "decision": "RETAIN",
            "action": "NONE",
        }
