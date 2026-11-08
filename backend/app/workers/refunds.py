import os
from uuid import uuid4
import httpx
from sqlalchemy import select
from app.db.storage import table,transaction,now
from app.core.circuit_breaker import shared_circuit_breaker

def run_refund(event):
    with transaction() as conn:
        shared_circuit_breaker.require_closed()
        refund=conn.execute(select(table('refunds')).where(table('refunds').c.id==event['payload']['refund_id'])).mappings().one()
        if refund['status']=='REFUNDED': return {'already_done':True}
        if refund['status']!='APPROVED': raise ValueError('Refund is not approved')
        payment=conn.execute(select(table('payment_attempts')).where(table('payment_attempts').c.id==refund['payment_attempt_id'])).mappings().one()
    url=os.environ.get('PAYMENT_GATEWAY_URL','')
    secret=os.environ.get('PAYMENT_GATEWAY_TOKEN','')
    if not url.startswith('https://') or not secret: raise RuntimeError('Refund provider gateway is not configured')
    with httpx.Client(timeout=15) as client:
        response=client.post(url.rstrip('/')+'/refunds',headers={'Authorization':'Bearer '+secret,'Idempotency-Key':str(refund['id'])},
            json={'refund_id':str(refund['id']),'payment_attempt_id':str(payment['id']),'provider':payment['provider'],
                'provider_transaction_id':payment['provider_transaction_id'],'amount':str(refund['amount']),'currency':refund['currency']})
        response.raise_for_status();result=response.json()
    if result.get('refund_id')!=str(refund['id']) or result.get('status')!='REFUNDED' or not result.get('provider_refund_id'):
        raise ValueError('Refund provider result is not final')
    return result

def apply_refund(conn,event,result):
    t=table('refunds')
    # Serialize entitlement revocation with publication and checkout for this organization.
    initial=conn.execute(select(t).where(t.c.id==event['payload']['refund_id'])).mappings().one()
    initial_payment=conn.execute(select(table('payment_attempts')).where(table('payment_attempts').c.id==initial['payment_attempt_id'])).mappings().one()
    organization_id=conn.execute(select(table('orders').c.organization_id).where(table('orders').c.id==initial_payment['order_id'])).scalar_one()
    conn.execute(select(table('organizations').c.id).where(table('organizations').c.id==organization_id).with_for_update())
    refund=conn.execute(select(t).where(t.c.id==event['payload']['refund_id']).with_for_update()).mappings().one()
    if refund['status']=='REFUNDED': return
    if result.get('already_done'): raise ValueError('Refund state changed during execution')
    payment=conn.execute(select(table('payment_attempts')).where(table('payment_attempts').c.id==refund['payment_attempt_id'])).mappings().one()
    order=conn.execute(select(table('orders')).where(table('orders').c.id==payment['order_id'])).mappings().one()
    conn.execute(t.update().where(t.c.id==refund['id']).values(status='REFUNDED',provider_refund_id=result['provider_refund_id'],resolved_at=now(),updated_at=now()))
    conn.execute(table('billing_ledger').insert().values(id=str(uuid4()),created_at=now(),updated_at=now(),organization_id=order['organization_id'],
        order_id=order['id'],payment_attempt_id=payment['id'],refund_id=refund['id'],entry_kind='REFUND_EXECUTED',amount=-refund['amount'],currency=refund['currency'],
        occurred_at=now(),dedupe_key='refund:'+str(refund['id'])))
    # A paid plan under refund is not available for future publication.
    conn.execute(table('service_entitlements').update().where(table('service_entitlements').c.order_id==order['id']).values(status='REFUNDED',updated_at=now()))
