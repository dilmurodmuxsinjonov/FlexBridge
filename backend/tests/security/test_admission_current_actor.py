"""Current actor survives no completed logout while waiting for admission material."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,text,or_
from app.db.storage import get_engine,table,transaction
from test_internship_admission import accepted_offer,post
from test_org_authority_transactions import wait_for_blocker
from test_admission_lifecycle import terms_request


def admission_snapshot():
    with transaction() as conn:
        result={}
        for name in ('placements','placement_terms','placement_decisions','mentor_assignments','placement_intakes',
                     'mentor_assignment_proofs','placement_consents','placement_admission_events','plan_tasks','workplace_log_reviews'):
            t=table(name)
            result[name]=[dict(row) for row in conn.execute(select(t).order_by(*t.primary_key.columns)).mappings()]
        audit=table('audit_events')
        result['audit']=[dict(row) for row in conn.execute(select(audit).where(or_(audit.c.action.like('MENTOR_%'),
            audit.c.action.like('PLACEMENT_%'),audit.c.action=='WORKPLACE_LOG_REVIEWED')).order_by(audit.c.id)).mappings()]
        return result


@pytest.mark.parametrize('kind',['create','nominate','candidate_accept','mentor_accept','activate','plan','publish','revoke','review'])
def test_completed_logout_after_real_business_wait_denies_admission_write(client,identities,organization,kind):
    candidate,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    who=host
    if kind=='create':
        material_name='offers';material_id=body['offer_id']
        request=lambda:client.post('/api/v1/placements',json=body,headers=host['headers'])
    else:
        placement=post(client,'/api/v1/placements',host,body,201)
        mentor=identities('MENTOR',organization)
        material_name='placements';material_id=placement['id']
        base='/api/v1/placements/'+placement['id'];terms=terms_request(placement)
        if kind=='nominate':
            request=lambda:client.post('/api/v1/internship-logs/mentor-assignments',headers=host['headers'],json={
                'placement_id':placement['id'],'organization_id':organization,'mentor_id':mentor['user_id']})
        elif kind=='candidate_accept':
            who=candidate
            request=lambda:client.post(base+'/accept',headers=who['headers'],json=terms)
        elif kind=='plan':request=lambda:client.get(base+'/plan',headers=who['headers'])
        elif kind=='publish':
            payload={**terms,'title':'Actual plan','objectives':'Learn and demonstrate the implementation.',
                'daily_limit_minutes':360,'weekly_limit_minutes':1800,'required_minutes':360,
                'tasks':[{'code':'TASK','title':'Implementation','expected_result':'Working implementation','required':True}]}
            request=lambda:client.put(base+'/plan',headers=who['headers'],json=payload)
        else:
            assignment=post(client,base+'/mentor-assignments',host,{'mentor_id':mentor['user_id']},201)
            if kind=='mentor_accept':
                who=mentor
                request=lambda:client.post(base+'/assignments/'+assignment['id']+'/accept',headers=who['headers'],json=terms)
            elif kind=='revoke':
                request=lambda:client.post(base+'/mentor-assignments/'+assignment['id']+'/revoke',headers=who['headers'],json=terms)
            else:
                post(client,base+'/accept',candidate,terms_request(placement),200)
                post(client,base+'/assignments/'+assignment['id']+'/accept',mentor,terms_request(placement),200)
                request=lambda:client.post(base+'/host-decisions',headers=who['headers'],json={**terms,'action':'ACTIVATE'})
                if kind=='review':
                    post(client,base+'/host-decisions',host,{**terms_request(placement),'action':'ACTIVATE'},200)
                    draft=client.put(base+'/logs/'+placement['start_date'],headers=candidate['headers'],json={
                        'day_type':'WORKED','summary_text':'Actual work','total_minutes':60})
                    assert draft.status_code==200,draft.text
                    log=draft.json();post(client,'/api/v1/logs/'+log['id']+'/submit',candidate,{},200)
                    who=mentor
                    request=lambda:client.post('/api/v1/internship-logs/daily-logs/'+log['id']+'/workplace-reviews',headers=who['headers'],json={
                        'placement_id':placement['id'],'mentor_assignment_id':assignment['id'],'decision':'APPROVED','comment':'Actual mentor review.'})
    before=admission_snapshot()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_engine().begin() as holder:
            material=table(material_name)
            holder.execute(select(material).where(material.c.id==material_id).with_for_update())
            pid=holder.execute(text('SELECT pg_backend_pid()')).scalar_one()
            pending=pool.submit(request);wait_for_blocker(pid)
            revoked=client.delete('/api/v1/me/sessions/'+who['session_id'],headers=who['headers'])
            assert revoked.status_code==200,revoked.text
        response=pending.result(timeout=30)
    assert response.status_code in (401,403),response.text
    assert admission_snapshot()==before
