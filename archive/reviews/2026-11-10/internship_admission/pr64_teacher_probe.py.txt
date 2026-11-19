"""Final unchanged-source acceptance control: formally appointed teacher, PASSWORD."""
from datetime import date,timedelta
from uuid import uuid4
from sqlalchemy import select
from app.core.iam_security import SENSITIVE_ROLES
from app.db.storage import table,transaction
from test_candidate import cv_fixture
from test_institution_onboarding import active_coordinator,staff_claim,accept,claim,decide


def test_formal_teacher_password_keeps_complete_own_enrollment_lifecycle(client,identities):
    institution=active_coordinator(client,identities);teacher=identities()
    appointment,contact,_=staff_claim(client,institution,teacher)
    assert accept(client,institution,appointment['id'],user=teacher,contact_id=contact['id']).status_code==200
    assert claim(client,institution['moderator'],appointment['case_id']).status_code==200
    assert decide(client,institution['moderator'],appointment['case_id']).status_code==200
    me=client.get('/api/v1/auth/me',headers=teacher['headers'])
    assert me.status_code==200 and 'TEACHER' in me.json()['roles']
    assert not SENSITIVE_ROLES.intersection(me.json()['roles'])
    with transaction() as conn:
        assert conn.execute(select(table('sessions').c.assurance).where(table('sessions').c.id==teacher['session_id'])).scalar_one()=='PASSWORD'
    body={'institution_id':appointment['institution_id'],'program':'Continuing education',
          'start_date':(date.today()-timedelta(days=30)).isoformat(),'idempotency_key':str(uuid4())}
    created=client.post('/api/v1/me/enrollments',headers=teacher['headers'],json=body)
    assert created.status_code==201,created.text
    entry=created.json();url='/api/v1/me/enrollments/'+entry['id']
    assert client.get('/api/v1/me/enrollments',headers=teacher['headers']).status_code==200
    assert client.get(url,headers=teacher['headers']).status_code==200
    document=cv_fixture(teacher)
    submitted=client.post(url+'/verification',headers=teacher['headers'],json={
        'expected_revision':1,'program':body['program'],'start_date':body['start_date'],
        'file_ids':[document['id']],'evidence_note':'Independent verification of teacher own enrollment.'})
    assert submitted.status_code==202 and submitted.json()['revision']==2,submitted.text
    case=entry['case_id'];moderator=institution['moderator']
    assigned=client.post('/api/v1/operator/verification-cases/'+case+'/claim',headers=moderator['headers'])
    assert assigned.status_code==200,assigned.text
    reviewed=client.post('/api/v1/operator/verification-cases/'+case+'/decide',headers=moderator['headers'],json={
        'decision':'APPROVE','expected_revision':2,'reason':'Independent exact revision review of this own enrollment.'})
    assert reviewed.status_code==200,reviewed.text
    assert client.get(url,headers=teacher['headers']).json()['current_student'] is True
    ended=client.post(url+'/end',headers=teacher['headers'],json={
        'idempotency_key':str(uuid4()),'reason':'End only this enrollment while keeping the teaching role.'})
    assert ended.status_code==200,ended.text
    assert client.get(url,headers=teacher['headers']).json()['current_student'] is False
    assert 'TEACHER' in client.get('/api/v1/auth/me',headers=teacher['headers']).json()['roles']
