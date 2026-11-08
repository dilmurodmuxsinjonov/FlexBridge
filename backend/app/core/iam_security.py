"""Cryptographic purpose binding and durable, independent IAM admission counters."""
import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import timedelta
from cryptography.fernet import Fernet,InvalidToken
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.db.storage import transaction,auth_continuations,auth_rate_limits,now
from app.services.auth import AuthError

SENSITIVE_ROLES=frozenset({'OWNER','BILLING','COORDINATOR','MODERATOR','SUPPORT','FINANCE','ADMIN'})

def digest(kind,value):
    key=os.environ.get('AUTH_HMAC_KEY','')
    if len(key)<32: raise AuthError('IAM_CONFIGURATION_REQUIRED','IAM signing key is not configured',503)
    return hmac.new(key.encode(),(kind+'\0'+str(value)).encode(),hashlib.sha256).hexdigest()

def cipher():
    try:return Fernet(os.environ['MFA_ENCRYPTION_KEY'].encode())
    except (KeyError,ValueError):raise AuthError('IAM_CONFIGURATION_REQUIRED','IAM encryption is not configured',503)

def encrypt(value):return cipher().encrypt(json.dumps(value,separators=(',',':')).encode()).decode()
def decrypt(value):
    try:return json.loads(cipher().decrypt(value.encode()))
    except (InvalidToken,ValueError,TypeError):raise AuthError('IAM_STATE_INVALID','IAM state cannot be verified',503)

def normalize_contact(channel,destination):
    value=destination.strip()
    if channel=='PHONE':
        value=re.sub(r'[ ()-]','',value)
        if not re.fullmatch(r'\+[1-9][0-9]{7,14}',value):raise AuthError('INVALID_CONTACT','Use international phone format',422)
    elif channel=='EMAIL':
        value=value.casefold()
        if len(value)>254 or not re.fullmatch(r'[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+',value) or any(ord(c)<33 or ord(c)==127 for c in value):
            raise AuthError('INVALID_CONTACT','Invalid email address',422)
    else:raise AuthError('INVALID_CHANNEL','Use PHONE or EMAIL',422)
    return value

def rate_limit(kind,value,limit,seconds):
    """Called before business UoW, so rejected business actions cannot roll back counters."""
    key=digest('rate:'+kind,value)
    exceeded=False
    with transaction() as conn:
        created=conn.execute(insert(auth_rate_limits).values(bucket_key=key,window_started_at=now(),count=1)
            .on_conflict_do_nothing().returning(auth_rate_limits.c.bucket_key)).scalar_one_or_none()
        row=conn.execute(select(auth_rate_limits).where(auth_rate_limits.c.bucket_key==key).with_for_update()).mappings().one()
        if created:pass
        elif row['window_started_at']+timedelta(seconds=seconds)<=now():
            conn.execute(auth_rate_limits.update().where(auth_rate_limits.c.bucket_key==key).values(window_started_at=now(),count=1))
        elif row['count']>=limit:exceeded=True
        else:conn.execute(auth_rate_limits.update().where(auth_rate_limits.c.bucket_key==key).values(count=row['count']+1))
    if exceeded:raise AuthError('RATE_LIMITED','Try again later',429)

def issue_continuation(conn,kind,*,user_id=None,challenge_id=None,payload=None,ttl=300):
    token=secrets.token_urlsafe(32)
    conn.execute(auth_continuations.insert().values(digest=digest('continuation',token),kind=kind,user_id=user_id,challenge_id=challenge_id,
        payload_encrypted=encrypt(payload or {}),created_at=now(),expires_at=now()+timedelta(seconds=ttl),attempts=0))
    return token

def continuation(conn,token,kind,*,consume=False):
    row=conn.execute(select(auth_continuations).where(auth_continuations.c.digest==digest('continuation',token)).with_for_update()).mappings().first()
    if not row or row['kind']!=kind or row['consumed_at'] or row['expires_at']<=now() or row['attempts']>=5:
        raise AuthError('INVALID_OR_EXPIRED_PROOF','Verification is required',401)
    if consume:conn.execute(auth_continuations.update().where(auth_continuations.c.digest==row['digest']).values(consumed_at=now()))
    return {**row,'payload':decrypt(row['payload_encrypted'])}
