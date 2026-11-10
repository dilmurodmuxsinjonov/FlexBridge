"""Placement-wide nonofficial teacher academic conclusions and immutable DB-054 proofs (API-108 / CAP-024)."""
from alembic import op

revision = '0018_academic_decisions'
down_revision = '0017_feature_flag_administration'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.academic_decision_proofs (
      decision_id uuid PRIMARY KEY REFERENCES flexbridge.placement_decisions(id),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      origin text NOT NULL CHECK(origin IN ('PUBLIC','LEGACY_IMPORT')),
      initial_snapshot jsonb NOT NULL CHECK(jsonb_typeof(initial_snapshot)='object'),
      placement_id uuid REFERENCES flexbridge.placements(id),
      assignment_id uuid REFERENCES flexbridge.academic_assignments(id),
      terms_id uuid REFERENCES flexbridge.placement_terms(id),
      terms_version integer CHECK(terms_version IS NULL OR terms_version>0),
      actor_id uuid REFERENCES flexbridge.users(id),
      session_id uuid REFERENCES flexbridge.sessions(id),
      auth_version integer,
      teacher_grant_id uuid REFERENCES flexbridge.institution_role_grants(id),
      teacher_appointment_id uuid REFERENCES flexbridge.institution_appointments(id),
      teacher_consent_id uuid REFERENCES flexbridge.academic_assignment_consents(id),
      consent_snapshot jsonb,
      assignment_proof_snapshot jsonb,
      basis_snapshot jsonb,
      basis_digest text,
      audit_event_id uuid UNIQUE REFERENCES flexbridge.audit_events(id),
      idempotency_key text,
      request_fingerprint text,
      receipt jsonb,
      UNIQUE(actor_id,idempotency_key),
      CHECK((origin='PUBLIC'
        AND placement_id IS NOT NULL
        AND assignment_id IS NOT NULL
        AND terms_id IS NOT NULL
        AND terms_version IS NOT NULL AND terms_version>0
        AND actor_id IS NOT NULL
        AND session_id IS NOT NULL
        AND auth_version IS NOT NULL
        AND teacher_grant_id IS NOT NULL
        AND teacher_appointment_id IS NOT NULL
        AND teacher_consent_id IS NOT NULL
        AND consent_snapshot IS NOT NULL AND jsonb_typeof(consent_snapshot)='object'
        AND assignment_proof_snapshot IS NOT NULL AND jsonb_typeof(assignment_proof_snapshot)='object'
        AND basis_snapshot IS NOT NULL AND jsonb_typeof(basis_snapshot)='object'
        AND basis_digest IS NOT NULL AND basis_digest ~ '^[0-9a-f]{64}$'
        AND audit_event_id IS NOT NULL
        AND idempotency_key IS NOT NULL AND length(idempotency_key) BETWEEN 8 AND 128
        AND request_fingerprint IS NOT NULL AND request_fingerprint ~ '^[0-9a-f]{64}$'
        AND receipt IS NOT NULL AND jsonb_typeof(receipt)='object')
      OR (origin='LEGACY_IMPORT'
        AND placement_id IS NULL
        AND assignment_id IS NULL
        AND terms_id IS NULL
        AND terms_version IS NULL
        AND actor_id IS NULL
        AND session_id IS NULL
        AND auth_version IS NULL
        AND teacher_grant_id IS NULL
        AND teacher_appointment_id IS NULL
        AND teacher_consent_id IS NULL
        AND consent_snapshot IS NULL
        AND assignment_proof_snapshot IS NULL
        AND basis_snapshot IS NULL
        AND basis_digest IS NULL
        AND audit_event_id IS NULL
        AND idempotency_key IS NULL
        AND request_fingerprint IS NULL
        AND receipt IS NULL))
    );

    CREATE UNIQUE INDEX uq_academic_decision_proof_basis
      ON flexbridge.academic_decision_proofs(assignment_id,terms_id,basis_digest)
      WHERE origin='PUBLIC';

    CREATE FUNCTION flexbridge.placement_decision_snapshot(d flexbridge.placement_decisions) RETURNS jsonb
    LANGUAGE sql STABLE SET TimeZone TO 'UTC' SET search_path=pg_catalog,flexbridge AS $$
      SELECT to_jsonb(d)
    $$;

    CREATE FUNCTION flexbridge.academic_jsonb_snapshot(value anyelement) RETURNS jsonb
    LANGUAGE sql STABLE SET TimeZone TO 'UTC' SET search_path=pg_catalog,flexbridge AS $$
      SELECT to_jsonb(value)
    $$;

    CREATE FUNCTION flexbridge.academic_decision_digest(value jsonb) RETURNS text
    LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,flexbridge AS $$
      SELECT encode(sha256(convert_to(CAST(value AS text),'UTF8')),'hex')
    $$;

    -- Capture all existing DB-054 rows verbatim as LEGACY_IMPORT with no fabricated teacher/session/intent.
    INSERT INTO flexbridge.academic_decision_proofs(decision_id,origin,initial_snapshot)
      SELECT d.id,'LEGACY_IMPORT',flexbridge.placement_decision_snapshot(d)
      FROM flexbridge.placement_decisions d;

    CREATE FUNCTION flexbridge.academic_decision_basis(pid uuid,aid uuid) RETURNS jsonb
    LANGUAGE sql STABLE SET TimeZone TO 'UTC' SET search_path=pg_catalog,flexbridge AS $$
      SELECT jsonb_build_object(
        'placement_id',p.id,
        'academic_assignment_id',a.id,
        'terms_id',t.id,
        'version',t.version,
        'plan',jsonb_build_object(
          'terms',to_jsonb(t),
          'tasks',COALESCE((
            SELECT jsonb_agg(to_jsonb(pt) ORDER BY pt.code,pt.id)
            FROM plan_tasks pt WHERE pt.terms_id=t.id
          ),CAST('[]' AS jsonb))
        ),
        'assignment',jsonb_build_object(
          'academic_assignment',to_jsonb(a),
          'assignment_proof',to_jsonb(q),
          'academic_binding',to_jsonb(b),
          'supervision',to_jsonb(s),
          'supervision_origin',to_jsonb(so),
          'enrollment',to_jsonb(e),
          'agreement',to_jsonb(ag),
          'candidate_user_id',c.user_id
        ),
        'daily_logs',COALESCE(logs.items,CAST('[]' AS jsonb)),
        'log_count',COALESCE(logs.log_count,0),
        'submitted_count',COALESCE(logs.submitted_count,0),
        'reviewed_count',COALESCE(logs.reviewed_count,0),
        'needs_revision_count',COALESCE(logs.needs_revision_count,0),
        'pending_count',COALESCE(logs.log_count,0)-COALESCE(logs.reviewed_count,0)-COALESCE(logs.needs_revision_count,0),
        'academic_review_complete',(
          COALESCE(logs.log_count,0)>0
          AND COALESCE(logs.reviewed_count,0)=COALESCE(logs.log_count,0)
          AND COALESCE(logs.needs_revision_count,0)=0
        )
      )
      FROM placements p
      JOIN placement_terms t ON t.id=p.current_terms_id AND t.placement_id=p.id
      JOIN candidate_profiles c ON c.id=p.candidate_id
      JOIN academic_assignments a ON a.id=aid AND a.placement_id=p.id
      LEFT JOIN academic_assignment_proofs q ON q.assignment_id=a.id
      LEFT JOIN placement_academic_bindings b ON b.placement_id=p.id
      LEFT JOIN student_supervisions s ON s.id=a.supervision_id
      LEFT JOIN supervision_origins so ON so.supervision_id=s.id
      LEFT JOIN enrollments e ON e.id=s.enrollment_id
      LEFT JOIN institution_agreements ag ON ag.id=s.agreement_id
      LEFT JOIN LATERAL (
        SELECT
          jsonb_agg(
            jsonb_build_object(
              'daily_log',to_jsonb(l),
              'current_revision',to_jsonb(r),
              'reviews',rev_data.items,
              'category',CASE
                WHEN sub.is_submitted AND rev_data.public_reviewed_count=1
                  AND rev_data.public_needs_revision_count=0 AND rev_data.total_review_count=1 THEN 'REVIEWED'
                WHEN sub.is_submitted AND rev_data.public_needs_revision_count>=1
                  AND rev_data.public_reviewed_count=0 THEN 'NEEDS_REVISION'
                ELSE 'PENDING'
              END
            ) ORDER BY l.id
          ) AS items,
          CAST(count(*) AS integer) AS log_count,
          CAST(count(*) FILTER (WHERE sub.is_submitted) AS integer) AS submitted_count,
          CAST(count(*) FILTER (
            WHERE sub.is_submitted AND rev_data.public_reviewed_count=1
              AND rev_data.public_needs_revision_count=0 AND rev_data.total_review_count=1
          ) AS integer) AS reviewed_count,
          CAST(count(*) FILTER (
            WHERE sub.is_submitted AND rev_data.public_needs_revision_count>=1
              AND rev_data.public_reviewed_count=0
          ) AS integer) AS needs_revision_count
        FROM daily_logs l
        LEFT JOIN log_revisions r ON r.id=l.current_revision_id AND r.daily_log_id=l.id
        CROSS JOIN LATERAL (
          SELECT (
            r.id IS NOT NULL
            AND r.daily_log_id=l.id
            AND r.terms_id=t.id
            AND r.author_id=c.user_id
            AND r.status='SUBMITTED'
            AND r.submitted_at IS NOT NULL
            AND r.submitted_at<=clock_timestamp()
          ) AS is_submitted
        ) sub
        CROSS JOIN LATERAL (
          SELECT
            COALESCE(
              jsonb_agg(
                jsonb_build_object('review',to_jsonb(rv),'proof',to_jsonb(rp))
                ORDER BY rv.id
              ),
              CAST('[]' AS jsonb)
            ) AS items,
            CAST(count(*) AS integer) AS total_review_count,
            CAST(count(*) FILTER (
              WHERE rv.decision='REVIEWED'
                AND rv.decided_at<=clock_timestamp()
                AND rp.origin='PUBLIC'
                AND rp.terms_id=r.terms_id
                AND rp.actor_id=q.teacher_user_id
                AND rp.teacher_grant_id=q.teacher_grant_id
                AND rp.teacher_appointment_id=q.teacher_appointment_id
                AND rp.initial_snapshot=to_jsonb(rv)
                AND rp.revision_snapshot=to_jsonb(r)
                AND rp.assignment_proof_snapshot=to_jsonb(q)
                AND rp.receipt=to_jsonb(rv)
            ) AS integer) AS public_reviewed_count,
            CAST(count(*) FILTER (
              WHERE rv.decision='NEEDS_REVISION'
                AND rv.decided_at<=clock_timestamp()
                AND rp.origin='PUBLIC'
                AND rp.terms_id=r.terms_id
                AND rp.actor_id=q.teacher_user_id
                AND rp.teacher_grant_id=q.teacher_grant_id
                AND rp.teacher_appointment_id=q.teacher_appointment_id
                AND rp.initial_snapshot=to_jsonb(rv)
                AND rp.revision_snapshot=to_jsonb(r)
                AND rp.assignment_proof_snapshot=to_jsonb(q)
                AND rp.receipt=to_jsonb(rv)
            ) AS integer) AS public_needs_revision_count
          FROM academic_log_reviews rv
          LEFT JOIN academic_review_proofs rp ON rp.review_id=rv.id
          WHERE r.id IS NOT NULL
            AND rv.revision_id=r.id
            AND rv.academic_assignment_id=a.id
            AND rv.placement_id=p.id
        ) rev_data
        WHERE l.placement_id=p.id
      ) logs ON true
      WHERE p.id=pid
    $$;

    CREATE FUNCTION flexbridge.academic_decision_basis_current(did uuid) RETURNS boolean
    LANGUAGE sql STABLE SET TimeZone TO 'UTC' SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(
        SELECT 1
        FROM placement_decisions d
        JOIN academic_decision_proofs dp ON dp.decision_id=d.id
        JOIN placements p ON p.id=d.placement_id
        JOIN placement_terms t ON t.id=d.terms_id AND t.placement_id=p.id
        JOIN academic_assignments a ON a.id=dp.assignment_id AND a.placement_id=p.id
        JOIN academic_assignment_proofs q ON q.assignment_id=a.id
        JOIN academic_assignment_consents consent ON consent.id=dp.teacher_consent_id
        WHERE d.id=did
          AND dp.origin='PUBLIC'
          AND dp.placement_id=p.id
          AND dp.terms_id=t.id
          AND p.current_terms_id=t.id
          AND dp.terms_version=t.version
          AND d.side='TEACHER'
          AND d.decision IN ('ACADEMIC_REVIEW_COMPLETE','ACADEMIC_REVISION_REQUIRED')
          AND d.reason IS NOT NULL AND d.reason=btrim(d.reason)
          AND length(d.reason) BETWEEN 1 AND 2000
          AND consent.assignment_id=a.id
          AND consent.placement_id=p.id
          AND consent.terms_id=t.id
          AND consent.actor_id=dp.actor_id
          AND consent.teacher_grant_id=dp.teacher_grant_id
          AND consent.teacher_appointment_id=dp.teacher_appointment_id
          AND dp.initial_snapshot=to_jsonb(d)
          AND dp.receipt=to_jsonb(d)
          AND dp.consent_snapshot=to_jsonb(consent)
          AND dp.assignment_proof_snapshot=to_jsonb(q)
          AND dp.basis_snapshot=flexbridge.academic_decision_basis(p.id,a.id)
          AND dp.basis_digest=flexbridge.academic_decision_digest(dp.basis_snapshot)
          AND (d.decision='ACADEMIC_REVISION_REQUIRED'
            OR CAST(dp.basis_snapshot->>'academic_review_complete' AS boolean) IS TRUE)
      )
    $$;

    CREATE FUNCTION flexbridge.stamp_academic_decision_audit_event() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.action='ACADEMIC_DECISION_RECORDED' THEN
        NEW.scope_snapshot = (CASE
          WHEN NEW.scope_snapshot IS NOT NULL AND jsonb_typeof(NEW.scope_snapshot)='object'
          THEN NEW.scope_snapshot
          ELSE jsonb_build_object()
        END) || jsonb_build_object('_academic_decision_top_xid',CAST(pg_current_xact_id() AS text));
      END IF;
      RETURN NEW;
    END $$;

    CREATE TRIGGER stamp_academic_decision_audit_event BEFORE INSERT ON flexbridge.audit_events
      FOR EACH ROW WHEN (NEW.action='ACADEMIC_DECISION_RECORDED')
      EXECUTE FUNCTION flexbridge.stamp_academic_decision_audit_event();

    CREATE FUNCTION flexbridge.guard_placement_decision_row() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.side='TEACHER' THEN
        IF NEW.decision NOT IN ('ACADEMIC_REVIEW_COMPLETE','ACADEMIC_REVISION_REQUIRED')
           OR NEW.reason IS NULL OR NEW.reason<>btrim(NEW.reason)
           OR length(NEW.reason) NOT BETWEEN 1 AND 2000
           OR NEW.decided_at>clock_timestamp() THEN
          RAISE EXCEPTION 'teacher placement decision requires valid academic conclusion vocabulary and reason'
            USING ERRCODE='23514';
        END IF;
      ELSIF NEW.decision IN ('ACADEMIC_REVIEW_COMPLETE','ACADEMIC_REVISION_REQUIRED') THEN
        RAISE EXCEPTION 'academic conclusion vocabulary requires TEACHER side'
          USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;

    CREATE TRIGGER valid_placement_decision_row BEFORE INSERT ON flexbridge.placement_decisions
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_placement_decision_row();

    CREATE FUNCTION flexbridge.guard_academic_decision_proof() RETURNS trigger
    LANGUAGE plpgsql SET TimeZone TO 'UTC' SET search_path=pg_catalog,flexbridge AS $$
    DECLARE
      basis jsonb;
    BEGIN
      IF NEW.origin<>'PUBLIC' THEN
        RAISE EXCEPTION 'academic decision legacy set is closed' USING ERRCODE='23514';
      END IF;
      basis = flexbridge.academic_decision_basis(NEW.placement_id,NEW.assignment_id);
      IF basis IS NULL
         OR NEW.basis_snapshot IS DISTINCT FROM basis
         OR NEW.basis_digest IS DISTINCT FROM flexbridge.academic_decision_digest(basis) THEN
        RAISE EXCEPTION 'academic decision proof requires exact server basis snapshot and digest'
          USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS(
        SELECT 1
        FROM placement_decisions d
        JOIN placements p ON p.id=d.placement_id
        JOIN placement_terms t ON t.id=d.terms_id AND t.placement_id=p.id
        JOIN candidate_profiles c ON c.id=p.candidate_id
        JOIN academic_assignments a ON a.id=NEW.assignment_id AND a.placement_id=p.id
        JOIN academic_assignment_proofs q ON q.assignment_id=a.id
        JOIN placement_academic_bindings b ON b.placement_id=p.id
        JOIN student_supervisions s ON s.id=a.supervision_id
        JOIN institution_agreements agreement ON agreement.id=s.agreement_id
        JOIN academic_assignment_consents consent ON consent.id=NEW.teacher_consent_id
        WHERE d.id=NEW.decision_id
          AND NEW.placement_id=p.id
          AND NEW.terms_id=t.id
          AND p.current_terms_id=t.id
          AND NEW.terms_version=t.version
          AND p.status='ACTIVE'
          AND p.academic_track
          AND p.enrollment_id=b.enrollment_id
          AND a.supervision_id=b.supervision_id
          AND a.institution_id=b.institution_id
          AND d.actor_id=NEW.actor_id
          AND d.side='TEACHER'
          AND d.decision IN ('ACADEMIC_REVIEW_COMPLETE','ACADEMIC_REVISION_REQUIRED')
          AND d.reason IS NOT NULL AND d.reason=btrim(d.reason)
          AND length(d.reason) BETWEEN 1 AND 2000
          AND d.decided_at<=clock_timestamp()
          AND q.teacher_user_id=NEW.actor_id
          AND NEW.actor_id<>c.user_id
          AND q.teacher_grant_id=NEW.teacher_grant_id
          AND q.teacher_appointment_id=NEW.teacher_appointment_id
          AND consent.assignment_id=a.id
          AND consent.placement_id=p.id
          AND consent.terms_id=t.id
          AND consent.actor_id=NEW.actor_id
          AND consent.teacher_grant_id=NEW.teacher_grant_id
          AND consent.teacher_appointment_id=NEW.teacher_appointment_id
          AND (b.origin='LEGACY_IMPORT' OR (
            t.terms_snapshot->'academic_scope'=b.scope_snapshot
            AND b.scope_snapshot->>'agreement_id'=CAST(agreement.id AS text)
            AND CAST(b.scope_snapshot->>'agreement_version' AS integer)=agreement.version
          ))
          AND academic_teacher_current(a.id,t.id)
          AND placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
          AND NEW.initial_snapshot=to_jsonb(d)
          AND NEW.receipt=to_jsonb(d)
          AND NEW.consent_snapshot=to_jsonb(consent)
          AND NEW.assignment_proof_snapshot=to_jsonb(q)
          AND (d.decision='ACADEMIC_REVISION_REQUIRED'
            OR CAST(basis->>'academic_review_complete' AS boolean) IS TRUE)
      ) THEN
        RAISE EXCEPTION 'academic decision proof requires exact current teacher authority, consent and eligible basis'
          USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS(
        SELECT 1 FROM audit_events ae
        WHERE ae.id=NEW.audit_event_id
          AND ae.actor_id=NEW.actor_id
          AND ae.action='ACADEMIC_DECISION_RECORDED'
          AND ae.object_type='placement_decision'
          AND ae.object_key=CAST(NEW.decision_id AS text)
          AND ae.scope_snapshot->>'source' IN ('API-108','API108')
          AND COALESCE(ae.scope_snapshot->>'assignment_id',ae.scope_snapshot->>'academic_assignment_id')=CAST(NEW.assignment_id AS text)
          AND ae.scope_snapshot->>'terms_id'=CAST(NEW.terms_id AS text)
          AND ae.scope_snapshot->>'basis_digest'=NEW.basis_digest
          AND ae.scope_snapshot->>'_academic_decision_top_xid'=CAST(pg_current_xact_id() AS text)
      ) THEN
        RAISE EXCEPTION 'academic decision proof requires its same-transaction audit event'
          USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;

    CREATE TRIGGER valid_academic_decision_proof BEFORE INSERT ON flexbridge.academic_decision_proofs
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_academic_decision_proof();

    CREATE FUNCTION flexbridge.require_academic_decision_proof() RETURNS trigger
    LANGUAGE plpgsql SET TimeZone TO 'UTC' SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.side='TEACHER' OR NEW.decision IN ('ACADEMIC_REVIEW_COMPLETE','ACADEMIC_REVISION_REQUIRED') THEN
        IF NOT EXISTS(
          SELECT 1 FROM academic_decision_proofs dp
          WHERE dp.decision_id=NEW.id
            AND dp.origin='PUBLIC'
            AND dp.initial_snapshot=to_jsonb(NEW)
            AND dp.receipt=to_jsonb(NEW)
        ) THEN
          RAISE EXCEPTION 'academic decision requires immutable public proof' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NULL;
    END $$;

    CREATE CONSTRAINT TRIGGER academic_decision_requires_proof AFTER INSERT ON flexbridge.placement_decisions
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION flexbridge.require_academic_decision_proof();

    CREATE FUNCTION flexbridge.require_academic_decision_commit_state() RETURNS trigger
    LANGUAGE plpgsql SET TimeZone TO 'UTC' SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
         OR NOT academic_teacher_current(NEW.assignment_id,NEW.terms_id)
         OR NOT academic_decision_basis_current(NEW.decision_id)
         OR NOT EXISTS(
           SELECT 1 FROM placements p
           JOIN placement_academic_bindings b ON b.placement_id=p.id
           JOIN student_supervisions s ON s.id=b.supervision_id
           JOIN institution_agreements agreement ON agreement.id=s.agreement_id
           JOIN placement_terms t ON t.id=p.current_terms_id AND t.placement_id=p.id
           WHERE p.id=NEW.placement_id
             AND p.status='ACTIVE'
             AND p.academic_track
             AND p.current_terms_id=NEW.terms_id
             AND t.version=NEW.terms_version
             AND academic_supervision_current(s.id,p.candidate_id)
             AND (b.origin='LEGACY_IMPORT' OR (
               t.terms_snapshot->'academic_scope'=b.scope_snapshot
               AND b.scope_snapshot->>'agreement_id'=CAST(agreement.id AS text)
               AND CAST(b.scope_snapshot->>'agreement_version' AS integer)=agreement.version
             ))
         ) THEN
        RAISE EXCEPTION 'academic decision requires current teacher authority and unchanged basis at commit'
          USING ERRCODE='23514';
      END IF;
      RETURN NULL;
    END $$;

    CREATE CONSTRAINT TRIGGER academic_decision_current_at_commit AFTER INSERT ON flexbridge.academic_decision_proofs
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION flexbridge.require_academic_decision_commit_state();

    CREATE TRIGGER immutable_placement_decisions BEFORE UPDATE OR DELETE ON flexbridge.placement_decisions
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();

    CREATE TRIGGER immutable_academic_decision_proofs BEFORE UPDATE OR DELETE ON flexbridge.academic_decision_proofs
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    """)


def downgrade():
    raise RuntimeError('Academic decision history needs a reviewed data-preserving rollback plan')
