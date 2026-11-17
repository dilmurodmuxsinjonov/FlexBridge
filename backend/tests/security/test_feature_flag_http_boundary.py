"""Actual API121 authentication, strict intent, privacy and input boundaries."""
from uuid import uuid4

from sqlalchemy import select

from app.db.storage import table,transaction,now


PATH='/api/v1/operator/feature-flags/R1_PART_TIME_JOBS'
BODY={'enabled':True,'reason':'Approved R1 configuration after operator review.'}


def headers(user,**updates):
    return {**user['headers'],'Idempotency-Key':str(uuid4()),'If-Match':'"0"',**updates}


def assert_private(response):
    assert response.headers['cache-control']=='no-store'


def assert_no_flag_effect():
    with transaction() as conn:
        for name in ('feature_flags','feature_flag_origins','feature_flag_change_events'):
            assert conn.execute(select(table(name))).first() is None
        audits=table('audit_events')
        assert conn.execute(select(audits.c.id).where(audits.c.action=='FEATURE_FLAG_ADMINISTERED')).first() is None


def test_anonymous_and_forged_identity_headers_cannot_administer(client,identities):
    admin=identities('ADMIN')
    for supplied in ({},{'X-User-Id':admin['user_id'],'X-Role':'ADMIN','X-MFA':'true'},
                     {'Authorization':'Bearer forged-admin-access-token'}):
        response=client.patch(PATH,headers={**supplied,'Idempotency-Key':str(uuid4()),'If-Match':'"0"'},json=BODY)
        assert response.status_code==401,response.text
        assert_private(response)
    assert_no_flag_effect()


def test_authenticated_moderator_cannot_use_admin_endpoint(client,identities):
    moderator=identities('MODERATOR')
    response=client.patch(PATH,headers=headers(moderator),json=BODY)
    assert response.status_code==403,response.text
    assert_private(response);assert_no_flag_effect()


def test_intent_headers_are_required_and_versions_cannot_be_ambiguous(client,identities):
    admin=identities('ADMIN')
    cases=[({'If-Match':'"0"'},'IDEMPOTENCY_KEY_REQUIRED'),
           ({'Idempotency-Key':str(uuid4())},'IF_MATCH_REQUIRED'),
           ({'Idempotency-Key':'short','If-Match':'"0"'},'INVALID_IDEMPOTENCY_KEY')]
    for version in ('0','*','W/"0"','"0", "1"','"-1"','"2147483648"'):
        cases.append(({'Idempotency-Key':str(uuid4()),'If-Match':version},'INVALID_IF_MATCH'))
    for supplied,code in cases:
        response=client.patch(PATH,headers={**admin['headers'],**supplied},json=BODY)
        assert response.status_code==400,response.text
        assert response.json()['detail']['code']==code
        assert_private(response)
    assert_no_flag_effect()


def test_client_cannot_coerce_boolean_or_add_schema_and_scope(client,identities):
    admin=identities('ADMIN')
    bodies=[{**BODY,'enabled':value} for value in ('true',1,None)]
    bodies += [{**BODY,'rule_schema':{'scope':'GLOBAL'}},
               {**BODY,'organization_id':str(uuid4())},{**BODY,'reason':' '*15}]
    for body in bodies:
        response=client.patch(PATH,headers=headers(admin),json=body)
        assert response.status_code==422,response.text
        assert_private(response)
    too_large=client.patch(PATH,headers={**headers(admin),'Content-Type':'application/json'},
        content='{"reason":"'+'x'*131073+'"}')
    assert too_large.status_code==413
    assert_private(too_large);assert_no_flag_effect()


def test_http_replay_requires_current_admin_grant_and_adds_no_effect(client,identities):
    admin=identities('ADMIN');intent=headers(admin)
    first=client.patch(PATH,headers=intent,json=BODY)
    assert first.status_code==200,first.text
    assert_private(first)
    assert client.patch(PATH,headers=intent,json=BODY).json()==first.json()
    with transaction() as conn:
        grants=table('platform_role_grants')
        conn.execute(grants.update().where(grants.c.user_id==admin['user_id']).values(revoked_at=now(),updated_at=now()))
    denied=client.patch(PATH,headers=intent,json=BODY)
    assert denied.status_code==403,denied.text
    assert_private(denied)
    with transaction() as conn:
        assert len(conn.execute(select(table('feature_flag_change_events'))).all())==1
        audits=table('audit_events')
        assert len(conn.execute(select(audits.c.id).where(audits.c.action=='FEATURE_FLAG_ADMINISTERED')).all())==1
