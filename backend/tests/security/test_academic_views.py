"""Actual scoped institutional list/queue HTTP; institutional metadata remains trusted setup."""
from uuid import uuid4

from sqlalchemy import select

from app.db.storage import table,transaction
from app.services.enrollments import enrollment_service
from app.db.institution_scope import TASHKENT
from app.db.storage import now
from datetime import timedelta
from test_academic_admission import pending_http,nominate,plan,accept_candidate_mentor
from test_academic_lifecycle import teacher_accept
from test_admission_lifecycle import terms_request,publish
from test_internship_admission import post
from test_organizations import actor


def get(client,path,user,**params):
    response=client.get('/api/v1/'+path,headers=user['headers'],params=params)
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='no-store'
    return response.json()


def active_revision(client,f):
    a=nominate(client,f);p=plan(client,f)
    accept_candidate_mentor(client,f,p)
    _,_,response=teacher_accept(client,f,a,p);assert response.status_code==200,response.text
    base='/api/v1/placements/'+f['placement']['id']
    post(client,base+'/host-decisions',f['owner'],{**terms_request(p),'action':'ACTIVATE'},200)
    response=client.put(base+'/logs/'+p['start_date'],headers=f['candidate']['headers'],json={
        'day_type':'WORKED','summary_text':'Private academic work summary','total_minutes':60})
    assert response.status_code==200,response.text
    return a,response.json()


def test_own_coordinator_lists_exact_scope_and_reachable_assignment_options(client,identities,organization):
    f=pending_http(client,identities,organization);prefix='institutions/'+f['inst']['id']
    rows=get(client,prefix+'/supervisions',f['coord'])['items'];assert len(rows)==1
    assert rows[0]['id']==f['supervision']['id'] and rows[0]['enrollment_id']==f['enrollment']['id']
    assert get(client,prefix+'/supervisions',f['coord'],purpose='OTHER_PURPOSE')['items']==[]
    assert get(client,prefix+'/supervisions',f['teacher'])['items']==[]
    queued=get(client,prefix+'/assignment-queue',f['coord']);assert len(queued['items'])==1
    assert queued['items'][0]['placement_id']==f['placement']['id']
    agreements=get(client,prefix+'/academic-agreements',f['coord'])['items']
    teachers=get(client,prefix+'/academic-teachers',f['coord'])['items']
    assert agreements[0]['id']==f['agreement']['id'] and teachers[0]['id']==f['teacher_member']['id']
    assert not {'signed_file_id','legal_basis','file_ids','student_ref_digest','application_id','salary_min'} & set(agreements[0])
    assigned=nominate(client,f)
    assert get(client,prefix+'/assignment-queue',f['coord'])['items']==[]
    rows=get(client,'student-supervisions/'+f['supervision']['id']+'/academic-assignments',f['coord'])['items']
    assert rows[0]['id']==assigned['id'] and rows[0]['placement_id']==f['placement']['id']
    assert rows[0]['current_terms_id']==assigned['assignment_receipt']['terms_id']


def test_personally_accepted_teacher_can_see_own_pending_supervision_before_host_start(client,identities,organization):
    f=pending_http(client,identities,organization);a=nominate(client,f);p=plan(client,f)
    _,_,response=teacher_accept(client,f,a,p);assert response.status_code==200,response.text
    assert p['status']=='PLANNED'
    rows=get(client,'institutions/'+f['inst']['id']+'/supervisions',f['teacher'])['items']
    assert rows[0]['id']==f['supervision']['id']
    own=get(client,'student-supervisions/'+f['supervision']['id']+'/academic-assignments',f['teacher'])['items']
    assert own[0]['id']==a['id']


def test_plan_changed_after_school_choice_requires_fresh_choice_in_queue_and_nomination(client,identities,organization):
    f=pending_http(client,identities,organization);base='/api/v1/placements/'+f['placement']['id']
    current=publish(client,f['owner'],f['placement'])
    assert get(client,'institutions/'+f['inst']['id']+'/assignment-queue',f['coord'])['items']==[]
    response=client.post(base+'/academic-assignments',headers=f['coord']['headers'],json=dict(institution_id=f['inst']['id'],
        supervision_id=f['supervision']['id'],supervisor_id=f['teacher_member']['id'],idempotency_key=str(uuid4())))
    assert response.status_code==409 and response.json()['detail']['code']=='STALE_STUDENT_SCHOOL_CHOICE',response.text
    with transaction() as conn:assert conn.execute(select(table('placement_academic_bindings'))).first() is None
    post(client,base+'/academic-requests',f['candidate'],{**terms_request(current),'enrollment_id':f['enrollment']['id']},201)
    assert len(get(client,'institutions/'+f['inst']['id']+'/assignment-queue',f['coord'])['items'])==1
    nominee=nominate(client,f);assert nominee['assignment_receipt']['version']==current['version']+1


def test_review_queue_requires_actual_submitted_revision_and_current_named_scope(client,identities,organization):
    f=pending_http(client,identities,organization)
    assert get(client,'me/academic-review-queue',f['teacher'])['items']==[]
    a,draft=active_revision(client,f)
    assert get(client,'me/academic-review-queue',f['teacher'])['items']==[]
    post(client,'/api/v1/logs/'+draft['id']+'/submit',f['candidate'],{},200)
    for user in (f['teacher'],f['coord']):
        rows=get(client,'me/academic-review-queue',user)['items'];assert len(rows)==1
        assert rows[0]['id']==draft['current_revision_id'] and rows[0]['daily_log_id']==draft['id']
        assert not {'summary','summary_text','total_minutes','legal_basis','file_ids','application_id','salary_min'} & rows[0].keys()
    assert get(client,'me/academic-review-queue',f['candidate'])['items']==[]
    post(client,'/api/v1/academic-assignments/'+a['id']+'/revoke',f['coord'],{'idempotency_key':str(uuid4())},200)
    assert get(client,'me/academic-review-queue',f['teacher'])['items']==[]
    assert len(get(client,'me/academic-review-queue',f['coord'])['items'])==1
    enrollment_service.end_own(actor(f['candidate']),f['enrollment']['id'],idempotency_key=str(uuid4()),
        reason='Student ended this enrollment.',effective_end_date=now().astimezone(TASHKENT).date()-timedelta(days=1))
    assert get(client,'me/academic-review-queue',f['coord'])['items']==[]


def test_current_teacher_password_can_list_only_personally_accepted_supervision(client,identities,organization):
    f=pending_http(client,identities,organization);prefix='institutions/'+f['inst']['id']
    active_revision(client,f)
    assert get(client,prefix+'/supervisions',f['teacher'])['items'][0]['id']==f['supervision']['id']
    response=client.get('/api/v1/'+prefix+'/assignment-queue',headers=f['teacher']['headers'])
    assert response.status_code==403,response.text
