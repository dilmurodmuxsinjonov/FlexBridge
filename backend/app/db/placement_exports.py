"""Typed placement report exports table; Alembic 0020 owns DDL and validation."""
from sqlalchemy import Column, Table

EXPORT_FIELDS = {
    'id': 'uuid',
    'created_at': 'timestamptz',
    'placement_id': 'uuid',
    'actor_id': 'uuid',
    'file_id': 'uuid',
    'export_format': 'text',
    'summary_snapshot': 'jsonb',
    'idempotency_key': 'text',
    'request_fingerprint': 'text',
    'receipt': 'jsonb',
    'expires_at': 'timestamptz',
}
REQUIRED_FIELDS = {
    'id',
    'created_at',
    'placement_id',
    'actor_id',
    'file_id',
    'export_format',
    'summary_snapshot',
    'idempotency_key',
    'request_fingerprint',
    'receipt',
    'expires_at',
}


def register_tables(metadata, types):
    if 'flexbridge.placement_exports' in metadata.tables:
        return metadata.tables['flexbridge.placement_exports']
    return Table(
        'placement_exports',
        metadata,
        *[
            Column(
                name,
                types[kind],
                primary_key=name == 'id',
                nullable=name not in REQUIRED_FIELDS,
            )
            for name, kind in EXPORT_FIELDS.items()
        ],
        schema='flexbridge',
    )
