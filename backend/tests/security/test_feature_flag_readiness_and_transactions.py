"""Actual flag storage failure and nested PostgreSQL transaction controls."""
from uuid import uuid4

import pytest
from sqlalchemy import select,text,null
from sqlalchemy.exc import IntegrityError

from app.db.storage import get_engine,transaction,table
from app.services.feature_flag_admin import flag_admin_service
from app.services.operations import PilotOperationsService
from app.core.audit import AppendOnlyAuditStore
from test_organizations import actor


def create(user):
    return flag_admin_service.administer(actor=actor(user),code='R1_PART_TIME_JOBS',enabled=True,
        reason='A genuine operational choice inside this disposable database.',
        idempotency_key=str(uuid4()),expected_version=0)


@pytest.mark.parametrize('missing', ['feature_flags','feature_flag_origins','feature_flag_change_events'])
def test_readiness_does_not_call_missing_flag_storage_available(missing):
    with get_engine().begin() as conn:
        conn.execute(text('ALTER TABLE flexbridge.'+missing+' RENAME TO probe_unavailable_flag_storage'))
    try:
        report=PilotOperationsService().get_pilot_readiness_report()
        assert report['schema_migrated'] is True
        assert report['pilot_ready'] is False and report['r2_freelance_enabled'] is False
        assert report['feature_flag_read_status']=='STORAGE_UNAVAILABLE'
    finally:
        with get_engine().begin() as conn:
            conn.execute(text('ALTER TABLE flexbridge.probe_unavailable_flag_storage RENAME TO '+missing))


def test_available_empty_flag_storage_is_distinct_from_disabled_r2():
    report=PilotOperationsService().get_pilot_readiness_report()
    assert report['feature_flag_read_status']=='AVAILABLE'
    assert report['r2_freelance_enabled'] is False and report['pilot_ready'] is False


def test_failed_probe_keeps_ambient_transaction_usable():
    with transaction() as conn:
        conn.execute(text('ALTER TABLE flexbridge.feature_flag_change_events RENAME TO probe_unavailable_flag_storage'))
        report=PilotOperationsService().get_pilot_readiness_report()
        assert report['feature_flag_read_status']=='STORAGE_UNAVAILABLE'
        assert conn.execute(text('SELECT 1')).scalar_one()==1
        conn.execute(text('ALTER TABLE flexbridge.probe_unavailable_flag_storage RENAME TO feature_flag_change_events'))


def test_fail_closed_read_keeps_an_implicit_ambient_transaction_usable():
    with transaction() as conn:
        conn.execute(text('ALTER TABLE flexbridge.feature_flag_change_events RENAME TO probe_unavailable_flag_storage'))
        assert flag_admin_service.effective_enabled('R1_PART_TIME_JOBS') is False
        assert conn.execute(text('SELECT 1')).scalar_one()==1
        conn.execute(text('ALTER TABLE flexbridge.probe_unavailable_flag_storage RENAME TO feature_flag_change_events'))


def test_current_admin_change_and_audit_work_inside_a_real_savepoint(identities):
    admin=identities('ADMIN')
    with transaction() as conn:
        with conn.begin_nested():
            receipt=create(admin)
            assert receipt['version']==1
    assert flag_admin_service.effective_enabled('R1_PART_TIME_JOBS') is True


def test_audit_from_an_earlier_transaction_cannot_be_reused_for_an_event(identities):
    admin=identities('ADMIN');create(admin)
    events=table('feature_flag_change_events')
    with transaction() as conn:old=dict(conn.execute(select(events)).mappings().one())
    if old['before_snapshot'] is None:old['before_snapshot']=null()
    # Keep all fields matching so the same-UoW audit check is the distinguishing
    # failure. Without it, this would reach a different UNIQUE violation instead.
    with pytest.raises(IntegrityError,match='same-transaction audit'),transaction() as conn:
        conn.execute(events.insert().values(**old))
    with transaction() as conn:assert len(conn.execute(select(events.c.id)).all())==1


def test_rollback_after_savepoint_leaves_no_flag_proof_or_flag_audit(identities):
    admin=identities('ADMIN')
    with pytest.raises(RuntimeError,match='controlled outer rollback'):
        with transaction() as conn:
            with conn.begin_nested():create(admin)
            raise RuntimeError('controlled outer rollback')
    with transaction() as conn:
        for name in ('feature_flags','feature_flag_origins','feature_flag_change_events'):
            assert conn.execute(select(table(name))).first() is None
        audits=table('audit_events')
        assert conn.execute(select(audits.c.id).where(audits.c.action=='FEATURE_FLAG_ADMINISTERED')).first() is None


def test_database_overwrites_a_caller_supplied_transaction_stamp(identities):
    admin=identities('ADMIN')
    with transaction() as conn:
        with conn.begin_nested():
            event=AppendOnlyAuditStore().append_audit_event(actor_id=admin['user_id'],
                action='FEATURE_FLAG_ADMINISTERED',entity_type='feature_flag',entity_id=str(uuid4()),
                metadata={'_feature_flag_top_xid':'forged-future-transaction','preserved':'original'})
        row=conn.execute(text('SELECT scope_snapshot,CAST(xmin AS text) AS row_xid, '
            'CAST(pg_current_xact_id() AS text) AS top_xid FROM flexbridge.audit_events WHERE id=CAST(:id AS uuid)'),
            {'id':event['id']}).mappings().one()
        assert row['scope_snapshot']=={'_feature_flag_top_xid':row['top_xid'],'preserved':'original'}
        assert row['row_xid']!=row['top_xid']  # an actual child transaction, not a plain write


def test_other_audit_actions_are_not_rewritten_by_flag_transaction_stamping(identities):
    user=identities()
    event=AppendOnlyAuditStore().append_audit_event(actor_id=user['user_id'],action='UNRELATED_DIAGNOSTIC',
        entity_type='test',entity_id=str(uuid4()),metadata={'_feature_flag_top_xid':'original'})
    with transaction() as conn:
        audits=table('audit_events')
        assert conn.execute(select(audits.c.scope_snapshot).where(audits.c.id==event['id'])).scalar_one()=={
            '_feature_flag_top_xid':'original'}
