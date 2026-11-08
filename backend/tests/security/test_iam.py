"""IAM flows use real PostgreSQL; only delivery transport is replaced at its boundary."""
import io
import json
import secrets
import hashlib
import struct
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID,uuid4
import cbor2
import pytest
from sqlalchemy import select,func
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers import bytes_to_base64url as b64
from app.db.storage import table,transaction,now,auth_continuations,auth_rate_limits
from app.services.identity import identity_service
from app.services.auth import auth_service,AuthError,generate_totp_code
from app.core.iam_security import decrypt,digest,rate_limit

PASSWORD='correct-passphrase-2026'
PHONE='+998901234567'

@pytest.fixture
def delivery(monkeypatch):
    from app.adapters import identity_delivery
    messages={}
    monkeypatch.setenv('AUTH_DELIVERY_URL','https://gateway.test.invalid')
    monkeypatch.setenv('AUTH_DELIVERY_TOKEN',secrets.token_urlsafe(32))
    def send(**kwargs):messages[kwargs['challenge_id']]=kwargs
    monkeypatch.setattr(identity_delivery,'send',send)
    return messages

def age_challenges():
    with transaction() as conn:
        conn.execute(table('auth_challenges').update().values(created_at=now()-timedelta(seconds=61)))

def request_code(client,delivery,purpose='REGISTER',destination=PHONE,channel='PHONE',headers=None):
    from app.workers.outbox import relay_pending_outbox_events
    response=client.post('/api/v1/auth/challenges',json={'purpose':purpose,'destination':destination,'channel':channel},headers=headers or {})
    assert response.status_code==202,response.text
    assert 'code' not in response.json() and 'user_id' not in response.json()
    cid=response.json()['challenge_id'];assert relay_pending_outbox_events()>=1
    return cid,delivery[cid]['code']

def proof(client,delivery,purpose='REGISTER',destination=PHONE,channel='PHONE',headers=None):
    cid,code=request_code(client,delivery,purpose,destination,channel,headers)
    response=client.post('/api/v1/auth/challenges/'+cid+'/consume',json={'purpose':purpose,'code':code})
    assert response.status_code==200,response.text
    return response.json()['verification_token']

def signup(client,delivery,destination=PHONE,channel='PHONE',name='Sardor',password=PASSWORD):
    token=proof(client,delivery,destination=destination,channel=channel)
    response=client.post('/api/v1/auth/register',json={'display_name':name,'password':password,'adult_confirmed':True,
        'verification_token':token,'terms_version':'test-terms-v1','privacy_version':'test-privacy-v1'})
    assert response.status_code==201,response.text
    return response.json()

def login(client,uid,password=PASSWORD,code=None):
    response=client.post('/api/v1/auth/login',json={'user_id':uid,'password':password,**({'totp_code':code} if code else {})})
    assert response.status_code==200,response.text
    return {**response.json(),'headers':{'Authorization':'Bearer '+response.json()['access_token']}}

def bind_phone(client,delivery,user):
    token=proof(client,delivery,purpose='CONTACT',headers=user['headers'])
    response=client.post('/api/v1/me/contacts',headers=user['headers'],json={'verification_token':token,'current_password':PASSWORD,
        **({'totp_code':generate_totp_code(user['totp_secret'])} if user.get('totp_secret') else {})})
    assert response.status_code==201,response.text

def test_signup_requires_contact_and_policy_proof(client,delivery):
    body={'display_name':'Sardor','password':PASSWORD,'adult_confirmed':True}
    assert client.post('/api/v1/auth/register',json=body).status_code==422
    token=proof(client,delivery)
    assert client.post('/api/v1/auth/register',json={**body,'verification_token':token,'terms_version':'outdated','privacy_version':'test-privacy-v1'}).status_code==422
    response=client.post('/api/v1/auth/register',json={**body,'verification_token':token,'terms_version':'test-terms-v1','privacy_version':'test-privacy-v1'})
    assert response.status_code==201,response.text
    assert response.json()['roles']==['CANDIDATE']
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('consent_events'))).scalar_one()==2
    assert client.post('/api/v1/auth/register',json={**body,'verification_token':token,'terms_version':'test-terms-v1','privacy_version':'test-privacy-v1'}).status_code==401

def test_otp_wrong_attempts_persist_and_lock_after_five(client,delivery):
    cid,code=request_code(client,delivery)
    wrong='000000' if code!='000000' else '111111'
    for _ in range(5):assert client.post('/api/v1/auth/challenges/'+cid+'/consume',json={'purpose':'REGISTER','code':wrong}).status_code==401
    assert client.post('/api/v1/auth/challenges/'+cid+'/consume',json={'purpose':'REGISTER','code':code}).status_code==401
    with transaction() as conn:
        row=conn.execute(select(table('auth_challenges')).where(table('auth_challenges').c.id==cid)).mappings().one()
    assert row['attempts']==5 and row['consumed_at'] is None

def test_expired_and_wrong_purpose_otp_rejected(client,delivery):
    cid,code=request_code(client,delivery)
    assert client.post('/api/v1/auth/challenges/'+cid+'/consume',json={'purpose':'LOGIN','code':code}).status_code==401
    with transaction() as conn:conn.execute(table('auth_challenges').update().where(table('auth_challenges').c.id==cid).values(expires_at=now()-timedelta(seconds=1)))
    assert client.post('/api/v1/auth/challenges/'+cid+'/consume',json={'purpose':'REGISTER','code':code}).status_code==401

def test_parallel_code_consume_is_single_use(client,delivery):
    cid,code=request_code(client,delivery)
    def consume(_):
        try:identity_service.consume(challenge_id=cid,purpose='REGISTER',code=code,ip='parallel-test');return True
        except AuthError:return False
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(consume,range(4)))
    assert sum(results)==1
    with transaction() as conn:assert conn.execute(select(func.count()).select_from(auth_continuations)).scalar_one()==1

def test_resend_cooldown_supersedes_old_code(client,delivery):
    from app.workers.outbox import relay_pending_outbox_events
    cid,code=request_code(client,delivery)
    url='/api/v1/auth/challenges/'+cid+'/resend'
    assert client.post(url,json={'purpose':'REGISTER'}).status_code==429
    age_challenges()
    response=client.post(url,json={'purpose':'REGISTER'});assert response.status_code==202,response.text
    new_id=response.json()['challenge_id'];assert new_id!=cid;relay_pending_outbox_events()
    assert client.post('/api/v1/auth/challenges/'+cid+'/consume',json={'purpose':'REGISTER','code':code}).status_code==401
    assert client.post('/api/v1/auth/challenges/'+new_id+'/consume',json={'purpose':'REGISTER','code':delivery[new_id]['code']}).status_code==200

def test_destination_limit_shared_across_purposes_and_ips(client,delivery):
    for i in range(5):
        age_challenges()
        identity_service.issue_challenge(channel='PHONE',destination=PHONE,purpose='REGISTER',ip='different-ip-'+str(i))
    age_challenges()
    with pytest.raises(AuthError) as error:identity_service.issue_challenge(channel='PHONE',destination=PHONE,purpose='RECOVERY',ip='another-ip')
    assert error.value.status_code==429

def test_delivery_unavailable_does_not_claim_sent(client,monkeypatch):
    monkeypatch.delenv('AUTH_DELIVERY_URL',raising=False)
    response=client.post('/api/v1/auth/challenges',json={'channel':'PHONE','destination':PHONE,'purpose':'REGISTER'})
    assert response.status_code==503
    with transaction() as conn:assert conn.execute(select(func.count()).select_from(table('auth_challenges'))).scalar_one()==0

def test_delivery_failure_retries_and_secret_not_in_outbox(client,delivery,monkeypatch):
    from app.adapters import identity_delivery
    from app.workers.outbox import relay_pending_outbox_events
    response=client.post('/api/v1/auth/challenges',json={'channel':'PHONE','destination':PHONE,'purpose':'REGISTER'});cid=response.json()['challenge_id']
    with transaction() as conn:
        row=conn.execute(select(table('auth_challenges')).where(table('auth_challenges').c.id==cid)).mappings().one()
        event=conn.execute(select(table('outbox_events'))).mappings().one()
    code=decrypt(row['delivery_encrypted'])['code']
    assert PHONE not in row['destination_encrypted'] and code not in row['delivery_encrypted']
    assert event['payload']=={'challenge_id':cid}
    def fail(**kwargs):raise RuntimeError('Gateway unavailable')
    monkeypatch.setattr(identity_delivery,'send',fail)
    assert relay_pending_outbox_events()==0
    assert client.post('/api/v1/auth/challenges/'+cid+'/consume',json={'purpose':'REGISTER','code':code}).status_code==401
    with transaction() as conn:assert conn.execute(select(table('outbox_events').c.processed_at)).scalar_one() is None

@pytest.mark.parametrize('channel,destination',[('PHONE','12345'),('EMAIL','bad@example'),('EMAIL','evil\r\n@example.com'),('EMAIL','evil\0@example.com')])
def test_invalid_contact_rejected(client,delivery,channel,destination):
    assert client.post('/api/v1/auth/challenges',json={'channel':channel,'destination':destination,'purpose':'REGISTER'}).status_code==422

def test_email_signup_and_contact_password_login(client,delivery):
    user=signup(client,delivery,destination='Sardor@Example.COM',channel='EMAIL')
    response=client.post('/api/v1/auth/login',json={'channel':'EMAIL','destination':'sardor@example.com','password':PASSWORD})
    assert response.status_code==200,response.text
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+response.json()['access_token']}).json()['user_id']==user['id']

def test_recycled_phone_creates_clean_account_and_revokes_old_tokens(client,delivery):
    old=signup(client,delivery,name='Old owner');old_session=login(client,old['id'])
    with transaction() as conn:
        conn.execute(table('candidate_profiles').update().where(table('candidate_profiles').c.user_id==old['id']).values(headline='Private old profile'))
    age_challenges()
    new=signup(client,delivery,name='Sardor',password='new-owner-passphrase-2026')
    assert new['id']!=old['id'] and new['roles']==['CANDIDATE']
    assert client.get('/api/v1/auth/me',headers=old_session['headers']).status_code==401
    response=client.post('/api/v1/auth/login',json={'channel':'PHONE','destination':PHONE,'password':'new-owner-passphrase-2026'})
    assert response.status_code==200,response.text
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+response.json()['access_token']}).json()['user_id']==new['id']
    assert client.post('/api/v1/auth/login',json={'user_id':old['id'],'password':'new-owner-passphrase-2026'}).status_code==401
    with transaction() as conn:
        assert conn.execute(select(table('candidate_profiles').c.headline).where(table('candidate_profiles').c.user_id==old['id'])).scalar_one()=='Private old profile'
        assert conn.execute(select(table('user_contacts').c.user_id).where(table('user_contacts').c.normalized_value==PHONE)).scalar_one()==new['id']

def test_phone_otp_alone_never_logs_into_existing_account(client,delivery):
    user=signup(client,delivery);token=proof(client,delivery,purpose='LOGIN')
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+token}).status_code==401
    assert client.post('/api/v1/auth/login',json={'verification_token':token}).status_code==422
    assert client.post('/api/v1/auth/login',json={'verification_token':token,'password':'wrong-password-1234'}).status_code==401
    response=client.post('/api/v1/auth/login',json={'verification_token':token,'password':PASSWORD})
    assert response.status_code==200,response.text
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+response.json()['access_token']}).json()['user_id']==user['id']

def test_unknown_account_recovery_is_generic_and_status_capability_is_scoped(client,delivery):
    token=proof(client,delivery,purpose='RECOVERY')
    response=client.post('/api/v1/auth/recovery',json={'verification_token':token});assert response.status_code==202,response.text
    body=response.json();assert body['status']=='PENDING_REVIEW' and 'reset_token' not in body and 'user_id' not in body
    url='/api/v1/auth/recovery/'+body['recovery_id']
    assert client.get(url,headers={'X-Recovery-Token':'x'*43}).status_code==401
    assert client.get(url,headers={'X-Recovery-Token':body['recovery_token']}).json()=={'recovery_id':body['recovery_id'],'status':'PENDING_REVIEW'}
    assert client.get('/api/v1/auth/recovery/'+str(uuid4()),headers={'X-Recovery-Token':body['recovery_token']}).status_code==401
    assert client.post(url+'/complete',json={'reset_token':body['recovery_token'],'new_password':'new-password-2026'}).status_code==401

def test_mfa_ticket_requires_factor_and_cannot_be_used_as_bearer(client,identities,organization):
    user=identities('OWNER',organization)
    response=client.post('/api/v1/auth/login',json={'user_id':user['user_id'],'password':PASSWORD})
    assert response.status_code==202 and 'access_token' not in response.json()
    ticket=response.json()['mfa_ticket']
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+ticket}).status_code==401
    response=client.post('/api/v1/auth/mfa/verify',json={'mfa_ticket':ticket,'code':generate_totp_code(user['totp_secret'])})
    assert response.status_code==200,response.text
    assert client.get('/api/v1/organizations/'+organization+'/memberships',headers={'Authorization':'Bearer '+response.json()['access_token']}).status_code==200
    assert client.post('/api/v1/auth/mfa/verify',json={'mfa_ticket':ticket,'code':generate_totp_code(user['totp_secret'])}).status_code==401

def test_five_wrong_mfa_codes_lock_ticket(client,identities,organization):
    user=identities('OWNER',organization);ticket=client.post('/api/v1/auth/login',json={'user_id':user['user_id'],'password':PASSWORD}).json()['mfa_ticket']
    code=generate_totp_code(user['totp_secret']);wrong='000000' if code!='000000' else '111111'
    for _ in range(5):assert client.post('/api/v1/auth/mfa/verify',json={'mfa_ticket':ticket,'code':wrong}).status_code==401
    assert client.post('/api/v1/auth/mfa/verify',json={'mfa_ticket':ticket,'code':code}).status_code==401

def test_recovery_requires_existing_factor_and_revokes_sessions(client,delivery,identities,organization):
    user=identities('OWNER',organization);bind_phone(client,delivery,user)
    codes=client.post('/api/v1/me/security/recovery-codes',headers=user['headers'],json={'current_password':PASSWORD,'totp_code':generate_totp_code(user['totp_secret'])}).json()['recovery_codes']
    with transaction() as conn:
        stored=list(conn.execute(select(table('mfa_credentials').c.secret_encrypted).where(table('mfa_credentials').c.kind=='RECOVERY_CODE')).scalars())
    assert len(codes)==8 and all(code not in stored for code in codes)
    old_ticket=client.post('/api/v1/auth/login',json={'user_id':user['user_id'],'password':PASSWORD}).json()['mfa_ticket']
    token=proof(client,delivery,purpose='RECOVERY')
    response=client.post('/api/v1/auth/recovery',json={'verification_token':token,'recovery_code':codes[0]})
    assert response.status_code==202,response.text
    case=response.json();assert case['status']=='READY_TO_RESET'
    url='/api/v1/auth/recovery/'+case['recovery_id']+'/complete'
    response=client.post(url,json={'reset_token':case['reset_token'],'new_password':'recovered-password-2026'})
    assert response.status_code==200,response.text
    assert client.get('/api/v1/auth/me',headers=user['headers']).status_code==401
    assert client.post('/api/v1/auth/mfa/verify',json={'mfa_ticket':old_ticket,'code':generate_totp_code(user['totp_secret'])}).status_code==401
    assert client.post(url,json={'reset_token':case['reset_token'],'new_password':'another-password-2026'}).status_code==401
    assert client.post('/api/v1/auth/login',json={'user_id':user['user_id'],'password':PASSWORD}).status_code==401
    recovered=login(client,user['user_id'],password='recovered-password-2026')
    assert recovered['mfa_enrollment_required']
    assert client.get('/api/v1/organizations/'+organization+'/memberships',headers=recovered['headers']).status_code==403
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('mfa_credentials')).where(table('mfa_credentials').c.user_id==user['user_id'],table('mfa_credentials').c.revoked_at.is_(None))).scalar_one()==0

def test_otp_only_recovery_cannot_reset_existing_account(client,delivery):
    user=signup(client,delivery);token=proof(client,delivery,purpose='RECOVERY')
    response=client.post('/api/v1/auth/recovery',json={'verification_token':token})
    assert response.status_code==202,response.text
    assert response.json()['status']=='PENDING_REVIEW' and 'reset_token' not in response.json()
    login(client,user['id'])

def test_login_rate_limit_normalizes_phone_aliases(client,delivery):
    signup(client,delivery)
    for i in range(10):
        value=PHONE if i%2 else '+998 (90) 123-45-67'
        assert client.post('/api/v1/auth/login',json={'channel':'PHONE','destination':value,'password':'wrong-password-1234'}).status_code==401
    assert client.post('/api/v1/auth/login',json={'channel':'PHONE','destination':PHONE,'password':PASSWORD}).status_code==429

def test_auth_cache_headers_and_body_limit(client):
    response=client.get('/api/v1/auth/options')
    assert response.headers['cache-control']=='no-store' and response.headers['referrer-policy']=='no-referrer'
    assert client.post('/api/v1/auth/passkeys/verify',content=b'x'*131073,headers={'Content-Type':'application/json'}).status_code==413

class SoftwareAuthenticator:
    """A cryptographic protocol fixture, not a browser or hardware authenticator."""
    def __init__(self,user_id):
        self.user_id=user_id;self.key=ec.generate_private_key(ec.SECP256R1());self.id=secrets.token_bytes(32)
    def client_data(self,kind,challenge,origin,cross_origin=False):
        return json.dumps({'type':kind,'challenge':challenge,'origin':origin,'crossOrigin':cross_origin},separators=(',',':')).encode()
    def registration(self,options,origin='http://localhost:8000',uv=True):
        public=self.key.public_key().public_numbers()
        cose=cbor2.dumps({1:2,3:-7,-1:1,-2:public.x.to_bytes(32,'big'),-3:public.y.to_bytes(32,'big')})
        auth=hashlib.sha256(options['rp']['id'].encode()).digest()+bytes([0x45 if uv else 0x41])+struct.pack('!I',0)+b'\0'*16+struct.pack('!H',len(self.id))+self.id+cose
        data=self.client_data('webauthn.create',options['challenge'],origin)
        return {'id':b64(self.id),'rawId':b64(self.id),'type':'public-key','response':{'clientDataJSON':b64(data),
            'attestationObject':b64(cbor2.dumps({'fmt':'none','attStmt':{},'authData':auth})),'transports':['internal']},'clientExtensionResults':{}}
    def assertion(self,options,count=1,origin='http://localhost:8000',rp='localhost',uv=True,cross_origin=False):
        auth=hashlib.sha256(rp.encode()).digest()+bytes([0x05 if uv else 0x01])+struct.pack('!I',count)
        data=self.client_data('webauthn.get',options['challenge'],origin,cross_origin)
        signature=self.key.sign(auth+hashlib.sha256(data).digest(),ec.ECDSA(hashes.SHA256()))
        return {'id':b64(self.id),'rawId':b64(self.id),'type':'public-key','response':{'clientDataJSON':b64(data),'authenticatorData':b64(auth),
            'signature':b64(signature),'userHandle':b64(UUID(self.user_id).bytes)},'clientExtensionResults':{}}

def enroll_passkey(client,user):
    authenticator=SoftwareAuthenticator(user['user_id'])
    response=client.post('/api/v1/me/security/passkeys/options',headers=user['headers'],json={'current_password':PASSWORD})
    assert response.status_code==200,response.text
    options=response.json()
    response=client.post('/api/v1/me/security/passkeys/verify',headers=user['headers'],json={'ceremony_token':options['ceremony_token'],
        'credential':authenticator.registration(options['public_key'])})
    assert response.status_code==201,response.text
    return authenticator,response.json()['credential_id']

def assertion_options(client,mfa_ticket=None):
    response=client.post('/api/v1/auth/passkeys/options',json={'mfa_ticket':mfa_ticket} if mfa_ticket else {})
    assert response.status_code==200,response.text
    return response.json()

def test_real_passkey_registration_login_counter_and_replay(client,identities):
    user=identities();authenticator,cid=enroll_passkey(client,user)
    assert client.get('/api/v1/auth/me',headers=user['headers']).status_code==401
    options=assertion_options(client)
    assert options['public_key']['userVerification']=='required' and not options['public_key'].get('allowCredentials')
    body={'ceremony_token':options['ceremony_token'],'credential':authenticator.assertion(options['public_key'])}
    response=client.post('/api/v1/auth/passkeys/verify',json=body);assert response.status_code==200,response.text
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+response.json()['access_token']}).json()['user_id']==user['user_id']
    assert client.post('/api/v1/auth/passkeys/verify',json=body).status_code==401
    with transaction() as conn:assert conn.execute(select(table('mfa_credentials').c.sign_count).where(table('mfa_credentials').c.id==cid)).scalar_one()==1

@pytest.mark.parametrize('mutation',['origin','rp','uv','signature','handle','counter'])
def test_passkey_rejects_invalid_assertions(client,identities,mutation):
    user=identities();authenticator,cid=enroll_passkey(client,user);options=assertion_options(client)
    args={'origin':'https://evil.example'} if mutation=='origin' else ({'rp':'evil.example'} if mutation=='rp' else ({'uv':False} if mutation=='uv' else {}))
    credential=authenticator.assertion(options['public_key'],**args)
    if mutation=='signature':credential['response']['signature']=b64(b'x'*64)
    if mutation=='handle':credential['response']['userHandle']=b64(UUID(str(uuid4())).bytes)
    if mutation=='counter':
        with transaction() as conn:conn.execute(table('mfa_credentials').update().where(table('mfa_credentials').c.id==cid).values(sign_count=1))
    response=client.post('/api/v1/auth/passkeys/verify',json={'ceremony_token':options['ceremony_token'],'credential':credential})
    assert response.status_code==401,response.text

def test_passkey_registration_requires_uv_and_own_ceremony(client,identities):
    user,other=identities(),identities();authenticator=SoftwareAuthenticator(user['user_id'])
    options=client.post('/api/v1/me/security/passkeys/options',headers=user['headers'],json={'current_password':PASSWORD}).json()
    body={'ceremony_token':options['ceremony_token'],'credential':authenticator.registration(options['public_key'],uv=False)}
    assert client.post('/api/v1/me/security/passkeys/verify',headers=other['headers'],json=body).status_code==403
    assert client.post('/api/v1/me/security/passkeys/verify',headers=user['headers'],json=body).status_code==401

def test_passkey_completes_password_mfa_ticket(client,identities):
    user=identities();authenticator,_=enroll_passkey(client,user)
    response=client.post('/api/v1/auth/login',json={'user_id':user['user_id'],'password':PASSWORD})
    assert response.status_code==202,response.text
    options=assertion_options(client,response.json()['mfa_ticket'])
    response=client.post('/api/v1/auth/passkeys/verify',json={'ceremony_token':options['ceremony_token'],'credential':authenticator.assertion(options['public_key'])})
    assert response.status_code==200,response.text

def test_sensitive_role_password_session_is_limited(client,identities,organization):
    user=identities('OWNER',organization)
    with transaction() as conn:
        conn.execute(table('mfa_credentials').update().where(table('mfa_credentials').c.user_id==user['user_id']).values(revoked_at=now()))
        auth_service.rotate_security(conn,user['user_id'])
    response=client.post('/api/v1/auth/login',json={'user_id':user['user_id'],'password':PASSWORD})
    assert response.status_code==200 and response.json()['mfa_enrollment_required']
    headers={'Authorization':'Bearer '+response.json()['access_token']}
    assert client.get('/api/v1/auth/me',headers=headers).status_code==200
    assert client.get('/api/v1/organizations/'+organization+'/memberships',headers=headers).status_code==403
    assert client.patch('/api/v1/me/security',headers=headers,json={'enable_totp':True,'current_password':PASSWORD}).status_code==200

def test_passkey_revoke_requires_owner_and_invalidates_sessions(client,identities):
    user,other=identities(),identities();authenticator,cid=enroll_passkey(client,user)
    options=assertion_options(client)
    response=client.post('/api/v1/auth/passkeys/verify',json={'ceremony_token':options['ceremony_token'],'credential':authenticator.assertion(options['public_key'])})
    headers={'Authorization':'Bearer '+response.json()['access_token']}
    assert client.request('DELETE','/api/v1/me/security/passkeys/'+cid,headers=other['headers'],json={'current_password':PASSWORD}).status_code==404
    response=client.request('DELETE','/api/v1/me/security/passkeys/'+cid,headers=headers,json={'current_password':PASSWORD})
    assert response.status_code==200,response.text
    assert client.get('/api/v1/auth/me',headers=headers).status_code==401
    options=assertion_options(client)
    assert client.post('/api/v1/auth/passkeys/verify',json={'ceremony_token':options['ceremony_token'],'credential':authenticator.assertion(options['public_key'],count=2)}).status_code==401

@pytest.mark.parametrize('malformation',['response_type','cross_origin','missing_fields'])
def test_malformed_and_cross_origin_passkeys_fail_closed(client,identities,malformation):
    from webauthn.helpers import base64url_to_bytes
    user=identities();authenticator,_=enroll_passkey(client,user);options=assertion_options(client)
    credential=authenticator.assertion(options['public_key'])
    if malformation=='response_type':credential['response']='invalid'
    elif malformation=='missing_fields':credential={'id':b64(authenticator.id),'response':{}}
    else:
        credential=authenticator.assertion(options['public_key'],cross_origin=True)
    response=client.post('/api/v1/auth/passkeys/verify',json={'ceremony_token':options['ceremony_token'],'credential':credential})
    assert response.status_code==401,response.text

def test_expired_passkey_ceremony_rejected(client,identities):
    user=identities();authenticator,_=enroll_passkey(client,user);options=assertion_options(client)
    with transaction() as conn:
        conn.execute(auth_continuations.update().where(auth_continuations.c.kind=='PASSKEY_LOGIN').values(expires_at=now()-timedelta(seconds=1)))
    assert client.post('/api/v1/auth/passkeys/verify',json={'ceremony_token':options['ceremony_token'],'credential':authenticator.assertion(options['public_key'])}).status_code==401

def test_stale_contact_proof_cannot_recover_previous_phone_owner(client,delivery):
    old=signup(client,delivery);token=proof(client,delivery,purpose='RECOVERY');age_challenges()
    new=signup(client,delivery,name='New owner',password='new-owner-password-2026')
    response=client.post('/api/v1/auth/recovery',json={'verification_token':token,'totp_code':'123456'})
    assert response.status_code==202 and response.json()['status']=='PENDING_REVIEW' and 'reset_token' not in response.json()
    login(client,old['id']);login(client,new['id'],password='new-owner-password-2026')

def test_password_change_cannot_race_with_stale_mfa_ticket(client,identities,organization):
    user=identities('OWNER',organization)
    ticket=client.post('/api/v1/auth/login',json={'user_id':user['user_id'],'password':PASSWORD}).json()['mfa_ticket']
    with transaction() as conn:auth_service.rotate_security(conn,user['user_id'])
    assert client.post('/api/v1/auth/mfa/verify',json={'mfa_ticket':ticket,'code':generate_totp_code(user['totp_secret'])}).status_code==401

def test_delivery_adapter_http_protocol(monkeypatch):
    import httpx
    from app.adapters import identity_delivery
    monkeypatch.setenv('AUTH_DELIVERY_URL','https://delivery.test.invalid');monkeypatch.setenv('AUTH_DELIVERY_TOKEN',secrets.token_urlsafe(32))
    seen=[];original_client=httpx.Client
    def respond(request):
        body=json.loads(request.content);seen.append(body)
        assert request.headers['Idempotency-Key']==body['request_id']
        return httpx.Response(200,json={'request_id':body['request_id'],'status':'ACCEPTED'})
    monkeypatch.setattr(identity_delivery.httpx,'Client',lambda **kwargs:original_client(transport=httpx.MockTransport(respond),**kwargs))
    identity_delivery.send(challenge_id=str(uuid4()),channel='PHONE',destination=PHONE,code='123456',ttl_seconds=300)
    assert seen[0]['channel']=='PHONE' and seen[0]['ttl_seconds']==300

def test_recent_passkey_can_replace_lost_totp(client,identities,organization):
    user=identities('OWNER',organization);authenticator,cid=enroll_passkey(client,user)
    options=assertion_options(client)
    response=client.post('/api/v1/auth/passkeys/verify',json={'ceremony_token':options['ceremony_token'],'credential':authenticator.assertion(options['public_key'])})
    assert response.status_code==200,response.text
    headers={'Authorization':'Bearer '+response.json()['access_token']}
    response=client.patch('/api/v1/me/security',headers=headers,json={'enable_totp':False,'current_password':PASSWORD})
    assert response.status_code==200,response.text
    with transaction() as conn:
        assert conn.execute(select(table('mfa_credentials').c.revoked_at).where(table('mfa_credentials').c.id==cid)).scalar_one() is None
    options=assertion_options(client)
    response=client.post('/api/v1/auth/passkeys/verify',json={'ceremony_token':options['ceremony_token'],'credential':authenticator.assertion(options['public_key'],count=2)})
    assert response.status_code==200,response.text
    assert client.get('/api/v1/organizations/'+organization+'/memberships',headers={'Authorization':'Bearer '+response.json()['access_token']}).status_code==200

def test_otp_proof_shared_with_second_process(client,delivery):
    import subprocess,sys
    from pathlib import Path
    cid,code=request_code(client,delivery)
    source='import json,sys; from app.services.identity import identity_service; print(json.dumps(identity_service.consume(**json.load(sys.stdin))))'
    result=subprocess.run([sys.executable,'-c',source],input=json.dumps({'challenge_id':cid,'purpose':'REGISTER','code':code,'ip':'child-process'}),
        cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    token=json.loads(result.stdout)['verification_token']
    response=client.post('/api/v1/auth/register',json={'display_name':'Sardor','password':PASSWORD,'adult_confirmed':True,
        'verification_token':token,'terms_version':'test-terms-v1','privacy_version':'test-privacy-v1'})
    assert response.status_code==201,response.text

def test_identity_worker_filter_does_not_wait_for_pdf_jobs():
    from app.db.storage import enqueue,outbox_table
    from app.workers.outbox import relay_pending_outbox_events
    with transaction() as conn:
        pdf=enqueue(conn,'FILE_SCAN_REQUESTED','pdf',{},'queued-pdf')
        otp=enqueue(conn,'AUTH_OTP_DELIVERY','otp',{},'queued-otp')
    seen=[]
    registry={kind:(lambda e:e['event_type'],lambda c,e,r:seen.append(r)) for kind in ['FILE_SCAN_REQUESTED','AUTH_OTP_DELIVERY']}
    assert relay_pending_outbox_events(event_types=('AUTH_OTP_DELIVERY',),registry=registry)==1
    assert seen==['AUTH_OTP_DELIVERY']
    with transaction() as conn:
        assert conn.execute(select(outbox_table.c.processed_at).where(outbox_table.c.id==pdf)).scalar_one() is None

def test_expired_otp_secrets_and_old_state_are_cleaned(client,delivery):
    from app.core.iam_security import issue_continuation
    from app.workers.outbox import relay_pending_outbox_events
    response=client.post('/api/v1/auth/challenges',json={'channel':'PHONE','destination':PHONE,'purpose':'REGISTER'})
    assert response.status_code==202;cid=response.json()['challenge_id']
    with transaction() as conn:
        conn.execute(table('auth_challenges').update().where(table('auth_challenges').c.id==cid).values(expires_at=now()-timedelta(seconds=1)))
    identity_service.expire_state()
    with transaction() as conn:
        row=conn.execute(select(table('auth_challenges')).where(table('auth_challenges').c.id==cid)).mappings().one()
        assert row['delivery_encrypted'] is None and row['delivery_status']=='EXPIRED'
        issue_continuation(conn,'CONTACT_REGISTER',challenge_id=cid,payload={})
        conn.execute(auth_continuations.update().values(created_at=now()-timedelta(days=2),expires_at=now()-timedelta(days=1)))
        conn.execute(table('auth_challenges').update().values(created_at=now()-timedelta(days=2)))
        conn.execute(auth_rate_limits.update().values(window_started_at=now()-timedelta(days=2)))
    identity_service.expire_state()
    with transaction() as conn:
        for t in [table('auth_challenges'),auth_continuations,auth_rate_limits]:assert conn.execute(select(func.count()).select_from(t)).scalar_one()==0
    assert relay_pending_outbox_events()==1 and delivery=={}

def test_totp_rfc_vectors_boundary_and_non_ascii():
    from app.services.auth import verify_totp_code
    secret='GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'
    for timestamp,expected in [(59,'287082'),(1111111109,'081804'),(1111111111,'050471'),(1234567890,'005924'),(2000000000,'279037'),(20000000000,'353130')]:
        assert generate_totp_code(secret,timestamp)==expected
    code=generate_totp_code(secret,59)
    assert verify_totp_code(secret,code,60)
    assert not verify_totp_code(secret,code,90)
    assert not verify_totp_code(secret,'٠٠٠٠٠٠',59)
