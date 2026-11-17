"""Placement completion requests, two-sided closure, and immutable audit proofs (API-049 / CAP-022)."""
from alembic import op

revision = '0019_placement_completions'
down_revision = '0018_academic_decisions'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.placement_completion_requests (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      placement_id uuid NOT NULL REFERENCES flexbridge.placements(id),
      terms_id uuid NOT NULL REFERENCES flexbridge.placement_terms(id),
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      side text NOT NULL CHECK(side IN ('CANDIDATE','HOST','MENTOR','TEACHER')),
      decision text NOT NULL CHECK(decision IN ('REQUEST_COMPLETION','CONFIRM_COMPLETION','REJECT_COMPLETION')),
      status text NOT NULL CHECK(status IN ('PENDING_HOST','PENDING_CANDIDATE','COMPLETED','REJECTED','SUPERSEDED')),
      reason text,
      early_completion boolean NOT NULL DEFAULT false,
      logged_minutes integer NOT NULL DEFAULT 0 CHECK(logged_minutes >= 0),
      required_minutes integer NOT NULL DEFAULT 0 CHECK(required_minutes >= 0),
      basis_snapshot jsonb NOT NULL CHECK(jsonb_typeof(basis_snapshot)='object'),
      idempotency_key text NOT NULL,
      request_fingerprint text NOT NULL,
      receipt jsonb NOT NULL CHECK(jsonb_typeof(receipt)='object'),
      decided_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );

    CREATE INDEX idx_placement_completion_requests_placement
      ON flexbridge.placement_completion_requests(placement_id, status);

    CREATE UNIQUE INDEX uq_placement_completion_requests_idempotency
      ON flexbridge.placement_completion_requests(placement_id, idempotency_key);

    CREATE OR REPLACE FUNCTION flexbridge.guard_placement_start() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF TG_OP='INSERT' THEN
        IF NEW.status<>'PLANNED' OR NEW.academic_track OR NEW.enrollment_id IS NOT NULL
        THEN RAISE EXCEPTION 'new placement requires planned intake' USING ERRCODE='23514'; END IF;
      ELSE
        IF NEW.status='ACTIVE' AND OLD.status<>'ACTIVE' AND OLD.status<>'COMPLETION_REQUESTED' AND
          (OLD.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION') OR NOT placement_ready_for_start(NEW.id,NEW.current_terms_id)
            OR NOT EXISTS(SELECT 1 FROM placement_admission_events e WHERE e.placement_id=NEW.id AND e.terms_id=NEW.current_terms_id AND e.action='ACTIVATE'))
        THEN RAISE EXCEPTION 'placement start requires immutable admission proof' USING ERRCODE='23514'; END IF;
        IF ROW(NEW.application_id,NEW.offer_id,NEW.candidate_id,NEW.organization_id,NEW.start_date,NEW.end_date)
          IS DISTINCT FROM ROW(OLD.application_id,OLD.offer_id,OLD.candidate_id,OLD.organization_id,OLD.start_date,OLD.end_date)
        THEN RAISE EXCEPTION 'placement source and dates are immutable' USING ERRCODE='23514'; END IF;
        IF ROW(NEW.academic_track,NEW.enrollment_id) IS DISTINCT FROM ROW(OLD.academic_track,OLD.enrollment_id) AND
          (OLD.academic_track OR OLD.enrollment_id IS NOT NULL OR NOT NEW.academic_track
            OR OLD.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION') OR NOT EXISTS(SELECT 1 FROM placement_academic_bindings b
              WHERE b.placement_id=NEW.id AND b.origin='PUBLIC' AND b.enrollment_id=NEW.enrollment_id AND b.terms_id=NEW.current_terms_id))
        THEN RAISE EXCEPTION 'academic binding requires immutable admission proof' USING ERRCODE='23514'; END IF;
        IF NEW.current_terms_id IS DISTINCT FROM OLD.current_terms_id AND OLD.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION')
        THEN RAISE EXCEPTION 'active plan amendment requires a separate lifecycle' USING ERRCODE='23514'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    """)


def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS flexbridge.placement_completion_requests CASCADE;

    CREATE OR REPLACE FUNCTION flexbridge.guard_placement_start() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF TG_OP='INSERT' THEN
        IF NEW.status<>'PLANNED' OR NEW.academic_track OR NEW.enrollment_id IS NOT NULL
        THEN RAISE EXCEPTION 'new placement requires planned intake' USING ERRCODE='23514'; END IF;
      ELSE
        IF NEW.status='ACTIVE' AND OLD.status<>'ACTIVE' AND
          (OLD.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION') OR NOT placement_ready_for_start(NEW.id,NEW.current_terms_id)
            OR NOT EXISTS(SELECT 1 FROM placement_admission_events e WHERE e.placement_id=NEW.id AND e.terms_id=NEW.current_terms_id AND e.action='ACTIVATE'))
        THEN RAISE EXCEPTION 'placement start requires immutable admission proof' USING ERRCODE='23514'; END IF;
        IF ROW(NEW.application_id,NEW.offer_id,NEW.candidate_id,NEW.organization_id,NEW.start_date,NEW.end_date)
          IS DISTINCT FROM ROW(OLD.application_id,OLD.offer_id,OLD.candidate_id,OLD.organization_id,OLD.start_date,OLD.end_date)
        THEN RAISE EXCEPTION 'placement source and dates are immutable' USING ERRCODE='23514'; END IF;
        IF ROW(NEW.academic_track,NEW.enrollment_id) IS DISTINCT FROM ROW(OLD.academic_track,OLD.enrollment_id) AND
          (OLD.academic_track OR OLD.enrollment_id IS NOT NULL OR NOT NEW.academic_track
            OR OLD.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION') OR NOT EXISTS(SELECT 1 FROM placement_academic_bindings b
              WHERE b.placement_id=NEW.id AND b.origin='PUBLIC' AND b.enrollment_id=NEW.enrollment_id AND b.terms_id=NEW.current_terms_id))
        THEN RAISE EXCEPTION 'academic binding requires immutable admission proof' USING ERRCODE='23514'; END IF;
        IF NEW.current_terms_id IS DISTINCT FROM OLD.current_terms_id AND OLD.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION')
        THEN RAISE EXCEPTION 'active plan amendment requires a separate lifecycle' USING ERRCODE='23514'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    """)
