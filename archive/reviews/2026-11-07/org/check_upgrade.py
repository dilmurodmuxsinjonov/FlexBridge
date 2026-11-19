"""Check populated 0003 upgrades and normalized-tax conflicts in disposable databases."""
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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services.auth import hash_password


def main():
    admin = make_url(os.environ['FLEXBRIDGE_TEST_ADMIN_URL'])
    results = {}
    with psycopg.connect(admin.set(drivername='postgresql').render_as_string(hide_password=False), autocommit=True) as control:
        for scenario in ('preserve', 'conflict'):
            name = 'flexbridge_test_org_upgrade_' + secrets.token_hex(5)
            control.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
            env = {**os.environ, 'DATABASE_URL': admin.set(database=name).render_as_string(hide_password=False)}
            env.pop('FLEXBRIDGE_DATABASE_URL', None)
            def migrate(target):
                return subprocess.run([sys.executable, '-m', 'alembic', '-c', str(ROOT/'backend/alembic.ini'),
                    'upgrade', target], cwd=ROOT, env=env, capture_output=True, text=True)
            try:
                assert migrate('0003_iam_flows').returncode == 0
                url = admin.set(database=name, drivername='postgresql').render_as_string(hide_password=False)
                uid = str(uuid4()); password_hash = hash_password('upgrade-test-only-password-2026')
                with psycopg.connect(url) as conn:
                    conn.execute("INSERT INTO flexbridge.users(id,display_name,password_hash,status,locale,timezone) VALUES (%s,'Legacy user',%s,'ACTIVE','uz','Asia/Tashkent')", (uid,password_hash))
                    identifiers = ['123-456-789','123 456 789'] if scenario == 'conflict' else ['123-456-789']
                    for value in identifiers:
                        conn.execute("INSERT INTO flexbridge.organizations(id,tax_id,legal_name,public_name,region,status) VALUES (%s,%s,'Legacy legal','Legacy public','Tashkent','VERIFIED')",(str(uuid4()),value))
                migrated = migrate('head')
                with psycopg.connect(url) as conn:
                    version = conn.execute('SELECT version_num FROM public.alembic_version').fetchone()[0]
                    preserved = conn.execute('SELECT password_hash FROM flexbridge.users WHERE id=%s',(uid,)).fetchone()[0] == password_hash
                    count = conn.execute('SELECT count(*) FROM flexbridge.organizations').fetchone()[0]
                    if scenario == 'preserve':
                        assert migrated.returncode == 0 and version == '0004_org_onboarding' and preserved and count == 1
                        assert conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'").fetchone()[0] == 99
                        results[scenario] = {'exit_code':0,'revision':version,'user_hash_preserved':preserved,'organizations_preserved':count}
                    else:
                        assert migrated.returncode != 0 and version == '0003_iam_flows' and preserved and count == 2
                        results[scenario] = {'upgrade_rejected':True,'revision_unchanged':version,'organizations_preserved':count}
            finally:
                control.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
    results['disposable_databases_removed'] = True
    Path(__file__).with_name('upgrade.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results))


if __name__ == '__main__':
    main()
