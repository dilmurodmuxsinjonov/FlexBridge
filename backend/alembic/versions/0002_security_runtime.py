"""Durable operational state; business invariants remain in the canonical schema."""
from alembic import op

revision = '0002_security_runtime'
down_revision = '0001_v14_baseline'
branch_labels = depends_on = None

def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.circuit_breaker_state (
      key text PRIMARY KEY, state text NOT NULL CHECK (state IN ('OPEN','CLOSED')),
      incident_id text, reason_code text, tripped_by text, tripped_at timestamptz,
      updated_at timestamptz NOT NULL DEFAULT now());
    INSERT INTO flexbridge.circuit_breaker_state(key,state) VALUES ('P1_FINANCE','CLOSED');
    CREATE TABLE flexbridge.domain_records (
      namespace text NOT NULL, record_id text NOT NULL, payload_json jsonb NOT NULL,
      updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(namespace,record_id));
    ALTER TABLE flexbridge.outbox_events ADD COLUMN claim_token uuid;
    ALTER TABLE flexbridge.files ADD COLUMN object_version text;
    ALTER TABLE flexbridge.files ADD COLUMN scan_error text;
    ALTER TABLE flexbridge.files ADD COLUMN scanned_at timestamptz;
    ALTER TABLE flexbridge.files ADD CONSTRAINT chk_scan_status CHECK
      (scan_status IN ('PENDING_SCAN','SCANNING','CLEAN','QUARANTINED','ERROR'));
    ALTER TABLE flexbridge.files ADD CONSTRAINT chk_clean_stored_object CHECK
      (scan_status <> 'CLEAN' OR (object_version IS NOT NULL AND scanned_at IS NOT NULL AND storage_key LIKE 'private/%'));
    ALTER TABLE flexbridge.refunds ADD CONSTRAINT chk_refund_approval_proof CHECK
      (status NOT IN ('APPROVED','REFUNDED') OR (approver_id IS NOT NULL AND second_approver_id IS NOT NULL));
    ALTER TABLE flexbridge.billing_ledger ADD CONSTRAINT chk_nonzero_ledger CHECK (amount <> 0);
    CREATE UNIQUE INDEX uq_entitlement_order ON flexbridge.service_entitlements(order_id) WHERE order_id IS NOT NULL;
    CREATE INDEX ix_pending_outbox ON flexbridge.outbox_events(available_at,id) WHERE processed_at IS NULL;
    ALTER TABLE flexbridge.availability_rules ADD COLUMN is_active boolean NOT NULL DEFAULT true;
    ALTER TABLE flexbridge.availability_rules ADD CONSTRAINT excl_availability_rules_no_overlap EXCLUDE USING gist
      (candidate_id WITH =, weekday WITH =, minute_range WITH &&,
       daterange(valid_from,COALESCE(valid_to,'infinity'::date),'[]') WITH &&) WHERE (is_active);
    ALTER TABLE flexbridge.availability_exceptions ADD CONSTRAINT excl_availability_exceptions_no_overlap EXCLUDE USING gist
      (candidate_id WITH =,local_date WITH =,minute_range WITH &&);
    ALTER TABLE flexbridge.opportunity_shifts ADD CONSTRAINT excl_opportunity_shifts_no_overlap EXCLUDE USING gist
      (revision_id WITH =,group_code WITH =,weekday WITH =,minute_range WITH &&);
    -- Trigger functions must work under the API's ordinary public search_path too.
    DO $$ DECLARE f record; BEGIN
      FOR f IN SELECT p.oid::regprocedure AS signature FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
               WHERE n.nspname='flexbridge'
      LOOP EXECUTE format('ALTER FUNCTION %s SET search_path = pg_catalog, flexbridge',f.signature); END LOOP;
    END $$;
    CREATE OR REPLACE FUNCTION flexbridge.fn_guard_log_revisions() RETURNS trigger
    LANGUAGE plpgsql SET search_path = pg_catalog, flexbridge AS $$ BEGIN
      IF TG_OP = 'DELETE' OR OLD.status <> 'DRAFT' THEN
        RAISE EXCEPTION 'Submitted revisions are immutable; create a new revision' USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END $$;
    """)

def downgrade():
    raise RuntimeError('Use a reviewed forward recovery migration; security records must not be silently deleted')
