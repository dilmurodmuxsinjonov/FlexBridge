"""Telegram phone verification: modes, webhook authentication and the polling worker.

Before this change the webhook was unauthenticated and returned the OTP, and the
website itself posted forged "contact" updates, so any phone number could be
"verified". LIVE mode must only accept Telegram (secret_token) and must deliver
the code only to the user's Telegram chat.
"""
import httpx
import pytest

from app.services import telegram_bot

PHONE = '+998901112233'
SECRET = 'webhook-secret-for-tests-0123'


@pytest.fixture
def sent(monkeypatch):
    messages = []
    monkeypatch.setattr(telegram_bot, '_send_telegram_api_message',
                        lambda chat_id, text, reply_markup=None: messages.append((chat_id, text)) or True)
    return messages


def live(monkeypatch, secret=SECRET):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123456:test-token')
    monkeypatch.setenv('TELEGRAM_BOT_USERNAME', 'FlexBridgeTestBot')
    monkeypatch.delenv('TELEGRAM_SIMULATION_MODE', raising=False)
    if secret:
        monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', secret)
    else:
        monkeypatch.delenv('TELEGRAM_WEBHOOK_SECRET', raising=False)


def issue(client):
    response = client.post('/api/v1/auth/challenges', json={
        'channel': 'PHONE', 'destination': PHONE, 'purpose': 'REGISTER', 'delivery_method': 'TELEGRAM'})
    assert response.status_code == 202, response.text
    return response.json()


def update(text=None, contact_phone=None, sender=777001, contact_owner=None):
    message = {'from': {'id': sender, 'first_name': 'T'}, 'chat': {'id': sender, 'type': 'private'}}
    if text:
        message['text'] = text
    if contact_phone:
        message['contact'] = {'phone_number': contact_phone, 'first_name': 'T',
                              'user_id': sender if contact_owner is None else contact_owner}
    return {'update_id': 1, 'message': message}


def test_disabled_by_default(client, monkeypatch):
    for name in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_SIMULATION_MODE', 'TELEGRAM_WEBHOOK_SECRET'):
        monkeypatch.delenv(name, raising=False)
    options = client.get('/api/v1/auth/options').json()
    assert options['telegram_mode'] == 'DISABLED' and options['delivery_methods'] == ['SMS']
    response = client.post('/api/v1/auth/challenges', json={
        'channel': 'PHONE', 'destination': PHONE, 'purpose': 'REGISTER', 'delivery_method': 'TELEGRAM'})
    assert response.status_code == 503 and 'TELEGRAM_UNAVAILABLE' in response.text
    assert client.post('/api/v1/auth/telegram/webhook', json=update('/start')).status_code == 503


def test_token_wins_over_simulation_flag(monkeypatch):
    monkeypatch.setenv('TELEGRAM_SIMULATION_MODE', 'true')
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '1:t')
    assert telegram_bot.telegram_mode() == 'LIVE'


def test_live_webhook_requires_configured_secret(client, monkeypatch, sent):
    live(monkeypatch, secret=None)
    assert client.post('/api/v1/auth/telegram/webhook', json=update('/start')).status_code == 503


def test_live_webhook_rejects_missing_or_wrong_secret(client, monkeypatch, sent):
    live(monkeypatch)
    assert client.post('/api/v1/auth/telegram/webhook', json=update('/start')).status_code == 403
    wrong = {'X-Telegram-Bot-Api-Secret-Token': 'nope'}
    assert client.post('/api/v1/auth/telegram/webhook', json=update('/start'), headers=wrong).status_code == 403
    assert sent == []


def test_live_flow_sends_code_only_to_telegram(client, monkeypatch, sent):
    live(monkeypatch)
    challenge = issue(client)
    assert challenge['telegram_deep_link'] == f"https://t.me/FlexBridgeTestBot?start={challenge['challenge_id']}"
    headers = {'X-Telegram-Bot-Api-Secret-Token': SECRET}

    started = client.post('/api/v1/auth/telegram/webhook',
                          json=update(f"/start {challenge['challenge_id']}"), headers=headers)
    assert started.status_code == 200 and started.json() == {'ok': True, 'step': 'AWAITING_CONTACT'}

    shared = client.post('/api/v1/auth/telegram/webhook', json=update(contact_phone=PHONE), headers=headers)
    assert shared.status_code == 200
    body = shared.json()
    assert body['telegram_verified'] is True
    assert 'otp_code' not in body and 'bot_message' not in body
    codes = [text for _, text in sent if 'tasdiqlash kodingiz' in text]
    assert len(codes) == 1

    status = client.get(f"/api/v1/auth/challenges/{challenge['challenge_id']}/status").json()
    assert status['telegram_verified'] is True


def test_live_forged_contact_is_refused_without_retry_storm(client, monkeypatch, sent):
    live(monkeypatch)
    challenge = issue(client)
    headers = {'X-Telegram-Bot-Api-Secret-Token': SECRET}
    client.post('/api/v1/auth/telegram/webhook', json=update(f"/start {challenge['challenge_id']}"), headers=headers)
    forged = client.post('/api/v1/auth/telegram/webhook',
                         json=update(contact_phone=PHONE, contact_owner=999), headers=headers)
    assert forged.status_code == 200
    assert forged.json() == {'ok': False, 'code': 'TELEGRAM_CONTACT_OWNERSHIP_MISMATCH'}
    status = client.get(f"/api/v1/auth/challenges/{challenge['challenge_id']}/status").json()
    assert status['telegram_verified'] is False


def test_live_ignores_body_supplied_challenge_id(client, monkeypatch, sent):
    live(monkeypatch)
    challenge = issue(client)
    headers = {'X-Telegram-Bot-Api-Secret-Token': SECRET}
    # A contact without a prior /start binding and with a mismatched phone must not
    # reach the website challenge via a body challenge_id.
    payload = {**update(contact_phone='+998909999999'), 'challenge_id': challenge['challenge_id']}
    response = client.post('/api/v1/auth/telegram/webhook', json=payload, headers=headers)
    assert response.status_code == 200 and response.json()['ok'] is False
    status = client.get(f"/api/v1/auth/challenges/{challenge['challenge_id']}/status").json()
    assert status['telegram_verified'] is False


def test_simulation_mode_keeps_scripted_staging_flow(client, monkeypatch, sent):
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
    monkeypatch.setenv('TELEGRAM_SIMULATION_MODE', 'true')
    challenge = issue(client)
    client.post('/api/v1/auth/telegram/webhook', json={**update('/start'), 'challenge_id': challenge['challenge_id']})
    response = client.post('/api/v1/auth/telegram/webhook',
                           json={**update(contact_phone=PHONE), 'challenge_id': challenge['challenge_id']})
    assert response.status_code == 200 and len(response.json()['otp_code']) == 6


def test_poller_processes_updates_and_tolerates_user_errors(monkeypatch):
    from app.services.auth import AuthError
    from app.workers import telegram_bot_poller as poller

    seen = []

    def handler(*, update, ip):
        seen.append(ip)
        if 'contact' in update['message']:
            raise AuthError('TELEGRAM_PHONE_MISMATCH', 'mismatch', 409)
        return {'step': 'AWAITING_CONTACT'}

    assert poller.process_update({'update_id': 5}, handler) == 'IGNORED'
    assert poller.process_update(update('/start'), handler) == 'AWAITING_CONTACT'
    assert poller.process_update(update(contact_phone=PHONE), handler) == 'TELEGRAM_PHONE_MISMATCH'
    assert seen == ['tg:777001', 'tg:777001']


def test_poller_advances_offset(monkeypatch):
    from app.workers import telegram_bot_poller as poller

    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '1:t')
    monkeypatch.setenv('TELEGRAM_API_BASE_URL', 'http://telegram.test')
    offsets = []

    def transport(request: httpx.Request) -> httpx.Response:
        import json
        body = json.loads(request.content or b'{}')
        offsets.append(body.get('offset'))
        result = [{'update_id': 41, 'message': {'from': {'id': 1}, 'chat': {'id': 1}, 'text': '/start'}}] if len(offsets) == 1 else []
        return httpx.Response(200, json={'ok': True, 'result': result})

    handled = []
    monkeypatch.setattr(poller, 'process_update', lambda upd, handler=None: handled.append(upd['update_id']) or 'OK')
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        poller.poll_forever(client, stop_after=2)
    assert handled == [41]
    assert offsets == [None, 42]
