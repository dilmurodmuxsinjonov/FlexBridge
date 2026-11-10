"""Actual PostgreSQL proof/upgrade tests; direct SQL here does not certify HTTP intake."""
from datetime import date, timedelta
import json
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_institution_migration import populated_database
from test_candidate import cv_fixture
from app.adapters.storage import file_snapshot


def new_institution(conn):
    row=dict(id=str(uuid4()), created_at=now(), updated_at=now(), registry_code=str(uuid4()),
             name='Enrollment school', region='Tashkent', status='VERIFIED')
    conn.execute(table('institutions').insert().values(**row))
    return row


def declared_sql(owner):
    """Bind an actual-session declaration in SQL, without pretending its API exists."""
    with transaction() as conn:
        inst = new_institution(conn)
        enrollment = insert_row(conn, 'enrollments', candidate_id=owner['candidate_id'],
                                institution_id=inst['id'], program='Engineering',
                                start_date=date.today()-timedelta(days=30), status='DECLARED')
        case = insert_row(conn, 'verification_cases', requester_id=owner['user_id'],
                          enrollment_id=enrollment['id'], kind='ENROLLMENT', status='DRAFT',
                          current_revision=1, due_at=now()+timedelta(days=1))
        conn.execute(table('enrollments').update().where(table('enrollments').c.id==enrollment['id'])
                     .values(verification_case_id=case['id']))
        conn.execute(table('enrollment_origins').insert().values(
            enrollment_id=enrollment['id'], created_at=now(), origin='PUBLIC',
            candidate_id=owner['candidate_id'], institution_id=inst['id'], actor_user_id=owner['user_id'],
            case_id=case['id'], initial_snapshot=json.loads(json.dumps(enrollment, default=str)),
            idempotency_key=str(uuid4()), request_fingerprint='a'*64))
    return enrollment, case


def declaration_proof(conn, owner, case, enrollment, session_id=None):
    version=conn.execute(select(table('users').c.auth_version).where(
        table('users').c.id==owner['user_id'])).scalar_one()
    conn.execute(table('enrollment_submissions').insert().values(
        case_id=case['id'], revision=1, created_at=now(), submitted_by_id=owner['user_id'],
        session_id=session_id or owner['session_id'], auth_version=version,
        program=enrollment['program'], start_date=enrollment['start_date'],
        end_date=None, student_ref_digest=None, evidence_note='', file_ids=[], file_snapshots={}))


def test_fresh_schema_and_unproved_new_verified_insert_are_rejected(identities):
    owner=identities()
    with transaction() as conn:
        assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one()=='0015_academic_admission'
        assert conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'")).scalar_one()==124
        inst=new_institution(conn)
    with pytest.raises(IntegrityError, match='requires exact approval proof'), transaction() as conn:
        insert_row(conn, 'enrollments', candidate_id=owner['candidate_id'], institution_id=inst['id'],
                   program='Engineering', start_date=date.today(), status='VERIFIED')
    with transaction() as conn:
        assert conn.execute(select(table('enrollments').c.id)).first() is None


def test_populated_upgrade_preserves_exact_legacy_set_and_prevents_new_legacy_and_resurrection():
    with populated_database() as (engine, migrate):
        migrate('0012_file_storage_versions')
        with engine.begin() as conn:
            user=insert_row(conn, 'users', display_name='Imported student', status='ACTIVE', locale='uz',
                            timezone='Asia/Tashkent', auth_version=1)
            profile=insert_row(conn, 'candidate_profiles', user_id=user['id'], headline='Ordinary candidate',
                               region='Tashkent', experience_months=0, visibility='PRIVATE')
            inst=new_institution(conn)
            verified=insert_row(conn, 'enrollments', candidate_id=profile['id'], institution_id=inst['id'],
                                program='Legacy program', start_date=date.today()-timedelta(days=30), status='VERIFIED')
            pending=insert_row(conn, 'enrollments', candidate_id=profile['id'], institution_id=inst['id'],
                               program='Pending import', start_date=date.today(), status='PENDING')
            before=dict(conn.execute(select(table('enrollments')).where(
                table('enrollments').c.id==verified['id'])).mappings().one())
        migrate('head')
        with engine.begin() as conn:
            original=conn.execute(select(table('enrollments')).where(table('enrollments').c.id==verified['id'])).mappings().one()
            assert dict(original)==before
            markers=conn.execute(select(table('enrollment_origins'))).mappings().all()
            assert len(markers)==2 and {m['origin'] for m in markers}=={'LEGACY_IMPORT'}
            assert all(m['case_id'] is None for m in markers)
            assert conn.execute(text('SELECT flexbridge.enrollment_is_current(:id)'), {'id':verified['id']}).scalar_one() is True
            assert conn.execute(text('SELECT flexbridge.enrollment_is_current(:id)'), {'id':pending['id']}).scalar_one() is False
            assert conn.execute(select(table('enrollment_events').c.id)).first() is None
            fresh=insert_row(conn, 'enrollments', candidate_id=profile['id'], institution_id=inst['id'],
                             program='New unreviewed entry', start_date=date.today(), status='DECLARED')
        with pytest.raises(IntegrityError, match='legacy set is closed'), engine.begin() as conn:
            conn.execute(table('enrollment_origins').insert().values(
                enrollment_id=fresh['id'], created_at=now(), origin='LEGACY_IMPORT',
                candidate_id=profile['id'], institution_id=inst['id'], actor_user_id=user['id'], initial_snapshot={}))
        with pytest.raises(IntegrityError, match='promoted or resurrected'), engine.begin() as conn:
            conn.execute(table('enrollments').update().where(table('enrollments').c.id==pending['id']).values(status='VERIFIED'))
        with engine.begin() as conn:
            conn.execute(table('enrollments').update().where(table('enrollments').c.id==verified['id']).values(status='PENDING'))
        with pytest.raises(IntegrityError, match='promoted or resurrected'), engine.begin() as conn:
            conn.execute(table('enrollments').update().where(table('enrollments').c.id==verified['id']).values(status='VERIFIED'))
        with engine.begin() as conn:
            assert conn.execute(select(table('candidate_profiles').c.id)).scalar_one()==profile['id']
            assert conn.execute(text('SELECT count(*) FROM flexbridge.enrollments')).scalar_one()==3
            assert conn.execute(text('SELECT count(*) FROM flexbridge.enrollment_origins')).scalar_one()==2


def test_declaration_has_no_eligibility_or_direct_decision_promotion(identities):
    owner=identities(); enrollment, case=declared_sql(owner)
    with transaction() as conn:
        declaration_proof(conn, owner, case, enrollment)
        assert conn.execute(text('SELECT flexbridge.enrollment_is_current(:id)'), {'id':enrollment['id']}).scalar_one() is False
    with pytest.raises(IntegrityError, match='decision proof missing'), transaction() as conn:
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id']).values(status='APPROVED'))
    with pytest.raises(IntegrityError, match='approved revision mismatch'), transaction() as conn:
        conn.execute(table('enrollments').update().where(table('enrollments').c.id==enrollment['id']).values(status='VERIFIED'))
    with pytest.raises(IntegrityError), transaction() as conn:
        conn.execute(table('enrollment_submissions').update().where(table('enrollment_submissions').c.case_id==case['id']).values(program='Rewritten'))


def test_own_declaration_cannot_record_another_users_session(identities):
    owner=identities(); other=identities(); enrollment, case=declared_sql(owner)
    with pytest.raises(IntegrityError, match='authority or revision mismatch'), transaction() as conn:
        declaration_proof(conn, owner, case, enrollment, session_id=other['session_id'])
    with transaction() as conn:
        assert conn.execute(select(table('enrollment_submissions').c.case_id)).first() is None


def pending_claimed_sql(owner, moderator):
    enrollment, case=declared_sql(owner); file=cv_fixture(owner)
    with transaction() as conn:
        declaration_proof(conn, owner, case, enrollment)
        version=conn.execute(select(table('users').c.auth_version).where(
            table('users').c.id==owner['user_id'])).scalar_one()
        conn.execute(table('enrollment_submissions').insert().values(
            case_id=case['id'], revision=2, created_at=now(), submitted_by_id=owner['user_id'],
            session_id=owner['session_id'], auth_version=version, program=enrollment['program'],
            start_date=enrollment['start_date'], end_date=None, student_ref_digest=None,
            evidence_note='Current enrollment supporting document.', file_ids=[file['id']],
            file_snapshots={file['id']:file_snapshot(file)}))
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id'])
                     .values(current_revision=2, status='PENDING'))
        conn.execute(table('enrollments').update().where(table('enrollments').c.id==enrollment['id']).values(status='PENDING'))
        grant=conn.execute(select(table('platform_role_grants').c.id).where(
            table('platform_role_grants').c.user_id==moderator['user_id'])).scalar_one()
        event=enrollment_review_event(conn, moderator, enrollment, case, grant, 'CLAIM')
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id'])
                     .values(assigned_reviewer_id=event['actor_id'], status='IN_REVIEW'))
    return enrollment, case, file, grant


def enrollment_review_event(conn, actor, enrollment, case, grant, action):
    version=conn.execute(select(table('users').c.auth_version).where(table('users').c.id==actor['user_id'])).scalar_one()
    values=dict(id=str(uuid4()), created_at=now(), enrollment_id=enrollment['id'], case_id=case['id'],
                revision=2, action=action, actor_id=actor['user_id'], session_id=actor['session_id'],
                auth_version=version, platform_grant_id=grant,
                reason='Independent review of exact enrollment evidence.', receipt={})
    conn.execute(table('enrollment_events').insert().values(**values))
    return values


def test_exact_owned_revision_and_independent_mfa_decision_can_verify(identities):
    owner=identities(); moderator=identities('MODERATOR')
    enrollment, case, _, grant=pending_claimed_sql(owner, moderator)
    with transaction() as conn:
        event=enrollment_review_event(conn, moderator, enrollment, case, grant, 'APPROVE')
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id'])
                     .values(status='APPROVED', decision_reason=event['reason'], decided_at=event['created_at']))
        conn.execute(table('enrollments').update().where(table('enrollments').c.id==enrollment['id']).values(status='VERIFIED'))
        assert conn.execute(text('SELECT flexbridge.enrollment_is_current(:id)'), {'id':enrollment['id']}).scalar_one() is True
    with pytest.raises(IntegrityError,match='history cannot be rewritten'), transaction() as conn:
        conn.execute(table('enrollments').update().where(table('enrollments').c.id==enrollment['id'])
                     .values(end_date=date.today()-timedelta(days=1)))
    with pytest.raises(IntegrityError), transaction() as conn:
        conn.execute(table('enrollment_events').delete().where(table('enrollment_events').c.enrollment_id==enrollment['id']))


def test_review_rejects_changed_file_material_without_writing_approval(identities):
    owner=identities(); moderator=identities('MODERATOR')
    enrollment, case, file, grant=pending_claimed_sql(owner, moderator)
    with transaction() as conn:
        conn.execute(table('files').update().where(table('files').c.id==file['id'])
                     .values(sha256='0'*64 if file['sha256']!='0'*64 else '1'*64))
    with pytest.raises(IntegrityError, match='material is stale'), transaction() as conn:
        enrollment_review_event(conn, moderator, enrollment, case, grant, 'APPROVE')
    with transaction() as conn:
        assert conn.execute(select(table('enrollment_events').c.id).where(table('enrollment_events').c.action=='APPROVE')).first() is None
        assert conn.execute(select(table('enrollments').c.status).where(table('enrollments').c.id==enrollment['id'])).scalar_one()=='PENDING'


def test_failed_populated_upgrade_rolls_back_captured_origins_without_losing_existing_data():
    with populated_database() as (engine,migrate):
        migrate('0012_file_storage_versions')
        with engine.begin() as conn:
            user=insert_row(conn,'users',display_name='Rollback import',status='ACTIVE',locale='uz',timezone='Asia/Tashkent',auth_version=1)
            profile=insert_row(conn,'candidate_profiles',user_id=user['id'],headline='Ordinary history',region='Tashkent',experience_months=0,visibility='PRIVATE')
            institution=new_institution(conn)
            enrollment=insert_row(conn,'enrollments',candidate_id=profile['id'],institution_id=institution['id'],
                                  program='Existing imported program',start_date=date.today(),status='VERIFIED')
            before=dict(conn.execute(select(table('enrollments')).where(table('enrollments').c.id==enrollment['id'])).mappings().one())
            # A real namespace collision fails after origins have been created and populated.
            conn.execute(text('CREATE TABLE flexbridge.enrollment_submissions (sentinel text NOT NULL)'))
            conn.execute(text("INSERT INTO flexbridge.enrollment_submissions VALUES ('Existing table data')"))
        failed=migrate('0013_enrollment_verification',False)
        assert failed.returncode!=0 and 'enrollment_submissions' in failed.stderr and 'already exists' in failed.stderr
        with engine.begin() as conn:
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one()=='0012_file_storage_versions'
            assert conn.execute(text("SELECT to_regclass('flexbridge.enrollment_origins')")).scalar_one() is None
            assert conn.execute(text('SELECT sentinel FROM flexbridge.enrollment_submissions')).scalar_one()=='Existing table data'
            assert dict(conn.execute(select(table('enrollments')).where(table('enrollments').c.id==enrollment['id'])).mappings().one())==before
