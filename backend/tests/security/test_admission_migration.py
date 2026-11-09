"""Populated PostgreSQL upgrades preserve history without inventing personal consent."""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db.storage import table, now
from app.services.placements import insert_row
from test_institution_migration import populated_database


def old_placement(conn, kind='INTERNSHIP'):
    """Pre-0014 SQL history only; this does not claim a public admission flow."""
    user=insert_row(conn,'users',display_name='Imported candidate',status='ACTIVE',locale='uz',timezone='Asia/Tashkent',auth_version=1)
    profile=insert_row(conn,'candidate_profiles',user_id=user['id'],headline='',region='Tashkent',experience_months=0,visibility='PRIVATE')
    owner=insert_row(conn,'users',display_name='Imported host',status='ACTIVE',locale='uz',timezone='Asia/Tashkent',auth_version=1)
    org=insert_row(conn,'organizations',tax_id=str(uuid4()),legal_name='Imported host',public_name='Imported host',region='Tashkent',status='VERIFIED')
    member=insert_row(conn,'org_memberships',organization_id=org['id'],user_id=owner['id'],status='ACTIVE')
    role=conn.execute(select(table('role_catalog').c.id).where(table('role_catalog').c.code=='MENTOR',table('role_catalog').c.scope_kind=='ORG')).scalar_one_or_none()
    if not role:role=insert_row(conn,'role_catalog',code='MENTOR',scope_kind='ORG',description='Imported mentor')['id']
    insert_row(conn,'org_role_grants',membership_id=member['id'],role_id=role,granted_by_id=owner['id'])
    opp=insert_row(conn,'opportunities',organization_id=org['id'],kind=kind,status='PUBLISHED',capacity=1,occupied_count=0)
    revision=insert_row(conn,'opportunity_revisions',opportunity_id=opp['id'],revision=1,author_id=owner['id'],title='Imported revision',
        description='Preserve the original snapshot.',region='Tashkent',work_mode='ONSITE',eligibility='OPEN',currency='UZS',is_paid=True,
        salary_min=20000,salary_max=20000,salary_period='HOURLY',salary_basis='GROSS',
        start_date=date.today(),schedule_policy='NEGOTIABLE',shift_match_mode='ANY',snapshot_schema=1,
        contract_type='INTERNSHIP_AGREEMENT' if kind=='INTERNSHIP' else 'LABOR_PART_TIME')
    conn.execute(table('opportunities').update().where(table('opportunities').c.id==opp['id']).values(current_revision_id=revision['id']))
    app=insert_row(conn,'applications',candidate_id=profile['id'],opportunity_id=opp['id'],status='SUBMITTED',version=1)
    attempt=insert_row(conn,'application_attempts',application_id=app['id'],opportunity_id=opp['id'],attempt_no=1,revision_id=revision['id'],
        profile_snapshot={},schedule_result='UNKNOWN',matching_version='1.4.0',submitted_at=now(),idempotency_key=str(uuid4()))
    offer=insert_row(conn,'offers',application_id=app['id'],attempt_id=attempt['id'],revision_id=revision['id'],issuer_membership_id=member['id'],
        terms_snapshot={'legacy':'exact original'},status='ACCEPTED',accepted_at=now(),expires_at=now()+timedelta(days=3),idempotency_key=str(uuid4()))
    placement=insert_row(conn,'placements',application_id=app['id'],offer_id=offer['id'],candidate_id=profile['id'],organization_id=org['id'],
        academic_track=False,status='ACTIVE',start_date=date.today(),end_date=date.today()+timedelta(days=60),version=4)
    terms=insert_row(conn,'placement_terms',placement_id=placement['id'],version=1,schema_version=1,terms_snapshot={'legacy':'exact plan'},
        daily_limit_minutes=480,weekly_limit_minutes=2400,required_minutes=100,candidate_accepted_at=now(),host_accepted_at=now())
    conn.execute(table('placements').update().where(table('placements').c.id==placement['id']).values(current_terms_id=terms['id']))
    assignment=insert_row(conn,'mentor_assignments',placement_id=placement['id'],membership_id=member['id'],organization_id=org['id'],
        assigned_by_id=owner['id'],assigned_at=now(),accepted_at=now())
    return placement['id'],terms['id'],assignment['id']


def snapshot(conn):
    return {name:[dict(r) for r in conn.execute(select(table(name)).order_by(table(name).c.id)).mappings()]
            for name in ('placements','placement_terms','mentor_assignments')}


def test_populated_upgrade_preserves_canonical_rows_without_creating_consents_or_verified_starts():
    with populated_database() as (engine,migrate):
        migrate('0013_enrollment_verification')
        with engine.begin() as conn:
            good=old_placement(conn)
            bad=old_placement(conn,'PART_TIME')
            before=snapshot(conn)
        migrate('head')
        with engine.begin() as conn:
            assert snapshot(conn)==before
            intakes=conn.execute(select(table('placement_intakes'))).mappings().all()
            assert len(intakes)==2 and {r['origin'] for r in intakes}=={'LEGACY_IMPORT'}
            assert all(r['actor_id'] is None and r['session_id'] is None for r in intakes)
            assert conn.execute(text('SELECT count(*) FROM flexbridge.mentor_assignment_proofs')).scalar_one()==2
            assert conn.execute(text('SELECT count(*) FROM flexbridge.placement_consents')).scalar_one()==0
            assert conn.execute(text('SELECT count(*) FROM flexbridge.placement_admission_events')).scalar_one()==0
            for pid,tid,_ in (good,bad):
                assert conn.execute(text('SELECT flexbridge.placement_ready_for_start(:p,:t)'),{'p':pid,'t':tid}).scalar_one() is False
            marker=dict(intakes[0])
        with pytest.raises(IntegrityError,match='legacy set is closed'),engine.begin() as conn:
            conn.execute(table('placement_intakes').insert().values(**marker))
        with pytest.raises(IntegrityError),engine.begin() as conn:
            conn.execute(table('placement_intakes').delete())


def test_failed_populated_upgrade_rolls_back_new_proof_tables_and_keeps_old_rows():
    with populated_database() as (engine,migrate):
        migrate('0013_enrollment_verification')
        with engine.begin() as conn:
            old_placement(conn)
            before=snapshot(conn)
            conn.execute(text('CREATE TABLE flexbridge.placement_consents(marker text)'))
            conn.execute(text("INSERT INTO flexbridge.placement_consents VALUES ('keep me')"))
        failed=migrate('head',False)
        assert failed.returncode!=0 and 'placement_consents' in failed.stderr
        with engine.begin() as conn:
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one()=='0013_enrollment_verification'
            assert snapshot(conn)==before
            assert conn.execute(text("SELECT to_regclass('flexbridge.placement_intakes')")).scalar_one() is None
            assert conn.execute(text("SELECT to_regclass('flexbridge.mentor_assignment_proofs')")).scalar_one() is None
            assert conn.execute(text('SELECT marker FROM flexbridge.placement_consents')).scalar_one()=='keep me'
