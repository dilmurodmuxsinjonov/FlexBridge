"""Public OTP proof/registration/contact bind racing with held invitation authority."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import select
from app.db.storage import transaction,table
from test_iam import delivery,proof
from test_organizations import mfa_user
from test_invitations import contact,invite,accept,DEST


@pytest.mark.parametrize('mode',['REGISTER','CONTACT'])
@pytest.mark.parametrize('action',['create','accept'])
def test_public_contact_recycling_returns_retry_without_deadlock_or_partial_grant(
        client,identities,organization,monkeypatch,delivery,mode,action):
    from app.services import identity,invitations
    owner=identities('OWNER',organization)
    recipient=mfa_user(identities) if action=='accept' else owner
    contact(recipient)
    token=None
    if action=='accept':
        response=invite(client,owner,organization);assert response.status_code==201,response.text
        token=response.json()['token']
    new_holder=mfa_user(identities) if mode=='CONTACT' else None
    verification=proof(client,delivery,purpose=mode,destination=DEST,
        headers=new_holder['headers'] if new_holder else None)
    bound,waiting,release=Event(),Event(),Event()
    original_bind,original_invite=identity.lock_contact,invitations.lock_contact
    def hold(conn,value):
        original_bind(conn,value);bound.set();assert release.wait(30)
    def observe(conn,value):
        try:return original_invite(conn,value)
        finally:waiting.set()
    monkeypatch.setattr(identity,'lock_contact',hold)
    monkeypatch.setattr(invitations,'lock_contact',observe)
    def recycle():
        if mode=='CONTACT':
            return client.post('/api/v1/me/contacts',headers=new_holder['headers'],json={
                'verification_token':verification,'current_password':'correct-passphrase-2026'})
        return client.post('/api/v1/auth/register',json={'verification_token':verification,
            'display_name':'New Contact Holder','password':'correct-passphrase-2026','adult_confirmed':True,
            'terms_version':'test-terms-v1','privacy_version':'test-privacy-v1'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        binding=pool.submit(recycle)
        try:
            assert bound.wait(30)
            pending=pool.submit(accept,client,recipient,token) if token else pool.submit(invite,client,owner,organization)
            assert waiting.wait(30)
        finally:release.set()
        result=pending.result(timeout=30);changed=binding.result(timeout=30)
    assert result.status_code==409 and result.json()['detail']['code']=='INVITATION_BUSY_RETRY',result.text
    assert changed.status_code==201,changed.text
    assert client.get('/api/v1/auth/me',headers=recipient['headers']).status_code==401
    with transaction() as conn:
        contacts=table('user_contacts')
        current=conn.execute(select(contacts.c.user_id).where(contacts.c.normalized_value==DEST,
            contacts.c.revoked_at.is_(None))).scalar_one()
        assert current!=recipient['user_id']
        if token:
            assert not conn.execute(select(table('org_invitations').c.id).where(table('org_invitations').c.accepted_at.is_not(None))).first()
            assert not conn.execute(select(table('org_memberships').c.id).where(
                table('org_memberships').c.organization_id==organization,
                table('org_memberships').c.user_id==recipient['user_id'])).first()
        else:assert not conn.execute(select(table('org_invitations').c.id)).first()


def test_contact_discovered_after_initial_lookup_is_not_used_as_an_unlocked_fk_target(client,identities,organization,monkeypatch,delivery):
    from app.services import invitations
    owner=identities('OWNER',organization);recipient=mfa_user(identities)
    verification=proof(client,delivery,purpose='CONTACT',destination=DEST,headers=recipient['headers'])
    checked,release=Event(),Event();original=invitations.lock_contact
    def pause(conn,value):
        checked.set();assert release.wait(30)
        return original(conn,value)
    monkeypatch.setattr(invitations,'lock_contact',pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(invite,client,owner,organization)
        try:
            assert checked.wait(30)
            response=client.post('/api/v1/me/contacts',headers=recipient['headers'],json={
                'verification_token':verification,'current_password':'correct-passphrase-2026'})
            assert response.status_code==201,response.text
        finally:release.set()
        response=pending.result(timeout=30)
    assert response.status_code==409 and response.json()['detail']['code']=='INVITATION_BUSY_RETRY',response.text
    with transaction() as conn:assert not conn.execute(select(table('org_invitations').c.id)).first()
    response=invite(client,owner,organization);assert response.status_code==201,response.text
    response=accept(client,recipient,response.json()['token']);assert response.status_code==200,response.text


def test_existing_contact_recycled_before_target_pin_is_rechecked_before_fk_write(client,identities,organization,monkeypatch,delivery):
    from app.services import invitations
    owner=identities('OWNER',organization);old_holder=mfa_user(identities);new_holder=mfa_user(identities)
    contact(old_holder)
    verification=proof(client,delivery,purpose='CONTACT',destination=DEST,headers=new_holder['headers'])
    checked,release=Event(),Event();original=invitations.lock_target_user
    def pause(conn,user_id):
        checked.set();assert release.wait(30)
        return original(conn,user_id)
    monkeypatch.setattr(invitations,'lock_target_user',pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(invite,client,owner,organization)
        try:
            assert checked.wait(30)
            changed=client.post('/api/v1/me/contacts',headers=new_holder['headers'],json={
                'verification_token':verification,'current_password':'correct-passphrase-2026'})
            assert changed.status_code==201,changed.text
        finally:release.set()
        result=pending.result(timeout=30)
    assert result.status_code==409 and result.json()['detail']['code']=='INVITATION_BUSY_RETRY',result.text
    assert client.get('/api/v1/auth/me',headers=old_holder['headers']).status_code==401
    with transaction() as conn:assert not conn.execute(select(table('org_invitations').c.id)).first()
    response=invite(client,owner,organization);assert response.status_code==201,response.text
    with transaction() as conn:
        target=conn.execute(select(table('org_invitations').c.target_user_id).where(
            table('org_invitations').c.id==response.json()['id'])).scalar_one()
        assert target==new_holder['user_id']
    response=accept(client,new_holder,response.json()['token']);assert response.status_code==200,response.text
