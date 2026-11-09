"""Populated0010 upgrade, collision rollback and real structural/history guards."""
from contextlib import contextmanager
from datetime import date,timedelta
import os
from pathlib import Path
import secrets
import subprocess
import sys
from uuid import uuid4
import psycopg
from psycopg import sql
import pytest
from sqlalchemy import create_engine,select,text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from app.db.storage import table,transaction,now
from app.services.placements import insert_row
from test_institution_authority import setup_scope

ROOT=Path(__file__).resolve().parents[3]


@contextmanager
def populated_database():
    admin=make_url(os.environ['FLEXBRIDGE_TEST_ADMIN_URL']);name='flexbridge_upgrade_'+secrets.token_hex(6)
    conn=psycopg.connect(admin.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True)
    conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    test_url=admin.set(database=name).render_as_string(hide_password=False)
    engine=create_engine(test_url,connect_args={'prepare_threshold':None},hide_parameters=True)
    env={**os.environ,'DATABASE_URL':test_url};env.pop('FLEXBRIDGE_DATABASE_URL',None)
    def migrate(target,check=True):
        return subprocess.run([sys.executable,'-m','alembic','-c',str(ROOT/'backend/alembic.ini'),'upgrade',target],
            cwd=ROOT,env=env,capture_output=True,text=True,check=check)
    try:
        migrate('0010_owner_continuity')
        yield engine,migrate
    finally:
        engine.dispose()
        assert name.startswith('flexbridge_upgrade_')
        conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)));conn.close()


def seed_old_scope(conn,*,mismatch=False,registry=None):
    user=insert_row(conn,'users',display_name='Legacy appointed user',status='ACTIVE',locale='uz',timezone='Asia/Tashkent',auth_version=1)
    other=insert_row(conn,'users',display_name='Legacy different user',status='ACTIVE',locale='uz',timezone='Asia/Tashkent',auth_version=1)
    inst=dict(id=str(uuid4()),created_at=now(),updated_at=now(),registry_code=registry or str(uuid4()),name='Legacy institution',region='Tashkent',status='VERIFIED')
    conn.execute(table('institutions').insert().values(**inst))
    file=insert_row(conn,'files',owner_user_id=user['id'],filename='appointment.pdf',mime_type='application/pdf',storage_key='private/legacy/'+str(uuid4()),
        byte_size=100,sha256='a'*64,scan_status='CLEAN',retention_class='VERIFICATION_EVIDENCE',object_version='trusted-legacy-version',scanned_at=now())
    member=insert_row(conn,'institution_memberships',institution_id=inst['id'],user_id=user['id'],status='ACTIVE',accepted_at=now())
    appointment=insert_row(conn,'institution_appointments',institution_id=inst['id'],user_id=other['id'] if mismatch else user['id'],document_file_id=file['id'],
        status='ACTIVE',valid_from=date.today()-timedelta(days=30),valid_to=date.today()+timedelta(days=30),accepted_at=now())
    roles=table('role_catalog');rid=conn.execute(select(roles.c.id).where(roles.c.scope_kind=='INSTITUTION',roles.c.code=='COORDINATOR')).scalar_one_or_none()
    if not rid:rid=insert_row(conn,'role_catalog',code='COORDINATOR',scope_kind='INSTITUTION',description='Legacy coordinator')['id']
    grant=insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=rid,appointment_id=appointment['id'])
    return user,inst,member,appointment,grant


def test_populated_upgrade_closes_invalid_grant_preserves_history_and_valid_authority():
    from app.db.institution_scope import institution_scope_query
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:
            bad=seed_old_scope(conn,mismatch=True);good=seed_old_scope(conn)
        migrate('head')
        with engine.begin() as conn:
            grants=table('institution_role_grants')
            badrow=conn.execute(select(grants).where(grants.c.id==bad[4]['id'])).mappings().one()
            goodrow=conn.execute(select(grants).where(grants.c.id==good[4]['id'])).mappings().one()
            assert badrow['revoked_at'] is not None and goodrow['revoked_at'] is None
            assert badrow['appointment_id']==bad[3]['id'] and badrow['membership_id']==bad[2]['id']
            assert conn.execute(institution_scope_query(bad[0]['id'],bad[1]['id'],('COORDINATOR',))).first() is None
            assert conn.execute(institution_scope_query(good[0]['id'],good[1]['id'],('COORDINATOR',))).first()
            audits=table('audit_events')
            event=conn.execute(select(audits).where(audits.c.action=='INSTITUTION_LEGACY_SCOPE_CLOSED',audits.c.object_key==bad[4]['id'])).mappings().one()
            assert event['actor_id'] is None and event['scope_snapshot']['migration']=='0011_institution_onboarding'
            assert conn.execute(select(table('institution_appointments').c.verification_case_id).where(table('institution_appointments').c.id==bad[3]['id'])).scalar_one() is None
            assert conn.execute(text('SELECT count(*) FROM flexbridge.institution_onboarding_consents')).scalar_one()==0


def test_normalized_registry_collision_aborts_whole_upgrade_without_merging():
    with populated_database() as (engine,migrate):
        with engine.begin() as conn:
            first=seed_old_scope(conn,registry='LEGACY-101');second=seed_old_scope(conn,registry=' legacy-101 ')
        failed=migrate('head',False)
        assert failed.returncode!=0 and 'registry normalization collision' in failed.stderr
        with engine.begin() as conn:
            assert conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one()=='0010_owner_continuity'
            assert conn.execute(text("SELECT to_regclass('flexbridge.institution_onboarding_requests')")).scalar_one() is None
            rows=conn.execute(select(table('institutions').c.registry_code).where(table('institutions').c.id.in_([first[1]['id'],second[1]['id']]))).scalars().all()
            assert set(rows)=={'LEGACY-101',' legacy-101 '}


def test_new_mismatched_grant_is_rejected_and_grant_history_cannot_be_rewritten(identities):
    user,other,inst,foreign,member,appointment,grant=setup_scope(identities)
    with pytest.raises(IntegrityError),transaction() as conn:
        invalid=insert_row(conn,'institution_appointments',institution_id=foreign['id'],user_id=other['user_id'],document_file_id=appointment['document_file_id'],
            status='ACTIVE',valid_from=date.today(),accepted_at=now())
        insert_row(conn,'institution_role_grants',membership_id=member['id'],role_id=grant['role_id'],appointment_id=invalid['id'])
    with transaction() as conn:
        g=table('institution_role_grants');stamp=now();conn.execute(g.update().where(g.c.id==grant['id']).values(revoked_at=stamp))
    with pytest.raises(IntegrityError),transaction() as conn:
        conn.execute(g.update().where(g.c.id==grant['id']).values(revoked_at=None))
    with transaction() as conn:
        assert conn.execute(select(g.c.revoked_at).where(g.c.id==grant['id'])).scalar_one()==stamp


def test_new_parent_retargeting_is_rejected_and_valid_scope_survives(identities):
    user,other,inst,foreign,member,appointment,grant=setup_scope(identities)
    for name,key,values in [('institution_appointments',appointment['id'],{'user_id':other['user_id']}),
        ('institution_memberships',member['id'],{'institution_id':foreign['id']})]:
        with pytest.raises(IntegrityError),transaction() as conn:
            t=table(name);conn.execute(t.update().where(t.c.id==key).values(**values))
    from app.db.institution_scope import institution_scope_query
    with transaction() as conn:assert conn.execute(institution_scope_query(user['user_id'],inst['id'],('COORDINATOR',))).first()
