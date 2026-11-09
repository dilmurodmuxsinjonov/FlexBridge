"""Changed-state HTTP requests must hold current authority through their business UOW."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import select
from app.db.storage import table, transaction, get_engine
from test_candidate import cv_fixture
from test_organizations import mfa_user, claim, decide
from test_owner_additions import member_id
from test_invitations import contact, invite, accept


def business_snapshot():
    names=('organizations','org_memberships','org_role_grants','org_invitations',
        'verification_cases','verification_evidence','organization_capabilities',
        'org_verification_submissions','domain_records','audit_events')
    with transaction() as conn:
        return {name:sorted((dict(row) for row in conn.execute(select(table(name))).mappings()),
            key=lambda row:repr(sorted(row.items()))) for name in names}


def operation(kind,client,identities,org):
    """Prepare a normally valid request before installing the authorization barrier."""
    from app.services import organizations, invitations
    from app.api.v1 import governance
    owner=identities('OWNER',org)
    module=organizations
    method,path,body='POST','',{}
    user=owner
    base='/api/v1/organizations/'+org
    if kind.startswith('register'):
        user=mfa_user(identities)
        if kind=='register_join':
            with transaction() as conn:
                conn.execute(table('organizations').update().where(table('organizations').c.id==org).values(tax_id='987654321'))
        file=cv_fixture(user)
        path='/api/v1/organizations'
        body=dict(tax_id='987654321' if kind=='register_join' else '777888999',legal_name='Authority Test',
            public_name='Authority Test',region='Tashkent',file_ids=[file['id']],evidence_note='Proof for organization onboarding')
    elif kind in ('submit','resubmit','patch','patch_noop'):
        file=cv_fixture(owner)
        evidence=dict(file_ids=[file['id']],evidence_note='Proof for organization profile change')
        if kind=='submit':
            with transaction() as conn:
                conn.execute(table('organization_capabilities').update().where(
                    table('organization_capabilities').c.organization_id==org,
                    table('organization_capabilities').c.capability=='JOB_EMPLOYER').values(status='REJECTED'))
            path=base+'/verification';body=dict(kind='JOB_EMPLOYER',**evidence)
        elif kind=='resubmit':
            response=client.patch(base,headers=owner['headers'],json=dict(public_name='Proposed Name',**evidence))
            assert response.status_code==202,response.text
            case=response.json()['case_id'];moderator=identities('MODERATOR')
            assert claim(client,moderator,case).status_code==200
            response=decide(client,moderator,case,'NEEDS_INFO');assert response.status_code==200,response.text
            path=base+'/verification';body=dict(kind='ORG_PROFILE_CHANGE',case_id=case,**evidence)
        else:
            method,path='PATCH',base
            body=dict(public_name='Test Company' if kind=='patch_noop' else 'Changed Name',**evidence)
    elif kind=='membership_revoke':
        staff=identities('HR',org)
        path=base+'/memberships/'+member_id(staff,org)+'/revoke'
        body={'reason':'Revoke this staff membership after authorization'}
    elif kind.startswith('join_'):
        applicant=mfa_user(identities);file=cv_fixture(applicant)
        with transaction() as conn:
            conn.execute(table('organizations').update().where(table('organizations').c.id==org).values(tax_id='987654321'))
        response=client.post('/api/v1/organizations',headers=applicant['headers'],json=dict(
            tax_id='987654321',legal_name='Ignored Replacement',public_name='Ignored Replacement',region='Tashkent',
            file_ids=[file['id']],evidence_note='Private organization join evidence'))
        assert response.status_code==202,response.text
        method,path,body='GET',base+'/membership-requests/'+response.json()['membership_id'],None
        if kind=='join_download':path+='/files/'+file['id']+'/download'
    elif kind.startswith('invitation_'):
        module=invitations
        if kind=='invitation_create':
            path=base+'/invitations';body={'channel':'PHONE','destination':'+998901234567','role_code':'HR'}
        else:
            target=mfa_user(identities);contact(target)
            response=invite(client,owner,org);assert response.status_code==201,response.text
            invitation=response.json()
            if kind in ('invitation_accept','invitation_replay'):
                user=target
                if kind=='invitation_replay':
                    response=accept(client,target,invitation['token']);assert response.status_code==200,response.text
                path='/api/v1/invitations/'+invitation['token']+'/accept'
            else:
                path=base+'/invitations/'+invitation['id']+'/revoke'
                body={'reason':'Withdraw this invitation after authorization'}
    elif kind.startswith('member_'):
        module=governance
        target=identities()
        path=base+'/members';body={'user_id':target['user_id'],'role_code':'HR'}
        if kind=='member_approve':
            creator=identities('OWNER',org)
            response=client.post(path,headers=creator['headers'],json=body)
            assert response.status_code==201,response.text
            path+='/'+response.json()['id']+'/approve';body={}
    else:raise AssertionError(kind)
    def request():
        return client.request(method,path,headers=user['headers'],**({'json':body} if body is not None else {}))
    return module,user,request


KINDS=('register_bootstrap','register_join','submit','resubmit','patch','patch_noop',
    'membership_revoke','join_detail','join_download','invitation_create','invitation_accept',
    'invitation_replay','invitation_revoke','member_create','member_approve')


@pytest.mark.parametrize('kind',KINDS)
def test_completed_session_revocation_blocks_inflight_request(client,identities,organization,monkeypatch,kind):
    module,user,request=operation(kind,client,identities,organization)
    signed=[]
    if kind=='join_download':
        from app.adapters import storage
        def presign(key,*,reference):
            signed.append(key)
            return 'https://storage.invalid/synthetic-authority-probe'
        monkeypatch.setattr(storage,'presign_get',presign)
    checked,release=Event(),Event();original=module.require_mfa
    def pause(actor):
        original(actor)
        if actor.user_id==user['user_id']:
            checked.set();assert release.wait(30),'Authorization barrier timed out'
    monkeypatch.setattr(module,'require_mfa',pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(request)
        try:
            assert checked.wait(30),'Request did not reach MFA preflight'
            revoked=client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers'])
            assert revoked.status_code==200,revoked.text
            before=business_snapshot()
        finally:release.set()
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),(kind,response.status_code)
    assert business_snapshot()==before,'Rejected request left partial business/audit changes'
    assert not signed,'Rejected request reached private URL signing'


@pytest.mark.parametrize('kind',[kind for kind in KINDS if kind!='register_bootstrap'])
@pytest.mark.parametrize('change',['revoke_session','disable_mfa'])
def test_security_change_while_waiting_for_organization_lock(client,identities,organization,monkeypatch,kind,change):
    module,user,request=operation(kind,client,identities,organization)
    if kind=='join_download':
        from app.adapters import storage
        def forbidden_sign(key,*,reference):raise AssertionError('Stale request reached private URL signing')
        monkeypatch.setattr(storage,'presign_get',forbidden_sign)
    checked=Event();original=module.require_mfa
    def observed(actor):
        original(actor)
        if actor.user_id==user['user_id']:checked.set()
    monkeypatch.setattr(module,'require_mfa',observed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        # The real database lock, not an authority stub, delays the business UOW.
        with get_engine().begin() as conn:
            orgs=table('organizations')
            conn.execute(select(orgs.c.id).where(orgs.c.id==organization).with_for_update())
            pending=pool.submit(request)
            assert checked.wait(30),'Request did not reach MFA preflight'
            assert not pending.done(),'Request bypassed the held organization lock'
            if change=='revoke_session':
                changed=client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers'])
            else:
                changed=client.patch('/api/v1/me/security',headers=user['headers'],json={
                    'enable_totp':False,'current_password':'correct-passphrase-2026'})
            assert changed.status_code==200,changed.text
            before=business_snapshot()
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),(kind,change,response.status_code)
    assert business_snapshot()==before,'Stale locked request left partial business/audit changes'
