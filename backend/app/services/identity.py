"""Contact verification is separate from account ownership and session authority."""
from datetime import timedelta
import hmac
import os
import secrets
from uuid import uuid4
from sqlalchemy import select,text,exists
from app.db.storage import table,transaction,now,enqueue,auth_continuations,auth_rate_limits
from app.core.iam_security import (digest,encrypt,decrypt,normalize_contact,rate_limit,
    issue_continuation,continuation,SENSITIVE_ROLES)
from app.core.audit import AppendOnlyAuditStore
from app.services.auth import auth_service,AuthError,verify_totp_code,hash_password,verify_password
from app.adapters.identity_delivery import configuration

audit=AppendOnlyAuditStore()

def lock_contact(conn,value):
    conn.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':digest('contact-lock',value)})

def lock_user(conn,user_id):
    return conn.execute(select(table('users')).where(table('users').c.id==user_id).with_for_update()).mappings().first()

def contact_row(conn,channel,value):
    t=table('user_contacts')
    return conn.execute(select(t).where(t.c.channel==channel,t.c.normalized_value==value,t.c.verified_at.is_not(None),t.c.revoked_at.is_(None))).mappings().first()

def require_factor(conn,user,password,totp_code=None,session_id=None):
    user=auth_service.check_password(conn,user,password)
    if user['totp_secret'] or user['has_passkey']:
        s=table('sessions')
        recent=conn.execute(select(s.c.id).where(s.c.id==session_id,s.c.user_id==user['id'],s.c.assurance=='MFA',s.c.revoked_at.is_(None),
            s.c.auth_version==user['auth_version'],s.c.created_at>now()-timedelta(minutes=5),s.c.expires_at>now())).first() if session_id else None
        code_valid=bool(user['totp_secret'] and verify_totp_code(user['totp_secret'],totp_code))
        if not recent and not code_valid:raise AuthError('STEP_UP_VERIFICATION_FAILED','A current MFA code or recent MFA login is required')
    return user

class IdentityService:
    def issue_challenge(self,*,channel,destination,purpose,ip,bound_user=None):
        if purpose not in ('REGISTER','LOGIN','RECOVERY','CONTACT'):raise AuthError('INVALID_PURPOSE','Invalid verification purpose',422)
        if purpose=='CONTACT' and not bound_user:raise AuthError('AUTH_REQUIRED','Sign in to verify a new contact')
        value=normalize_contact(channel,destination)
        configuration();digest('configuration','check');encrypt({})
        rate_limit('otp-ip',ip,20,600);rate_limit('otp-target',channel+':'+value,5,600)
        with transaction() as conn:
            lock_contact(conn,channel+':'+value)
            return self._issue(conn,channel,value,purpose,bound_user)

    def _issue(self,conn,channel,value,purpose,bound_user=None):
        t=table('auth_challenges');dest_digest=digest('destination',channel+':'+value)
        old=conn.execute(select(t).where(t.c.destination_digest==dest_digest,t.c.purpose==purpose).order_by(t.c.created_at.desc()).limit(1)).mappings().first()
        if old and old['created_at']+timedelta(seconds=60)>now():raise AuthError('RESEND_COOLDOWN','Wait before requesting another code',429)
        conn.execute(t.update().where(t.c.destination_digest==dest_digest,t.c.purpose==purpose,t.c.consumed_at.is_(None),t.c.superseded_at.is_(None))
            .values(superseded_at=now(),delivery_status='SUPERSEDED',delivery_encrypted=None))
        contact=contact_row(conn,channel,value) if purpose in ('LOGIN','RECOVERY') else None
        challenge_id=str(uuid4());code=f'{secrets.randbelow(1000000):06d}'
        conn.execute(t.insert().values(id=challenge_id,created_at=now(),updated_at=now(),channel=channel,purpose=purpose,
            user_id=bound_user if purpose=='CONTACT' else (contact['user_id'] if contact else None),contact_id=contact['id'] if contact else None,
            destination_digest=dest_digest,code_hmac=digest('otp',challenge_id+':'+purpose+':'+code),
            expires_at=now()+timedelta(minutes=5),attempts=0,destination_encrypted=encrypt({'value':value}),
            delivery_encrypted=encrypt({'code':code}),delivery_status='PENDING'))
        enqueue(conn,'AUTH_OTP_DELIVERY',challenge_id,{'challenge_id':challenge_id},'otp:'+challenge_id)
        return {'challenge_id':challenge_id,'status':'QUEUED','expires_in':300,'resend_after':60}

    def resend(self,*,challenge_id,purpose,ip,bound_user=None):
        # A public UUID alone cannot reveal the destination; all replies omit contact/account details.
        t=table('auth_challenges')
        with transaction() as conn:
            row=conn.execute(select(t).where(t.c.id==challenge_id)).mappings().first()
        if not row or row['purpose']!=purpose:raise AuthError('INVALID_OR_EXPIRED_PROOF','Verification is required')
        if purpose=='CONTACT' and row['user_id']!=bound_user:raise AuthError('AUTH_REQUIRED','Sign in to verify a new contact')
        value=decrypt(row['destination_encrypted'])['value']
        return self.issue_challenge(channel=row['channel'],destination=value,purpose=purpose,ip=ip,bound_user=bound_user)

    def consume(self,*,challenge_id,purpose,code,ip):
        rate_limit('otp-verify-ip',ip,40,600)
        error=None;result=None;t=table('auth_challenges')
        with transaction() as conn:
            row=conn.execute(select(t).where(t.c.id==challenge_id).with_for_update()).mappings().first()
            if (not row or row['purpose']!=purpose or row['expires_at']<=now() or row['consumed_at'] or row['superseded_at'] or row['attempts']>=5
                or row['delivery_status']!='SENT'):
                error=AuthError('INVALID_OR_EXPIRED_CODE','Verification code is invalid or expired')
            elif not hmac.compare_digest(row['code_hmac'],digest('otp',challenge_id+':'+purpose+':'+code)):
                conn.execute(t.update().where(t.c.id==challenge_id).values(attempts=row['attempts']+1,updated_at=now()))
                error=AuthError('INVALID_OR_EXPIRED_CODE','Verification code is invalid or expired')
            else:
                value=decrypt(row['destination_encrypted'])['value']
                token=issue_continuation(conn,'CONTACT_'+purpose,user_id=row['user_id'],challenge_id=challenge_id,
                    payload={'channel':row['channel'],'value':value,'contact_id':row['contact_id']})
                conn.execute(t.update().where(t.c.id==challenge_id).values(consumed_at=now(),delivery_status='CONSUMED',delivery_encrypted=None,updated_at=now()))
                result={'verification_token':token,'purpose':purpose,'expires_in':300}
        if error:raise error
        return result

    def _bind_contact(self,conn,*,user_id,channel,value):
        lock_contact(conn,channel+':'+value)
        old=contact_row(conn,channel,value)
        if old and old['user_id']==user_id:return old['id']
        if old:
            # Never move a contact row (and its account history) to another person.
            conn.execute(table('user_contacts').update().where(table('user_contacts').c.id==old['id']).values(
                normalized_value='released:'+str(uuid4()),revoked_at=now(),is_primary=False,updated_at=now()))
            auth_service.rotate_security(conn,old['user_id'])
            audit.append_audit_event(actor_id=user_id,action='CONTACT_REBOUND_TO_NEW_ACCOUNT',entity_type='contact',entity_id=old['id'],
                metadata={'previous_user_id':old['user_id'],'destination_digest':digest('destination',channel+':'+value)})
        cid=str(uuid4())
        conn.execute(table('user_contacts').insert().values(id=cid,created_at=now(),updated_at=now(),user_id=user_id,channel=channel,
            normalized_value=value,verified_at=now(),is_primary=True))
        return cid

    def register(self,*,verification_token,display_name,password,adult_confirmed,terms_version,privacy_version,roles=None,enable_totp=False):
        if set(roles or ['CANDIDATE'])!={'CANDIDATE'}:raise AuthError('FORBIDDEN_PRIVILEGED_ROLE_REGISTRATION','Public signup creates only a candidate',403)
        if not verification_token:raise AuthError('CONTACT_VERIFICATION_REQUIRED','Verify your contact before registration',422)
        expected_terms=os.environ.get('TERMS_POLICY_VERSION');expected_privacy=os.environ.get('PRIVACY_POLICY_VERSION')
        if not expected_terms or not expected_privacy:raise AuthError('POLICY_CONFIGURATION_REQUIRED','Published policy versions must be configured',503)
        if terms_version!=expected_terms or privacy_version!=expected_privacy:raise AuthError('POLICY_ACCEPTANCE_REQUIRED','Accept the current policy versions',422)
        with transaction() as conn:
            proof=continuation(conn,verification_token,'CONTACT_REGISTER',consume=True)
            user=auth_service.register_user(display_name=display_name,password=password,adult_confirmed=adult_confirmed,roles=roles,enable_totp=enable_totp)
            self._bind_contact(conn,user_id=user['id'],channel=proof['payload']['channel'],value=proof['payload']['value'])
            for purpose,version in [('TERMS',terms_version),('PRIVACY',privacy_version)]:
                audit.append_consent_event(user_id=user['id'],consent_type=purpose,policy_version=version,granted=True)
            audit.append_audit_event(actor_id=user['id'],action='ACCOUNT_REGISTERED',entity_type='user',entity_id=user['id'])
            return {k:user[k] for k in ('id','display_name','roles','adult_declared_at')}

    def resolve_user(self,conn,*,user_id=None,channel=None,destination=None):
        if user_id:return str(user_id)
        if not channel or not destination:raise AuthError('LOGIN_IDENTIFIER_REQUIRED','Supply user_id or contact',422)
        value=normalize_contact(channel,destination);contact=contact_row(conn,channel,value)
        return contact['user_id'] if contact else str(uuid4())

    def begin_login(self,*,password,ip,user_id=None,channel=None,destination=None,totp_code=None,verification_token=None):
        rate_limit('login-ip',ip,30,600)
        if verification_token:
            with transaction() as conn:
                p=continuation(conn,verification_token,'CONTACT_LOGIN')['payload']
                identifier=p['channel']+':'+p['value']
        else:
            identifier=str(user_id) if user_id else str(channel)+':'+normalize_contact(channel,destination or '')
        rate_limit('login-identifier',identifier,10,600)
        with transaction() as conn:
            if verification_token:
                proof=continuation(conn,verification_token,'CONTACT_LOGIN',consume=True)
                p=proof['payload'];contact=contact_row(conn,p['channel'],p['value'])
                if not contact or contact['id']!=p['contact_id'] or contact['user_id']!=proof['user_id']:
                    raise AuthError('INVALID_CREDENTIALS','Invalid credentials')
                uid=contact['user_id']
            else:uid=self.resolve_user(conn,user_id=user_id,channel=channel,destination=destination)
            user=auth_service.check_password(conn,uid,password)
            if (user['totp_secret'] or user['has_passkey']) and not totp_code:
                token=issue_continuation(conn,'PASSWORD_MFA',user_id=uid,payload={'auth_version':user['auth_version']})
                return {'mfa_required':True,'mfa_ticket':token,'expires_in':300}
            if user['totp_secret']:
                if not verify_totp_code(user['totp_secret'],totp_code):raise AuthError('INVALID_CREDENTIALS','Invalid credentials')
                assurance='MFA'
            elif user['has_passkey']:
                raise AuthError('MFA_REQUIRED','Verify a registered passkey')
            else:assurance='PASSWORD'
            result=auth_service.issue_session(conn,uid,assurance=assurance)
            if set(user['roles']) & SENSITIVE_ROLES and assurance!='MFA':result['mfa_enrollment_required']=True
            return result

    def verify_mfa(self,*,mfa_ticket,code,ip):
        rate_limit('mfa-ip',ip,30,600);error=None;result=None
        with transaction() as conn:
            ticket=continuation(conn,mfa_ticket,'PASSWORD_MFA')
            user=lock_user(conn,ticket['user_id'])
            if not user or user['auth_version']!=ticket['payload']['auth_version']:raise AuthError('INVALID_OR_EXPIRED_PROOF','Sign in again')
            loaded=auth_service._load_user(user['id'])
            if not loaded['totp_secret'] or not verify_totp_code(loaded['totp_secret'],code):
                conn.execute(auth_continuations.update().where(auth_continuations.c.digest==ticket['digest']).values(attempts=ticket['attempts']+1))
                error=AuthError('INVALID_MFA_CODE','MFA verification failed')
            else:
                continuation(conn,mfa_ticket,'PASSWORD_MFA',consume=True)
                result=auth_service.issue_session(conn,user['id'],assurance='MFA')
        if error:raise error
        return result

    def bind_contact(self,*,actor,verification_token,password,totp_code=None):
        rate_limit('security-management',actor.user_id,10,600)
        with transaction() as conn:
            require_factor(conn,actor.user_id,password,totp_code,actor.session_id)
            proof=continuation(conn,verification_token,'CONTACT_CONTACT',consume=True)
            if proof['user_id']!=actor.user_id:raise AuthError('CONTACT_SCOPE_FORBIDDEN','Verify this contact for your own account',403)
            cid=self._bind_contact(conn,user_id=actor.user_id,channel=proof['payload']['channel'],value=proof['payload']['value'])
            audit.append_audit_event(actor_id=actor.user_id,action='CONTACT_VERIFIED',entity_type='contact',entity_id=cid)
            return {'contact_id':cid,'verified':True}

    def recovery_codes(self,*,actor,password,totp_code=None):
        rate_limit('security-management',actor.user_id,10,600)
        with transaction() as conn:
            user=require_factor(conn,actor.user_id,password,totp_code,actor.session_id)
            if not user['totp_secret'] and not user['has_passkey']:raise AuthError('MFA_ENROLLMENT_REQUIRED','Enable MFA before issuing recovery codes',403)
            t=table('mfa_credentials')
            conn.execute(t.update().where(t.c.user_id==actor.user_id,t.c.kind=='RECOVERY_CODE',t.c.revoked_at.is_(None)).values(revoked_at=now()))
            codes=[secrets.token_urlsafe(24) for _ in range(8)]
            for code in codes:
                conn.execute(t.insert().values(id=str(uuid4()),created_at=now(),updated_at=now(),user_id=actor.user_id,kind='RECOVERY_CODE',
                    credential_key=str(uuid4()),secret_encrypted=digest('recovery-code',code),sign_count=0,verified_at=now()))
            audit.append_audit_event(actor_id=actor.user_id,action='RECOVERY_CODES_ROTATED',entity_type='user',entity_id=actor.user_id)
            return {'recovery_codes':codes,'show_once':True}

    def request_recovery(self,*,verification_token,ip,recovery_code=None,totp_code=None):
        rate_limit('recovery-ip',ip,15,1800)
        with transaction() as conn:
            proof=continuation(conn,verification_token,'CONTACT_RECOVERY',consume=True)
            p=proof['payload'];contact=contact_row(conn,p['channel'],p['value'])
            uid=proof['user_id'] if contact and contact['id']==p['contact_id'] and contact['user_id']==proof['user_id'] else None
            user=lock_user(conn,uid) if uid else None
            trusted=False
            if user and user['status']=='ACTIVE':
                if recovery_code:
                    t=table('mfa_credentials')
                    credential=conn.execute(select(t).where(t.c.user_id==uid,t.c.kind=='RECOVERY_CODE',t.c.secret_encrypted==digest('recovery-code',recovery_code),
                        t.c.verified_at.is_not(None),t.c.revoked_at.is_(None)).with_for_update()).mappings().first()
                    if credential:
                        trusted=True;conn.execute(t.update().where(t.c.id==credential['id']).values(revoked_at=now(),updated_at=now()))
                elif totp_code:
                    loaded=auth_service._load_user(uid)
                    trusted=bool(loaded['totp_secret'] and verify_totp_code(loaded['totp_secret'],totp_code))
            rid=str(uuid4());status='READY_TO_RESET' if trusted else 'PENDING_REVIEW'
            conn.execute(table('recovery_requests').insert().values(id=rid,created_at=now(),updated_at=now(),user_id=uid,kind='ACCOUNT_ACCESS',status=status,
                requester_contact_digest=digest('destination',p['channel']+':'+p['value'])))
            payload={'request_id':rid,'contact_id':p['contact_id'],'auth_version':user['auth_version'] if user else None}
            status_token=issue_continuation(conn,'RECOVERY_STATUS',user_id=uid,payload=payload,ttl=1800)
            result={'recovery_id':rid,'recovery_token':status_token,'status':status,'expires_in':1800}
            if trusted:result['reset_token']=issue_continuation(conn,'RECOVERY_RESET',user_id=uid,payload=payload,ttl=300)
            return result

    def recovery_status(self,*,request_id,recovery_token):
        with transaction() as conn:
            proof=continuation(conn,recovery_token,'RECOVERY_STATUS')
            if proof['payload']['request_id']!=request_id:raise AuthError('INVALID_OR_EXPIRED_PROOF','Verification is required')
            row=conn.execute(select(table('recovery_requests')).where(table('recovery_requests').c.id==request_id)).mappings().one()
            if row['kind']!='ACCOUNT_ACCESS':raise AuthError('INVALID_OR_EXPIRED_PROOF','Verification is required')
            return {'recovery_id':request_id,'status':row['status']}

    def complete_recovery(self,*,request_id,reset_token,new_password,ip):
        rate_limit('recovery-complete-ip',ip,15,600)
        with transaction() as conn:
            proof=continuation(conn,reset_token,'RECOVERY_RESET',consume=True)
            if proof['payload']['request_id']!=request_id:raise AuthError('INVALID_OR_EXPIRED_PROOF','Verification is required')
            user=lock_user(conn,proof['user_id']);p=proof['payload']
            contact=conn.execute(select(table('user_contacts')).where(table('user_contacts').c.id==p['contact_id'],table('user_contacts').c.user_id==proof['user_id'],
                table('user_contacts').c.revoked_at.is_(None))).mappings().first()
            if not user or user['status']!='ACTIVE' or user['auth_version']!=p['auth_version'] or not contact:raise AuthError('INVALID_OR_EXPIRED_PROOF','Verification is required')
            t=table('recovery_requests')
            request=conn.execute(select(t).where(t.c.id==request_id).with_for_update()).mappings().one()
            if request['kind']!='ACCOUNT_ACCESS' or request['status']!='READY_TO_RESET':raise AuthError('INVALID_OR_EXPIRED_PROOF','Verification is required')
            conn.execute(table('users').update().where(table('users').c.id==user['id']).values(password_hash=hash_password(new_password),updated_at=now()))
            auth_service.rotate_security(conn,user['id'])
            # Recovery can replace a lost authenticator. Old factors and backup codes cannot survive it.
            conn.execute(table('mfa_credentials').update().where(table('mfa_credentials').c.user_id==user['id'])
                .values(revoked_at=now(),updated_at=now()))
            conn.execute(t.update().where(t.c.id==request_id).values(status='COMPLETED',resolved_at=now(),updated_at=now()))
            audit.append_audit_event(actor_id=user['id'],action='ACCOUNT_PASSWORD_RECOVERED',entity_type='user',entity_id=user['id'])
            return {'status':'COMPLETED','reauthentication_required':True}

    def expire_state(self,batch_size=1000):
        """Bounded primary-DB cleanup; backup/WAL retention is a separate infrastructure policy."""
        challenges=table('auth_challenges');cutoff=now()-timedelta(days=1)
        with transaction() as conn:
            expired=select(challenges.c.id).where(challenges.c.expires_at<=now(),challenges.c.delivery_status.in_(['PENDING','SENT']))\
                .order_by(challenges.c.expires_at).limit(batch_size).with_for_update(skip_locked=True)
            conn.execute(challenges.update().where(challenges.c.id.in_(expired)).values(delivery_encrypted=None,delivery_status='EXPIRED',updated_at=now()))
            old_tokens=select(auth_continuations.c.digest).where(auth_continuations.c.created_at<cutoff,auth_continuations.c.expires_at<=now())\
                .limit(batch_size).with_for_update(skip_locked=True)
            conn.execute(auth_continuations.delete().where(auth_continuations.c.digest.in_(old_tokens)))
            old_challenges=select(challenges.c.id).where(challenges.c.created_at<cutoff,challenges.c.expires_at<=now(),
                ~exists(select(auth_continuations.c.digest).where(auth_continuations.c.challenge_id==challenges.c.id)))\
                .order_by(challenges.c.created_at).limit(batch_size).with_for_update(skip_locked=True)
            conn.execute(challenges.delete().where(challenges.c.id.in_(old_challenges)))
            old_rates=select(auth_rate_limits.c.bucket_key).where(auth_rate_limits.c.window_started_at<cutoff).limit(batch_size).with_for_update(skip_locked=True)
            conn.execute(auth_rate_limits.delete().where(auth_rate_limits.c.bucket_key.in_(old_rates)))

identity_service=IdentityService()
