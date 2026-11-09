"""Typed access to the migrated PostgreSQL schema. Startup never manufactures DDL."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, MetaData, Numeric, Table, Text, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID, insert
from sqlalchemy.engine import Connection, Engine

ROOT = Path(__file__).resolve().parents[3]
MODEL_JSON_PATH = ROOT / 'specs/v1_4/FlexBridge_model_1_4.json'
metadata = MetaData(schema='flexbridge')
_TYPES = {'uuid': UUID(as_uuid=False), 'text': Text(), 'integer': Integer(), 'boolean': Boolean(),
    'date': Date(), 'timestamptz': DateTime(timezone=True), 'jsonb': JSONB(), 'numeric(18,2)': Numeric(18, 2)}
for definition in json.loads(MODEL_JSON_PATH.read_text(encoding='utf-8'))['tables']:
    Table(definition['name'], metadata, *[Column(f['name'], _TYPES[f['type']],
        primary_key=f['pk'], nullable=f['nullable']) for f in definition['fields']])

def table(name: str) -> Table:
    return metadata.tables['flexbridge.' + name]

users_table = table('users')
sessions_table = table('sessions')
users_table.append_column(Column('auth_version',Integer,nullable=False))
for c in (Column('role_id',UUID(as_uuid=False)),Column('channel',Text),Column('target_user_id',UUID(as_uuid=False)),Column('target_contact_id',UUID(as_uuid=False))):
    table('org_invitations').append_column(c)
sessions_table.append_column(Column('auth_version',Integer,nullable=False))
for c in (Column('destination_encrypted',Text),Column('delivery_encrypted',Text),
          Column('delivery_status',Text,nullable=False),Column('sent_at',DateTime(timezone=True))):
    table('auth_challenges').append_column(c)
auth_continuations = Table('auth_continuations',metadata,Column('digest',Text,primary_key=True),
    Column('kind',Text,nullable=False),Column('user_id',UUID(as_uuid=False)),Column('challenge_id',UUID(as_uuid=False)),
    Column('payload_encrypted',Text,nullable=False),Column('created_at',DateTime(timezone=True),nullable=False),
    Column('expires_at',DateTime(timezone=True),nullable=False),Column('consumed_at',DateTime(timezone=True)),
    Column('attempts',Integer,nullable=False))
auth_rate_limits = Table('auth_rate_limits',metadata,Column('bucket_key',Text,primary_key=True),
    Column('window_started_at',DateTime(timezone=True),nullable=False),Column('count',Integer,nullable=False))
org_verification_submissions = Table('org_verification_submissions',metadata,
    Column('case_id',UUID(as_uuid=False),primary_key=True),Column('revision',Integer,primary_key=True),
    Column('organization_id',UUID(as_uuid=False),nullable=False),Column('requester_membership_id',UUID(as_uuid=False)),
    Column('proposed_fields',JSONB,nullable=False),Column('created_at',DateTime(timezone=True),nullable=False))
retention_evaluations = Table('retention_evaluations',metadata,
    Column('id',UUID(as_uuid=False),primary_key=True),Column('created_at',DateTime(timezone=True),nullable=False),
    Column('actor_id',UUID(as_uuid=False),nullable=False),Column('idempotency_key',Text,nullable=False),
    Column('request_fingerprint',Text,nullable=False),Column('data_category',Text,nullable=False),
    Column('requested_age_days',Integer,nullable=False),Column('requested_records_scanned',Integer,nullable=False),
    Column('policy_snapshot',JSONB,nullable=False),Column('evaluation',JSONB,nullable=False),
    Column('mode',Text,nullable=False),Column('status',Text,nullable=False),Column('records_scanned',Integer,nullable=False),
    Column('records_actioned',Integer,nullable=False),Column('finished_at',DateTime(timezone=True),nullable=False))
moderation_appeal_requests = Table('moderation_appeal_requests',metadata,
    Column('case_id',UUID(as_uuid=False),primary_key=True),Column('created_at',DateTime(timezone=True),nullable=False),
    Column('original_action_id',UUID(as_uuid=False),nullable=False),Column('opportunity_id',UUID(as_uuid=False),nullable=False),
    Column('revision_id',UUID(as_uuid=False),nullable=False),Column('appellant_id',UUID(as_uuid=False),nullable=False),
    Column('reason',Text,nullable=False),Column('revision_snapshot',JSONB,nullable=False),
    Column('original_decision',JSONB,nullable=False),Column('status',Text,nullable=False),
    Column('reviewer_id',UUID(as_uuid=False)),Column('decision',Text),Column('decision_reason',Text),
    Column('resolved_at',DateTime(timezone=True)))
owner_addition_requests = Table('owner_addition_requests',metadata,
    Column('case_id',UUID(as_uuid=False),primary_key=True),Column('created_at',DateTime(timezone=True),nullable=False),
    Column('organization_id',UUID(as_uuid=False),nullable=False),Column('requester_user_id',UUID(as_uuid=False),nullable=False),
    Column('requester_membership_id',UUID(as_uuid=False),nullable=False),Column('requester_grant_id',UUID(as_uuid=False),nullable=False),
    Column('requester_auth_version',Integer,nullable=False),
    Column('requester_session_id',UUID(as_uuid=False),nullable=False),Column('target_user_id',UUID(as_uuid=False),nullable=False),
    Column('target_membership_id',UUID(as_uuid=False),nullable=False),Column('idempotency_key',Text,nullable=False),
    Column('request_fingerprint',Text,nullable=False))
owner_addition_consents = Table('owner_addition_consents',metadata,
    Column('id',UUID(as_uuid=False),primary_key=True),Column('case_id',UUID(as_uuid=False),nullable=False),
    Column('created_at',DateTime(timezone=True),nullable=False),Column('revision',Integer,nullable=False),
    Column('event_no',Integer,nullable=False),Column('actor_id',UUID(as_uuid=False),nullable=False),
    Column('auth_version',Integer,nullable=False),Column('session_id',UUID(as_uuid=False),nullable=False),
    Column('decision',Text,nullable=False),Column('target_staff_grant_id',UUID(as_uuid=False)),
    Column('contact_id',UUID(as_uuid=False)),Column('contact_digest',Text),
    Column('contact_verified_at',DateTime(timezone=True)),Column('expires_at',DateTime(timezone=True)))
owner_transfer_requests = Table('owner_transfer_requests',metadata,
    Column('case_id',UUID(as_uuid=False),primary_key=True),Column('created_at',DateTime(timezone=True),nullable=False),
    Column('organization_id',UUID(as_uuid=False),nullable=False),Column('requester_user_id',UUID(as_uuid=False),nullable=False),
    Column('requester_membership_id',UUID(as_uuid=False),nullable=False),Column('requester_grant_id',UUID(as_uuid=False),nullable=False),
    Column('requester_auth_version',Integer,nullable=False),
    Column('requester_session_id',UUID(as_uuid=False),nullable=False),Column('target_user_id',UUID(as_uuid=False),nullable=False),
    Column('target_membership_id',UUID(as_uuid=False),nullable=False),Column('target_grant_id',UUID(as_uuid=False),nullable=False),Column('idempotency_key',Text,nullable=False),
    Column('request_fingerprint',Text,nullable=False))
owner_transfer_consents = Table('owner_transfer_consents',metadata,
    Column('id',UUID(as_uuid=False),primary_key=True),Column('case_id',UUID(as_uuid=False),nullable=False),
    Column('created_at',DateTime(timezone=True),nullable=False),Column('revision',Integer,nullable=False),
    Column('event_no',Integer,nullable=False),Column('actor_id',UUID(as_uuid=False),nullable=False),
    Column('auth_version',Integer,nullable=False),Column('session_id',UUID(as_uuid=False),nullable=False),
    Column('decision',Text,nullable=False),Column('target_owner_grant_id',UUID(as_uuid=False)),
    Column('contact_id',UUID(as_uuid=False)),Column('contact_digest',Text),
    Column('contact_verified_at',DateTime(timezone=True)),Column('expires_at',DateTime(timezone=True)))
owner_continuity_requests = Table('owner_continuity_requests',metadata,
    Column('case_id',UUID(as_uuid=False),primary_key=True),Column('recovery_id',UUID(as_uuid=False),nullable=False),
    Column('organization_id',UUID(as_uuid=False),nullable=False),Column('applicant_id',UUID(as_uuid=False),nullable=False),
    Column('membership_id',UUID(as_uuid=False),nullable=False),Column('staff_grant_id',UUID(as_uuid=False),nullable=False),
    Column('auth_version',Integer,nullable=False),Column('session_id',UUID(as_uuid=False),nullable=False),
    Column('contact_id',UUID(as_uuid=False),nullable=False),Column('contact_digest',Text,nullable=False),
    Column('contact_verified_at',DateTime(timezone=True),nullable=False),Column('created_at',DateTime(timezone=True),nullable=False),
    Column('expires_at',DateTime(timezone=True),nullable=False),Column('owner_roster',JSONB,nullable=False),
    Column('evidence_file_ids',JSONB,nullable=False),Column('evidence_note',Text,nullable=False),
    Column('idempotency_key',Text,nullable=False),Column('request_fingerprint',Text,nullable=False))
owner_continuity_events = Table('owner_continuity_events',metadata,
    Column('id',UUID(as_uuid=False),primary_key=True),Column('case_id',UUID(as_uuid=False),nullable=False),
    Column('stage',Text,nullable=False),Column('action',Text,nullable=False),Column('actor_id',UUID(as_uuid=False),nullable=False),
    Column('authority_grant_id',UUID(as_uuid=False),nullable=False),Column('auth_version',Integer,nullable=False),
    Column('session_id',UUID(as_uuid=False),nullable=False),Column('created_at',DateTime(timezone=True),nullable=False),
    Column('claim_id',UUID(as_uuid=False)),Column('reason',Text),Column('result_owner_grant_id',UUID(as_uuid=False)),
    Column('ownership_event_id',UUID(as_uuid=False)))
from app.db.institution_onboarding import register_tables as register_institution_tables
register_institution_tables(metadata,_TYPES)
from app.db.enrollment_verification import register_tables as register_enrollment_tables
register_enrollment_tables(metadata,_TYPES)
from app.db.placement_admission import register_tables as register_admission_tables
register_admission_tables(metadata,_TYPES)
circuit_breaker_table = Table('circuit_breaker_state', metadata,
    Column('key', Text, primary_key=True), Column('state', Text, nullable=False), Column('incident_id', Text),
    Column('reason_code', Text), Column('tripped_by', Text), Column('tripped_at', DateTime(timezone=True)),
    Column('updated_at', DateTime(timezone=True), nullable=False))
kv_records_table = Table('domain_records', metadata, Column('namespace', Text, primary_key=True),
    Column('record_id', Text, primary_key=True), Column('payload_json', JSONB, nullable=False),
    Column('updated_at', DateTime(timezone=True), nullable=False))
outbox_table = table('outbox_events')
for c in (Column('claimed_by', Text), Column('lease_until', DateTime(timezone=True)), Column('claim_token', UUID(as_uuid=False))):
    outbox_table.append_column(c)
files_table = table('files')
table('availability_rules').append_column(Column('is_active', Boolean,nullable=False))
for c in (Column('object_version', Text), Column('scan_error', Text), Column('scanned_at', DateTime(timezone=True)),
          Column('storage_bucket', Text), Column('storage_version_id', Text), Column('storage_etag', Text)):
    files_table.append_column(c)
_ENGINE: Engine | None = None
_CURRENT: ContextVar[Connection | None] = ContextVar('unit_of_work', default=None)

def now() -> datetime:
    return datetime.now(timezone.utc)

def get_database_url() -> str:
    value = os.environ.get('FLEXBRIDGE_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if not value or not value.startswith('postgresql+psycopg://'):
        raise RuntimeError('DATABASE_URL must use PostgreSQL/psycopg; run migrations before starting the API')
    return value

def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(get_database_url(), pool_pre_ping=True,
            connect_args={'prepare_threshold': None}, hide_parameters=True)
    return _ENGINE

def init_storage() -> Engine:
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        revision = conn.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one()
        if revision != '0014_placement_admission':
            raise RuntimeError('Database migrations are not current')
    return engine

@contextmanager
def transaction() -> Iterator[Connection]:
    existing = _CURRENT.get()
    if existing is not None:
        yield existing
        return
    with get_engine().begin() as conn:
        token = _CURRENT.set(conn)
        try:
            yield conn
        finally:
            _CURRENT.reset(token)

def current_connection() -> Connection | None:
    return _CURRENT.get()


@contextmanager
def read_snapshot() -> Iterator[Connection]:
    """Keep a multi-query matching read consistent during atomic schedule replacements."""
    existing = _CURRENT.get()
    if existing is not None:
        yield existing
        return
    with get_engine().connect().execution_options(isolation_level='REPEATABLE READ') as conn:
        with conn.begin():
            token = _CURRENT.set(conn)
            try:
                yield conn
            finally:
                _CURRENT.reset(token)

def json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, default=lambda x: x.isoformat() if isinstance(x, (date, datetime)) else str(x)))

def save_domain_record(namespace: str, record_id: str, payload: dict[str, Any]) -> None:
    if namespace in {'orders', 'invoices', 'payment_attempts', 'refunds', 'billing_ledger', 'outbox_events'}:
        raise ValueError('Use the typed transactional repository for this namespace')
    with transaction() as conn:
        stmt = insert(kv_records_table).values(namespace=namespace, record_id=record_id,
            payload_json=json_value(payload), updated_at=now())
        conn.execute(stmt.on_conflict_do_update(index_elements=['namespace', 'record_id'],
            set_={'payload_json': stmt.excluded.payload_json, 'updated_at': stmt.excluded.updated_at}))

def load_domain_record(namespace: str, record_id: str) -> dict[str, Any] | None:
    with transaction() as conn:
        return conn.execute(select(kv_records_table.c.payload_json).where(
            kv_records_table.c.namespace == namespace, kv_records_table.c.record_id == record_id)).scalar_one_or_none()

def list_domain_records(namespace: str) -> list[dict[str, Any]]:
    with transaction() as conn:
        return list(conn.execute(select(kv_records_table.c.payload_json).where(kv_records_table.c.namespace == namespace)).scalars())

def enqueue(conn: Connection, event_type: str, aggregate_key: str, payload: dict[str, Any], dedupe_key: str) -> str:
    event_id = str(uuid4())
    stmt = insert(outbox_table).values(id=event_id, created_at=now(), updated_at=now(), event_type=event_type,
        schema_version=1, aggregate_key=aggregate_key, payload=json_value(payload), dedupe_key=dedupe_key,
        available_at=now(), attempts=0)
    conn.execute(stmt.on_conflict_do_nothing(index_elements=['dedupe_key']))
    return event_id
