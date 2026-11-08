"""Contact-bound invitation authority, revocation, races and secret-safe URL handling."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db.storage import table,transaction,now
from app.services.placements import insert_row
from app.services.identity import identity_service
from test_organizations import mfa_user

DEST='+998901234567'


def contact(user,value=DEST,channel='PHONE',verified=True):
    with transaction() as conn:
        return insert_row(conn,'user_contacts',user_id=user['user_id'],channel=channel,normalized_value=value,
            verified_at=now() if verified else None,is_primary=True)


def invite(client,owner,org,destination=DEST,role='HR',channel='PHONE'):
    return client.post('/api/v1/organizations/'+org+'/invitations',headers=owner['headers'],json={
        'channel':channel,'destination':destination,'role_code':role})


def accept(client,user,token):
    return client.post('/api/v1/invitations/'+token+'/accept',headers=user['headers'],json={})


def test_fresh_invitation_creates_new_grant_and_preserves_revoked_history(client,identities,organization):
    owner=identities('OWNER',organization);user=mfa_user(identities);contact(user)
    response=invite(client,owner,organization);assert response.status_code==201,response.text
    first=response.json();response=accept(client,user,first['token'])
    assert response.status_code==200,response.text
    member=response.json()['membership_id']
    response=client.post('/api/v1/organizations/'+organization+'/memberships/'+member+'/revoke',headers=owner['headers'],
        json={'reason':'Revoke the former staff relationship'})
    assert response.status_code==200,response.text
    with transaction() as conn:
        old=dict(conn.execute(select(table('org_role_grants')).where(table('org_role_grants').c.membership_id==member)).mappings().one())
    assert old['revoked_at'] is not None
    response=invite(client,owner,organization);assert response.status_code==201,response.text
    fresh=response.json();response=accept(client,user,fresh['token'])
    assert response.status_code==200,response.text
    with transaction() as conn:
        grants=[dict(r) for r in conn.execute(select(table('org_role_grants')).where(table('org_role_grants').c.membership_id==member)).mappings()]
        assert len(grants)==2
        assert next(r for r in grants if r['id']==old['id'])==old
        active=[r for r in grants if r['revoked_at'] is None]
        assert len(active)==1 and active[0]['id']!=old['id']
    response=accept(client,user,fresh['token']);assert response.status_code==200 and response.json()['idempotent_replay']


def test_invitation_is_hashed_and_explicit_role_is_accepted_once(client,identities,organization):
    owner=identities('OWNER',organization);user=mfa_user(identities);contact(user)
    result=invite(client,owner,organization)
    assert result.status_code==201,result.text
    invitation=result.json();token=invitation['token']
    assert result.headers['cache-control']=='no-store'
    with transaction() as conn:
        row=conn.execute(select(table('org_invitations'))).mappings().one()
        assert token not in row.values() and DEST not in row.values() and len(row['token_digest'])==64
        assert 86390<(row['expires_at']-now()).total_seconds()<=86400
    preview=client.get('/api/v1/invitations/'+token)
    assert preview.status_code==200 and preview.json()['role_code']=='HR'
    assert all(k not in preview.json() for k in ('destination','contact_digest','target_user_id','file_ids'))
    response=accept(client,user,token)
    assert response.status_code==200,response.text
    assert not response.json()['idempotent_replay']
    repeat=accept(client,user,token)
    assert repeat.status_code==200 and repeat.json()['idempotent_replay']
    with transaction() as conn:
        conn.execute(table('org_invitations').update().where(table('org_invitations').c.id==invitation['id']).values(expires_at=now()-timedelta(seconds=1)))
    assert accept(client,user,token).json()['idempotent_replay']
    roles=client.get('/api/v1/auth/me',headers=user['headers']).json()['roles']
    assert 'HR' in roles and 'OWNER' not in roles and 'BILLING' not in roles
    assert client.get('/api/v1/invitations/'+token).status_code==404


@pytest.mark.parametrize('role',['OWNER','ADMIN','MODERATOR','SUPER_ADMIN'])
def test_privileged_invitation_roles_are_forbidden(client,identities,organization,role):
    assert invite(client,identities('OWNER',organization),organization,role=role).status_code==422


def test_wrong_account_unverified_contact_and_password_session_are_rejected(client,identities,organization):
    owner=identities('OWNER',organization);user=mfa_user(identities);wrong=mfa_user(identities)
    row=contact(user,verified=False)
    token=invite(client,owner,organization).json()['token']
    assert accept(client,wrong,token).status_code==403
    assert accept(client,user,token).status_code==403
    with transaction() as conn:
        conn.execute(table('user_contacts').update().where(table('user_contacts').c.id==row['id']).values(verified_at=now()))
    assert accept(client,user,token).status_code==200
    plain=identities()
    assert accept(client,plain,token).status_code==403


@pytest.mark.parametrize('state',['EXPIRED','REVOKED','SUPERSEDED'])
def test_dead_invitations_cannot_be_previewed_or_accepted(client,identities,organization,state):
    owner=identities('OWNER',organization);user=mfa_user(identities);contact(user)
    row=invite(client,owner,organization).json();token=row['token']
    if state=='EXPIRED':
        with transaction() as conn:
            conn.execute(table('org_invitations').update().where(table('org_invitations').c.id==row['id']).values(expires_at=now()-timedelta(seconds=1)))
    elif state=='REVOKED':
        response=client.post('/api/v1/organizations/'+organization+'/invitations/'+row['id']+'/revoke',
            headers=owner['headers'],json={'reason':'Cancel this staff invitation'})
        assert response.status_code==200,response.text
    else:assert invite(client,owner,organization).status_code==201
    assert client.get('/api/v1/invitations/'+token).status_code==404
    assert accept(client,user,token).status_code==404


def test_contact_recycling_cannot_move_an_existing_target_invitation(client,identities,organization):
    owner=identities('OWNER',organization);old=mfa_user(identities);contact(old)
    token=invite(client,owner,organization).json()['token']
    new=mfa_user(identities)
    with transaction() as conn:
        identity_service._bind_contact(conn,user_id=new['user_id'],channel='PHONE',value=DEST)
    assert accept(client,new,token).status_code==403
    with transaction() as conn:
        assert not conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.organization_id==organization,
            table('org_memberships').c.user_id==new['user_id'])).first()


def test_email_normalization_and_unknown_contact_registration(client,identities,organization):
    owner=identities('OWNER',organization)
    token=invite(client,owner,organization,destination='Person@Example.Test',channel='EMAIL',role='MENTOR').json()['token']
    user=mfa_user(identities);contact(user,'person@example.test','EMAIL')
    assert accept(client,user,token).status_code==200
    assert 'MENTOR' in client.get('/api/v1/auth/me',headers=user['headers']).json()['roles']


def test_parallel_accept_has_one_membership_and_grant(client,identities,organization):
    owner=identities('OWNER',organization);user=mfa_user(identities);contact(user)
    token=invite(client,owner,organization,role='BILLING').json()['token']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[future.result(timeout=20) for future in [pool.submit(accept,client,user,token) for _ in range(2)]]
    assert all(r.status_code==200 for r in results),[r.status_code for r in results]
    assert sorted(r.json()['idempotent_replay'] for r in results)==[False,True]
    with transaction() as conn:
        memberships=table('org_memberships');grants=table('org_role_grants')
        ids=list(conn.execute(select(memberships.c.id).where(memberships.c.organization_id==organization,
            memberships.c.user_id==user['user_id'])).scalars())
        assert len(ids)==1
        assert conn.execute(select(func.count()).select_from(grants).where(grants.c.membership_id==ids[0])).scalar_one()==1


def test_inviter_membership_revocation_invalidates_pending_link(client,identities,organization):
    owner,other=identities('OWNER',organization),identities('OWNER',organization)
    user=mfa_user(identities);contact(user)
    token=invite(client,owner,organization).json()['token']
    with transaction() as conn:
        mid=conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.user_id==owner['user_id'])).scalar_one()
    response=client.post('/api/v1/organizations/'+organization+'/memberships/'+mid+'/revoke',headers=other['headers'],
        json={'reason':'Revoke former owner membership'})
    assert response.status_code==200,response.text
    assert client.get('/api/v1/invitations/'+token).status_code==404
    assert accept(client,user,token).status_code==404


def test_owner_role_revocation_is_rechecked_without_membership_event(client,identities,organization):
    owner=identities('OWNER',organization);user=mfa_user(identities);contact(user)
    token=invite(client,owner,organization).json()['token']
    with transaction() as conn:
        mid=conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.user_id==owner['user_id'])).scalar_one()
        conn.execute(table('org_role_grants').update().where(table('org_role_grants').c.membership_id==mid).values(revoked_at=now()))
    assert accept(client,user,token).status_code==404


def test_old_links_never_restore_revoked_membership_but_new_explicit_invite_can(client,identities,organization):
    owner=identities('OWNER',organization);user=mfa_user(identities);contact(user)
    first=invite(client,owner,organization,role='BILLING').json()['token']
    joined=accept(client,user,first).json()
    pending=invite(client,owner,organization,role='HR').json()['token']
    response=client.post('/api/v1/organizations/'+organization+'/memberships/'+joined['membership_id']+'/revoke',
        headers=owner['headers'],json={'reason':'Revoke staff organization scope'})
    assert response.status_code==200,response.text
    assert accept(client,user,first).status_code==409
    assert accept(client,user,pending).status_code==404
    fresh=invite(client,owner,organization,role='HR').json()['token']
    assert accept(client,user,fresh).status_code==200
    roles=client.get('/api/v1/auth/me',headers=user['headers']).json()['roles']
    assert 'HR' in roles and 'BILLING' not in roles and 'OWNER' not in roles


def test_invitation_scope_and_self_invites(client,identities,organization):
    owner=identities('OWNER',organization);outsider=mfa_user(identities)
    assert invite(client,outsider,organization).status_code==403
    with transaction() as conn:
        other=insert_row(conn,'organizations',tax_id='987654321',legal_name='Other',public_name='Other',region='Tashkent',status='VERIFIED')
    assert invite(client,owner,other['id']).status_code==403
    contact(owner)
    assert invite(client,owner,organization).status_code==403
    assert client.post('/api/v1/invitations/'+'a'*43+'/accept',json={}).status_code==401


def test_tampered_owner_role_in_database_still_cannot_be_granted(client,identities,organization):
    owner=identities('OWNER',organization);user=mfa_user(identities);contact(user)
    invitation=invite(client,owner,organization).json()
    with transaction() as conn:
        rid=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='OWNER')).scalar_one()
        conn.execute(table('org_invitations').update().where(table('org_invitations').c.id==invitation['id']).values(role_id=rid))
    assert accept(client,user,invitation['token']).status_code==404


def test_inactive_legacy_grants_are_not_implicitly_reactivated(client,identities,organization):
    owner=identities('OWNER',organization);user=mfa_user(identities);contact(user)
    with transaction() as conn:
        membership=insert_row(conn,'org_memberships',organization_id=organization,user_id=user['user_id'],status='PENDING_APPROVAL')
        rid=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='BILLING')).scalar_one()
        insert_row(conn,'org_role_grants',membership_id=membership['id'],role_id=rid,granted_by_id=owner['user_id'])
    token=invite(client,owner,organization,role='HR').json()['token']
    assert accept(client,user,token).status_code==200
    roles=client.get('/api/v1/auth/me',headers=user['headers']).json()['roles']
    assert 'HR' in roles and 'BILLING' not in roles


def test_url_token_is_redacted_even_for_oversized_body_and_unhandled_error():
    from app.core.iam_http import IAMHTTPMiddleware
    token='A'*43
    async def exercise(oversized=False):
        scope={'type':'http','path':'/api/v1/invitations/'+token,'raw_path':('/api/v1/invitations/'+token).encode(),'query_string':b'secret=query'}
        messages=[]
        async def app(scope,receive,send):raise RuntimeError('synthetic error')
        async def receive():return {'type':'http.request','body':b'x'*20 if oversized else b'','more_body':False}
        async def send(message):messages.append(message)
        try:await IAMHTTPMiddleware(app,max_bytes=10)(scope,receive,send)
        except RuntimeError:pass
        assert token not in scope['path'] and token.encode() not in scope['raw_path'] and scope['query_string']==b''
        if oversized:assert messages[0]['status']==413
    asyncio.run(exercise());asyncio.run(exercise(True))
