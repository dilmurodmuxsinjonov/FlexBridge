"""Coordinator creation/binding notices reach only the actual enrolled student."""
from sqlalchemy import select
import pytest
from uuid import uuid4
from datetime import timedelta

from app.db.storage import table,transaction,now
from app.workers.outbox import relay_pending_outbox_events
from app.services.supervision_notices import EVENT_TYPE,run_notice,apply_notice
from app.services.academic_admission import academic_service
from test_academic_admission import pending_http,nominate,school_body
from test_academic_authority import academic_fixture
from test_academic_views import get


def test_actual_coordinator_responsibility_and_binding_produce_distinct_minimal_notices(client,identities,organization):
    f=pending_http(client,identities,organization);nominate(client,f)
    assert client.delete('/api/v1/me/sessions/'+f['coord']['session_id'],headers=f['coord']['headers']).status_code==200
    assert relay_pending_outbox_events(event_types=(EVENT_TYPE,))==2
    assert relay_pending_outbox_events(event_types=(EVENT_TYPE,))==0
    items=get(client,'me/notifications',f['candidate'])['items'];assert len(items)==2
    assert {r['notice']['kind'] for r in items}=={'SUPERVISION_CREATED','PLACEMENT_BOUND'}
    for row in items:
        n=row['notice'];assert n['coordinator_user_id']==f['coord']['user_id'] and n['enrollment_id']==f['enrollment']['id']
        assert n['historical'] is True and not {'legal_basis','file_ids','teacher_user_id','salary_min'} & n.keys()
    creation=next(r for r in items if r['notice']['kind']=='SUPERVISION_CREATED')
    assert creation['placement_id'] is None and creation['notice']['placement_id'] is None
    assert get(client,'me/notifications',f['teacher'])['items']==[]
    with transaction() as conn:
        events=conn.execute(select(table('outbox_events')).where(table('outbox_events').c.event_type==EVENT_TYPE)).mappings().all()
        assert len(events)==2 and all(r['processed_at'] is not None for r in events)


@pytest.mark.parametrize('mode',['apply_failure','stale_fence'])
def test_coordinator_notice_inbox_is_atomic_and_fenced(client,identities,organization,mode):
    f=pending_http(client,identities,organization)
    def fail(conn,event,payload):
        apply_notice(conn,event,payload)
        raise RuntimeError('Injected after coordinator inbox insert')
    def stale(event):
        with transaction() as conn:
            e=table('outbox_events');conn.execute(e.update().where(e.c.id==event['id']).values(claim_token=str(uuid4())))
        return run_notice(event)
    registry={EVENT_TYPE:(stale,apply_notice) if mode=='stale_fence' else (run_notice,fail)}
    assert relay_pending_outbox_events(event_types=(EVENT_TYPE,),registry=registry)==0
    assert get(client,'me/notifications',f['candidate'])['items']==[]
    with transaction() as conn:
        e=table('outbox_events');row=conn.execute(select(e).where(e.c.event_type==EVENT_TYPE)).mappings().one()
        assert row['processed_at'] is None
        expired=now()-timedelta(seconds=1)
        conn.execute(e.update().where(e.c.id==row['id']).values(available_at=expired,lease_until=expired))
    assert relay_pending_outbox_events(event_types=(EVENT_TYPE,))==1
    assert len(get(client,'me/notifications',f['candidate'])['items'])==1


def test_failed_responsibility_audit_rolls_back_supervision_origin_and_notice(client,identities,organization,monkeypatch):
    f=academic_fixture(identities,organization,make_supervision=False);body=school_body(f)
    def fail(**kwargs):raise RuntimeError('Injected coordinator audit failure')
    with monkeypatch.context() as patch:
        patch.setattr(academic_service.audit,'append_audit_event',fail)
        response=client.post('/api/v1/student-supervisions',headers=f['coord']['headers'],json=body)
        assert response.status_code==503,response.text
    with transaction() as conn:
        assert conn.execute(select(table('student_supervisions'))).first() is None
        assert conn.execute(select(table('supervision_origins'))).first() is None
        assert conn.execute(select(table('outbox_events')).where(table('outbox_events').c.event_type==EVENT_TYPE)).first() is None
    response=client.post('/api/v1/student-supervisions',headers=f['coord']['headers'],json=body)
    assert response.status_code==201,response.text
    assert relay_pending_outbox_events(event_types=(EVENT_TYPE,))==1


def test_foreign_supervision_cannot_replace_bound_notice_source(client,identities,organization):
    first=pending_http(client,identities,organization);nominate(client,first)
    other=pending_http(client,identities,organization);nominate(client,other)
    with transaction() as conn:
        e=table('outbox_events');rows=conn.execute(select(e).where(e.c.event_type==EVENT_TYPE)).mappings().all()
        bound=next(r for r in rows if r['payload']['kind']=='PLACEMENT_BOUND' and r['payload']['placement_id']==first['placement']['id'])
        conn.execute(e.update().where(e.c.id==bound['id']).values(payload={**bound['payload'],'supervision_id':other['supervision']['id']}))
    assert relay_pending_outbox_events(event_types=(EVENT_TYPE,))==3
    own=get(client,'me/notifications',first['candidate'])['items']
    assert len(own)==1 and own[0]['notice']['supervision_id']==first['supervision']['id']
    assert len(get(client,'me/notifications',other['candidate'])['items'])==2
