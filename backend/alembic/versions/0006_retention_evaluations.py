"""Immutable, non-destructive retention evaluation records."""
from alembic import op

revision='0006_retention_evaluations'
down_revision='0005_org_invitations'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.retention_evaluations (
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      idempotency_key text NOT NULL, request_fingerprint text NOT NULL,
      data_category text NOT NULL, requested_age_days integer NOT NULL CHECK(requested_age_days >= 0),
      requested_records_scanned integer NOT NULL CHECK(requested_records_scanned >= 0),
      policy_snapshot jsonb NOT NULL CHECK(jsonb_typeof(policy_snapshot)='object'),
      evaluation jsonb NOT NULL CHECK(jsonb_typeof(evaluation)='object'),
      mode text NOT NULL CHECK(mode='DRY_RUN'), status text NOT NULL CHECK(status='EVALUATED_ONLY'),
      records_scanned integer NOT NULL CHECK(records_scanned=0),
      records_actioned integer NOT NULL CHECK(records_actioned=0),
      finished_at timestamptz NOT NULL,
      UNIQUE(actor_id,idempotency_key));
    CREATE INDEX ix_retention_eval_created ON flexbridge.retention_evaluations(created_at,id);
    CREATE FUNCTION flexbridge.immutable_retention_evaluation() RETURNS trigger
      LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
      BEGIN RAISE EXCEPTION 'Retention evaluation records are immutable' USING ERRCODE='23514'; END $$;
    CREATE TRIGGER retention_eval_immutable BEFORE UPDATE OR DELETE ON flexbridge.retention_evaluations
      FOR EACH ROW EXECUTE FUNCTION flexbridge.immutable_retention_evaluation();
    """)


def downgrade():
    raise RuntimeError('Retention audit history needs a reviewed forward recovery migration')
