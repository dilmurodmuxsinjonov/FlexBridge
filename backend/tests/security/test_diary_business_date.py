"""SQL submission dates must use the R1 business calendar, independent of server timezone."""
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.storage import table, transaction, now
from app.services.placements import insert_row
from test_admission_lifecycle import planned, accept_sides, terms_request
from test_internship_admission import post


@pytest.mark.parametrize('timezone',['Etc/GMT+12','Pacific/Kiritimati'])
@pytest.mark.parametrize('day_offset',[0,1])
def test_sql_diary_accepts_business_today_and_rejects_business_tomorrow(
    client,identities,organization,timezone,day_offset):
    candidate,host,mentor,p,assignment=planned(client,identities,organization)
    accept_sides(client,candidate,mentor,p,assignment,p)
    post(client,'/api/v1/placements/'+p['id']+'/host-decisions',host,{**terms_request(p),'action':'ACTIVATE'},200)
    with transaction() as conn:
        conn.execute(text("SELECT set_config('TimeZone',:zone,true)"),{'zone':timezone})
        today=conn.execute(text("SELECT (clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date")).scalar_one()
        day=today+timedelta(days=day_offset)
        daily=insert_row(conn,'daily_logs',placement_id=p['id'],local_date=day,version=1)
        revision=insert_row(conn,'log_revisions',daily_log_id=daily['id'],revision=1,terms_id=p['current_terms_id'],
            author_id=candidate['user_id'],day_type='WORKED',summary='Controlled SQL date boundary',total_minutes=60,
            status='DRAFT',idempotency_key=str(uuid4()))
        insert_row(conn,'log_task_entries',revision_id=revision['id'],result_text='Actual work',minutes=60)
        conn.execute(table('daily_logs').update().where(table('daily_logs').c.id==daily['id']).values(current_revision_id=revision['id']))
    def submit():
        with transaction() as conn:
            conn.execute(text("SELECT set_config('TimeZone',:zone,true)"),{'zone':timezone})
            conn.execute(table('log_revisions').update().where(table('log_revisions').c.id==revision['id'])
                .values(status='SUBMITTED',submitted_at=now()))
    if day_offset:
        with pytest.raises(IntegrityError):submit()
    else:submit()
