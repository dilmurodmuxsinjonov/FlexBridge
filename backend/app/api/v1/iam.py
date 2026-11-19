"""IAM challenge, recovery and WebAuthn contracts. Secrets never enter URL parameters."""
import hmac
import os
from typing import Literal,Any
from uuid import UUID
from fastapi import APIRouter,Depends,Header,Request
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from app.api.dependencies import ActorContext,require_actor_context
from app.db.storage import table,transaction
from app.services.auth import AuthError
from app.services.identity import identity_service
from app.services.passkeys import passkey_service

router=APIRouter(prefix='/api/v1',tags=['identity'])

class Input(BaseModel):model_config=ConfigDict(extra='forbid')
class ChallengeInput(Input):
    channel:Literal['PHONE','EMAIL']
    destination:str=Field(min_length=3,max_length=254)
    purpose:Literal['REGISTER','LOGIN','RECOVERY','CONTACT']
    delivery_method:Literal['SMS','TELEGRAM','EMAIL']|None=None
class TelegramWebhookInput(BaseModel):
    model_config=ConfigDict(extra='allow')
    update_id:int|None=None
    message:dict[str,Any]|None=None
    update:dict[str,Any]|None=None
    challenge_id:UUID|None=None
class ResendInput(Input):purpose:Literal['REGISTER','LOGIN','RECOVERY','CONTACT']
class ConsumeInput(ResendInput):code:str=Field(pattern=r'^[0-9]{6}$')
class MFAInput(Input):
    mfa_ticket:str=Field(min_length=32,max_length=128)
    code:str=Field(pattern=r'^[0-9]{6}$')
class StepUpInput(Input):
    current_password:str=Field(min_length=1,max_length=1024)
    totp_code:str|None=Field(default=None,pattern=r'^[0-9]{6}$')
class ProfileUpdateInput(Input):
    display_name:str=Field(min_length=2,max_length=200)
class ChangePasswordInput(StepUpInput):
    new_password:str=Field(min_length=12,max_length=1024)
class ContactInput(StepUpInput):verification_token:str=Field(min_length=32,max_length=128)
class RecoveryInput(Input):
    verification_token:str=Field(min_length=32,max_length=128)
    recovery_code:str|None=Field(default=None,min_length=20,max_length=128)
    totp_code:str|None=Field(default=None,pattern=r'^[0-9]{6}$')
class RecoveryCompleteInput(Input):
    reset_token:str=Field(min_length=32,max_length=128)
    new_password:str=Field(min_length=12,max_length=1024)
class PasskeyOptionsInput(Input):mfa_ticket:str|None=Field(default=None,min_length=32,max_length=128)
class PasskeyVerifyInput(Input):
    ceremony_token:str=Field(min_length=32,max_length=128)
    credential:dict[str,Any]

def ip(request):return request.client.host if request.client else 'unknown'

@router.get('/auth/options')
def options():
    from app.services.telegram_bot import get_bot_username, telegram_mode
    mode=telegram_mode()
    return {'channels':['PHONE','EMAIL'],'delivery_methods':['SMS','TELEGRAM'] if mode!='DISABLED' else ['SMS'],
        'telegram_mode':mode,
        'telegram_bot_username':get_bot_username(),'otp_expires_in':300,'otp_max_attempts':5,'resend_after':60,
        'terms_version':os.environ.get('TERMS_POLICY_VERSION'),'privacy_version':os.environ.get('PRIVACY_POLICY_VERSION')}

@router.post('/auth/challenges',status_code=202)
def challenge(payload:ChallengeInput,request:Request,authorization:str|None=Header(default=None)):
    actor=require_actor_context(authorization) if payload.purpose=='CONTACT' else None
    return identity_service.issue_challenge(**payload.model_dump(),ip=ip(request),bound_user=actor.user_id if actor else None)

@router.get('/auth/challenges/{id}/status')
def challenge_status(id:UUID,request:Request):
    return identity_service.challenge_status(challenge_id=str(id),ip=ip(request))

@router.post('/auth/telegram/webhook')
def telegram_webhook(payload:TelegramWebhookInput,request:Request,
        x_telegram_bot_api_secret_token:str|None=Header(default=None)):
    """Telegram Bot API webhook.

    LIVE: only Telegram may call it (setWebhook secret_token checked in constant
    time); the OTP is sent to the user's chat and never returned; errors answer
    200 so Telegram does not retry (the bot already told the user what to do).
    SIMULATION (local staging tests only): legacy unauthenticated echo.
    """
    from app.services.telegram_bot import public_result, telegram_bot_service, telegram_mode
    mode=telegram_mode()
    if mode=='DISABLED':
        raise AuthError('TELEGRAM_DISABLED','Telegram verification is not configured',503)
    raw_update=payload.update if isinstance(payload.update,dict) else payload.model_dump(exclude={'update','challenge_id'},exclude_none=True)
    if mode=='SIMULATION':
        return telegram_bot_service.handle_update(update=raw_update,ip=ip(request),
            explicit_challenge_id=str(payload.challenge_id) if payload.challenge_id else None)
    secret=os.environ.get('TELEGRAM_WEBHOOK_SECRET','')
    if not secret:
        raise AuthError('TELEGRAM_WEBHOOK_NOT_CONFIGURED','Set TELEGRAM_WEBHOOK_SECRET or use the polling worker',503)
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(x_telegram_bot_api_secret_token,secret):
        raise AuthError('TELEGRAM_WEBHOOK_FORBIDDEN','Invalid Telegram webhook secret',403)
    sender=((raw_update.get('message') or {}).get('from') or {}).get('id')
    try:
        result=telegram_bot_service.handle_update(update=raw_update,ip=f'tg:{sender}' if sender else ip(request))
    except AuthError as exc:
        return {'ok':False,'code':exc.code}
    return public_result(result)

@router.post('/auth/challenges/{id}/resend',status_code=202)
def resend(id:UUID,payload:ResendInput,request:Request,authorization:str|None=Header(default=None)):
    actor=require_actor_context(authorization) if payload.purpose=='CONTACT' else None
    return identity_service.resend(challenge_id=str(id),purpose=payload.purpose,ip=ip(request),bound_user=actor.user_id if actor else None)

@router.post('/auth/challenges/{id}/consume')
def consume(id:UUID,payload:ConsumeInput,request:Request):
    return identity_service.consume(challenge_id=str(id),**payload.model_dump(),ip=ip(request))

@router.post('/auth/mfa/verify')
def verify_mfa(payload:MFAInput,request:Request):
    return identity_service.verify_mfa(**payload.model_dump(),ip=ip(request))

@router.get('/me/contacts')
def list_contacts(actor:ActorContext=Depends(require_actor_context)):
    contacts=table('user_contacts')
    with transaction() as conn:
        rows=conn.execute(select(contacts.c.id,contacts.c.channel,contacts.c.normalized_value,contacts.c.is_primary,contacts.c.verified_at)
            .where(contacts.c.user_id==actor.user_id,contacts.c.verified_at.is_not(None),contacts.c.revoked_at.is_(None))
            .order_by(contacts.c.is_primary.desc(),contacts.c.created_at.desc())).mappings().all()
        items=[]
        for r in rows:
            val=str(r['normalized_value'] or '')
            if '@' in val:
                local,domain=val.split('@',1)
                masked=(local[:2]+'***@'+domain) if len(local)>2 else ('***@'+domain)
            elif len(val)>=7:
                masked=val[:6]+'***'+val[-4:]
            else:
                masked='***'
            items.append({'id':str(r['id']),'channel':r['channel'],'masked_destination':masked,'is_primary':bool(r['is_primary']),'verified_at':r['verified_at']})
        return {'items':items}

@router.patch('/me/profile')
def update_profile(payload:ProfileUpdateInput,actor:ActorContext=Depends(require_actor_context)):
    return identity_service.update_profile(actor=actor,display_name=payload.display_name)

@router.post('/me/security/password')
def change_password(payload:ChangePasswordInput,actor:ActorContext=Depends(require_actor_context)):
    return identity_service.change_password(
        actor=actor,
        current_password=payload.current_password,
        new_password=payload.new_password,
        totp_code=payload.totp_code,
    )

@router.post('/me/contacts',status_code=201)
def bind_contact(payload:ContactInput,actor:ActorContext=Depends(require_actor_context)):
    return identity_service.bind_contact(actor=actor,verification_token=payload.verification_token,password=payload.current_password,totp_code=payload.totp_code)

@router.patch('/me/contacts/{id}/primary')
def set_primary_contact(id:UUID,payload:StepUpInput,actor:ActorContext=Depends(require_actor_context)):
    return identity_service.set_primary_contact(actor=actor,contact_id=str(id),password=payload.current_password,totp_code=payload.totp_code)

@router.delete('/me/contacts/{id}')
def remove_contact(id:UUID,payload:StepUpInput,actor:ActorContext=Depends(require_actor_context)):
    return identity_service.remove_contact(actor=actor,contact_id=str(id),password=payload.current_password,totp_code=payload.totp_code)

@router.post('/me/security/recovery-codes')
def recovery_codes(payload:StepUpInput,actor:ActorContext=Depends(require_actor_context)):
    return identity_service.recovery_codes(actor=actor,password=payload.current_password,totp_code=payload.totp_code)

@router.post('/auth/recovery',status_code=202)
def recovery(payload:RecoveryInput,request:Request):
    return identity_service.request_recovery(**payload.model_dump(),ip=ip(request))

@router.get('/auth/recovery/{id}')
def recovery_status(id:UUID,x_recovery_token:str=Header(min_length=32,max_length=128)):
    return identity_service.recovery_status(request_id=str(id),recovery_token=x_recovery_token)

@router.post('/auth/recovery/{id}/complete')
def recovery_complete(id:UUID,payload:RecoveryCompleteInput,request:Request):
    return identity_service.complete_recovery(request_id=str(id),**payload.model_dump(),ip=ip(request))

@router.post('/me/security/passkeys/options')
def passkey_registration_options(payload:StepUpInput,actor:ActorContext=Depends(require_actor_context)):
    return passkey_service.registration_options(actor=actor,password=payload.current_password,totp_code=payload.totp_code)

@router.post('/me/security/passkeys/verify',status_code=201)
def passkey_registration_verify(payload:PasskeyVerifyInput,actor:ActorContext=Depends(require_actor_context)):
    return passkey_service.verify_registration(actor=actor,**payload.model_dump())

@router.post('/auth/passkeys/options')
def passkey_authentication_options(payload:PasskeyOptionsInput,request:Request):
    return passkey_service.authentication_options(**payload.model_dump(),ip=ip(request))

@router.post('/auth/passkeys/verify')
def passkey_authentication_verify(payload:PasskeyVerifyInput,request:Request):
    return passkey_service.verify_authentication(**payload.model_dump(),ip=ip(request))

@router.delete('/me/security/passkeys/{id}')
def passkey_revoke(id:UUID,payload:StepUpInput,actor:ActorContext=Depends(require_actor_context)):
    return passkey_service.revoke(actor=actor,credential_id=str(id),password=payload.current_password,totp_code=payload.totp_code)
