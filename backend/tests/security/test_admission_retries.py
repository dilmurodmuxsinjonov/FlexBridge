"""Actual HTTP intake/nomination retries preserve one immutable intent and current projections."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import text

from app.db.storage import transaction
from test_internship_admission import accepted_offer,post
from test_admission_lifecycle import planned,terms_request


def test_concurrent_intake_retries_create_one_resource_and_one_receipt(client,identities,organization):
    _,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    def request(_):return client.post('/api/v1/placements',headers=host['headers'],json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(request,(0,1)))
    assert [r.status_code for r in responses]==[201,201],[r.text for r in responses]
    assert responses[0].json()==responses[1].json()
    with transaction() as conn:
        assert conn.execute(text('SELECT count(*) FROM flexbridge.placements')).scalar_one()==1
        assert conn.execute(text('SELECT count(*) FROM flexbridge.placement_intakes')).scalar_one()==1
        assert conn.execute(text("SELECT count(*) FROM flexbridge.audit_events WHERE action='PLACEMENT_PLANNED'")).scalar_one()==1


def test_intake_retry_after_cancel_preserves_history_and_returns_current_state(client,identities,organization):
    _,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    p=post(client,'/api/v1/placements',host,body,201)
    post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,{**terms_request(p),'action':'CANCEL'},200)
    replay=post(client,'/api/v1/placements',host,body,201)
    assert replay['id']==p['id'] and replay['status']=='CANCELLED'
    assert replay['intake_receipt']==p['intake_receipt']
    assert replay['intake_receipt']['status_at_creation']=='PLANNED'


def test_intake_key_cannot_be_reused_for_another_valid_same_host_offer(client,identities,organization):
    _,host,first=accepted_offer(client,identities,organization,'INTERNSHIP')
    _,_,second=accepted_offer(client,identities,organization,'INTERNSHIP')
    post(client,'/api/v1/placements',host,first,201)
    second['idempotency_key']=first['idempotency_key']
    response=client.post('/api/v1/placements',headers=host['headers'],json=second)
    assert response.status_code==409 and response.json()['detail']['code']=='IDEMPOTENCY_KEY_REUSED',response.text
    with transaction() as conn:assert conn.execute(text('SELECT count(*) FROM flexbridge.placements')).scalar_one()==1


def test_nomination_same_key_through_both_aliases_creates_one_assignment(client,identities,organization):
    _,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    p=post(client,'/api/v1/placements',host,body,201);mentor=identities('MENTOR',organization)
    request={'mentor_id':mentor['user_id'],'idempotency_key':str(uuid4())}
    calls=(('/api/v1/placements/'+p['id']+'/mentor-assignments',request),
           ('/api/v1/internship-logs/mentor-assignments',{**request,'placement_id':p['id'],'organization_id':organization}))
    def nominate(args):return client.post(args[0],headers=host['headers'],json=args[1])
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(nominate,calls))
    assert [r.status_code for r in responses]==[201,201],[r.text for r in responses]
    assert responses[0].json()==responses[1].json()
    with transaction() as conn:
        assert conn.execute(text('SELECT count(*) FROM flexbridge.mentor_assignments')).scalar_one()==1
        assert conn.execute(text('SELECT count(*) FROM flexbridge.mentor_assignment_proofs')).scalar_one()==1


def test_nomination_retry_after_revoke_returns_original_receipt_without_resurrection(client,identities,organization):
    _,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    p=post(client,'/api/v1/placements',host,body,201);mentor=identities('MENTOR',organization)
    request={'mentor_id':mentor['user_id'],'idempotency_key':str(uuid4())}
    base='/api/v1/placements/'+p['id']
    original=post(client,base+'/mentor-assignments',host,request,201)
    post(client,base+'/mentor-assignments/'+original['id']+'/revoke',host,terms_request(p),200)
    replay=post(client,base+'/mentor-assignments',host,request,201)
    assert replay['id']==original['id'] and replay['revoked_at'] is not None and replay['accepted_at'] is None
    assert replay['nomination_receipt']==original['nomination_receipt']
    other=identities('MENTOR',organization)
    conflict=client.post(base+'/mentor-assignments',headers=host['headers'],json={**request,'mentor_id':other['user_id']})
    assert conflict.status_code==409 and conflict.json()['detail']['code']=='IDEMPOTENCY_KEY_REUSED',conflict.text


def test_failed_intake_does_not_reserve_key_or_leave_proof(client,identities,organization,monkeypatch):
    from app.core.audit import AppendOnlyAuditStore
    from test_admission_current_actor import admission_snapshot
    _,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    before=admission_snapshot();original=AppendOnlyAuditStore.append_audit_event
    def broken(self,**kwargs):
        if kwargs['action']=='PLACEMENT_PLANNED':raise RuntimeError('Injected intake audit failure')
        return original(self,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(AppendOnlyAuditStore,'append_audit_event',broken)
        response=client.post('/api/v1/placements',headers=host['headers'],json=body)
        assert response.status_code==503,response.text
    assert admission_snapshot()==before
    post(client,'/api/v1/placements',host,body,201)
