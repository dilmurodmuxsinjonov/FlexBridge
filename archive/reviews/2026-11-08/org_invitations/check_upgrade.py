"""Preserve 0004 data/accepted history; invalidate legacy pending role-less invitations."""
import json,os,secrets,subprocess,sys
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT=Path(__file__).resolve().parents[3]


def main():
    admin=make_url(os.environ['FLEXBRIDGE_TEST_ADMIN_URL']);name='flexbridge_test_invite_upgrade_'+secrets.token_hex(5)
    env={**os.environ,'DATABASE_URL':admin.set(database=name).render_as_string(hide_password=False)}
    env.pop('FLEXBRIDGE_DATABASE_URL',None)
    with psycopg.connect(admin.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True) as control:
        control.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            def migrate(target):
                result=subprocess.run([sys.executable,'-m','alembic','-c',str(ROOT/'backend/alembic.ini'),'upgrade',target],
                    cwd=ROOT,env=env,capture_output=True)
                assert result.returncode==0,'Synthetic migration failed'
            migrate('0004_org_onboarding')
            url=admin.set(database=name,drivername='postgresql').render_as_string(hide_password=False)
            user,org,member,pending,accepted=[str(uuid4()) for _ in range(5)]
            with psycopg.connect(url) as conn:
                conn.execute("INSERT INTO flexbridge.users(id,display_name,status,locale,timezone) VALUES (%s,'Legacy user','ACTIVE','uz','Asia/Tashkent')",(user,))
                conn.execute("INSERT INTO flexbridge.organizations(id,tax_id,legal_name,public_name,region,status) VALUES (%s,'123456789','Legacy','Legacy','Tashkent','VERIFIED')",(org,))
                conn.execute("INSERT INTO flexbridge.org_memberships(id,organization_id,user_id,status) VALUES (%s,%s,%s,'ACTIVE')",(member,org,user))
                for key,complete in ((pending,False),(accepted,True)):
                    conn.execute("INSERT INTO flexbridge.org_invitations(id,organization_id,inviter_membership_id,contact_digest,token_digest,expires_at,accepted_by_id,accepted_at) VALUES (%s,%s,%s,'synthetic-contact',%s,now()+interval '24 hours',%s,CASE WHEN %s THEN now() ELSE NULL END)",
                        (key,org,member,'synthetic-'+key,user if complete else None,complete))
            migrate('head')
            with psycopg.connect(url) as conn:
                assert conn.execute('SELECT version_num FROM public.alembic_version').fetchone()[0]=='0005_org_invitations'
                assert conn.execute('SELECT revoked_at IS NOT NULL FROM flexbridge.org_invitations WHERE id=%s',(pending,)).fetchone()[0]
                assert conn.execute('SELECT accepted_at IS NOT NULL AND revoked_at IS NULL FROM flexbridge.org_invitations WHERE id=%s',(accepted,)).fetchone()[0]
                assert conn.execute('SELECT count(*) FROM flexbridge.org_invitations').fetchone()[0]==2
                assert conn.execute('SELECT count(*) FROM flexbridge.org_role_grants').fetchone()[0]==0
            result={'head':'0005_org_invitations','legacy_pending_revoked':True,'accepted_history_preserved':True,
                'rows_preserved':2,'grants_created':0}
            Path(__file__).with_name('upgrade.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(result)
        finally:control.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))

if __name__=='__main__':main()
