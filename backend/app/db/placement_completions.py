"""Typed placement completion requests table; Alembic 0019 owns DDL and validation."""
from sqlalchemy import Column, Table

COMPLETION_FIELDS = {
    'id': 'uuid',
    'created_at': 'timestamptz',
    'placement_id': 'uuid',
    'terms_id': 'uuid',
    'actor_id': 'uuid',
    'side': 'text',
    'decision': 'text',
    'status': 'text',
    'reason': 'text',
    'early_completion': 'boolean',
    'logged_minutes': 'integer',
    'required_minutes': 'integer',
    'basis_snapshot': 'jsonb',
    'idempotency_key': 'text',
    'request_fingerprint': 'text',
    'receipt': 'jsonb',
    'decided_at': 'timestamptz',
}
REQUIRED_FIELDS = {
    'id',
    'created_at',
    'placement_id',
    'terms_id',
    'actor_id',
    'side',
    'decision',
    'status',
    'basis_snapshot',
    'idempotency_key',
    'request_fingerprint',
    'receipt',
    'decided_at',
}


def register_tables(metadata, types):
    if 'flexbridge.placement_completion_requests' in metadata.tables:
        return metadata.tables['flexbridge.placement_completion_requests']
    return Table(
        'placement_completion_requests',
        metadata,
        *[
            Column(
                name,
                types[kind],
                primary_key=name == 'id',
                nullable=name not in REQUIRED_FIELDS,
            )
            for name, kind in COMPLETION_FIELDS.items()
        ],
        schema='flexbridge',
    )
