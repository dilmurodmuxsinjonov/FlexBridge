"""Real HTTP session mutation before/after observed PostgreSQL authority waits."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import select,text,func
from app.db.storage import table,transaction,get_engine
from test_institution_onboarding import first_claim,submit,accept,claim,decide,active_coordinator
from test_org_authority_transactions import wait_for_blocker


def operation(kind,client,identities):
    if kind=='revoke':
        f=active_coordinator(client,identities)
        request=lambda:client.post('/api/v1/institution-appointments/'+f['appointment']+'/revoke',headers=f['user']['headers'],json={'reason':'Current named appointee withdraws this appointment'})
        return f,f['user'],request,('institutions',f['institution_id'])
    f=first_claim(identities)
    if kind=='submit':return f,f['user'],lambda:submit(client,f),('files',f['document']['id'])
    created=submit(client,f);assert created.status_code==202,created.text
    f.update(appointment=created.json()['id'],case=created.json()['case_id'],institution_id=created.json()['institution_id'])
    moderator=identities('MODERATOR');f['moderator']=moderator
    if kind=='review':
        assert accept(client,f,f['appointment']).status_code==200
        assert claim(client,moderator,f['case']).status_code==200
        return f,moderator,lambda:decide(client,moderator,f['case']),('institutions',f['institution_id'])
    assert claim(client,moderator,f['case']).status_code==200
    reviewed=decide(client,moderator,f['case'],'NEEDS_INFO' if kind=='resubmit' else 'APPROVE');assert reviewed.status_code==200,reviewed.text
    if kind=='consent':request=lambda:accept(client,f,f['appointment'])
    else:
        request=lambda:client.post('/api/v1/institution-appointments/'+f['appointment']+'/revisions',headers=f['user']['headers'],json={
            **f['body'],'expected_revision':1,'evidence_note':'Revised appointment documents after independent review feedback'})
    return f,f['user'],request,('institutions',f['institution_id'])


def business_snapshot():
    with transaction() as conn:
        rows={name:[tuple(row) for row in conn.execute(select(table(name)).order_by(*table(name).primary_key.columns))] for name in (
            'institutions','institution_agreements','institution_appointments','institution_memberships','institution_role_grants',
            'institution_onboarding_requests','institution_onboarding_submissions','institution_onboarding_consents','institution_onboarding_decisions','verification_cases')}
        audits=table('audit_events')
        rows['institution_audit']=conn.execute(select(func.count()).select_from(audits).where(audits.c.action.like('INSTITUTION_%'))).scalar_one()
    return rows


@pytest.mark.parametrize('kind',['submit','review','consent','resubmit','revoke'])
def test_completed_logout_while_business_row_is_held_denies_the_pending_write(client,identities,kind):
    f,user,request,(name,key)=operation(kind,client,identities)
    before=business_snapshot()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as blocker:
            t=table(name);blocker.execute(select(t).where(t.c.id==key).with_for_update())
            pid=blocker.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(request);wait_for_blocker(pid)
            logout=client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers']);assert logout.status_code==200,logout.text
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert business_snapshot()==before


@pytest.mark.parametrize('kind',['submit','review','consent','resubmit','revoke'])
def test_authorized_commit_precedes_a_waiting_actual_logout(client,identities,monkeypatch,kind):
    from app.services import institution_onboarding as module
    f,user,request,_=operation(kind,client,identities)
    guard='moderator_authority' if kind=='review' else 'account_authority'
    original=getattr(module,guard);held,release=Event(),Event();pids=[]
    def hold(conn,actor,*args,**kwargs):
        result=original(conn,actor,*args,**kwargs)
        if actor.user_id==user['user_id']:
            pids.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
            held.set();assert release.wait(30),'Institution authority release timed out'
        return result
    monkeypatch.setattr(module,guard,hold)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending=pool.submit(request)
        try:
            assert held.wait(30),'Institution business request did not acquire current authority'
            logout=pool.submit(lambda:client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers']))
            wait_for_blocker(pids[0]);assert not logout.done()
        finally:release.set()
        response=pending.result(timeout=30);changed=logout.result(timeout=30)
    assert response.status_code==(202 if kind in ('submit','resubmit') else 200),response.text
    assert changed.status_code==200,changed.text
    assert client.get('/api/v1/auth/me',headers=user['headers']).status_code==401
