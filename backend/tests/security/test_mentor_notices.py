"""Actual in-app worker/inbox effects; no external delivery or live users are involved."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from datetime import timedelta

from sqlalchemy import select,text

from app.db.storage import table,transaction,now,get_engine
from app.services.mentor_notices import EVENT_TYPE,run_notice,apply_notice
from app.workers.outbox import relay_pending_outbox_events
from test_admission_lifecycle import planned,terms_request
from test_internship_admission import post
from test_org_authority_transactions import wait_for_blocker


def deliver(**kwargs):return relay_pending_outbox_events(event_types=[EVENT_TYPE],**kwargs)


def inbox(client,user,**params):
    response=client.get('/api/v1/me/notifications',headers=user['headers'],params=params)
    assert response.status_code==200 and response.headers['cache-control']=='no-store',response.text
    return response.json()


def test_nomination_acceptance_and_revoke_reach_only_candidate_inbox_once(client,identities,organization):
    candidate,host,mentor,p,assignment=planned(client,identities,organization)
    assert inbox(client,candidate)['items']==[]
    assert deliver()==1 and deliver()==0
    first=inbox(client,candidate)['items'];assert len(first)==1
    notice=first[0]['notice']
    assert notice['mentor_user_id']==mentor['user_id'] and notice['assignment_id']==assignment['id']
    assert notice['kind']=='NOMINATED' and notice['scope_at_event']==['PLAN']
    assert inbox(client,host)['items']==[] and inbox(client,mentor)['items']==[]
    post(client,'/api/v1/placements/'+p['id']+'/assignments/'+assignment['id']+'/accept',mentor,terms_request(p),200)
    # Queue effects acknowledge valid historical intents after author logout.
    assert client.delete('/api/v1/me/sessions/'+mentor['session_id'],headers=mentor['headers']).status_code==200
    assert deliver()==1
    post(client,'/api/v1/placements/'+p['id']+'/mentor-assignments/'+assignment['id']+'/revoke',host,terms_request(p),200)
    assert deliver()==1
    items=inbox(client,candidate)['items']
    assert [i['notice']['kind'] for i in items]==['NOMINATED','ACCEPTED','REVOKED']
    assert items[-1]['notice']['scope_at_event']==[] and all(i['notice']['historical'] for i in items)
    assert all(i['notice']['link']=='/api/v1/placements/'+p['id']+'/plan' for i in items)
    foreign=client.post('/api/v1/me/notifications/'+items[0]['id']+'/read',headers=host['headers'])
    assert foreign.status_code==404,foreign.text
    read=post(client,'/api/v1/me/notifications/'+items[0]['id']+'/read',candidate,{},200)
    assert post(client,'/api/v1/me/notifications/'+items[0]['id']+'/read',candidate,{},200)==read
    assert len(inbox(client,candidate)['items'])==2 and len(inbox(client,candidate,unread_only=False)['items'])==3


def test_worker_inbox_apply_failure_rolls_back_then_retry_delivers_one_row(client,identities,organization):
    candidate,_,_,_,_=planned(client,identities,organization)
    def fail(conn,event,result):
        apply_notice(conn,event,result)
        raise RuntimeError('Injected after local inbox insert')
    assert deliver(registry={EVENT_TYPE:(run_notice,fail)})==0
    assert inbox(client,candidate)['items']==[]
    with transaction() as conn:
        e=table('outbox_events')
        row=conn.execute(select(e).where(e.c.event_type==EVENT_TYPE)).mappings().one()
        assert row['processed_at'] is None and row['attempts']==1
        conn.execute(e.update().where(e.c.id==row['id']).values(available_at=now()))
    assert deliver()==1 and deliver()==0 and len(inbox(client,candidate)['items'])==1


def test_stale_worker_fence_cannot_publish_mentor_notice(client,identities,organization):
    candidate,_,_,_,_=planned(client,identities,organization)
    def reclaim(event):
        with transaction() as conn:
            e=table('outbox_events')
            conn.execute(e.update().where(e.c.id==event['id']).values(claim_token=str(uuid4())))
        return run_notice(event)
    assert deliver(registry={EVENT_TYPE:(reclaim,apply_notice)})==0
    assert inbox(client,candidate)['items']==[]
    with transaction() as conn:
        e=table('outbox_events')
        assert conn.execute(select(e.c.processed_at).where(e.c.event_type==EVENT_TYPE)).scalar_one() is None
        expired=now()-timedelta(seconds=1)
        conn.execute(e.update().where(e.c.event_type==EVENT_TYPE).values(lease_until=expired,available_at=expired))
    assert deliver()==1 and len(inbox(client,candidate)['items'])==1


def test_nomination_audit_failure_rolls_back_notice_proof_and_key(client,identities,organization,monkeypatch):
    from app.services.placement_admission import admission_service
    from test_admission_current_actor import admission_snapshot
    _,host,mentor,p,_=planned(client,identities,organization)
    before=admission_snapshot();original=admission_service.audit.append_audit_event
    request={'mentor_id':mentor['user_id'],'idempotency_key':str(uuid4())}
    def broken(**kwargs):
        if kwargs['action']=='MENTOR_ASSIGNMENT_NOMINATED':raise RuntimeError('Injected nomination audit failure')
        return original(**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(admission_service.audit,'append_audit_event',broken)
        response=client.post('/api/v1/placements/'+p['id']+'/mentor-assignments',headers=host['headers'],json=request)
        assert response.status_code==503,response.text
    assert admission_snapshot()==before
    post(client,'/api/v1/placements/'+p['id']+'/mentor-assignments',host,request,201)
    assert deliver()==2  # original fixture nomination plus the successful retried one


def test_read_rechecks_actual_session_after_notification_row_wait(client,identities,organization):
    candidate,_,_,_,_=planned(client,identities,organization);assert deliver()==1
    notification=inbox(client,candidate)['items'][0]
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            n=table('notifications')
            holder.execute(select(n).where(n.c.id==notification['id']).with_for_update())
            pid=holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(lambda:client.post('/api/v1/me/notifications/'+notification['id']+'/read',headers=candidate['headers']))
            wait_for_blocker(pid)
            assert client.delete('/api/v1/me/sessions/'+candidate['session_id'],headers=candidate['headers']).status_code==200
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    with transaction() as conn:
        assert conn.execute(select(table('notifications').c.read_at)).scalar_one() is None
        assert conn.execute(text("SELECT count(*) FROM flexbridge.audit_events WHERE action='NOTIFICATION_READ'")).scalar_one()==0


def test_unknown_notification_never_returns_arbitrary_outbox_payload(client,identities):
    from app.services.placements import insert_row
    owner=identities()
    with transaction() as conn:
        event=insert_row(conn,'outbox_events',event_type='OTHER_PRIVATE_EVENT',schema_version=1,aggregate_key='private',
            payload={'opaque':'private-content-must-stay-hidden'},dedupe_key=str(uuid4()),available_at=now(),processed_at=now(),attempts=1)
        insert_row(conn,'notifications',user_id=owner['user_id'],event_id=event['id'],template_code='UNRELATED_HISTORY')
    result=inbox(client,owner)
    assert len(result['items'])==1 and result['items'][0]['notice'] is None
    assert 'private-content-must-stay-hidden' not in str(result) and '_notice_payload' not in str(result)
