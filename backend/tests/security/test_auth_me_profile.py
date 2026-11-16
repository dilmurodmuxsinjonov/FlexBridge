"""/auth/me returns the caller's own display name (profile card) and nothing about others."""


def test_auth_me_returns_own_display_name(client, identities):
    user = identities()
    other = identities()
    me = client.get('/api/v1/auth/me', headers=user['headers'])
    assert me.status_code == 200, me.text
    body = me.json()
    assert body['user_id'] == user['user_id']
    assert body['display_name'] == 'Test User'
    assert set(body) == {'user_id', 'session_id', 'roles', 'display_name'}
    assert other['user_id'] not in me.text


def test_auth_me_still_requires_a_session(client):
    assert client.get('/api/v1/auth/me').status_code == 401
