"""Version provenance and public failure boundaries; provider calls explicitly stubbed."""
import io
from uuid import UUID
import pytest
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from botocore.stub import Stubber
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app.adapters import storage
from app.db.storage import table, transaction, now
from app.db.institution_scope import institution_scope_query
from test_candidate import cv_fixture
from test_institution_migration import populated_database, seed_old_scope
from test_institution_onboarding import first_claim, submit, accept, claim, decide
from test_regressions import count


@pytest.mark.parametrize('version', [None, '', 'null', 'NULL', ' null ', ' '])
def test_provider_etag_is_never_used_as_version(version):
    with pytest.raises(storage.StorageReferenceError) as rejected:
        storage.response_reference({'ETag': 'ordinary-etag', 'VersionId': version})
    assert rejected.value.code == 'FILE_STORAGE_VERSIONING_REQUIRED' and rejected.value.status_code == 503


@pytest.mark.parametrize('wrong', ['VersionId', 'ETag'])
def test_selected_version_read_rejects_wrong_provider_response_and_closes_body(monkeypatch, wrong):
    for name, value in {'S3_ENDPOINT_URL': 'https://storage.invalid', 'S3_ACCESS_KEY': 'fixture-access',
            'S3_SECRET_KEY': 'fixture-secret'}.items():
        monkeypatch.setenv(name, value)
    actual = storage.client()
    stream = io.BytesIO(b'original')
    response = {'Body': StreamingBody(stream, 8), 'VersionId': 'selected-version', 'ETag': 'selected-etag'}
    response[wrong] = 'other-object-reference'
    stub = Stubber(actual)
    stub.add_response('get_object', response, {'Bucket': 'test-private-bucket', 'Key': 'quarantine/source.pdf',
        'VersionId': 'selected-version', 'IfMatch': 'selected-etag'})
    monkeypatch.setattr(storage, 'client', lambda **unused: actual)
    with stub, pytest.raises(storage.StorageReferenceError) as rejected:
        storage.read('quarantine/source.pdf', storage.ObjectReference('test-private-bucket', 'selected-version', 'selected-etag'), 20)
    assert rejected.value.code == 'FILE_STORAGE_READ_MISMATCH' and stream.closed


def test_bucket_reconfiguration_does_not_sign_a_different_bucket(client, identities, monkeypatch):
    owner = identities()
    file = cv_fixture(owner)
    signed = []
    monkeypatch.setattr(storage, 'client', lambda **unused: signed.append(True))
    monkeypatch.setenv('S3_BUCKET', 'different-bucket')
    response = client.get('/api/v1/files/' + file['id'] + '/download', headers=owner['headers'])
    assert response.status_code == 503 and response.json()['detail']['code'] == 'FILE_STORAGE_BUCKET_MISMATCH'
    assert signed == [] and file['storage_key'] not in response.text


def test_provider_failure_has_no_url_or_raw_provider_detail(client, identities, monkeypatch):
    owner = identities()
    monkeypatch.setattr(storage, 'presign_put', lambda key, size: 'https://fixture.invalid/upload')
    response = client.post('/api/v1/files/upload-intents', headers=owner['headers'], json={'filename': 'file.pdf', 'size_bytes': 100})
    assert response.status_code == 201
    file_id = response.json()['id']
    def unavailable(key):
        raise ClientError({'Error': {'Code': 'NoSuchKey', 'Message': 'provider-internal-material'}}, 'HeadObject')
    monkeypatch.setattr(storage, 'head', unavailable)
    response = client.post('/api/v1/files/' + file_id + '/complete-upload', headers=owner['headers'])
    assert response.status_code == 503 and response.json()['detail']['code'] == 'DEPENDENCY_UNAVAILABLE'
    assert 'provider-internal-material' not in response.text
    with transaction() as conn:
        assert conn.execute(select(table('files').c.scan_status).where(table('files').c.id == file_id)).scalar_one() == 'PENDING_SCAN'
    assert count('outbox_events') == 0


def test_populated0011_upgrade_preserves_legacy_file_and_accepted_authority():
    with populated_database() as (engine, migrate):
        migrate('0011_institution_onboarding')
        with engine.begin() as conn:
            user, inst, member, appointment, grant = seed_old_scope(conn)
            before_file = dict(conn.execute(text('SELECT * FROM flexbridge.files WHERE id=:id'), {'id': appointment['document_file_id']}).mappings().one())
            before_file = {key: str(value) if isinstance(value, UUID) else value for key, value in before_file.items()}
            before_grant = dict(conn.execute(select(table('institution_role_grants')).where(table('institution_role_grants').c.id == grant['id'])).mappings().one())
        migrate('head')
        with engine.begin() as conn:
            after_file = dict(conn.execute(select(table('files')).where(table('files').c.id == before_file['id'])).mappings().one())
            assert {key: after_file[key] for key in before_file} == before_file
            assert all(after_file[key] is None for key in ('storage_bucket', 'storage_version_id', 'storage_etag'))
            after_grant = dict(conn.execute(select(table('institution_role_grants')).where(table('institution_role_grants').c.id == grant['id'])).mappings().one())
            assert after_grant == before_grant
            assert conn.execute(institution_scope_query(user['id'], inst['id'], ('COORDINATOR',))).first()
            with pytest.raises(storage.StorageReferenceError) as legacy:
                storage.file_reference(after_file)
            assert legacy.value.code == 'FILE_STORAGE_REFERENCE_REQUIRED'
            assert conn.execute(text('SELECT count(*) FROM flexbridge.institution_onboarding_consents')).scalar_one() == 0


@pytest.mark.parametrize('values', [
    {'storage_bucket': None, 'storage_version_id': None, 'storage_etag': None},
    {'storage_version_id': 'null'}, {'storage_etag': None}, {'object_version': 'other-reference'},
])
def test_new_clean_provenance_cannot_be_removed_or_partially_rewritten(identities, values):
    file = cv_fixture(identities())
    with pytest.raises(IntegrityError), transaction() as conn:
        conn.execute(table('files').update().where(table('files').c.id == file['id']).values(**values))
    with transaction() as conn:
        row = conn.execute(select(table('files')).where(table('files').c.id == file['id'])).mappings().one()
        assert row['storage_version_id'] == file['storage_version_id']


def test_old_revision_snapshot_cannot_activate_without_explicit_new_revision(client, identities, monkeypatch):
    from app.services import institution_onboarding as module
    original = module.file_snapshot
    # Trusted historical-shape fixture; no public snapshot mutation API exists.
    with monkeypatch.context() as old:
        old.setattr(module, 'file_snapshot', lambda row: {key: original(row)[key] for key in ('sha256', 'object_version', 'storage_key', 'byte_size')})
        flow = first_claim(identities)
        response = submit(client, flow)
        assert response.status_code == 202
        appointment, case = response.json()['id'], response.json()['case_id']
        assert accept(client, flow, appointment).status_code == 200
    moderator = identities('MODERATOR')
    assert claim(client, moderator, case).status_code == 200
    response = decide(client, moderator, case)
    assert response.status_code == 409 and response.json()['detail']['code'] == 'INSTITUTION_EVIDENCE_CHANGED'
    assert count('institution_role_grants') == 0
    assert decide(client, moderator, case, decision='NEEDS_INFO').status_code == 200
    path = '/api/v1/institution-appointments/' + appointment + '/revisions'
    response = client.post(path, headers={**flow['user']['headers'], 'Idempotency-Key': 'new-storage-proof-revision'},
        json={**flow['body'], 'expected_revision': 1})
    assert response.status_code == 202, response.text
    assert decide(client, moderator, case, revision=2).status_code == 200
    assert count('institution_role_grants') == 0, 'Earlier revision acceptance cannot activate new evidence'
    assert accept(client, flow, appointment, revision=2).status_code == 200
    assert count('institution_role_grants') == 1


@pytest.mark.parametrize('viewer', ['requester', 'reviewer'])
def test_scoped_institution_signer_pins_exact_reference_and_failure_rolls_back_audit(client, identities, monkeypatch, viewer):
    flow = first_claim(identities)
    created = submit(client, flow)
    assert created.status_code == 202
    appointment, case = created.json()['id'], created.json()['case_id']
    if viewer == 'reviewer':
        user = identities('MODERATOR')
        assert claim(client, user, case).status_code == 200
        path = '/api/v1/operator/verification-cases/' + case + '/files/' + flow['document']['id'] + '/download'
    else:
        user = flow['user']
        path = '/api/v1/institution-appointments/' + appointment + '/files/' + flow['document']['id'] + '/download'
    calls = []
    def sign(key, *, reference):
        expected = flow['document']
        assert key == expected['storage_key']
        assert (reference.bucket, reference.version_id, reference.etag) == (
            expected['storage_bucket'], expected['storage_version_id'], expected['storage_etag'])
        calls.append(key)
        return 'https://fixture.invalid/version-bound'
    monkeypatch.setattr(storage, 'presign_get', sign)
    assert client.get(path, headers=identities()['headers']).status_code == 403 and calls == []
    response = client.get(path, headers=user['headers'])
    assert response.status_code == 200 and len(calls) == 1 and response.json()['expires_in_seconds'] == 60
    before = count('audit_events')
    def failure(key, *, reference):
        raise ClientError({'Error': {'Code': 'ServiceUnavailable', 'Message': 'private-provider-detail'}}, 'GetObject')
    monkeypatch.setattr(storage, 'presign_get', failure)
    response = client.get(path, headers=user['headers'])
    assert response.status_code == 503 and 'private-provider-detail' not in response.text
    assert count('audit_events') == before
