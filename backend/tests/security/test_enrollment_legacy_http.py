"""Pre-upgrade imported history, then actual-session HTTP after forward migration."""
from datetime import date, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.db import storage
from app.services.placements import insert_row
from test_enrollment_migration import new_institution
from test_institution_migration import populated_database


@pytest.mark.parametrize('state',['current_verified','future_verified','pending'])
def test_captured_legacy_history_can_end_without_inventing_public_review(client,identities,state):
    with populated_database() as (engine,migrate):
        migrate('0012_file_storage_versions')
        previous_engine=storage._ENGINE
        try:
            # Separate disposable database; restore the session fixture's engine even on failure.
            storage._ENGINE=engine
            owner=identities()
            start=date.today()+timedelta(days=30) if state=='future_verified' else date.today()-timedelta(days=30)
            with engine.begin() as conn:
                institution=new_institution(conn)
                enrollment=insert_row(conn,'enrollments',candidate_id=owner['candidate_id'],institution_id=institution['id'],
                    program='Imported education history',start_date=start,status='PENDING' if state=='pending' else 'VERIFIED')
            migrate('head')
            detail=client.get('/api/v1/me/enrollments/'+enrollment['id'],headers=owner['headers'])
            assert detail.status_code==200,detail.text
            assert detail.json()['verification_origin']=='LEGACY_IMPORT' and detail.json()['reviewed'] is False
            assert detail.json()['current_student']==(state=='current_verified')
            body={'idempotency_key':str(uuid4()),'reason':'I end this imported education while preserving its history.'}
            response=client.post('/api/v1/me/enrollments/'+enrollment['id']+'/end',json=body,headers=owner['headers'])
            assert response.status_code==200,response.text
            retry=client.post('/api/v1/me/enrollments/'+enrollment['id']+'/end',json=body,headers=owner['headers'])
            assert retry.status_code==200 and retry.json()==response.json()
            current=client.get('/api/v1/me/enrollments/'+enrollment['id'],headers=owner['headers'])
            assert current.status_code==200 and current.json()['current_student'] is False
            assert current.json()['status']==('WITHDRAWN' if state=='pending' else 'ENDED')
            assert client.get('/api/v1/me/candidate',headers=owner['headers']).status_code==200
            with engine.begin() as conn:
                marker=conn.execute(select(storage.table('enrollment_origins'))).mappings().one()
                assert marker['origin']=='LEGACY_IMPORT' and marker['case_id'] is None
                assert marker['initial_snapshot']['status']==('PENDING' if state=='pending' else 'VERIFIED')
                assert conn.execute(select(storage.table('verification_cases').c.id)).first() is None
                assert conn.execute(select(storage.table('enrollment_submissions').c.case_id)).first() is None
                event=conn.execute(select(storage.table('enrollment_events'))).mappings().one()
                assert event['case_id'] is None and event['revision'] is None
                assert conn.execute(select(storage.table('candidate_profiles').c.id)).scalar_one()==owner['candidate_id']
                saved=conn.execute(select(storage.table('enrollments')).where(storage.table('enrollments').c.id==enrollment['id'])).mappings().one()
                assert saved['program']==enrollment['program'] and saved['start_date']==start
                assert saved['end_date'] is None or saved['end_date']>=start
        finally:
            storage._ENGINE=previous_engine
