"""Dedicated disposable PostgreSQL: preserve ownership/grant history while upgrading0008->0009."""
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
    if result.returncode:raise RuntimeError('Migration failed; connection details withheld')

try:
    upgrade('0008_owner_additions')
    with psycopg.connect(url.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True) as db:
        owner,target,moderator,org,owner_member,target_member,case,event,old_grant=[uuid4() for _ in range(9)]
        for uid in (owner,target,moderator):
            db.execute("INSERT INTO flexbridge.users(id,display_name,status,locale,timezone) VALUES(%s,'Upgrade fixture','ACTIVE','uz','Asia/Tashkent')",(uid,))
        db.execute("INSERT INTO flexbridge.organizations(id,tax_id,legal_name,public_name,region,status) VALUES(%s,%s,'Upgrade fixture','Upgrade fixture','Tashkent','VERIFIED')",(org,str(100000000+secrets.randbelow(900000000))))
        for mid,uid in ((owner_member,owner),(target_member,target)):
            db.execute("INSERT INTO flexbridge.org_memberships(id,organization_id,user_id,status,accepted_at) VALUES(%s,%s,%s,'ACTIVE',now())",(mid,org,uid))
        owner_role=db.execute("SELECT id FROM flexbridge.role_catalog WHERE code='OWNER' AND scope_kind='ORG'").fetchone()[0]
        staff_role=db.execute("SELECT id FROM flexbridge.role_catalog WHERE code='HR' AND scope_kind='ORG'").fetchone()[0]
        db.execute('INSERT INTO flexbridge.org_role_grants(id,membership_id,role_id,granted_by_id) VALUES(%s,%s,%s,%s)',(uuid4(),owner_member,owner_role,moderator))
        db.execute('INSERT INTO flexbridge.org_role_grants(id,membership_id,role_id,granted_by_id) VALUES(%s,%s,%s,%s)',(uuid4(),target_member,staff_role,owner))
        db.execute('INSERT INTO flexbridge.org_role_grants(id,membership_id,role_id,granted_by_id,revoked_at) VALUES(%s,%s,%s,%s,now())',(old_grant,target_member,owner_role,moderator))
        db.execute("INSERT INTO flexbridge.verification_cases(id,requester_id,organization_id,kind,status,current_revision,assigned_reviewer_id,due_at,decided_at) VALUES(%s,%s,%s,'ORG_REPRESENTATIVE','APPROVED',1,%s,now(),now())",(case,owner,org,moderator))
        # Platform MODERATOR is supplied by explicit trusted test metadata, not seeded in0008.
        moderator_role=uuid4()
        db.execute("INSERT INTO flexbridge.role_catalog(id,code,scope_kind,description) VALUES(%s,'MODERATOR','PLATFORM','Upgrade fixture')",(moderator_role,))
        db.execute("INSERT INTO flexbridge.platform_role_grants(id,user_id,role_id,granted_by_id,expires_at) VALUES(%s,%s,%s,%s,now()+interval '1 day')",(uuid4(),moderator,moderator_role,owner))
        db.execute('INSERT INTO flexbridge.org_ownership_events(id,organization_id,new_membership_id,verification_case_id,approved_by_id,effective_at) VALUES(%s,%s,%s,%s,%s,now())',(event,org,owner_member,case,moderator))
        grant_before=db.execute('SELECT row_to_json(g)::text FROM flexbridge.org_role_grants g WHERE id=%s',(old_grant,)).fetchone()[0]
        event_before=db.execute('SELECT row_to_json(e)::text FROM flexbridge.org_ownership_events e WHERE id=%s',(event,)).fetchone()[0]
        before_count=db.execute("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'").fetchone()[0]
        proof_before=db.execute("SELECT pg_get_functiondef('flexbridge.guard_owner_event_proof()'::regprocedure)").fetchone()[0]
        upgrade('0009_owner_transfers')
        proof_after=db.execute("SELECT pg_get_functiondef('flexbridge.guard_owner_event_proof()'::regprocedure)").fetchone()[0]
        grant_after=db.execute('SELECT row_to_json(g)::text FROM flexbridge.org_role_grants g WHERE id=%s',(old_grant,)).fetchone()[0]
        event_after=db.execute('SELECT row_to_json(e)::text FROM flexbridge.org_ownership_events e WHERE id=%s',(event,)).fetchone()[0]
        after_count=db.execute("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'").fetchone()[0]
        new_grant=uuid4()
        db.execute('INSERT INTO flexbridge.org_role_grants(id,membership_id,role_id,granted_by_id) VALUES(%s,%s,%s,%s)',(new_grant,target_member,owner_role,moderator))
        duplicate_blocked=False
        try:db.execute('INSERT INTO flexbridge.org_role_grants(id,membership_id,role_id,granted_by_id) VALUES(%s,%s,%s,%s)',(uuid4(),target_member,owner_role,moderator))
        except psycopg.errors.UniqueViolation:duplicate_blocked=True
        immutable=False
        try:db.execute('UPDATE flexbridge.org_ownership_events SET effective_at=now() WHERE id=%s',(event,))
        except psycopg.errors.CheckViolation:immutable=True
        result=dict(from_revision='0008_owner_additions',to_revision='0009_owner_transfers',tables_before=before_count,
            tables_after=after_count,prior_addition_proof_function_preserved=proof_before==proof_after,revoked_grant_preserved=grant_before==grant_after,ownership_event_preserved=event_before==event_after,
            fresh_active_grant_id_differs=new_grant!=old_grant,duplicate_active_grant_blocked=duplicate_blocked,ownership_event_mutation_blocked=immutable,
            scope='Synthetic populated legacy history and privileged SQL index probe, not an HTTP grant or legal identity proof')
        assert before_count==103 and after_count==105 and all(result[k] for k in ('prior_addition_proof_function_preserved','revoked_grant_preserved','ownership_event_preserved',
            'fresh_active_grant_id_differs','duplicate_active_grant_blocked','ownership_event_mutation_blocked'))
        (Path(__file__).parent/'upgrade.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result))
finally:
    connection.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
    connection.close()
