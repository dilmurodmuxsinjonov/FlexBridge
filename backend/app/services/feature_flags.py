"""Feature Flags service (`DB-092`) for FlexBridge 1.4 (S2.1.3).

Manages stage-gated rollout flags (`R1` enabled vs `R2..R5` disabled by default)
with organization/institution scope overrides and immutable audit event logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.audit import AppendOnlyAuditStore

DEFAULT_FEATURE_FLAGS: tuple[dict[str, Any], ...] = (
    {
        "key": "R1_PART_TIME_JOBS",
        "stage": "R1",
        "enabled": True,
        "description": "18+ nomzodlar uchun moslashuvchan yarim stavkali ish oqimi",
    },
    {
        "key": "R1_GENERAL_INTERNSHIPS",
        "stage": "R1",
        "enabled": True,
        "description": "Umumiy amaliyot va mentorlik oqimi",
    },
    {
        "key": "R1_ACADEMIC_INTERNSHIPS",
        "stage": "R1",
        "enabled": True,
        "description": "Oliygoh / texnikum bilan bog'langan akademik amaliyot va kundalik oqimi",
    },
    {
        "key": "R1_PAID_ORG_PLANS",
        "stage": "R1",
        "enabled": True,
        "description": "SINGLE_POST_30D (149 000 so'm) va ORG_PLAN_30D (599 000 so'm, 5 parallel slot)",
    },
    {
        "key": "R2_FREELANCE_MARKETPLACE",
        "stage": "R2",
        "enabled": False,
        "description": "Frilans buyurtmalar va bosqichli topshirish (R1 doirasida o'chiq)",
    },
)


@dataclass
class FeatureFlagService:
    """Service for querying and updating `DB-092 feature_flags` with scope overrides."""

    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)
    _flags: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {item["key"]: dict(item) for item in DEFAULT_FEATURE_FLAGS}
    )
    _org_overrides: dict[tuple[str, str], bool] = field(default_factory=dict)

    def is_enabled(self, key: str, *, organization_id: str | None = None) -> bool:
        if key not in self._flags:
            raise KeyError(f"Unknown feature flag: {key}")
        if organization_id is not None and (key, organization_id) in self._org_overrides:
            return self._org_overrides[(key, organization_id)]
        return bool(self._flags[key]["enabled"])

    def set_global_flag(self, *, key: str, enabled: bool, actor_id: str, reason: str) -> dict[str, Any]:
        if key not in self._flags:
            raise KeyError(f"Unknown feature flag: {key}")
        self._flags[key]["enabled"] = enabled
        self.audit_store.append_audit_event(
            actor_id=actor_id,
            action="FEATURE_FLAG_UPDATED",
            entity_type="feature_flag",
            entity_id=key,
            metadata={"enabled": enabled, "reason": reason},
        )
        return dict(self._flags[key])

    def set_organization_override(
        self,
        *,
        key: str,
        organization_id: str,
        enabled: bool,
        actor_id: str,
    ) -> None:
        if key not in self._flags:
            raise KeyError(f"Unknown feature flag: {key}")
        self._org_overrides[(key, organization_id)] = enabled
        self.audit_store.append_audit_event(
            actor_id=actor_id,
            action="FEATURE_FLAG_ORG_OVERRIDE_SET",
            entity_type="feature_flag",
            entity_id=f"{key}:{organization_id}",
            metadata={"organization_id": organization_id, "enabled": enabled},
        )

    def list_flags(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._flags.values()]
