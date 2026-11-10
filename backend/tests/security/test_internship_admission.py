"""Independent pinned-source HTTP observations; publication metadata is trusted setup."""
from sqlalchemy import select
from app.db.storage import table,transaction
from app.services.opportunities import opportunity_service
from uuid import uuid4


def post(client,path,who,body,status):
    response=client.post(path,json=body,headers=who['headers'])
    assert response.status_code==status,(path,response.status_code,response.json())
    return response.json()


def accepted_offer(client,identities,organization,kind):
    candidate=identities();host=identities('OWNER',organization)
    revision=opportunity_service.create_opportunity_revision(
        organization_id=organization,title='Controlled opportunity',opportunity_kind=kind,
        contract_type='LABOR_PART_TIME' if kind=='PART_TIME_JOB' else 'INTERNSHIP_AGREEMENT',
        compensation_type='HOURLY',hourly_pay=20000,actor_user_id=host['user_id'])
    with transaction() as conn:
        conn.execute(table('opportunities').update().where(table('opportunities').c.id==revision['opportunity_id']).values(status='PUBLISHED'))
    application=post(client,'/api/v1/applications',candidate,
        {'opportunity_id':revision['opportunity_id'],'candidate_id':candidate['candidate_id']},201)
    post(client,'/api/v1/applications/'+application['id']+'/attempts',candidate,{'opportunity_id':revision['opportunity_id']},201)
    offer=post(client,'/api/v1/offers',host,{'application_id':application['id'],
        'opportunity_id':revision['opportunity_id'],'candidate_id':candidate['candidate_id']},201)
    post(client,'/api/v1/offers/'+offer['id']+'/respond',candidate,{'decision':'ACCEPT'},200)
    body={'application_id':application['id'],'offer_id':offer['id'],'opportunity_id':revision['opportunity_id'],
          'candidate_id':candidate['candidate_id'],'organization_id':organization,'idempotency_key':str(uuid4())}
    return candidate,host,body


def test_actual_part_time_offer_cannot_create_an_internship_placement(client,identities,organization):
    _,host,body=accepted_offer(client,identities,organization,'PART_TIME_JOB')
    response=client.post('/api/v1/placements',json=body,headers=host['headers'])
    with transaction() as conn:
        created=[dict(row) for row in conn.execute(select(table('placements'))).mappings()]
    assert response.status_code==409 and not created,(response.status_code,response.json(),created)


def test_actual_internship_cannot_activate_without_personally_accepted_mentor(client,identities,organization):
    candidate,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    placement=post(client,'/api/v1/placements',host,body,201)
    terms={'terms_id':placement['current_terms_id'],'version':1,'idempotency_key':str(uuid4())}
    post(client,'/api/v1/placements/'+placement['id']+'/confirm-start',candidate,{'party':'CANDIDATE',**terms},200)
    response=client.post('/api/v1/placements/'+placement['id']+'/confirm-start',
        json={'party':'ORGANIZATION',**terms,'idempotency_key':str(uuid4())},headers=host['headers'])
    with transaction() as conn:
        saved=dict(conn.execute(select(table('placements')).where(table('placements').c.id==placement['id'])).mappings().one())
        mentors=conn.execute(select(table('mentor_assignments').c.id)).scalars().all()
    assert saved['status']!='ACTIVE',(response.status_code,response.json(),saved,mentors)


def test_actual_active_staff_without_mentor_role_cannot_be_nominated_as_mentor(client,identities,organization):
    _,host,body=accepted_offer(client,identities,organization,'INTERNSHIP')
    placement=post(client,'/api/v1/placements',host,body,201)
    hr=identities('HR',organization)
    response=client.post('/api/v1/internship-logs/mentor-assignments',headers=host['headers'],
        json={'placement_id':placement['id'],'organization_id':organization,'mentor_id':hr['user_id'],'idempotency_key':str(uuid4())})
    with transaction() as conn:
        rows=[dict(row) for row in conn.execute(select(table('mentor_assignments'))).mappings()]
    assert response.status_code==403 and not rows,(response.status_code,response.json(),rows)
