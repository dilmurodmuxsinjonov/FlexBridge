"""Actual academic viewer-change notices from immutable local proof, not external delivery."""
from uuid import uuid4
from datetime import timedelta
import pytest

from sqlalchemy import select

from app.db.storage import table,transaction,now
from app.db.institution_scope import TASHKENT
from app.services.placements import insert_row
from app.workers.outbox import relay_pending_outbox_events
from app.services.academic_notices import run_notice,apply_notice
from test_academic_admission import pending_http,nominate,plan,accept_candidate_mentor
from test_academic_lifecycle import teacher_accept
from test_admission_lifecycle import terms_request
from test_internship_admission import post


TOPIC='PLACEMENT_ACADEMIC_NOTICE'


def test_active_teacher_reassignment_notifies_candidate_of_actual_viewer_history(client,identities,organization):
    f=pending_http(client,identities,organization);first=nominate(client,f);p=plan(client,f)
    accept_candidate_mentor(client,f,p)
    _,_,accepted=teacher_accept(client,f,first,p);assert accepted.status_code==200,accepted.text
    base='/api/v1/placements/'+f['placement']['id']
    post(client,base+'/host-decisions',f['owner'],{**terms_request(p),'action':'ACTIVATE'},200)
    post(client,'/api/v1/academic-assignments/'+first['id']+'/revoke',f['coord'],{'idempotency_key':str(uuid4())},200)
    replacement=identities()
    with transaction() as conn:
        member=insert_row(conn,'institution_memberships',institution_id=f['inst']['id'],user_id=replacement['user_id'],status='ACTIVE',accepted_at=now())
        appointment=insert_row(conn,'institution_appointments',institution_id=f['inst']['id'],user_id=replacement['user_id'],
            document_file_id=f['teacher_appointment']['document_file_id'],status='ACTIVE',valid_from=now().astimezone(TASHKENT).date(),accepted_at=now())
        insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=f['teacher_grant']['role_id'],appointment_id=appointment['id'])
    new={**f,'teacher':replacement,'teacher_member':member}
    second=nominate(client,new)
    url,body,accepted=teacher_accept(client,new,second,p);assert accepted.status_code==200,accepted.text
    assert client.post(url,headers=replacement['headers'],json=body).json()==accepted.json()
    # Delivery acknowledges already committed intent after the authors log out.
    for user in (f['coord'],replacement):
        assert client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers']).status_code==200
    with transaction() as conn:
        events=[dict(r) for r in conn.execute(select(table('outbox_events')).where(table('outbox_events').c.event_type==TOPIC)).mappings()]
        assert len(events)==5
        assert sorted(e['payload']['kind'] for e in events)==['ACCEPTED','ACCEPTED','NOMINATED','NOMINATED','REVOKED']
    assert relay_pending_outbox_events(event_types=(TOPIC,))==5
    assert relay_pending_outbox_events(event_types=(TOPIC,))==0
    response=client.get('/api/v1/me/notifications',headers=f['candidate']['headers'])
    assert response.status_code==200,response.text
    items=response.json()['items'];assert len(items)==5
    for item in items:
        notice=item['notice'];assert notice['assignment_kind']=='TEACHER' and notice['historical'] is True
        assert notice['institution_id']==f['inst']['id'] and notice['placement_id']==f['placement']['id']
        assert notice['teacher_user_id'] in (f['teacher']['user_id'],replacement['user_id'])
        assert not {'enrollment_id','legal_basis','salary_min','file_ids','mentor_user_id'} & notice.keys()
    outsider=identities()
    assert client.get('/api/v1/me/notifications',headers=outsider['headers']).json()['items']==[]
    assert client.post('/api/v1/me/notifications/'+items[0]['id']+'/read',headers=outsider['headers']).status_code==404
    post(client,'/api/v1/me/notifications/'+items[0]['id']+'/read',f['candidate'],{},200)


@pytest.mark.parametrize('mode',['apply_failure','stale_fence'])
def test_academic_worker_failure_or_stale_fence_has_no_partial_inbox_effect(client,identities,organization,mode):
    f=pending_http(client,identities,organization);nominate(client,f)
    def apply_failure(conn,event,payload):
        apply_notice(conn,event,payload)
        raise RuntimeError('Injected after academic inbox insert')
    def stale_fence(event):
        with transaction() as conn:
            e=table('outbox_events');conn.execute(e.update().where(e.c.id==event['id']).values(claim_token=str(uuid4())))
        return run_notice(event)
    registry={TOPIC:(stale_fence,apply_notice) if mode=='stale_fence' else (run_notice,apply_failure)}
    assert relay_pending_outbox_events(event_types=(TOPIC,),registry=registry)==0
    assert client.get('/api/v1/me/notifications',headers=f['candidate']['headers']).json()['items']==[]
    with transaction() as conn:
        e=table('outbox_events');row=conn.execute(select(e).where(e.c.event_type==TOPIC)).mappings().one()
        assert row['processed_at'] is None
        expired=now()-timedelta(seconds=1)
        conn.execute(e.update().where(e.c.id==row['id']).values(available_at=expired,lease_until=expired))
    assert relay_pending_outbox_events(event_types=(TOPIC,))==1
    assert len(client.get('/api/v1/me/notifications',headers=f['candidate']['headers']).json()['items'])==1


def test_forged_cross_placement_envelope_cannot_redirect_academic_notice(client,identities,organization):
    first=pending_http(client,identities,organization);nominate(client,first)
    other=pending_http(client,identities,organization);nominate(client,other)
    with transaction() as conn:
        e=table('outbox_events');row=conn.execute(select(e).where(e.c.event_type==TOPIC,e.c.aggregate_key==first['placement']['id'])).mappings().one()
        conn.execute(e.update().where(e.c.id==row['id']).values(payload={**row['payload'],'placement_id':other['placement']['id']}))
    assert relay_pending_outbox_events(event_types=(TOPIC,))==1
    assert client.get('/api/v1/me/notifications',headers=first['candidate']['headers']).json()['items']==[]
    items=client.get('/api/v1/me/notifications',headers=other['candidate']['headers']).json()['items']
    assert len(items)==1 and items[0]['notice']['placement_id']==other['placement']['id']
