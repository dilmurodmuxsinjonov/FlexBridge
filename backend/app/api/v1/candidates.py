"""Canonical CAN self-service endpoints; actor IDs and verification are server-owned."""
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.dependencies import ActorContext, require_actor_context, candidate_id_for
from app.services.candidates import candidate_service
from app.services.availability import availability_service
from app.services.schedule import local_today

router = APIRouter(prefix='/api/v1', tags=['candidate'])


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class ProfilePatch(Input):
    headline: str | None = Field(default=None, min_length=1, max_length=200)
    region: str | None = Field(default=None, min_length=1, max_length=100)
    bio: str | None = Field(default=None, max_length=5000)
    experience_months: int | None = Field(default=None, ge=0, le=1200)

    @model_validator(mode='after')
    def nonnull_fields(self):
        if any(getattr(self, name) is None for name in self.model_fields_set - {'bio'}):
            raise ValueError('Only bio may be null')
        return self


class SkillInput(Input):
    skill_id: UUID
    level: str = Field(min_length=1, max_length=64)


class SkillsPatch(Input):
    skills: list[SkillInput] = Field(default_factory=list, max_length=100)
    remove_skill_ids: list[UUID] = Field(default_factory=list, max_length=100)


class CVInput(Input):
    file_id: UUID | None


class RuleInput(Input):
    weekday: int = Field(ge=1, le=7)
    start_minute: int = Field(ge=0, lt=1440)
    end_minute: int = Field(gt=0, le=1440)
    valid_from: date = Field(default_factory=local_today)
    valid_to: date | None = None
    timezone: Literal['Asia/Tashkent'] = 'Asia/Tashkent'

    @model_validator(mode='after')
    def bounds(self):
        if self.start_minute >= self.end_minute or (self.valid_to is not None and self.valid_to < self.valid_from):
            raise ValueError('Invalid interval or validity dates')
        return self


class AvailabilityInput(Input):
    rules: list[RuleInput] = Field(max_length=100)


class ExceptionInput(Input):
    local_date: date
    kind: Literal['AVAILABLE', 'UNAVAILABLE']
    start_minute: int = Field(ge=0, lt=1440)
    end_minute: int = Field(gt=0, le=1440)

    @model_validator(mode='after')
    def bounds(self):
        if self.start_minute >= self.end_minute:
            raise ValueError('Interval must be nonempty')
        return self


class ExceptionsInput(Input):
    from_date: date
    to_date: date
    exceptions: list[ExceptionInput] = Field(max_length=400)

    @model_validator(mode='after')
    def bounds(self):
        if self.to_date == date.max or not 0 <= (self.to_date - self.from_date).days <= 365:
            raise ValueError('Replacement range must be at most 366 days, inclusive')
        if any(not self.from_date <= item.local_date <= self.to_date for item in self.exceptions):
            raise ValueError('All exceptions must be inside the replacement range')
        return self


@router.get('/me/candidate')
def get_profile(actor: ActorContext = Depends(require_actor_context)):
    return candidate_service.get_profile(actor)


@router.patch('/me/candidate')
def patch_profile(payload: ProfilePatch, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id': 'API-026', **candidate_service.update_profile(actor, payload.model_dump(exclude_unset=True))}


@router.patch('/me/candidate/skills')
def patch_skills(payload: SkillsPatch, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id': 'API-032', **candidate_service.update_skills(actor,
        [item.model_dump() for item in payload.skills], payload.remove_skill_ids)}


@router.post('/me/candidate/cv')
def link_cv(payload: CVInput, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id': 'API-033', **candidate_service.link_cv(actor, payload.file_id)}


@router.get('/skills')
def skill_catalog(q: str = Query(default='', max_length=100), limit: int = Query(default=50, ge=1, le=100),
                  actor: ActorContext = Depends(require_actor_context)):
    return {'items': candidate_service.catalog(q, limit)}


@router.put('/me/availability')
def put_availability(payload: AvailabilityInput, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id': 'API-028', **availability_service.replace_rules(actor,
        [item.model_dump() for item in payload.rules])}


@router.get('/me/availability')
def get_availability(from_date: date | None = None, days: int = Query(default=28, ge=1, le=366),
                     actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id': 'API-035', **availability_service.get_my_schedule(actor, from_date, days)}


@router.put('/me/availability/exceptions')
def put_exceptions(payload: ExceptionsInput, actor: ActorContext = Depends(require_actor_context)):
    return {'contract_id': 'API-036', **availability_service.replace_exceptions(actor,
        payload.from_date, payload.to_date, [item.model_dump() for item in payload.exceptions])}
