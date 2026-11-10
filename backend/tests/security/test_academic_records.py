"""Actual minimum academic record reads; staff/file metadata is trusted setup, not legal/scan certification."""
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest

from sqlalchemy import select,text

from app.db.storage import table,transaction,get_engine,now
from app.db.institution_scope import TASHKENT
from app.services.academic_records import academic_record_service
from app.services.placements import insert_row
from test_academic_authority import academic_fixture,accepted_assignment
from test_academic_admission import pending_http,plan
from test_academic_views import active_revision
from test_admission_lifecycle import terms_request
from test_internship_admission import post
from test_candidate import cv_fixture
from test_org_authority_transactions import wait_for_blocker


def detail(client,user,revision,status=200):
    response=client.get('/api/v1/log-revisions/'+revision+'/academic',headers=user['headers'])
    assert response.status_code==status,response.text
    assert response.headers['cache-control']=='no-store'
    return response.json()


def submitted(client,f):
    _,draft=active_revision(client,f)
    post(client,'/api/v1/logs/'+draft['id']+'/submit',f['candidate'],{},200)
    return draft


def test_teacher_password_and_exact_coordinator_read_minimum_diary_and_workplace_decision(client,identities,organization):
    f=pending_http(client,identities,organization);draft=submitted(client,f)
    with transaction() as conn:
        a=dict(conn.execute(select(table('mentor_assignments'))).mappings().one())
    post(client,'/api/v1/internship-logs/daily-logs/'+draft['id']+'/workplace-reviews',f['owner'],dict(
        placement_id=f['placement']['id'],mentor_assignment_id=a['id'],decision='APPROVED',comment='Workplace result checked.'),201)
    for user in (f['teacher'],f['coord']):
        row=detail(client,user,draft['current_revision_id'])
        assert row['id']==draft['current_revision_id'] and row['summary']=='Private academic work summary'
        assert row['is_current_revision'] is True
        assert row['tasks'][0]['result_text'] and row['total_minutes']>0
        assert not {'start_minute','end_minute'} & row['tasks'][0].keys()
        assert row['workplace_reviews'][0]['decision']=='APPROVED' and row['academic_reviews']==[]
        assert row['workplace_reviews'][0]['mentor_assignment_id']==a['id']
        assert not {'application_id','salary_min','legal_basis','files','storage_key','signed_url'} & row.keys()


def test_historical_submitted_read_survives_pointer_change_and_cancellation_while_draft_stays_private(client,identities,organization):
    f=pending_http(client,identities,organization);draft=submitted(client,f);p=plan(client,f)
    next_draft=client.put('/api/v1/placements/'+f['placement']['id']+'/logs/'+p['start_date'],headers=f['candidate']['headers'],json={
        'day_type':'WORKED','summary_text':'Unsubmitted private replacement','total_minutes':30})
    assert next_draft.status_code==409,next_draft.text
    assert next_draft.json()['detail']['code']=='SUBMITTED_LOG_IMMUTABLE'
    # Trusted future-amendment metadata, not a claim that the amendment API exists.
    # The already submitted row and its author/terms remain untouched.
    with transaction() as conn:
        replacement=insert_row(conn,'log_revisions',daily_log_id=draft['id'],revision=2,terms_id=p['terms_id'],
            author_id=f['candidate']['user_id'],day_type='WORKED',summary='Unsubmitted private replacement',total_minutes=0,status='DRAFT',idempotency_key=str(uuid4()))
        daily=table('daily_logs');conn.execute(daily.update().where(daily.c.id==draft['id']).values(current_revision_id=replacement['id']))
    changed=replacement['id'];assert changed!=draft['current_revision_id']
    assert detail(client,f['teacher'],draft['current_revision_id'])['summary']=='Private academic work summary'
    assert detail(client,f['teacher'],draft['current_revision_id'])['is_current_revision'] is False
    detail(client,f['teacher'],changed,404)
    post(client,'/api/v1/placements/'+f['placement']['id']+'/host-decisions',f['owner'],{**terms_request(p),'action':'CANCEL'},200)
    assert detail(client,f['teacher'],draft['current_revision_id'])['placement_status']=='CANCELLED'
    assert detail(client,f['coord'],draft['current_revision_id'])['placement_status']=='CANCELLED'


def test_academic_reader_does_not_grant_private_attachment_download(client,identities,organization):
    f=pending_http(client,identities,organization);_,draft=active_revision(client,f);file=cv_fixture(f['candidate'])
    with transaction() as conn:
        entries=table('log_task_entries');entry=conn.execute(select(entries.c.id).where(entries.c.revision_id==draft['current_revision_id'])).scalar_one()
        # Trusted stored attachment metadata; no claim of a public sharing or scan flow.
        insert_row(conn,'log_evidence',entry_id=entry,file_id=file['id'],visibility='PRIVATE_HOST_EVIDENCE')
    post(client,'/api/v1/logs/'+draft['id']+'/submit',f['candidate'],{},200)
    row=detail(client,f['teacher'],draft['current_revision_id'])
    assert file['id'] not in str(row) and file['storage_key'] not in str(row)
    assert client.get('/api/v1/files/'+file['id']+'/download',headers=f['teacher']['headers']).status_code==403


def test_coordinator_cannot_read_own_diary_through_staff_role(client,identities,organization):
    f=academic_fixture(identities,organization,candidate_is_coordinator=True);accepted_assignment(f);p=plan(client,f)
    response=client.put('/api/v1/placements/'+f['placement']['id']+'/logs/'+p['start_date'],headers=f['candidate']['headers'],json={
        'day_type':'WORKED','summary_text':'Student who also coordinates','total_minutes':60})
    assert response.status_code==200,response.text
    draft=response.json();post(client,'/api/v1/logs/'+draft['id']+'/submit',f['candidate'],{},200)
    detail(client,f['coord'],draft['current_revision_id'],404)
    assert detail(client,f['teacher'],draft['current_revision_id'])['summary']=='Student who also coordinates'


def test_current_same_school_teacher_without_personal_assignment_cannot_read(client,identities,organization):
    f=pending_http(client,identities,organization);draft=submitted(client,f);other=identities()
    with transaction() as conn:
        member=insert_row(conn,'institution_memberships',institution_id=f['inst']['id'],user_id=other['user_id'],status='ACTIVE',accepted_at=now())
        appointment=insert_row(conn,'institution_appointments',institution_id=f['inst']['id'],user_id=other['user_id'],
            document_file_id=f['teacher_appointment']['document_file_id'],status='ACTIVE',valid_from=now().astimezone(TASHKENT).date()-timedelta(days=1),accepted_at=now())
        insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=f['teacher_grant']['role_id'],appointment_id=appointment['id'])
    detail(client,other,draft['current_revision_id'],404)


def test_reappointed_teacher_cannot_revive_old_record_scope(client,identities,organization):
    f=pending_http(client,identities,organization);draft=submitted(client,f)
    with transaction() as conn:
        g=table('institution_role_grants');conn.execute(g.update().where(g.c.id==f['teacher_grant']['id']).values(revoked_at=now()))
        appointment=insert_row(conn,'institution_appointments',institution_id=f['inst']['id'],user_id=f['teacher']['user_id'],
            document_file_id=f['teacher_appointment']['document_file_id'],status='ACTIVE',valid_from=now().astimezone(TASHKENT).date(),accepted_at=now())
        insert_row(conn,'institution_role_grants',membership_id=f['teacher_member']['id'],role_id=f['teacher_grant']['role_id'],appointment_id=appointment['id'])
    detail(client,f['teacher'],draft['current_revision_id'],404)


@pytest.mark.parametrize('change',['session','grant'])
def test_read_rechecks_actual_authority_after_institution_wait(client,identities,organization,change):
    f=pending_http(client,identities,organization);draft=submitted(client,f)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            inst=table('institutions');holder.execute(select(inst).where(inst.c.id==f['inst']['id']).with_for_update())
            pid=holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(lambda:client.get('/api/v1/log-revisions/'+draft['current_revision_id']+'/academic',headers=f['teacher']['headers']))
            wait_for_blocker(pid)
            if change=='session':assert client.delete('/api/v1/me/sessions/'+f['teacher']['session_id'],headers=f['teacher']['headers']).status_code==200
            else:
                with transaction() as conn:
                    g=table('institution_role_grants');conn.execute(g.update().where(g.c.id==f['teacher_grant']['id']).values(revoked_at=now()))
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    with transaction() as conn:
        assert conn.execute(text("SELECT count(*) FROM flexbridge.audit_events WHERE action='ACADEMIC_REVISION_VIEWED'")).scalar_one()==0


def test_failed_read_audit_returns_no_diary_content_or_partial_audit(client,identities,organization,monkeypatch):
    f=pending_http(client,identities,organization);draft=submitted(client,f);append=academic_record_service.audit.append_audit_event
    def fail(**kwargs):
        append(**kwargs)
        raise RuntimeError('Injected after private academic read audit insert')
    monkeypatch.setattr(academic_record_service.audit,'append_audit_event',fail)
    response=client.get('/api/v1/log-revisions/'+draft['current_revision_id']+'/academic',headers=f['teacher']['headers'])
    assert response.status_code==503 and 'Private academic work summary' not in response.text,response.text
    with transaction() as conn:
        assert conn.execute(text("SELECT count(*) FROM flexbridge.audit_events WHERE action='ACADEMIC_REVISION_VIEWED'")).scalar_one()==0
