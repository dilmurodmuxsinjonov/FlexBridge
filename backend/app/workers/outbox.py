"""Lease/fencing outbox. Effects must succeed before a pending event is acknowledged."""
import logging
import os
import time
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select,or_
from app.db.storage import transaction,now,outbox_table,save_domain_record,init_storage

logger=logging.getLogger(__name__)

def handlers():
    from app.services.files_quarantine import run_scan,apply_scan
    from app.workers.refunds import run_refund,apply_refund
    from app.workers.identity_delivery import run_delivery,apply_delivery
    return {'FILE_SCAN_REQUESTED':(run_scan,apply_scan),'REFUND_EXECUTE':(run_refund,apply_refund),'AUTH_OTP_DELIVERY':(run_delivery,apply_delivery)}

def relay_pending_outbox_events(batch_size=50,registry=None,event_types=None):
    registry=handlers() if registry is None else registry
    worker=str(uuid4());claimed=[]
    with transaction() as conn:
        query=select(outbox_table).where(outbox_table.c.processed_at.is_(None),outbox_table.c.available_at<=now(),
            outbox_table.c.attempts<5,or_(outbox_table.c.lease_until.is_(None),outbox_table.c.lease_until<now()))
        if event_types is not None:query=query.where(outbox_table.c.event_type.in_(event_types))
        rows=conn.execute(query.order_by(outbox_table.c.available_at,outbox_table.c.id).limit(batch_size).with_for_update(skip_locked=True)).mappings().all()
        for r in rows:
            token=str(uuid4())
            conn.execute(outbox_table.update().where(outbox_table.c.id==r['id']).values(claimed_by=worker,claim_token=token,
                lease_until=now()+timedelta(seconds=120),attempts=r['attempts']+1,updated_at=now()))
            claimed.append(({**r,'attempts':r['attempts']+1},token))
    completed=0
    for event,token in claimed:
        try:
            execute,apply=registry[event['event_type']]
            result=execute(event)
            with transaction() as conn:
                current=conn.execute(select(outbox_table.c.claim_token).where(outbox_table.c.id==event['id']).with_for_update()).scalar_one()
                if str(current)!=token: continue
                apply(conn,event,result)
                conn.execute(outbox_table.update().where(outbox_table.c.id==event['id']).values(processed_at=now(),lease_until=None,updated_at=now()))
                completed+=1
        except Exception as exc:
            # No payloads, credentials or raw provider responses in logs.
            logger.warning('Outbox attempt failed: %s (%s)',event['id'],type(exc).__name__)
            with transaction() as conn:
                conn.execute(outbox_table.update().where(outbox_table.c.id==event['id'],outbox_table.c.claim_token==token)
                    .values(lease_until=None,available_at=now()+timedelta(seconds=min(2**event['attempts'],60)),updated_at=now()))
    return completed

def main():
    init_storage()
    event_types=tuple(v.strip() for v in os.environ.get('OUTBOX_EVENT_TYPES','FILE_SCAN_REQUESTED,REFUND_EXECUTE').split(',') if v.strip())
    heartbeat_key=os.environ.get('OUTBOX_WORKER_KEY','outbox')
    last_identity_cleanup=0
    while True:
        if 'AUTH_OTP_DELIVERY' in event_types and time.monotonic()-last_identity_cleanup>=30:
            from app.services.identity import identity_service
            identity_service.expire_state()
            last_identity_cleanup=time.monotonic()
        # A serial worker does not reserve a large batch whose later leases would expire while waiting.
        completed=relay_pending_outbox_events(batch_size=1,event_types=event_types)
        save_domain_record('worker_heartbeat',heartbeat_key,{'at':now().isoformat()})
        if not completed:time.sleep(.5)

if __name__=='__main__': main()
