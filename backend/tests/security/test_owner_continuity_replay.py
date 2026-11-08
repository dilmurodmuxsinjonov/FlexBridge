"""Matching intake receipts must close stale pending intent without reviving authority."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func
from app.db.storage import table,transaction,now
from test_owner_continuity import setup_continuity,submit,ready,decide
from test_owner_additions import has_owner

@pytest.mark.parametrize('change',['contact','staff_grant'])
def test_matching_intake_replay_closes_stale_case_and_tracking(client,setup_continuity,change):
    flow=setup_continuity;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id']
    with transaction() as conn:
        if change=='contact':
            conn.execute(table('user_contacts').update().where(table('user_contacts').c.id==flow['contact']['id']).values(revoked_at=now()))
        else:
            conn.execute(table('org_role_grants').update().where(table('org_role_grants').c.membership_id==flow['member']).values(revoked_at=now()))
    response=submit(client,flow)
    assert response.status_code==202 and response.json()['status']=='EXPIRED' and response.json()['idempotent_replay'],response.text
    with transaction() as conn:
        assert conn.execute(select(table('verification_cases').c.status).where(table('verification_cases').c.id==case)).scalar_one()=='EXPIRED'
        assert conn.execute(select(table('recovery_requests').c.status)).scalar_one()=='EXPIRED'
    assert not has_owner(flow['member'])

def test_parallel_matching_stale_replays_close_once(client,setup_continuity):
    flow=setup_continuity;response=submit(client,flow);assert response.status_code==202,response.text
    case=response.json()['id']
    with transaction() as conn:
        conn.execute(table('user_contacts').update().where(table('user_contacts').c.id==flow['contact']['id']).values(revoked_at=now()))
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:submit(client,flow),range(2)))
    assert all(r.status_code==202 and r.json()['status']=='EXPIRED' and r.json()['idempotent_replay'] for r in responses),[r.json() for r in responses]
    with transaction() as conn:
        audit=table('audit_events')
        assert conn.execute(select(func.count()).select_from(audit).where(audit.c.object_key==case,audit.c.action=='OWNER_CONTINUITY_EXPIRED')).scalar_one()==1
    assert not has_owner(flow['member'])

def test_finalized_matching_intake_remains_a_read_only_receipt(client,setup_continuity):
    flow=setup_continuity;case=ready(client,flow);response=decide(client,flow,case,'compliance')
    assert response.status_code==200 and response.json()['status']=='APPROVED',response.text
    with transaction() as conn:
        conn.execute(table('user_contacts').update().where(table('user_contacts').c.id==flow['contact']['id']).values(revoked_at=now()))
    response=submit(client,flow)
    assert response.status_code==202 and response.json()['status']=='APPROVED' and response.json()['idempotent_replay'],response.text
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('org_ownership_events'))).scalar_one()==1
        assert conn.execute(select(table('recovery_requests').c.status)).scalar_one()=='COMPLETED'
    assert has_owner(flow['member'])
