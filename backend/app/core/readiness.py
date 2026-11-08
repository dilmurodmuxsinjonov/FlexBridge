"""Readiness reflects live dependencies, never a manually asserted environment flag."""
from datetime import datetime, timezone
import os
import socket
from sqlalchemy import text
from app.db.storage import init_storage,load_domain_record

def dependency_readiness():
    checks={}
    try:
        engine=init_storage()
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        checks['database']=True
    except Exception: checks['database']=False
    try:
        from app.adapters.storage import client
        client().head_bucket(Bucket=os.environ['S3_BUCKET'])
        checks['object_storage']=True
    except Exception: checks['object_storage']=False
    try:
        with socket.create_connection((os.environ['CLAMAV_HOST'],int(os.environ.get('CLAMAV_PORT','3310'))),timeout=2) as conn:
            conn.settimeout(2);conn.sendall(b'zPING\0')
            checks['antivirus']=conn.recv(64).rstrip(b'\0\r\n')==b'PONG'
    except Exception: checks['antivirus']=False
    try:
        row=load_domain_record('worker_heartbeat','outbox')
        checks['outbox_worker']=bool(row and 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(row['at'])).total_seconds()<60)
    except Exception: checks['outbox_worker']=False
    try:
        row=load_domain_record('worker_heartbeat','identity')
        checks['identity_worker']=bool(row and 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(row['at'])).total_seconds()<60)
    except Exception:checks['identity_worker']=False
    checks['payment_configuration']=bool(len(os.environ.get('PAYMENT_WEBHOOK_SECRET',''))>=32
        and os.environ.get('PAYMENT_GATEWAY_URL','').startswith('https://') and os.environ.get('PAYMENT_GATEWAY_TOKEN'))
    try:
        from cryptography.fernet import Fernet
        Fernet(os.environ['MFA_ENCRYPTION_KEY'].encode())
        checks['mfa_configuration']=True
    except Exception: checks['mfa_configuration']=False
    try:
        from app.core.iam_security import digest
        from app.adapters.identity_delivery import configuration
        from app.services.passkeys import rp_configuration
        digest('readiness','configuration');configuration();rp_configuration()
        checks['identity_configuration']=bool(os.environ.get('TERMS_POLICY_VERSION') and os.environ.get('PRIVACY_POLICY_VERSION'))
    except Exception:checks['identity_configuration']=False
    return {'ready':all(checks.values()),'checks':checks}
