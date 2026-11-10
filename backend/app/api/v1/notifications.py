"""Own unread transactional inbox and idempotent own read acknowledgement."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.api.dependencies import ActorContext, require_actor_context
from app.services.mentor_notices import notification_service as service

router=APIRouter(prefix='/api/v1/me/notifications',tags=['notifications'])


@router.get('')
def own(limit: int=Query(default=50,ge=1,le=100),after: UUID|None=None,unread_only: bool=True,
        actor: ActorContext=Depends(require_actor_context)):
    return service.own(actor,limit=limit,after=after,unread_only=unread_only)


@router.post('/{id}/read')
def read(id: UUID,actor: ActorContext=Depends(require_actor_context)):
    return service.read(actor,str(id))
