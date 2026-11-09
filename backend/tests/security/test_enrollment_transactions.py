"""Actual HTTP/PG waits, atomic rollback and concurrency for enrollment boundaries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import select, text
from app.api.dependencies import ActorContext
from app.db.storage import get_engine, read_snapshot, table, transaction
from app.services.enrollments import enrollment_service as service
from test_enrollments import create, enrollment_body
from test_org_authority_transactions import wait_for_blocker


def snapshot():
    with transaction() as conn:
        result={}
        for name in ('enrollments','enrollment_origins','enrollment_submissions','enrollment_events','verification_cases','verification_evidence'):
            rows=[dict(r) for r in conn.execute(select(table(name))).mappings()]
            result[name]=sorted(rows,key=lambda row:str(sorted(row.items())))
        audits=table('audit_events')
        result['audit']=[dict(r) for r in conn.execute(select(audits).where(audits.c.action.like('ENROLLMENT%')).order_by(audits.c.id)).mappings()]
        return result


def own_operation(kind,client,identities):
    owner=identities();body,_=enrollment_body(owner,files=kind=='revision')
    if kind=='create':return owner,lambda:client.post('/api/v1/me/enrollments',json=body,headers=owner['headers'])
    # A declaration can submit its first evidence revision without moderator setup.
    if kind=='revision':
        evidence=body['file_ids'];body={**body,'file_ids':[],'evidence_note':''}
    entry=create(client,owner,body);url='/api/v1/me/enrollments/'+entry['id']
    if kind=='list':request=lambda:client.get('/api/v1/me/enrollments',headers=owner['headers'])
    elif kind=='detail':request=lambda:client.get(url,headers=owner['headers'])
    elif kind=='end':request=lambda:client.post(url+'/end',headers=owner['headers'],json={
        'idempotency_key':str(uuid4()),'reason':'I withdraw this own declared enrollment.'})
    elif kind=='revision':request=lambda:client.post(url+'/verification',headers=owner['headers'],json={
        'expected_revision':1,'program':body['program'],'start_date':body['start_date'],
        'file_ids':evidence,'evidence_note':'Current own evidence for the first submission.'})
    else:raise AssertionError(kind)
    return owner,request


@pytest.mark.parametrize('kind',['create','list','detail','revision','end'])
def test_actual_completed_logout_while_profile_is_held_denies_own_operation(client,identities,kind):
    owner,request=own_operation(kind,client,identities);before=snapshot()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            holder.execute(select(table('candidate_profiles')).where(table('candidate_profiles').c.id==owner['candidate_id']).with_for_update())
            pid=holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(request);wait_for_blocker(pid)
            revoked=client.delete('/api/v1/me/sessions/'+owner['session_id'],headers=owner['headers'])
            assert revoked.status_code==200,revoked.text
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert snapshot()==before


def pending_review(client,identities):
    owner=identities();moderator=identities('MODERATOR');body,_=enrollment_body(owner,files=True)
    entry=create(client,owner,body)
    response=client.post('/api/v1/operator/verification-cases/'+entry['case_id']+'/claim',headers=moderator['headers'])
    assert response.status_code==200,response.text
    def approve():
        return client.post('/api/v1/operator/verification-cases/'+entry['case_id']+'/decide',headers=moderator['headers'],
                           json={'decision':'APPROVE','expected_revision':1,'reason':'Independent exact enrollment decision with current authority.'})
    return owner,moderator,entry,approve


def test_actual_moderator_logout_before_institution_wait_finishes_denies_decision(client,identities):
    _,moderator,entry,approve=pending_review(client,identities);before=snapshot()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            holder.execute(select(table('institutions')).where(table('institutions').c.id==entry['institution_id']).with_for_update())
            pid=holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(approve);wait_for_blocker(pid)
            revoked=client.delete('/api/v1/me/sessions/'+moderator['session_id'],headers=moderator['headers'])
            assert revoked.status_code==200,revoked.text
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert snapshot()==before


@pytest.mark.parametrize('kind',['create','end','approve'])
def test_audit_failure_rolls_back_business_proof_and_decision(client,identities,monkeypatch,kind):
    if kind=='approve':_,_,_,request=pending_review(client,identities)
    else:_,request=own_operation(kind,client,identities)
    before=snapshot()
    def unavailable(**kwargs):raise RuntimeError('Controlled audit failure')
    monkeypatch.setattr(service.audit_store,'append_audit_event',unavailable)
    response=request();assert response.status_code==503,response.text
    assert snapshot()==before


def test_concurrent_create_replay_and_review_vs_end_have_one_terminal_history(client,identities):
    owner=identities();moderator=identities('MODERATOR');body,_=enrollment_body(owner,files=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(lambda:client.post('/api/v1/me/enrollments',json=body,headers=owner['headers'])) for _ in range(2)]
        replies=[future.result(timeout=30) for future in futures]
    assert all(r.status_code==201 for r in replies),[r.text for r in replies]
    entry=replies[0].json();assert replies[1].json()['id']==entry['id']
    claim=client.post('/api/v1/operator/verification-cases/'+entry['case_id']+'/claim',headers=moderator['headers'])
    assert claim.status_code==200,claim.text
    with ThreadPoolExecutor(max_workers=2) as pool:
        approval=pool.submit(lambda:client.post('/api/v1/operator/verification-cases/'+entry['case_id']+'/decide',headers=moderator['headers'],
            json={'decision':'APPROVE','expected_revision':1,'reason':'Independent enrollment review racing an own end request.'}))
        ending=pool.submit(lambda:client.post('/api/v1/me/enrollments/'+entry['id']+'/end',headers=owner['headers'],
            json={'idempotency_key':str(uuid4()),'reason':'I end or withdraw this enrollment permanently.'}))
        approved=approval.result(timeout=30);ended=ending.result(timeout=30)
    assert approved.status_code in (200,403,409),approved.text
    assert ended.status_code==200,ended.text
    final=client.get('/api/v1/me/enrollments/'+entry['id'],headers=owner['headers']).json()
    assert final['status'] in ('ENDED','WITHDRAWN') and final['current_student'] is False
    with transaction() as conn:
        assert conn.execute(select(table('enrollments').c.id)).scalars().all()==[entry['id']]
        actions=conn.execute(select(table('enrollment_events').c.action)).scalars().all()
        assert sum(a in ('END','WITHDRAW') for a in actions)==1
        assert actions.count('APPROVE')==(1 if final['status']=='ENDED' else 0)


@pytest.mark.parametrize('method',['list','detail'])
def test_human_enrollment_read_rejects_frozen_outer_snapshot(client,identities,method):
    owner=identities();body,_=enrollment_body(owner);entry=create(client,owner,body)
    actor=ActorContext(owner['user_id'],owner['session_id'],())
    before=snapshot()
    with pytest.raises(RuntimeError,match='READ COMMITTED'),read_snapshot() as conn:
        conn.execute(text('SELECT 1'))
        if method=='list':service.list_own(actor)
        else:service.detail_own(actor,entry['id'])
    assert snapshot()==before
