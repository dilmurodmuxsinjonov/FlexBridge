"""Changed concurrent contact recycling probe against pinned organization authority fix."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from sqlalchemy import select
from app.db.storage import transaction,table,get_engine
from app.core.iam_security import issue_continuation
from test_organizations import mfa_user
from test_invitations import contact,invite,accept,DEST


def test_contact_rebind_and_invitation_do_not_form_a_database_deadlock(client,identities,organization,monkeypatch):
    from app.services import identity,invitations
    owner=identities('OWNER',organization);recipient=mfa_user(identities);contact(owner)
    # Trusted contact-verification proof; no real OTP delivery claimed.
    with transaction() as conn:
        proof=issue_continuation(conn,'CONTACT_CONTACT',user_id=recipient['user_id'],payload={'channel':'PHONE','value':DEST})
    bound,inviting,release=Event(),Event(),Event()
    original_bind,original_invite=identity.lock_contact,invitations.lock_contact
    def hold_contact(conn,value):
        original_bind(conn,value);bound.set();assert release.wait(30)
    def watch_contact(conn,value):
        inviting.set();return original_invite(conn,value)
    monkeypatch.setattr(identity,'lock_contact',hold_contact)
    monkeypatch.setattr(invitations,'lock_contact',watch_contact)
    with ThreadPoolExecutor(max_workers=2) as pool:
        binding=pool.submit(client.post,'/api/v1/me/contacts',headers=recipient['headers'],json={
            'verification_token':proof,'current_password':'correct-passphrase-2026'})
        try:
            assert bound.wait(30)
            invitation=pool.submit(invite,client,owner,organization)
            assert inviting.wait(30)
        finally:release.set()
        binding_result=binding.result(timeout=30);invitation_result=invitation.result(timeout=30)
    assert binding_result.status_code==201 and invitation_result.status_code in (401,403,409),(
        binding_result.status_code,invitation_result.status_code)
    assert invitation_result.status_code==409
    assert invitation_result.json()['detail']['code']=='INVITATION_BUSY_RETRY'
    with transaction() as conn:assert not conn.execute(select(table('org_invitations').c.id)).first()


def test_contact_rebind_and_acceptance_do_not_form_a_database_deadlock(client,identities,organization,monkeypatch):
    from app.services import identity,invitations
    owner=identities('OWNER',organization);recipient=mfa_user(identities);new_holder=mfa_user(identities)
    contact(recipient);response=invite(client,owner,organization);assert response.status_code==201,response.text
    invitation=response.json()
    with transaction() as conn:
        proof=issue_continuation(conn,'CONTACT_CONTACT',user_id=new_holder['user_id'],payload={'channel':'PHONE','value':DEST})
    bound,accepting,release=Event(),Event(),Event()
    original_bind,original_accept=identity.lock_contact,invitations.lock_contact
    def hold_contact(conn,value):
        original_bind(conn,value);bound.set();assert release.wait(30)
    def watch_contact(conn,value):
        accepting.set();return original_accept(conn,value)
    monkeypatch.setattr(identity,'lock_contact',hold_contact)
    monkeypatch.setattr(invitations,'lock_contact',watch_contact)
    with ThreadPoolExecutor(max_workers=2) as pool:
        binding=pool.submit(client.post,'/api/v1/me/contacts',headers=new_holder['headers'],json={
            'verification_token':proof,'current_password':'correct-passphrase-2026'})
        try:
            assert bound.wait(30)
            pending=pool.submit(accept,client,recipient,invitation['token'])
            assert accepting.wait(30)
        finally:release.set()
        changed=binding.result(timeout=30);result=pending.result(timeout=30)
    assert changed.status_code==201,changed.text
    assert result.status_code==409 and result.json()['detail']['code']=='INVITATION_BUSY_RETRY',result.text
    with transaction() as conn:
        stored=conn.execute(select(table('org_invitations')).where(table('org_invitations').c.id==invitation['id'])).mappings().one()
        assert stored['accepted_at'] is None
        assert not conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.user_id==recipient['user_id'])).first()


def test_existing_target_user_lock_returns_retry_then_fresh_invite_succeeds(client,identities,organization):
    owner=identities('OWNER',organization);recipient=mfa_user(identities);contact(recipient)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as conn:
            users=table('users')
            conn.execute(select(users.c.id).where(users.c.id==recipient['user_id']).with_for_update())
            response=pool.submit(invite,client,owner,organization).result(timeout=20)
        assert response.status_code==409,response.text
        assert response.json()['detail']['code']=='INVITATION_BUSY_RETRY'
    response=invite(client,owner,organization);assert response.status_code==201,response.text
    response=accept(client,recipient,response.json()['token']);assert response.status_code==200,response.text


def test_inviter_user_lock_returns_retry_without_grant_then_accepts(client,identities,organization):
    owner=identities('OWNER',organization);recipient=mfa_user(identities);contact(recipient)
    response=invite(client,owner,organization);assert response.status_code==201,response.text
    token=response.json()['token']
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as conn:
            users=table('users')
            conn.execute(select(users.c.id).where(users.c.id==owner['user_id']).with_for_update())
            result=pool.submit(accept,client,recipient,token).result(timeout=20)
        assert result.status_code==409,result.text
        assert result.json()['detail']['code']=='INVITATION_BUSY_RETRY'
    response=accept(client,recipient,token);assert response.status_code==200,response.text
