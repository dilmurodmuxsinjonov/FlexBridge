"""Pinned source probes: actual sessions and SQL waits; explicit storage doubles."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import uuid4
import pytest
from sqlalchemy import select, text
from app.adapters import storage
from app.db.storage import table, transaction, get_engine, now
from app.services.files_quarantine import file_quarantine_service as service
from app.services.placements import insert_row
from test_candidate import cv_fixture
from test_org_authority_transactions import wait_for_blocker


def operation(kind, client, identities, monkeypatch, owner=None):
    owner = owner or identities()
    signed = []
    monkeypatch.setattr(storage, 'presign_put', lambda key, size: signed.append('PUT') or 'https://fixture.invalid/upload')
    monkeypatch.setattr(storage, 'presign_get', lambda key, *, reference: signed.append('GET') or 'https://fixture.invalid/download')
    def head(key):
        signed.append('HEAD')
        return {'ContentLength':100,'ETag':'"'+uuid4().hex+'"','VersionId':str(uuid4())}
    monkeypatch.setattr(storage,'head',head)
    if kind == 'initiate':
        request = lambda: client.post('/api/v1/files/upload-intents', headers=owner['headers'], json={'filename': 'private.pdf', 'size_bytes': 100})
        return owner, request, signed, None
    if kind == 'complete':
        created = client.post('/api/v1/files/upload-intents', headers=owner['headers'], json={'filename': 'private.pdf', 'size_bytes': 100})
        assert created.status_code == 201
        key = created.json()['id']
        request = lambda: client.post('/api/v1/files/' + key + '/complete-upload', headers=owner['headers'])
    else:
        key = cv_fixture(owner)['id']
        request = lambda: client.get('/api/v1/files/' + key + '/download', headers=owner['headers'])
    signed.clear()
    return owner, request, signed, key


def business():
    with transaction() as conn:
        return {name: [tuple(row) for row in conn.execute(select(table(name)).order_by(table(name).c.id))]
                for name in ('files', 'outbox_events')}


def change_security(change, client, owner):
    if change == 'logout':
        result = client.delete('/api/v1/me/sessions/' + owner['session_id'], headers=owner['headers'])
        assert result.status_code == 200
        return
    with transaction() as conn:
        if change == 'expiry':
            conn.execute(table('sessions').update().where(table('sessions').c.id == owner['session_id']).values(expires_at=now()-timedelta(seconds=1)))
        elif change == 'auth_version':
            users = table('users')
            conn.execute(users.update().where(users.c.id == owner['user_id']).values(auth_version=users.c.auth_version+1))
        elif change == 'suspended':
            conn.execute(table('users').update().where(table('users').c.id == owner['user_id']).values(status='SUSPENDED'))
        else:
            roles = table('role_catalog')
            role = conn.execute(select(roles.c.id).where(roles.c.code == 'MODERATOR', roles.c.scope_kind == 'PLATFORM')).scalar_one_or_none()
            if role is None:
                role = insert_row(conn, 'role_catalog', code='MODERATOR', scope_kind='PLATFORM', description='Trusted current role fixture')['id']
            grantor=insert_row(conn,'users',display_name='Independent trusted grantor',status='ACTIVE',locale='uz',timezone='Asia/Tashkent')
            insert_row(conn, 'platform_role_grants', user_id=owner['user_id'], role_id=role,
                granted_by_id=grantor['id'], expires_at=now()+timedelta(hours=1))


@pytest.mark.parametrize('kind', ['initiate', 'complete', 'download'])
@pytest.mark.parametrize('change', ['logout', 'expiry', 'auth_version', 'suspended', 'sensitive_role'])
def test_security_change_after_preflight_denies_owner_file_operation(client, identities, monkeypatch, kind, change):
    owner, request, signed, file_id = operation(kind, client, identities, monkeypatch)
    before = business()
    with ThreadPoolExecutor(max_workers=1) as pool:
        if kind == 'initiate':
            # No existing business row: an explicit service-entry barrier follows
            # real middleware/dependency authentication, not a claimed SQL wait.
            ready, release = Event(), Event()
            original = service.initiate_upload_api_x01
            def entry(**kwargs):
                ready.set()
                assert release.wait(30)
                return original(**kwargs)
            monkeypatch.setattr(service, 'initiate_upload_api_x01', entry)
            pending = pool.submit(request)
            try:
                assert ready.wait(30)
                change_security(change, client, owner)
            finally:
                release.set()
        else:
            with get_engine().begin() as blocker:
                if kind == 'complete':
                    blocker.execute(select(table('files')).where(table('files').c.id == file_id).with_for_update())
                else:
                    # Current download is a plain SELECT; use an actual table
                    # lock, explicitly not a claimed row-level wait.
                    blocker.execute(text('LOCK TABLE flexbridge.files IN ACCESS EXCLUSIVE MODE'))
                pid = blocker.execute(text('SELECT pg_backend_pid()')).scalar_one()
                pending = pool.submit(request)
                wait_for_blocker(pid)
                change_security(change, client, owner)
        response = pending.result(timeout=30)
    assert response.status_code in (401, 403), (kind, change, response.status_code)
    assert business() == before and not signed
