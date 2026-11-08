"""PostgreSQL ownership concurrency, failure rollback and immutable history."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.db.storage import table,transaction,now
from app.services.placements import insert_row
from test_owner_additions import setup_owner,submit,consent,ready,has_owner,member_id
from test_organizations import decide,claim


def counts(case):
    with transaction() as conn:
        events=conn.execute(select(func.count()).select_from(table('org_ownership_events')).where(
            table('org_ownership_events').c.verification_case_id==case)).scalar_one()
        audits=conn.execute(select(func.count()).select_from(table('audit_events')).where(
            table('audit_events').c.object_key==case,table('audit_events').c.action=='OWNER_ADDITION_APPROVED')).scalar_one()
        return events,audits


def test_parallel_submit_consent_and_approval_are_single_effect(client,setup_owner):
    flow=setup_owner
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[f.result(timeout=30) for f in [pool.submit(submit,client,flow) for _ in range(2)]]
    assert [r.status_code for r in results]==[202,202]
    assert results[0].json()['id']==results[1].json()['id']
    case=results[0].json()['id']
    assert sorted(r.json()['idempotent_replay'] for r in results)==[False,True]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[f.result(timeout=30) for f in [pool.submit(consent,client,flow,case) for _ in range(2)]]
    assert [r.status_code for r in results]==[200,200]
    assert sorted(r.json()['idempotent_replay'] for r in results)==[False,True]
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[f.result(timeout=30) for f in [pool.submit(decide,client,flow['moderator'],case) for _ in range(2)]]
    assert [r.status_code for r in results]==[200,200],[r.text for r in results]
    assert sorted(r.json()['idempotent_replay'] for r in results)==[False,True]
    assert results[0].json()['ownership_event_id']==results[1].json()['ownership_event_id']
    assert has_owner(flow['target_member']) and counts(case)==(1,1)
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('owner_addition_consents'))).scalar_one()==1


def test_parallel_cancel_and_approval_have_one_terminal_outcome(client,setup_owner):
    flow=setup_owner;case=ready(client,flow)
    def cancel():return client.post('/api/v1/owner-requests/'+case+'/cancel',headers=flow['owner']['headers'],
        json={'reason':'Requester cancels before approval commits'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        approval=pool.submit(decide,client,flow['moderator'],case);cancellation=pool.submit(cancel)
        approved,cancelled=approval.result(timeout=30),cancellation.result(timeout=30)
    assert sorted((approved.status_code,cancelled.status_code))==[200,409]
    assert has_owner(flow['target_member'])==(approved.status_code==200)
    assert counts(case)==((1,1) if approved.status_code==200 else (0,0))


def test_requester_revocation_serializes_with_approval(client,setup_owner,identities):
    flow=setup_owner;case=ready(client,flow);other_owner=identities('OWNER',flow['org'])
    requester_member=member_id(flow['owner'],flow['org'])
    def revoke():return client.post('/api/v1/organizations/'+flow['org']+'/memberships/'+requester_member+'/revoke',
        headers=other_owner['headers'],json={'reason':'Revoke the original requester authority'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        approval=pool.submit(decide,client,flow['moderator'],case);revocation=pool.submit(revoke)
        approved,revoked=approval.result(timeout=30),revocation.result(timeout=30)
    assert revoked.status_code==200,revoked.text
    assert approved.status_code in (200,403),approved.text
    assert has_owner(flow['target_member'])==(approved.status_code==200)
    assert counts(case)==((1,1) if approved.status_code==200 else (0,0))


@pytest.mark.parametrize('stage',['grant','event','audit','deferred_proof'])
def test_grant_event_case_and_audit_roll_back_together(client,setup_owner,monkeypatch,stage):
    from app.services import owner_additions as module
    flow=setup_owner;case=ready(client,flow);original_insert=module.insert_row
    def insert(conn,name,**values):
        if (stage=='grant' and name=='org_role_grants') or (stage=='event' and name=='org_ownership_events'):
            raise RuntimeError('Synthetic write-boundary failure')
        if stage=='deferred_proof' and name=='org_ownership_events':
            values['approved_by_id']=flow['owner']['user_id']
        return original_insert(conn,name,**values)
    def audit(**kwargs):raise RuntimeError('Synthetic audit failure')
    monkeypatch.setattr(module,'insert_row',insert)
    if stage=='audit':monkeypatch.setattr(module.owner_addition_service.audit_store,'append_audit_event',audit)
    response=decide(client,flow['moderator'],case)
    assert response.status_code==(409 if stage=='deferred_proof' else 503),response.text
    assert not has_owner(flow['target_member']) and counts(case)==(0,0)
    with transaction() as conn:
        assert conn.execute(select(table('verification_cases').c.status).where(table('verification_cases').c.id==case)).scalar_one()=='IN_REVIEW'


@pytest.mark.parametrize('phase',['proposal','consent'])
def test_early_audit_failure_does_not_leave_partial_proposal_or_consent(client,setup_owner,monkeypatch,phase):
    from app.services.owner_additions import owner_addition_service
    flow=setup_owner;case=None
    if phase=='consent':
        response=submit(client,flow);assert response.status_code==202,response.text
        case=response.json()['id']
    def fail(**kwargs):raise RuntimeError('Synthetic audit failure')
    monkeypatch.setattr(owner_addition_service.audit_store,'append_audit_event',fail)
    response=submit(client,flow) if phase=='proposal' else consent(client,flow,case)
    assert response.status_code==503,response.text
    assert not has_owner(flow['target_member'])
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('owner_addition_consents'))).scalar_one()==0
        assert conn.execute(select(func.count()).select_from(table('owner_addition_requests'))).scalar_one()==(0 if phase=='proposal' else 1)
        if case:assert conn.execute(select(table('verification_cases').c.status).where(table('verification_cases').c.id==case)).scalar_one()=='WAITING_CONSENT'


def test_proposal_consent_evidence_and_ownership_event_are_immutable(client,setup_owner):
    flow=setup_owner;case=ready(client,flow)
    response=decide(client,flow['moderator'],case);assert response.status_code==200,response.text
    with transaction() as conn:
        consent_id=conn.execute(select(table('owner_addition_consents').c.id)).scalar_one()
        note_id=conn.execute(select(table('verification_evidence').c.id).where(table('verification_evidence').c.case_id==case,
            table('verification_evidence').c.note.is_not(None))).scalar_one()
    targets=[('owner_addition_requests','case_id',case,{'idempotency_key':'another-valid-request-key'}),
        ('owner_addition_consents','id',consent_id,{'contact_digest':'different-nonempty-binding'}),
        ('org_ownership_events','id',response.json()['ownership_event_id'],{'effective_at':now()}),
        ('verification_evidence','id',note_id,{'note':'Overwritten evidence justification'})]
    for name,key,value,changes in targets:
        target=table(name)
        with pytest.raises(IntegrityError) as error,transaction() as conn:
            conn.execute(target.update().where(target.c[key]==value).values(**changes))
        assert error.value.orig.sqlstate=='23514'
        with pytest.raises(IntegrityError),transaction() as conn:conn.execute(target.delete().where(target.c[key]==value))


def test_owner_regrant_preserves_revoked_grant_and_prevents_two_active_grants(client,setup_owner):
    flow=setup_owner
    with transaction() as conn:
        owner_role=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='OWNER',
            table('role_catalog').c.scope_kind=='ORG')).scalar_one()
        # Explicit legacy-history fixture; it is not a fresh authorization grant.
        old=insert_row(conn,'org_role_grants',membership_id=flow['target_member'],role_id=owner_role,
            granted_by_id=flow['owner']['user_id'],revoked_at=now())
    case=ready(client,flow);response=decide(client,flow['moderator'],case)
    assert response.status_code==200,response.text
    with transaction() as conn:
        records=[dict(r) for r in conn.execute(select(table('org_role_grants')).where(
            table('org_role_grants').c.membership_id==flow['target_member'],table('org_role_grants').c.role_id==owner_role)).mappings()]
        assert len(records)==2 and next(r for r in records if r['id']==old['id'])==old
        assert len([r for r in records if r['revoked_at'] is None])==1
    with pytest.raises(IntegrityError),transaction() as conn:
        insert_row(conn,'org_role_grants',membership_id=flow['target_member'],role_id=owner_role,granted_by_id=flow['moderator']['user_id'])


def test_proposal_and_consent_survive_another_python_process(client,setup_owner):
    flow=setup_owner;case=ready(client,flow);target=flow['target']
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[2])}
    code="from app.api.dependencies import ActorContext;from app.services.owner_additions import owner_addition_service;import sys,json;r=owner_addition_service.read(ActorContext(sys.argv[1],sys.argv[2],()),sys.argv[3]);print(json.dumps({'id':r['id'],'status':r['status'],'decision':r['consent']['decision']}))"
    child=subprocess.run([sys.executable,'-c',code,target['user_id'],target['session_id'],case],
        env=env,capture_output=True,text=True,check=True)
    assert json.loads(child.stdout)=={'id':case,'status':'IN_REVIEW','decision':'ACCEPT'}


def test_owner_case_without_proposal_fails_closed_and_revisions_are_strict(client,setup_owner):
    flow=setup_owner
    with transaction() as conn:
        fake=insert_row(conn,'verification_cases',requester_id=flow['owner']['user_id'],organization_id=flow['org'],
            kind='ORG_OWNER_ADDITION',status='PENDING',current_revision=1,due_at=now())
    response=claim(client,flow['moderator'],fake['id']);assert response.status_code==404,response.text
    case=ready(client,flow)
    response=client.post('/api/v1/operator/verification-cases/'+case+'/decide',headers=flow['moderator']['headers'],json={
        'decision':'APPROVE','expected_revision':True,'reason':'Independent evidence review completed'})
    assert response.status_code==422,response.text
    response=consent(client,flow,case,revision=True);assert response.status_code==422,response.text
    assert not has_owner(flow['target_member'])
