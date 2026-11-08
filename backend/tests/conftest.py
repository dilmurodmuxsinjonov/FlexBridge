"""Each test runs against a freshly emptied, disposable migrated PostgreSQL database."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
from datetime import timedelta
from uuid import uuid4
import psycopg
from psycopg import sql
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='session',autouse=True)
def database():
    url=os.environ.get('FLEXBRIDGE_TEST_ADMIN_URL')
    if not url:
        pytest.fail('Set FLEXBRIDGE_TEST_ADMIN_URL to an isolated PostgreSQL test server (createdb privilege required)')
    admin=make_url(url)
    name='flexbridge_test_'+secrets.token_hex(5)
    conn=psycopg.connect(admin.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True)
    conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    test_url=admin.set(database=name).render_as_string(hide_password=False)
    previous=os.environ.get('DATABASE_URL'); previous_fb=os.environ.pop('FLEXBRIDGE_DATABASE_URL',None)
    os.environ['DATABASE_URL']=test_url
    os.environ['PAYMENT_WEBHOOK_SECRET']=secrets.token_urlsafe(48)
    os.environ['AUTH_HMAC_KEY']=secrets.token_urlsafe(48)
    os.environ['TERMS_POLICY_VERSION']='test-terms-v1'
    os.environ['PRIVACY_POLICY_VERSION']='test-privacy-v1'
    os.environ['WEBAUTHN_RP_ID']='localhost'
    os.environ['WEBAUTHN_ORIGIN']='http://localhost:8000'
    from cryptography.fernet import Fernet
    os.environ['MFA_ENCRYPTION_KEY']=Fernet.generate_key().decode()
    try:
        subprocess.run([sys.executable,'-m','alembic','-c',str(ROOT/'backend/alembic.ini'),'upgrade','head'],check=True,cwd=ROOT,capture_output=True)
        from app.db import storage
        if storage._ENGINE is not None: storage._ENGINE.dispose()
        storage._ENGINE=None
        storage.init_storage()
        yield
    finally:
        from app.db import storage
        if storage._ENGINE is not None: storage._ENGINE.dispose()
        storage._ENGINE=None
        conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name))); conn.close()
        if previous is None: os.environ.pop('DATABASE_URL',None)
        else: os.environ['DATABASE_URL']=previous
        if previous_fb: os.environ['FLEXBRIDGE_DATABASE_URL']=previous_fb

@pytest.fixture(autouse=True)
def clean_database(database):
    from app.db.storage import get_engine
    engine=get_engine()
    assert make_url(str(engine.url)).database.startswith('flexbridge_test_')
    with engine.begin() as conn:
        # Role catalog is migration-seeded reference data; grants and all mutable state are emptied.
        names=conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='flexbridge' AND tablename NOT IN ('circuit_breaker_state','role_catalog')")).scalars().all()
        quoted=','.join('flexbridge."'+n.replace('"','""')+'"' for n in names)
        conn.execute(text('TRUNCATE '+quoted+' CASCADE'))
        conn.execute(text("UPDATE flexbridge.circuit_breaker_state SET state='CLOSED',incident_id=NULL,reason_code=NULL"))

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c: yield c

@pytest.fixture
def identities():
    from app.services.auth import auth_service,generate_totp_code
    from app.db.storage import table,transaction,now
    from app.api.dependencies import ActorContext,candidate_id_for
    def create(role=None,org=None):
        user=auth_service.register_user(display_name='Test User',password='correct-passphrase-2026',adult_confirmed=True)
        uid=user['id']
        with transaction() as conn:
            if role:
                rid=str(uuid4()); scope='ORG' if org else 'PLATFORM'
                existing=conn.execute(table('role_catalog').select().where(table('role_catalog').c.code==role,table('role_catalog').c.scope_kind==scope)).mappings().first()
                if existing: rid=existing['id']
                else: conn.execute(table('role_catalog').insert().values(id=rid,created_at=now(),updated_at=now(),code=role,scope_kind=scope,description=role))
                if org:
                    mid=str(uuid4())
                    conn.execute(table('org_memberships').insert().values(id=mid,created_at=now(),updated_at=now(),organization_id=org,user_id=uid,status='ACTIVE'))
                    conn.execute(table('org_role_grants').insert().values(id=str(uuid4()),created_at=now(),updated_at=now(),membership_id=mid,role_id=rid,granted_by_id=uid))
                else:
                    conn.execute(table('platform_role_grants').insert().values(id=str(uuid4()),created_at=now(),updated_at=now(),user_id=uid,role_id=rid,
                        granted_by_id=auth_service.register_user(display_name='Test Grantor',password='grantor-passphrase-2026',adult_confirmed=True)['id'],expires_at=now()+timedelta(hours=1)))
        totp_secret=None
        if role:
            totp_secret=auth_service.enroll_totp(uid,'correct-passphrase-2026')
            auth_service.confirm_totp(uid,generate_totp_code(totp_secret))
        session=auth_service.login(user_id=uid,password='correct-passphrase-2026',totp_code=generate_totp_code(totp_secret) if totp_secret else None)
        return {'user_id':uid,'candidate_id':candidate_id_for(ActorContext(uid,'',())),'totp_secret':totp_secret,**session,'headers':{'Authorization':'Bearer '+session['access_token']}}
    return create

@pytest.fixture
def organization():
    from app.db.storage import table,transaction,now
    oid=str(uuid4())
    with transaction() as conn:
        conn.execute(table('organizations').insert().values(id=oid,created_at=now(),updated_at=now(),tax_id=secrets.token_hex(8),
            legal_name='Test Company',public_name='Test Company',region='Tashkent',status='VERIFIED'))
        # Explicit trusted fixtures, not public runtime provisioning or real verification.
        from app.services.placements import insert_row
        requester=insert_row(conn,'users',display_name='Fixture requester',status='ACTIVE',locale='uz',timezone='Asia/Tashkent')
        reviewer=insert_row(conn,'users',display_name='Fixture reviewer',status='ACTIVE',locale='uz',timezone='Asia/Tashkent')
        for code in ('JOB_EMPLOYER','INTERNSHIP_HOST'):
            case=insert_row(conn,'verification_cases',requester_id=requester['id'],organization_id=oid,kind=code,
                status='APPROVED',current_revision=1,assigned_reviewer_id=reviewer['id'],due_at=now(),decided_at=now())
            insert_row(conn,'organization_capabilities',organization_id=oid,capability=code,status='ACTIVE',approved_case_id=case['id'])
    return oid
