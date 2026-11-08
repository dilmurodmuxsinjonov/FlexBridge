"""Automated test suite for S2.1.3: Retention Policy v1 (`DB-083`) and Feature Flags (`DB-092`) services."""

from __future__ import annotations

import pytest

from app.services.feature_flags import FeatureFlagService
from app.services.retention import RetentionPolicyService, RetentionPolicyValidationError


def test_retention_policy_v1_lifecycle_decisions() -> None:
    """Verify `DB-083` retention evaluation for drafts (23d warning / 30d purge), applications (365d), and fiscal ledger (1825d)."""
    svc = RetentionPolicyService()
    assert len(svc.list_policies()) == 8

    # Unpublished draft: <23 days -> RETAIN, 23..29 days -> WARN_EXPIRING, >=30 days -> PURGE_DUE
    assert svc.evaluate_age_days("UNPUBLISHED_DRAFT", 10)["decision"] == "RETAIN"
    warn_eval = svc.evaluate_age_days("UNPUBLISHED_DRAFT", 23)
    assert warn_eval["decision"] == "WARN_EXPIRING"
    assert warn_eval["action"] == "SEND_23_DAY_DRAFT_EXPIRY_WARNING"
    assert svc.evaluate_age_days("UNPUBLISHED_DRAFT", 30)["decision"] == "PURGE_DUE"

    # Closed application at 365 days -> ANONYMIZE_PII
    app_eval = svc.evaluate_age_days("APPLICATION_AND_SNAPSHOT", 365)
    assert app_eval["decision"] == "PURGE_DUE"
    assert app_eval["action"] == "ANONYMIZE_PII"

    # Fiscal ledger retained for 5 years (1825 days)
    assert svc.evaluate_age_days("BILLING_AND_FISCAL_LEDGER", 1800)["decision"] == "RETAIN"
    assert svc.evaluate_age_days("BILLING_AND_FISCAL_LEDGER", 1825)["decision"] == "PURGE_DUE"


def test_retention_policy_legal_basis_validation() -> None:
    """Verify `chk_retention_legal_basis` rejects short legal_basis or non-positive active_days."""
    svc = RetentionPolicyService()
    with pytest.raises(RetentionPolicyValidationError):
        svc.register_custom_policy(
            data_class="CUSTOM_TEMP",
            policy_version=1,
            active_days=30,
            backup_expiry_days=7,
            legal_basis="short",
        )
    with pytest.raises(RetentionPolicyValidationError):
        svc.register_custom_policy(
            data_class="CUSTOM_TEMP",
            policy_version=1,
            active_days=0,
            backup_expiry_days=7,
            legal_basis="To'liq huquqiy asos matni",
        )


def test_feature_flags_r1_vs_r2_defaults_and_org_overrides(identities, organization) -> None:
    """Verify R1 flows are enabled, R2 freelance is disabled by default, and org overrides + audit work."""
    ff = FeatureFlagService()
    assert ff.is_enabled("R1_PART_TIME_JOBS") is True
    assert ff.is_enabled("R1_GENERAL_INTERNSHIPS") is True
    assert ff.is_enabled("R1_ACADEMIC_INTERNSHIPS") is True
    assert ff.is_enabled("R1_PAID_ORG_PLANS") is True
    assert ff.is_enabled("R2_FREELANCE_MARKETPLACE") is False

    # Pilot override for a specific organization
    ff.set_organization_override(
        key="R2_FREELANCE_MARKETPLACE",
        organization_id=organization,
        enabled=True,
        actor_id=identities("ADMIN")["user_id"],
    )
    assert ff.is_enabled("R2_FREELANCE_MARKETPLACE", organization_id=organization) is True
    assert ff.is_enabled("R2_FREELANCE_MARKETPLACE", organization_id="org-other") is False
    assert sum(event['action']=='FEATURE_FLAG_ORG_OVERRIDE_SET' for event in ff.audit_store.list_audit_events()) == 1
