"""SQLAlchemy 2.0 persistent database storage engine for FlexBridge R1 (FIX-02, R-03, REV-002).

Provides cross-process, restart-safe SQL persistence for all 94 canonical 1.4 tables,
users, hashed-token sessions, circuit-breaker state, idempotency keys, payment events,
orders, invoices, entitlements, and audit records.
Resolves `FLEXBRIDGE_DATABASE_URL` or `DATABASE_URL` when set, defaulting to a local
WAL-enabled SQLite database at `backend/.data/flexbridge_r1.sqlite3`.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, TypeDecorator, create_engine, event, select
from sqlalchemy.engine import Engine

DATA_DIR = Path(__file__).resolve().parents[2] / ".data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SQLITE_URL = f"sqlite:///{(DATA_DIR / 'flexbridge_r1.sqlite3').as_posix()}"
MODEL_JSON_PATH = Path(__file__).resolve().parents[3] / "specs" / "v1_4" / "FlexBridge_model_1_4.json"


def get_database_url() -> str:
    """Resolve database URL from FLEXBRIDGE_DATABASE_URL, DATABASE_URL, or default SQLite path."""
    return (
        os.environ.get("FLEXBRIDGE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or DEFAULT_SQLITE_URL
    )


class HashedSessionIdType(TypeDecorator):
    """Stores only the SHA-256 digest of a bearer session token in SQL while allowing transparent lookup."""

    impl = String(128)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        token_str = str(value)
        if token_str.startswith("sha256:"):
            return token_str
        return "sha256:" + hashlib.sha256(token_str.encode("utf-8")).hexdigest()

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return str(value)


metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("display_name", String(255), nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("status", String(32), nullable=False, default="ACTIVE"),
    Column("adult_declared_at", String(64), nullable=False),
    Column("roles_json", Text, nullable=False),
    Column("totp_enabled", Integer, nullable=False, default=0),
    Column("totp_secret", String(128), nullable=True),
    Column("created_at", String(64), nullable=False),
)

sessions_table = Table(
    "sessions",
    metadata,
    Column("session_id", HashedSessionIdType(), primary_key=True),
    Column("token_digest", String(128), nullable=False, index=True),
    Column("user_id", String(64), nullable=False, index=True),
    Column("status", String(32), nullable=False, default="ACTIVE"),
    Column("roles_json", Text, nullable=False),
    Column("created_at", String(64), nullable=False),
    Column("expires_at", String(64), nullable=False),
    Column("revoked_at", String(64), nullable=True),
    Column("revoked_by", String(64), nullable=True),
    Column("revoke_reason", Text, nullable=True),
)

circuit_breaker_table = Table(
    "circuit_breaker_state",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("state", String(32), nullable=False),
    Column("incident_id", String(128), nullable=True),
    Column("reason_code", String(128), nullable=True),
    Column("tripped_by", String(128), nullable=True),
    Column("tripped_at", String(64), nullable=True),
    Column("updated_at", String(64), nullable=False),
)

kv_records_table = Table(
    "domain_records",
    metadata,
    Column("namespace", String(64), primary_key=True),
    Column("record_id", String(128), primary_key=True),
    Column("payload_json", Text, nullable=False),
    Column("updated_at", String(64), nullable=False),
)


def _register_canonical_94_tables() -> None:
    """Register all 94 canonical 1.4 tables from FlexBridge_model_1_4.json in SQLAlchemy metadata."""
    if not MODEL_JSON_PATH.exists():
        return
    raw_model = json.loads(MODEL_JSON_PATH.read_text(encoding="utf-8"))
    for tbl in raw_model.get("tables", []):
        table_name = tbl["name"]
        if table_name in metadata.tables:
            continue
        cols: list[Column[Any]] = []
        fields = tbl.get("fields", [])
        has_pk = any(bool(f.get("pk")) for f in fields)
        for idx, fld in enumerate(fields):
            col_name = fld["name"]
            is_pk = bool(fld.get("pk")) or (not has_pk and idx == 0)
            col_type = Integer if fld.get("type") in ("integer", "bigint", "smallint") else Text
            if is_pk and col_type is Text:
                col_type = String(128)
            cols.append(
                Column(
                    col_name,
                    col_type,
                    primary_key=is_pk,
                    nullable=False if is_pk else bool(fld.get("nullable", True)),
                )
            )
        Table(table_name, metadata, *cols)


_register_canonical_94_tables()

_ENGINE: Engine | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        url = get_database_url()
        connect_args = {"check_same_thread": False, "timeout": 10.0} if url.startswith("sqlite") else {}
        _ENGINE = create_engine(url, future=True, connect_args=connect_args)
        if url.startswith("sqlite"):
            @event.listens_for(_ENGINE, "connect")
            def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.execute("PRAGMA foreign_keys=ON;")
                cursor.close()
        metadata.create_all(_ENGINE)
    return _ENGINE


def init_storage() -> Engine:
    """Initialize engine and ensure all canonical tables exist."""
    return get_engine()


def save_domain_record(namespace: str, record_id: str, payload: dict[str, Any]) -> None:
    engine = get_engine()
    now = datetime.now(timezone.utc).isoformat()
    payload_str = json.dumps(payload, ensure_ascii=False, default=str)
    with engine.begin() as conn:
        existing = conn.execute(
            select(kv_records_table.c.record_id).where(
                kv_records_table.c.namespace == namespace,
                kv_records_table.c.record_id == record_id,
            )
        ).first()
        if existing:
            conn.execute(
                kv_records_table.update()
                .where(
                    kv_records_table.c.namespace == namespace,
                    kv_records_table.c.record_id == record_id,
                )
                .values(payload_json=payload_str, updated_at=now)
            )
        else:
            conn.execute(
                kv_records_table.insert().values(
                    namespace=namespace,
                    record_id=record_id,
                    payload_json=payload_str,
                    updated_at=now,
                )
            )


def load_domain_record(namespace: str, record_id: str) -> dict[str, Any] | None:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(kv_records_table.c.payload_json).where(
                kv_records_table.c.namespace == namespace,
                kv_records_table.c.record_id == record_id,
            )
        ).first()
        if not row:
            return None
        return json.loads(row[0])


def list_domain_records(namespace: str) -> list[dict[str, Any]]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(kv_records_table.c.payload_json).where(
                kv_records_table.c.namespace == namespace
            )
        ).fetchall()
        return [json.loads(r[0]) for r in rows]
