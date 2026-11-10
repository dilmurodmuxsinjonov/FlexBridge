"""Populated0015 review preservation and transactional forward-migration failure."""
import pytest
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db.storage import table, now
from app.services.placements import get_row, insert_row
from app.services.academic_admission import snapshot
from test_academic_migration import legacy_academic
from test_institution_migration import populated_database


def old_review(conn, decision):
    f = legacy_academic(conn)
    p = get_row(conn,'placements',f['placement_id'])
    candidate = get_row(conn,'candidate_profiles',p['candidate_id'])
    log = insert_row(conn,'daily_logs',placement_id=p['id'],local_date=p['start_date'],version=1)
    revision = insert_row(conn,'log_revisions',daily_log_id=log['id'],revision=1,terms_id=f['terms_id'],
        author_id=candidate['user_id'],day_type='DAY_OFF',summary='Original imported record',total_minutes=0,
        status='SUBMITTED',submitted_at=now(),idempotency_key='legacy-review-'+log['id'])
    return insert_row(conn,'academic_log_reviews',revision_id=revision['id'],placement_id=p['id'],
        academic_assignment_id=f['assignment_id'],decision=decision,comment='Preserve original feedback verbatim.',decided_at=now())


def history(conn):
    return {name:[dict(r) for r in conn.execute(select(table(name)).order_by(table(name).c.id)).mappings()]
            for name in ('placements','placement_terms','academic_assignments','daily_logs','log_revisions','academic_log_reviews')}


@pytest.mark.parametrize('decision', ['APPROVED','REJECTED','CHANGES_REQUESTED','LOCAL_HISTORICAL_VALUE'])
def test_populated_review_upgrade_keeps_original_decision_without_fabricated_actor(decision):
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:review = old_review(conn,decision)
        migrate('0015_academic_admission')
        with engine.begin() as conn:before = history(conn)
        migrate('head')
        with engine.begin() as conn:
            assert history(conn) == before
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one() == '0017_feature_flag_administration'
            assert conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'")).scalar_one() == 127
            proof = dict(conn.execute(select(table('academic_review_proofs'))).mappings().one())
            assert proof['review_id'] == review['id'] and proof['origin'] == 'LEGACY_IMPORT'
            assert proof['initial_snapshot']['decision'] == decision
            assert all(value is None for key,value in proof.items()
                       if key not in ('review_id','created_at','origin','initial_snapshot'))
        with pytest.raises(IntegrityError,match='legacy set is closed'),engine.begin() as conn:
            conn.execute(table('academic_review_proofs').insert().values(**proof))
        with pytest.raises(IntegrityError),engine.begin() as conn:
            conn.execute(table('academic_log_reviews').update().values(decision='REVIEWED'))


def test_failed_review_upgrade_rolls_back_capture_and_retains_0015_history():
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:old_review(conn,'APPROVED')
        migrate('0015_academic_admission')
        with engine.begin() as conn:
            before = history(conn)
            conn.execute(text("""CREATE FUNCTION flexbridge.guard_academic_review_proof() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$"""))
            function = conn.execute(text("SELECT pg_get_functiondef('flexbridge.guard_academic_review_proof()'::regprocedure)")).scalar_one()
        failed = migrate('head',False)
        assert failed.returncode != 0 and 'guard_academic_review_proof' in failed.stderr
        with engine.begin() as conn:
            assert history(conn) == before
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one() == '0015_academic_admission'
            assert conn.execute(text("SELECT to_regclass('flexbridge.academic_review_proofs')")).scalar_one() is None
            assert conn.execute(text("SELECT pg_get_functiondef('flexbridge.guard_academic_review_proof()'::regprocedure)")).scalar_one() == function


def test_legacy_assignment_without_exact_plan_consent_cannot_create_public_review():
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:
            f = legacy_academic(conn)
            p = get_row(conn,'placements',f['placement_id'])
            candidate = get_row(conn,'candidate_profiles',p['candidate_id'])
            log = insert_row(conn,'daily_logs',placement_id=p['id'],local_date=p['start_date'],version=1)
            revision = insert_row(conn,'log_revisions',daily_log_id=log['id'],revision=1,terms_id=f['terms_id'],
                author_id=candidate['user_id'],day_type='DAY_OFF',summary='Imported submitted revision',total_minutes=0,
                status='SUBMITTED',submitted_at=now(),idempotency_key=str(uuid4()))
            session = insert_row(conn,'sessions',user_id=f['teacher_id'],assurance='PASSWORD',
                auth_version=1,token_digest=str(uuid4()),expires_at=now()+timedelta(hours=1),last_seen_at=now())
        migrate('head')
        with engine.begin() as conn:
            assert conn.execute(text('SELECT flexbridge.academic_teacher_current(:a,:t)'),
                {'a':f['assignment_id'],'t':f['terms_id']}).scalar_one() is True
            assert conn.execute(select(table('academic_assignment_consents'))).first() is None
            assert conn.execute(text('SELECT flexbridge.placement_actor_current(:u,:s,1)'),
                {'u':f['teacher_id'],'s':session['id']}).scalar_one() is True
        with pytest.raises(IntegrityError,match='exact current teacher'),engine.begin() as conn:
            review = insert_row(conn,'academic_log_reviews',revision_id=revision['id'],placement_id=p['id'],
                academic_assignment_id=f['assignment_id'],decision='REVIEWED',comment='No exact consent exists.',decided_at=now())
            stored = snapshot(conn,'academic_log_reviews',review['id'])
            q = conn.execute(text('SELECT to_jsonb(q) FROM flexbridge.academic_assignment_proofs q WHERE assignment_id=:a'),
                {'a':f['assignment_id']}).scalar_one()
            conn.execute(table('academic_review_proofs').insert().values(review_id=review['id'],created_at=now(),origin='PUBLIC',
                initial_snapshot=stored,terms_id=f['terms_id'],actor_id=f['teacher_id'],session_id=session['id'],auth_version=1,
                teacher_grant_id=q['teacher_grant_id'],teacher_appointment_id=q['teacher_appointment_id'],
                assignment_proof_snapshot=q,revision_snapshot=snapshot(conn,'log_revisions',revision['id']),
                idempotency_key=str(uuid4()),request_fingerprint='a'*64,receipt=stored))
        with engine.begin() as conn:
            assert conn.execute(select(table('academic_log_reviews'))).first() is None
