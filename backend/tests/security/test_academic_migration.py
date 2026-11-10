"""Populated academic upgrades; trusted pre-upgrade SQL history is not HTTP consent."""
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError

from app.db.storage import table,now
from app.db.institution_scope import TASHKENT
from app.services.placements import insert_row,get_row
from test_institution_migration import populated_database,seed_old_scope
from test_admission_migration import old_placement


HISTORY=('placements','placement_terms','mentor_assignments','enrollments','student_supervisions','academic_assignments')


def history(conn):
    return {name:[dict(r) for r in conn.execute(select(table(name)).order_by(table(name).c.id)).mappings()] for name in HISTORY}


def legacy_academic(conn,*,ambiguous=False):
    coordinator,inst,member,_,_=seed_old_scope(conn)
    pid,tid,_=old_placement(conn)
    p=get_row(conn,'placements',pid);today=now().astimezone(TASHKENT).date()
    enrollment=insert_row(conn,'enrollments',candidate_id=p['candidate_id'],institution_id=inst['id'],program='Imported engineering',
        start_date=today-timedelta(days=30),status='VERIFIED')
    agreement=insert_row(conn,'institution_agreements',institution_id=inst['id'],version=1,status='ACTIVE',valid_from=today-timedelta(days=30),purposes=['ACADEMIC_VIEW'])
    supervision=insert_row(conn,'student_supervisions',institution_id=inst['id'],enrollment_id=enrollment['id'],
        coordinator_membership_id=member['id'],agreement_id=agreement['id'],purpose='ACADEMIC_VIEW',legal_basis='Original imported basis.',
        status='ACTIVE',accepted_at=now())
    teacher=insert_row(conn,'users',display_name='Imported teacher',status='ACTIVE',locale='uz',timezone='Asia/Tashkent',auth_version=1)
    tm=insert_row(conn,'institution_memberships',institution_id=inst['id'],user_id=teacher['id'],status='ACTIVE',accepted_at=now())
    roles=table('role_catalog')
    rid=conn.execute(select(roles.c.id).where(roles.c.code=='TEACHER',roles.c.scope_kind=='INSTITUTION')).scalar_one_or_none()
    if not rid:rid=insert_row(conn,'role_catalog',code='TEACHER',scope_kind='INSTITUTION',description='Imported teacher')['id']
    document=get_row(conn,'institution_appointments',conn.execute(select(table('institution_appointments').c.id).where(
        table('institution_appointments').c.user_id==coordinator['id'])).scalar_one())['document_file_id']
    grants=[]
    for _ in range(2 if ambiguous else 1):
        appointment=insert_row(conn,'institution_appointments',institution_id=inst['id'],user_id=teacher['id'],document_file_id=document,
            status='ACTIVE',valid_from=today-timedelta(days=30),accepted_at=now())
        grants.append(insert_row(conn,'institution_role_grants',membership_id=tm['id'],role_id=rid,appointment_id=appointment['id']))
    assignment=insert_row(conn,'academic_assignments',placement_id=pid,institution_id=inst['id'],teacher_membership_id=tm['id'],
        supervision_id=supervision['id'],assigned_by_id=coordinator['id'],assigned_at=now(),accepted_at=now())
    conn.execute(table('placements').update().where(table('placements').c.id==pid).values(academic_track=True,enrollment_id=enrollment['id']))
    return dict(placement_id=pid,terms_id=tid,supervision_id=supervision['id'],assignment_id=assignment['id'],
        teacher_id=teacher['id'],teacher_member_id=tm['id'],teacher_role_id=rid,institution_id=inst['id'],document_id=document,grants=grants)


@pytest.mark.parametrize('ambiguous',[False,True])
def test_populated_academic_upgrade_preserves_history_without_fabricating_new_consent(ambiguous):
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:f=legacy_academic(conn,ambiguous=ambiguous)
        migrate('0014_placement_admission')
        with engine.begin() as conn:before=history(conn)
        migrate('head')
        with engine.begin() as conn:
            assert history(conn)==before
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one()=='0018_academic_decisions'
            assert conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'")).scalar_one()==128
            q=dict(conn.execute(select(table('academic_assignment_proofs'))).mappings().one())
            b=dict(conn.execute(select(table('placement_academic_bindings'))).mappings().one())
            s=dict(conn.execute(select(table('supervision_origins'))).mappings().one())
            for proof in (q,b,s):
                assert proof['origin']=='LEGACY_IMPORT'
                assert all(proof[k] is None for k in ('actor_id','session_id','auth_version','coordinator_grant_id','idempotency_key','request_fingerprint','receipt'))
            assert b['supervision_id']==f['supervision_id']
            assert (q['teacher_grant_id'] is None)==ambiguous
            if not ambiguous:assert q['teacher_grant_id']==f['grants'][0]['id']
            assert conn.execute(text('SELECT flexbridge.academic_teacher_current(:a,:t)'),{'a':f['assignment_id'],'t':f['terms_id']}).scalar_one() is (not ambiguous)
            # Captured legacy history is not a new activation authorization.
            assert conn.execute(text('SELECT flexbridge.academic_placement_ready(:p,:t)'),{'p':f['placement_id'],'t':f['terms_id']}).scalar_one() is False
            for name in ('student_academic_requests','academic_assignment_consents','academic_assignment_events'):
                assert conn.execute(select(table(name))).first() is None
        with pytest.raises(IntegrityError,match='legacy set is closed'),engine.begin() as conn:
            conn.execute(table('academic_assignment_proofs').insert().values(**q))
        with pytest.raises(IntegrityError),engine.begin() as conn:
            conn.execute(table('supervision_origins').delete())
        with engine.begin() as conn:
            for grant in f['grants']:
                conn.execute(table('institution_role_grants').update().where(table('institution_role_grants').c.id==grant['id']).values(revoked_at=now()))
            appointment=insert_row(conn,'institution_appointments',institution_id=f['institution_id'],user_id=f['teacher_id'],
                document_file_id=f['document_id'],status='ACTIVE',valid_from=now().astimezone(TASHKENT).date(),accepted_at=now())
            insert_row(conn,'institution_role_grants',membership_id=f['teacher_member_id'],role_id=f['teacher_role_id'],appointment_id=appointment['id'])
            assert conn.execute(text('SELECT flexbridge.academic_teacher_current(:a,:t)'),{'a':f['assignment_id'],'t':f['terms_id']}).scalar_one() is False


def test_academic_upgrade_failure_rolls_back_partial_ddl_and_keeps_0014_history():
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:legacy_academic(conn)
        migrate('0014_placement_admission')
        with engine.begin() as conn:
            before=history(conn)
            functions={name:conn.execute(text("SELECT pg_get_functiondef(('flexbridge.'||:name)::regprocedure)"),{'name':name}).scalar_one()
                for name in ('placement_ready_for_start(uuid,uuid)','guard_placement_start()')}
            conn.execute(text('CREATE TABLE flexbridge.academic_assignment_consents(marker text)'))
            conn.execute(text("INSERT INTO flexbridge.academic_assignment_consents VALUES ('preserve collision marker')"))
        failed=migrate('head',False)
        assert failed.returncode!=0 and 'academic_assignment_consents' in failed.stderr
        with engine.begin() as conn:
            assert history(conn)==before
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one()=='0014_placement_admission'
            for name,definition in functions.items():
                assert conn.execute(text("SELECT pg_get_functiondef(('flexbridge.'||:name)::regprocedure)"),{'name':name}).scalar_one()==definition
            assert conn.execute(text("SELECT to_regclass('flexbridge.supervision_origins')")).scalar_one() is None
            assert conn.execute(text("SELECT to_regclass('flexbridge.placement_academic_bindings')")).scalar_one() is None
            assert conn.execute(text("SELECT to_regprocedure('flexbridge.academic_grant_current(uuid,uuid,uuid,text)')")).scalar_one() is None
            assert conn.execute(text('SELECT marker FROM flexbridge.academic_assignment_consents')).scalar_one()=='preserve collision marker'
