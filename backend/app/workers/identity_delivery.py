from sqlalchemy import select
from app.db.storage import table,transaction,now
from app.core.iam_security import decrypt
from app.adapters import identity_delivery

def run_delivery(event):
    t=table('auth_challenges')
    with transaction() as conn:
        row=conn.execute(select(t).where(t.c.id==event['payload']['challenge_id'])).mappings().first()
        if not row:return {'sent':False}
        if row['consumed_at'] or row['superseded_at'] or row['expires_at']<=now():return {'sent':False}
        if row['delivery_status']=='SENT':return {'sent':True}
        message=decrypt(row['delivery_encrypted']);destination=decrypt(row['destination_encrypted'])
    identity_delivery.send(challenge_id=row['id'],channel=row['channel'],destination=destination['value'],code=message['code'],
        ttl_seconds=max(1,int((row['expires_at']-now()).total_seconds())))
    return {'sent':True}

def apply_delivery(conn,event,result):
    t=table('auth_challenges')
    conn.execute(t.update().where(t.c.id==event['payload']['challenge_id'],t.c.consumed_at.is_(None),t.c.superseded_at.is_(None))
        .values(delivery_status='SENT' if result['sent'] else 'EXPIRED',sent_at=now() if result['sent'] else None,delivery_encrypted=None))
