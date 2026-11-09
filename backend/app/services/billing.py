"""PostgreSQL transactions for orders, captures, quota and independently approved refunds."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import hashlib
import hmac
import json
import os
import time
from uuid import uuid4, uuid5, NAMESPACE_URL
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from app.db.storage import table, transaction, now, enqueue
from app.core.circuit_breaker import shared_circuit_breaker
from app.core.audit import AppendOnlyAuditStore

class BillingInvariantError(ValueError):
    pass

TARIFF_CATALOG={
    'SINGLE_POST_30D':{'price_uzs':149000,'total_post_credits':1,'concurrent_active_limit':1,'duration_days':30},
    'ORG_PLAN_30D':{'price_uzs':599000,'total_post_credits':None,'concurrent_active_limit':5,'duration_days':30}}

@dataclass(frozen=True)
class OrderRecord:
    id:str; organization_id:str; plan_code:str; amount_uzs:int; currency_code:str; status:str; created_by:str; created_at:object
@dataclass(frozen=True)
class InvoiceRecord:
    id:str; order_id:str; organization_id:str; amount_uzs:int; currency_code:str; status:str; issued_at:object; paid_at:object=None
@dataclass(frozen=True)
class PaymentAttemptRecord:
    id:str; invoice_id:str; provider_code:str; idempotency_key:str; amount_uzs:int; currency_code:str; status:str; entitlement_id:str|None; created_at:object

def _id(label): return str(uuid5(NAMESPACE_URL,'flexbridge:'+label))
def _fingerprint(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class BillingQuotaService:
    circuit_breaker=shared_circuit_breaker
    audit_store=AppendOnlyAuditStore()

    def _guard(self,conn,org):
        self.circuit_breaker.require_closed()
        if not conn.execute(select(table('organizations').c.id).where(table('organizations').c.id==org).with_for_update()).first():
            raise BillingInvariantError('ORGANIZATION_NOT_FOUND')

    def _audit(self,actor,action,kind,key,meta=None):
        self.audit_store.append_audit_event(actor_id=actor,action=action,entity_type=kind,entity_id=key,metadata=meta or {})

    def _seed_tariff(self,conn,code):
        if code not in TARIFF_CATALOG: raise BillingInvariantError('UNKNOWN_TARIFF')
        tariff=TARIFF_CATALOG[code]
        # Versioned product seed is deterministic and never changes an existing price.
        conn.execute(insert(table('products')).values(id=_id(code),created_at=now(),updated_at=now(),code=code,
            name=code,service_kind=code,active=True).on_conflict_do_nothing(index_elements=['id']))
        price_id=_id(code+':v1')
        conn.execute(insert(table('price_versions')).values(id=price_id,created_at=now(),updated_at=now(),product_id=_id(code),version=1,
            amount=tariff['price_uzs'],currency='UZS',duration_days=30,tax_included=True,valid_from=now()).on_conflict_do_nothing(index_elements=['id']))
        return price_id,tariff

    def create_order_and_invoice(self,*,actor,organization_id,plan_code,currency_code='UZS',idempotency_key=None):
        from app.services.authority import mfa_authority,org_authority
        created_by=actor.user_id
        if currency_code!='UZS': raise BillingInvariantError('INVALID_CURRENCY')
        key=idempotency_key or str(uuid4())
        with transaction() as conn:
            self._guard(conn,organization_id)
            mfa_authority(conn,actor)
            org_authority(conn,actor.user_id,organization_id,'OWNER','BILLING')
            price_id,tariff=self._seed_tariff(conn,plan_code)
            # Same user and operation key cannot be reused for a different target or price.
            digest=_fingerprint([organization_id,plan_code,currency_code])
            replay=self._claim(conn,created_by,'CREATE_ORDER',key,digest)
            if replay:
                order=self._get_order(replay,conn)
                invoice=self._invoice_for_order(replay,conn)
                return order,invoice
            order_id,invoice_id=str(uuid4()),str(uuid4())
            conn.execute(table('orders').insert().values(id=order_id,created_at=now(),updated_at=now(),organization_id=organization_id,
                purchaser_id=created_by,price_id=price_id,amount=tariff['price_uzs'],currency='UZS',price_snapshot={'plan_code':plan_code,**tariff},
                status='PENDING_PAYMENT',idempotency_key=str(uuid4())))
            conn.execute(table('invoices').insert().values(id=invoice_id,created_at=now(),updated_at=now(),order_id=order_id,
                number='FB-'+invoice_id,amount=tariff['price_uzs'],currency='UZS',fiscal_status='PENDING',issued_at=now()))
            self._finish(conn,created_by,'CREATE_ORDER',key,order_id)
            self._audit(created_by,'ORDER_CREATED','order',order_id)
            return self._get_order(order_id,conn),self._invoice_for_order(order_id,conn)

    def _claim(self,conn,user,operation,key,digest):
        idem=table('idempotency_keys')
        conn.execute(insert(idem).values(id=str(uuid4()),created_at=now(),updated_at=now(),user_id=user,operation=operation,
            key=key,request_digest=digest,expires_at=now()+timedelta(days=1)).on_conflict_do_nothing(index_elements=['user_id','operation','key']))
        row=conn.execute(select(idem).where(idem.c.user_id==user,idem.c.operation==operation,idem.c.key==key).with_for_update()).mappings().one()
        if row['request_digest']!=digest: raise BillingInvariantError('IDEMPOTENCY_CONFLICT')
        return row['response_ref']

    def _finish(self,conn,user,operation,key,ref):
        t=table('idempotency_keys')
        conn.execute(t.update().where(t.c.user_id==user,t.c.operation==operation,t.c.key==key)
            .values(response_status=200,response_ref=ref,updated_at=now()))

    def _get_order(self,id,conn=None):
        with transaction() as c:
            r=(conn or c).execute(select(table('orders')).where(table('orders').c.id==id)).mappings().first()
            return OrderRecord(r['id'],r['organization_id'],r['price_snapshot']['plan_code'],int(r['amount']),r['currency'],r['status'],r['purchaser_id'],r['created_at']) if r else None

    def _invoice_for_order(self,id,conn):
        r=conn.execute(select(table('invoices')).where(table('invoices').c.order_id==id)).mappings().one()
        org=conn.execute(select(table('orders').c.organization_id).where(table('orders').c.id==id)).scalar_one()
        return InvoiceRecord(r['id'],id,org,int(r['amount']),r['currency'],'PAID' if r['paid_at'] else 'ISSUED',r['issued_at'],r['paid_at'])

    def _get_invoice(self,id):
        with transaction() as conn:
            oid=conn.execute(select(table('invoices').c.order_id).where(table('invoices').c.id==id)).scalar_one_or_none()
            return self._invoice_for_order(oid,conn) if oid else None

    def _attempt(self,conn,id,key=''):
        r=conn.execute(select(table('payment_attempts')).where(table('payment_attempts').c.id==id)).mappings().one()
        invoice=self._invoice_for_order(r['order_id'],conn)
        entitlement=conn.execute(select(table('service_entitlements').c.id).where(table('service_entitlements').c.order_id==r['order_id'])).scalar_one_or_none()
        return PaymentAttemptRecord(r['id'],invoice.id,r['provider'],key,int(r['amount']),r['currency'],r['status'],entitlement,r['created_at'])

    def process_payment_attempt(self,*,actor,invoice_id,provider_code,idempotency_key,amount_uzs,currency_code='UZS',provider_confirmed=False):
        from app.services.authority import mfa_authority,org_authority
        actor_user_id=actor.user_id
        if provider_confirmed: raise BillingInvariantError('PROVIDER_CONFIRMATION_MUST_USE_AUTHENTICATED_CALLBACK')
        if provider_code!='HMAC': raise BillingInvariantError('PROVIDER_ADAPTER_NOT_CONFIGURED')
        with transaction() as conn:
            inv=self._get_invoice(invoice_id)
            if not inv: raise BillingInvariantError('INVOICE_NOT_FOUND')
            self._guard(conn,inv.organization_id)
            invoice=conn.execute(select(table('invoices')).where(table('invoices').c.id==invoice_id).with_for_update()).mappings().one()
            mfa_authority(conn,actor)
            org_authority(conn,actor.user_id,inv.organization_id,'OWNER','BILLING')
            replay=self._claim(conn,actor_user_id,'PAYMENT_ATTEMPT',idempotency_key,_fingerprint([invoice_id,provider_code,amount_uzs,currency_code]))
            if replay: return self._attempt(conn,replay,idempotency_key)
            if invoice['paid_at']: raise BillingInvariantError('INVOICE_ALREADY_PAID')
            if Decimal(amount_uzs)!=invoice['amount'] or currency_code!=invoice['currency']: raise BillingInvariantError('PAYMENT_AMOUNT_MISMATCH')
            attempt_id=str(uuid4())
            conn.execute(table('payment_attempts').insert().values(id=attempt_id,created_at=now(),updated_at=now(),order_id=invoice['order_id'],
                provider=provider_code,amount=invoice['amount'],currency=invoice['currency'],status='PENDING_PROVIDER',requested_at=now()))
            self._finish(conn,actor_user_id,'PAYMENT_ATTEMPT',idempotency_key,attempt_id)
            return self._attempt(conn,attempt_id,idempotency_key)

    def sign_webhook_payload(self,*,provider,provider_event_id,attempt_id,amount_uzs,currency='UZS',timestamp):
        if provider!='HMAC': raise BillingInvariantError('PROVIDER_ADAPTER_NOT_CONFIGURED')
        secret=os.environ.get('PAYMENT_WEBHOOK_SECRET','')
        if len(secret)<32: raise BillingInvariantError('PAYMENT_WEBHOOK_NOT_CONFIGURED')
        body=json.dumps([provider,provider_event_id,str(attempt_id),amount_uzs,currency,timestamp],separators=(',',':'))
        return hmac.new(secret.encode(),body.encode(),hashlib.sha256).hexdigest()

    def confirm_payment_webhook_api_x04(self,*,provider,provider_event_id,attempt_id,amount_uzs,signature,timestamp,currency='UZS'):
        expected=self.sign_webhook_payload(provider=provider,provider_event_id=provider_event_id,attempt_id=attempt_id,
            amount_uzs=amount_uzs,currency=currency,timestamp=timestamp)
        if abs(time.time()-timestamp)>300 or not hmac.compare_digest(signature,expected): raise BillingInvariantError('WEBHOOK_SIGNATURE_INVALID')
        with transaction() as conn:
            pa,orders=table('payment_attempts'),table('orders')
            original=conn.execute(select(pa).where(pa.c.id==attempt_id)).mappings().first()
            if not original: raise BillingInvariantError('PAYMENT_ATTEMPT_NOT_FOUND')
            order=conn.execute(select(orders).where(orders.c.id==original['order_id'])).mappings().one()
            # Captured facts can arrive during an incident; no new checkout/refund is admitted.
            conn.execute(select(table('organizations').c.id).where(table('organizations').c.id==order['organization_id']).with_for_update())
            order=conn.execute(select(orders).where(orders.c.id==order['id']).with_for_update()).mappings().one()
            attempt=conn.execute(select(pa).where(pa.c.id==attempt_id).with_for_update()).mappings().one()
            if attempt['provider']!=provider or attempt['currency']!=currency or attempt['amount']!=Decimal(amount_uzs):
                raise BillingInvariantError('PAYMENT_AMOUNT_MISMATCH')
            events=table('payment_events')
            digest=_fingerprint([str(attempt_id),amount_uzs,currency])
            previous=conn.execute(select(events).where(events.c.provider==provider,events.c.event_key==provider_event_id)).mappings().first()
            if previous:
                if previous['payload_digest']!=digest: raise BillingInvariantError('PROVIDER_EVENT_CONFLICT')
                return {'attempt_id':attempt_id,'status':'CAPTURED','idempotent_replay':True}
            if attempt['status']=='CAPTURED':
                return {'attempt_id':attempt_id,'status':'CAPTURED','idempotent_replay':True}
            invoice=self._invoice_for_order(order['id'],conn)
            if invoice.paid_at: raise BillingInvariantError('ORDER_ALREADY_CAPTURED')
            conn.execute(events.insert().values(id=str(uuid4()),created_at=now(),updated_at=now(),attempt_id=attempt_id,provider=provider,
                event_key=provider_event_id,payload_digest=digest,normalized_payload={'amount':amount_uzs,'currency':currency},received_at=now(),processed_at=now()))
            conn.execute(pa.update().where(pa.c.id==attempt_id).values(status='CAPTURED',provider_transaction_id=provider_event_id,confirmed_at=now(),updated_at=now()))
            conn.execute(table('invoices').update().where(table('invoices').c.id==invoice.id).values(paid_at=now(),updated_at=now()))
            conn.execute(orders.update().where(orders.c.id==order['id']).values(status='COMPLETED',updated_at=now()))
            tariff=order['price_snapshot']
            conn.execute(table('service_entitlements').insert().values(id=str(uuid4()),created_at=now(),updated_at=now(),organization_id=order['organization_id'],
                order_id=order['id'],service_kind=tariff['plan_code'],status='ACTIVE',starts_at=now(),ends_at=now()+timedelta(days=tariff['duration_days']),
                quota=tariff['total_post_credits'],concurrent_active_limit=tariff['concurrent_active_limit']))
            conn.execute(table('billing_ledger').insert().values(id=str(uuid4()),created_at=now(),updated_at=now(),organization_id=order['organization_id'],
                order_id=order['id'],payment_attempt_id=attempt_id,entry_kind='PAYMENT_CAPTURED',amount=amount_uzs,currency=currency,occurred_at=now(),dedupe_key='capture:'+str(attempt_id)))
            self._audit(None,'PAYMENT_CAPTURED','payment',str(attempt_id))
            return {'attempt_id':attempt_id,'status':'CAPTURED','idempotent_replay':False}

    def active_entitlement(self,organization_id,conn=None):
        t=table('service_entitlements')
        with transaction() as c:
            return (conn or c).execute(select(t).where(t.c.organization_id==organization_id,t.c.status=='ACTIVE',t.c.starts_at<=now(),t.c.ends_at>now())
                .order_by(t.c.ends_at.desc(),t.c.id).limit(1)).mappings().first()

    def publish_opportunity_with_quota(self,*,organization_id,opportunity_id,actor_user_id):
        from app.api.dependencies import ActorContext,require_org
        with transaction() as conn:
            self._guard(conn,organization_id)
            require_org(ActorContext(actor_user_id,'',()),organization_id,'OWNER','HR','HOST_COORDINATOR')
            ent=self.active_entitlement(organization_id,conn)
            if not ent: raise BillingInvariantError('ACTIVE_ENTITLEMENT_REQUIRED')
            opps=table('opportunities')
            opp=conn.execute(select(opps).where(opps.c.id==opportunity_id,opps.c.organization_id==organization_id).with_for_update()).mappings().first()
            if not opp: raise BillingInvariantError('OPPORTUNITY_NOT_FOUND')
            from app.services.organizations import require_capability
            require_capability(conn, organization_id, 'JOB_EMPLOYER' if opp['kind']=='PART_TIME' else 'INTERNSHIP_HOST')
            if opp['status']=='PUBLISHED': return {'status':'PUBLISHED','opportunity_id':opportunity_id}
            if opp['status'] not in ('APPROVED','PAUSED'): raise BillingInvariantError('MODERATION_APPROVAL_REQUIRED')
            count=conn.execute(select(func.count()).select_from(opps).where(opps.c.organization_id==organization_id,opps.c.status=='PUBLISHED',
                (opps.c.expires_at.is_(None)) | (opps.c.expires_at>now()))).scalar_one()
            if count>=ent['concurrent_active_limit']: raise BillingInvariantError('CONCURRENT_QUOTA_REACHED')
            if ent['quota'] is not None and opp['published_at'] is None:
                if ent['quota']<=0: raise BillingInvariantError('POST_CREDITS_EXHAUSTED')
                conn.execute(table('service_entitlements').update().where(table('service_entitlements').c.id==ent['id']).values(quota=ent['quota']-1))
            conn.execute(opps.update().where(opps.c.id==opportunity_id).values(status='PUBLISHED',published_at=opp['published_at'] or now(),expires_at=ent['ends_at'],updated_at=now()))
            conn.execute(table('opportunity_revisions').update().where(table('opportunity_revisions').c.id==opp['current_revision_id'],
                table('opportunity_revisions').c.published_at.is_(None)).values(published_at=now()))
            self._audit(actor_user_id,'OPPORTUNITY_PUBLISHED','opportunity',opportunity_id)
            return {'status':'PUBLISHED','opportunity_id':opportunity_id,'active_published_count':count+1}

    def update_opportunity_status(self,*,opportunity_id,new_status,actor_user_id):
        from app.api.dependencies import ActorContext,require_org
        with transaction() as conn:
            t=table('opportunities')
            row=conn.execute(select(t).where(t.c.id==opportunity_id)).mappings().first()
            if not row: raise BillingInvariantError('OPPORTUNITY_NOT_FOUND')
            conn.execute(select(table('organizations').c.id).where(table('organizations').c.id==row['organization_id']).with_for_update())
            require_org(ActorContext(actor_user_id,'',()),row['organization_id'],'OWNER','HR','HOST_COORDINATOR')
            row=conn.execute(select(t).where(t.c.id==opportunity_id).with_for_update()).mappings().one()
            if new_status not in ('PAUSED','CLOSED') or row['status'] not in ('PUBLISHED','PAUSED'): raise BillingInvariantError('INVALID_OPPORTUNITY_TRANSITION')
            conn.execute(t.update().where(t.c.id==opportunity_id).values(status=new_status,updated_at=now()))
            self._audit(actor_user_id,'OPPORTUNITY_'+new_status,'opportunity',opportunity_id)
            return {'opportunity_id':opportunity_id,'status':new_status}

    def request_refund(self,*,actor,invoice_id,amount_uzs,reason):
        from app.services.authority import mfa_authority,org_authority
        requested_by=actor.user_id
        with transaction() as conn:
            inv=self._get_invoice(invoice_id)
            if not inv: raise BillingInvariantError('INVOICE_NOT_FOUND')
            self._guard(conn,inv.organization_id)
            pa=table('payment_attempts')
            captured=conn.execute(select(pa).where(pa.c.order_id==inv.order_id,pa.c.status=='CAPTURED').with_for_update()).mappings().first()
            mfa_authority(conn,actor)
            org_authority(conn,actor.user_id,inv.organization_id,'OWNER','BILLING')
            if not captured: raise BillingInvariantError('CAPTURED_PAYMENT_REQUIRED')
            refunds=table('refunds')
            reserved=conn.execute(select(func.coalesce(func.sum(refunds.c.amount),0)).where(refunds.c.payment_attempt_id==captured['id'],
                refunds.c.status.not_in(['REJECTED','CANCELLED','FAILED']))).scalar_one()
            if amount_uzs<=0 or Decimal(amount_uzs)+reserved>captured['amount']: raise BillingInvariantError('REFUND_LIMIT_EXCEEDED')
            rid=str(uuid4())
            conn.execute(refunds.insert().values(id=rid,created_at=now(),updated_at=now(),payment_attempt_id=captured['id'],requester_id=requested_by,
                amount=amount_uzs,currency=captured['currency'],reason=reason,status='REQUESTED'))
            self._audit(requested_by,'REFUND_REQUESTED','refund',rid)
            return {'refund_id':rid,'status':'REQUESTED'}

    def approve_refund(self,refund_id,actor):
        from app.services.authority import platform_authority
        actor_id=actor.user_id
        with transaction() as conn:
            self.circuit_breaker.require_closed()
            t=table('refunds')
            r=conn.execute(select(t).where(t.c.id==refund_id).with_for_update()).mappings().first()
            platform_authority(conn,actor,'FINANCE')
            if not r: raise BillingInvariantError('REFUND_NOT_FOUND')
            if actor_id in (r['requester_id'],r['approver_id'],r['second_approver_id']): raise BillingInvariantError('SELF_APPROVAL_FORBIDDEN')
            if r['status'] not in ('REQUESTED','PENDING_SECOND_APPROVAL'): raise BillingInvariantError('INVALID_REFUND_STATE')
            values={'updated_at':now()}
            if r['approver_id'] is None: values.update(approver_id=actor_id,status='PENDING_SECOND_APPROVAL')
            else:
                values.update(second_approver_id=actor_id,status='APPROVED')
                enqueue(conn,'REFUND_EXECUTE',str(refund_id),{'refund_id':str(refund_id)},'refund:'+str(refund_id))
            conn.execute(t.update().where(t.c.id==refund_id).values(**values))
            self._audit(actor_id,'REFUND_APPROVED','refund',str(refund_id))
            return {'refund_id':refund_id,'status':values['status']}

    def request_and_approve_refund(self,**kwargs):
        raise BillingInvariantError('INDEPENDENT_APPROVAL_REQUIRED')
