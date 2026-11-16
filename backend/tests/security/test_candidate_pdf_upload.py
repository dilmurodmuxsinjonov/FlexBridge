"""Candidate direct PDF upload is fail-closed (API-026-DIRECT-UPLOAD).

Before: the service called a non-existent ``antivirus.scan_bytes`` and swallowed
the error, so no upload was ever scanned; storage failures were swallowed too
(a CLEAN record pointed at a missing object); and a request without content
produced a generated blank PDF that could be attached as "evidence".
"""
import base64
import io

import pytest
from pypdf import PdfWriter
from sqlalchemy import func, select

from app.adapters import antivirus, storage
from app.db.storage import table, transaction

URL = '/api/v1/me/candidate/files/upload'


def pdf_b64() -> str:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return base64.b64encode(buf.getvalue()).decode('ascii')


def file_count(user_id) -> int:
    with transaction() as conn:
        files = table('files')
        return conn.execute(select(func.count()).select_from(files).where(files.c.owner_user_id == user_id)).scalar_one()


@pytest.fixture
def object_store(monkeypatch):
    writes = {}

    def write(key, raw):
        writes[key] = raw
        return storage.ObjectReference('test-private-bucket', 'v1', 'etag-1')

    monkeypatch.setattr(storage, 'write_private', write)
    return writes


def test_clean_pdf_is_scanned_stored_and_recorded(client, identities, object_store, monkeypatch):
    scanned = []
    monkeypatch.setattr(antivirus, 'scan', lambda raw: scanned.append(raw))
    student = identities()
    r = client.post(URL, headers=student['headers'], json={'filename': 'cv.pdf', 'purpose': 'CV', 'content_base64': pdf_b64()})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body['scan_status'] == 'CLEAN' and body['linked_as_cv'] is True
    assert len(scanned) == 1 and list(object_store.values()) == scanned
    with transaction() as conn:
        files = table('files')
        row = conn.execute(select(files).where(files.c.id == body['file_id'])).mappings().one()
    assert row['storage_bucket'] == 'test-private-bucket' and row['storage_version_id'] == 'v1' and row['storage_etag'] == 'etag-1'


def test_missing_content_never_generates_a_blank_pdf(client, identities, object_store, monkeypatch):
    monkeypatch.setattr(antivirus, 'scan', lambda raw: None)
    student = identities()
    r = client.post(URL, headers=student['headers'], json={'filename': 'cert.pdf', 'purpose': 'CERTIFICATE'})
    assert r.status_code == 422
    assert object_store == {} and file_count(student['user_id']) == 0


def test_antivirus_outage_fails_closed(client, identities, object_store, monkeypatch):
    def unavailable(raw):
        raise RuntimeError('ClamAV is not configured')

    monkeypatch.setattr(antivirus, 'scan', unavailable)
    student = identities()
    r = client.post(URL, headers=student['headers'], json={'filename': 'cv.pdf', 'purpose': 'CV', 'content_base64': pdf_b64()})
    assert r.status_code == 503 and 'ANTIVIRUS_UNAVAILABLE' in r.text
    assert object_store == {} and file_count(student['user_id']) == 0


def test_malware_verdict_is_rejected(client, identities, object_store, monkeypatch):
    def infected(raw):
        raise ValueError('MALWARE_DETECTED')

    monkeypatch.setattr(antivirus, 'scan', infected)
    student = identities()
    r = client.post(URL, headers=student['headers'], json={'filename': 'x.pdf', 'content_base64': pdf_b64()})
    assert r.status_code == 422 and 'MALWARE_DETECTED_QUARANTINED' in r.text
    assert object_store == {} and file_count(student['user_id']) == 0


def test_storage_failure_leaves_no_clean_record(client, identities, monkeypatch):
    monkeypatch.setattr(antivirus, 'scan', lambda raw: None)

    def broken(key, raw):
        raise ConnectionError('object store down')

    monkeypatch.setattr(storage, 'write_private', broken)
    student = identities()
    r = client.post(URL, headers=student['headers'], json={'filename': 'cv.pdf', 'purpose': 'CV', 'content_base64': pdf_b64()})
    assert r.status_code == 503 and 'FILE_STORAGE_UNAVAILABLE' in r.text
    assert file_count(student['user_id']) == 0


def test_non_pdf_bytes_rejected(client, identities, object_store, monkeypatch):
    monkeypatch.setattr(antivirus, 'scan', lambda raw: None)
    student = identities()
    fake = base64.b64encode(b'GIF89a' + b'\0' * 64).decode('ascii')
    r = client.post(URL, headers=student['headers'], json={'filename': 'x.pdf', 'content_base64': fake})
    assert r.status_code == 422 and 'INVALID_PDF_FORMAT' in r.text
    assert object_store == {}
