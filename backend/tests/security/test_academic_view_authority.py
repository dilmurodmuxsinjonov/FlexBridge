"""Current policy after real scope/account waits; role metadata changes are trusted administration."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest

from sqlalchemy import select

from app.db.storage import table,transaction,get_engine,now
from app.services.placements import insert_row
from app.services import academic_views
from test_academic_admission import pending_http
from test_academic_views import active_revision
from test_org_authority_transactions import wait_for_blocker


def test_coordinator_granted_after_initial_account_check_requires_mfa_before_teacher_response(client,identities,organization,monkeypatch):
    f=pending_http(client,identities,organization);active_revision(client,f)
    checked=Event();release=Event();original=academic_views.account_authority
    def hold(conn,actor,**kwargs):
        original(conn,actor,**kwargs)
        if not checked.is_set():
            checked.set();assert release.wait(30)
    monkeypatch.setattr(academic_views,'account_authority',hold)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(lambda:client.get('/api/v1/institutions/'+f['inst']['id']+'/supervisions',headers=f['teacher']['headers']))
        try:
            assert checked.wait(30)
            with transaction() as conn:
                roles=table('role_catalog')
                rid=conn.execute(select(roles.c.id).where(roles.c.code=='COORDINATOR',roles.c.scope_kind=='INSTITUTION')).scalar_one()
                insert_row(conn,'institution_role_grants',membership_id=f['teacher_member']['id'],role_id=rid,appointment_id=f['teacher_appointment']['id'])
        finally:release.set()
        response=pending.result(timeout=30)
    assert response.status_code==403 and response.json()['detail']['code']=='MFA_REQUIRED',response.text


@pytest.mark.parametrize('kind',['supervisions','assignment-queue','review-queue'])
@pytest.mark.parametrize('change',['session','grant'])
def test_current_authority_is_checked_after_real_institution_wait(client,identities,organization,kind,change):
    f=pending_http(client,identities,organization);user=f['coord'];grant=f['grant']
    if kind!='assignment-queue':
        _,draft=active_revision(client,f);user=f['teacher'];grant=f['teacher_grant']
        if kind=='review-queue':
            response=client.post('/api/v1/logs/'+draft['id']+'/submit',headers=f['candidate']['headers'])
            assert response.status_code==200,response.text
    path='/api/v1/me/academic-review-queue' if kind=='review-queue' else '/api/v1/institutions/'+f['inst']['id']+'/'+kind
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            t=table('institutions');holder.execute(select(t).where(t.c.id==f['inst']['id']).with_for_update())
            from sqlalchemy import text
            pid=holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(lambda:client.get(path,headers=user['headers']));wait_for_blocker(pid)
            if change=='session':
                response=client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers'])
                assert response.status_code==200,response.text
            else:
                with transaction() as conn:
                    t=table('institution_role_grants');conn.execute(t.update().where(t.c.id==grant['id']).values(revoked_at=now()))
        response=pending.result(timeout=30)
    if kind=='review-queue' and change=='grant':
        assert response.status_code==200 and response.json()['items']==[],response.text
    else:assert response.status_code in (401,403),response.text
