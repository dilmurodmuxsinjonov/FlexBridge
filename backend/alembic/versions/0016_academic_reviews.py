"""Keep academic feedback immutable, revision-specific and independently attributable."""
from alembic import op

revision = '0016_academic_reviews'
down_revision = '0015_academic_admission'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.academic_review_proofs (
      review_id uuid PRIMARY KEY REFERENCES flexbridge.academic_log_reviews(id),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      origin text NOT NULL CHECK(origin IN ('PUBLIC','LEGACY_IMPORT')),
      initial_snapshot jsonb NOT NULL CHECK(jsonb_typeof(initial_snapshot)='object'),
      terms_id uuid REFERENCES flexbridge.placement_terms(id),
      actor_id uuid REFERENCES flexbridge.users(id),
      session_id uuid REFERENCES flexbridge.sessions(id),auth_version integer,
      teacher_grant_id uuid REFERENCES flexbridge.institution_role_grants(id),
      teacher_appointment_id uuid REFERENCES flexbridge.institution_appointments(id),
      assignment_proof_snapshot jsonb,revision_snapshot jsonb,
      idempotency_key text,request_fingerprint text,receipt jsonb,
      UNIQUE(actor_id,idempotency_key),
      CHECK((origin='PUBLIC' AND terms_id IS NOT NULL AND actor_id IS NOT NULL
        AND session_id IS NOT NULL AND auth_version IS NOT NULL AND teacher_grant_id IS NOT NULL
        AND teacher_appointment_id IS NOT NULL AND jsonb_typeof(assignment_proof_snapshot)='object'
        AND assignment_proof_snapshot IS NOT NULL AND revision_snapshot IS NOT NULL
        AND jsonb_typeof(revision_snapshot)='object' AND length(idempotency_key) BETWEEN 8 AND 128
        AND idempotency_key IS NOT NULL AND request_fingerprint ~ '^[0-9a-f]{64}$'
        AND request_fingerprint IS NOT NULL AND receipt IS NOT NULL AND jsonb_typeof(receipt)='object')
        OR (origin='LEGACY_IMPORT' AND terms_id IS NULL AND actor_id IS NULL AND session_id IS NULL
        AND auth_version IS NULL AND teacher_grant_id IS NULL AND teacher_appointment_id IS NULL
        AND assignment_proof_snapshot IS NULL AND revision_snapshot IS NULL AND idempotency_key IS NULL
        AND request_fingerprint IS NULL AND receipt IS NULL))
    );
    -- Preserve exactly what existed; do not manufacture historical teacher/session consent.
    INSERT INTO flexbridge.academic_review_proofs(review_id,origin,initial_snapshot)
      SELECT id,'LEGACY_IMPORT',to_jsonb(r) FROM flexbridge.academic_log_reviews r;

    CREATE FUNCTION flexbridge.guard_academic_review_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.origin<>'PUBLIC' THEN
        RAISE EXCEPTION 'academic review legacy set is closed' USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS(SELECT 1 FROM academic_log_reviews review
        JOIN log_revisions r ON r.id=review.revision_id JOIN daily_logs l ON l.id=r.daily_log_id
        JOIN placements p ON p.id=l.placement_id JOIN placement_terms t ON t.id=r.terms_id
        JOIN candidate_profiles c ON c.id=p.candidate_id
        JOIN academic_assignments a ON a.id=review.academic_assignment_id
        JOIN academic_assignment_proofs q ON q.assignment_id=a.id
        JOIN placement_academic_bindings b ON b.placement_id=p.id
        JOIN placement_terms current_terms ON current_terms.id=p.current_terms_id
        WHERE review.id=NEW.review_id AND review.placement_id=p.id AND a.placement_id=p.id
          AND t.placement_id=p.id AND r.terms_id=NEW.terms_id AND p.status='ACTIVE'
          AND r.status='SUBMITTED' AND r.submitted_at<=clock_timestamp() AND r.author_id=c.user_id
          AND review.decision IN ('REVIEWED','NEEDS_REVISION') AND review.decided_at<=clock_timestamp()
          AND q.teacher_user_id=NEW.actor_id AND NEW.actor_id<>c.user_id
          AND q.teacher_grant_id=NEW.teacher_grant_id AND q.teacher_appointment_id=NEW.teacher_appointment_id
          AND academic_teacher_current(a.id,r.terms_id)
          AND EXISTS(SELECT 1 FROM academic_assignment_consents consent WHERE consent.assignment_id=a.id
            AND consent.terms_id=r.terms_id AND consent.actor_id=NEW.actor_id
            AND consent.teacher_grant_id=NEW.teacher_grant_id AND consent.teacher_appointment_id=NEW.teacher_appointment_id)
          AND (b.origin='LEGACY_IMPORT' OR current_terms.terms_snapshot->'academic_scope'=b.scope_snapshot)
          AND placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
          AND NEW.initial_snapshot=to_jsonb(review) AND NEW.revision_snapshot=to_jsonb(r)
          AND NEW.assignment_proof_snapshot=to_jsonb(q)
          AND NEW.receipt=to_jsonb(review))
      THEN RAISE EXCEPTION 'academic review requires exact current teacher and submitted revision proof'
        USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_academic_review_proof BEFORE INSERT ON flexbridge.academic_review_proofs
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_academic_review_proof();
    CREATE FUNCTION flexbridge.require_academic_review_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM academic_review_proofs WHERE review_id=NEW.id) THEN
        RAISE EXCEPTION 'academic review requires immutable proof' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER academic_review_requires_proof AFTER INSERT ON flexbridge.academic_log_reviews
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION flexbridge.require_academic_review_proof();
    CREATE TRIGGER immutable_academic_reviews BEFORE UPDATE OR DELETE ON flexbridge.academic_log_reviews
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_academic_review_proofs BEFORE UPDATE OR DELETE ON flexbridge.academic_review_proofs
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    """)


def downgrade():
    raise RuntimeError('Academic review history needs a reviewed data-preserving rollback plan')
