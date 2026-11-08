"""Baseline v1.4 schema and TD-001 storage/outbox/idempotency refinements (FIX-02).

Revision ID: 0001_v1_4_baseline_and_td001_fixes
Revises: None
Create Date: 2026-11-07
"""

from __future__ import annotations

from pathlib import Path
from alembic import op

revision = "0001_v14_baseline"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "FlexBridge_1_4_schema.sql"

TD001_REFINEMENTS_SQL = """
-- TD-001 Section 11 & 19: Allow files.sha256 to be NULL while PENDING_SCAN, mandatory when CLEAN
ALTER TABLE flexbridge.files ALTER COLUMN sha256 DROP NOT NULL;
ALTER TABLE flexbridge.files DROP CONSTRAINT IF EXISTS chk_files_clean_requires_sha256;
ALTER TABLE flexbridge.files ADD CONSTRAINT chk_files_clean_requires_sha256
    CHECK (scan_status <> 'CLEAN' OR (sha256 IS NOT NULL AND length(btrim(sha256)) = 64));

-- TD-001 Section 12 & 19: Outbox lease, fencing attempt counter, and retry columns
ALTER TABLE flexbridge.outbox_events ADD COLUMN IF NOT EXISTS claimed_by text;
ALTER TABLE flexbridge.outbox_events ADD COLUMN IF NOT EXISTS lease_until timestamptz;
ALTER TABLE flexbridge.outbox_events ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0;
"""


def upgrade() -> None:
    sql_text = SCHEMA_PATH.read_text(encoding="utf-8")
    import re
    sql_text = re.sub(r'^BEGIN;\s*', '', sql_text, count=1, flags=re.MULTILINE)
    sql_text = re.sub(r'COMMIT;\s*$', '', sql_text, count=1)
    op.get_bind().connection.driver_connection.execute(sql_text, prepare=False)
    op.execute(TD001_REFINEMENTS_SQL)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS flexbridge CASCADE;")
