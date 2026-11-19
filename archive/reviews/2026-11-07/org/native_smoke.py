"""Native uvicorn ORG flow using disposable SQL identities and explicit CLEAN metadata fixtures."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'backend'), str(ROOT/'backend/tests/security')]
spec = importlib.util.spec_from_file_location('org_smoke_fixtures', ROOT/'backend/tests/conftest.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
from test_organizations import mfa_user
from test_candidate import cv_fixture


def main():
    database = fixtures.database.__wrapped__()
    next(database)
    server = None
    statuses = []
    try:
        create = fixtures.identities.__wrapped__()
        user, moderator = mfa_user(create), create('MODERATOR')
        file = cv_fixture(user)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
        server = subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
            cwd=ROOT/'backend', env=os.environ.copy(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with httpx.Client(base_url='http://127.0.0.1:'+str(port), timeout=15, trust_env=False) as client:
            for _ in range(100):
                try:
                    if client.get('/api/v1/health/live').status_code == 200: break
                except httpx.HTTPError: pass
                if server.poll() is not None: raise RuntimeError('Native API stopped before smoke test')
                time.sleep(.1)
            else: raise RuntimeError('Native API did not start')
            def request(method,path,actor=None,body=None,expected=200):
                response = client.request(method,path,headers=actor['headers'] if actor else {},json=body)
                assert response.status_code == expected,(method,path,response.status_code)
                statuses.append({'method':method,'path':path,'status':response.status_code})
                return response.json()
            created = request('POST','/api/v1/organizations',user,{'tax_id':'123456789','legal_name':'Native Company',
                'public_name':'Native Company','region':'Tashkent','file_ids':[file['id']],
                'evidence_note':'Synthetic representative proof'},202)
            org,case = created['organization_id'],created['case_id']
            request('POST','/api/v1/operator/verification-cases/'+case+'/claim',moderator)
            decision={'decision':'APPROVE','expected_revision':1,'reason':'Independent synthetic proof reviewed'}
            request('POST','/api/v1/operator/verification-cases/'+case+'/decide',moderator,decision)
            request('GET','/api/v1/organizations/'+org+'/memberships',user)
            public = request('GET','/api/v1/organizations/'+org+'/public')
            assert public['capabilities']==[]
            cap = request('POST','/api/v1/organizations/'+org+'/verification',user,{
                'kind':'JOB_EMPLOYER','file_ids':[file['id']],'evidence_note':'Synthetic capability proof'},202)['id']
            request('POST','/api/v1/operator/verification-cases/'+cap+'/claim',moderator)
            request('POST','/api/v1/operator/verification-cases/'+cap+'/decide',moderator,decision)
            public = request('GET','/api/v1/organizations/'+org+'/public')
            assert public['capabilities']==['JOB_EMPLOYER']
            request('POST','/api/v1/organizations/'+org+'/memberships/'+created['membership_id']+'/revoke',
                user,{'reason':'Synthetic last owner revocation'},409)
        result={'checks':statuses,'passed':len(statuses),'scope':'Native HTTP, real disposable PostgreSQL; CLEAN file metadata fixture, no live document scanner/registry'}
        Path(__file__).with_name('native_smoke.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print({'passed':len(statuses)})
    finally:
        if server is not None:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill();server.wait(timeout=10)
        database.close()


if __name__ == '__main__':main()
