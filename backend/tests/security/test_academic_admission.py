"""Actual academic HTTP intake; institutional/publication prerequisites are trusted metadata."""
from uuid import uuid4
import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError

from app.db.storage import table,transaction,now
from test_academic_authority import academic_fixture
from test_admission_lifecycle import terms_request
from test_internship_admission import post


def school_body(f):
    return dict(institution_id=f['inst']['id'],enrollment_id=f['enrollment']['id'],agreement_id=f['agreement']['id'],
                purpose='ACADEMIC_VIEW',legal_basis='Explicit current institution academic agreement.',idempotency_key=str(uuid4()))


def pending_http(client,identities,organization,*,choose=True):
    f=academic_fixture(identities,organization,make_supervision=False)
    if choose:
        post(client,'/api/v1/placements/'+f['placement']['id']+'/academic-requests',f['candidate'],
             {**terms_request(f['placement']),'enrollment_id':f['enrollment']['id']},201)
    f['supervision']=post(client,'/api/v1/student-supervisions',f['coord'],school_body(f),201)
    return f


def nominate(client,f):
    return post(client,'/api/v1/placements/'+f['placement']['id']+'/academic-assignments',f['coord'],dict(
        institution_id=f['inst']['id'],supervision_id=f['supervision']['id'],supervisor_id=f['teacher_member']['id'],idempotency_key=str(uuid4())),201)


def plan(client,f,who=None):
    response=client.get('/api/v1/placements/'+f['placement']['id']+'/plan',headers=(who or f['candidate'])['headers'])
    assert response.status_code==200,response.text
    return response.json()


def accept_candidate_mentor(client,f,p):
    base='/api/v1/placements/'+f['placement']['id']
    post(client,base+'/accept',f['candidate'],terms_request(p),200)
    mentor=post(client,base+'/mentor-assignments',f['owner'],dict(mentor_id=f['owner']['user_id'],idempotency_key=str(uuid4())),201)
    post(client,base+'/assignments/'+mentor['id']+'/accept',f['owner'],terms_request(p),200)


def test_actual_pending_school_and_teacher_http_flow_then_password_review(client,identities,organization):
    f=pending_http(client,identities,organization)
    assignment=nominate(client,f);p=plan(client,f)
    assert p['status']=='PLANNED' and p['version']==2 and p['academic_required'] is True
    assert p['academic_scope']=={'institution_id':f['inst']['id'],'purpose':'ACADEMIC_VIEW'}
    assert plan(client,f,f['teacher'])['terms_id']==p['terms_id']
    response=client.get('/api/v1/me/academic-assignments',headers=f['teacher']['headers'])
    assert response.status_code==200 and response.json()['items'][0]['id']==assignment['id'],response.text
    accept_candidate_mentor(client,f,p)
    base='/api/v1/placements/'+f['placement']['id']
    denied=client.post(base+'/host-decisions',headers=f['owner']['headers'],json={**terms_request(p),'action':'ACTIVATE'})
    assert denied.status_code==409,denied.text
    teacher_body={**terms_request(p),'assignment_kind':'TEACHER'}
    receipt=post(client,base+'/assignments/'+assignment['id']+'/accept',f['teacher'],teacher_body,200)
    assert receipt['side']=='TEACHER'
    assert post(client,base+'/assignments/'+assignment['id']+'/accept',f['teacher'],teacher_body,200)==receipt
    post(client,base+'/host-decisions',f['owner'],{**terms_request(p),'action':'ACTIVATE'},200)
    assert plan(client,f)['status']=='ACTIVE'
    draft=client.put(base+'/logs/'+p['start_date'],headers=f['candidate']['headers'],json={
        'day_type':'WORKED','summary_text':'Actual academic work result','total_minutes':60})
    assert draft.status_code==200,draft.text
    post(client,'/api/v1/logs/'+draft.json()['id']+'/submit',f['candidate'],{},200)
    post(client,'/api/v1/internship-logs/daily-logs/'+draft.json()['id']+'/academic-reviews',f['teacher'],dict(
        placement_id=f['placement']['id'],academic_assignment_id=assignment['id'],decision='REVIEWED',comment='Actual academic review.',
        expected_revision_id=draft.json()['current_revision_id'],idempotency_key=str(uuid4())),201)
    with transaction() as conn:
        assert conn.execute(select(table('sessions').c.assurance).where(table('sessions').c.id==f['teacher']['session_id'])).scalar_one()=='PASSWORD'
        assert conn.execute(text('SELECT count(*) FROM flexbridge.academic_assignment_consents')).scalar_one()==1
        assert conn.execute(text('SELECT count(*) FROM flexbridge.academic_log_reviews')).scalar_one()==1


def test_coordinator_cannot_capture_pending_school_without_student_choice(client,identities,organization):
    f=pending_http(client,identities,organization,choose=False)
    body=dict(institution_id=f['inst']['id'],supervision_id=f['supervision']['id'],supervisor_id=f['teacher_member']['id'],idempotency_key=str(uuid4()))
    response=client.post('/api/v1/placements/'+f['placement']['id']+'/academic-assignments',headers=f['coord']['headers'],json=body)
    assert response.status_code==403 and response.json()['detail']['code']=='STUDENT_SCHOOL_CHOICE_REQUIRED',response.text
    with transaction() as conn:
        assert conn.execute(select(table('placement_academic_bindings').c.placement_id)).first() is None
        assert conn.execute(select(table('academic_assignments').c.id)).first() is None
        assert conn.execute(text('SELECT count(*) FROM flexbridge.placement_terms')).scalar_one()==1


def test_foreign_actor_cannot_select_students_verified_enrollment(client,identities,organization):
    f=academic_fixture(identities,organization,make_supervision=False)
    response=client.post('/api/v1/placements/'+f['placement']['id']+'/academic-requests',headers=f['teacher']['headers'],
        json={**terms_request(f['placement']),'enrollment_id':f['enrollment']['id']})
    assert response.status_code==403,response.text
    with transaction() as conn:assert conn.execute(select(table('student_academic_requests').c.id)).first() is None


def test_binding_replaces_pre_school_plan_and_old_acceptance_cannot_approve_new_scope(client,identities,organization):
    f=pending_http(client,identities,organization)
    old=plan(client,f)
    post(client,'/api/v1/placements/'+f['placement']['id']+'/accept',f['candidate'],terms_request(old),200)
    nominate(client,f);current=plan(client,f)
    assert current['terms_id']!=old['terms_id'] and current['version']==old['version']+1
    response=client.post('/api/v1/placements/'+f['placement']['id']+'/accept',headers=f['candidate']['headers'],json=terms_request(old))
    assert response.status_code==409,response.text
    with transaction() as conn:
        assert conn.execute(text('SELECT candidate_accepted_at FROM flexbridge.placement_terms WHERE id=:id'),{'id':current['terms_id']}).scalar_one() is None


def test_teacher_acceptance_and_membership_cannot_be_forged_in_sql(client,identities,organization):
    f=pending_http(client,identities,organization);assignment=nominate(client,f)
    for fields in ({'accepted_at':now()},{'teacher_membership_id':f['member']['id']}):
        with pytest.raises(IntegrityError),transaction() as conn:
            conn.execute(table('academic_assignments').update().where(table('academic_assignments').c.id==assignment['id']).values(**fields))
    with transaction() as conn:assert conn.execute(select(table('academic_assignment_consents').c.id)).first() is None
