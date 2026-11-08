"""Verify an incremental 0002 -> 0003 upgrade against synthetic existing accounts."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from uuid import uuid4
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from cryptography.fernet import Fernet

ROOT=Path(__file__).resolve().parents[3]

if __name__=='__main__':
    admin=make_url(os.environ['FLEXBRIDGE_TEST_ADMIN_URL'])
    name='flexbridge_test_upgrade_'+secrets.token_hex(5)
    connection=psycopg.connect(admin.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True)
    connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    env={**os.environ,'DATABASE_URL':admin.set(database=name).render_as_string(hide_password=False)}
    env.pop('FLEXBRIDGE_DATABASE_URL',None)
    try:
        command=[sys.executable,'-m','alembic','-c',str(ROOT/'backend/alembic.ini'),'upgrade']
        subprocess.run(command+['0002_security_runtime'],env=env,cwd=ROOT,check=True,capture_output=True)
        sys.path.insert(0,str(ROOT/'backend'))
        from app.services.auth import hash_password
        password_hash=hash_password('synthetic-legacy-password')
        cipher=Fernet(Fernet.generate_key());encrypted=cipher.encrypt(b'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ').decode()
        users=[str(uuid4()),str(uuid4())];tokens=[secrets.token_urlsafe(32) for _ in range(3)];sessions=[str(uuid4()) for _ in tokens]
        url=admin.set(database=name,drivername='postgresql').render_as_string(hide_password=False)
        with psycopg.connect(url) as db:
            for uid in users:
                db.execute("INSERT INTO flexbridge.users(id,display_name,status,password_hash,locale,timezone,adult_declared_at) VALUES (%s,'Synthetic existing user','ACTIVE',%s,'uz','Asia/Tashkent',now())",(uid,password_hash))
            db.execute("INSERT INTO flexbridge.mfa_credentials(id,user_id,kind,credential_key,secret_encrypted,sign_count,verified_at) VALUES (%s,%s,'TOTP',%s,%s,0,now())",(str(uuid4()),users[1],str(uuid4()),encrypted))
            for index,(uid,assurance) in enumerate([(users[0],'PASSWORD'),(users[1],'PASSWORD'),(users[1],'MFA')]):
                db.execute("INSERT INTO flexbridge.sessions(id,user_id,token_digest,assurance,expires_at,last_seen_at) VALUES (%s,%s,%s,%s,now()+interval '1 hour',now())",
                    (sessions[index],uid,hashlib.sha256(tokens[index].encode()).hexdigest(),assurance))
        subprocess.run(command+['head'],env=env,cwd=ROOT,check=True,capture_output=True)
        with psycopg.connect(url) as db:
            records=db.execute('SELECT id,password_hash,auth_version FROM flexbridge.users ORDER BY id').fetchall()
            assert len(records)==2 and all(row[1]==password_hash and row[2]==1 for row in records)
            assert db.execute('SELECT secret_encrypted FROM flexbridge.mfa_credentials').fetchone()[0]==encrypted
            rows=dict(db.execute('SELECT id::text,revoked_at IS NOT NULL FROM flexbridge.sessions').fetchall())
            assert rows[sessions[0]] is False and rows[sessions[1]] is True and rows[sessions[2]] is False
            assert db.execute('SELECT version_num FROM public.alembic_version').fetchone()[0]=='0003_iam_flows'
        report={'upgrade':'0002_security_runtime -> 0003_iam_flows','existing_users_preserved':2,
            'password_hashes_preserved':True,'encrypted_totp_preserved':True,'legacy_pre_mfa_session_revoked':True,
            'existing_mfa_session_preserved':True,'ordinary_password_session_preserved':True,'synthetic_database_only':True}
        (Path(__file__).parent/'upgrade.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
    finally:
        assert name.startswith('flexbridge_test_upgrade_')
        connection.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)));connection.close()
