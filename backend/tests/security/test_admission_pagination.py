"""More than100 owned resources, stable cursor pages and foreign-anchor denial."""
from uuid import uuid4
from sqlalchemy import select

from app.db.storage import table,transaction,now
from app.services.placements import get_row,insert_row
from test_internship_admission import accepted_offer,post
from test_mentor_notices import inbox


def next_offer_seed(original):
    """Bulk prerequisites only: publication/application/accepted-offer metadata is trusted.

    Each placement intake and nomination below still uses the actual HTTP actor.
    This fixture does not certify the upstream offer/publication workflow.
    """
    def clone(conn,name,source_id,**changes):
        data=get_row(conn,name,source_id)
        for key in ('id','created_at','updated_at'):data.pop(key)
        return insert_row(conn,name,**{**data,**changes})
    with transaction() as conn:
        old=get_row(conn,'offers',original['offer_id'])
        opp=clone(conn,'opportunities',original['opportunity_id'],current_revision_id=None)
        revision=clone(conn,'opportunity_revisions',old['revision_id'],opportunity_id=opp['id'])
        conn.execute(table('opportunities').update().where(table('opportunities').c.id==opp['id']).values(current_revision_id=revision['id']))
        app=clone(conn,'applications',original['application_id'],opportunity_id=opp['id'])
        attempt=clone(conn,'application_attempts',old['attempt_id'],application_id=app['id'],opportunity_id=opp['id'],
                      revision_id=revision['id'],idempotency_key=str(uuid4()))
        offer=clone(conn,'offers',old['id'],application_id=app['id'],attempt_id=attempt['id'],revision_id=revision['id'],
                    terms_snapshot={'opportunity_id':opp['id']},idempotency_key=str(uuid4()))
    return {**original,'application_id':app['id'],'offer_id':offer['id'],'opportunity_id':opp['id'],'idempotency_key':str(uuid4())}


def collect(client,url,user,limit=40):
    result=[];after=None
    for _ in range(10):
        response=client.get(url,headers=user['headers'],params={'limit':limit,**({'after':after} if after else {})})
        assert response.status_code==200 and response.headers['cache-control']=='no-store',response.text
        page=response.json();result.extend(row['id'] for row in page['items'])
        after=page['next_after']
        if after is None:return result
    raise AssertionError('Pagination did not terminate')


def test_all_owned_placement_lists_exceed_100_without_truncation_or_foreign_cursor(client,identities,organization):
    candidate,host,original=accepted_offer(client,identities,organization,'INTERNSHIP')
    mentor=identities('MENTOR',organization);placements=set();assignments=set()
    for index in range(105):
        body=original if index==0 else next_offer_seed(original)
        placement=post(client,'/api/v1/placements',host,body,201)
        assignment=post(client,'/api/v1/placements/'+placement['id']+'/mentor-assignments',host,
                        {'mentor_id':mentor['user_id'],'idempotency_key':str(uuid4())},201)
        placements.add(placement['id']);assignments.add(assignment['id'])
    queries=[('/api/v1/me/placements',candidate,placements),
             ('/api/v1/organizations/'+organization+'/placements',host,placements),
             ('/api/v1/me/mentor-assignments',mentor,assignments)]
    for url,user,expected in queries:
        actual=collect(client,url,user)
        assert len(actual)==len(set(actual))==105 and set(actual)==expected
        for invalid in (0,101):
            assert client.get(url,headers=user['headers'],params={'limit':invalid}).status_code==422
    outsider=identities();other_mentor=identities('MENTOR',organization)
    assert client.get('/api/v1/me/placements',headers=outsider['headers'],params={'after':next(iter(placements))}).status_code==404
    assert client.get('/api/v1/me/mentor-assignments',headers=other_mentor['headers'],params={'after':next(iter(assignments))}).status_code==404
    assert client.get('/api/v1/organizations/'+organization+'/placements',headers=outsider['headers'],params={'after':next(iter(placements))}).status_code==403


def test_notification_tied_timestamps_page_over_100_and_read_cursor_stays_usable(client,identities):
    owner=identities();outsider=identities();stamp=now();ids=set()
    # Trusted historical metadata for paging; real notice delivery is tested separately.
    with transaction() as conn:
        for _ in range(105):
            event=insert_row(conn,'outbox_events',event_type='HISTORICAL_LOCAL',schema_version=1,aggregate_key='history',payload={},
                dedupe_key=str(uuid4()),available_at=stamp,processed_at=stamp,attempts=1)
            n=insert_row(conn,'notifications',user_id=owner['user_id'],event_id=event['id'],template_code='HISTORICAL_LOCAL',created_at=stamp)
            ids.add(n['id'])
    actual=collect(client,'/api/v1/me/notifications',owner)
    assert len(actual)==len(set(actual))==105 and set(actual)==ids
    first=inbox(client,owner,limit=1)['items'][0]
    post(client,'/api/v1/me/notifications/'+first['id']+'/read',owner,{},200)
    remaining=inbox(client,owner,limit=100,after=first['id'])
    assert len(remaining['items'])==100 and remaining['next_after'] is not None
    assert client.get('/api/v1/me/notifications',headers=outsider['headers'],params={'after':first['id']}).status_code==404
