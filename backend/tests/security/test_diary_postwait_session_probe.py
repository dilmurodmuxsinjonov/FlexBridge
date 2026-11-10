"""Independent public diary write/logout overlap on accepted source.

School/document fixtures are trusted metadata. Draft, login, logout and the
blocked diary update use actual current HTTP/session behavior, never mocked auth.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from time import monotonic,sleep
from uuid import uuid4

import pytest
from sqlalchemy import select,text

from app.api.dependencies import ActorContext
from app.db.storage import get_engine,table,transaction
from app.services.governance import GovernanceError
from app.services.internship_logs import internship_log_service as service,InternshipLogScopeError
from academic_review_observer import labeled_requests,wait_for_requests
from test_academic_reviews import ready
from test_org_authority_transactions import wait_for_blocker
from test_organizations import actor


def diary_snapshot(placement_id):
    """Compare pointers, all revisions and task rows, including attempted inserts."""
    with transaction() as conn:
        daily,revisions,tasks=(table(n) for n in ('daily_logs','log_revisions','log_task_entries'))
        logs=list(conn.execute(select(daily).where(daily.c.placement_id==placement_id)
                               .order_by(daily.c.id)).mappings())
        revision_rows=list(conn.execute(select(revisions).join(daily,daily.c.id==revisions.c.daily_log_id)
            .where(daily.c.placement_id==placement_id).order_by(revisions.c.id)).mappings())
        task_rows=list(conn.execute(select(tasks).join(revisions,revisions.c.id==tasks.c.revision_id)
            .join(daily,daily.c.id==revisions.c.daily_log_id).where(daily.c.placement_id==placement_id)
            .order_by(tasks.c.id)).mappings())
        return [[dict(row) for row in rows] for rows in (logs,revision_rows,task_rows)]


def send_diary(client,f,draft,operation):
    day=draft['log_date']
    payload={'day_type':'WORKED','summary_text':'A real diary boundary write.','total_minutes':30}
    if operation=='save':
        return client.put('/api/v1/placements/'+f['placement']['id']+'/logs/'+day,
                          headers=f['candidate']['headers'],json=payload)
    if operation=='submit':
        return client.post('/api/v1/logs/'+draft['id']+'/submit',headers=f['candidate']['headers'],json={})
    assert operation=='combined'
    return client.post('/api/v1/internship-logs/daily-logs',headers=f['candidate']['headers'],
                       json={**payload,'placement_id':f['placement']['id'],'log_date':day})


def direct_diary(f,draft,operation,current_actor):
    common={'actor':current_actor,'placement_id':f['placement']['id'],'log_date':draft['log_date']}
    if operation=='submit':return service.submit_daily_log_api_056(**common,log_id=draft['id'])
    save=service.save_draft_daily_log_api_054 if operation=='save' else service.create_daily_log_with_revision
    return save(**common,summary_text='Direct service boundary write.',total_minutes=30)


def hold_row(conn,f,draft,kind):
    relation,identifier={'placement':('placements',f['placement']['id']),
                         'daily_log':('daily_logs',draft['id']),
                         'revision':('log_revisions',draft['current_revision_id'])}[kind]
    # Relation names are fixed test constants; values remain bound SQL parameters.
    conn.execute(text('SELECT id FROM flexbridge.'+relation+' WHERE id=CAST(:id AS uuid) FOR UPDATE'),
                 {'id':identifier})
    return conn.execute(text('SELECT pg_backend_pid()')).scalar_one()


def test_logout_during_a_real_parent_wait_prevents_a_late_diary_write(client,identities,organization,request):
    f,_,draft=ready(client,identities,organization,submit=False)
    original=diary_snapshot(f['placement']['id'])
    label='diary-session-'+str(uuid4())
    path='/api/v1/placements/'+f['placement']['id']+'/logs/'+draft['log_date'] if 'log_date' in draft else None
    if path is None:
        with transaction() as conn:
            daily=table('daily_logs')
            day=conn.execute(select(daily.c.local_date).where(daily.c.id==draft['id'])).scalar_one().isoformat()
        path='/api/v1/placements/'+f['placement']['id']+'/logs/'+day
    def update():
        return client.put(path,headers=f['candidate']['headers'],json={'day_type':'WORKED',
            'summary_text':'This must not commit after the actual session logout.','total_minutes':30})
    with labeled_requests(get_engine()) as call,ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            holder.execute(text('SELECT id FROM flexbridge.placements WHERE id=CAST(:id AS uuid) FOR UPDATE'),
                           {'id':f['placement']['id']})
            future=pool.submit(call,label,update)
            observed=wait_for_requests(get_engine(),[label])
            request.node.user_properties.append(('actual_diary_parent_wait',json.dumps(observed,sort_keys=True)))
            logout=client.delete('/api/v1/me/sessions/'+f['candidate']['session_id'],headers=f['candidate']['headers'])
            assert logout.status_code==200,logout.text
        response=future.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert diary_snapshot(f['placement']['id'])==original


@pytest.mark.parametrize('operation,kind',[
    ('save','daily_log'),('save','revision'),
    ('submit','placement'),('submit','daily_log'),('submit','revision'),
    ('combined','placement'),('combined','daily_log'),('combined','revision'),
])
def test_logout_during_other_actual_diary_waits_has_no_effect(client,identities,organization,request,operation,kind):
    f,_,draft=ready(client,identities,organization,submit=False)
    original=diary_snapshot(f['placement']['id']);label='diary-'+str(uuid4())
    with labeled_requests(get_engine()) as call,ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            pid=hold_row(holder,f,draft,kind)
            future=pool.submit(call,label,send_diary,client,f,draft,operation)
            observed=wait_for_requests(get_engine(),[label])
            assert pid in observed[0]['blockers']
            request.node.user_properties.append(('actual_'+operation+'_'+kind+'_wait',json.dumps(observed,sort_keys=True)))
            logout=client.delete('/api/v1/me/sessions/'+f['candidate']['session_id'],headers=f['candidate']['headers'])
            assert logout.status_code==200,logout.text
        response=future.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert diary_snapshot(f['placement']['id'])==original


@pytest.mark.parametrize('operation',['save','submit','combined'])
def test_expiry_during_actual_session_lock_wait_has_no_effect(client,identities,organization,request,operation):
    f,_,draft=ready(client,identities,organization,submit=False)
    original=diary_snapshot(f['placement']['id']);label='diary-expiry-'+str(uuid4())
    with labeled_requests(get_engine()) as call,ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as parent:
            parent_pid=hold_row(parent,f,draft,'placement')
            future=pool.submit(call,label,send_diary,client,f,draft,operation)
            first=wait_for_requests(get_engine(),[label]);assert parent_pid in first[0]['blockers']
            # Trusted expiry metadata on the real already authenticated session.
            with get_engine().begin() as setup:
                expires=setup.execute(text("UPDATE flexbridge.sessions SET expires_at=clock_timestamp()+interval '3 seconds' "
                    'WHERE id=CAST(:id AS uuid) RETURNING expires_at'),{'id':f['candidate']['session_id']}).scalar_one()
            with get_engine().begin() as session_holder:
                session_holder.execute(text('SELECT id FROM flexbridge.sessions WHERE id=CAST(:id AS uuid) FOR UPDATE'),
                                       {'id':f['candidate']['session_id']})
                session_pid=session_holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
                parent.commit()
                wait_for_blocker(session_pid)
                second=wait_for_requests(get_engine(),[label]);assert session_pid in second[0]['blockers']
                request.node.user_properties.append(('actual_'+operation+'_session_wait',json.dumps(
                    {'parent':first,'session':second,'expires_at':expires.isoformat()},sort_keys=True)))
                deadline=monotonic()+8
                while True:
                    with get_engine().connect() as observer:
                        expired=observer.execute(text('SELECT clock_timestamp()>=:expires'),{'expires':expires}).scalar_one()
                    if expired:break
                    assert monotonic()<deadline,'SQL session expiry was not reached'
                    sleep(.02)
        response=future.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert diary_snapshot(f['placement']['id'])==original


@pytest.mark.parametrize('kind',['missing_actor','foreign_session','foreign_owner'])
def test_direct_services_require_current_session_bound_to_the_candidate(client,identities,organization,kind):
    f,_,draft=ready(client,identities,organization,submit=False)
    bad={'missing_actor':None,'foreign_session':ActorContext(f['candidate']['user_id'],f['teacher']['session_id'],()),
         'foreign_owner':actor(f['teacher'])}[kind]
    original=diary_snapshot(f['placement']['id'])
    for operation in ['save','submit','combined']:
        with pytest.raises((GovernanceError,InternshipLogScopeError)) as denied:
            direct_diary(f,draft,operation,bad)
        assert denied.value.status_code in (401,403)
        assert diary_snapshot(f['placement']['id'])==original


@pytest.mark.parametrize('operation',['save','submit','combined'])
def test_actual_current_candidate_can_use_each_diary_write(client,identities,organization,operation):
    f,_,draft=ready(client,identities,organization,submit=False)
    response=send_diary(client,f,draft,operation)
    assert response.status_code==(201 if operation=='combined' else 200),response.text
    with transaction() as conn:
        current=conn.execute(text('SELECT l.version,r.status,r.author_id FROM flexbridge.daily_logs l '
            'JOIN flexbridge.log_revisions r ON r.id=l.current_revision_id WHERE l.id=CAST(:id AS uuid)'),
            {'id':draft['id']}).mappings().one()
        assert current['status']==('DRAFT' if operation=='save' else 'SUBMITTED')
        assert str(current['author_id'])==str(f['candidate']['user_id'])
        assert current['version']==(1 if operation=='submit' else 2)


@pytest.mark.parametrize('isolation',['REPEATABLE READ','SERIALIZABLE'])
def test_diary_rejects_stale_snapshot_isolation_before_changes(client,identities,organization,isolation):
    f,_,draft=ready(client,identities,organization,submit=False)
    original=diary_snapshot(f['placement']['id'])
    with transaction() as conn:
        conn.execute(text('SET TRANSACTION ISOLATION LEVEL '+isolation))
        for operation in ['save','submit','combined']:
            with pytest.raises(InternshipLogScopeError) as denied:
                direct_diary(f,draft,operation,actor(f['candidate']))
            assert denied.value.status_code==503 and denied.value.code=='DIARY_ISOLATION_UNSAFE'
    assert diary_snapshot(f['placement']['id'])==original
