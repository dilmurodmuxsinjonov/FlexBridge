"""Both authority orderings, scoped-grant locks and business rollback on native PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic
from uuid import uuid4
import pytest
from sqlalchemy import select,text
from app.api.dependencies import ActorContext
from app.db.storage import table,transaction,now
from app.services.governance import GovernanceError,governance_service
from test_org_authority import operation,business_snapshot


def wait_for_blocker(blocker):
    deadline=monotonic()+10
    tick=Event()
    while monotonic()<deadline:
        with transaction() as conn:
            if conn.execute(text('SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE :blocker = ANY(pg_blocking_pids(pid)))'),
                    {'blocker':blocker}).scalar_one():return
        tick.wait(.02)
    raise AssertionError('Competing authority change did not wait on the real database lock')


@pytest.mark.parametrize('kind',['membership_revoke','invitation_accept','member_approve'])
@pytest.mark.parametrize('change',['revoke_session','disable_mfa'])
def test_authorized_commit_precedes_waiting_security_change(client,identities,organization,monkeypatch,kind,change):
    from app.services import authority,organizations,invitations
    _,user,request=operation(kind,client,identities,organization)
    held,release=Event(),Event();pid=[];original=authority.mfa_authority
    def hold(conn,actor):
        original(conn,actor)
        if actor.user_id==user['user_id']:
            pid.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
            held.set();assert release.wait(30),'Authority release timed out'
    for module in (authority,organizations,invitations):monkeypatch.setattr(module,'mfa_authority',hold)
    def change_security():
        if change=='revoke_session':
            return client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers'])
        return client.patch('/api/v1/me/security',headers=user['headers'],json={
            'enable_totp':False,'current_password':'correct-passphrase-2026'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending=pool.submit(request)
        try:
            assert held.wait(30),'Business request did not hold authority'
            revocation=pool.submit(change_security)
            wait_for_blocker(pid[0])
            assert not revocation.done()
        finally:release.set()
        result=pending.result(timeout=30);changed=revocation.result(timeout=30)
    assert result.status_code==200,result.text
    assert changed.status_code==200,changed.text
    assert client.get('/api/v1/auth/me',headers=user['headers']).status_code==401
    with transaction() as conn:
        member_id=result.json().get('membership_id') or result.json()['id']
        status=conn.execute(select(table('org_memberships').c.status).where(table('org_memberships').c.id==member_id)).scalar_one()
    assert status==('REVOKED' if kind=='membership_revoke' else 'ACTIVE')


@pytest.mark.parametrize('kind',['submit','patch','membership_revoke','invitation_create','invitation_revoke','member_create','member_approve','join_detail'])
def test_completed_scoped_grant_revocation_blocks_after_preflight(client,identities,organization,monkeypatch,kind):
    module,user,request=operation(kind,client,identities,organization)
    checked,release=Event(),Event();original=module.require_mfa
    def pause(actor):
        original(actor)
        checked.set();assert release.wait(30)
    monkeypatch.setattr(module,'require_mfa',pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(request)
        try:
            assert checked.wait(30)
            with transaction() as conn:
                members,grants=table('org_memberships'),table('org_role_grants')
                ids=select(members.c.id).where(members.c.user_id==user['user_id'],members.c.organization_id==organization)
                conn.execute(grants.update().where(grants.c.membership_id.in_(ids)).values(revoked_at=now(),updated_at=now()))
            before=business_snapshot()
        finally:release.set()
        response=pending.result(timeout=30)
    assert response.status_code==403,(kind,response.status_code)
    assert business_snapshot()==before


def test_scoped_grant_cannot_change_during_authorized_commit(client,identities,organization,monkeypatch):
    from app.services import organizations
    _,user,request=operation('membership_revoke',client,identities,organization)
    held,release=Event(),Event();pid=[];original=organizations.org_authority
    def hold(conn,*args):
        result=original(conn,*args)
        pid.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
        held.set();assert release.wait(30)
        return result
    monkeypatch.setattr(organizations,'org_authority',hold)
    def revoke_grant():
        with transaction() as conn:
            grants,members=table('org_role_grants'),table('org_memberships')
            ids=select(members.c.id).where(members.c.user_id==user['user_id'],members.c.organization_id==organization)
            conn.execute(grants.update().where(grants.c.membership_id.in_(ids)).values(revoked_at=now(),updated_at=now()))
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending=pool.submit(request)
        try:
            assert held.wait(30)
            revocation=pool.submit(revoke_grant)
            wait_for_blocker(pid[0]);assert not revocation.done()
        finally:release.set()
        response=pending.result(timeout=30);revocation.result(timeout=30)
    assert response.status_code==200,response.text


@pytest.mark.parametrize('kind,action',[
    ('register_bootstrap','ORG_VERIFICATION_SUBMITTED'),('submit','ORG_VERIFICATION_SUBMITTED'),
    ('resubmit','ORG_VERIFICATION_RESUBMITTED'),('membership_revoke','ORG_MEMBERSHIP_REVOKED'),
    ('invitation_create','ORG_INVITATION_CREATED'),('invitation_accept','ORG_INVITATION_ACCEPTED'),
    ('invitation_revoke','ORG_INVITATION_REVOKED'),('member_approve','ORG_MEMBER_APPROVED_DUAL_CONTROL')])
def test_audit_failure_rolls_back_authorized_business_effect(client,identities,organization,monkeypatch,kind,action):
    from app.core.audit import AppendOnlyAuditStore
    _,_,request=operation(kind,client,identities,organization)
    before=business_snapshot();original=AppendOnlyAuditStore.append_audit_event
    def fail(self,**kwargs):
        if kwargs['action']==action:raise RuntimeError('Injected transactional audit failure')
        return original(self,**kwargs)
    monkeypatch.setattr(AppendOnlyAuditStore,'append_audit_event',fail)
    response=request()
    assert response.status_code==503,response.text
    assert response.json()['detail']['code']=='DEPENDENCY_UNAVAILABLE'
    assert business_snapshot()==before


@pytest.mark.parametrize('session_kind',['missing','other_user','unknown'])
def test_governance_service_requires_actual_current_actor_session(identities,organization,session_kind):
    owner=identities('OWNER',organization);target=identities()
    session={'missing':None,'other_user':target['session_id'],'unknown':str(uuid4())}[session_kind]
    actor=ActorContext(owner['user_id'],session,('OWNER','MODERATOR'))
    before=business_snapshot()
    with pytest.raises(GovernanceError,match='MFA_REQUIRED'):
        governance_service.create_org_member_request(actor=actor,organization_id=organization,user_id=target['user_id'],role_code='HR')
    assert business_snapshot()==before
