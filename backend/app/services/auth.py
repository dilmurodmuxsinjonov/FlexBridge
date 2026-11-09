"""Opaque sessions, canonical grants and standard Argon2id. No cache grants authority."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from datetime import timedelta
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from argon2.low_level import Type
from cryptography.fernet import Fernet
from sqlalchemy import select, and_

from app.db.storage import now, table, transaction

PUBLIC_REGISTER_ALLOWED_ROLES = frozenset({'CANDIDATE'})
_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, type=Type.ID)

class AuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int=401):
        super().__init__(message)
        self.code, self.status_code = code, status_code

def hash_password(password: str, salt: str | None=None) -> str:
    # Explicit salt is for deterministic cryptographic unit tests, never HTTP input.
    return _HASHER.hash(password, salt=salt.encode() if salt else None)

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return _HASHER.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False

def generate_totp_code(secret: str, timestamp: int | None=None, step: int=30) -> str:
    key = base64.b32decode(secret.upper() + '='*((8-len(secret)%8)%8))
    digest = hmac.new(key, struct.pack('>Q', (int(time.time()) if timestamp is None else timestamp)//step), hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = (struct.unpack('>I', digest[offset:offset+4])[0] & 0x7fffffff) % 1000000
    return f'{value:06d}'

def verify_totp_code(secret,code,timestamp=None):
    if not isinstance(code,str) or len(code)!=6 or not all('0'<=c<='9' for c in code):return False
    current=int(time.time()) if timestamp is None else timestamp
    # Account for entry/transmission at the 30-second boundary and one step of clock skew.
    comparisons=[hmac.compare_digest(generate_totp_code(secret,max(0,current+offset*30)),code) for offset in (-1,0,1)]
    return any(comparisons)

def _cipher() -> Fernet:
    key = os.environ.get('MFA_ENCRYPTION_KEY')
    if not key:
        raise AuthError('MFA_CONFIGURATION_REQUIRED', 'MFA encryption is not configured', 503)
    return Fernet(key.encode())

def roles_for(conn, user_id: str) -> list[str]:
    roles = {'CANDIDATE'}
    grants, catalog = table('platform_role_grants'), table('role_catalog')
    roles.update(conn.execute(select(catalog.c.code).select_from(grants.join(catalog, grants.c.role_id==catalog.c.id)).where(
        grants.c.user_id==user_id, grants.c.revoked_at.is_(None), grants.c.expires_at>now(),catalog.c.scope_kind=='PLATFORM')).scalars())
    for membership_name, grant_name in [('org_memberships','org_role_grants')]:
        membership, scoped = table(membership_name), table(grant_name)
        roles.update(conn.execute(select(catalog.c.code).select_from(membership.join(scoped, scoped.c.membership_id==membership.c.id)
            .join(catalog, catalog.c.id==scoped.c.role_id)).where(membership.c.user_id==user_id,
            membership.c.status=='ACTIVE', membership.c.revoked_at.is_(None), scoped.c.revoked_at.is_(None),catalog.c.scope_kind=='ORG')).scalars())
    from app.db.institution_scope import institution_scope_query
    roles.update(conn.execute(institution_scope_query(user_id).with_only_columns(catalog.c.code)).scalars())
    return sorted(roles)

class AuthSessionService:
    def register_user(self, *, display_name: str, password: str, adult_confirmed: bool,
                      roles: list[str] | None=None, enable_totp: bool=False, **unused):
        if not adult_confirmed:
            raise AuthError('ADULT_DECLARATION_REQUIRED','An adult declaration is required',422)
        if set(roles or ['CANDIDATE']) != {'CANDIDATE'}:
            raise AuthError('FORBIDDEN_PRIVILEGED_ROLE_REGISTRATION','Roles are assigned through verified grants',403)
        if enable_totp:
            raise AuthError('MFA_ENROLLMENT_REQUIRED','Enable MFA through authenticated enrollment',422)
        user_id = str(uuid4())
        with transaction() as conn:
            conn.execute(table('users').insert().values(id=user_id, created_at=now(), updated_at=now(),
                display_name=display_name, password_hash=hash_password(password), status='ACTIVE', locale='uz',
                timezone='Asia/Tashkent', adult_declared_at=now()))
            conn.execute(table('candidate_profiles').insert().values(id=str(uuid4()), created_at=now(),updated_at=now(),
                user_id=user_id,headline=display_name,region='',experience_months=0,visibility='PRIVATE'))
        return self._load_user(user_id)

    def _load_user(self, user_id):
        with transaction() as conn:
            row = conn.execute(select(table('users')).where(table('users').c.id==user_id)).mappings().first()
            if row is None:
                return None
            user = dict(row)
            user['roles'] = roles_for(conn,user_id)
            credential = conn.execute(select(table('mfa_credentials')).where(table('mfa_credentials').c.user_id==user_id,
                table('mfa_credentials').c.kind=='TOTP',table('mfa_credentials').c.revoked_at.is_(None),
                table('mfa_credentials').c.verified_at.is_not(None))).mappings().first()
            user['totp_secret'] = _cipher().decrypt(credential['secret_encrypted'].encode()).decode() if credential else None
            user['has_passkey']=conn.execute(select(table('mfa_credentials').c.id).where(table('mfa_credentials').c.user_id==user_id,
                table('mfa_credentials').c.kind=='PASSKEY',table('mfa_credentials').c.revoked_at.is_(None),
                table('mfa_credentials').c.verified_at.is_not(None))).first() is not None
            return user

    def login(self, *, user_id, password, totp_code=None):
        with transaction() as conn:
            user=self.check_password(conn,user_id,password)
            if user['has_passkey'] and not user['totp_secret']:
                raise AuthError('MFA_REQUIRED','Verify a registered passkey')
            if user['totp_secret'] and not verify_totp_code(user['totp_secret'],totp_code):
                raise AuthError('TOTP_REQUIRED_OR_INVALID','MFA verification required')
            return self.issue_session(conn,user_id,assurance='MFA' if user['totp_secret'] else 'PASSWORD')

    def check_password(self,conn,user_id,password):
        row=conn.execute(select(table('users')).where(table('users').c.id==user_id).with_for_update()).mappings().first()
        valid=verify_password(password,row['password_hash'] if row and row['password_hash'] else _DUMMY_HASH)
        if not row or not valid or row['status']!='ACTIVE':
            raise AuthError('INVALID_CREDENTIALS','Invalid credentials')
        return self._load_user(user_id)

    def issue_session(self,conn,user_id,*,assurance):
        user=conn.execute(select(table('users')).where(table('users').c.id==user_id).with_for_update()).mappings().one()
        if user['status']!='ACTIVE':raise AuthError('INVALID_CREDENTIALS','Invalid credentials')
        token = secrets.token_urlsafe(32)
        session_id = str(uuid4())
        conn.execute(table('sessions').insert().values(id=session_id,user_id=user_id,auth_version=user['auth_version'],
            created_at=now(),updated_at=now(),token_digest=hashlib.sha256(token.encode()).hexdigest(),
            assurance=assurance,expires_at=now()+timedelta(hours=12),last_seen_at=now()))
        return {'session_id':session_id,'access_token':token,'token_type':'bearer','expires_in':43200}

    def validate_session(self, token):
        digest = hashlib.sha256(token.encode()).hexdigest()
        sessions, users = table('sessions'),table('users')
        with transaction() as conn:
            row = conn.execute(select(sessions,users.c.status.label('user_status'),users.c.auth_version.label('user_auth_version')).select_from(sessions.join(users,sessions.c.user_id==users.c.id))
                .where(sessions.c.token_digest==digest)).mappings().first()
            if not row or row['revoked_at'] or row['user_status']!='ACTIVE' or row['auth_version']!=row['user_auth_version']:
                raise AuthError('AUTH_REVOKED','Session is invalid or revoked')
            if row['expires_at'] <= now():
                raise AuthError('SESSION_EXPIRED','Session has expired')
            return {'session_id':row['id'],'user_id':row['user_id'],'roles':roles_for(conn,row['user_id']),
                'assurance':row['assurance'],'expires_at':row['expires_at'],'status':'ACTIVE'}

    def rotate_security(self,conn,user_id):
        users,sessions=table('users'),table('sessions')
        conn.execute(select(users.c.id).where(users.c.id==user_id).with_for_update())
        conn.execute(users.update().where(users.c.id==user_id).values(auth_version=users.c.auth_version+1,updated_at=now()))
        conn.execute(sessions.update().where(sessions.c.user_id==user_id,sessions.c.revoked_at.is_(None)).values(revoked_at=now(),updated_at=now()))

    def revoke_session(self, *, session_id, actor_id, reason='USER_LOGOUT', require_owner_user_id=None):
        from app.core.audit import AppendOnlyAuditStore
        sessions = table('sessions')
        with transaction() as conn:
            conn.execute(select(table('users').c.id).where(table('users').c.id==actor_id).with_for_update())
            row = conn.execute(select(sessions).where(sessions.c.id==session_id).with_for_update()).mappings().first()
            if not row:
                raise AuthError('SESSION_NOT_FOUND','Session not found',404)
            if row['user_id'] != actor_id:
                raise AuthError('FORBIDDEN_SESSION_SCOPE','Only the session owner can revoke it',403)
            conn.execute(sessions.update().where(sessions.c.id==session_id).values(revoked_at=now(),updated_at=now()))
            AppendOnlyAuditStore().append_audit_event(actor_id=actor_id,action='SESSION_REVOKED',entity_type='session',entity_id=session_id,
                metadata={'reason':reason})
            return {'session_id':session_id,'status':'REVOKED','revoked_at':now()}

    def revoke_all_user_sessions(self, *, user_id, actor_id, reason):
        sessions=table('sessions')
        with transaction() as conn:
            return conn.execute(sessions.update().where(sessions.c.user_id==user_id,sessions.c.revoked_at.is_(None))
                .values(revoked_at=now(),updated_at=now())).rowcount

    def enroll_totp(self,user_id,password,totp_code=None,session_id=None):
        from app.services.identity import require_factor
        with transaction() as conn:
            require_factor(conn,user_id,password,totp_code,session_id)
            secret=base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
            conn.execute(table('mfa_credentials').insert().values(id=str(uuid4()),created_at=now(),updated_at=now(),user_id=user_id,
                kind='TOTP',credential_key=str(uuid4()),secret_encrypted=_cipher().encrypt(secret.encode()).decode(),sign_count=0))
            from app.core.audit import AppendOnlyAuditStore
            AppendOnlyAuditStore().append_audit_event(actor_id=user_id,action='MFA_TOTP_ENROLLMENT_STARTED',entity_type='user',entity_id=user_id)
        return secret

    def confirm_totp(self,user_id,code):
        credentials=table('mfa_credentials')
        with transaction() as conn:
            conn.execute(select(table('users').c.id).where(table('users').c.id==user_id).with_for_update())
            row=conn.execute(select(credentials).where(credentials.c.user_id==user_id,credentials.c.kind=='TOTP',
                credentials.c.revoked_at.is_(None),credentials.c.verified_at.is_(None),credentials.c.created_at>now()-timedelta(minutes=5)).order_by(credentials.c.created_at.desc())
                .with_for_update()).mappings().first()
            if not row or not verify_totp_code(_cipher().decrypt(row['secret_encrypted'].encode()).decode(),code):
                raise AuthError('TOTP_REQUIRED_OR_INVALID','Invalid enrollment code')
            conn.execute(credentials.update().where(credentials.c.user_id==user_id,credentials.c.kind=='TOTP',credentials.c.verified_at.is_not(None))
                .values(revoked_at=now(),updated_at=now()))
            conn.execute(credentials.update().where(credentials.c.id==row['id']).values(verified_at=now(),updated_at=now()))
            self.rotate_security(conn,user_id)
            from app.core.audit import AppendOnlyAuditStore
            AppendOnlyAuditStore().append_audit_event(actor_id=user_id,action='MFA_TOTP_ENABLED',entity_type='user',entity_id=user_id)

_DUMMY_HASH=hash_password(secrets.token_urlsafe(32))
auth_service=AuthSessionService()
