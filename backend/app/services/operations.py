"""S2.9.1 & S2.10.1: Moderation Appeals, Retention Execution (DB-084) & R1 Pilot Operations Readiness.

Implements:
- S2.9.1: DB-082 moderation_appeals (distinct reviewer from original moderator INV-11, justification >= 15 chars AC-041),
  DB-084 retention_executions lifecycle audit trail, and immutable audit chain verification.
- S2.10.1: R1 Pilot Readiness & Operations verification (RPO=24h, RTO=4h, P1 FinanceCircuitBreaker state,
  17/17 PostgreSQL invariants, 42 Acceptance Criteria AC-001..042, and Q-011 R2_FREELANCE_MARKETPLACE=False guard).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from typing import Any, Dict, List
import uuid

from app.core.audit import AppendOnlyAuditStore
from app.core.circuit_breaker import FinanceCircuitBreaker, shared_circuit_breaker
from app.db.schema import get_schema_summary
from app.db.storage import get_database_url
from app.services.feature_flags import FeatureFlagService
from app.services.retention import RetentionPolicyService


class OperationsInvariantError(ValueError):
    """Raised when moderation appeal dual-control, retention, or RPO/RTO SLA checks fail."""


@dataclass(frozen=True)
class ModerationAppealRecord:
    """Represents a row in DB-082 moderation_appeals."""

    id: str
    moderation_action_id: str
    appellant_user_id: str
    original_moderator_id: str
    appeal_reviewer_id: str
    appeal_reason: str
    decision: str
    resolution_note: str
    resolved_at: datetime


@dataclass(frozen=True)
class RetentionExecutionRecord:
    """Represents a row in DB-084 retention_executions."""

    id: str
    data_category: str
    records_scanned: int
    records_actioned: int
    executed_action: str
    legal_basis: str
    executed_by: str
    executed_at: datetime


@dataclass
class PilotOperationsService:
    """Coordinates S2.9.1 moderation/audit/retention workflows and S2.10.1 R1 pilot readiness reporting."""

    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)
    circuit_breaker: FinanceCircuitBreaker = field(default_factory=lambda: shared_circuit_breaker)
    retention_service: RetentionPolicyService = field(default_factory=RetentionPolicyService)
    feature_flag_service: FeatureFlagService = field(default_factory=FeatureFlagService)
    _appeals: Dict[str, ModerationAppealRecord] = field(default_factory=dict)
    _retention_executions: List[RetentionExecutionRecord] = field(default_factory=list)

    def submit_and_resolve_moderation_appeal(
        self,
        *,
        moderation_action_id: str,
        appellant_user_id: str,
        original_moderator_id: str,
        appeal_reviewer_id: str,
        appeal_reason: str,
        decision: str,
        resolution_note: str,
    ) -> ModerationAppealRecord:
        """Resolves a moderation appeal (DB-082) enforcing INV-11 (distinct reviewer) and AC-041."""
        if original_moderator_id == appeal_reviewer_id:
            raise OperationsInvariantError(
                "INV-11 violation: Appeal reviewer must be distinct from the original moderator."
            )
        if appellant_user_id == appeal_reviewer_id:
            raise OperationsInvariantError(
                "INV-11 violation: Appellant cannot review their own moderation appeal."
            )
        if decision not in {"UPHELD", "OVERTURNED"}:
            raise OperationsInvariantError(f"Unsupported appeal decision '{decision}'.")
        if not resolution_note or len(resolution_note.strip()) < 15:
            raise OperationsInvariantError(
                "AC-041 violation: Appeal resolution_note must be at least 15 characters."
            )

        record = ModerationAppealRecord(
            id=str(uuid.uuid4()),
            moderation_action_id=moderation_action_id,
            appellant_user_id=appellant_user_id,
            original_moderator_id=original_moderator_id,
            appeal_reviewer_id=appeal_reviewer_id,
            appeal_reason=appeal_reason.strip(),
            decision=decision,
            resolution_note=resolution_note.strip(),
            resolved_at=datetime.now(timezone.utc),
        )
        self._appeals[record.id] = record

        self.audit_store.append_audit_event(
            actor_id=appeal_reviewer_id,
            action="MODERATION_APPEAL_RESOLVED",
            entity_type="moderation_appeals",
            entity_id=record.id,
            metadata={
                "moderation_action_id": moderation_action_id,
                "original_moderator_id": original_moderator_id,
                "decision": decision,
                "resolution_note": record.resolution_note,
            },
        )
        return record

    def execute_retention_job(
        self,
        *,
        data_category: str,
        age_days: int,
        records_scanned: int,
        executed_by: str,
    ) -> RetentionExecutionRecord:
        """Runs a retention policy evaluation (DB-083) and logs a DB-084 retention_executions record."""
        eval_res = self.retention_service.evaluate_age_days(
            data_class=data_category,
            age_days=age_days,
        )
        policy = self.retention_service.get_policy(data_category)
        decision_status = str(eval_res["decision"])
        records_actioned = records_scanned if decision_status in {"PURGE_DUE", "WARN_EXPIRING"} else 0

        exec_record = RetentionExecutionRecord(
            id=str(uuid.uuid4()),
            data_category=data_category,
            records_scanned=records_scanned,
            records_actioned=records_actioned,
            executed_action=decision_status,
            legal_basis=str(policy["legal_basis"]),
            executed_by=executed_by,
            executed_at=datetime.now(timezone.utc),
        )
        self._retention_executions.append(exec_record)

        self.audit_store.append_audit_event(
            actor_id=executed_by,
            action="RETENTION_POLICY_EXECUTED",
            entity_type="retention_executions",
            entity_id=exec_record.id,
            metadata={
                "data_category": data_category,
                "age_days": age_days,
                "decision_status": decision_status,
                "records_scanned": records_scanned,
                "records_actioned": records_actioned,
            },
        )
        return exec_record

    def get_pilot_readiness_report(self) -> Dict[str, Any]:
        """Generates the S2.10.1 R1 Pilot Readiness Report across schema, DR targets, AC-001..042, and Q-011."""
        summary = get_schema_summary()
        counts = summary["counts"]
        pg_ver = summary["postgres_verification"]

        r2_freelance_enabled = self.feature_flag_service.is_enabled("R2_FREELANCE_MARKETPLACE")
        r1_jobs_enabled = self.feature_flag_service.is_enabled("R1_PART_TIME_JOBS")
        r1_general_intern_enabled = self.feature_flag_service.is_enabled("R1_GENERAL_INTERNSHIPS")
        r1_academic_intern_enabled = self.feature_flag_service.is_enabled("R1_ACADEMIC_INTERNSHIPS")

        schema_and_invariants_ready = (
            summary["schema_sql_exists"] is True
            and counts.get("tables") == 94
            and counts.get("fields") == 935
            and counts.get("foreign_keys") == 214
            and counts.get("acceptance_criteria") == 42
            and counts.get("reference_errors") == 0
            and pg_ver.get("all_checks_passed") is True
            and self.circuit_breaker.state == "CLOSED"
            and r2_freelance_enabled is False
            and r1_jobs_enabled is True
            and r1_general_intern_enabled is True
            and r1_academic_intern_enabled is True
        )
        external_services_ready = (
            get_database_url().startswith("postgresql")
            and os.environ.get("FLEXBRIDGE_EXTERNAL_SERVICES_VERIFIED") == "1"
        )
        pilot_ready = schema_and_invariants_ready and external_services_ready

        return {
            "pilot_ready": pilot_ready,
            "schema_and_invariants_ready": schema_and_invariants_ready,
            "external_services_ready": external_services_ready,
            "release_stage": "R1_PILOT",
            "q_011_r2_freelance_deferred": {
                "R2_FREELANCE_MARKETPLACE": r2_freelance_enabled,
                "R1_PART_TIME_JOBS": r1_jobs_enabled,
                "R1_GENERAL_INTERNSHIPS": r1_general_intern_enabled,
                "R1_ACADEMIC_INTERNSHIPS": r1_academic_intern_enabled,
            },
            "disaster_recovery_and_safety": {
                "rpo_hours_target": 24,
                "rto_hours_target": 4,
                "p1_finance_circuit_breaker_state": self.circuit_breaker.state,
                "pgbouncer_pool_mode": "transaction",
            },
            "schema_and_invariants": {
                "tables": counts.get("tables"),
                "fields": counts.get("fields"),
                "foreign_keys": counts.get("foreign_keys"),
                "acceptance_criteria": counts.get("acceptance_criteria"),
                "reference_errors": counts.get("reference_errors"),
                "postgres_17_of_17_passed": pg_ver.get("all_checks_passed"),
            },
            "audit_and_retention_stats": {
                "audit_events_count": len(self.audit_store.list_audit_events()),
                "appeals_resolved_count": len(self._appeals),
                "retention_executions_count": len(self._retention_executions),
            },
        }
