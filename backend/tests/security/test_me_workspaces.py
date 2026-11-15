"""GET /api/v1/me/workspaces lists only effective org/institution grants of the caller."""
from uuid import uuid4

from app.db.storage import table, transaction, now
from test_institution_authority import setup_scope


def test_requires_authentication(client):
    assert client.get('/api/v1/me/workspaces').status_code == 401


def test_candidate_has_no_workspaces(client, identities):
    user = identities()
    response = client.get('/api/v1/me/workspaces', headers=user['headers'])
    assert response.status_code == 200, response.text
    assert response.json()['organizations'] == []
    assert response.json()['institutions'] == []


def test_lists_own_organization_with_roles_only(client, identities, organization):
    owner = identities('OWNER', organization)
    outsider = identities('HR', organization)
    with transaction() as conn:
        conn.execute(table('organizations').insert().values(
            id=str(uuid4()), created_at=now(), updated_at=now(), tax_id=uuid4().hex[:12],
            legal_name='Foreign LLC', public_name='Foreign', region='Samarqand', status='VERIFIED'))

    body = client.get('/api/v1/me/workspaces', headers=owner['headers']).json()
    assert [(o['id'], o['name'], o['roles']) for o in body['organizations']] == [(organization, 'Test Company', ['OWNER'])]
    assert body['institutions'] == []

    other = client.get('/api/v1/me/workspaces', headers=outsider['headers']).json()
    assert [o['roles'] for o in other['organizations']] == [['HR']]


def test_revoked_membership_is_not_listed(client, identities, organization):
    owner = identities('OWNER', organization)
    with transaction() as conn:
        members = table('org_memberships')
        conn.execute(members.update().where(members.c.user_id == owner['user_id']).values(revoked_at=now()))
    body = client.get('/api/v1/me/workspaces', headers=owner['headers']).json()
    assert body['organizations'] == []


def test_lists_current_institution_appointment(client, identities):
    user, _, inst, foreign, _, _, _ = setup_scope(identities, 'TEACHER')
    body = client.get('/api/v1/me/workspaces', headers=user['headers']).json()
    assert [(i['id'], i['roles']) for i in body['institutions']] == [(inst['id'], ['TEACHER'])]
    assert foreign['id'] not in {i['id'] for i in body['institutions']}


def test_revoked_appointment_is_not_listed(client, identities):
    user, _, inst, _, _, appointment, _ = setup_scope(identities)
    with transaction() as conn:
        appointments = table('institution_appointments')
        conn.execute(appointments.update().where(appointments.c.id == appointment['id']).values(status='REVOKED'))
    body = client.get('/api/v1/me/workspaces', headers=user['headers']).json()
    assert body['institutions'] == []


def _draft(owner, organization, title):
    from app.services.opportunities import opportunity_service
    return opportunity_service.create_opportunity_revision(
        organization_id=organization, title=title, opportunity_kind='PART_TIME_JOB',
        contract_type='LABOR_PART_TIME', compensation_type='HOURLY', stipend_amount=None,
        hourly_pay=20000, actor_user_id=owner['user_id'])


def test_managers_see_all_statuses_of_own_organization(client, identities, organization):
    from test_candidate import published_fixture
    owner = identities('OWNER', organization)
    hr = identities('HR', organization)
    draft = _draft(owner, organization, 'Qoralama e’lon')
    published = published_fixture(owner, organization)

    for actor in (owner, hr):
        response = client.get(f'/api/v1/organizations/{organization}/opportunities/manage', headers=actor['headers'])
        assert response.status_code == 200, response.text
        items = {item['id']: item for item in response.json()['items']}
        assert items[draft['opportunity_id']]['status'] == 'DRAFT'
        assert items[draft['opportunity_id']]['title'] == 'Qoralama e’lon'
        assert items[published['opportunity_id']]['status'] == 'PUBLISHED'
        assert items[published['opportunity_id']]['applications_count'] == 0

    only_drafts = client.get(f'/api/v1/organizations/{organization}/opportunities/manage?status=draft',
                             headers=owner['headers']).json()['items']
    assert [item['id'] for item in only_drafts] == [draft['opportunity_id']]


def test_non_managers_cannot_list_organization_opportunities(client, identities, organization):
    mentor = identities('MENTOR', organization)
    stranger = identities()
    other_owner = identities('OWNER', organization)
    with transaction() as conn:
        foreign = str(uuid4())
        conn.execute(table('organizations').insert().values(
            id=foreign, created_at=now(), updated_at=now(), tax_id=uuid4().hex[:12],
            legal_name='Foreign LLC', public_name='Foreign', region='Samarqand', status='VERIFIED'))
    path = f'/api/v1/organizations/{organization}/opportunities/manage'
    assert client.get(path, headers=mentor['headers']).status_code == 403
    assert client.get(path, headers=stranger['headers']).status_code == 403
    assert client.get(f'/api/v1/organizations/{foreign}/opportunities/manage', headers=other_owner['headers']).status_code == 403
