from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request as HTTPRequest
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from app.api.dependencies import ActorContext, require_actor_context
from app.services.auth import AuthError, auth_service, verify_password, generate_totp_code
from app.db.storage import table, transaction, now
import hmac

router=APIRouter(prefix='/api/v1',tags=['auth'])
class Request(BaseModel):
    model_config=ConfigDict(extra='forbid')
class RegisterRequest(Request):
    display_name:str=Field(min_length=2,max_length=200)
    password:str=Field(min_length=12,max_length=1024)
    adult_confirmed:bool
    roles:list[str]=Field(default_factory=lambda:['CANDIDATE'])
    enable_totp:bool=False
    verification_token:str|None=Field(default=None,max_length=128)
    terms_version:str|None=Field(default=None,max_length=64)
    privacy_version:str|None=Field(default=None,max_length=64)
class LoginRequest(Request):
    user_id:UUID|None=None
    channel:str|None=None
    destination:str|None=Field(default=None,max_length=254)
    password:str=Field(min_length=1,max_length=1024)
    totp_code:str|None=Field(default=None,pattern=r'^[0-9]{6}$')
    verification_token:str|None=Field(default=None,max_length=128)
class SecurityRequest(Request):
    enable_totp:bool=True
    current_password:str|None=None
    step_up_totp_code:str|None=None
class ConfirmMFA(Request):
    code:str=Field(pattern=r'^[0-9]{6}$')
class RevokeRequest(Request):
    reason:str='USER_LOGOUT'

@router.post('/auth/register',status_code=201)
def register(payload:RegisterRequest):
    from app.services.identity import identity_service
    return identity_service.register(**payload.model_dump())

@router.post('/auth/login')
def login(payload:LoginRequest,request:HTTPRequest):
    from app.services.identity import identity_service
    result=identity_service.begin_login(**payload.model_dump(),ip=request.client.host if request.client else 'unknown')
    return JSONResponse(status_code=202 if result.get('mfa_required') else 200,content=jsonable_encoder(result))

@router.get('/auth/me')
def me(actor:ActorContext=Depends(require_actor_context)):
    return {'user_id':actor.user_id,'session_id':actor.session_id,'roles':actor.roles}

@router.delete('/me/sessions/{id}')
def revoke(id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return auth_service.revoke_session(session_id=str(id),actor_id=actor.user_id,require_owner_user_id=actor.user_id)

@router.post('/auth/sessions/{session_id}/revoke')
def revoke_legacy(session_id:UUID,payload:RevokeRequest,actor:ActorContext=Depends(require_actor_context)):
    return auth_service.revoke_session(session_id=str(session_id),actor_id=actor.user_id,reason=payload.reason,require_owner_user_id=actor.user_id)

@router.patch('/me/security')
def security(payload:SecurityRequest,actor:ActorContext=Depends(require_actor_context)):
    from app.core.iam_security import rate_limit
    rate_limit('security-management',actor.user_id,10,600)
    if payload.enable_totp:
        if not payload.current_password:
            raise AuthError('STEP_UP_VERIFICATION_FAILED','Current password required')
        secret=auth_service.enroll_totp(actor.user_id,payload.current_password,payload.step_up_totp_code,actor.session_id)
        return {'totp_enabled':False,'enrollment_pending':True,'secret':secret}
    if not payload.current_password:
        raise AuthError('STEP_UP_VERIFICATION_FAILED','Current password required')
    with transaction() as conn:
        from app.services.identity import require_factor
        require_factor(conn,actor.user_id,payload.current_password,payload.step_up_totp_code,actor.session_id)
        conn.execute(table('mfa_credentials').update().where(table('mfa_credentials').c.user_id==actor.user_id,
            table('mfa_credentials').c.kind=='TOTP').values(revoked_at=now(),updated_at=now()))
        auth_service.rotate_security(conn,actor.user_id)
        from app.core.audit import AppendOnlyAuditStore
        AppendOnlyAuditStore().append_audit_event(actor_id=actor.user_id,action='MFA_TOTP_DISABLED',entity_type='user',entity_id=actor.user_id)
    return {'totp_enabled':False,'step_up_verified':True,'reauthentication_required':True}

@router.post('/me/security/totp/confirm')
def confirm(payload:ConfirmMFA,actor:ActorContext=Depends(require_actor_context)):
    from app.core.iam_security import rate_limit
    rate_limit('totp-confirm',actor.user_id,10,600)
    auth_service.confirm_totp(actor.user_id,payload.code)
    return {'totp_enabled':True,'reauthentication_required':True}
