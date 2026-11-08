"""Atomic quorum, competing terminal actions and late-proof failures on PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import select,func
from app.db.storage import table,transaction,now
from test_owner_continuity import setup_continuity,submit,claim,decide,ready,NOTE
from test_owner_additions import has_owner,member_id
from test_candidate import cv_fixture
from test_invitations import contact
from uuid import uuid4

def state(case):
    with transaction() as conn:
        current=conn.execute(select(table('verification_cases').c.status).where(table('verification_cases').c.id==case)).scalar_one()
        recovery=conn.execute(select(table('recovery_requests').c.status).join(table('owner_continuity_requests'),
            table('owner_continuity_requests').c.recovery_id==table('recovery_requests').c.id).where(table('owner_continuity_requests').c.case_id==case)).scalar_one()
        return current,recovery

def test_parallel_intake_claims_recommendation_and_finalization_are_single_effect(client,setup_continuity):
    flow=setup_continuity
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:submit(client,flow),range(2)))
    assert [r.status_code for r in responses]==[202,202]
    assert responses[0].json()['id']==responses[1].json()['id']
    assert sorted(r.json()['idempotent_replay'] for r in responses)==[False,True]
    case=responses[0].json()['id']
    for stage in ('moderator','compliance'):
        with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:claim(client,flow,case,stage),range(2)))
        assert [r.status_code for r in responses]==[200,200]
        assert sorted(r.json()['idempotent_replay'] for r in responses)==[False,True]
        with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:decide(client,flow,case,stage),range(2)))
        assert [r.status_code for r in responses]==[200,200]
        assert sorted(r.json()['idempotent_replay'] for r in responses)==[False,True]
        if stage=='moderator':assert not has_owner(flow['member'])
    assert has_owner(flow['member']) and has_owner(flow['owner_member'])
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('owner_continuity_events'))).scalar_one()==4
        assert conn.execute(select(func.count()).select_from(table('owner_continuity_requests'))).scalar_one()==1
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==1
        audit=table('audit_events')
        assert conn.execute(select(func.count()).select_from(audit).where(audit.c.object_key==case,audit.c.action=='OWNER_CONTINUITY_APPROVE')).scalar_one()==1
    conflict=submit(client,flow,evidence_note='Changed intent under a previously used idempotency key')
    assert conflict.status_code==409,conflict.text
    repeat=submit(client,flow);assert repeat.status_code==202 and repeat.json()['status']=='APPROVED' and repeat.json()['idempotent_replay'],repeat.text

def test_parallel_different_applicants_only_create_one_open_org_case(client,setup_continuity,identities):
    flow=setup_continuity;other=identities('HR',flow['org'])
    changed={**flow,'applicant':other,'member':member_id(other,flow['org']),'file':cv_fixture(other),
        'contact':contact(other,value=str(uuid4())+'@example.test',channel='EMAIL')}
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda f:submit(client,f),(flow,changed)))
    assert sorted(r.status_code for r in responses)==[202,409],[r.status_code for r in responses]
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('owner_continuity_requests'))).scalar_one()==1
        assert conn.execute(select(func.count()).select_from(table('recovery_requests'))).scalar_one()==1
    assert not has_owner(flow['member']) and not has_owner(changed['member'])

@pytest.mark.parametrize('action',['withdraw','owner_object'])
def test_terminal_objection_or_withdrawal_racing_finalization_has_one_outcome(client,setup_continuity,action):
    flow=setup_continuity;case=ready(client,flow)
    def close():
        if action=='withdraw':return client.post('/api/v1/owner-continuity/'+case+'/withdraw',headers=flow['applicant']['headers'],
            json={'reason':'Withdraw my continuity request before final approval'})
        return client.post('/api/v1/organizations/'+flow['org']+'/owner-continuity/'+case+'/object',headers=flow['owner']['headers'],
            json={'reason':'Current owner objects before continuity finalization'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(decide,client,flow,case,'compliance');b=pool.submit(close)
        results=[a.result(),b.result()]
    assert sorted(r.status_code for r in results)==[200,409],[r.status_code for r in results]
    current,tracking=state(case)
    assert (current,tracking) in (('APPROVED','COMPLETED'),('CANCELLED','CANCELLED'))
    assert has_owner(flow['member'])==(current=='APPROVED') and has_owner(flow['owner_member'])

@pytest.mark.parametrize('phase',['grant','review','event','audit','deferred_actor','deferred_route','late_moderator_expiry','late_compliance_expiry'])
def test_final_grant_quorum_history_case_tracking_and_audit_roll_back(client,setup_continuity,monkeypatch,phase):
    from app.services import owner_continuity as module
    flow=setup_continuity;case=ready(client,flow);original_insert=module.insert_row;original_event=module.owner_continuity_service._event
    def insert(conn,name,**values):
        if (phase=='grant' and name=='org_role_grants') or (phase=='event' and name=='org_ownership_events'):
            raise RuntimeError('Synthetic continuity write failure')
        if name=='org_ownership_events':
            if phase=='deferred_actor':values['approved_by_id']=flow['moderator']['user_id']
            if phase=='deferred_route':values['previous_membership_id']=flow['owner_member']
        return original_insert(conn,name,**values)
    def event(conn,actor,stage,action,request,grant_id,**extra):
        if action=='APPROVE' and phase=='review':raise RuntimeError('Synthetic final quorum write failure')
        result=original_event(conn,actor,stage,action,request,grant_id,**extra)
        if action=='APPROVE' and phase.startswith('late_'):
            role=flow['moderator' if phase=='late_moderator_expiry' else 'compliance']
            grants=table('platform_role_grants')
            conn.execute(grants.update().where(grants.c.user_id==role['user_id']).values(expires_at=now()-timedelta(seconds=1)))
        return result
    def fail_audit(**kwargs):raise RuntimeError('Synthetic final continuity audit failure')
    monkeypatch.setattr(module,'insert_row',insert);monkeypatch.setattr(module.owner_continuity_service,'_event',event)
    if phase=='audit':monkeypatch.setattr(module.owner_continuity_service.audit_store,'append_audit_event',fail_audit)
    response=decide(client,flow,case,'compliance')
    assert response.status_code==(409 if phase.startswith(('deferred_','late_')) else 503),response.text
    assert not has_owner(flow['member']) and has_owner(flow['owner_member'])
    assert state(case)==('WAITING_COMPLIANCE','WAITING_COMPLIANCE')
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==0
        assert conn.execute(select(func.count()).select_from(table('owner_continuity_events')).where(table('owner_continuity_events').c.action=='APPROVE')).scalar_one()==0

@pytest.mark.parametrize('phase',['submit','moderator_claim','recommend','compliance_claim'])
def test_early_audit_failure_leaves_no_partial_stage_or_tracking(client,setup_continuity,monkeypatch,phase):
    from app.services.owner_continuity import owner_continuity_service
    flow=setup_continuity;case=None
    if phase!='submit':
        response=submit(client,flow);assert response.status_code==202,response.text
        case=response.json()['id']
        if phase in ('recommend','compliance_claim'):
            response=claim(client,flow,case,'moderator');assert response.status_code==200,response.text
        if phase=='compliance_claim':
            response=decide(client,flow,case,'moderator');assert response.status_code==200,response.text
    def fail(**kwargs):raise RuntimeError('Synthetic early continuity audit failure')
    monkeypatch.setattr(owner_continuity_service.audit_store,'append_audit_event',fail)
    if phase=='submit':response=submit(client,flow)
    elif phase=='moderator_claim':response=claim(client,flow,case,'moderator')
    elif phase=='recommend':response=decide(client,flow,case,'moderator')
    else:response=claim(client,flow,case,'compliance')
    assert response.status_code==503,response.text
    assert not has_owner(flow['member'])
    with transaction() as conn:
        expected={'submit':0,'moderator_claim':0,'recommend':1,'compliance_claim':2}[phase]
        assert conn.execute(select(func.count()).select_from(table('owner_continuity_events'))).scalar_one()==expected
        assert conn.execute(select(func.count()).select_from(table('owner_continuity_requests'))).scalar_one()==(0 if phase=='submit' else 1)
        assert conn.execute(select(func.count()).select_from(table('recovery_requests'))).scalar_one()==(0 if phase=='submit' else 1)
    if case:
        wanted='WAITING_COMPLIANCE' if phase=='compliance_claim' else 'WAITING_MODERATOR'
        assert state(case)==(wanted,wanted)
