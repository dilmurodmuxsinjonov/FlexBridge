"""Universal account self-service tests across roles: display name, password rotation, primary login switch, and contact removal."""
from uuid import uuid4
import secrets
import pytest
from sqlalchemy import select
from app.db.storage import table, transaction, now
from app.services.auth import auth_service, generate_totp_code
from app.workers.outbox import relay_pending_outbox_events

PASSWORD = 'correct-passphrase-2026'
NEW_PASSWORD = 'updated-strong-passphrase-2026'


@pytest.fixture
def delivery(monkeypatch):
    from app.adapters import identity_delivery
    messages = {}
    monkeypatch.setenv('AUTH_DELIVERY_URL', 'https://gateway.test.invalid')
    monkeypatch.setenv('AUTH_DELIVERY_TOKEN', secrets.token_urlsafe(32))
    monkeypatch.setattr(identity_delivery, 'send', lambda **kwargs: messages.__setitem__(kwargs['challenge_id'], kwargs))
    return messages


def _age_challenges():
    from datetime import timedelta
    with transaction() as conn:
        conn.execute(table('auth_challenges').update().values(created_at=now() - timedelta(seconds=61)))


def _proof(client, delivery, *, destination, channel='PHONE', purpose='REGISTER', headers=None):
    resp = client.post(
        '/api/v1/auth/challenges',
        json={'purpose': purpose, 'destination': destination, 'channel': channel},
        headers=headers or {},
    )
    assert resp.status_code == 202, resp.text
    cid = resp.json()['challenge_id']
    assert relay_pending_outbox_events() >= 1
    consume = client.post(f'/api/v1/auth/challenges/{cid}/consume', json={'purpose': purpose, 'code': delivery[cid]['code']})
    assert consume.status_code == 200, consume.text
    return consume.json()['verification_token']


def _signup_with_contact(client, delivery, *, phone='+998901112233', name='Sardor Alimov'):
    token = _proof(client, delivery, destination=phone, channel='PHONE', purpose='REGISTER')
    resp = client.post(
        '/api/v1/auth/register',
        json={
            'display_name': name,
            'password': PASSWORD,
            'adult_confirmed': True,
            'verification_token': token,
            'terms_version': 'test-terms-v1',
            'privacy_version': 'test-privacy-v1',
        },
    )
    assert resp.status_code == 201, resp.text
    uid = resp.json()['id']
    login = client.post('/api/v1/auth/login', json={'user_id': uid, 'password': PASSWORD})
    assert login.status_code == 200, login.text
    return {'user_id': uid, **login.json(), 'headers': {'Authorization': 'Bearer ' + login.json()['access_token']}}


@pytest.mark.parametrize('role_kind', ['CANDIDATE', 'EMPLOYER', 'ACADEMIC', 'OPERATOR'])
def test_all_roles_can_update_profile_change_password_and_manage_contacts(client, delivery, identities, organization, role_kind):
    if role_kind == 'CANDIDATE':
        actor = identities()
    elif role_kind == 'EMPLOYER':
        actor = identities('EMPLOYER', organization)
    elif role_kind == 'ACADEMIC':
        actor = identities('ACADEMIC')
    else:
        actor = identities('OPERATOR')

    # 1. Update display_name (non-candidate and candidate roles alike)
    new_name = f'{role_kind}   Updated   Name'
    prof = client.patch('/api/v1/me/profile', headers=actor['headers'], json={'display_name': new_name})
    assert prof.status_code == 200, prof.text
    assert prof.json()['display_name'] == f'{role_kind} Updated Name'
    me = client.get('/api/v1/auth/me', headers=actor['headers'])
    assert me.status_code == 200, me.text
    assert me.json()['display_name'] == f'{role_kind} Updated Name'

    # 2. Bind two contacts -> first becomes primary, second stays secondary (is_primary=False)
    phone = f'+99890{secrets.randbelow(8999999) + 1000000}'
    email = f'{role_kind.lower()}.{secrets.token_hex(4)}@example.com'
    step_totp = {'totp_code': generate_totp_code(actor['totp_secret'])} if actor.get('totp_secret') else {}

    t_phone = _proof(client, delivery, destination=phone, channel='PHONE', purpose='CONTACT', headers=actor['headers'])
    b1 = client.post('/api/v1/me/contacts', headers=actor['headers'], json={'verification_token': t_phone, 'current_password': PASSWORD, **step_totp})
    assert b1.status_code == 201, b1.text

    _age_challenges()
    t_email = _proof(client, delivery, destination=email, channel='EMAIL', purpose='CONTACT', headers=actor['headers'])
    b2 = client.post('/api/v1/me/contacts', headers=actor['headers'], json={'verification_token': t_email, 'current_password': PASSWORD, **step_totp})
    assert b2.status_code == 201, b2.text

    contacts = client.get('/api/v1/me/contacts', headers=actor['headers']).json()['items']
    assert len(contacts) == 2
    by_id = {c['id']: c for c in contacts}
    assert by_id[b1.json()['contact_id']]['is_primary'] is True
    assert by_id[b2.json()['contact_id']]['is_primary'] is False

    # 3. Switch primary login contact to email
    switched = client.patch(
        f"/api/v1/me/contacts/{b2.json()['contact_id']}/primary",
        headers=actor['headers'],
        json={'current_password': PASSWORD, **step_totp},
    )
    assert switched.status_code == 200, switched.text
    assert switched.json()['is_primary'] is True

    contacts_after = client.get('/api/v1/me/contacts', headers=actor['headers']).json()['items']
    assert {c['id']: c['is_primary'] for c in contacts_after} == {
        b1.json()['contact_id']: False,
        b2.json()['contact_id']: True,
    }

    # 4. Change password with second active session -> current session survives, other session is revoked
    other_totp = {'totp_code': generate_totp_code(actor['totp_secret'])} if actor.get('totp_secret') else {}
    second_login = client.post('/api/v1/auth/login', json={'user_id': actor['user_id'], 'password': PASSWORD, **other_totp})
    assert second_login.status_code == 200, second_login.text
    second_headers = {'Authorization': 'Bearer ' + second_login.json()['access_token']}

    changed = client.post(
        '/api/v1/me/security/password',
        headers=actor['headers'],
        json={'current_password': PASSWORD, 'new_password': NEW_PASSWORD, **step_totp},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()['password_updated'] is True
    assert changed.json()['revoked_other_sessions'] >= 1
    assert changed.json()['reauthentication_required'] is False

    assert client.get('/api/v1/auth/me', headers=actor['headers']).status_code == 200
    assert client.get('/api/v1/auth/me', headers=second_headers).status_code == 401

    assert client.post('/api/v1/auth/login', json={'channel': 'EMAIL', 'destination': email, 'password': PASSWORD}).status_code == 401
    fresh_login = client.post(
        '/api/v1/auth/login',
        json={'channel': 'EMAIL', 'destination': email, 'password': NEW_PASSWORD, **other_totp},
    )
    assert fresh_login.status_code == 200, fresh_login.text


def test_profile_and_password_validation_and_step_up_enforced(client, identities):
    actor = identities()

    # Blank spaces only rejected
    bad_name = client.patch('/api/v1/me/profile', headers=actor['headers'], json={'display_name': '     '})
    assert bad_name.status_code == 422
    assert bad_name.json()['detail']['code'] == 'INVALID_DISPLAY_NAME'

    # Wrong current password rejected
    wrong_pw = client.post(
        '/api/v1/me/security/password',
        headers=actor['headers'],
        json={'current_password': 'wrong-passphrase-2026', 'new_password': NEW_PASSWORD},
    )
    assert wrong_pw.status_code == 401

    # Same new password rejected
    same_pw = client.post(
        '/api/v1/me/security/password',
        headers=actor['headers'],
        json={'current_password': PASSWORD, 'new_password': PASSWORD},
    )
    assert same_pw.status_code == 422
    assert same_pw.json()['detail']['code'] == 'PASSWORD_UNCHANGED'

    # Short password rejected by Pydantic
    short_pw = client.post(
        '/api/v1/me/security/password',
        headers=actor['headers'],
        json={'current_password': PASSWORD, 'new_password': 'short'},
    )
    assert short_pw.status_code == 422

    # MFA-enrolled user without fresh MFA session requires totp_code
    secret = auth_service.enroll_totp(actor['user_id'], PASSWORD)
    auth_service.confirm_totp(actor['user_id'], generate_totp_code(secret))
    old_session = client.post('/api/v1/auth/login', json={'user_id': actor['user_id'], 'password': PASSWORD, 'totp_code': generate_totp_code(secret)})
    assert old_session.status_code == 200
    headers = {'Authorization': 'Bearer ' + old_session.json()['access_token']}
    with transaction() as conn:
        from datetime import timedelta
        conn.execute(table('sessions').update().where(table('sessions').c.user_id == actor['user_id']).values(created_at=now() - timedelta(minutes=10)))

    no_mfa = client.post(
        '/api/v1/me/security/password',
        headers=headers,
        json={'current_password': PASSWORD, 'new_password': NEW_PASSWORD},
    )
    assert no_mfa.status_code == 401
    assert no_mfa.json()['detail']['code'] == 'STEP_UP_VERIFICATION_FAILED'

    ok_mfa = client.post(
        '/api/v1/me/security/password',
        headers=headers,
        json={'current_password': PASSWORD, 'new_password': NEW_PASSWORD, 'totp_code': generate_totp_code(secret)},
    )
    assert ok_mfa.status_code == 200, ok_mfa.text


def test_contact_removal_promotes_remaining_blocks_last_and_blocks_cross_user_idor(client, delivery):
    owner = _signup_with_contact(client, delivery, phone='+998901234567', name='Owner One')
    _age_challenges()
    email_token = _proof(client, delivery, destination='owner1@example.com', channel='EMAIL', purpose='CONTACT', headers=owner['headers'])
    bind_email = client.post('/api/v1/me/contacts', headers=owner['headers'], json={'verification_token': email_token, 'current_password': PASSWORD})
    assert bind_email.status_code == 201

    contacts = client.get('/api/v1/me/contacts', headers=owner['headers']).json()['items']
    primary_phone = next(c for c in contacts if c['channel'] == 'PHONE')
    secondary_email = next(c for c in contacts if c['channel'] == 'EMAIL')
    assert primary_phone['is_primary'] is True and secondary_email['is_primary'] is False

    # Cross-account IDOR blocked
    _age_challenges()
    intruder = _signup_with_contact(client, delivery, phone='+998907778899', name='Other User')
    assert client.request('DELETE', f"/api/v1/me/contacts/{secondary_email['id']}", headers=intruder['headers'], json={'current_password': PASSWORD}).status_code == 404
    assert client.patch(f"/api/v1/me/contacts/{secondary_email['id']}/primary", headers=intruder['headers'], json={'current_password': PASSWORD}).status_code == 404

    # Removing primary auto-promotes remaining contact and tombstones released number
    removed = client.request('DELETE', f"/api/v1/me/contacts/{primary_phone['id']}", headers=owner['headers'], json={'current_password': PASSWORD})
    assert removed.status_code == 200, removed.text
    assert removed.json()['removed'] is True
    assert removed.json()['promoted_primary_contact_id'] == secondary_email['id']

    remaining = client.get('/api/v1/me/contacts', headers=owner['headers']).json()['items']
    assert len(remaining) == 1
    assert remaining[0]['id'] == secondary_email['id']
    assert remaining[0]['is_primary'] is True

    with transaction() as conn:
        row = conn.execute(select(table('user_contacts')).where(table('user_contacts').c.id == primary_phone['id'])).mappings().one()
    assert row['revoked_at'] is not None
    assert row['is_primary'] is False
    assert row['normalized_value'].startswith('released:')

    # Last verified contact cannot be removed (409)
    last_del = client.request(
        'DELETE',
        f"/api/v1/me/contacts/{secondary_email['id']}",
        headers=owner['headers'],
        json={'current_password': PASSWORD},
    )
    assert last_del.status_code == 409
    assert last_del.json()['detail']['code'] == 'LAST_CONTACT_CANNOT_BE_REMOVED'

    # Old released phone can be claimed cleanly by a fresh signup
    _age_challenges()
    new_user = _signup_with_contact(client, delivery, phone='+998901234567', name='New Phone Owner')
    assert new_user['user_id'] != owner['user_id']
