"""Post-fix controls planned for59; do not execute against the old implementation."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import select, text
from app.api.dependencies import ActorContext
from app.db.storage import table, transaction
from app.services.files_quarantine import file_quarantine_service as service
from app.services.governance import GovernanceError
from test_files_authority_expanded import operation, business
from test_org_authority_transactions import wait_for_blocker


@pytest.mark.parametrize('kind', ['initiate', 'complete', 'download'])
def test_authorized_file_operation_commits_before_actual_waiting_logout(client, identities, monkeypatch, kind):
    from app.services import files_quarantine as module
    owner, request, signed, file_id = operation(kind, client, identities, monkeypatch)
    original = module.account_authority
    held, release = Event(), Event()
    pids = []
    def guarded(conn, actor, **kwargs):
        original(conn, actor, **kwargs)
        if actor.user_id == owner['user_id']:
            pids.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
            held.set()
            assert release.wait(30)
    monkeypatch.setattr(module, 'account_authority', guarded)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(request)
        try:
            assert held.wait(30)
            revoked = pool.submit(lambda: client.delete('/api/v1/me/sessions/' + owner['session_id'], headers=owner['headers']))
            wait_for_blocker(pids[0])
            assert not revoked.done()
        finally:
            release.set()
        response, logout = pending.result(timeout=30), revoked.result(timeout=30)
    assert response.status_code == {'initiate': 201, 'complete': 202, 'download': 200}[kind]
    assert logout.status_code == 200
    assert client.get('/api/v1/auth/me', headers=owner['headers']).status_code == 401
    if kind == 'complete':
        with transaction() as conn:
            assert conn.execute(select(table('files').c.scan_status).where(table('files').c.id == file_id)).scalar_one() == 'SCANNING'
            assert conn.execute(select(table('outbox_events').c.id).where(table('outbox_events').c.aggregate_key == file_id)).first()


@pytest.mark.parametrize('kind', ['initiate', 'complete', 'download'])
def test_current_password_owner_succeeds_and_foreign_session_never_substitutes(client, identities, monkeypatch, kind):
    owner, request, signed, file_id = operation(kind, client, identities, monkeypatch)
    stranger = identities()
    forged = ActorContext(owner['user_id'], stranger['session_id'], ())
    before = business()
    with pytest.raises(GovernanceError) as rejected:
        if kind == 'initiate':
            service.initiate_upload_api_x01(actor=forged, filename='private.pdf', size_bytes=100)
        elif kind == 'complete':
            service.complete_upload(file_id, forged)
        else:
            service.issue_signed_download_url_api_x03(file_id=file_id, actor=forged)
    assert rejected.value.status_code in (401, 403)
    assert business() == before and signed == []
    response = request()
    assert response.status_code == {'initiate': 201, 'complete': 202, 'download': 200}[kind]


@pytest.mark.parametrize('kind', ['initiate', 'complete', 'download'])
def test_provider_failure_rolls_back_file_and_outbox(client, identities, monkeypatch, kind):
    from app.adapters import storage
    owner, request, signed, file_id = operation(kind, client, identities, monkeypatch)
    before = business()
    def fail(*args, **kwargs):
        raise RuntimeError('Synthetic provider failure after current authority')
    monkeypatch.setattr(storage, {'initiate': 'presign_put', 'complete': 'head', 'download': 'presign_get'}[kind], fail)
    response = request()
    assert response.status_code == 503
    assert business() == before


@pytest.mark.parametrize('kind', ['initiate', 'complete', 'download'])
def test_current_sensitive_mfa_actor_retains_owner_file_access(client, identities, monkeypatch, kind):
    owner = identities('MODERATOR')
    owner, request, signed, file_id = operation(kind, client, identities, monkeypatch, owner=owner)
    response = request()
    assert response.status_code == {'initiate': 201, 'complete': 202, 'download': 200}[kind]
