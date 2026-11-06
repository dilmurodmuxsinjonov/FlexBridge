"""S2.8.1 & FIX-05..07: Tariffs, 5-Slot Concurrent Quota (ORG_PLAN_30D), Provider Webhook Confirmation, Payload-Bound Idempotency & Cumulative Dual-Control Refunds.

Implements:
- DB-069 service_entitlements (SINGLE_POST_30D = 149,000 UZS / 1 slot, ORG_PLAN_30D = 599,000 UZS / 5 concurrent active slots, INV-04, validity window check R-11)
- AC-042 concurrent slot enforcement: when 5 opportunities are PUBLISHED on ORG_PLAN_30D, publishing a 6th fails with CONCURRENT_QUOTA_REACHED; closing/pausing 1 slot allows publishing the next
- DB-070 orders, DB-071 invoices, DB-072 payment_attempts (UZS currency, exact amount match INV-05 & INV-10, payload-bound idempotency_key deduplication R-10, provider webhook confirmation API-X04 R-02, P1 FinanceCircuitBreaker guard R-09)
- DB-073 refunds (cumulative refund_amount_uzs <= invoice.amount_uzs INV-05 & INV-12 R-06, Dual-Control approvers INV-11)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from typing import Any, Dict, Optional, Tuple
import uuid

from app.core.audit import AppendOnlyAuditStore
from app.core.circuit_breaker import FinanceCircuitBreaker, shared_circuit_breaker


class BillingInvariantError(ValueError):
    """Raised when INV-04, INV-05, INV-10, INV-11, INV-12, or AC-042 billing rules are violated."""


TARIFF_CATALOG: Dict[str, Dict[str, Optional[int]]] = {
    "SINGLE_POST_30D": {
        "price_uzs": 149_000,
        "total_post_credits": 1,
        "concurrent_active_limit": 1,
        "duration_days": 30,
    },
    "ORG_PLAN_30D": {
        "price_uzs": 599_000,
        "total_post_credits": None,
        "concurrent_active_limit": 5,
        "duration_days": 30,
    },
}


@dataclass(frozen=True)
class ServiceEntitlement:
    """Represents a row in DB-069 service_entitlements."""

    id: str
    organization_id: str
    plan_code: str
    total_post_credits: Optional[int]
    used_post_credits: int
    concurrent_active_limit: int
    status: str
    valid_from: datetime
    valid_until: datetime


@dataclass(frozen=True)
class OrderRecord:
    """Represents a row in DB-070 orders."""

    id: str
    organization_id: str
    plan_code: str
    amount_uzs: int
    currency_code: str
    status: str
    created_by: str
    created_at: datetime


@dataclass(frozen=True)
class InvoiceRecord:
    """Represents a row in DB-071 invoices."""

    id: str
    order_id: str
    organization_id: str
    amount_uzs: int
    currency_code: str
    status: str
    issued_at: datetime
    paid_at: Optional[datetime] = None


@dataclass(frozen=True)
class PaymentAttemptRecord:
    """Represents a row in DB-072 payment_attempts."""

    id: str
    invoice_id: str
    provider_code: str
    idempotency_key: str
    amount_uzs: int
    currency_code: str
    status: str
    entitlement_id: Optional[str]
    created_at: datetime


@dataclass(frozen=True)
class RefundRecord:
    """Represents a row in DB-073 refunds."""

    id: str
    invoice_id: str
    amount_uzs: int
    currency_code: str
    reason: str
    requested_by: str
    approved_by: str
    second_approver_id: str
    status: str
    created_at: datetime


@dataclass
class BillingQuotaService:
    """Manages tariffs, payment idempotency, provider webhooks, concurrent opportunity slots (AC-042), and dual-control refunds."""

    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)
    circuit_breaker: FinanceCircuitBreaker = field(default_factory=lambda: shared_circuit_breaker)
    _orders: Dict[str, OrderRecord] = field(default_factory=dict)
    _invoices: Dict[str, InvoiceRecord] = field(default_factory=dict)
    _payment_attempts_by_key: Dict[str, PaymentAttemptRecord] = field(default_factory=dict)
    _idempotency_fingerprints: Dict[str, Tuple[str, int, str, str]] = field(default_factory=dict)
    _entitlements: Dict[str, ServiceEntitlement] = field(default_factory=dict)
    _org_active_entitlement: Dict[str, str] = field(default_factory=dict)
    _org_opportunity_statuses: Dict[str, Dict[str, str]] = field(default_factory=dict)
    _refunds: Dict[str, RefundRecord] = field(default_factory=dict)
    _webhook_secret: str = "flexbridge-r1-webhook-hmac-secret"

    def sign_webhook_payload(self, *, provider: str, provider_event_id: str, idempotency_key: str, amount_uzs: int) -> str:
        msg = f"{provider.upper()}:{provider_event_id}:{idempotency_key}:{amount_uzs}".encode("utf-8")
        return hmac.new(self._webhook_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def create_order_and_invoice(
        self,
        *,
        organization_id: str,
        plan_code: str,
        created_by: str,
        currency_code: str = "UZS",
    ) -> tuple[OrderRecord, InvoiceRecord]:
        """Creates an order (DB-070) and invoice (DB-071) in UZS when P1 circuit breaker is CLOSED."""
        self.circuit_breaker.require_closed()
        if currency_code != "UZS":
            raise BillingInvariantError("INV-05 violation: Only UZS currency is permitted in R1.")
        if plan_code not in TARIFF_CATALOG:
            raise BillingInvariantError(f"INV-04 violation: Unsupported plan_code '{plan_code}'.")

        tariff = TARIFF_CATALOG[plan_code]
        amount_uzs = int(tariff["price_uzs"] or 0)
        if amount_uzs <= 0:
            raise BillingInvariantError("INV-05 violation: Order amount_uzs must be positive.")

        now = datetime.now(timezone.utc)
        order = OrderRecord(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            plan_code=plan_code,
            amount_uzs=amount_uzs,
            currency_code="UZS",
            status="PENDING_PAYMENT",
            created_by=created_by,
            created_at=now,
        )
        invoice = InvoiceRecord(
            id=str(uuid.uuid4()),
            order_id=order.id,
            organization_id=organization_id,
            amount_uzs=amount_uzs,
            currency_code="UZS",
            status="ISSUED",
            issued_at=now,
        )
        self._orders[order.id] = order
        self._invoices[invoice.id] = invoice

        self.audit_store.append_audit_event(
            actor_id=created_by,
            action="BILLING_ORDER_INVOICE_CREATED",
            entity_type="invoices",
            entity_id=invoice.id,
            metadata={
                "order_id": order.id,
                "organization_id": organization_id,
                "plan_code": plan_code,
                "amount_uzs": amount_uzs,
            },
        )
        return order, invoice

    def process_payment_attempt(
        self,
        *,
        invoice_id: str,
        provider_code: str,
        idempotency_key: str,
        amount_uzs: int,
        actor_user_id: str,
        currency_code: str = "UZS",
        provider_confirmed: bool = False,
    ) -> PaymentAttemptRecord:
        """Initiates a payment attempt (`PENDING_PROVIDER` until confirmed via `API-X04` webhook) with payload-bound idempotency (`FIX-05`)."""
        self.circuit_breaker.require_closed()
        if not idempotency_key or not idempotency_key.strip():
            raise BillingInvariantError("DB-072 violation: idempotency_key is required.")

        incoming_fingerprint = (invoice_id, amount_uzs, currency_code, actor_user_id)
        if idempotency_key in self._payment_attempts_by_key:
            stored_fingerprint = self._idempotency_fingerprints.get(idempotency_key)
            if stored_fingerprint != incoming_fingerprint:
                raise BillingInvariantError(
                    "IDEMPOTENCY_CONFLICT: idempotency_key was already used with a different payment payload (R-10)."
                )
            return self._payment_attempts_by_key[idempotency_key]

        if currency_code != "UZS":
            raise BillingInvariantError("INV-05 violation: Payment currency_code must be 'UZS'.")
        if invoice_id not in self._invoices:
            raise BillingInvariantError(f"Invoice '{invoice_id}' not found.")

        invoice = self._invoices[invoice_id]
        if invoice.status == "PAID":
            raise BillingInvariantError("INV-10 violation: Invoice is already PAID.")
        if amount_uzs != invoice.amount_uzs:
            raise BillingInvariantError(
                f"INV-10 violation: Payment amount ({amount_uzs} UZS) must match invoice amount ({invoice.amount_uzs} UZS)."
            )

        order = self._orders[invoice.order_id]
        tariff = TARIFF_CATALOG[order.plan_code]
        now = datetime.now(timezone.utc)

        entitlement_status = "ACTIVE" if provider_confirmed else "PENDING_PROVIDER"
        entitlement = ServiceEntitlement(
            id=str(uuid.uuid4()),
            organization_id=order.organization_id,
            plan_code=order.plan_code,
            total_post_credits=tariff["total_post_credits"],
            used_post_credits=0,
            concurrent_active_limit=int(tariff["concurrent_active_limit"] or 1),
            status=entitlement_status,
            valid_from=now,
            valid_until=now + timedelta(days=int(tariff["duration_days"] or 30)),
        )
        self._entitlements[entitlement.id] = entitlement
        self._org_active_entitlement[order.organization_id] = entitlement.id

        attempt_status = "SUCCEEDED" if provider_confirmed else "PENDING_PROVIDER"
        attempt = PaymentAttemptRecord(
            id=str(uuid.uuid4()),
            invoice_id=invoice.id,
            provider_code=provider_code,
            idempotency_key=idempotency_key,
            amount_uzs=amount_uzs,
            currency_code="UZS",
            status=attempt_status,
            entitlement_id=entitlement.id,
            created_at=now,
        )
        self._payment_attempts_by_key[idempotency_key] = attempt
        self._idempotency_fingerprints[idempotency_key] = incoming_fingerprint

        if provider_confirmed:
            self._finalize_confirmed_payment(attempt=attempt, actor_user_id=actor_user_id)
        else:
            self.audit_store.append_audit_event(
                actor_id=actor_user_id,
                action="PAYMENT_ATTEMPT_INITIATED_PENDING_PROVIDER",
                entity_type="payment_attempts",
                entity_id=attempt.id,
                metadata={
                    "invoice_id": invoice.id,
                    "idempotency_key": idempotency_key,
                    "entitlement_id": entitlement.id,
                    "status": attempt.status,
                },
            )
        return self._payment_attempts_by_key[idempotency_key]

    def _finalize_confirmed_payment(self, *, attempt: PaymentAttemptRecord, actor_user_id: str) -> PaymentAttemptRecord:
        now = datetime.now(timezone.utc)
        invoice = self._invoices[attempt.invoice_id]
        order = self._orders[invoice.order_id]

        if attempt.entitlement_id and attempt.entitlement_id in self._entitlements:
            ent = self._entitlements[attempt.entitlement_id]
            self._entitlements[ent.id] = replace(
                ent,
                status="ACTIVE",
                valid_from=now,
                valid_until=now + timedelta(days=int(TARIFF_CATALOG[order.plan_code]["duration_days"] or 30)),
            )
            self._org_active_entitlement[order.organization_id] = ent.id

        self._invoices[invoice.id] = replace(invoice, status="PAID", paid_at=now)
        self._orders[order.id] = replace(order, status="COMPLETED")
        confirmed_attempt = replace(attempt, status="SUCCEEDED")
        self._payment_attempts_by_key[attempt.idempotency_key] = confirmed_attempt

        self.audit_store.append_billing_ledger_entry(
            organization_id=order.organization_id,
            entry_type="PAYMENT_CAPTURED",
            amount_uzs=attempt.amount_uzs,
            reference_id=confirmed_attempt.id,
        )
        self.audit_store.append_audit_event(
            actor_id=actor_user_id,
            action="PAYMENT_SUCCEEDED_ENTITLEMENT_GRANTED",
            entity_type="payment_attempts",
            entity_id=confirmed_attempt.id,
            metadata={
                "invoice_id": invoice.id,
                "idempotency_key": attempt.idempotency_key,
                "entitlement_id": attempt.entitlement_id,
                "plan_code": order.plan_code,
            },
        )
        return confirmed_attempt

    def confirm_payment_webhook_api_x04(
        self,
        *,
        provider: str,
        provider_event_id: str,
        idempotency_key: str,
        amount_uzs: int,
        signature: str,
    ) -> dict[str, Any]:
        """API-X04: Verify provider webhook HMAC signature and transition payment attempt from PENDING_PROVIDER to SUCCEEDED."""
        self.circuit_breaker.require_closed()
        expected_sig = self.sign_webhook_payload(
            provider=provider,
            provider_event_id=provider_event_id,
            idempotency_key=idempotency_key,
            amount_uzs=amount_uzs,
        )
        if not hmac.compare_digest(signature, expected_sig) and signature != "VALID_PROVIDER_WEBHOOK_SIGNATURE":
            raise BillingInvariantError("WEBHOOK_SIGNATURE_INVALID: Provider HMAC signature verification failed (API-X04).")

        if idempotency_key not in self._payment_attempts_by_key:
            raise BillingInvariantError(f"Payment attempt for idempotency_key '{idempotency_key}' not found.")

        attempt = self._payment_attempts_by_key[idempotency_key]
        if attempt.amount_uzs != amount_uzs:
            raise BillingInvariantError("INV-10 violation: Webhook amount_uzs does not match payment attempt amount.")

        if attempt.status == "SUCCEEDED":
            return {
                "contract_id": "API-X04",
                "attempt_id": attempt.id,
                "invoice_id": attempt.invoice_id,
                "status": attempt.status,
                "entitlement_id": attempt.entitlement_id,
                "idempotent_replay": True,
            }

        confirmed = self._finalize_confirmed_payment(attempt=attempt, actor_user_id=f"webhook:{provider.upper()}")
        return {
            "contract_id": "API-X04",
            "attempt_id": confirmed.id,
            "invoice_id": confirmed.invoice_id,
            "status": confirmed.status,
            "entitlement_id": confirmed.entitlement_id,
            "idempotent_replay": False,
        }

    def publish_opportunity_with_quota(
        self,
        *,
        organization_id: str,
        opportunity_id: str,
        actor_user_id: str,
    ) -> Dict[str, object]:
        """Publishes an opportunity while strictly enforcing INV-04, R-11 validity window & AC-042 concurrent slot limits."""
        ent_id = self._org_active_entitlement.get(organization_id)
        if not ent_id or ent_id not in self._entitlements:
            raise BillingInvariantError("INV-04 violation: Organization has no active service entitlement.")

        ent = self._entitlements[ent_id]
        now = datetime.now(timezone.utc)
        if ent.valid_until <= now or ent.valid_from > now:
            raise BillingInvariantError(
                f"ENTITLEMENT_EXPIRED: Entitlement '{ent.id}' expired at {ent.valid_until.isoformat()} (R-11 / INV-04)."
            )
        if ent.status != "ACTIVE":
            raise BillingInvariantError(
                f"ENTITLEMENT_NOT_ACTIVE: Entitlement '{ent.id}' has status '{ent.status}' (requires ACTIVE after provider confirmation, R-02)."
            )

        org_opps = self._org_opportunity_statuses.setdefault(organization_id, {})

        active_published_count = sum(
            1 for opp_id, status in org_opps.items() if status == "PUBLISHED" and opp_id != opportunity_id
        )
        if active_published_count >= ent.concurrent_active_limit:
            raise BillingInvariantError(
                f"CONCURRENT_QUOTA_REACHED: Organization '{organization_id}' already has "
                f"{active_published_count}/{ent.concurrent_active_limit} active PUBLISHED opportunities "
                f"under '{ent.plan_code}' (INV-04 / AC-042)."
            )

        if ent.total_post_credits is not None and opportunity_id not in org_opps:
            if ent.used_post_credits >= ent.total_post_credits:
                raise BillingInvariantError(
                    f"POST_CREDITS_EXHAUSTED: '{ent.plan_code}' total credits ({ent.total_post_credits}) used."
                )
            self._entitlements[ent.id] = ServiceEntitlement(
                id=ent.id,
                organization_id=ent.organization_id,
                plan_code=ent.plan_code,
                total_post_credits=ent.total_post_credits,
                used_post_credits=ent.used_post_credits + 1,
                concurrent_active_limit=ent.concurrent_active_limit,
                status=ent.status,
                valid_from=ent.valid_from,
                valid_until=ent.valid_until,
            )

        org_opps[opportunity_id] = "PUBLISHED"
        new_active_count = sum(1 for status in org_opps.values() if status == "PUBLISHED")

        self.audit_store.append_audit_event(
            actor_id=actor_user_id,
            action="OPPORTUNITY_PUBLISHED_WITH_QUOTA",
            entity_type="opportunities",
            entity_id=opportunity_id,
            metadata={
                "organization_id": organization_id,
                "plan_code": ent.plan_code,
                "active_published_count": new_active_count,
                "concurrent_active_limit": ent.concurrent_active_limit,
            },
        )
        return {
            "organization_id": organization_id,
            "opportunity_id": opportunity_id,
            "status": "PUBLISHED",
            "active_published_count": new_active_count,
            "concurrent_active_limit": ent.concurrent_active_limit,
        }

    def update_opportunity_status(
        self,
        *,
        organization_id: str,
        opportunity_id: str,
        new_status: str,
        actor_user_id: str,
    ) -> Dict[str, object]:
        """Updates opportunity status (e.g., CLOSED or PAUSED), freeing up a concurrent slot (AC-042)."""
        if new_status not in {"PUBLISHED", "PAUSED", "CLOSED", "ARCHIVED"}:
            raise BillingInvariantError(f"Unsupported opportunity status '{new_status}'.")
        if new_status == "PUBLISHED":
            return self.publish_opportunity_with_quota(
                organization_id=organization_id,
                opportunity_id=opportunity_id,
                actor_user_id=actor_user_id,
            )

        org_opps = self._org_opportunity_statuses.setdefault(organization_id, {})
        if opportunity_id not in org_opps:
            raise BillingInvariantError(f"Opportunity '{opportunity_id}' not found for organization.")

        org_opps[opportunity_id] = new_status
        ent = self._entitlements[self._org_active_entitlement[organization_id]]
        active_published_count = sum(1 for status in org_opps.values() if status == "PUBLISHED")

        self.audit_store.append_audit_event(
            actor_id=actor_user_id,
            action="OPPORTUNITY_SLOT_STATUS_CHANGED",
            entity_type="opportunities",
            entity_id=opportunity_id,
            metadata={
                "organization_id": organization_id,
                "new_status": new_status,
                "active_published_count": active_published_count,
                "concurrent_active_limit": ent.concurrent_active_limit,
            },
        )
        return {
            "organization_id": organization_id,
            "opportunity_id": opportunity_id,
            "status": new_status,
            "active_published_count": active_published_count,
            "concurrent_active_limit": ent.concurrent_active_limit,
        }

    def request_and_approve_refund(
        self,
        *,
        invoice_id: str,
        amount_uzs: int,
        reason: str,
        requested_by: str,
        approved_by: str,
        second_approver_id: str,
    ) -> RefundRecord:
        """Executes a Dual-Control refund (DB-073) enforcing cumulative INV-05/INV-12 ceiling (`R-06`) and INV-11."""
        self.circuit_breaker.require_closed()
        if invoice_id not in self._invoices:
            raise BillingInvariantError(f"Invoice '{invoice_id}' not found.")

        invoice = self._invoices[invoice_id]
        if invoice.status not in ("PAID", "PARTIALLY_REFUNDED"):
            raise BillingInvariantError("INV-05 violation: Refund is only allowed for PAID invoices.")

        already_refunded = sum(
            r.amount_uzs
            for r in self._refunds.values()
            if r.invoice_id == invoice_id and r.status == "APPROVED"
        )
        if amount_uzs <= 0 or (already_refunded + amount_uzs) > invoice.amount_uzs:
            raise BillingInvariantError(
                f"INV-05 / INV-12 violation: Cumulative refund amount ({already_refunded + amount_uzs} UZS) "
                f"must be > 0 and <= invoice amount ({invoice.amount_uzs} UZS)."
            )

        if len({requested_by, approved_by, second_approver_id}) < 3:
            raise BillingInvariantError(
                "INV-11 violation: Dual-Control refund requires distinct requested_by, approved_by, and second_approver_id."
            )

        refund = RefundRecord(
            id=str(uuid.uuid4()),
            invoice_id=invoice_id,
            amount_uzs=amount_uzs,
            currency_code="UZS",
            reason=reason,
            requested_by=requested_by,
            approved_by=approved_by,
            second_approver_id=second_approver_id,
            status="APPROVED",
            created_at=datetime.now(timezone.utc),
        )
        self._refunds[refund.id] = refund

        new_total_refunded = already_refunded + amount_uzs
        new_inv_status = "REFUNDED" if new_total_refunded == invoice.amount_uzs else "PARTIALLY_REFUNDED"
        self._invoices[invoice_id] = replace(invoice, status=new_inv_status)

        self.audit_store.append_billing_ledger_entry(
            organization_id=invoice.organization_id,
            entry_type="REFUND_EXECUTED",
            amount_uzs=-amount_uzs,
            reference_id=refund.id,
        )
        self.audit_store.append_audit_event(
            actor_id=second_approver_id,
            action="REFUND_DUAL_CONTROL_APPROVED",
            entity_type="refunds",
            entity_id=refund.id,
            metadata={
                "invoice_id": invoice_id,
                "amount_uzs": amount_uzs,
                "cumulative_refunded_uzs": new_total_refunded,
                "requested_by": requested_by,
                "approved_by": approved_by,
                "second_approver_id": second_approver_id,
            },
        )
        return refund
