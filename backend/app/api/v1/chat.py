"""User-to-user chat API (Issue #253). Rules live in app.services.chat."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ActorContext, require_actor_context
from app.services.chat import chat_service as chat

router = APIRouter(prefix='/api/v1/chat', tags=['chat'])


class _Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class DirectInput(_Strict):
    user_id: UUID | None = None
    contact_code: str | None = Field(default=None, min_length=8, max_length=8)


class GroupInput(_Strict):
    title: str = Field(min_length=1, max_length=80)
    member_ids: list[UUID] = Field(default_factory=list, max_length=199)


class RenameInput(_Strict):
    title: str = Field(min_length=1, max_length=80)


class MembersInput(_Strict):
    member_ids: list[UUID] = Field(min_length=1, max_length=199)


class MessageInput(_Strict):
    body: str = Field(min_length=1, max_length=4000)


class JoinInput(_Strict):
    token: str = Field(min_length=16, max_length=128)


@router.get('/me')
def my_code(actor: ActorContext = Depends(require_actor_context)):
    return chat.my_code(actor)


@router.post('/me/contact-code/rotate')
def rotate_code(actor: ActorContext = Depends(require_actor_context)):
    return chat.my_code(actor, rotate=True)


@router.get('/contacts')
def contacts(q: str | None = Query(default=None, max_length=80), actor: ActorContext = Depends(require_actor_context)):
    return chat.contacts(actor, q)


@router.get('/conversations')
def conversations(actor: ActorContext = Depends(require_actor_context)):
    return chat.list_conversations(actor)


@router.get('/conversations/{cid}')
def conversation(cid: UUID, actor: ActorContext = Depends(require_actor_context)):
    return chat.get_conversation(actor, str(cid))


@router.post('/direct')
def direct(payload: DirectInput, actor: ActorContext = Depends(require_actor_context)):
    return chat.start_direct(actor, user_id=str(payload.user_id) if payload.user_id else None, contact_code=payload.contact_code)


@router.post('/groups', status_code=201)
def create_group(payload: GroupInput, actor: ActorContext = Depends(require_actor_context)):
    return chat.create_group(actor, title=payload.title, member_ids=[str(m) for m in payload.member_ids])


@router.patch('/groups/{cid}')
def rename_group(cid: UUID, payload: RenameInput, actor: ActorContext = Depends(require_actor_context)):
    return chat.rename_group(actor, str(cid), payload.title)


@router.post('/groups/{cid}/members')
def add_members(cid: UUID, payload: MembersInput, actor: ActorContext = Depends(require_actor_context)):
    return chat.add_members(actor, str(cid), [str(m) for m in payload.member_ids])


@router.delete('/groups/{cid}/members/{uid}')
def remove_member(cid: UUID, uid: UUID, actor: ActorContext = Depends(require_actor_context)):
    return chat.remove_member(actor, str(cid), str(uid))


@router.post('/groups/{cid}/invite-link')
def enable_link(cid: UUID, actor: ActorContext = Depends(require_actor_context)):
    return chat.invite_link(actor, str(cid), enable=True)


@router.delete('/groups/{cid}/invite-link')
def disable_link(cid: UUID, actor: ActorContext = Depends(require_actor_context)):
    return chat.invite_link(actor, str(cid), enable=False)


@router.post('/join')
def join(payload: JoinInput, actor: ActorContext = Depends(require_actor_context)):
    return chat.join_by_link(actor, payload.token)


@router.get('/conversations/{cid}/messages')
def messages(cid: UUID, before: UUID | None = None, limit: int = Query(default=50, ge=1, le=100),
             actor: ActorContext = Depends(require_actor_context)):
    return chat.list_messages(actor, str(cid), before=str(before) if before else None, limit=limit)


@router.post('/conversations/{cid}/messages', status_code=201)
def send(cid: UUID, payload: MessageInput, actor: ActorContext = Depends(require_actor_context)):
    return chat.send(actor, str(cid), payload.body)


@router.post('/conversations/{cid}/read')
def read(cid: UUID, actor: ActorContext = Depends(require_actor_context)):
    return chat.mark_read(actor, str(cid))


@router.delete('/messages/{mid}')
def delete_message(mid: UUID, actor: ActorContext = Depends(require_actor_context)):
    return chat.delete_message(actor, str(mid))


@router.post('/blocks/{uid}')
def block(uid: UUID, actor: ActorContext = Depends(require_actor_context)):
    return chat.block(actor, str(uid), blocked=True)


@router.delete('/blocks/{uid}')
def unblock(uid: UUID, actor: ActorContext = Depends(require_actor_context)):
    return chat.block(actor, str(uid), blocked=False)
