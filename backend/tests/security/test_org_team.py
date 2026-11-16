"""Issue #239: the company's main (OWNER) account sees and manages its people.

GET /organizations/{org}/team lists members with names and active roles,
join requests with the requested role, and open invitations - owner only.
"""
from uuid import uuid4

from test_invitations import accept, contact, invite
from test_organizations import mfa_user, onboard, register


def team(client, user, org):
    return client.get(f'/api/v1/organizations/{org}/team', headers=user['headers'])


def test_founder_becomes_owner_and_sees_named_team(client, identities):
    owner, mod, row = onboard(client, identities)
    org = row['organization_id']
    data = team(client, owner, org)
    assert data.status_code == 200, data.text
    body = data.json()
    assert body['organization']['status'] == 'VERIFIED'
    [me] = body['members']
    assert me['is_self'] and me['roles'] == ['OWNER'] and me['display_name']
    assert body['join_requests'] == [] and body['invitations'] == []

    # Invitation: listed with its role until accepted, then a named HR member.
    staff = mfa_user(identities)
    destination = '+99890' + str(uuid4().int)[:7]
    contact(staff, value=destination)
    created = invite(client, owner, org, destination=destination, role='MENTOR')
    assert created.status_code == 201, created.text
    [pending] = team(client, owner, org).json()['invitations']
    assert pending['role_code'] == 'MENTOR' and pending['channel'] == 'PHONE'
    assert accept(client, staff, created.json()['token']).status_code == 200
    after = team(client, owner, org).json()
    assert after['invitations'] == []
    mentor = next(m for m in after['members'] if not m['is_self'])
    assert mentor['roles'] == ['MENTOR'] and mentor['status'] == 'ACTIVE'


def test_join_request_shows_requested_role_and_owner_approves(client, identities):
    owner, mod, row = onboard(client, identities)
    org = row['organization_id']
    joiner = mfa_user(identities)
    joined = register(client, joiner, membership_role='HOST_COORDINATOR')
    assert joined.status_code == 202, joined.text
    [request] = team(client, owner, org).json()['join_requests']
    assert request['requested_role'] == 'HOST_COORDINATOR' and request['self_join'] is True
    approve = client.post(f"/api/v1/organizations/{org}/members/{request['membership_id']}/approve", headers=owner['headers'], json={})
    assert approve.status_code == 200, approve.text
    body = team(client, owner, org).json()
    assert body['join_requests'] == []
    assert any(m['roles'] == ['HOST_COORDINATOR'] for m in body['members'])


def test_team_is_owner_only(client, identities, organization):
    owner = identities('OWNER', organization)
    hr = identities('HR', organization)
    assert team(client, owner, organization).status_code == 200
    assert team(client, hr, organization).status_code == 403
    assert team(client, identities(), organization).status_code == 403
    assert client.get(f'/api/v1/organizations/{organization}/team').status_code == 401
