"""Workspace read models for staff portals (no new authority, read-only)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import ActorContext, require_actor_context, require_org

router = APIRouter(prefix='/api/v1', tags=['workspaces'])

# Same roles that may manage applications of an opportunity (application_hr).
ORG_OPPORTUNITY_MANAGERS = ('OWNER', 'HR', 'HOST_COORDINATOR')


@router.get('/me/workspaces')
def my_workspaces(actor: ActorContext = Depends(require_actor_context)) -> dict[str, Any]:
    """Organizations and institutions where the actor currently holds an effective grant."""
    from app.services.workspaces import list_workspaces
    return {'contract_id': 'API-ME-WORKSPACES', **list_workspaces(actor.user_id)}


@router.get('/organizations/{org}/opportunities/manage')
def manage_organization_opportunities(
    org: UUID,
    status: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=50, ge=1, le=100),
    actor: ActorContext = Depends(require_actor_context),
) -> dict[str, Any]:
    """All opportunities of an organization in every status, for its managers (`API-076`).

    The public `GET /organizations/{id}/opportunities` (API-009) only returns
    PUBLISHED items, so staff could not pick drafts or closed vacancies and had
    to paste opportunity UUIDs.
    """
    require_org(actor, str(org), *ORG_OPPORTUNITY_MANAGERS)
    from app.services.workspaces import list_org_opportunities
    return {'contract_id': 'API-076', 'organization_id': str(org),
            'items': list_org_opportunities(str(org), status=status, limit=limit)}
