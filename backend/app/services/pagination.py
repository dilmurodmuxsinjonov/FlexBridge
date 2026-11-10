"""Scoped keyset pages; an anchor must belong to the same authorized query."""
from uuid import UUID
from sqlalchemy import tuple_
from app.services.placements import PlacementScopeError


def page(conn, query, identifier, ordered_at, *, limit=50, after=None, cursor_query=None):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise PlacementScopeError('INVALID_PAGE_LIMIT', status_code=422)
    def columns(q):return q.add_columns(identifier.label('_page_id'), ordered_at.label('_page_time'))
    if after is not None:
        try:after=str(UUID(str(after)))
        except (ValueError,TypeError,AttributeError) as exc:
            raise PlacementScopeError('INVALID_PAGE_CURSOR', status_code=422) from exc
        anchor=conn.execute(columns(cursor_query if cursor_query is not None else query)
                            .where(identifier==after)).mappings().first()
        if not anchor:raise PlacementScopeError('PAGE_CURSOR_NOT_FOUND', status_code=404)
        query=query.where(tuple_(ordered_at,identifier)>(anchor['_page_time'],anchor['_page_id']))
    rows=conn.execute(columns(query).order_by(ordered_at,identifier).limit(limit+1)).mappings().all()
    next_after=str(rows[limit-1]['_page_id']) if len(rows)>limit else None
    return {'items':[{k:v for k,v in row.items() if k not in ('_page_id','_page_time')} for row in rows[:limit]],
            'next_after':next_after}
