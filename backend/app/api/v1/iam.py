"""IAM challenge, recovery and WebAuthn contracts. Secrets never enter URL parameters."""
import os
from typing import Literal,Any
from uuid import UUID
from fastapi import APIRouter,Depends,Header,Request
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import ActorContext,require_actor_context
from app.services.identity import identity_service
from app.services.passkeys import passkey_service

router=APIRouter(prefix='/api/v1',tags=['identity'])

class Input(BaseModel):model_config=ConfigDict(extra='forbid')
class ChallengeInput(Input):
    channel:Literal['PHONE','EMAIL']
    destination:str=Field(min_length=3,max_length=254)
    purpose:Literal['REGISTER','LOGIN','RECOVERY','CONTACT']
class ResendInput(Input):purpose:Literal['REGISTER','LOGIN','RECOVERY','CONTACT']
class ConsumeInput(ResendInput):code:str=Field(pattern=r'^[0-9]{6}$')
class MFAInput(Input):
    mfa_ticket:str=Field(min_length=32,max_length=128)
    code:str=Field(pattern=r'^[0-9]{6}$')
class StepUpInput(Input):
    current_password:str=Field(min_length=1,max_length=1024)
    totp_code:str|None=Field(default=None,pattern=r'^[0-9]{6}$')
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
    return {'channels':['PHONE','EMAIL'],'otp_expires_in':300,'otp_max_attempts':5,'resend_after':60,
        'terms_version':os.environ.get('TERMS_POLICY_VERSION'),'privacy_version':os.environ.get('PRIVACY_POLICY_VERSION')}

@router.post('/auth/challenges',status_code=202)
def challenge(payload:ChallengeInput,request:Request,authorization:str|None=Header(default=None)):
    actor=require_actor_context(authorization) if payload.purpose=='CONTACT' else None
    return identity_service.issue_challenge(**payload.model_dump(),ip=ip(request),bound_user=actor.user_id if actor else None)

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

@router.post('/me/contacts',status_code=201)
def bind_contact(payload:ContactInput,actor:ActorContext=Depends(require_actor_context)):
    return identity_service.bind_contact(actor=actor,verification_token=payload.verification_token,password=payload.current_password,totp_code=payload.totp_code)

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
