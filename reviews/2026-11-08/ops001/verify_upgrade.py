"""Run only against an explicit dedicated test admin server; creates/drops one random DB."""
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

root=Path(__file__).resolve().parents[3]
admin=make_url(os.environ['FLEXBRIDGE_TEST_ADMIN_URL'])
name='flexbridge_test_'+secrets.token_hex(5)
connection=psycopg.connect(admin.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True)
connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
url=admin.set(database=name)
env={**os.environ,'DATABASE_URL':url.render_as_string(hide_password=False)}
env.pop('FLEXBRIDGE_DATABASE_URL',None)

def upgrade(revision):
    result=subprocess.run([sys.executable,'-m','alembic','-c',str(root/'backend/alembic.ini'),'upgrade',revision],
        cwd=root,env=env,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('Migration failed; captured output intentionally withheld to avoid connection details')

try:
    upgrade('0005_org_invitations')
    with psycopg.connect(url.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True) as db:
        before_count=db.execute("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'").fetchone()[0]
        uid=uuid4()
        db.execute("INSERT INTO flexbridge.users(id,created_at,updated_at,display_name,status,locale,timezone) VALUES(%s,now(),now(),'Upgrade fixture','ACTIVE','uz','Asia/Tashkent')",(uid,))
        before=db.execute('SELECT row_to_json(u)::text FROM flexbridge.users u WHERE id=%s',(uid,)).fetchone()[0]
        upgrade('head')
        after=db.execute('SELECT row_to_json(u)::text FROM flexbridge.users u WHERE id=%s',(uid,)).fetchone()[0]
        revision=db.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        after_count=db.execute("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'").fetchone()[0]
        result=dict(from_revision='0005_org_invitations',to_revision=revision,tables_before=before_count,
            tables_after=after_count,populated_user_preserved=before==after,scope='Dedicated native PostgreSQL; representative row, no production data')
        assert before==after and before_count==99 and after_count==100 and revision=='0006_retention_evaluations'
        (Path(__file__).parent/'upgrade.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result))
finally:
    connection.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
    connection.close()
