"""Native API + separate worker + real local HTTPS gateway, without sending SMS/email."""
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import ipaddress
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.error
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sqlalchemy import select
from app.db.storage import transaction,table

ROOT=Path(__file__).resolve().parents[3]

def test_native_http_registration_with_tls_delivery_and_worker():
    received={};accepted=threading.Event();gateway_token=secrets.token_urlsafe(32)
    class Gateway(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.path=='/otp' and self.headers['Authorization']=='Bearer '+gateway_token
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert self.headers['Idempotency-Key']==body['request_id']
            received[body['request_id']]=body;raw=json.dumps({'request_id':body['request_id'],'status':'ACCEPTED'}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            accepted.set()
        def log_message(self,*args):pass
    temporary_root=(ROOT/'backend/.data').resolve();temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temporary_root,prefix='iam-http-') as folder:
        temp=Path(folder).resolve();assert temp.parent==temporary_root and temp.name.startswith('iam-http-')
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])
        certificate=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())\
            .not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=1)).not_valid_after(datetime.now(timezone.utc)+timedelta(days=1))\
            .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)\
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1')),x509.DNSName('localhost')]),critical=False).sign(key,hashes.SHA256())
        cert_path=temp/'cert.pem';key_path=temp/'key.pem'
        cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert_path,key_path)
        gateway=HTTPServer(('127.0.0.1',0),Gateway);gateway.socket=context.wrap_socket(gateway.socket,server_side=True)
        gateway_thread=threading.Thread(target=gateway.serve_forever,daemon=True);gateway_thread.start()
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env={**os.environ,'AUTH_DELIVERY_URL':'https://127.0.0.1:'+str(gateway.server_port),'AUTH_DELIVERY_TOKEN':gateway_token,
            'SSL_CERT_FILE':str(cert_path),'NO_PROXY':'127.0.0.1,localhost','OUTBOX_EVENT_TYPES':'AUTH_OTP_DELIVERY','OUTBOX_WORKER_KEY':'identity'}
        flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        processes=[]
        with (temp/'processes.log').open('w',encoding='utf-8') as log:
            try:
                for command in [[sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
                    [sys.executable,'-m','app.workers.outbox']]:
                    processes.append(subprocess.Popen(command,cwd=ROOT/'backend',env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=flags))
                base='http://127.0.0.1:'+str(port)
                def request(path,body=None,token=None):
                    headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})}
                    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
                    with urllib.request.urlopen(req,timeout=5) as response:return response.status,json.load(response)
                for _ in range(100):
                    try:request('/api/v1/health/live');break
                    except (OSError,urllib.error.URLError):time.sleep(.05)
                status,challenge=request('/api/v1/auth/challenges',{'channel':'PHONE','destination':'+998901234567','purpose':'REGISTER'})
                assert status==202 and 'code' not in challenge
                assert accepted.wait(10),'Local TLS gateway did not receive the queued challenge'
                cid=challenge['challenge_id']
                for _ in range(100):
                    with transaction() as conn:sent=conn.execute(select(table('auth_challenges').c.delivery_status).where(table('auth_challenges').c.id==cid)).scalar_one()=='SENT'
                    if sent:break
                    time.sleep(.02)
                assert sent
                status,verified=request('/api/v1/auth/challenges/'+cid+'/consume',{'purpose':'REGISTER','code':received[cid]['code']});assert status==200
                status,user=request('/api/v1/auth/register',{'display_name':'Sardor','password':'native-http-password-2026','adult_confirmed':True,
                    'verification_token':verified['verification_token'],'terms_version':'test-terms-v1','privacy_version':'test-privacy-v1'});assert status==201
                status,session=request('/api/v1/auth/login',{'channel':'PHONE','destination':'+998901234567','password':'native-http-password-2026'});assert status==200
                status,me=request('/api/v1/auth/me',token=session['access_token']);assert status==200 and me['user_id']==user['id']
            finally:
                for process in reversed(processes):
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
                gateway.shutdown();gateway.server_close();gateway_thread.join(timeout=3)
