"""Issue #247: a student reads their own class timetable; only MFA coordinators may rewrite it.

Rewriting the timetable resets every current VERIFIED student's work availability,
so it must not be open to any staff member, and a merely pending enrollment must
neither reveal the institution's schedule nor have its availability overwritten.
"""
from sqlalchemy import select

from app.db.storage import table, transaction
from test_enrollment_institution_review import pending, staff
from test_institution_recovery import verified_student

SLOTS = [
    {"group_code": "ENG-1", "program_name": "Engineering", "weekday": 1, "para_number": 1,
     "subject_name": "Oliy matematika", "lesson_type": "LECTURE", "room": "A-101", "teacher_name": "A. Karimov"},
    {"group_code": "ENG-1", "program_name": "Engineering", "weekday": 1, "para_number": 2,
     "subject_name": "Dasturlash asoslari", "lesson_type": "LAB", "room": "B-204"},
    {"group_code": "LAW-1", "program_name": "Law", "weekday": 2, "para_number": 1,
     "subject_name": "Konstitutsiyaviy huquq", "room": "C-3"},
]


def save(client, inst, user, slots=SLOTS):
    return client.put(f'/api/v1/institutions/{inst}/timetables', headers=user['headers'],
                      json={'mode': 'REPLACE', 'slots': slots, 'academic_semester': '2026-2027 kuzgi'})


def mine(client, user):
    r = client.get('/api/v1/me/timetable', headers=user['headers'])
    assert r.status_code == 200, r.text
    return r.json()


def rules_for(candidate_id):
    t = table('availability_rules')
    with transaction() as conn:
        return conn.execute(select(t.c.weekday, t.c.start_minute, t.c.end_minute)
                            .where(t.c.candidate_id == candidate_id)).all()


def test_verified_student_sees_only_their_group(client, identities):
    student, inst, coordinator, _ = verified_student(client, identities)
    assert mine(client, student)['status'] == 'TIMETABLE_NOT_PUBLISHED'

    saved = save(client, inst, coordinator)
    assert saved.status_code == 200, saved.text

    body = mine(client, student)
    assert body['status'] == 'OK'
    assert body['group_code'] == 'ENG-1' and body['matched_by'] == 'PROGRAM'
    assert body['academic_semester'] == '2026-2027 kuzgi'
    subjects = [s['subject_name'] for s in body['slots']]
    assert subjects == ['Oliy matematika', 'Dasturlash asoslari']
    assert all('group_code' not in s and 'id' not in s for s in body['slots'])
    assert body['slots'][0]['start_time'] == '08:30' and body['slots'][1]['lesson_type'] == 'LABORATORIYA'
    monday = next(d for d in body['free_windows'] if d['weekday'] == 1)
    assert monday['class_count'] == 2
    assert all(iv['start_minute'] >= 11 * 60 + 20 for iv in monday['free_intervals'])

    # The same windows were written to the student's availability.
    assert rules_for(student['candidate_id'])


def test_pending_student_gets_no_schedule_and_keeps_own_availability(client, identities):
    student, inst, _entry = pending(client, identities)
    coordinator = staff(identities, inst)
    assert save(client, inst, coordinator).status_code == 200
    assert mine(client, student)['status'] == 'NO_VERIFIED_ENROLLMENT'
    assert mine(client, student)['slots'] == []
    assert rules_for(student['candidate_id']) == []


def test_teacher_cannot_rewrite_the_timetable(client, identities):
    _student, inst, _coordinator, _ = verified_student(client, identities)
    teacher = staff(identities, inst, role='TEACHER')
    r = save(client, inst, teacher)
    assert r.status_code == 403, r.text
    imported = client.post(f'/api/v1/institutions/{inst}/timetables/import', headers=teacher['headers'],
                           json={'format': 'JSON', 'content': '[]'})
    assert imported.status_code == 403, imported.text
    # Reading stays available to staff.
    assert client.get(f'/api/v1/institutions/{inst}/timetables', headers=teacher['headers']).status_code == 200


def test_my_timetable_requires_a_session(client):
    assert client.get('/api/v1/me/timetable').status_code == 401
