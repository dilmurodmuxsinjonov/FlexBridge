"""Issue #253: user-to-user chat with groups.

Reachability is relationship-based (colleagues, employer<->applicant,
university<->verified student, existing chat partner) or by a contact code the
other person shares. Conversations exist only for their members; blocks cut
direct messages both ways; deleted text is erased.
"""
from sqlalchemy import select

from app.db.storage import table, transaction

API = '/api/v1/chat'


def contacts(client, user, q=None):
    r = client.get(API + '/contacts', headers=user['headers'], params={'q': q} if q else None)
    assert r.status_code == 200, r.text
    return {c['user_id']: c for c in r.json()['items']}


def direct(client, user, **body):
    return client.post(API + '/direct', headers=user['headers'], json=body)


def send(client, user, cid, body):
    return client.post(f'{API}/conversations/{cid}/messages', headers=user['headers'], json={'body': body})


def conversations(client, user):
    r = client.get(API + '/conversations', headers=user['headers'])
    assert r.status_code == 200, r.text
    return r.json()


def test_colleagues_reach_each_other_strangers_need_a_code(client, identities, organization):
    a, b, stranger = identities('HR', organization), identities('HR', organization), identities()
    assert b['user_id'] in contacts(client, a)
    assert contacts(client, a)[b['user_id']]['relation'] == 'COLLEAGUE'
    assert stranger['user_id'] not in contacts(client, a)

    first = direct(client, a, user_id=b['user_id'])
    assert first.status_code == 200, first.text
    again = direct(client, b, user_id=a['user_id'])
    assert again.json()['id'] == first.json()['id']  # one direct conversation per pair

    assert direct(client, a, user_id=stranger['user_id']).status_code == 403
    code = client.get(API + '/me', headers=stranger['headers']).json()['contact_code']
    assert len(code) == 8
    via_code = direct(client, a, contact_code=code)
    assert via_code.status_code == 200, via_code.text
    assert via_code.json()['title'] == 'Test User' and via_code.json()['kind'] == 'DIRECT'
    # A chat partner is now a contact; the rotated code no longer works.
    assert stranger['user_id'] in contacts(client, a)
    rotated = client.post(API + '/me/contact-code/rotate', headers=stranger['headers']).json()['contact_code']
    assert rotated != code
    assert direct(client, identities(), contact_code=code).status_code == 404
    assert direct(client, a, contact_code=client.get(API + '/me', headers=a['headers']).json()['contact_code']).status_code == 422


def test_messages_unread_and_member_only_visibility(client, identities, organization):
    a, b, outsider = identities('HR', organization), identities('HR', organization), identities()
    cid = direct(client, a, user_id=b['user_id']).json()['id']
    assert send(client, a, cid, 'Salom!').status_code == 201
    assert send(client, a, cid, '  Ertaga uchrashamizmi?  ').json()['body'] == 'Ertaga uchrashamizmi?'

    listed = conversations(client, b)
    assert listed['unread_total'] == 2
    item = next(c for c in listed['items'] if c['id'] == cid)
    assert item['last_message']['body'] == 'Ertaga uchrashamizmi?' and not item['last_message']['mine']
    msgs = client.get(f'{API}/conversations/{cid}/messages', headers=b['headers']).json()
    assert [m['body'] for m in msgs['items']] == ['Salom!', 'Ertaga uchrashamizmi?']
    assert client.post(f'{API}/conversations/{cid}/read', headers=b['headers']).status_code == 200
    assert conversations(client, b)['unread_total'] == 0

    # Pagination is stable and older-first within a page.
    older = client.get(f'{API}/conversations/{cid}/messages', headers=b['headers'],
                       params={'before': msgs['items'][1]['id']}).json()
    assert [m['body'] for m in older['items']] == ['Salom!']

    for path in (f'{API}/conversations/{cid}', f'{API}/conversations/{cid}/messages'):
        assert client.get(path, headers=outsider['headers']).status_code == 404
    assert send(client, outsider, cid, 'hi').status_code == 404
    assert send(client, a, cid, '').status_code == 422
    assert send(client, a, cid, 'x' * 4001).status_code == 422


def test_groups_owner_rules_invite_link_and_succession(client, identities, organization):
    owner, colleague, other_colleague = (identities('HR', organization) for _ in range(3))
    stranger = identities()
    assert client.post(API + '/groups', headers=owner['headers'],
                       json={'title': 'Bo‘lim', 'member_ids': [stranger['user_id']]}).status_code == 403
    created = client.post(API + '/groups', headers=owner['headers'],
                          json={'title': 'Amaliyot jamoasi', 'member_ids': [colleague['user_id']]})
    assert created.status_code == 201, created.text
    g = created.json()
    assert g['kind'] == 'GROUP' and g['member_count'] == 2 and g['my_role'] == 'OWNER'
    gid = g['id']

    # Only the owner manages the group.
    assert client.patch(f'{API}/groups/{gid}', headers=colleague['headers'], json={'title': 'X'}).status_code == 403
    assert client.post(f'{API}/groups/{gid}/members', headers=colleague['headers'],
                       json={'member_ids': [other_colleague['user_id']]}).status_code == 403
    assert client.post(f'{API}/groups/{gid}/invite-link', headers=colleague['headers']).status_code == 403
    assert client.patch(f'{API}/groups/{gid}', headers=owner['headers'], json={'title': 'Yangi nom'}).json()['title'] == 'Yangi nom'

    token = client.post(f'{API}/groups/{gid}/invite-link', headers=owner['headers']).json()['invite_token']
    with transaction() as conn:  # only a digest is stored
        stored = conn.execute(select(table('chat_conversations').c.invite_token_hash)
                              .where(table('chat_conversations').c.id == gid)).scalar_one()
    assert stored and stored != token
    joined = client.post(API + '/join', headers=stranger['headers'], json={'token': token})
    assert joined.status_code == 200, joined.text
    assert joined.json()['member_count'] == 3
    assert client.delete(f'{API}/groups/{gid}/invite-link', headers=owner['headers']).status_code == 200
    assert client.post(API + '/join', headers=other_colleague['headers'], json={'token': token}).status_code == 404

    # A member leaves; the owner leaves and the longest-standing member takes over.
    assert client.delete(f'{API}/groups/{gid}/members/{stranger["user_id"]}', headers=stranger['headers']).json()['left']
    assert client.get(f'{API}/conversations/{gid}', headers=stranger['headers']).status_code == 404
    assert client.delete(f'{API}/groups/{gid}/members/{owner["user_id"]}', headers=owner['headers']).status_code == 200
    after = client.get(f'{API}/conversations/{gid}', headers=colleague['headers']).json()
    assert after['my_role'] == 'OWNER' and after['member_count'] == 1


def test_block_cuts_direct_messages_both_ways(client, identities, organization):
    a, b = identities('HR', organization), identities('HR', organization)
    cid = direct(client, a, user_id=b['user_id']).json()['id']
    assert client.post(f'{API}/blocks/{a["user_id"]}', headers=b['headers']).status_code == 200
    assert send(client, a, cid, 'Salom').status_code == 403
    assert send(client, b, cid, 'Salom').status_code == 403
    assert a['user_id'] not in contacts(client, b) and b['user_id'] not in contacts(client, a)
    assert direct(client, a, user_id=b['user_id']).status_code == 403
    assert client.get(f'{API}/conversations/{cid}', headers=b['headers']).json()['blocked'] is True
    assert client.delete(f'{API}/blocks/{a["user_id"]}', headers=b['headers']).status_code == 200
    assert send(client, a, cid, 'Salom').status_code == 201


def test_only_the_sender_deletes_and_the_text_is_erased(client, identities, organization):
    a, b = identities('HR', organization), identities('HR', organization)
    cid = direct(client, a, user_id=b['user_id']).json()['id']
    mid = send(client, a, cid, 'Maxfiy matn').json()['id']
    assert client.delete(f'{API}/messages/{mid}', headers=b['headers']).status_code == 403
    assert client.delete(f'{API}/messages/{mid}', headers=a['headers']).status_code == 200
    item = client.get(f'{API}/conversations/{cid}/messages', headers=b['headers']).json()['items'][0]
    assert item['deleted'] and item['body'] is None
    with transaction() as conn:
        assert conn.execute(select(table('chat_messages').c.body).where(table('chat_messages').c.id == mid)).scalar_one() == '·'


def test_chat_requires_a_session(client):
    assert client.get(API + '/conversations').status_code == 401
    assert client.get(API + '/contacts').status_code == 401
