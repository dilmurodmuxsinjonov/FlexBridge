"""Initial moderation holds current security and platform scope after opportunity locks."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import uuid4
import pytest
from sqlalchemy import select,text,event
from app.api.dependencies import ActorContext
from app.db.storage import table,transaction,get_engine,now
from app.services.governance import governance_service,GovernanceError
from test_adapters_and_quota import draft
from test_organizations import mfa_user
from test_org_authority_transactions import wait_for_blocker


def setup_action(client,identities,org,action='REJECT'):
    owner=identities('OWNER',org);moderator=identities('MODERATOR');revision=draft(owner,org)
    body=dict(target_entity_type='opportunity',target_entity_id=revision['opportunity_id'],
        action_type=action,policy_code='EVIDENCE_REVIEW',reason_code='MATERIAL_EVIDENCE',
        justification='Independent review of the current opportunity is complete')
    def request():return client.post('/api/v1/moderation/actions',headers=moderator['headers'],json=body)
    return owner,moderator,revision,body,request


def snapshot():
    with transaction() as conn:
        return {name:sorted((dict(row) for row in conn.execute(select(table(name))).mappings()),key=repr)
            for name in ('opportunities','opportunity_revisions','moderation_cases','moderation_actions','audit_events')}


def change_authority(client,user,change):
    if change=='session':
        response=client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers'])
        assert response.status_code==200,response.text
    elif change=='disable_mfa':
        response=client.patch('/api/v1/me/security',headers=user['headers'],json={
            'enable_totp':False,'current_password':'correct-passphrase-2026'})
        assert response.status_code==200,response.text
    else:
        # Trusted administrative mutations; no public privilege-provisioning API claimed.
        with transaction() as conn:
            users,grants=table('users'),table('platform_role_grants')
            if change=='account':
                conn.execute(users.update().where(users.c.id==user['user_id']).values(status='SUSPENDED',updated_at=now()))
            elif change=='auth_version':
                conn.execute(users.update().where(users.c.id==user['user_id']).values(auth_version=users.c.auth_version+1,updated_at=now()))
            elif change=='role':
                conn.execute(grants.update().where(grants.c.user_id==user['user_id']).values(revoked_at=now(),updated_at=now()))
            elif change=='role_expiry':
                conn.execute(grants.update().where(grants.c.user_id==user['user_id']).values(expires_at=now()-timedelta(seconds=1),updated_at=now()))
            else:raise AssertionError(change)


@pytest.mark.parametrize('change',['session','disable_mfa','account','auth_version','role','role_expiry'])
def test_completed_authority_change_blocks_initial_decision(client,identities,organization,monkeypatch,change):
    from app.services import governance
    _,moderator,revision,_,request=setup_action(client,identities,organization)
    checked,release=Event(),Event();original=governance.get_row
    def pause(conn,name,row_id,lock=False):
        if name=='opportunities' and row_id==revision['opportunity_id'] and lock:
            checked.set();assert release.wait(30)
        return original(conn,name,row_id,lock)
    monkeypatch.setattr(governance,'get_row',pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(request)
        try:
            assert checked.wait(30)
            change_authority(client,moderator,change);before=snapshot()
        finally:release.set()
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),(change,response.status_code)
    assert snapshot()==before


@pytest.mark.parametrize('change',['session','disable_mfa','role'])
def test_authorized_initial_decision_commits_before_waiting_revocation(client,identities,organization,monkeypatch,change):
    from app.services import authority
    _,moderator,revision,_,request=setup_action(client,identities,organization)
    held,release=Event(),Event();pid=[];original=authority.moderator_authority
    def hold(conn,actor):
        original(conn,actor)
        pid.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
        held.set();assert release.wait(30)
    monkeypatch.setattr(authority,'moderator_authority',hold)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending=pool.submit(request)
        try:
            assert held.wait(30)
            revocation=pool.submit(change_authority,client,moderator,change)
            wait_for_blocker(pid[0]);assert not revocation.done()
        finally:release.set()
        response=pending.result(timeout=30);revocation.result(timeout=30)
    assert response.status_code==201,response.text
    with transaction() as conn:
        assert conn.execute(select(table('opportunities').c.status).where(
            table('opportunities').c.id==revision['opportunity_id'])).scalar_one()=='REJECTED'
        assert len(list(conn.execute(select(table('moderation_actions').c.id))))==1
    assert request().status_code in (401,403)


def test_parallel_initial_decisions_have_one_canonical_effect(client,identities,organization):
    _,_,_,_,request=setup_action(client,identities,organization)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:request(),range(2)))
    assert sorted(r.status_code for r in responses)==[201,409]
    with transaction() as conn:
        assert len(list(conn.execute(select(table('moderation_actions').c.id))))==1
        assert len(list(conn.execute(select(table('moderation_cases').c.id))))==1
        audit=table('audit_events')
        assert len(list(conn.execute(select(audit.c.id).where(audit.c.action=='MODERATION_REJECT'))))==1


def test_cached_moderator_roles_do_not_authorize_a_current_unprivileged_session(client,identities,organization):
    _,_,_,body,_=setup_action(client,identities,organization)
    user=mfa_user(identities);actor=ActorContext(user['user_id'],user['session_id'],('MODERATOR','ADMIN'))
    before=snapshot()
    with pytest.raises(GovernanceError,match='FORBIDDEN_ROLE'):
        governance_service.record_moderation_action(actor=actor,**body)
    assert snapshot()==before


def test_current_mfa_and_platform_role_do_not_allow_self_moderation(client,identities,organization):
    from app.services.placements import insert_row
    owner,moderator,_,body,_=setup_action(client,identities,organization)
    with transaction() as conn:
        roles=table('role_catalog')
        role_id=conn.execute(select(roles.c.id).where(roles.c.code=='MODERATOR',roles.c.scope_kind=='PLATFORM')).scalar_one()
        insert_row(conn,'platform_role_grants',user_id=owner['user_id'],role_id=role_id,
            granted_by_id=moderator['user_id'],expires_at=now()+timedelta(hours=1))
    before=snapshot()
    response=client.post('/api/v1/moderation/actions',headers=owner['headers'],json=body)
    assert response.status_code==403 and response.json()['detail']['code']=='SELF_MODERATION_FORBIDDEN',response.text
    assert snapshot()==before


@pytest.mark.parametrize('change',['session','disable_mfa'])
def test_real_opportunity_lock_wait_rechecks_security(client,identities,organization,monkeypatch,change):
    _,moderator,revision,_,request=setup_action(client,identities,organization)
    checked=Event();engine=get_engine()
    def observed(conn,cursor,statement,parameters,context,executemany):
        if 'FROM flexbridge.opportunities' in statement and 'FOR UPDATE' in statement:checked.set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        # Independent connection keeps the service ContextVar out of HTTP requests.
        with engine.begin() as conn:
            opps=table('opportunities')
            conn.execute(select(opps.c.id).where(opps.c.id==revision['opportunity_id']).with_for_update())
            event.listen(engine,'before_cursor_execute',observed)
            try:
                pending=pool.submit(request)
                assert checked.wait(30) and not pending.done()
                change_authority(client,moderator,change);before=snapshot()
            finally:event.remove(engine,'before_cursor_execute',observed)
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),(change,response.status_code)
    assert snapshot()==before


@pytest.mark.parametrize('action,status',[('APPROVE','APPROVED'),('REJECT','REJECTED')])
def test_current_independent_mfa_moderator_commits_one_decision(client,identities,organization,action,status):
    _,moderator,revision,_,request=setup_action(client,identities,organization,action)
    response=request();assert response.status_code==201,response.text
    with transaction() as conn:
        stored=conn.execute(select(table('opportunities').c.status).where(table('opportunities').c.id==revision['opportunity_id'])).scalar_one()
        actions=list(conn.execute(select(table('moderation_actions'))).mappings())
        assert stored==status and len(actions)==1
        assert actions[0]['actor_id']==moderator['user_id'] and actions[0]['action']==action
    before=snapshot();assert request().status_code==409;assert snapshot()==before


@pytest.mark.parametrize('phase',['case','action','audit'])
def test_initial_moderation_failure_leaves_no_partial_effect(client,identities,organization,monkeypatch,phase):
    from app.services import governance
    from app.core.audit import AppendOnlyAuditStore
    _,_,_,_,request=setup_action(client,identities,organization)
    before=snapshot();original_insert=governance.insert_row;original_audit=AppendOnlyAuditStore.append_audit_event
    def insert(conn,name,**kwargs):
        if name=={'case':'moderation_cases','action':'moderation_actions'}.get(phase):raise RuntimeError('Injected moderation write failure')
        return original_insert(conn,name,**kwargs)
    def audit(self,**kwargs):
        if phase=='audit' and kwargs['action']=='MODERATION_REJECT':raise RuntimeError('Injected moderation audit failure')
        return original_audit(self,**kwargs)
    monkeypatch.setattr(governance,'insert_row',insert);monkeypatch.setattr(AppendOnlyAuditStore,'append_audit_event',audit)
    response=request();assert response.status_code==503,response.text
    assert snapshot()==before


@pytest.mark.parametrize('session_kind',['missing','foreign','unknown'])
def test_initial_moderation_service_cannot_rebuild_authority_from_user_id(identities,organization,client,session_kind):
    _,moderator,_,body,_=setup_action(client,identities,organization)
    other=identities()
    session={'missing':None,'foreign':other['session_id'],'unknown':str(uuid4())}[session_kind]
    actor=ActorContext(moderator['user_id'],session,('MODERATOR','ADMIN'))
    before=snapshot()
    with pytest.raises(GovernanceError,match='MFA_REQUIRED'):
        governance_service.record_moderation_action(actor=actor,**body)
    assert snapshot()==before
