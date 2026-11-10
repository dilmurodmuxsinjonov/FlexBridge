"""Academic guards with actual-session supervision, nomination, personal acceptance and start.

Institution/appointment/agreement/publication metadata is trusted setup. Enrollment
uses independent review; new school/teacher/host admission uses real services.
Dedicated test_academic_admission exercises the new HTTP boundaries.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta
from threading import Event
from uuid import uuid4
import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import ActorContext
from app.db.storage import get_engine,table,transaction,now
from app.services.internship_logs import internship_log_service as service
from app.services.placements import insert_row,placement_service,get_row
from app.services.opportunities import opportunity_service
from test_candidate import cv_fixture
from test_institution_authority import setup_scope
from test_organizations import actor
from test_regressions import count
from test_org_authority_transactions import wait_for_blocker
from app.services.enrollments import enrollment_service
from app.services.academic_admission import academic_service
from app.services.placement_admission import admission_service
from app.db.institution_scope import TASHKENT


CREATE_PATHS=('/api/v1/internships/academic-assignments','/api/v1/internship-logs/academic-assignments')


def academic_fixture(identities,organization,*,enrollment_end_date=None,make_supervision=True,candidate_is_coordinator=False):
    coord,_,inst,_,member,appointment,grant=setup_scope(identities)
    teacher=identities();candidate=coord if candidate_is_coordinator else identities();owner=identities('OWNER',organization)
    file=cv_fixture(teacher);today=now().astimezone(TASHKENT).date()
    enrollment_file=cv_fixture(candidate);reviewer=identities('MODERATOR')
    request=enrollment_service.create(actor(candidate),institution_id=inst['id'],idempotency_key=str(uuid4()),
        program='Engineering',start_date=today-timedelta(days=30),end_date=enrollment_end_date,file_ids=[enrollment_file['id']],
        evidence_note='Independent enrollment evidence for this academic fixture.')
    enrollment_service.claim(actor(reviewer),request['case_id'])
    enrollment_service.decide(actor(reviewer),request['case_id'],decision='APPROVE',expected_revision=1,
        reason='Independent review of this academic enrollment fixture.')
    with transaction() as conn:
        tm=insert_row(conn,'institution_memberships',institution_id=inst['id'],user_id=teacher['user_id'],status='ACTIVE',accepted_at=now())
        ta=insert_row(conn,'institution_appointments',institution_id=inst['id'],user_id=teacher['user_id'],document_file_id=file['id'],status='ACTIVE',
            valid_from=today-timedelta(days=30),valid_to=today+timedelta(days=30),accepted_at=now())
        roles=table('role_catalog');rid=conn.execute(select(roles.c.id).where(roles.c.code=='TEACHER',roles.c.scope_kind=='INSTITUTION')).scalar_one_or_none()
        if not rid:rid=insert_row(conn,'role_catalog',code='TEACHER',scope_kind='INSTITUTION',description='Trusted teacher fixture')['id']
        tg=insert_row(conn,'institution_role_grants',membership_id=tm['id'],role_id=rid,appointment_id=ta['id'])
        en=get_row(conn,'enrollments',request['id'])
        agreement=insert_row(conn,'institution_agreements',institution_id=inst['id'],version=1,status='ACTIVE',valid_from=today-timedelta(days=30),purposes=['ACADEMIC_VIEW'])
        rid=conn.execute(select(roles.c.id).where(roles.c.code=='MENTOR',roles.c.scope_kind=='ORG')).scalar_one_or_none()
        if not rid:rid=insert_row(conn,'role_catalog',code='MENTOR',scope_kind='ORG',description='Trusted host mentor prerequisite')['id']
        members=table('org_memberships')
        owner_member=conn.execute(select(members.c.id).where(members.c.user_id==owner['user_id'],members.c.organization_id==organization)).scalar_one()
        insert_row(conn,'org_role_grants',membership_id=owner_member,role_id=rid,granted_by_id=owner['user_id'])
    supervision=None
    if make_supervision:
        supervision=academic_service.create_supervision(actor(coord),institution_id=inst['id'],enrollment_id=en['id'],
            agreement_id=agreement['id'],purpose='ACADEMIC_VIEW',legal_basis='Explicit fixture academic agreement basis.',idempotency_key=str(uuid4()))
    rev=opportunity_service.create_opportunity_revision(organization_id=organization,title='Academic internship',opportunity_kind='ACADEMIC_INTERNSHIP',
        contract_type='UNPAID_ACADEMIC_INTERNSHIP_AGREEMENT',compensation_type='UNPAID_ACADEMIC',actor_user_id=owner['user_id'])
    with transaction() as conn:
        conn.execute(table('opportunities').update().where(table('opportunities').c.id==rev['opportunity_id']).values(status='PUBLISHED'))
        conn.execute(table('opportunity_revisions').update().where(table('opportunity_revisions').c.id==rev['id']).values(eligibility='ENROLLED'))
    app=placement_service.create_application(opportunity_id=rev['opportunity_id'],candidate_id=candidate['candidate_id'],actor_user_id=candidate['user_id'])
    placement_service.create_application_attempt(application_id=app['id'],opportunity_id=rev['opportunity_id'],actor_user_id=candidate['user_id'])
    offer=placement_service.create_offer(application_id=app['id'],opportunity_id=rev['opportunity_id'],candidate_id=candidate['candidate_id'],offered_by=owner['user_id'])
    placement_service.respond_to_offer_api_043(offer_id=offer['id'],candidate_id=candidate['candidate_id'],decision='ACCEPT')
    p=placement_service.create_placement(application_id=app['id'],offer_id=offer['id'],opportunity_id=rev['opportunity_id'],candidate_id=candidate['candidate_id'],organization_id=organization,actor=actor(owner),idempotency_key=str(uuid4()))
    if make_supervision:
        academic_service.request_student(actor=actor(candidate),placement_id=p['id'],enrollment_id=en['id'],
            terms_id=p['current_terms_id'],version=1,idempotency_key=str(uuid4()))
    return dict(coord=coord,teacher=teacher,candidate=candidate,owner=owner,organization=organization,inst=inst,member=member,appointment=appointment,grant=grant,
        teacher_member=tm,teacher_appointment=ta,teacher_grant=tg,enrollment=en,agreement=agreement,supervision=supervision,placement=p)


def assignment_body(f):
    return dict(placement_id=f['placement']['id'],institution_id=f['inst']['id'],supervisor_id=f['teacher_member']['id'],
                supervision_id=f['supervision']['id'],idempotency_key=str(uuid4()))


def accepted_assignment(f):
    assignment=service.create_academic_assignment(actor=actor(f['coord']),**assignment_body(f))
    with transaction() as conn:
        p=get_row(conn,'placements',f['placement']['id']);terms=get_row(conn,'placement_terms',p['current_terms_id'])
    args=dict(placement_id=p['id'],terms_id=terms['id'],version=terms['version'])
    academic_service.accept(actor=actor(f['teacher']),assignment_id=assignment['id'],**args,idempotency_key=str(uuid4()))
    admission_service.accept_candidate(actor=actor(f['candidate']),**args,idempotency_key=str(uuid4()))
    mentor=admission_service.nominate_mentor(actor=actor(f['owner']),placement_id=p['id'],organization_id=f['organization'],
        mentor_id=f['owner']['user_id'],idempotency_key=str(uuid4()))
    admission_service.accept_mentor(actor=actor(f['owner']),assignment_id=mentor['id'],**args,idempotency_key=str(uuid4()))
    admission_service.host_decision(actor=actor(f['owner']),**args,action='ACTIVATE',idempotency_key=str(uuid4()))
    with transaction() as conn:
        f['placement']=get_row(conn,'placements',p['id'])
        return get_row(conn,'academic_assignments',assignment['id'])


def review_request(client,f,assignment,**extra):
    log=service.create_daily_log_with_revision(actor=actor(f['candidate']),placement_id=f['placement']['id'],log_date=f['placement']['start_date'].isoformat(),summary_text='Research work',total_minutes=60)
    body=dict(placement_id=f['placement']['id'],academic_assignment_id=assignment['id'],
        expected_revision_id=log['current_revision_id'],idempotency_key=str(uuid4()),decision='REVIEWED',comment='Reviewed',**extra)
    return lambda:client.post('/api/v1/internship-logs/daily-logs/'+log['id']+'/academic-reviews',json=body,headers=f['teacher']['headers'])


@pytest.mark.parametrize('path',CREATE_PATHS)
def test_create_real_coordinator_and_teacher_then_revoke_idempotently(client,identities,organization,path):
    f=academic_fixture(identities,organization)
    r=client.post(path,json=assignment_body(f),headers=f['coord']['headers']);assert r.status_code==201,r.text
    assert r.json()['assigned_by_id']==f['coord']['user_id'] and count('academic_assignments')==1
    url='/api/v1/internships/academic-assignments/'+r.json()['id']
    # Access cleanup remains possible when the target teacher has lost authority.
    with transaction() as conn:
        conn.execute(table('institution_role_grants').update().where(table('institution_role_grants').c.id==f['teacher_grant']['id']).values(revoked_at=now()))
    first=client.patch(url,json={'status':'REVOKED'},headers=f['coord']['headers']);assert first.status_code==200,first.text
    again=client.patch(url,json={'status':'REVOKED'},headers=f['coord']['headers']);assert again.status_code==200,again.text
    assert datetime.fromisoformat(first.json()['revoked_at'])==datetime.fromisoformat(again.json()['revoked_at'])
    with transaction() as conn:
        actions=conn.execute(select(table('audit_events').c.action).where(table('audit_events').c.object_key==r.json()['id'])).scalars().all()
    assert sorted(actions)==['ACADEMIC_ASSIGNMENT_CREATED','ACADEMIC_ASSIGNMENT_REVOKED']


@pytest.mark.parametrize('path',CREATE_PATHS)
@pytest.mark.parametrize('state',['coord_expired','teacher_expired','teacher_unaccepted','teacher_role_revoked','self_assignment','other_coordinator'])
def test_create_denies_invalid_current_people_without_effect(client,identities,organization,path,state):
    f=academic_fixture(identities,organization);body=assignment_body(f)
    with transaction() as conn:
        if state in ('coord_expired','teacher_expired','teacher_unaccepted'):
            target=f['appointment'] if state=='coord_expired' else f['teacher_appointment']
            values={'accepted_at':None} if state=='teacher_unaccepted' else {'valid_to':date.today()-timedelta(days=1)}
            conn.execute(table('institution_appointments').update().where(table('institution_appointments').c.id==target['id']).values(**values))
        elif state=='teacher_role_revoked':
            conn.execute(table('institution_role_grants').update().where(table('institution_role_grants').c.id==f['teacher_grant']['id']).values(revoked_at=now()))
        elif state=='self_assignment':body['supervisor_id']=f['member']['id']
        else:
            conn.execute(table('student_supervisions').update().where(table('student_supervisions').c.id==f['supervision']['id']).values(coordinator_membership_id=f['teacher_member']['id']))
    before=count('audit_events')
    r=client.post(path,json=body,headers=f['coord']['headers']);assert r.status_code==403,r.text
    assert count('academic_assignments')==0 and count('audit_events')==before


def test_teacher_password_session_can_review_current_assignment(client,identities,organization):
    f=academic_fixture(identities,organization);assignment=accepted_assignment(f)
    with transaction() as conn:
        assert get_row(conn,'sessions',f['teacher']['session_id'])['assurance']=='PASSWORD'
    response=review_request(client,f,assignment)();assert response.status_code==201,response.text
    assert count('academic_log_reviews')==1


@pytest.mark.parametrize('state',['teacher_expired','assignment_revoked',
    'supervision_revoked','supervision_unaccepted','supervision_future_acceptance','agreement_expired','agreement_inactive',
    'purpose_disabled','basis_empty','enrollment_ended','enrollment_unverified','inactive_placement'])
def test_review_current_parent_chain_required_without_effect(client,identities,organization,state):
    f=academic_fixture(identities,organization);assignment=accepted_assignment(f);request=review_request(client,f,assignment)
    targets={
        'teacher_expired':('institution_appointments','teacher_appointment',{'valid_to':date.today()-timedelta(days=1)}),
        'supervision_revoked':('student_supervisions','supervision',{'revoked_at':now()}),
        'supervision_unaccepted':('student_supervisions','supervision',{'accepted_at':None}),
        'supervision_future_acceptance':('student_supervisions','supervision',{'accepted_at':now()+timedelta(days=1)}),
        'agreement_expired':('institution_agreements','agreement',{'valid_to':date.today()-timedelta(days=1)}),
        'agreement_inactive':('institution_agreements','agreement',{'status':'REVOKED'}),
        'purpose_disabled':('institution_agreements','agreement',{'purposes':{'ACADEMIC_VIEW':False}}),
        'basis_empty':('student_supervisions','supervision',{'legal_basis':'  '}),
        'enrollment_unverified':('enrollments','enrollment',{'status':'PENDING'}),
        'inactive_placement':('placements','placement',{'status':'CANCELLED'})}
    with transaction() as conn:
        if state=='assignment_revoked':
            academic_service.revoke(actor(f['coord']),assignment['id'],idempotency_key=str(uuid4()))
        elif state=='enrollment_ended':
            # End through the real lifecycle; approved proof dates are immutable.
            enrollment_service.end_own(actor(f['candidate']),f['enrollment']['id'],idempotency_key=str(uuid4()),
                reason='This student ended their enrollment before the review.',effective_end_date=date.today()-timedelta(days=1))
        else:
            name,key,values=targets[state];t=table(name);conn.execute(t.update().where(t.c.id==f[key]['id']).values(**values))
    before=count('audit_events');r=request();assert r.status_code==403,r.text
    assert count('academic_log_reviews')==0 and count('audit_events')==before


@pytest.mark.parametrize('state',['assignment_unaccepted','assignment_future_acceptance','ordinary_track','self_review'])
def test_accepted_academic_identity_and_consent_cannot_be_rewritten(client,identities,organization,state):
    f=academic_fixture(identities,organization);assignment=accepted_assignment(f)
    name='academic_assignments';key=assignment['id']
    if state=='self_review':
        with transaction() as conn:
            tm=insert_row(conn,'institution_memberships',institution_id=f['inst']['id'],user_id=f['candidate']['user_id'],status='ACTIVE',accepted_at=now())
            ta=insert_row(conn,'institution_appointments',institution_id=f['inst']['id'],user_id=f['candidate']['user_id'],
                document_file_id=f['teacher_appointment']['document_file_id'],status='ACTIVE',valid_from=now().astimezone(TASHKENT).date(),accepted_at=now())
            insert_row(conn,'institution_role_grants',membership_id=tm['id'],role_id=f['teacher_grant']['role_id'],appointment_id=ta['id'])
        values={'teacher_membership_id':tm['id']}
    elif state=='ordinary_track':
        name='placements';key=f['placement']['id'];values={'academic_track':False}
    else:values={'accepted_at':None if state=='assignment_unaccepted' else now()+timedelta(days=1)}
    before=count('audit_events')
    with pytest.raises(IntegrityError),transaction() as conn:
        t=table(name);conn.execute(t.update().where(t.c.id==key).values(**values))
    assert count('academic_log_reviews')==0 and count('audit_events')==before
    # The failed corruption attempt leaves the original personal consent usable.
    response=review_request(client,f,assignment)();assert response.status_code==201,response.text
    assert count('academic_log_reviews')==1


def test_expired_verified_enrollment_cannot_start_academic_assignment(client,identities,organization):
    f=academic_fixture(identities,organization,enrollment_end_date=now().astimezone(TASHKENT).date()-timedelta(days=1),make_supervision=False)
    with transaction() as conn:
        assert get_row(conn,'enrollments',f['enrollment']['id'])['status']=='VERIFIED'
    before=count('audit_events')
    response=client.post('/api/v1/student-supervisions',json=dict(institution_id=f['inst']['id'],enrollment_id=f['enrollment']['id'],
        agreement_id=f['agreement']['id'],purpose='ACADEMIC_VIEW',legal_basis='Current school agreement.',idempotency_key=str(uuid4())),headers=f['coord']['headers'])
    assert response.status_code==403,response.text
    assert count('student_supervisions')==0 and count('academic_assignments')==0 and count('audit_events')==before


def test_grade_is_rejected_in_diary_review_without_effect(client,identities,organization):
    f=academic_fixture(identities,organization);assignment=accepted_assignment(f)
    r=review_request(client,f,assignment,academic_grade=5)();assert r.status_code==422,r.text
    assert count('academic_log_reviews')==0


@pytest.mark.parametrize('kind',['create','revoke','review'])
@pytest.mark.parametrize('change',['session','appointment','grant','account_version'])
def test_committed_security_change_after_real_business_wait_denies_write(client,identities,organization,kind,change):
    f=academic_fixture(identities,organization)
    if kind=='create':
        user=f['coord'];request=lambda:client.post(CREATE_PATHS[0],json=assignment_body(f),headers=user['headers'])
    else:
        assignment=accepted_assignment(f)
        if kind=='review':user=f['teacher'];request=review_request(client,f,assignment)
        else:
            user=f['coord'];request=lambda:client.patch('/api/v1/internships/academic-assignments/'+assignment['id'],json={'status':'REVOKED'},headers=user['headers'])
    before=(count('academic_assignments'),count('academic_log_reviews'),count('audit_events'))
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as blocker:
            blocker.execute(select(table('institutions')).where(table('institutions').c.id==f['inst']['id']).with_for_update())
            pid=blocker.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(request);wait_for_blocker(pid)
            with transaction() as conn:
                if change=='session':name,key,values='sessions',user['session_id'],{'revoked_at':now()}
                elif change=='account_version':
                    name,key,values='users',user['user_id'],{'auth_version':get_row(conn,'users',user['user_id'])['auth_version']+1}
                else:
                    prefix='teacher_' if kind=='review' else ''
                    name='institution_appointments' if change=='appointment' else 'institution_role_grants'
                    key=f[prefix+change]['id'];values={'status':'REVOKED'} if change=='appointment' else {'revoked_at':now()}
                t=table(name);conn.execute(t.update().where(t.c.id==key).values(**values))
        r=pending.result(timeout=30)
    assert r.status_code in (401,403),r.text
    assert (count('academic_assignments'),count('academic_log_reviews'),count('audit_events'))==before
    if kind=='revoke':
        with transaction() as conn:assert get_row(conn,'academic_assignments',assignment['id'])['revoked_at'] is None


def test_target_user_busy_returns_retry_and_rolls_back(client,identities,organization):
    f=academic_fixture(identities,organization);before=count('audit_events')
    with get_engine().begin() as blocker:
        blocker.execute(select(table('users')).where(table('users').c.id==f['teacher']['user_id']).with_for_update())
        r=client.post(CREATE_PATHS[0],json=assignment_body(f),headers=f['coord']['headers'])
        assert r.status_code==409,r.text
        assert r.json()['detail']['code']=='INSTITUTION_AUTHORITY_BUSY_RETRY'
    assert count('academic_assignments')==0 and count('audit_events')==before
    assert client.post(CREATE_PATHS[0],json=assignment_body(f),headers=f['coord']['headers']).status_code==201


def test_audit_failure_rolls_back_created_assignment(client,identities,organization,monkeypatch):
    f=academic_fixture(identities,organization)
    def fail(**kwargs):raise RuntimeError('Audit unavailable')
    monkeypatch.setattr(academic_service.audit,'append_audit_event',fail)
    r=client.post(CREATE_PATHS[0],json=assignment_body(f),headers=f['coord']['headers']);assert r.status_code==503,r.text
    assert count('academic_assignments')==0


@pytest.mark.parametrize('kind',['create','revoke','review'])
@pytest.mark.parametrize('change',['session','appointment','grant'])
def test_authorized_commit_precedes_waiting_security_change(client,identities,organization,monkeypatch,kind,change):
    from app.services import authority
    f=academic_fixture(identities,organization)
    if kind=='create':
        user=f['coord'];request=lambda:client.post(CREATE_PATHS[0],json=assignment_body(f),headers=user['headers'])
    else:
        assignment=accepted_assignment(f)
        if kind=='review':user=f['teacher'];request=review_request(client,f,assignment)
        else:
            user=f['coord'];request=lambda:client.patch('/api/v1/internships/academic-assignments/'+assignment['id'],json={'status':'REVOKED'},headers=user['headers'])
    held,release=Event(),Event();pids=[];original=authority.institution_authority
    def hold(conn,context,*args,**kwargs):
        result=original(conn,context,*args,**kwargs)
        pids.append(conn.execute(text('SELECT pg_backend_pid()')).scalar_one())
        held.set();assert release.wait(30)
        return result
    monkeypatch.setattr(authority,'institution_authority',hold)
    def revoke():
        if change=='session':return client.delete('/api/v1/me/sessions/'+user['session_id'],headers=user['headers'])
        prefix='teacher_' if kind=='review' else ''
        name='institution_appointments' if change=='appointment' else 'institution_role_grants'
        values={'status':'REVOKED'} if change=='appointment' else {'revoked_at':now()}
        with transaction() as conn:
            t=table(name);conn.execute(t.update().where(t.c.id==f[prefix+change]['id']).values(**values))
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending=pool.submit(request)
        try:
            assert held.wait(30)
            changed=pool.submit(revoke);wait_for_blocker(pids[0]);assert not changed.done()
        finally:release.set()
        response=pending.result(timeout=30);result=changed.result(timeout=30)
    assert response.status_code==(200 if kind=='revoke' else 201),response.text
    if change=='session':assert result.status_code==200,result.text
    if kind=='review':assert count('academic_log_reviews')==1
    elif kind=='create':assert count('academic_assignments')==1
    else:
        with transaction() as conn:assert get_row(conn,'academic_assignments',assignment['id'])['revoked_at'] is not None


@pytest.mark.parametrize('session',['foreign','unknown','expired','revoked'])
def test_direct_service_cannot_use_cached_claims_with_invalid_session(identities,organization,session):
    from app.services.governance import GovernanceError
    f=academic_fixture(identities,organization);uid=f['coord']['user_id'];sid=f['coord']['session_id']
    if session=='foreign':sid=f['teacher']['session_id']
    elif session=='unknown':sid=str(uuid4())
    else:
        with transaction() as conn:
            values={'expires_at':now()-timedelta(seconds=1)} if session=='expired' else {'revoked_at':now()}
            conn.execute(table('sessions').update().where(table('sessions').c.id==sid).values(**values))
    with pytest.raises(GovernanceError):
        service.create_academic_assignment(actor=ActorContext(uid,sid,('COORDINATOR','TEACHER')),**assignment_body(f))
    assert count('academic_assignments')==0


def add_teacher_coordinator_role(f):
    with transaction() as conn:
        roles=table('role_catalog');rid=conn.execute(select(roles.c.id).where(roles.c.code=='COORDINATOR',roles.c.scope_kind=='INSTITUTION')).scalar_one()
        insert_row(conn,'institution_role_grants',membership_id=f['teacher_member']['id'],role_id=rid,appointment_id=f['teacher_appointment']['id'])


def test_teacher_who_also_coordinates_cannot_bypass_mfa_in_service(client,identities,organization):
    from app.services.governance import GovernanceError
    f=academic_fixture(identities,organization);assignment=accepted_assignment(f)
    log=service.create_daily_log_with_revision(actor=actor(f['candidate']),placement_id=f['placement']['id'],log_date=f['placement']['start_date'].isoformat(),summary_text='Research',total_minutes=60)
    add_teacher_coordinator_role(f)
    with pytest.raises(GovernanceError,match='MFA_REQUIRED'):
        service.review_academic(actor=actor(f['teacher']),daily_log_id=log['id'],placement_id=f['placement']['id'],assignment_id=assignment['id'],
            expected_revision_id=log['current_revision_id'],idempotency_key=str(uuid4()),decision='REVIEWED',comment='Reviewed')
    assert count('academic_log_reviews')==0


def test_sensitive_role_granted_after_http_preflight_requires_mfa_at_write(client,identities,organization):
    f=academic_fixture(identities,organization);assignment=accepted_assignment(f);request=review_request(client,f,assignment)
    before=count('audit_events')
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as blocker:
            blocker.execute(select(table('institutions')).where(table('institutions').c.id==f['inst']['id']).with_for_update())
            pid=blocker.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(request);wait_for_blocker(pid)
            add_teacher_coordinator_role(f)
        r=pending.result(timeout=30)
    assert r.status_code==403,r.text
    assert r.json()['detail']['code']=='MFA_REQUIRED'
    assert count('academic_log_reviews')==0 and count('audit_events')==before


def test_imported_revision_author_must_own_placement_candidate(client,identities,organization):
    f=academic_fixture(identities,organization);assignment=accepted_assignment(f)
    draft=service.save_draft_daily_log_api_054(actor=actor(f['candidate']),placement_id=f['placement']['id'],log_date=f['placement']['start_date'].isoformat(),summary_text='Research',total_minutes=60)
    with transaction() as conn:
        # Trusted legacy/import corruption, not a demonstrated public draft exploit.
        t=table('log_revisions');conn.execute(t.update().where(t.c.id==draft['current_revision_id']).values(author_id=f['coord']['user_id'],status='SUBMITTED',submitted_at=now()))
    before=count('audit_events')
    r=client.post('/api/v1/internship-logs/daily-logs/'+draft['id']+'/academic-reviews',headers=f['teacher']['headers'],json={
        'placement_id':f['placement']['id'],'academic_assignment_id':assignment['id'],'decision':'REVIEWED',
        'expected_revision_id':draft['current_revision_id'],'idempotency_key':str(uuid4())})
    assert r.status_code==403,r.text
    assert count('academic_log_reviews')==0 and count('audit_events')==before
