"""Revoking and regranting authority must not revive a prior delegated proposal/consent."""
from uuid import uuid4
from test_owner_additions import setup_owner,ready,member_id,has_owner,consent,NOTE
from test_candidate import cv_fixture
from test_invitations import contact,invite,accept
from test_organizations import claim,decide


def revoke(client,owner,org,member):
    response=client.post('/api/v1/organizations/'+org+'/memberships/'+member+'/revoke',headers=owner['headers'],
        json={'reason':'End the previous scoped authorization'})
    assert response.status_code==200,response.text


def rejoin_staff(client,owner,user,org,verified):
    response=invite(client,owner,org,destination=verified['normalized_value'],role='HR',channel=verified['channel'])
    assert response.status_code==201,response.text
    response=accept(client,user,response.json()['token'])
    assert response.status_code==200,response.text


def test_old_requester_grant_cannot_authorize_after_owner_is_regranted(client,setup_owner,identities):
    flow=setup_owner;owner=flow['owner'];org=flow['org']
    verified=contact(owner,value=str(uuid4())+'@example.test',channel='EMAIL')
    old_case=ready(client,flow);other_owner=identities('OWNER',org)
    original_member=member_id(owner,org)
    revoke(client,other_owner,org,original_member)
    rejoin_staff(client,other_owner,owner,org,verified)
    restored={**flow,'owner':other_owner,'target':owner,'target_member':original_member,
        'contact':verified,'file':cv_fixture(other_owner)}
    restoring_case=ready(client,restored)
    response=decide(client,flow['moderator'],restoring_case)
    assert response.status_code==200,response.text
    assert has_owner(original_member)
    response=decide(client,flow['moderator'],old_case)
    assert response.status_code==409,response.text
    assert not has_owner(flow['target_member'])
    # A current owner can cancel stale intent and create a new, explicitly authorized proposal.
    response=client.post('/api/v1/owner-requests/'+old_case+'/cancel',headers=owner['headers'],
        json={'reason':'Cancel the proposal from the revoked grant'})
    assert response.status_code==200,response.text
    response=client.post('/api/v1/organizations/'+org+'/owner-requests',headers={**owner['headers'],
        'Idempotency-Key':'fresh-proposal-after-owner-regrant'},json={'target_membership_id':flow['target_member'],
        'file_ids':[flow['file']['id']],'evidence_note':NOTE})
    assert response.status_code==202,response.text
    fresh_case=response.json()['id'];response=consent(client,flow,fresh_case)
    assert response.status_code==200,response.text
    response=claim(client,flow['moderator'],fresh_case);assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],fresh_case);assert response.status_code==200,response.text


def test_staff_regrant_requires_fresh_consent_to_the_pending_proposal(client,setup_owner):
    flow=setup_owner;case=ready(client,flow)
    revoke(client,flow['owner'],flow['org'],flow['target_member'])
    rejoin_staff(client,flow['owner'],flow['target'],flow['org'],flow['contact'])
    response=decide(client,flow['moderator'],case)
    assert response.status_code==409,response.text
    assert not has_owner(flow['target_member'])
    response=consent(client,flow,case);assert response.status_code==200,response.text
    assert not response.json()['idempotent_replay']
    response=decide(client,flow['moderator'],case);assert response.status_code==200,response.text
    assert has_owner(flow['target_member'])
