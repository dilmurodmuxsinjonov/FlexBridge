"""Issue #259: moderators get a queue of draft vacancies, so the existing
POST /moderation/actions decision is reachable from the operator UI.

Found in the staging browser run: an employer's new vacancy stayed DRAFT forever,
because nothing listed drafts for a moderator."""
from test_adapters_and_quota import draft

Q = '/api/v1/moderation/opportunities'


def decide(client, moderator, opportunity_id, action='APPROVE'):
    return client.post('/api/v1/moderation/actions', headers=moderator['headers'], json=dict(
        target_entity_type='opportunity', target_entity_id=opportunity_id, action_type=action,
        policy_code='CONTENT_POLICY', reason_code='MEETS_POLICY',
        justification='Vacancy text, pay and contract type were reviewed and are acceptable'))


def test_moderator_sees_drafts_and_approval_removes_them(client, identities, organization):
    owner = identities('OWNER', organization)
    moderator = identities('MODERATOR')
    first, second = draft(owner, organization), draft(owner, organization)

    r = client.get(Q, headers=moderator['headers'])
    assert r.status_code == 200, r.text
    items = {i['id']: i for i in r.json()['items']}
    assert first['opportunity_id'] in items and second['opportunity_id'] in items
    item = items[first['opportunity_id']]
    assert item['title'] == 'Quota test' and item['organization_name'] == 'Test Company'
    assert item['own'] is False and 'author_id' not in item
    assert item['salary_min'] == 10000

    assert decide(client, moderator, first['opportunity_id']).status_code == 201
    assert decide(client, moderator, second['opportunity_id'], 'REJECT').status_code == 201
    left = {i['id'] for i in client.get(Q, headers=moderator['headers']).json()['items']}
    assert first['opportunity_id'] not in left and second['opportunity_id'] not in left


def test_queue_is_moderator_only(client, identities, organization):
    owner = identities('OWNER', organization)
    draft(owner, organization)
    assert client.get(Q, headers=owner['headers']).status_code == 403
    assert client.get(Q, headers=identities()['headers']).status_code == 403
    assert client.get(Q).status_code == 401
