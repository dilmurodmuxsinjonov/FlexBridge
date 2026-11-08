"""Dedicated random database: preserve a populated rejection while upgrading0006->0007."""
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
    upgrade('0006_retention_evaluations')
    with psycopg.connect(url.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True) as db:
        owner,moderator,org,opp,rev,case,action=[uuid4() for _ in range(7)]
        for uid in (owner,moderator):
            db.execute("INSERT INTO flexbridge.users(id,display_name,status,locale,timezone) VALUES(%s,'Upgrade fixture','ACTIVE','uz','Asia/Tashkent')",(uid,))
        db.execute("INSERT INTO flexbridge.organizations(id,tax_id,legal_name,public_name,region,status) VALUES(%s,%s,'Upgrade fixture','Upgrade fixture','Tashkent','VERIFIED')",(org,str(org)))
        db.execute("INSERT INTO flexbridge.opportunities(id,organization_id,kind,status,capacity,occupied_count) VALUES(%s,%s,'PART_TIME','REJECTED',1,0)",(opp,org))
        db.execute("""INSERT INTO flexbridge.opportunity_revisions(id,opportunity_id,revision,author_id,title,description,region,
            work_mode,eligibility,currency,is_paid,start_date,schedule_policy,shift_match_mode,snapshot_schema,contract_type,
            salary_min,salary_period,salary_basis) VALUES(%s,%s,1,%s,'Upgrade fixture','Original content','Tashkent','ONSITE','OPEN',
            'UZS',true,current_date,'FIXED','ALL_SHIFTS_IN_GROUP',1,'LABOR_PART_TIME',10000,'HOUR','GROSS')""",(rev,opp,owner))
        db.execute('UPDATE flexbridge.opportunities SET current_revision_id=%s WHERE id=%s',(rev,opp))
        db.execute("INSERT INTO flexbridge.moderation_cases(id,reporter_id,opportunity_id,category,status,severity,due_at,assigned_to_id) VALUES(%s,%s,%s,'UPGRADE_FIXTURE','RESOLVED','LOW',now(),%s)",(case,moderator,opp,moderator))
        db.execute("INSERT INTO flexbridge.moderation_actions(id,case_id,actor_id,action,reason,occurred_at) VALUES(%s,%s,%s,'REJECT','Original independent rejection',now())",(action,case,moderator))
        before=db.execute('SELECT row_to_json(a)::text FROM flexbridge.moderation_actions a WHERE id=%s',(action,)).fetchone()[0]
        before_count=db.execute("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'").fetchone()[0]
        upgrade('0007_moderation_appeals')
        after=db.execute('SELECT row_to_json(a)::text FROM flexbridge.moderation_actions a WHERE id=%s',(action,)).fetchone()[0]
        after_count=db.execute("SELECT count(*) FROM pg_tables WHERE schemaname='flexbridge'").fetchone()[0]
        protected=False
        try:db.execute("UPDATE flexbridge.moderation_actions SET reason='Overwritten history' WHERE id=%s",(action,))
        except psycopg.errors.CheckViolation:protected=True
        result=dict(from_revision='0006_retention_evaluations',to_revision='0007_moderation_appeals',tables_before=before_count,
            tables_after=after_count,original_action_preserved=before==after,original_action_mutation_blocked=protected,
            scope='Dedicated native PostgreSQL with explicit synthetic populated rejection')
        assert before==after and protected and before_count==100 and after_count==101
        (Path(__file__).parent/'upgrade.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result))
finally:
    connection.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
    connection.close()
