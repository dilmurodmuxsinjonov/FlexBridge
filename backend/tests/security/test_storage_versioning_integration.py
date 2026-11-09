"""Actual localhost S3 requests; generated credentials; AV explicitly doubled.

Provider-admin overwrite/deletion is trusted test setup, not a public exploit.
No presigned URL or credential is included in evidence/assertion messages.
"""
from dataclasses import dataclass, field
from datetime import timedelta
import hashlib
import io
import os
from pathlib import Path
import platform
import runpy
import secrets
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from uuid import uuid4
import pytest
from botocore.exceptions import ClientError
from pypdf import PdfWriter
from sqlalchemy import select
from app.adapters import storage, antivirus
from app.db.storage import transaction, table, now
from app.services.files_quarantine import run_scan, apply_scan
from app.workers.outbox import relay_pending_outbox_events

ROOT = Path(__file__).resolve().parents[3]


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


@dataclass(repr=False)
class MinioServer:
    endpoint: str
    access: str = field(repr=False)
    secret: str = field(repr=False)


@pytest.fixture(scope='session')
def minio_server():
    binary = os.environ.get('MINIO_TEST_BINARY')
    if not binary:
        pytest.fail('Prepare scripts/prepare_test_minio.py and set MINIO_TEST_BINARY; real S3 tests cannot be skipped')
    sources = runpy.run_path(str(ROOT / 'scripts/prepare_test_minio.py'))['SOURCES']
    assert hashlib.sha256(Path(binary).read_bytes()).hexdigest() == sources[platform.system()][1]
    data_root = ROOT / 'backend/.data'
    data_root.mkdir(parents=True, exist_ok=True)
    directory = tempfile.TemporaryDirectory(dir=data_root, prefix='minio_test_')
    api_port, console_port = free_port(), free_port()
    while console_port == api_port:
        console_port = free_port()
    server = MinioServer(f'http://127.0.0.1:{api_port}', secrets.token_hex(12), secrets.token_urlsafe(36))
    process = subprocess.Popen([binary, 'server', directory.name, '--address', f'127.0.0.1:{api_port}',
        '--console-address', f'127.0.0.1:{console_port}'],
        env={**os.environ, 'MINIO_ROOT_USER': server.access, 'MINIO_ROOT_PASSWORD': server.secret,
            'MINIO_BROWSER': 'off', 'MINIO_UPDATE': 'off'},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                with urlopen(server.endpoint + '/minio/health/live', timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    pytest.fail('Disposable localhost MinIO did not become healthy')
                time.sleep(.2)
        yield server
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        # Only this generated workspace-local directory may be recursively removed.
        assert Path(directory.name).resolve().is_relative_to(data_root.resolve())
        assert Path(directory.name).name.startswith('minio_test_')
        directory.cleanup()


@pytest.fixture
def versioned_store(minio_server, monkeypatch):
    for name, value in {'S3_ENDPOINT_URL': minio_server.endpoint, 'S3_PUBLIC_ENDPOINT_URL': minio_server.endpoint,
            'S3_ACCESS_KEY': minio_server.access, 'S3_SECRET_KEY': minio_server.secret,
            'S3_BUCKET': 'flexbridge-test-' + secrets.token_hex(8)}.items():
        monkeypatch.setenv(name, value)
    actual = storage.client()
    actual.create_bucket(Bucket=storage.bucket())
    actual.put_bucket_versioning(Bucket=storage.bucket(), VersioningConfiguration={'Status': 'Enabled'})
    return actual


def pdf(size=100):
    writer = PdfWriter()
    writer.add_blank_page(width=size, height=size)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def begin_upload(client, owner, raw):
    response = client.post('/api/v1/files/upload-intents', headers=owner['headers'], json={
        'filename': 'evidence.pdf', 'mime_type': 'application/pdf', 'size_bytes': len(raw)})
    assert response.status_code == 201
    intent = response.json()
    with urlopen(Request(intent['upload_url'], data=raw, method='PUT', headers={
            'Content-Type': 'application/pdf', 'Content-Length': str(len(raw))}), timeout=5) as uploaded:
        assert uploaded.status == 200
    return intent['id']


def complete(client, owner, file_id):
    return client.post('/api/v1/files/' + file_id + '/complete-upload', headers=owner['headers'])


def stored(file_id):
    with transaction() as conn:
        return dict(conn.execute(select(table('files')).where(table('files').c.id == file_id)).mappings().one())


def fetch(url):
    try:
        with urlopen(url, timeout=5) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, b''


def test_pinned_scan_and_download_survive_current_key_replacement(client, identities, versioned_store, monkeypatch):
    owner, outsider = identities(), identities()
    original, replacement = pdf(), pdf(200)
    file_id = begin_upload(client, owner, original)
    assert complete(client, owner, file_id).status_code == 202
    quarantine = stored(file_id)
    versioned_store.put_object(Bucket=storage.bucket(), Key=quarantine['storage_key'], Body=replacement)
    scanned = []
    monkeypatch.setattr(antivirus, 'scan', lambda raw: scanned.append(raw))
    assert relay_pending_outbox_events() == 1
    clean = stored(file_id)
    assert scanned == [original] and clean['sha256'] == hashlib.sha256(original).hexdigest()
    assert clean['storage_version_id'] != quarantine['storage_version_id']
    assert client.get('/api/v1/files/' + file_id + '/download', headers=outsider['headers']).status_code == 403
    authorized = client.get('/api/v1/files/' + file_id + '/download', headers=owner['headers'])
    assert authorized.status_code == 200
    url = authorized.json()['signed_url']
    replacement_result = versioned_store.put_object(Bucket=storage.bucket(), Key=clean['storage_key'], Body=replacement)
    assert fetch(url) == (200, original)
    parts = urlsplit(url)
    query = [(key, replacement_result['VersionId'] if key == 'versionId' else value) for key, value in parse_qsl(parts.query)]
    altered = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    assert fetch(altered)[0] == 403
    versioned_store.delete_object(Bucket=storage.bucket(), Key=clean['storage_key'])
    assert fetch(url) == (200, original), 'A current delete marker must not retarget a version URL'
    versioned_store.delete_object(Bucket=storage.bucket(), Key=clean['storage_key'], VersionId=clean['storage_version_id'])
    assert fetch(url)[0] in (403, 404), 'Deleted pinned version must fail, never read a replacement'


def test_unversioned_completion_cannot_enqueue_scan(client, identities, versioned_store):
    versioned_store.put_bucket_versioning(Bucket=storage.bucket(), VersioningConfiguration={'Status': 'Suspended'})
    owner = identities()
    file_id = begin_upload(client, owner, pdf())
    response = complete(client, owner, file_id)
    assert response.status_code == 503 and response.json()['detail']['code'] == 'FILE_STORAGE_VERSIONING_REQUIRED'
    assert stored(file_id)['scan_status'] == 'PENDING_SCAN'
    with transaction() as conn:
        assert not conn.execute(select(table('outbox_events').c.id).where(table('outbox_events').c.aggregate_key == file_id)).first()


def test_suspended_private_write_cannot_publish_clean(client, identities, versioned_store, monkeypatch):
    owner = identities()
    file_id = begin_upload(client, owner, pdf())
    assert complete(client, owner, file_id).status_code == 202
    monkeypatch.setattr(antivirus, 'scan', lambda raw: None)
    versioned_store.put_bucket_versioning(Bucket=storage.bucket(), VersioningConfiguration={'Status': 'Suspended'})
    assert relay_pending_outbox_events() == 0
    assert stored(file_id)['scan_status'] == 'SCANNING'
    assert client.get('/api/v1/files/' + file_id + '/download', headers=owner['headers']).status_code == 409


def test_changed_source_generation_cannot_publish_or_rebind_queued_intent(client, identities, versioned_store, monkeypatch):
    owner = identities()
    file_id = begin_upload(client, owner, pdf())
    assert complete(client, owner, file_id).status_code == 202
    initial = stored(file_id)
    monkeypatch.setattr(antivirus, 'scan', lambda raw: None)
    changed = []
    def execute(event):
        result = run_scan(event)
        replacement = pdf(200)
        reference = storage.response_reference(versioned_store.put_object(
            Bucket=storage.bucket(), Key=initial['storage_key'], Body=replacement))
        # Trusted DB maintenance fixture; no public scan-reset/rebind API exists.
        with transaction() as conn:
            conn.execute(table('files').update().where(table('files').c.id == file_id).values(
                **reference.values(), object_version=reference.etag, byte_size=len(replacement)))
        changed.append(reference.version_id)
        return result
    assert relay_pending_outbox_events(registry={'FILE_SCAN_REQUESTED': (execute, apply_scan)}) == 0
    assert stored(file_id)['scan_status'] == 'SCANNING' and stored(file_id)['storage_version_id'] == changed[0]
    with transaction() as conn:
        events = table('outbox_events')
        event = conn.execute(select(events).where(events.c.aggregate_key == file_id)).mappings().one()
        assert event['processed_at'] is None and event['payload']['source']['storage_version_id'] == initial['storage_version_id']
        conn.execute(events.update().where(events.c.id == event['id']).values(available_at=now(), lease_until=None))
    assert relay_pending_outbox_events() == 0, 'Old queued source must not silently scan a new generation'
    assert stored(file_id)['scan_status'] == 'SCANNING'


@pytest.mark.parametrize('failure', ['stale_token', 'apply_failure'])
def test_orphaned_private_put_retry_uses_pinned_source(client, identities, versioned_store, monkeypatch, failure):
    owner = identities()
    original = pdf()
    file_id = begin_upload(client, owner, original)
    assert complete(client, owner, file_id).status_code == 202
    monkeypatch.setattr(antivirus, 'scan', lambda raw: None)
    events = table('outbox_events')
    def execute(event):
        result = run_scan(event)
        if failure == 'stale_token':
            with transaction() as conn:
                conn.execute(events.update().where(events.c.id == event['id']).values(claim_token=str(uuid4())))
        return result
    def apply(conn, event, result):
        if failure == 'apply_failure':
            raise RuntimeError('Intentional apply rollback after actual private PUT')
        apply_scan(conn, event, result)
    assert relay_pending_outbox_events(registry={'FILE_SCAN_REQUESTED': (execute, apply)}) == 0
    assert stored(file_id)['scan_status'] == 'SCANNING'
    with transaction() as conn:
        event = conn.execute(select(events).where(events.c.aggregate_key == file_id)).mappings().one()
        assert event['processed_at'] is None
        conn.execute(events.update().where(events.c.id == event['id']).values(lease_until=now()-timedelta(seconds=1), available_at=now()))
    retry_errors = []
    def retry(event):
        try:
            return run_scan(event)
        except ClientError as error:
            retry_errors.append((error.operation_name, error.response.get('Error', {}).get('Code')))
            raise
    assert relay_pending_outbox_events(registry={'FILE_SCAN_REQUESTED': (retry, apply_scan)}) == 1, retry_errors
    clean = stored(file_id)
    versions = versioned_store.list_object_versions(Bucket=storage.bucket(), Prefix=clean['storage_key'])['Versions']
    assert len(versions) == 2 and clean['storage_version_id'] in [v['VersionId'] for v in versions]
    authorized = client.get('/api/v1/files/' + file_id + '/download', headers=owner['headers'])
    assert authorized.status_code == 200 and fetch(authorized.json()['signed_url']) == (200, original)


def test_readiness_tracks_real_enabled_suspended_and_unavailable_bucket(versioned_store, monkeypatch):
    from app.core.readiness import dependency_readiness
    checks = dependency_readiness()['checks']
    assert checks['object_storage'] and checks['object_storage_versioning']
    versioned_store.put_bucket_versioning(Bucket=storage.bucket(), VersioningConfiguration={'Status': 'Suspended'})
    checks = dependency_readiness()['checks']
    assert checks['object_storage'] and not checks['object_storage_versioning']
    monkeypatch.setenv('S3_BUCKET', 'missing-' + secrets.token_hex(8))
    checks = dependency_readiness()['checks']
    assert not checks['object_storage'] and not checks['object_storage_versioning']
