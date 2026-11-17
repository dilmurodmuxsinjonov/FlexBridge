"""Issue #237: a student without MFA recovers access with the university's vouching.

OTP alone still never resets a password. The independent factor is an approval
by a current MFA coordinator of an institution where the student holds a current
VERIFIED enrollment; it is bound to the same contact, single use and time-limited.
"""
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from app.db.storage import now, table, transaction
from test_enrollment_institution_review import REASON, base, pending, staff
from test_iam import delivery, proof  # noqa: F401  (pytest fixture import)
from test_invitations import contact

NEW_PASSWORD = 'recovered-by-university-2026'


def verified_student(client, identities):
    student, inst, entry = pending(client, identities)
    coordinator = staff(identities, inst)
    case = base(inst) + '/' + entry['case_id']
    assert client.post(case + '/claim', headers=coordinator['headers']).status_code == 200
    decided = client.post(case + '/decision', headers=coordinator['headers'],
                          json={'decision': 'APPROVE', 'expected_revision': 1, 'reason': REASON})
    assert decided.status_code == 200, decided.text
    email = str(uuid4()) + '@student.test'
    contact(student, value=email, channel='EMAIL')
    return student, inst, coordinator, email


def otp_only_request(client, delivery, email):
    token = proof(client, delivery, purpose='RECOVERY', destination=email, channel='EMAIL')
    r = client.post('/api/v1/auth/recovery', json={'verification_token': token})
    assert r.status_code == 202, r.text
    assert r.json()['status'] == 'PENDING_REVIEW' and 'reset_token' not in r.json()
    return r.json()


def queue(client, inst, user):
    return client.get(f'/api/v1/institutions/{inst}/recovery-requests', headers=user['headers'])


def decide(client, inst, user, rid, decision='APPROVE'):
    return client.post(f'/api/v1/institutions/{inst}/recovery-requests/{rid}/decide', headers=user['headers'],
                       json={'decision': decision, 'reason': 'Student identity confirmed in person at the dean office'})


def age_challenges():
    with transaction() as conn:
        conn.execute(table('auth_challenges').update().values(created_at=now() - timedelta(seconds=61)))


def test_coordinator_approval_lets_the_student_reset_once(client, identities, delivery):
    student, inst, coordinator, email = verified_student(client, identities)
    request = otp_only_request(client, delivery, email)

    listed = queue(client, inst, coordinator)
    assert listed.status_code == 200, listed.text
    [item] = listed.json()['items']
    assert item['id'] == request['recovery_id'] and item['student_name']
    assert item['contacts'][0]['channel'] == 'EMAIL' and '***' in item['contacts'][0]['masked']
    assert email not in listed.text

    approved = decide(client, inst, coordinator, request['recovery_id'])
    assert approved.status_code == 200, approved.text
    assert approved.json()['status'] == 'APPROVED' and approved.json()['valid_until']
    assert queue(client, inst, coordinator).json()['items'] == []
    assert decide(client, inst, coordinator, request['recovery_id']).status_code == 404  # already decided

    # The student restarts with the same contact: now READY_TO_RESET without TOTP/backup code.
    age_challenges()
    token = proof(client, delivery, purpose='RECOVERY', destination=email, channel='EMAIL')
    ready = client.post('/api/v1/auth/recovery', json={'verification_token': token})
    assert ready.status_code == 202, ready.text
    assert ready.json()['status'] == 'READY_TO_RESET' and ready.json()['reset_token']
    done = client.post(f"/api/v1/auth/recovery/{ready.json()['recovery_id']}/complete",
                       json={'reset_token': ready.json()['reset_token'], 'new_password': NEW_PASSWORD})
    assert done.status_code == 200, done.text
    assert client.post('/api/v1/auth/login', json={'user_id': student['user_id'], 'password': NEW_PASSWORD}).status_code == 200
    assert client.get('/api/v1/auth/me', headers=student['headers']).status_code == 401  # old sessions revoked

    # Single use: a third attempt goes back to review.
    age_challenges()
    again = otp_only_request(client, delivery, email)
    assert again['status'] == 'PENDING_REVIEW'
    with transaction() as conn:
        r = table('recovery_requests')
        status = conn.execute(select(r.c.status).where(r.c.id == request['recovery_id'])).scalar_one()
    assert status == 'CONSUMED'


def test_only_the_students_own_institution_coordinator_can_decide(client, identities, delivery):
    student, inst, coordinator, email = verified_student(client, identities)
    request = otp_only_request(client, delivery, email)

    _, other_inst, _ = pending(client, identities)
    outsider = staff(identities, other_inst)
    assert queue(client, other_inst, outsider).json()['items'] == []
    assert decide(client, other_inst, outsider, request['recovery_id']).status_code == 404
    assert queue(client, inst, outsider).status_code == 403
    assert decide(client, inst, outsider, request['recovery_id']).status_code == 403

    teacher = staff(identities, inst, role='TEACHER')
    assert queue(client, inst, teacher).status_code == 403
    assert decide(client, inst, student, request['recovery_id']).status_code == 403
    assert client.get(f'/api/v1/institutions/{inst}/recovery-requests').status_code == 401

    rejected = decide(client, inst, coordinator, request['recovery_id'], decision='REJECT')
    assert rejected.status_code == 200 and rejected.json()['status'] == 'REJECTED'
    age_challenges()
    assert otp_only_request(client, delivery, email)['status'] == 'PENDING_REVIEW'


def test_approval_is_bound_to_the_contact_and_expires(client, identities, delivery):
    student, inst, coordinator, email = verified_student(client, identities)
    request = otp_only_request(client, delivery, email)
    assert decide(client, inst, coordinator, request['recovery_id']).status_code == 200

    # A different verified contact of the same student does not inherit the approval.
    other = str(uuid4()) + '@student.test'
    contact(student, value=other, channel='EMAIL')
    assert otp_only_request(client, delivery, other)['status'] == 'PENDING_REVIEW'

    # After 72 hours the approval no longer counts.
    with transaction() as conn:
        r = table('recovery_requests')
        conn.execute(r.update().where(r.c.id == request['recovery_id']).values(resolved_at=now() - timedelta(hours=73)))
    age_challenges()
    assert otp_only_request(client, delivery, email)['status'] == 'PENDING_REVIEW'


def test_reason_is_required(client, identities, delivery):
    student, inst, coordinator, email = verified_student(client, identities)
    request = otp_only_request(client, delivery, email)
    short = client.post(f"/api/v1/institutions/{inst}/recovery-requests/{request['recovery_id']}/decide",
                        headers=coordinator['headers'], json={'decision': 'APPROVE', 'reason': 'ok'})
    assert short.status_code == 422
