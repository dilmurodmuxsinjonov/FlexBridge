"""Fresh authority never revives a former departure; persistence and rollback."""
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.db.storage import table,transaction
from test_owner_transfers import setup_transfer,ready,submit,consent,NOTE
from test_owner_additions import ready as addition_ready,has_owner
from test_owner_grant_boundaries import revoke,rejoin_staff
from test_candidate import cv_fixture
from test_invitations import contact
from test_organizations import claim,decide

@pytest.mark.parametrize('participant',['requester','successor'])
def test_revoke_reinvite_and_reviewed_regrant_requires_new_departure_request(client,setup_transfer,participant):
    flow=setup_transfer;old_case=ready(client,flow)
    changed=flow['owner'] if participant=='requester' else flow['target']
    authority=flow['target'] if participant=='requester' else flow['owner']
    membership=flow['owner_member'] if participant=='requester' else flow['target_member']
    verified=contact(changed,value=str(uuid4())+'@example.test',channel='EMAIL') if participant=='requester' else flow['contact']
    revoke(client,authority,flow['org'],membership)
    rejoin_staff(client,authority,changed,flow['org'],verified)
    restoration={**flow,'owner':authority,'target':changed,'target_member':membership,'file':cv_fixture(authority),'contact':verified}
    restoring_case=addition_ready(client,restoration)
    response=decide(client,flow['moderator'],restoring_case);assert response.status_code==200,response.text
    assert has_owner(flow['owner_member']) and has_owner(flow['target_member'])
    response=decide(client,flow['moderator'],old_case);assert response.status_code==409,response.text
    if participant=='successor':
        response=consent(client,flow,old_case);assert response.status_code==409,response.text
    response=client.post('/api/v1/owner-transfers/'+old_case+'/cancel',headers=flow['owner']['headers'],json={
        'reason':'Discard the intent bound to the former original grant'})
    assert response.status_code==200,response.text
    response=submit(client,flow,key='new-transfer-with-current-grant');assert response.status_code==202,response.text
    fresh=response.json()['id'];response=consent(client,flow,fresh);assert response.status_code==200,response.text
    response=claim(client,flow['moderator'],fresh);assert response.status_code==200,response.text
    response=decide(client,flow['moderator'],fresh);assert response.status_code==200,response.text
    assert not has_owner(flow['owner_member']) and has_owner(flow['target_member'])

@pytest.mark.parametrize('phase',['proposal','consent'])
def test_audit_failure_leaves_no_partial_intent(client,setup_transfer,monkeypatch,phase):
    from app.services.owner_transfers import owner_transfer_service
    flow=setup_transfer;case=None
    if phase=='consent':
        response=submit(client,flow);assert response.status_code==202,response.text
        case=response.json()['id']
    def fail(**kwargs):raise RuntimeError('Synthetic ownership intent audit failure')
    monkeypatch.setattr(owner_transfer_service.audit_store,'append_audit_event',fail)
    response=submit(client,flow) if phase=='proposal' else consent(client,flow,case)
    assert response.status_code==503,response.text
    assert has_owner(flow['owner_member']) and has_owner(flow['target_member'])
    with transaction() as conn:
        assert conn.execute(select(func.count()).select_from(table('owner_transfer_consents'))).scalar_one()==0
        assert conn.execute(select(func.count()).select_from(table('owner_transfer_requests'))).scalar_one()==(0 if phase=='proposal' else 1)
        if case:assert conn.execute(select(table('verification_cases').c.status).where(table('verification_cases').c.id==case)).scalar_one()=='WAITING_CONSENT'

def test_departed_requester_can_read_receipt_in_second_process(client,setup_transfer):
    flow=setup_transfer;case=ready(client,flow)
    response=decide(client,flow['moderator'],case);assert response.status_code==200,response.text
    user=flow['owner'];env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[2])}
    code="from app.api.dependencies import ActorContext;from app.services.owner_transfers import owner_transfer_service;import sys,json;r=owner_transfer_service.read(ActorContext(sys.argv[1],sys.argv[2],()),sys.argv[3]);print(json.dumps({'id':r['id'],'status':r['status'],'decision':r['consent']['decision']}))"
    child=subprocess.run([sys.executable,'-c',code,user['user_id'],user['session_id'],case],env=env,capture_output=True,text=True,check=True)
    assert json.loads(child.stdout)=={'id':case,'status':'APPROVED','decision':'ACCEPT'}

def test_successor_can_refresh_consent_after_account_security_change(client,setup_transfer):
    from app.services.auth import generate_totp_code
    flow=setup_transfer;case=ready(client,flow)
    with transaction() as conn:
        conn.execute(table('users').update().where(table('users').c.id==flow['target']['user_id']).values(auth_version=table('users').c.auth_version+1))
    response=decide(client,flow['moderator'],case);assert response.status_code==409,response.text
    response=consent(client,flow,case);assert response.status_code==401,response.text
    target=flow['target']
    response=client.post('/api/v1/auth/login',json={'user_id':target['user_id'],'password':'correct-passphrase-2026',
        'totp_code':generate_totp_code(target['totp_secret'])})
    assert response.status_code==200,response.text
    signed_in={**target,'headers':{'Authorization':'Bearer '+response.json()['access_token']}}
    response=consent(client,flow,case,actor=signed_in);assert response.status_code==200 and not response.json()['idempotent_replay'],response.text
    response=decide(client,flow['moderator'],case);assert response.status_code==200,response.text
