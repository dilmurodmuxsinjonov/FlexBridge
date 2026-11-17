"""Versioned global flag administration under actual current platform ADMIN."""
import re

from fastapi import APIRouter,Depends,Header,Path
from pydantic import BaseModel,ConfigDict,Field,StrictBool,StrictStr

from app.api.dependencies import ActorContext,require_actor_context,require_platform
from app.core.iam_security import rate_limit
from app.services.feature_flag_admin import flag_admin_service
from app.services.governance import GovernanceError

router=APIRouter(prefix='/api/v1/operator/feature-flags',tags=['feature-flags'])


class FeatureFlagPatch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled:StrictBool
    reason:StrictStr=Field(min_length=15,max_length=2000)


def request_intent(key,version):
    if key is None:
        raise GovernanceError('IDEMPOTENCY_KEY_REQUIRED',status_code=400)
    normalized=key.strip()
    if not 8<=len(normalized)<=128 or any(ord(c)<32 or ord(c)>126 for c in normalized):
        raise GovernanceError('INVALID_IDEMPOTENCY_KEY',status_code=400)
    if version is None:
        raise GovernanceError('IF_MATCH_REQUIRED',status_code=400)
    match=re.fullmatch(r'"(0|[1-9][0-9]{0,9})"',version)
    if not match or int(match.group(1))>2147483647:
        raise GovernanceError('INVALID_IF_MATCH',status_code=400)
    return normalized,int(match.group(1))


@router.patch('/{code}')
def administer_flag(payload:FeatureFlagPatch,code:str=Path(min_length=1,max_length=80),
        idempotency_key:str|None=Header(default=None,alias='Idempotency-Key'),
        if_match:str|None=Header(default=None,alias='If-Match'),actor:ActorContext=Depends(require_actor_context)):
    key,version=request_intent(idempotency_key,if_match)
    # Cheap current-role precheck/rate counter ends before the business UoW.
    # The service still pins actual current authority after all business waits.
    require_platform(actor,'ADMIN')
    rate_limit('feature-flag-admin',actor.user_id,20,600)
    return flag_admin_service.administer(actor=actor,code=code,enabled=payload.enabled,reason=payload.reason,
        idempotency_key=key,expected_version=version)
