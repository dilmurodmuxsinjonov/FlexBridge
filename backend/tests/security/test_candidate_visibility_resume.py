"""Candidate search consent and the resume employers actually see.

Before: every profile was PRIVATE with no way to change it, so employer search
never listed real students; employers saw no resume sections; a skill counted
as "verified" whenever any verification case was linked.
"""
from sqlalchemy import select

from app.db.storage import table, transaction

RESUME = {
    'work_experiences': [{
        'company_name': 'Uzinfocom', 'position': 'Backend intern', 'work_type': 'PROJECT',
        'start_date': '2025-09-01', 'is_current': True, 'responsibilities': 'API ishlab chiqish',
        'location': 'Toshkent', 'technologies': ['Python', 'PostgreSQL'],
    }],
    'languages': [{'language_name': "O'zbek tili", 'level': 'NATIVE'},
                  {'language_name': 'Ingliz tili', 'level': 'C1', 'certificate_score': 'IELTS 7.5'}],
    'education_details': {'faculty': 'Kompyuter injiniringi', 'study_year': '3', 'gpa': '4.6',
                          'university_name': 'TATU', 'major': 'Dasturiy injiniring',
                          'degree_level': 'BAKALAVR', 'thesis_topic': 'Smenali jadval algoritmi'},
    'career_preferences': {'preferred_work_mode': 'HYBRID', 'career_objective': 'Backend dasturchi bo‘lish',
                           'desired_roles': ['Backend intern', 'Data analyst'], 'preferred_weekly_hours': 25,
                           'telegram_username': '@private_handle', 'github_url': 'https://github.com/student'},
}


def detail(client, employer, candidate_id):
    return client.get(f'/api/v1/employer/candidates/{candidate_id}', headers=employer['headers'])


def test_visibility_consent_controls_employer_access(client, identities, organization):
    student = identities()
    employer = identities('HR', organization)
    assert detail(client, employer, student['candidate_id']).status_code == 404

    opened = client.put('/api/v1/me/candidate/visibility', headers=student['headers'], json={'visibility': 'EMPLOYERS'})
    assert opened.status_code == 200, opened.text
    assert opened.json()['visibility'] == 'EMPLOYERS'
    assert detail(client, employer, student['candidate_id']).status_code == 200

    closed = client.put('/api/v1/me/candidate/visibility', headers=student['headers'], json={'visibility': 'PRIVATE'})
    assert closed.status_code == 200 and closed.json()['visibility'] == 'PRIVATE'
    assert detail(client, employer, student['candidate_id']).status_code == 404

    with transaction() as conn:
        events = table('audit_events')
        actions = conn.execute(select(events.c.action).where(events.c.actor_id == student['user_id'])).scalars().all()
    assert actions.count('CANDIDATE_VISIBILITY_CHANGED') == 2


def test_visibility_rejects_other_values_and_patch_still_forbidden(client, identities):
    student = identities()
    assert client.put('/api/v1/me/candidate/visibility', headers=student['headers'],
                      json={'visibility': 'PUBLIC'}).status_code == 422
    assert client.patch('/api/v1/me/candidate', headers=student['headers'],
                        json={'visibility': 'EMPLOYERS'}).status_code == 422
    assert client.put('/api/v1/me/candidate/visibility', json={'visibility': 'EMPLOYERS'}).status_code == 401


def test_resume_extra_fields_round_trip(client, identities):
    student = identities()
    saved = client.put('/api/v1/me/candidate/resume-details', headers=student['headers'], json=RESUME)
    assert saved.status_code == 200, saved.text
    body = client.get('/api/v1/me/candidate/resume-details', headers=student['headers']).json()
    work = body['work_experiences'][0]
    assert work['work_type'] == 'PROJECT' and work['location'] == 'Toshkent'
    assert work['technologies'] == ['Python', 'PostgreSQL']
    assert body['languages'][0]['level'] == 'NATIVE'
    assert body['education_details']['university_name'] == 'TATU'
    assert body['education_details']['thesis_topic'] == 'Smenali jadval algoritmi'
    assert body['career_preferences']['desired_roles'] == ['Backend intern', 'Data analyst']
    assert body['career_preferences']['preferred_weekly_hours'] == 25


def test_employer_sees_resume_without_personal_contacts(client, identities, organization):
    student = identities()
    employer = identities('OWNER', organization)
    client.put('/api/v1/me/candidate/resume-details', headers=student['headers'], json=RESUME)
    client.put('/api/v1/me/candidate/visibility', headers=student['headers'], json={'visibility': 'EMPLOYERS'})

    response = detail(client, employer, student['candidate_id'])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['student_verified'] is False
    resume = data['resume']
    assert resume['work_experiences'][0]['position'] == 'Backend intern'
    assert [l['level'] for l in resume['languages']] == ['NATIVE', 'C1']
    assert resume['career_preferences']['github_url'] == 'https://github.com/student'
    assert 'telegram_username' not in resume['career_preferences']
    assert '@private_handle' not in response.text
