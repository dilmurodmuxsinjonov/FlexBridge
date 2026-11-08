"""WebAuthn ceremonies verified by py_webauthn, bound to RP/origin/account/version."""
import json
import os
from urllib.parse import urlparse
from uuid import UUID,uuid4
from sqlalchemy import select
from webauthn import (generate_registration_options,generate_authentication_options,
    verify_registration_response,verify_authentication_response)
from webauthn.helpers import options_to_json,bytes_to_base64url,base64url_to_bytes
from webauthn.helpers.structs import (AuthenticatorSelectionCriteria,UserVerificationRequirement,
    ResidentKeyRequirement,PublicKeyCredentialDescriptor,AttestationConveyancePreference)
from webauthn.helpers.exceptions import WebAuthnException
from app.db.storage import table,transaction,now,auth_continuations
from app.core.iam_security import issue_continuation,continuation,rate_limit
from app.services.identity import require_factor,lock_user,audit
from app.services.auth import auth_service,AuthError

def rp_configuration():
    rp=os.environ.get('WEBAUTHN_RP_ID','');origin=os.environ.get('WEBAUTHN_ORIGIN','')
    parsed=urlparse(origin)
    if (not rp or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment
        or not (parsed.hostname==rp or parsed.hostname.endswith('.'+rp))
        or not (parsed.scheme=='https' or (parsed.scheme=='http' and parsed.hostname=='localhost' and rp=='localhost' and os.environ.get('FLEXBRIDGE_ENV')!='production'))):
        raise AuthError('PASSKEY_CONFIGURATION_REQUIRED','Configure the passkey RP and exact origin',503)
    return rp,origin.rstrip('/')

def public_credential_id(value):
    if not isinstance(value,str) or not 1<=len(value)<=2048:raise ValueError('Invalid credential ID')
    return bytes_to_base64url(base64url_to_bytes(value))

def check_body(credential):
    if not isinstance(credential,dict) or len(json.dumps(credential))>65536:raise AuthError('INVALID_PASSKEY_RESPONSE','Invalid credential response',422)

def require_first_party(credential):
    response=credential.get('response')
    if not isinstance(response,dict) or not isinstance(response.get('clientDataJSON'),str):raise ValueError('Invalid client data')
    raw=base64url_to_bytes(response['clientDataJSON'])
    if len(raw)>16384:raise ValueError('Client data is too large')
    data=json.loads(raw)
    if not isinstance(data,dict) or data.get('crossOrigin',False) is not False or data.get('topOrigin'):
        raise ValueError('Cross-origin ceremonies are not supported')

class PasskeyService:
    def registration_options(self,*,actor,password,totp_code=None):
        rate_limit('security-management',actor.user_id,10,600)
        rp,origin=rp_configuration()
        with transaction() as conn:
            user=require_factor(conn,actor.user_id,password,totp_code,actor.session_id)
            t=table('mfa_credentials')
            existing=conn.execute(select(t.c.credential_key).where(t.c.user_id==actor.user_id,t.c.kind=='PASSKEY',t.c.revoked_at.is_(None))).scalars().all()
            options=generate_registration_options(rp_id=rp,rp_name='FlexBridge',user_id=UUID(actor.user_id).bytes,user_name=actor.user_id,
                user_display_name=user['display_name'],attestation=AttestationConveyancePreference.NONE,
                authenticator_selection=AuthenticatorSelectionCriteria(user_verification=UserVerificationRequirement.REQUIRED,resident_key=ResidentKeyRequirement.REQUIRED),
                exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(k.removeprefix('passkey:'))) for k in existing],timeout=300000)
            token=issue_continuation(conn,'PASSKEY_REGISTER',user_id=actor.user_id,payload={'challenge':bytes_to_base64url(options.challenge),
                'rp_id':rp,'origin':origin,'auth_version':user['auth_version']})
            return {'ceremony_token':token,'public_key':json.loads(options_to_json(options)),'expires_in':300}

    def verify_registration(self,*,actor,ceremony_token,credential):
        check_body(credential);error=None;result=None
        with transaction() as conn:
            ceremony=continuation(conn,ceremony_token,'PASSKEY_REGISTER');p=ceremony['payload']
            if ceremony['user_id']!=actor.user_id:raise AuthError('PASSKEY_SCOPE_FORBIDDEN','This ceremony belongs to another account',403)
            user=lock_user(conn,actor.user_id)
            if user['auth_version']!=p['auth_version']:raise AuthError('INVALID_OR_EXPIRED_PROOF','Start a new ceremony')
            try:
                require_first_party(credential)
                verification=verify_registration_response(credential=credential,expected_challenge=base64url_to_bytes(p['challenge']),
                    expected_rp_id=p['rp_id'],expected_origin=p['origin'],require_user_presence=True,require_user_verification=True)
            except (WebAuthnException,ValueError,TypeError,KeyError):
                conn.execute(auth_continuations.update().where(auth_continuations.c.digest==ceremony['digest']).values(attempts=ceremony['attempts']+1))
                error=AuthError('PASSKEY_VERIFICATION_FAILED','The passkey response could not be verified')
            else:
                continuation(conn,ceremony_token,'PASSKEY_REGISTER',consume=True)
                cid=str(uuid4())
                public={'cose':bytes_to_base64url(verification.credential_public_key),
                    'device_type':verification.credential_device_type.value,'backed_up':verification.credential_backed_up}
                conn.execute(table('mfa_credentials').insert().values(id=cid,created_at=now(),updated_at=now(),user_id=actor.user_id,kind='PASSKEY',
                    credential_key='passkey:'+bytes_to_base64url(verification.credential_id),public_key=json.dumps(public),sign_count=verification.sign_count,verified_at=now()))
                auth_service.rotate_security(conn,actor.user_id)
                audit.append_audit_event(actor_id=actor.user_id,action='PASSKEY_REGISTERED',entity_type='mfa_credential',entity_id=cid)
                result={'credential_id':cid,'passkey_enabled':True,'reauthentication_required':True}
        if error:raise error
        return result

    def authentication_options(self,*,ip,mfa_ticket=None):
        rate_limit('passkey-options-ip',ip,30,600);rp,origin=rp_configuration()
        with transaction() as conn:
            user_id=None;version=None;allowed=[]
            if mfa_ticket:
                ticket=continuation(conn,mfa_ticket,'PASSWORD_MFA');user_id=ticket['user_id']
                user=lock_user(conn,user_id)
                if user['auth_version']!=ticket['payload']['auth_version']:raise AuthError('INVALID_OR_EXPIRED_PROOF','Sign in again')
                version=user['auth_version']
                t=table('mfa_credentials')
                keys=conn.execute(select(t.c.credential_key).where(t.c.user_id==user_id,t.c.kind=='PASSKEY',t.c.revoked_at.is_(None),t.c.verified_at.is_not(None))).scalars().all()
                allowed=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(k.removeprefix('passkey:'))) for k in keys]
            options=generate_authentication_options(rp_id=rp,allow_credentials=allowed,user_verification=UserVerificationRequirement.REQUIRED,timeout=300000)
            token=issue_continuation(conn,'PASSKEY_LOGIN',user_id=user_id,payload={'challenge':bytes_to_base64url(options.challenge),
                'rp_id':rp,'origin':origin,'auth_version':version,'mfa_ticket':mfa_ticket})
            return {'ceremony_token':token,'public_key':json.loads(options_to_json(options)),'expires_in':300}

    def verify_authentication(self,*,ceremony_token,credential,ip):
        check_body(credential);rate_limit('passkey-verify-ip',ip,30,600);error=None;result=None
        with transaction() as conn:
            ceremony=continuation(conn,ceremony_token,'PASSKEY_LOGIN');p=ceremony['payload'];t=table('mfa_credentials')
            if p.get('mfa_ticket'):continuation(conn,p['mfa_ticket'],'PASSWORD_MFA')
            try:key='passkey:'+public_credential_id(credential.get('id'))
            except (ValueError,TypeError):key='invalid'
            initial=conn.execute(select(t).where(t.c.credential_key==key,t.c.kind=='PASSKEY',t.c.revoked_at.is_(None),t.c.verified_at.is_not(None))).mappings().first()
            user=lock_user(conn,initial['user_id']) if initial else None
            saved=conn.execute(select(t).where(t.c.id==initial['id'],t.c.revoked_at.is_(None)).with_for_update()).mappings().first() if initial else None
            try:
                require_first_party(credential)
                if not saved or not user or user['status']!='ACTIVE':raise ValueError('Invalid credential')
                if ceremony['user_id'] and (user['id']!=ceremony['user_id'] or user['auth_version']!=p['auth_version']):raise ValueError('Stale account binding')
                handle=credential.get('response',{}).get('userHandle')
                if (not ceremony['user_id'] and not handle) or (handle and base64url_to_bytes(handle)!=UUID(user['id']).bytes):raise ValueError('Invalid user handle')
                public=json.loads(saved['public_key'])
                verification=verify_authentication_response(credential=credential,expected_challenge=base64url_to_bytes(p['challenge']),
                    expected_rp_id=p['rp_id'],expected_origin=p['origin'],credential_public_key=base64url_to_bytes(public['cose']),
                    credential_current_sign_count=saved['sign_count'],require_user_verification=True)
            except (WebAuthnException,ValueError,TypeError,KeyError):
                conn.execute(auth_continuations.update().where(auth_continuations.c.digest==ceremony['digest']).values(attempts=ceremony['attempts']+1))
                error=AuthError('PASSKEY_VERIFICATION_FAILED','The passkey response could not be verified')
            else:
                continuation(conn,ceremony_token,'PASSKEY_LOGIN',consume=True)
                if p.get('mfa_ticket'):continuation(conn,p['mfa_ticket'],'PASSWORD_MFA',consume=True)
                public.update(device_type=verification.credential_device_type.value,backed_up=verification.credential_backed_up)
                conn.execute(t.update().where(t.c.id==saved['id']).values(sign_count=verification.new_sign_count,public_key=json.dumps(public),updated_at=now()))
                result=auth_service.issue_session(conn,user['id'],assurance='MFA')
        if error:raise error
        return result

    def revoke(self,*,actor,credential_id,password,totp_code=None):
        rate_limit('security-management',actor.user_id,10,600)
        with transaction() as conn:
            require_factor(conn,actor.user_id,password,totp_code,actor.session_id)
            t=table('mfa_credentials')
            credential=conn.execute(select(t).where(t.c.id==credential_id,t.c.user_id==actor.user_id,t.c.kind=='PASSKEY').with_for_update()).mappings().first()
            if not credential:raise AuthError('PASSKEY_NOT_FOUND','Passkey not found',404)
            conn.execute(t.update().where(t.c.id==credential_id).values(revoked_at=now(),updated_at=now()))
            auth_service.rotate_security(conn,actor.user_id)
            audit.append_audit_event(actor_id=actor.user_id,action='PASSKEY_REVOKED',entity_type='mfa_credential',entity_id=credential_id)
            return {'status':'REVOKED','reauthentication_required':True}

passkey_service=PasskeyService()
