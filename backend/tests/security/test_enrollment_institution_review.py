"""0022: the student's own university coordinator may review enrollment (until HEMIS).

Kept invariants: never the requester, claim before decision, MFA session,
current-institution scope enforced by the service *and* by the DB guard.
"""
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.institution_scope import TASHKENT
from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_candidate import cv_fixture
from test_enrollment_migration import new_institution
from test_enrollments import create, enrollment_body
from test_organizations import mfa_user

REASON = 'Checked against the dean office student register.'


def staff(identities, institution_id, role='COORDINATOR', *, appointment_status='ACTIVE'):
    user = mfa_user(identities)
    file = cv_fixture(user)
    today = now().astimezone(TASHKENT).date()
    with transaction() as conn:
        member = insert_row(conn, 'institution_memberships', institution_id=institution_id, user_id=user['user_id'],
                            status='ACTIVE', accepted_at=now())
        appointment = insert_row(conn, 'institution_appointments', institution_id=institution_id, user_id=user['user_id'],
                                 document_file_id=file['id'], status=appointment_status, valid_from=today - timedelta(days=30),
                                 valid_to=today + timedelta(days=30), accepted_at=now())
        roles = table('role_catalog')
        rid = conn.execute(select(roles.c.id).where(roles.c.code == role, roles.c.scope_kind == 'INSTITUTION')).scalar_one_or_none()
        if not rid:
            rid = insert_row(conn, 'role_catalog', code=role, scope_kind='INSTITUTION', description='Test institution staff')['id']
        insert_row(conn, 'institution_role_grants', membership_id=member['id'], role_id=rid, appointment_id=appointment['id'])
    return user


def pending(client, identities):
    student = identities()
    body, _ = enrollment_body(student, files=True)
    entry = create(client, student, body)
    assert entry['status'] == 'PENDING'
    return student, body['institution_id'], entry


def base(inst):
    return f'/api/v1/institutions/{inst}/enrollment-requests'


def test_coordinator_reviews_own_institution_student(client, identities):
    student, inst, entry = pending(client, identities)
    coordinator = staff(identities, inst)

    queue = client.get(base(inst), headers=coordinator['headers'])
    assert queue.status_code == 200, queue.text
    [item] = queue.json()['items']
    assert item['case_id'] == entry['case_id'] and item['program'] == 'Engineering'
    assert item['student_name'] and item['assigned_to_me'] is False

    case = base(inst) + '/' + entry['case_id']
    assert client.post(case + '/claim', headers=coordinator['headers']).status_code == 200
    detail = client.get(case, headers=coordinator['headers'])
    assert detail.status_code == 200, detail.text
    assert detail.json()['submissions'][0]['files'][0]['download_path'].startswith(base(inst) + '/')

    decided = client.post(case + '/decision', headers=coordinator['headers'],
                          json={'decision': 'APPROVE', 'expected_revision': 1, 'reason': REASON})
    assert decided.status_code == 200, decided.text
    assert decided.json()['case_status'] == 'APPROVED'

    current = client.get('/api/v1/me/enrollments/' + entry['id'], headers=student['headers']).json()
    assert current['current_student'] is True
    with transaction() as conn:
        events = table('enrollment_events')
        row = conn.execute(select(events.c.platform_grant_id, events.c.institution_grant_id)
                           .where(events.c.case_id == entry['case_id'], events.c.action == 'APPROVE')).one()
    assert row.platform_grant_id is None and row.institution_grant_id is not None


def test_other_institution_and_teacher_cannot_review(client, identities):
    _, inst, entry = pending(client, identities)
    with transaction() as conn:
        other_inst = new_institution(conn)['id']
    outsider = staff(identities, other_inst)
    teacher = staff(identities, inst, 'TEACHER')

    assert client.get(base(other_inst), headers=outsider['headers']).json()['items'] == []
    assert client.post(base(other_inst) + '/' + entry['case_id'] + '/claim', headers=outsider['headers']).status_code == 404
    # The operator path re-checks authority against the enrollment's own institution.
    assert client.post('/api/v1/operator/verification-cases/' + entry['case_id'] + '/claim',
                       headers=outsider['headers']).status_code == 403
    assert client.get(base(inst), headers=teacher['headers']).status_code == 403
    assert client.post(base(inst) + '/' + entry['case_id'] + '/claim', headers=teacher['headers']).status_code == 403


def test_expired_appointment_loses_review_authority(client, identities):
    _, inst, entry = pending(client, identities)
    coordinator = staff(identities, inst, appointment_status='REVOKED')
    assert client.get(base(inst), headers=coordinator['headers']).status_code == 403
    assert client.post(base(inst) + '/' + entry['case_id'] + '/claim', headers=coordinator['headers']).status_code == 403


def test_coordinator_cannot_review_own_request(client, identities):
    with transaction() as conn:
        inst = new_institution(conn)['id']
    coordinator = staff(identities, inst)
    body, _ = enrollment_body(coordinator, files=True)
    body['institution_id'] = inst
    entry = create(client, coordinator, body)
    assert all(i['case_id'] != entry['case_id'] for i in client.get(base(inst), headers=coordinator['headers']).json()['items'])
    response = client.post(base(inst) + '/' + entry['case_id'] + '/claim', headers=coordinator['headers'])
    assert response.status_code == 403 and 'SELF_REVIEW_FORBIDDEN' in response.text


def test_db_guard_rejects_institution_proof_for_another_institution(client, identities):
    """The 0022 trigger checks the grant independently of the service."""
    from app.db.storage import get_engine
    _, inst, entry = pending(client, identities)
    with transaction() as conn:
        other_inst = new_institution(conn)['id']
    outsider = staff(identities, other_inst)
    with transaction() as conn:
        grants, members = table('institution_role_grants'), table('institution_memberships')
        grant_id = conn.execute(select(grants.c.id).join(members, members.c.id == grants.c.membership_id)
                                .where(members.c.user_id == outsider['user_id'])).scalar_one()
        version = conn.execute(select(table('users').c.auth_version).where(table('users').c.id == outsider['user_id'])).scalar_one()
    with pytest.raises(Exception, match='reviewer authority invalid'):
        with get_engine().begin() as conn:
            conn.execute(table('enrollment_events').insert().values(
                id=str(uuid4()), enrollment_id=entry['id'], case_id=entry['case_id'], revision=1, action='CLAIM',
                actor_id=outsider['user_id'], session_id=outsider['session_id'], auth_version=version,
                institution_grant_id=grant_id, reason='Forged claim from a different institution.'))


def test_moderator_flow_unchanged(client, identities):
    _, _, entry = pending(client, identities)
    moderator = identities('MODERATOR')
    assert client.post('/api/v1/operator/verification-cases/' + entry['case_id'] + '/claim',
                       headers=moderator['headers']).status_code == 200
    with transaction() as conn:
        events = table('enrollment_events')
        row = conn.execute(select(events.c.platform_grant_id, events.c.institution_grant_id)
                           .where(events.c.case_id == entry['case_id'], events.c.action == 'CLAIM')).one()
    assert row.platform_grant_id is not None and row.institution_grant_id is None
