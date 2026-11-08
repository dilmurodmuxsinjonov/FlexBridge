"""Two independent procedural reviewers; no identity/legal/live-provider certification."""
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db.storage import table,transaction
from test_owner_additions import member_id,has_owner
from test_candidate import cv_fixture
from test_invitations import contact

NOTE='Authority evidence for existing staff continuity when the current owner cannot submit'
REASON='Independent review of the supplied organization authority evidence'

@pytest.fixture
def setup_continuity(identities,organization):
    owner=identities('OWNER',organization);applicant=identities('HR',organization)
    return dict(owner=owner,applicant=applicant,moderator=identities('MODERATOR'),compliance=identities('COMPLIANCE'),
        org=organization,member=member_id(applicant,organization),owner_member=member_id(owner,organization),
        file=cv_fixture(applicant),contact=contact(applicant,value=str(uuid4())+'@example.test',channel='EMAIL'))

def submit(client,flow,key='continuity-self-request',actor=None,**changes):
    return client.post('/api/v1/organizations/'+flow['org']+'/owner-continuity',headers={
        **(actor or flow['applicant'])['headers'],'Idempotency-Key':key},json={
        'contact_id':flow['contact']['id'],'file_ids':[flow['file']['id']],'evidence_note':NOTE,**changes})

def path(case,stage):return '/api/v1/operator/owner-continuity/'+stage+'/cases/'+case

def claim(client,flow,case,stage,actor=None):
    return client.post(path(case,stage)+'/claim',headers=(actor or flow[stage])['headers'])

def decide(client,flow,case,stage,decision=None,actor=None,reason=REASON,**changes):
    return client.post(path(case,stage)+'/decide',headers=(actor or flow[stage])['headers'],json={
        'decision':decision or ('RECOMMEND' if stage=='moderator' else 'APPROVE'),'expected_revision':1,'reason':reason,**changes})

def recommended(client,flow):
    response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];response=claim(client,flow,case,'moderator');assert response.status_code==200,response.text
    response=decide(client,flow,case,'moderator');assert response.status_code==200,response.text
    assert response.json()['status']=='WAITING_COMPLIANCE'
    return case

def ready(client,flow):
    case=recommended(client,flow);response=claim(client,flow,case,'compliance');assert response.status_code==200,response.text
    return case

def test_two_distinct_reviews_are_required_and_existing_owners_are_preserved(client,setup_continuity):
    flow=setup_continuity;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];assert response.json()['status']=='WAITING_MODERATOR'
    assert response.headers['cache-control']=='no-store' and not has_owner(flow['member'])
    response=claim(client,flow,case,'compliance');assert response.status_code==409,response.text
    response=claim(client,flow,case,'moderator');assert response.status_code==200,response.text
    response=decide(client,flow,case,'moderator','APPROVE');assert response.status_code==422,response.text
    response=decide(client,flow,case,'moderator');assert response.status_code==200,response.text
    assert response.json()['status']=='WAITING_COMPLIANCE' and not has_owner(flow['member'])
    response=claim(client,flow,case,'compliance');assert response.status_code==200,response.text
    response=decide(client,flow,case,'compliance');assert response.status_code==200,response.text
    assert response.json()['status']=='APPROVED' and response.json()['ownership_event_id']
    assert has_owner(flow['member']) and has_owner(flow['owner_member'])
    event=response.json()['ownership_event_id']
    with transaction() as conn:
        history=conn.execute(select(table('org_ownership_events')).where(table('org_ownership_events').c.id==event)).mappings().one()
        assert history['previous_membership_id'] is None and history['approved_by_id']==flow['compliance']['user_id']
        recovery=conn.execute(select(table('recovery_requests'))).mappings().one()
        assert recovery['kind']=='ORG_OWNER_CONTINUITY' and recovery['status']=='COMPLETED' and recovery['reviewer_id'] is None
        grants,roles=table('org_role_grants'),table('role_catalog')
        codes=conn.execute(select(roles.c.code).join(grants,grants.c.role_id==roles.c.id).where(grants.c.membership_id==flow['member'],grants.c.revoked_at.is_(None))).scalars().all()
        assert set(codes)=={'HR','OWNER'}
    repeat=decide(client,flow,case,'compliance');assert repeat.status_code==200 and repeat.json()['idempotent_replay'] and repeat.json()['ownership_event_id']==event,repeat.text

def test_current_owner_objection_is_terminal_without_grant(client,setup_continuity):
    flow=setup_continuity;case=ready(client,flow)
    response=client.get('/api/v1/organizations/'+flow['org']+'/owner-continuity',headers=flow['owner']['headers'])
    assert response.status_code==200 and response.json()['items'][0]['id']==case,response.text
    assert 'evidence_note' not in response.text and flow['contact']['normalized_value'] not in response.text
    response=client.post('/api/v1/organizations/'+flow['org']+'/owner-continuity/'+case+'/object',headers=flow['owner']['headers'],
        json={'reason':'Current owner objects to this continuity authority claim'})
    assert response.status_code==200 and response.json()['status']=='CANCELLED',response.text
    response=decide(client,flow,case,'compliance');assert response.status_code==409,response.text
    assert not has_owner(flow['member']) and has_owner(flow['owner_member'])

def test_needs_info_requires_new_request_and_generic_resubmission_is_rejected(client,setup_continuity):
    flow=setup_continuity;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id'];response=claim(client,flow,case,'moderator');assert response.status_code==200,response.text
    response=decide(client,flow,case,'moderator','NEEDS_INFO');assert response.status_code==200,response.text
    response=client.post('/api/v1/organizations/'+flow['org']+'/verification',headers=flow['applicant']['headers'],json={
        'kind':'JOB_EMPLOYER','case_id':case,'file_ids':[flow['file']['id']],'evidence_note':NOTE})
    assert response.status_code==422,response.text
    response=submit(client,flow,key='new-proposal-with-new-evidence');assert response.status_code==202,response.text
    assert response.json()['id']!=case and response.json()['status']=='WAITING_MODERATOR'
    assert not has_owner(flow['member'])
