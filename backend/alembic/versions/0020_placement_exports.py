"""Placement report exports, short-lived informational reports, and audit tracking (API-052 / CAP-026)."""
from alembic import op

revision = '0020_placement_exports'
down_revision = '0019_placement_completions'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.placement_exports (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      placement_id uuid NOT NULL REFERENCES flexbridge.placements(id),
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      file_id uuid NOT NULL REFERENCES flexbridge.files(id),
      export_format text NOT NULL CHECK(export_format IN ('PDF','JSON')),
      summary_snapshot jsonb NOT NULL CHECK(jsonb_typeof(summary_snapshot)='object'),
      idempotency_key text NOT NULL,
      request_fingerprint text NOT NULL,
      receipt jsonb NOT NULL CHECK(jsonb_typeof(receipt)='object'),
      expires_at timestamptz NOT NULL
    );

    CREATE INDEX idx_placement_exports_placement
      ON flexbridge.placement_exports(placement_id, created_at DESC);

    CREATE UNIQUE INDEX uq_placement_exports_idempotency
      ON flexbridge.placement_exports(placement_id, idempotency_key);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS flexbridge.placement_exports CASCADE;")
