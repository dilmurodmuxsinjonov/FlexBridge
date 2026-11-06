"""Alembic migration environment connected to FlexBridge canonical metadata."""

from __future__ import annotations

from app.db.storage import get_database_url, get_engine, metadata

target_metadata = metadata


def run_migrations_offline() -> None:
    """Provide canonical database URL and metadata for offline migration inspection."""
    _ = get_database_url()


def run_migrations_online() -> None:
    """Ensure canonical schema is bound and created on the active engine."""
    engine = get_engine()
    target_metadata.create_all(engine)
