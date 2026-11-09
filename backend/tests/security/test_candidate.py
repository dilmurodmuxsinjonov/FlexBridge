"""Candidate isolation and real PostgreSQL matching regressions."""
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import event, select
import pytest

from app.db.storage import get_engine, table, transaction, now
from app.services.availability import availability_service
from app.services.opportunities import opportunity_service
from app.services.schedule import local_today
from app.services.placements import insert_row
from app.api.dependencies import ActorContext


def candidate_actor(user):
    return ActorContext(user['user_id'],user['session_id'],())


def published_fixture(owner, organization, *, stipend=False, weekday=None,
                      start_minute=540, end_minute=600, **revision_changes):
    revision = opportunity_service.create_opportunity_revision(
        organization_id=organization, title='Candidate matching test',
        opportunity_kind='GENERAL_INTERNSHIP' if stipend else 'PART_TIME_JOB',
        contract_type='INTERNSHIP_AGREEMENT' if stipend else 'LABOR_PART_TIME',
        compensation_type='STIPEND' if stipend else 'HOURLY',
        stipend_amount=500000 if stipend else None, hourly_pay=None if stipend else 20000,
        actor_user_id=owner['user_id'])
    opportunity_service.add_opportunity_shift(revision_id=revision['id'], group_code='A',
        weekday=weekday or local_today().isoweekday(), start_minute=start_minute, end_minute=end_minute,
        actor_user_id=owner['user_id'])
    with transaction() as conn:
        if revision_changes:
            conn.execute(table('opportunity_revisions').update().where(
                table('opportunity_revisions').c.id == revision['id']).values(**revision_changes))
        conn.execute(table('opportunities').update().where(
            table('opportunities').c.id == revision['opportunity_id']).values(status='PUBLISHED'))
    return revision


@pytest.mark.parametrize('start_offset,end_offset,available', [(-14,-1,False),(1,14,False),(0,0,True),(-14,0,True)])
def test_availability_validity_boundaries(identities,start_offset,end_offset,available):
    candidate=identities();today=local_today()
    rule=availability_service.add_availability_rule(actor=candidate_actor(candidate),candidate_id=candidate['candidate_id'],
        weekday=today.isoweekday(),start_minute=540,end_minute=600)
    with transaction() as conn:
        conn.execute(table('availability_rules').update().where(table('availability_rules').c.id==rule['id'])
            .values(valid_from=today+timedelta(days=start_offset),valid_to=today+timedelta(days=end_offset)))
    assert availability_service.is_candidate_available_for_shift(candidate_id=candidate['candidate_id'],
        weekday=today.isoweekday(),start_minute=540,end_minute=600,check_date=today.isoformat()) is available


def test_stipend_feed_and_scoped_batch_queries(identities,organization):
    owner=identities('OWNER',organization);candidate=identities();other=identities()
    availability_service.add_availability_rule(actor=candidate_actor(candidate),candidate_id=candidate['candidate_id'],
        weekday=local_today().isoweekday(),start_minute=510,end_minute=630)
    availability_service.add_availability_rule(actor=candidate_actor(other),candidate_id=other['candidate_id'],
        weekday=local_today().isoweekday(),start_minute=0,end_minute=1440)
    for _ in range(3): published_fixture(owner,organization,stipend=True)
    statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany):statements.append((statement,parameters))
    event.listen(get_engine(),'before_cursor_execute',capture)
    try:
        feed=opportunity_service.match_candidate_feed_api_003(candidate_id=candidate['candidate_id'])
    finally:event.remove(get_engine(),'before_cursor_execute',capture)
    assert len(feed)==3 and all(item['compensation_type']=='STIPEND' for item in feed)
    selects=[(q,p) for q,p in statements if q.lstrip().upper().startswith('SELECT')]
    assert len(selects)<=4
    assert all('WHERE' in q.upper() for q,p in selects)
    availability_queries=[(q,p) for q,p in selects if 'flexbridge.availability_' in q]
    assert len(availability_queries)==2
    assert all(candidate['candidate_id'] in p.values() and other['candidate_id'] not in p.values()
               for q,p in availability_queries)


def put_rules(client, user, rules):
    return client.put('/api/v1/me/availability', headers=user['headers'], json={'rules': rules})


def weekly(weekday=None, start=510, end=630, **extra):
    return {'weekday': weekday or local_today().isoweekday(), 'start_minute': start, 'end_minute': end, **extra}


def preview(client, user, revision, **extra):
    return client.post('/api/v1/matching/preview', headers=user['headers'], json={
        'candidate_id': user['candidate_id'], 'opportunity_id': revision['opportunity_id'], **extra})


def test_profile_self_service_and_private_response(client,identities):
    user,other=identities(),identities()
    response=client.patch('/api/v1/me/candidate',headers=user['headers'],json={
        'headline':'Python developer','region':'Tashkent','bio':'Part time work','experience_months':12})
    assert response.status_code==200,response.text
    assert response.json()['user_id']==user['user_id'] and response.json()['visibility']=='PRIVATE'
    assert response.headers['cache-control']=='no-store'
    assert client.get('/api/v1/me/candidate',headers=other['headers']).json()['headline']!='Python developer'
    assert client.get('/api/v1/me/candidate').status_code==401
    assert client.patch('/api/v1/me/candidate',headers=user['headers'],json={'bio':None}).json()['bio'] is None


@pytest.mark.parametrize('payload',[
    {'user_id':str(uuid4())},{'verification_case_id':str(uuid4())},{'student_verified':True},
    {'visibility':'PUBLIC'},{'experience_months':-1},{'headline':None},{'headline':'  '}])
def test_profile_rejects_authority_and_invalid_fields(client,identities,payload):
    assert client.patch('/api/v1/me/candidate',headers=identities()['headers'],json=payload).status_code==422


def skill_fixture(active=True):
    with transaction() as conn:
        return insert_row(conn,'skills',code='PYTHON-'+str(uuid4()),name_uz='Python',name_ru='Питон',aliases=[],active=active)


def test_skills_are_self_declared_until_independently_verified(client,identities):
    user,reviewer=identities(),identities();skill=skill_fixture()
    body={'skills':[{'skill_id':skill['id'],'level':'INTERMEDIATE'}]}
    response=client.patch('/api/v1/me/candidate/skills',headers=user['headers'],json=body)
    assert response.status_code==200,response.text
    assert response.json()['skills'][0]['verified'] is False
    with transaction() as conn:
        case=insert_row(conn,'verification_cases',requester_id=user['user_id'],candidate_id=user['candidate_id'],
            kind='CANDIDATE_SKILL',status='PENDING',current_revision=1,due_at=now()+timedelta(days=1),
            assigned_reviewer_id=reviewer['user_id'])
        conn.execute(table('candidate_skills').update().where(table('candidate_skills').c.candidate_id==user['candidate_id']).values(verification_case_id=case['id']))
    assert not client.get('/api/v1/me/candidate',headers=user['headers']).json()['skills'][0]['verified']
    with transaction() as conn:
        conn.execute(table('verification_cases').update().where(table('verification_cases').c.id==case['id']).values(status='APPROVED'))
    assert client.get('/api/v1/me/candidate',headers=user['headers']).json()['skills'][0]['verified']
    # A no-op edit preserves the reviewed assertion; changing the assertion clears it.
    assert client.patch('/api/v1/me/candidate/skills',headers=user['headers'],json=body).json()['skills'][0]['verified']
    body['skills'][0]['level']='ADVANCED'
    assert not client.patch('/api/v1/me/candidate/skills',headers=user['headers'],json=body).json()['skills'][0]['verified']
    assert client.get('/api/v1/me/candidate',headers=reviewer['headers']).json()['skills']==[]
    assert client.patch('/api/v1/me/candidate/skills',headers=user['headers'],json={'remove_skill_ids':[skill['id']]}).json()['skills']==[]


def test_skill_input_validation_and_catalog(client,identities):
    user=identities();active=skill_fixture();inactive=skill_fixture(False)
    result=client.get('/api/v1/skills?q=Python',headers=user['headers'])
    assert result.status_code==200 and [s['id'] for s in result.json()['items']]==[active['id']]
    for skill_id in (inactive['id'],str(uuid4())):
        assert client.patch('/api/v1/me/candidate/skills',headers=user['headers'],json={
            'skills':[{'skill_id':skill_id,'level':'BASIC'}]}).status_code==422
    body={'skills':[{'skill_id':active['id'],'level':'BASIC','verified':True}]}
    assert client.patch('/api/v1/me/candidate/skills',headers=user['headers'],json=body).status_code==422
    body={'skills':[{'skill_id':active['id'],'level':'BASIC'}]*2}
    assert client.patch('/api/v1/me/candidate/skills',headers=user['headers'],json=body).status_code==422


def cv_fixture(user, status='CLEAN', deleted=False):
    from app.db.storage import now
    version=str(uuid4());etag='"'+uuid4().hex+'"'
    with transaction() as conn:
        return insert_row(conn,'files',owner_user_id=user['user_id'],filename='cv.pdf',mime_type='application/pdf',
            storage_key=('quarantine/' if status=='SCANNING' else 'private/test/')+str(uuid4()),byte_size=100,sha256='a'*64,scan_status=status,
            retention_class='VERIFICATION_EVIDENCE',deleted_at=now() if deleted else None,
            object_version=version if status=='CLEAN' else (etag if status=='SCANNING' else None),
            storage_bucket='test-private-bucket' if status in ('CLEAN','SCANNING') else None,
            storage_version_id=version if status in ('CLEAN','SCANNING') else None,
            storage_etag=etag if status in ('CLEAN','SCANNING') else None,
            scanned_at=now() if status=='CLEAN' else None)


@pytest.mark.parametrize('status',['PENDING_SCAN','SCANNING','QUARANTINED'])
def test_cv_requires_clean_owned_file(client,identities,status):
    user=identities();file=cv_fixture(user,status)
    response=client.post('/api/v1/me/candidate/cv',headers=user['headers'],json={'file_id':file['id']})
    assert response.status_code==409,response.text
    assert client.get('/api/v1/me/candidate',headers=user['headers']).json()['cv_file_id'] is None


def test_cv_link_unlink_and_foreign_deleted_files(client,identities):
    user,other=identities(),identities();file=cv_fixture(user)
    assert client.post('/api/v1/me/candidate/cv',headers=other['headers'],json={'file_id':file['id']}).status_code==403
    assert client.post('/api/v1/me/candidate/cv',headers=user['headers'],json={'file_id':file['id']}).status_code==200
    own=client.get('/api/v1/me/candidate',headers=user['headers'])
    assert own.json()['cv_file_id']==file['id'] and 'storage_key' not in own.text and 'signed_url' not in own.text
    assert client.get('/api/v1/me/candidate',headers=other['headers']).json()['cv_file_id'] is None
    deleted=cv_fixture(user,deleted=True)
    assert client.post('/api/v1/me/candidate/cv',headers=user['headers'],json={'file_id':deleted['id']}).status_code==409
    with transaction() as conn:
        conn.execute(table('files').update().where(table('files').c.id==file['id']).values(mime_type='application/zip'))
    assert client.post('/api/v1/me/candidate/cv',headers=user['headers'],json={'file_id':file['id']}).status_code==409
    assert client.post('/api/v1/me/candidate/cv',headers=user['headers'],json={'file_id':None}).json()['cv_file_id'] is None


def test_weekly_union_replacement_and_scope(client,identities):
    user,other=identities(),identities()
    response=put_rules(client,user,[weekly(start=540,end=660),weekly(start=600,end=720),weekly(start=720,end=780)])
    assert response.status_code==200,response.text
    assert len(response.json()['rules'])==1
    assert response.json()['effective_days'][0]['intervals']==[{'start_minute':540,'end_minute':780}]
    assert client.get('/api/v1/me/availability',headers=other['headers']).json()['rules']==[]
    assert put_rules(client,user,[]).json()['rules']==[]


def test_weekly_replacement_rolls_back_on_period_overlap(client,identities):
    user=identities();today=local_today()
    assert put_rules(client,user,[weekly(start=100,end=200)]).status_code==200
    response=put_rules(client,user,[weekly(valid_from=today.isoformat()),
        weekly(valid_from=(today+timedelta(days=1)).isoformat())])
    assert response.status_code==409,response.text
    persisted=client.get('/api/v1/me/availability',headers=user['headers']).json()['rules']
    assert len(persisted)==1 and persisted[0]['start_minute']==100


def test_exceptions_union_subtraction_and_atomic_range(client,identities):
    user=identities();today=local_today()
    assert put_rules(client,user,[weekly(start=540,end=720)]).status_code==200
    def replace(exceptions):
        return client.put('/api/v1/me/availability/exceptions',headers=user['headers'],json={
            'from_date':today.isoformat(),'to_date':today.isoformat(),'exceptions':exceptions})
    exception={'local_date':today.isoformat(),'kind':'UNAVAILABLE','start_minute':600,'end_minute':660}
    response=replace([exception])
    assert response.status_code==200,response.text
    assert response.json()['effective_days'][0]['intervals']==[
        {'start_minute':540,'end_minute':600},{'start_minute':660,'end_minute':720}]
    assert replace([exception,{**exception,'kind':'AVAILABLE'}]).status_code==409
    assert len(client.get('/api/v1/me/availability',headers=user['headers']).json()['exceptions'])==1
    assert replace([{**exception,'kind':'AVAILABLE','start_minute':720,'end_minute':780}]).status_code==200
    assert client.get('/api/v1/me/availability',headers=user['headers']).json()['effective_days'][0]['intervals']==[
        {'start_minute':540,'end_minute':780}]


@pytest.mark.parametrize('rule',[weekly(start=600,end=600),weekly(timezone='Europe/London'),weekly(weekday=8),
    weekly(valid_from='2026-11-10',valid_to='2026-11-09')])
def test_schedule_validation(client,identities,rule):
    assert put_rules(client,identities(),[rule]).status_code==422


def test_preview_28_day_exception_and_ownership(client,identities,organization):
    owner=identities('OWNER',organization);user,other=identities(),identities();revision=published_fixture(owner,organization)
    assert preview(client,user,revision).json()['result']=='UNKNOWN'
    assert put_rules(client,user,[weekly()]).status_code==200
    result=preview(client,user,revision)
    assert result.status_code==200,result.text
    assert result.json()['result']=='MATCH' and result.json()['checked_occurrences']==4
    assert result.json()['commute_buffer_minutes']==30 and result.headers['cache-control']=='no-store'
    target=local_today()+timedelta(days=7)
    response=client.put('/api/v1/me/availability/exceptions',headers=user['headers'],json={
        'from_date':target.isoformat(),'to_date':target.isoformat(),'exceptions':[
            {'local_date':target.isoformat(),'kind':'UNAVAILABLE','start_minute':550,'end_minute':560}]})
    assert response.status_code==200,response.text
    assert preview(client,user,revision).json()['result']=='CONFLICT'
    assert preview(client,user,revision,candidate_id=other['candidate_id']).status_code==403
    assert preview(client,user,revision,check_date='invalid').status_code==422


def test_remote_has_no_travel_buffer(client,identities,organization):
    owner=identities('OWNER',organization);user=identities()
    remote=published_fixture(owner,organization,work_mode='REMOTE')
    onsite=published_fixture(owner,organization)
    put_rules(client,user,[weekly(start=540,end=600)])
    assert preview(client,user,remote).json()['result']=='MATCH'
    assert preview(client,user,remote).json()['commute_buffer_minutes']==0
    assert preview(client,user,onsite).json()['result']=='CONFLICT'
    assert preview(client,user,onsite,commute_buffer_minutes=0).json()['result']=='MATCH'


def test_sunday_midnight_buffer_uses_saturday_availability(client,identities,organization):
    owner=identities('OWNER',organization);user=identities()
    revision=published_fixture(owner,organization,weekday=7,start_minute=0,end_minute=60)
    sunday=local_today()+timedelta(days=(7-local_today().isoweekday())%7)
    put_rules(client,user,[weekly(weekday=7,start=0,end=90)])
    assert preview(client,user,revision,check_date=sunday.isoformat()).json()['result']=='CONFLICT'
    put_rules(client,user,[weekly(weekday=7,start=0,end=90),weekly(weekday=6,start=1410,end=1440,
        valid_from=(local_today()-timedelta(days=7)).isoformat())])
    assert preview(client,user,revision,check_date=sunday.isoformat()).json()['result']=='MATCH'


def test_no_real_occurrences_never_matches(client,identities,organization):
    owner=identities('OWNER',organization);user=identities();tomorrow=local_today()+timedelta(days=1)
    revision=published_fixture(owner,organization,start_date=tomorrow,end_date=tomorrow)
    put_rules(client,user,[weekly()])
    result=preview(client,user,revision)
    assert result.status_code==200,result.text
    assert result.json()['result']=='UNKNOWN' and result.json()['reason_codes']==['NO_REQUIRED_OCCURRENCES']


def test_matching_pages_advance_even_when_no_matches(identities,organization):
    owner=identities('OWNER',organization);user=identities()
    for _ in range(3):published_fixture(owner,organization)
    cursor=None;seen=[]
    for _ in range(3):
        page=opportunity_service.match_feed_page(candidate_id=user['candidate_id'],limit=1,after_id=cursor)
        assert page['items']==[] and len(page['evaluations'])==1
        seen.append(page['evaluations'][0]['opportunity_id']);cursor=page['next_cursor']
    assert cursor is None and len(set(seen))==3


def test_generic_preview_preserves_result_and_window_metadata(client,identities,organization):
    owner=identities('OWNER',organization);user=identities()
    revision=published_fixture(owner,organization)
    request={'candidate_id':user['candidate_id']}
    response=client.post('/api/v1/matching/preview',headers=user['headers'],json=request)
    assert response.status_code==200,response.text
    assert response.json()['result']=='UNKNOWN' and response.json()['checked_from']==local_today().isoformat()
    put_rules(client,user,[weekly()])
    response=client.post('/api/v1/matching/preview',headers=user['headers'],json=request)
    assert response.json()['result']=='MATCH' and response.json()['items'][0]['revision_id']==revision['id']
    assert response.json()['algorithm_version']=='1.4.1-can' and response.json()['availability_revision']


def test_repeatable_matching_snapshot_during_schedule_edit(client,identities):
    from concurrent.futures import ThreadPoolExecutor
    from app.db.storage import read_snapshot
    from app.services.schedule import load_snapshot
    from app.services.availability import availability_service
    user=identities();today=local_today()
    put_rules(client,user,[weekly(start=540,end=600)])
    with read_snapshot():
        before=load_snapshot(user['candidate_id'],today,today+timedelta(days=1))
        with ThreadPoolExecutor(max_workers=1) as pool:
            rules=[{'weekday':today.isoweekday(),'start_minute':700,'end_minute':800,
                'valid_from':today,'valid_to':None,'timezone':'Asia/Tashkent'}]
            pool.submit(availability_service.replace_rules,candidate_actor(user),rules).result(timeout=10)
        during=load_snapshot(user['candidate_id'],today,today+timedelta(days=1))
        assert before.revision==during.revision
        assert during.covers(today,540,600)
    after=load_snapshot(user['candidate_id'],today,today+timedelta(days=1))
    assert not after.covers(today,540,600) and after.covers(today,700,800)


def test_concurrent_weekly_replacements_are_whole_schedules(client,identities):
    from concurrent.futures import ThreadPoolExecutor
    user=identities()
    variants=[[weekly(start=100,end=200),weekly(start=300,end=400)],
              [weekly(start=500,end=600),weekly(start=700,end=800)]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(put_rules,client,user,rules) for rules in variants]
        for future in futures:
            response=future.result(timeout=10)
            assert response.status_code==200,response.text
    rows=client.get('/api/v1/me/availability',headers=user['headers']).json()['rules']
    actual=sorted((r['start_minute'],r['end_minute']) for r in rows)
    assert actual in [[(100,200),(300,400)],[(500,600),(700,800)]]


def test_exception_replacement_does_not_delete_outside_window(client,identities):
    user=identities();today=local_today();tomorrow=today+timedelta(days=1)
    availability_service.add_availability_exception(actor=candidate_actor(user),candidate_id=user['candidate_id'],exception_date=tomorrow.isoformat(),
        start_minute=600,end_minute=660)
    response=client.put('/api/v1/me/availability/exceptions',headers=user['headers'],json={
        'from_date':today.isoformat(),'to_date':today.isoformat(),'exceptions':[]})
    assert response.status_code==200,response.text
    rows=client.get('/api/v1/me/availability',headers=user['headers']).json()['exceptions']
    assert len(rows)==1 and rows[0]['local_date']==tomorrow.isoformat()
    assert client.put('/api/v1/me/availability/exceptions',headers=user['headers'],json={
        'from_date':today.isoformat(),'to_date':today.isoformat(),'exceptions':[
            {'local_date':tomorrow.isoformat(),'kind':'AVAILABLE','start_minute':0,'end_minute':60}]}).status_code==422


def test_preview_hides_drafts_and_rejects_impossible_dates(client,identities,organization):
    owner=identities('OWNER',organization);user=identities()
    revision=published_fixture(owner,organization)
    assert preview(client,user,revision,check_date='9999-12-31').status_code==422
    assert client.get('/api/v1/me/availability?from_date=9999-12-31',headers=user['headers']).status_code==422
    with transaction() as conn:
        conn.execute(table('opportunities').update().where(table('opportunities').c.id==revision['opportunity_id']).values(status='DRAFT'))
    assert preview(client,user,revision).status_code==404


@pytest.mark.parametrize('method,path,body',[
    ('GET','/api/v1/me/candidate',None),('PATCH','/api/v1/me/candidate',{}),
    ('PATCH','/api/v1/me/candidate/skills',{}),('POST','/api/v1/me/candidate/cv',{'file_id':None}),
    ('GET','/api/v1/me/availability',None),('PUT','/api/v1/me/availability',{'rules':[]}),
    ('PUT','/api/v1/me/availability/exceptions',{}),('GET','/api/v1/skills',None)])
def test_candidate_routes_require_authentication(client,method,path,body):
    assert client.request(method,path,json=body).status_code==401
