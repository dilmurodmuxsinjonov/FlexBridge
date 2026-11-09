"""Current actor survives no completed logout while waiting for admission material."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,text
from app.db.storage import get_engine,table,transaction
from test_internship_admission import accepted_offer,post
from test_org_authority_transactions import wait_for_blocker


def admission_snapshot():
    with transaction() as conn:
        result={}
        for name in ('placements','placement_terms','placement_decisions','mentor_assignments'):
            result[name]=[dict(row) for row in conn.execute(select(table(name)).order_by(table(name).c.id)).mappings()]
        audit=table('audit_events')
        result['audit']=[dict(row) for row in conn.execute(select(audit).where(audit.c.action.like('MENTOR_%')).order_by(audit.c.id)).mappings()]
        return result


@pytest.mark.parametrize('kind',['create','nominate'])
def test_completed_logout_after_real_business_wait_denies_admission_write(client,identities,organization,kind):
    _,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    if kind=='create':
        material_name='offers';material_id=body['offer_id']
        request=lambda:client.post('/api/v1/placements',json=body,headers=host['headers'])
    else:
        placement=post(client,'/api/v1/placements',host,body,201)
        mentor=identities('MENTOR',organization)
        material_name='placements';material_id=placement['id']
        request=lambda:client.post('/api/v1/internship-logs/mentor-assignments',headers=host['headers'],json={
            'placement_id':placement['id'],'organization_id':organization,'mentor_id':mentor['user_id']})
    before=admission_snapshot()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            material=table(material_name)
            holder.execute(select(material).where(material.c.id==material_id).with_for_update())
            pid=holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(request);wait_for_blocker(pid)
            revoked=client.delete('/api/v1/me/sessions/'+host['session_id'],headers=host['headers'])
            assert revoked.status_code==200,revoked.text
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert admission_snapshot()==before
