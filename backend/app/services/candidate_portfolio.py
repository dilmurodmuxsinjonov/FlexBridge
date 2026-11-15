"""Candidate portfolio showcase service (API-026 / CAP-002)."""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, and_

from app.api.dependencies import ActorContext, candidate_id_for
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.services.auth import AuthError
from app.services.authority import account_authority

audit = AppendOnlyAuditStore()


class CandidatePortfolioService:
    def list_portfolio(
        self,
        actor: ActorContext,
        limit: int = 50,
        after_id: str | None = None,
    ) -> dict[str, Any]:
        with transaction() as conn:
            cand_id = candidate_id_for(actor)
            account_authority(conn, actor)

            t_port = table('candidate_portfolios')
            query = select(t_port).where(t_port.c.candidate_id == cand_id)

            if after_id:
                after_row = conn.execute(
                    select(t_port.c.created_at).where(t_port.c.id == after_id)
                ).first()
                if after_row:
                    query = query.where(t_port.c.created_at < after_row[0])

            query = query.order_by(t_port.c.created_at.desc()).limit(min(limit, 100))
            rows = conn.execute(query).mappings().all()

            count_query = select(t_port.c.id).where(t_port.c.candidate_id == cand_id)
            total = len(conn.execute(count_query).all())

            items = []
            for r in rows:
                item = dict(r)
                if item.get('start_date') and hasattr(item['start_date'], 'isoformat'):
                    item['start_date'] = item['start_date'].isoformat()
                if item.get('end_date') and hasattr(item['end_date'], 'isoformat'):
                    item['end_date'] = item['end_date'].isoformat()
                if item.get('created_at') and hasattr(item['created_at'], 'isoformat'):
                    item['created_at'] = item['created_at'].isoformat()
                if item.get('updated_at') and hasattr(item['updated_at'], 'isoformat'):
                    item['updated_at'] = item['updated_at'].isoformat()
                items.append(item)

            return {
                'contract_id': 'API-026-PORTFOLIO-LIST',
                'items': items,
                'total': total,
            }

    def create_portfolio(
        self,
        actor: ActorContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with transaction() as conn:
            cand_id = candidate_id_for(actor)
            account_authority(conn, actor)

            title = str(payload.get('title', '')).strip()
            if not 2 <= len(title) <= 200:
                raise AuthError('INVALID_PORTFOLIO_TITLE', 'Title must be 2-200 characters', 422)

            description = str(payload.get('description', '')).strip()
            if not 2 <= len(description) <= 5000:
                raise AuthError('INVALID_PORTFOLIO_DESCRIPTION', 'Description must be 2-5000 characters', 422)

            start_date = payload.get('start_date')
            end_date = payload.get('end_date')
            if start_date and end_date and str(end_date) < str(start_date):
                raise AuthError('INVALID_DATE_RANGE', 'End date must be greater than or equal to start date', 422)

            skills = payload.get('skills') or []
            if not isinstance(skills, list):
                raise AuthError('INVALID_SKILLS', 'Skills must be a list', 422)

            file_id = payload.get('file_id')
            if file_id is not None:
                files = table('files')
                f_row = conn.execute(
                    select(files).where(
                        files.c.id == str(file_id),
                        files.c.owner_user_id == actor.user_id,
                    )
                ).mappings().first()
                if not f_row:
                    raise AuthError('FILE_ACCESS_DENIED', 'Cannot attach file owned by another user', 403)
                if f_row.get('deleted_at') or f_row.get('scan_status') != 'CLEAN':
                    raise AuthError('FILE_NOT_CLEAN', 'Attached file must be scanned and CLEAN', 409)

            item_id = str(uuid4())
            ts = now()
            conn.execute(
                table('candidate_portfolios').insert().values(
                    id=item_id,
                    created_at=ts,
                    updated_at=ts,
                    candidate_id=cand_id,
                    title=title,
                    description=description,
                    project_url=payload.get('project_url'),
                    github_url=payload.get('github_url'),
                    skills=skills,
                    start_date=start_date,
                    end_date=end_date,
                    file_id=str(file_id) if file_id else None,
                )
            )

            audit.append_audit_event(
                actor_id=actor.user_id,
                action='CANDIDATE_PORTFOLIO_CREATED',
                entity_type='candidate_portfolio',
                entity_id=item_id,
                metadata={'candidate_id': cand_id, 'title': title},
            )

            return {
                'id': item_id,
                'candidate_id': cand_id,
                'title': title,
                'description': description,
                'project_url': payload.get('project_url'),
                'github_url': payload.get('github_url'),
                'skills': skills,
                'start_date': str(start_date) if start_date else None,
                'end_date': str(end_date) if end_date else None,
                'file_id': str(file_id) if file_id else None,
                'created_at': ts.isoformat(),
                'updated_at': ts.isoformat(),
            }

    def update_portfolio(
        self,
        actor: ActorContext,
        item_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with transaction() as conn:
            cand_id = candidate_id_for(actor)
            account_authority(conn, actor)

            t_port = table('candidate_portfolios')
            existing = conn.execute(
                select(t_port).where(t_port.c.id == item_id)
            ).mappings().first()

            if not existing:
                raise AuthError('PORTFOLIO_NOT_FOUND', 'Portfolio item not found', 404)

            # IDOR defense: Item must belong to caller's candidate_id
            if str(existing['candidate_id']) != cand_id:
                raise AuthError('PORTFOLIO_ACCESS_DENIED', 'Cannot edit portfolio item of another candidate', 403)

            updates: dict[str, Any] = {}
            if 'title' in payload:
                title = str(payload['title']).strip()
                if not 2 <= len(title) <= 200:
                    raise AuthError('INVALID_PORTFOLIO_TITLE', 'Title must be 2-200 characters', 422)
                updates['title'] = title

            if 'description' in payload:
                description = str(payload['description']).strip()
                if not 2 <= len(description) <= 5000:
                    raise AuthError('INVALID_PORTFOLIO_DESCRIPTION', 'Description must be 2-5000 characters', 422)
                updates['description'] = description

            if 'project_url' in payload:
                updates['project_url'] = payload['project_url']
            if 'github_url' in payload:
                updates['github_url'] = payload['github_url']
            if 'skills' in payload:
                if not isinstance(payload['skills'], list):
                    raise AuthError('INVALID_SKILLS', 'Skills must be a list', 422)
                updates['skills'] = payload['skills']

            start_date = payload.get('start_date', existing.get('start_date'))
            end_date = payload.get('end_date', existing.get('end_date'))
            if start_date and end_date and str(end_date) < str(start_date):
                raise AuthError('INVALID_DATE_RANGE', 'End date must be greater than or equal to start date', 422)

            if 'start_date' in payload:
                updates['start_date'] = payload['start_date']
            if 'end_date' in payload:
                updates['end_date'] = payload['end_date']

            if 'file_id' in payload:
                file_id = payload['file_id']
                if file_id is not None:
                    files = table('files')
                    f_row = conn.execute(
                        select(files).where(
                            files.c.id == str(file_id),
                            files.c.owner_user_id == actor.user_id,
                        )
                    ).mappings().first()
                    if not f_row:
                        raise AuthError('FILE_ACCESS_DENIED', 'Cannot attach file owned by another user', 403)
                    if f_row.get('deleted_at') or f_row.get('scan_status') != 'CLEAN':
                        raise AuthError('FILE_NOT_CLEAN', 'Attached file must be scanned and CLEAN', 409)
                updates['file_id'] = str(file_id) if file_id else None

            updates['updated_at'] = now()

            conn.execute(
                t_port.update().where(t_port.c.id == item_id).values(**updates)
            )

            audit.append_audit_event(
                actor_id=actor.user_id,
                action='CANDIDATE_PORTFOLIO_UPDATED',
                entity_type='candidate_portfolio',
                entity_id=item_id,
                metadata={'candidate_id': cand_id},
            )

            updated_row = conn.execute(
                select(t_port).where(t_port.c.id == item_id)
            ).mappings().first()

            result = dict(updated_row)
            if result.get('start_date') and hasattr(result['start_date'], 'isoformat'):
                result['start_date'] = result['start_date'].isoformat()
            if result.get('end_date') and hasattr(result['end_date'], 'isoformat'):
                result['end_date'] = result['end_date'].isoformat()
            if result.get('created_at') and hasattr(result['created_at'], 'isoformat'):
                result['created_at'] = result['created_at'].isoformat()
            if result.get('updated_at') and hasattr(result['updated_at'], 'isoformat'):
                result['updated_at'] = result['updated_at'].isoformat()
            return result

    def delete_portfolio(self, actor: ActorContext, item_id: str) -> None:
        with transaction() as conn:
            cand_id = candidate_id_for(actor)
            account_authority(conn, actor)

            t_port = table('candidate_portfolios')
            existing = conn.execute(
                select(t_port).where(t_port.c.id == item_id)
            ).mappings().first()

            if not existing:
                raise AuthError('PORTFOLIO_NOT_FOUND', 'Portfolio item not found', 404)

            # IDOR defense: Item must belong to caller's candidate_id
            if str(existing['candidate_id']) != cand_id:
                raise AuthError('PORTFOLIO_ACCESS_DENIED', 'Cannot delete portfolio item of another candidate', 403)

            conn.execute(t_port.delete().where(t_port.c.id == item_id))

            audit.append_audit_event(
                actor_id=actor.user_id,
                action='CANDIDATE_PORTFOLIO_DELETED',
                entity_type='candidate_portfolio',
                entity_id=item_id,
                metadata={'candidate_id': cand_id},
            )


candidate_portfolio_service = CandidatePortfolioService()
