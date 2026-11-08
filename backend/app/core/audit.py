"""Audit and ledger writes share the business transaction and PostgreSQL immutability guards."""
from uuid import UUID, uuid4
from sqlalchemy import select
from app.db.storage import table, transaction, now, json_value

class ImmutableRecordError(Exception):
    def __init__(self,table,message='Record is immutable',sqlstate='23514'):
        super().__init__(message)
        self.table,self.sqlstate=table,sqlstate

class AppendOnlyAuditStore:
    def append_audit_event(self,*,actor_id,action,entity_type,entity_id,metadata=None):
        event_id=str(uuid4())
        # System jobs have no impersonated user. HTTP callers always supply their authenticated UUID.
        if actor_id:
            actor_id=str(UUID(str(actor_id)))
        with transaction() as conn:
            conn.execute(table('audit_events').insert().values(id=event_id,created_at=now(),updated_at=now(),actor_id=actor_id,
                action=action,object_type=entity_type,object_key=str(entity_id),scope_snapshot=json_value(metadata or {}),
                request_id=str(uuid4()),occurred_at=now()))
        return {'id':event_id,'action':action,'entity_id':entity_id}

    def append_consent_event(self,*,user_id,consent_type,policy_version,granted):
        with transaction() as conn:
            conn.execute(table('consent_events').insert().values(id=str(uuid4()),created_at=now(),updated_at=now(),
                user_id=user_id,purpose=consent_type,policy_version=policy_version,action='GRANTED' if granted else 'REVOKED',
                legal_basis='User consent recorded by authenticated workflow',occurred_at=now()))

    def append_billing_ledger_entry(self,*,organization_id,entry_type,amount_uzs,reference_id):
        raise RuntimeError('Ledger writes require the typed payment/refund transaction')

    def list_audit_events(self):
        with transaction() as conn:
            return [dict(r) for r in conn.execute(select(table('audit_events'))).mappings()]

    def update_record(self,table,record_id,**updates):
        raise ImmutableRecordError(table)

    def delete_record(self,table,record_id):
        raise ImmutableRecordError(table)

def guard_opportunity_revision_update(existing,updates):
    if existing.get('published_at'):
        raise ImmutableRecordError('opportunity_revisions')
    return {**existing,**updates}

def guard_log_revision_update(existing,updates):
    if existing.get('status','DRAFT')!='DRAFT' and any(existing.get(k)!=v for k,v in updates.items()):
        raise ImmutableRecordError('log_revisions')
    return {**existing,**updates}
