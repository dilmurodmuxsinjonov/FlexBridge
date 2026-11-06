"""Automated test suite for S2.1.2: DEFERRABLE circular FK transactions, append-only audit/immutability, and P1 finance circuit-breaker."""

from __future__ import annotations

import pytest

from app.core.audit import (
    AppendOnlyAuditStore,
    ImmutableRecordError,
    guard_log_revision_update,
    guard_opportunity_revision_update,
)
from app.core.circuit_breaker import FinanceCircuitBreaker, FinanceCircuitOpenError
from app.db.session import ConstraintViolationError, DeferredUnitOfWork


def test_deferred_circular_fk_opportunity_and_thread_success() -> None:
    """Verify circular FK pairs (`opportunities <-> opportunity_revisions`, `threads <-> messages`) commit atomically."""
    uow = DeferredUnitOfWork()
    opp, rev = uow.create_opportunity_with_initial_revision(
        organization_id="org-1",
        created_by="user-hr-1",
        title="Backend Python Intern",
    )
    assert opp["current_revision_id"] == rev["id"]
    assert rev["opportunity_id"] == opp["id"]
    assert uow.sql_trace[-3:] == [
        "BEGIN;",
        "SET CONSTRAINTS ALL IMMEDIATE;",
        "COMMIT;",
    ]

    thread, msg = uow.create_thread_with_first_message(
        created_by="user-hr-1",
        subject="Suhbat taklifi",
        body="Assalomu alaykum, ertaga soat 15:00 da suhbat.",
    )
    assert thread["last_message_id"] == msg["id"]
    assert msg["thread_id"] == thread["id"]


def test_deferred_circular_fk_rollback_on_broken_reference() -> None:
    """Verify `SET CONSTRAINTS ALL IMMEDIATE` rolls back the entire transaction if a circular FK is broken."""
    uow = DeferredUnitOfWork()
    with pytest.raises(ConstraintViolationError) as exc_info:
        with uow.atomic_deferred():
            uow.opportunities["opp-broken"] = {
                "id": "opp-broken",
                "organization_id": "org-1",
                "current_revision_id": "rev-missing",
            }
    assert exc_info.value.sqlstate == "23503"
    assert "opp-broken" not in uow.opportunities
    assert uow.sql_trace[-1] == "ROLLBACK;"


def test_append_only_audit_consent_and_billing_ledger() -> None:
    """Verify `audit_events`, `consent_events`, and `billing_ledger` reject UPDATE and DELETE (`INV-13`, `INV-16`)."""
    store = AppendOnlyAuditStore()
    audit = store.append_audit_event(
        actor_id="user-1",
        action="OPPORTUNITY_PUBLISHED",
        entity_type="opportunity",
        entity_id="opp-1",
    )
    consent = store.append_consent_event(
        user_id="user-1",
        consent_type="PERSONAL_DATA_PROCESSING",
        policy_version="v1.4",
        granted=True,
    )
    ledger = store.append_billing_ledger_entry(
        organization_id="org-1",
        entry_type="INVOICE_PAYMENT",
        amount_uzs=599000,
        reference_id="inv-1",
    )

    for table_name, rec_id in (
        ("audit_events", audit["id"]),
        ("consent_events", consent["id"]),
        ("billing_ledger", ledger["id"]),
    ):
        with pytest.raises(ImmutableRecordError) as up_err:
            store.update_record(table_name, rec_id, action="TAMPERED")
        assert up_err.value.sqlstate == "23514"

        with pytest.raises(ImmutableRecordError) as del_err:
            store.delete_record(table_name, rec_id)
        assert del_err.value.sqlstate == "23514"


def test_published_opportunity_and_submitted_log_revision_immutability() -> None:
    """Verify published `opportunity_revisions` and submitted `log_revisions` reject mutation (`INV-16`)."""
    draft_opp_rev = {
        "id": "rev-1",
        "opportunity_id": "opp-1",
        "title": "Dastlabki sarlavha",
        "published_at": None,
    }
    updated_draft = guard_opportunity_revision_update(draft_opp_rev, {"title": "Yangilangan sarlavha"})
    assert updated_draft["title"] == "Yangilangan sarlavha"

    published_opp_rev = dict(updated_draft, published_at="2026-11-07T00:00:00Z")
    with pytest.raises(ImmutableRecordError):
        guard_opportunity_revision_update(published_opp_rev, {"title": "Ruxsatsiz o'zgarish"})

    submitted_log_rev = {
        "id": "log-rev-1",
        "daily_log_id": "log-1",
        "revision": 1,
        "terms_id": "terms-1",
        "author_id": "student-1",
        "day_type": "WORKDAY",
        "total_minutes": 240,
        "status": "SUBMITTED",
    }
    with pytest.raises(ImmutableRecordError):
        guard_log_revision_update(submitted_log_rev, {"total_minutes": 480})


def test_p1_finance_circuit_breaker_and_dual_control_reset() -> None:
    """Verify P1 finance circuit-breaker blocks financial ops when OPEN and requires dual-control to reset."""
    cb = FinanceCircuitBreaker()
    cb.require_closed()  # Should pass when CLOSED

    cb.trip(
        actor_id="admin-1",
        incident_id="INC-2026-001",
        reason_code="LEDGER_MISMATCH_DETECTED",
        details="Billing ledger vs payment_attempts discrepancy check",
    )
    assert cb.state == "OPEN"

    with pytest.raises(FinanceCircuitOpenError) as exc_info:
        cb.require_closed()
    assert exc_info.value.code == "P1_FINANCE_CIRCUIT_OPEN"

    # Self-approval reset must fail
    with pytest.raises(ValueError, match="SELF_APPROVAL_FORBIDDEN"):
        cb.reset(
            actor_id="admin-1",
            second_approver_id="admin-1",
            resolution_note="Attempted self-reset",
        )

    # Dual-control reset with second admin succeeds
    cb.reset(
        actor_id="admin-1",
        second_approver_id="finance-admin-2",
        resolution_note="Reconciled ledger and verified DB-072 idempotency",
    )
    assert cb.state == "CLOSED"
    cb.require_closed()
    assert len(cb.audit_store.list_audit_events()) == 2
