"""Workspaces the current user may act in (GET /api/v1/me/workspaces).

Portals previously asked staff to paste organization / institution UUIDs. This
read model lists exactly the organizations and institutions where the actor
currently holds an effective grant, using the same rules as authorization:
- organizations: ACTIVE, non-revoked membership with non-revoked ORG role grants
- institutions: the shared institution_scope_query (accepted, current appointment)
It never widens authority; every action is still checked by its own endpoint.
"""
from __future__ import annotations

from sqlalchemy import select

from app.db.institution_scope import institution_scope_query
from app.db.storage import table, transaction


def list_workspaces(user_id: str) -> dict:
    orgs, members, grants, catalog = (table(n) for n in ('organizations', 'org_memberships', 'org_role_grants', 'role_catalog'))
    institutions = table('institutions')
    with transaction() as conn:
        org_rows = conn.execute(
            select(orgs.c.id, orgs.c.public_name, orgs.c.legal_name, orgs.c.region, orgs.c.status, catalog.c.code)
            .select_from(
                members.join(orgs, orgs.c.id == members.c.organization_id)
                .join(grants, grants.c.membership_id == members.c.id)
                .join(catalog, catalog.c.id == grants.c.role_id)
            )
            .where(
                members.c.user_id == user_id,
                members.c.status == 'ACTIVE',
                members.c.revoked_at.is_(None),
                grants.c.revoked_at.is_(None),
                catalog.c.scope_kind == 'ORG',
            )
        ).mappings().all()

        scope = institution_scope_query(user_id).subquery()
        inst_rows = conn.execute(
            select(institutions.c.id, institutions.c.name, institutions.c.region, institutions.c.status, scope.c._authority_role)
            .select_from(scope.join(institutions, institutions.c.id == scope.c.institution_id))
        ).mappings().all()

    organizations: dict[str, dict] = {}
    for row in org_rows:
        entry = organizations.setdefault(str(row['id']), {
            'id': str(row['id']),
            'name': row['public_name'] or row['legal_name'],
            'legal_name': row['legal_name'],
            'region': row['region'],
            'status': row['status'],
            'roles': [],
        })
        if row['code'] not in entry['roles']:
            entry['roles'].append(row['code'])

    result_institutions: dict[str, dict] = {}
    for row in inst_rows:
        entry = result_institutions.setdefault(str(row['id']), {
            'id': str(row['id']),
            'name': row['name'],
            'region': row['region'],
            'status': row['status'],
            'roles': [],
        })
        if row['_authority_role'] not in entry['roles']:
            entry['roles'].append(row['_authority_role'])

    def ordered(items: dict[str, dict]) -> list[dict]:
        out = sorted(items.values(), key=lambda item: (item['name'] or '').lower())
        for item in out:
            item['roles'].sort()
        return out

    return {'organizations': ordered(organizations), 'institutions': ordered(result_institutions)}


def list_org_opportunities(organization_id: str, *, status: str | None = None, limit: int = 50) -> list[dict]:
    """Every opportunity of one organization with its current revision title (newest first)."""
    opps, revisions, applications = table('opportunities'), table('opportunity_revisions'), table('applications')
    cases, actions, appeals = table('moderation_cases'), table('moderation_actions'), table('moderation_appeal_requests')
    with transaction() as conn:
        query = (
            select(
                opps.c.id, opps.c.kind, opps.c.status, opps.c.capacity, opps.c.occupied_count,
                opps.c.published_at, opps.c.expires_at, opps.c.closed_at, opps.c.created_at,
                revisions.c.title, revisions.c.region, revisions.c.work_mode,
            )
            .select_from(opps.outerjoin(revisions, revisions.c.id == opps.c.current_revision_id))
            .where(opps.c.organization_id == organization_id)
            .order_by(opps.c.created_at.desc(), opps.c.id)
            .limit(limit)
        )
        if status:
            query = query.where(opps.c.status == status.upper())
        rows = conn.execute(query).mappings().all()
        counts: dict[str, int] = {}
        rejection_actions: dict[str, str] = {}
        latest_appeals: dict[str, dict] = {}
        if rows:
            from sqlalchemy import func
            ids = [row['id'] for row in rows]
            counts = {
                str(opp_id): int(total)
                for opp_id, total in conn.execute(
                    select(applications.c.opportunity_id, func.count())
                    .where(applications.c.opportunity_id.in_(ids))
                    .group_by(applications.c.opportunity_id)
                ).all()
            }
            rejected_ids = [row['id'] for row in rows if row['status'] == 'REJECTED']
            if rejected_ids:
                action_rows = conn.execute(
                    select(cases.c.opportunity_id, actions.c.id.label('action_id'))
                    .select_from(actions.join(cases, cases.c.id == actions.c.case_id))
                    .where(cases.c.opportunity_id.in_(rejected_ids), actions.c.action == 'REJECT')
                    .order_by(actions.c.occurred_at.desc(), actions.c.created_at.desc(), actions.c.id.desc())
                ).mappings().all()
                for ar in action_rows:
                    rejection_actions.setdefault(str(ar['opportunity_id']), str(ar['action_id']))
                if rejection_actions:
                    appeal_rows = conn.execute(
                        select(
                            appeals.c.original_action_id,
                            appeals.c.case_id,
                            appeals.c.status,
                            appeals.c.decision,
                            appeals.c.decision_reason,
                        )
                        .where(appeals.c.original_action_id.in_(list(rejection_actions.values())))
                    ).mappings().all()
                    for ap in appeal_rows:
                        latest_appeals[str(ap['original_action_id'])] = {
                            'case_id': str(ap['case_id']),
                            'status': ap['status'],
                            'decision': ap['decision'],
                            'decision_reason': ap['decision_reason'],
                        }
    return [
        {
            'id': str(row['id']),
            'title': row['title'] or 'Nomsiz e’lon',
            'kind': row['kind'],
            'status': row['status'],
            'region': row['region'],
            'work_mode': row['work_mode'],
            'capacity': row['capacity'],
            'occupied_count': row['occupied_count'],
            'applications_count': counts.get(str(row['id']), 0),
            'published_at': row['published_at'].isoformat() if row['published_at'] else None,
            'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None,
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'latest_rejection_action_id': rejection_actions.get(str(row['id'])),
            'latest_appeal': latest_appeals.get(rejection_actions.get(str(row['id']), '')) if rejection_actions.get(str(row['id'])) else None,
        }
        for row in rows
    ]


def list_org_mentors(organization_id: str, *, limit: int = 100) -> list[dict]:
    """Active members holding a non-revoked MENTOR grant in one organization."""
    members, grants, roles, users = (
        table(n) for n in ('org_memberships', 'org_role_grants', 'role_catalog', 'users')
    )
    with transaction() as conn:
        rows = conn.execute(
            select(
                members.c.id.label('membership_id'),
                users.c.id.label('user_id'),
                users.c.display_name,
            )
            .select_from(
                members.join(users, users.c.id == members.c.user_id)
                .join(grants, grants.c.membership_id == members.c.id)
                .join(roles, roles.c.id == grants.c.role_id)
            )
            .where(
                members.c.organization_id == organization_id,
                members.c.status == 'ACTIVE',
                members.c.revoked_at.is_(None),
                grants.c.revoked_at.is_(None),
                roles.c.scope_kind == 'ORG',
                roles.c.code == 'MENTOR',
                users.c.status == 'ACTIVE',
            )
            .order_by(users.c.display_name, members.c.id)
            .limit(limit)
        ).mappings().all()
    seen: set[str] = set()
    items: list[dict] = []
    for r in rows:
        uid = str(r['user_id'])
        if uid in seen:
            continue
        seen.add(uid)
        items.append({
            'user_id': uid,
            'membership_id': str(r['membership_id']),
            'display_name': r['display_name'] or 'Mentor',
        })
    return items
