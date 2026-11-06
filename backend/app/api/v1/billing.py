"""S2.8.1: FastAPI Endpoints for Tariffs, Payments, Concurrent Slot Quota (AC-042) & Refunds."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.billing import BillingInvariantError, BillingQuotaService

router = APIRouter(prefix="/api/v1/billing", tags=["billing-quota"])
billing_service = BillingQuotaService()


class CreateOrderRequest(BaseModel):
    organization_id: str
    plan_code: str
    created_by: str
    currency_code: str = "UZS"


class PaymentAttemptRequest(BaseModel):
    invoice_id: str
    provider_code: str = "PAYME"
    idempotency_key: str
    amount_uzs: int
    actor_user_id: str
    currency_code: str = "UZS"


class OpportunityQuotaPublishRequest(BaseModel):
    organization_id: str
    opportunity_id: str
    actor_user_id: str


class OpportunityStatusUpdateRequest(BaseModel):
    organization_id: str
    opportunity_id: str
    new_status: str
    actor_user_id: str


class RefundRequest(BaseModel):
    invoice_id: str
    amount_uzs: int
    reason: str
    requested_by: str
    approved_by: str
    second_approver_id: str


@router.post("/orders", status_code=201)
def create_order_endpoint(req: CreateOrderRequest):
    try:
        order, invoice = billing_service.create_order_and_invoice(
            organization_id=req.organization_id,
            plan_code=req.plan_code,
            created_by=req.created_by,
            currency_code=req.currency_code,
        )
        return {
            "order_id": order.id,
            "invoice_id": invoice.id,
            "plan_code": order.plan_code,
            "amount_uzs": invoice.amount_uzs,
            "currency_code": invoice.currency_code,
            "invoice_status": invoice.status,
        }
    except BillingInvariantError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/payments/attempts")
def process_payment_attempt_endpoint(req: PaymentAttemptRequest):
    try:
        attempt = billing_service.process_payment_attempt(
            invoice_id=req.invoice_id,
            provider_code=req.provider_code,
            idempotency_key=req.idempotency_key,
            amount_uzs=req.amount_uzs,
            actor_user_id=req.actor_user_id,
            currency_code=req.currency_code,
        )
        return {
            "attempt_id": attempt.id,
            "invoice_id": attempt.invoice_id,
            "idempotency_key": attempt.idempotency_key,
            "amount_uzs": attempt.amount_uzs,
            "status": attempt.status,
            "entitlement_id": attempt.entitlement_id,
        }
    except BillingInvariantError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/slots/publish")
def publish_slot_endpoint(req: OpportunityQuotaPublishRequest):
    try:
        return billing_service.publish_opportunity_with_quota(
            organization_id=req.organization_id,
            opportunity_id=req.opportunity_id,
            actor_user_id=req.actor_user_id,
        )
    except BillingInvariantError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/slots/status")
def update_slot_status_endpoint(req: OpportunityStatusUpdateRequest):
    try:
        return billing_service.update_opportunity_status(
            organization_id=req.organization_id,
            opportunity_id=req.opportunity_id,
            new_status=req.new_status,
            actor_user_id=req.actor_user_id,
        )
    except BillingInvariantError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/refunds", status_code=201)
def create_refund_endpoint(req: RefundRequest):
    try:
        refund = billing_service.request_and_approve_refund(
            invoice_id=req.invoice_id,
            amount_uzs=req.amount_uzs,
            reason=req.reason,
            requested_by=req.requested_by,
            approved_by=req.approved_by,
            second_approver_id=req.second_approver_id,
        )
        return {
            "refund_id": refund.id,
            "invoice_id": refund.invoice_id,
            "amount_uzs": refund.amount_uzs,
            "status": refund.status,
        }
    except BillingInvariantError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
