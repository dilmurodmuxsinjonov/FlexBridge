"""Durable dry-run records never turn a requested count into an actual purge claim."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.db.storage import table,transaction,now,retention_evaluations
from app.services.placements import insert_row
from app.services.operations import PilotOperationsService,OperationsInvariantError
from app.services.retention import RetentionPolicyService,RetentionPolicyValidationError

BASE='/api/v1/operations/retention-executions'


def evaluate(client,user,*,key='retention-request-key',**changes):
    return client.post(BASE,headers={**user['headers'],'Idempotency-Key':key},json={
        'data_category':'UNPUBLISHED_DRAFT','age_days':30,'records_scanned':999,**changes})


def test_durable_evaluation_is_truthful_and_retrievable(client,identities):
    user=identities('COMPLIANCE')
    response=evaluate(client,user)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['dry_run'] and result['execution_status']=='NOT_EXECUTED'
    assert result['records_scanned']==result['records_actioned']==0
    assert result['requested_records_scanned']==999 and result['evaluation']['decision']=='PURGE_DUE'
    assert result['policy_snapshot']['legal_approval_status']=='NOT_CERTIFIED'
    assert response.headers['cache-control']=='no-store'
    read=client.get(BASE+'/'+result['id'],headers=user['headers'])
    assert read.status_code==200 and read.json()['id']==result['id']
    with transaction() as conn:
        record=conn.execute(select(retention_evaluations)).mappings().one()
        assert record['actor_id']==user['user_id'] and record['mode']=='DRY_RUN' and record['records_actioned']==0
        assert conn.execute(select(func.count()).select_from(table('audit_events')).where(
            table('audit_events').c.action=='RETENTION_DRY_RUN_RECORDED')).scalar_one()==1


def test_evaluation_survives_new_python_process(client,identities):
    user=identities('COMPLIANCE');result=evaluate(client,user).json()
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[2])}
    code="from app.api.dependencies import ActorContext;from app.services.operations import PilotOperationsService;import json,sys;actor=ActorContext(sys.argv[1],sys.argv[2],());r=PilotOperationsService().get_retention_evaluation(actor,sys.argv[3]);print(json.dumps({'id':r['id'],'records_actioned':r['records_actioned'],'status':r['execution_status']}))"
    child=subprocess.run([sys.executable,'-c',code,user['user_id'],user['session_id'],result['id']],
        env=env,capture_output=True,text=True,check=True)
    data=json.loads(child.stdout)
    assert data=={'id':result['id'],'records_actioned':0,'status':'NOT_EXECUTED'}


def test_idempotent_parallel_evaluations_and_payload_conflict(client,identities):
    user=identities('COMPLIANCE')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(evaluate,client,user) for _ in range(2)]
        results=[future.result(timeout=20) for future in futures]
    assert all(r.status_code==200 for r in results),[r.status_code for r in results]
    assert results[0].json()['id']==results[1].json()['id']
    assert sorted(r.json()['idempotent_replay'] for r in results)==[False,True]
    assert evaluate(client,user,age_days=31).status_code==409
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(retention_evaluations)).scalar_one()==1
        assert conn.execute(select(func.count()).select_from(table('audit_events')).where(
            table('audit_events').c.action=='RETENTION_DRY_RUN_RECORDED')).scalar_one()==1


def test_record_and_audit_share_one_transaction(client,identities,monkeypatch):
    from app.api.v1.operations import operations_service
    user=identities('COMPLIANCE')
    def fail(**kwargs):raise RuntimeError('Synthetic audit failure')
    monkeypatch.setattr(operations_service.audit_store,'append_audit_event',fail)
    assert evaluate(client,user).status_code==503
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(retention_evaluations)).scalar_one()==0


def test_evaluation_rows_are_immutable(client,identities):
    result=evaluate(client,identities('COMPLIANCE')).json()
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(retention_evaluations.update().where(retention_evaluations.c.id==result['id']).values(records_actioned=999))
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(retention_evaluations.delete().where(retention_evaluations.c.id==result['id']))


def test_retention_dry_run_does_not_delete_any_draft(client,identities,organization):
    from test_adapters_and_quota import draft
    owner=identities('OWNER',organization);revision=draft(owner,organization)
    response=evaluate(client,identities('COMPLIANCE'))
    assert response.status_code==200 and response.json()['records_actioned']==0
    with transaction() as conn:
        assert conn.execute(select(table('opportunities').c.id).where(table('opportunities').c.id==revision['opportunity_id'])).scalar_one()


def test_wrong_roles_anonymous_and_password_only_compliance_are_rejected(client,identities):
    assert client.post(BASE,json={}).status_code==401
    assert evaluate(client,identities()).status_code==403
    assert evaluate(client,identities('ADMIN')).status_code==403
    grantor=identities('COMPLIANCE');user=identities()
    with transaction() as conn:
        rid=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='COMPLIANCE')).scalar_one()
        insert_row(conn,'platform_role_grants',user_id=user['user_id'],role_id=rid,granted_by_id=grantor['user_id'],expires_at=now()+timedelta(hours=1))
    response=evaluate(client,user)
    assert response.status_code==403 and response.json()['detail']['code']=='MFA_REQUIRED'


def test_current_role_is_required_to_read_a_record(client,identities):
    user=identities('COMPLIANCE');result=evaluate(client,user).json()
    assert client.get(BASE+'/'+result['id'],headers=identities()['headers']).status_code==403
    admin=identities('ADMIN')
    assert client.get(BASE+'/'+result['id'],headers=admin['headers']).status_code==200
    with transaction() as conn:
        conn.execute(table('platform_role_grants').update().where(table('platform_role_grants').c.user_id==user['user_id']).values(revoked_at=now()))
    assert client.get(BASE+'/'+result['id'],headers=user['headers']).status_code==403


@pytest.mark.parametrize('changes',[
    {'age_days':-1},{'records_scanned':-1},{'data_category':'UNKNOWN'},
    {'actor_id':str(uuid4())},{'mode':'PURGE'},{'records_actioned':100},
    {'age_days':True},{'age_days':'30'},{'records_scanned':1.2},{'records_scanned':False}])
def test_untrusted_inputs_cannot_claim_execution(client,identities,changes):
    assert evaluate(client,identities('COMPLIANCE'),**changes).status_code==422


def test_missing_idempotency_key_is_rejected(client,identities):
    assert client.post(BASE,headers=identities('COMPLIANCE')['headers'],json={
        'data_category':'UNPUBLISHED_DRAFT','age_days':30}).status_code==422


def test_internal_evaluation_rejects_boolean_numbers(identities):
    from app.api.dependencies import ActorContext
    user=identities('COMPLIANCE');actor=ActorContext(user['user_id'],user['session_id'],())
    service=PilotOperationsService()
    for age,count in ((True,0),(30,False)):
        with pytest.raises(OperationsInvariantError) as exc:
            service.record_retention_evaluation(actor,data_category='UNPUBLISHED_DRAFT',age_days=age,
                records_scanned=count,idempotency_key='internal-validation-key')
        assert exc.value.status_code==422


def test_legacy_nonpersistent_execution_and_combined_appeal_are_closed(client,identities):
    response=client.post('/api/v1/operations/moderation-appeals',headers=identities('MODERATOR')['headers'],json={})
    assert response.status_code==410
    service=PilotOperationsService()
    with pytest.raises(OperationsInvariantError):service.execute_retention_job()
    with pytest.raises(OperationsInvariantError):service.submit_and_resolve_moderation_appeal()
    assert not hasattr(service,'_appeals') and not hasattr(service,'_retention_executions')
    policy=RetentionPolicyService()
    with pytest.raises(RetentionPolicyValidationError):
        policy.register_custom_policy(data_class='CUSTOM',policy_version=1,active_days=30,
            backup_expiry_days=7,legal_basis='Reference policy without legal review')
    with pytest.raises(KeyError):policy.get_policy('CUSTOM')
