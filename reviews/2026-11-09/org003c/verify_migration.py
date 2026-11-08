"""Fresh disposable PostgreSQL migration smoke, without application startup or acceptance claims."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT=Path(__file__).resolve().parents[3]
admin=make_url(os.environ['FLEXBRIDGE_TEST_ADMIN_URL'])
name='flexbridge_test_'+secrets.token_hex(5)
conn=psycopg.connect(admin.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True)
conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
url=admin.set(database=name)
env={**os.environ,'DATABASE_URL':url.render_as_string(hide_password=False)}
env.pop('FLEXBRIDGE_DATABASE_URL',None)
try:
    result=subprocess.run([sys.executable,'-m','alembic','-c',str(ROOT/'backend/alembic.ini'),'upgrade','head'],
        cwd=ROOT,env=env,capture_output=True,text=True)
    if result.returncode:
        # SQL traceback can contain fixture metadata, but connection credentials are withheld.
        safe=result.stderr.replace(url.render_as_string(hide_password=False),'[DATABASE_URL_REDACTED]')
        (Path(__file__).parent/'migration_error.txt').write_text(safe,encoding='utf-8')
        raise RuntimeError('Migration failed; diagnostic saved without connection URL')
    with psycopg.connect(url.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True) as db:
        revision=db.execute('SELECT version_num FROM public.alembic_version').fetchone()[0]
        count=db.execute("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'").fetchone()[0]
        roster=db.execute('SELECT flexbridge.continuity_owner_roster(%s)',('00000000-0000-0000-0000-000000000001',)).fetchone()[0]
        assert revision=='0010_owner_continuity' and count==107 and roster==[]
        evidence=dict(revision=revision,runtime_tables=count,empty_organization_roster=roster,
            scope='Fresh DDL smoke only; no application startup, live identity, quorum or grant acceptance')
        (Path(__file__).parent/'migration.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(evidence))
finally:
    conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
    conn.close()
