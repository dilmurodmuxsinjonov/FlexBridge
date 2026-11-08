"""Named staff consent, independent OWNER proof, SQL history and real transaction races."""
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db.storage import table,transaction,now
from test_candidate import cv_fixture
from test_invitations import contact
from test_organizations import claim,decide

NOTE='Evidence authorizing this additional organization representative'


def member_id(user,org):
    with transaction() as conn:
        return conn.execute(select(table('org_memberships').c.id).where(table('org_memberships').c.user_id==user['user_id'],
            table('org_memberships').c.organization_id==org)).scalar_one()


def has_owner(member):
    with transaction() as conn:
        grants,roles=table('org_role_grants'),table('role_catalog')
        return conn.execute(select(grants.c.id).join(roles,roles.c.id==grants.c.role_id).where(
            grants.c.membership_id==member,grants.c.revoked_at.is_(None),roles.c.code=='OWNER',roles.c.scope_kind=='ORG')).first() is not None


@pytest.fixture
def setup_owner(identities,organization):
    owner=identities('OWNER',organization);target=identities('HR',organization);moderator=identities('MODERATOR')
    verified=contact(target,value=str(uuid4())+'@example.test',channel='EMAIL')
    return dict(owner=owner,target=target,moderator=moderator,org=organization,target_member=member_id(target,organization),
        file=cv_fixture(owner),contact=verified)


def submit(client,flow,**changes):
    return client.post('/api/v1/organizations/'+flow['org']+'/owner-requests',headers={
        **flow['owner']['headers'],'Idempotency-Key':'owner-addition-request'},json={
            'target_membership_id':flow['target_member'],'file_ids':[flow['file']['id']],'evidence_note':NOTE,**changes})


def consent(client,flow,case,*,actor=None,revision=1,decision='ACCEPT',contact_id=None,**changes):
    payload={'expected_revision':revision,'decision':decision,**changes}
    if decision=='ACCEPT':payload['contact_id']=contact_id or flow['contact']['id']
    return client.post('/api/v1/owner-requests/'+case+'/consent',headers=(actor or flow['target'])['headers'],json=payload)


def accepted(client,flow):
    response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];response=consent(client,flow,case)
    assert response.status_code==200,response.text
    return case


def test_real_target_consent_and_independent_approval_grant_only_owner(client,setup_owner):
    flow=setup_owner;response=submit(client,flow)
    assert response.status_code==202,response.text
    case=response.json()['id'];assert response.json()['status']=='WAITING_CONSENT'
    assert response.headers['cache-control']=='no-store' and not has_owner(flow['target_member'])
    response=claim(client,flow['moderator'],case);assert response.status_code==409,response.text
    response=consent(client,flow,case,actor=flow['owner']);assert response.status_code==403,response.text
    response=consent(client,flow,case);assert response.status_code==200,response.text
    assert response.json()['status']=='PENDING' and not has_owner(flow['target_member'])
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    detail=client.get('/api/v1/operator/verification-cases/'+case,headers=flow['moderator']['headers'])
    assert detail.status_code==200,detail.text
    assert detail.json()['owner_request']['target_user_id']==flow['target']['user_id']
    assert flow['contact']['normalized_value'] not in detail.text
    response=decide(client,flow['moderator'],case);assert response.status_code==200,response.text
    assert response.json()['status']=='APPROVED' and has_owner(flow['target_member'])
    event=response.json()['ownership_event_id'];assert event
    repeat=decide(client,flow['moderator'],case);assert repeat.status_code==200,repeat.text
    assert repeat.json()['idempotent_replay'] and repeat.json()['ownership_event_id']==event
    response=client.get('/api/v1/organizations/'+flow['org']+'/memberships',headers=flow['target']['headers'])
    assert response.status_code==200,response.text
    with transaction() as conn:
        grants,roles=table('org_role_grants'),table('role_catalog')
        codes=conn.execute(select(roles.c.code).join(grants,grants.c.role_id==roles.c.id).where(
            grants.c.membership_id==flow['target_member'],grants.c.revoked_at.is_(None))).scalars().all()
        assert set(codes)=={'HR','OWNER'}
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==1


def test_new_evidence_revision_requires_fresh_named_target_consent(client,setup_owner):
    flow=setup_owner;case=accepted(client,flow)
    response=claim(client,flow['moderator'],case);assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],case,'NEEDS_INFO');assert response.status_code==200,response.text
    revised_file=cv_fixture(flow['owner'])
    response=client.post('/api/v1/owner-requests/'+case+'/resubmit',headers=flow['owner']['headers'],json={
        'expected_revision':1,'file_ids':[revised_file['id']],'evidence_note':'Additional evidence for the same named target'})
    assert response.status_code==200,response.text
    assert response.json()['revision']==2 and response.json()['status']=='WAITING_CONSENT'
    response=decide(client,flow['moderator'],case,revision=2);assert response.status_code==409,response.text
    response=consent(client,flow,case,revision=1);assert response.status_code==409,response.text
    response=consent(client,flow,case,revision=2);assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],case,revision=2);assert response.status_code==200,response.text
    assert has_owner(flow['target_member'])
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('owner_addition_consents'))).scalar_one()==2
        assert conn.execute(select(func.count()).select_from(table('org_verification_submissions'))).scalar_one()==2
