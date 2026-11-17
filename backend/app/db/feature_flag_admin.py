"""Typed feature-flag administration proof tables; Alembic 0017 owns DDL and validation."""
from sqlalchemy import Column, Table

ORIGIN_FIELDS = {'flag_id': 'uuid', 'code': 'text', 'origin': 'text', 'initial_snapshot': 'jsonb',
                 'created_at': 'timestamptz'}
EVENT_FIELDS = {'id': 'uuid', 'created_at': 'timestamptz', 'flag_id': 'uuid', 'code': 'text', 'version': 'integer',
                'prior_event_id': 'uuid', 'enabled': 'boolean', 'rule_schema': 'jsonb', 'reason': 'text',
                'before_snapshot': 'jsonb', 'after_snapshot': 'jsonb', 'before_digest': 'text',
                'after_digest': 'text', 'actor_id': 'uuid', 'session_id': 'uuid', 'auth_version': 'integer',
                'admin_grant_id': 'uuid', 'decided_at': 'timestamptz', 'idempotency_key': 'text',
                'request_fingerprint': 'text', 'audit_event_id': 'uuid', 'receipt': 'jsonb'}
EVENT_NULLABLE = {'prior_event_id', 'before_snapshot', 'before_digest'}


def register_tables(metadata, types):
    Table('feature_flag_origins', metadata,
          *[Column(name, types[kind], primary_key=name == 'flag_id', nullable=False)
            for name, kind in ORIGIN_FIELDS.items()])
    Table('feature_flag_change_events', metadata,
          *[Column(name, types[kind], primary_key=name == 'id', nullable=name in EVENT_NULLABLE)
            for name, kind in EVENT_FIELDS.items()])
