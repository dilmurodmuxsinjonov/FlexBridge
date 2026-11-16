"""University account manages its own staff (Issue #235).

The first coordinator is the university's own account; it lists every staff
appointment of its institution and the agreement a staff request must cite,
and can attach staff evidence PDFs through the fail-closed direct upload.
"""
import base64
import io
from datetime import date, timedelta
from uuid import uuid4

import pytest
from pypdf import PdfWriter
from sqlalchemy import func, select

from app.adapters import antivirus, storage
from app.db.storage import table, transaction
from test_institution_onboarding import accept, active_coordinator, claim, decide, staff_claim
from test_invitations import contact


def pdf_b64() -> str:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return base64.b64encode(buf.getvalue()).decode('ascii')


@pytest.fixture
def object_store(monkeypatch):
    writes = {}

    def write(key, raw):
        writes[key] = raw
        return storage.ObjectReference('test-private-bucket', 'v-' + uuid4().hex[:8], 'etag-' + uuid4().hex[:8])

    monkeypatch.setattr(storage, 'write_private', write)
    monkeypatch.setattr(antivirus, 'scan', lambda raw: None)
    return writes


def staff_list(client, user, inst):
    return client.get(f'/api/v1/institutions/{inst}/staff-appointments', headers=user['headers'])


def test_coordinator_lists_staff_lifecycle_and_current_agreement(client, identities):
    f = active_coordinator(client, identities)
    listed = staff_list(client, f['user'], f['institution_id'])
    assert listed.status_code == 200, listed.text
    data = listed.json()
    assert data['agreement']['id'] == f['agreement_id']
    assert data['institution']['registry_code'] == f['body']['registry_code'].upper()
    [me] = data['items']
    assert me['role'] == 'COORDINATOR' and me['is_self'] is True and me['role_active'] is True

    teacher = identities()
    request, verified, _ = staff_claim(client, f, teacher)
    pending = {i['id']: i for i in staff_list(client, f['user'], f['institution_id']).json()['items']}[request['id']]
    assert pending['role'] == 'TEACHER' and pending['role_active'] is False and pending['is_self'] is False
    assert pending['status'] == 'PENDING_REVIEW'

    assert accept(client, f, request['id'], user=teacher, contact_id=verified['id']).status_code == 200
    assert claim(client, f['moderator'], request['case_id']).status_code == 200
    assert decide(client, f['moderator'], request['case_id']).status_code == 200
    active = {i['id']: i for i in staff_list(client, f['user'], f['institution_id']).json()['items']}[request['id']]
    assert active['role_active'] is True and active['status'] == 'ACTIVE'

    # A teacher is staff, not an administrator of the staff list.
    assert staff_list(client, teacher, f['institution_id']).status_code == 403

    revoked = client.post(f"/api/v1/institution-appointments/{request['id']}/revoke", headers=f['user']['headers'],
                          json={'reason': 'Teacher left the department at the end of semester'})
    assert revoked.status_code == 200, revoked.text
    after = {i['id']: i for i in staff_list(client, f['user'], f['institution_id']).json()['items']}[request['id']]
    assert after['status'] == 'REVOKED' and after['role_active'] is False


def test_staff_list_is_private_to_the_institution(client, identities):
    f = active_coordinator(client, identities)
    stranger = identities()
    assert staff_list(client, stranger, f['institution_id']).status_code == 403
    assert client.get(f"/api/v1/institutions/{f['institution_id']}/staff-appointments").status_code == 401
    assert staff_list(client, f['user'], str(uuid4())).status_code in (403, 404)


def test_staff_pdf_upload_feeds_a_staff_appointment(client, identities, object_store):
    f = active_coordinator(client, identities)
    up = client.post('/api/v1/files/pdf', headers=f['user']['headers'],
                     json={'filename': 'buyruq', 'purpose': 'INSTITUTION_APPOINTMENT', 'content_base64': pdf_b64()})
    assert up.status_code == 201, up.text
    doc = up.json()
    assert doc['scan_status'] == 'CLEAN' and doc['filename'] == 'buyruq.pdf' and len(object_store) == 1

    teacher = identities()
    verified = contact(teacher, value=str(uuid4()) + '@example.test', channel='EMAIL')
    body = dict(registry_code=f['body']['registry_code'], document_file_id=doc['file_id'], contact_id=f['contact']['id'],
                valid_from=date.today().isoformat(), valid_to=(date.today() + timedelta(days=90)).isoformat(),
                legal_basis='Teacher appointment under the reviewed institution agreement', file_ids=[doc['file_id']],
                evidence_note='Teacher formal appointment for independent platform review', agreement_id=f['agreement_id'],
                target_channel='EMAIL', target_destination=verified['normalized_value'])
    r = client.post('/api/v1/institution-appointments', headers={**f['user']['headers'], 'Idempotency-Key': 'staff-upload-request'}, json=body)
    assert r.status_code == 202, r.text
    assert r.json()['mode'] == 'STAFF_TEACHER'


def test_staff_pdf_upload_is_fail_closed(client, identities, monkeypatch, object_store):
    user = identities()

    def unavailable(raw):
        raise RuntimeError('ClamAV is not configured')

    monkeypatch.setattr(antivirus, 'scan', unavailable)
    r = client.post('/api/v1/files/pdf', headers=user['headers'],
                    json={'purpose': 'INSTITUTION_AGREEMENT', 'content_base64': pdf_b64()})
    assert r.status_code == 503 and 'ANTIVIRUS_UNAVAILABLE' in r.text
    with transaction() as conn:
        files = table('files')
        assert conn.execute(select(func.count()).select_from(files).where(files.c.owner_user_id == user['user_id'])).scalar_one() == 0
    assert object_store == {}

    assert client.post('/api/v1/files/pdf', headers=user['headers'],
                       json={'purpose': 'CV', 'content_base64': pdf_b64()}).status_code == 422
    assert client.post('/api/v1/files/pdf', headers=user['headers'],
                       json={'purpose': 'INSTITUTION_AGREEMENT'}).status_code == 422
    assert client.post('/api/v1/files/pdf', json={'purpose': 'INSTITUTION_AGREEMENT', 'content_base64': pdf_b64()}).status_code == 401
