"""Native HTTP invitation flow and Uvicorn access-log token redaction."""
import importlib.util,json,os,socket,subprocess,sys,time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/tests/security')]
spec=importlib.util.spec_from_file_location('invite_smoke_fixtures',ROOT/'backend/tests/conftest.py')
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
from test_organizations import mfa_user
from test_invitations import contact,DEST


def main():
    database=fixtures.database.__wrapped__();next(database)
    server=None
    try:
        create=fixtures.identities.__wrapped__();org=fixtures.organization.__wrapped__()
        owner=create('OWNER',org);user=mfa_user(create);contact(user)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
            cwd=ROOT/'backend',env=os.environ.copy(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with httpx.Client(base_url='http://127.0.0.1:'+str(port),timeout=15,trust_env=False) as client:
            for _ in range(100):
                try:
                    if client.get('/api/v1/health/live').status_code==200:break
                except httpx.HTTPError:pass
                if server.poll() is not None:raise RuntimeError('Native API stopped')
                time.sleep(.1)
            else:raise RuntimeError('Native API did not start')
            response=client.post('/api/v1/organizations/'+org+'/invitations',headers=owner['headers'],json={
                'channel':'PHONE','destination':DEST,'role_code':'HR'})
            assert response.status_code==201
            token=response.json()['token'];path='/api/v1/invitations/'+token
            preview=client.get(path)
            assert preview.status_code==200 and preview.headers['referrer-policy']=='no-referrer'
            accepted=client.post(path+'/accept',headers=user['headers'],json={})
            assert accepted.status_code==200
            repeated=client.post(path+'/accept',headers=user['headers'],json={})
            assert repeated.status_code==200 and repeated.json()['idempotent_replay']
            assert client.get(path).status_code==404
            assert 'HR' in client.get('/api/v1/auth/me',headers=user['headers']).json()['roles']
        server.terminate();stdout,stderr=server.communicate(timeout=10)
        logs=(stdout+stderr).decode('utf-8',errors='replace')
        assert token not in logs,'Invitation token appeared in native access log'
        assert 'REDACTED' in logs,'Native access log did not exercise redaction'
        Path(__file__).with_name('access_log_redacted.txt').write_text(logs,encoding='utf-8')
        result={'checks':6,'passed':6,'native_access_log_token_redacted':True,
            'scope':'Native uvicorn, disposable PostgreSQL; verified contact fixture, no real SMS/email delivery'}
        Path(__file__).with_name('native_smoke.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(result)
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:server.communicate(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.communicate(timeout=10)
        database.close()

if __name__=='__main__':main()
