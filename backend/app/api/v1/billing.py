from dataclasses import asdict
from uuid import UUID
from fastapi import APIRouter,Depends
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import ActorContext,require_actor_context
from app.services.billing import BillingQuotaService

billing_service=BillingQuotaService()
router=APIRouter(prefix='/api/v1/billing',tags=['billing'])
class Request(BaseModel): model_config=ConfigDict(extra='forbid')
class CreateOrderRequest(Request):
    organization_id:UUID
    plan_code:str
    idempotency_key:str=Field(min_length=8,max_length=128)
class PaymentAttemptRequest(Request):
    invoice_id:UUID
    provider_code:str='HMAC'
    idempotency_key:str=Field(min_length=8,max_length=128)
    amount_uzs:int=Field(gt=0)
    currency_code:str='UZS'
class RefundRequest(Request):
    invoice_id:UUID
    amount_uzs:int=Field(gt=0)
    reason:str=Field(min_length=15,max_length=2000)
class PublishRequest(Request):
    organization_id:UUID
    opportunity_id:UUID

@router.post('/orders',status_code=201)
def order(req:CreateOrderRequest,actor:ActorContext=Depends(require_actor_context)):
    o,i=billing_service.create_order_and_invoice(organization_id=str(req.organization_id),plan_code=req.plan_code,
        actor=actor,idempotency_key=req.idempotency_key)
    return {'order_id':o.id,'invoice_id':i.id,'amount_uzs':i.amount_uzs,'invoice_status':i.status}

@router.post('/payments/attempts')
def payment(req:PaymentAttemptRequest,actor:ActorContext=Depends(require_actor_context)):
    r=billing_service.process_payment_attempt(invoice_id=str(req.invoice_id),provider_code=req.provider_code,
        idempotency_key=req.idempotency_key,amount_uzs=req.amount_uzs,currency_code=req.currency_code,actor=actor)
    return {**asdict(r),'attempt_id':r.id}

@router.post('/refunds',status_code=201)
def refund(req:RefundRequest,actor:ActorContext=Depends(require_actor_context)):
    return billing_service.request_refund(invoice_id=str(req.invoice_id),amount_uzs=req.amount_uzs,reason=req.reason,actor=actor)

@router.post('/slots/publish')
def publish(req:PublishRequest,actor:ActorContext=Depends(require_actor_context)):
    return billing_service.publish_opportunity_with_quota(organization_id=str(req.organization_id),opportunity_id=str(req.opportunity_id),actor_user_id=actor.user_id)
