"""Preserve enrollment imports; require immutable proof for new verified state."""
from alembic import op

revision = '0013_enrollment_verification'
down_revision = '0012_file_storage_versions'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE flexbridge.enrollment_origins (
      enrollment_id uuid PRIMARY KEY REFERENCES flexbridge.enrollments(id),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      origin text NOT NULL CHECK(origin IN ('PUBLIC','LEGACY_IMPORT')),
      candidate_id uuid NOT NULL REFERENCES flexbridge.candidate_profiles(id),
      institution_id uuid NOT NULL REFERENCES flexbridge.institutions(id),
      actor_user_id uuid NOT NULL REFERENCES flexbridge.users(id),
      case_id uuid UNIQUE REFERENCES flexbridge.verification_cases(id),
      initial_snapshot jsonb NOT NULL CHECK(jsonb_typeof(initial_snapshot)='object'),
      idempotency_key text,
      request_fingerprint text,
      UNIQUE(actor_user_id,idempotency_key),
      FOREIGN KEY(enrollment_id,institution_id) REFERENCES flexbridge.enrollments(id,institution_id),
      CHECK((origin='PUBLIC' AND case_id IS NOT NULL AND length(idempotency_key) BETWEEN 8 AND 128
        AND request_fingerprint ~ '^[0-9a-f]{64}$' AND idempotency_key IS NOT NULL AND request_fingerprint IS NOT NULL)
        OR (origin='LEGACY_IMPORT' AND case_id IS NULL AND idempotency_key IS NULL AND request_fingerprint IS NULL))
    );
    INSERT INTO flexbridge.enrollment_origins(enrollment_id,origin,candidate_id,institution_id,actor_user_id,initial_snapshot)
      SELECT e.id,'LEGACY_IMPORT',e.candidate_id,e.institution_id,p.user_id,to_jsonb(e)
      FROM flexbridge.enrollments e JOIN flexbridge.candidate_profiles p ON p.id=e.candidate_id;

    CREATE TABLE flexbridge.enrollment_submissions (
      case_id uuid NOT NULL REFERENCES flexbridge.enrollment_origins(case_id),
      revision integer NOT NULL CHECK(revision>0),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      submitted_by_id uuid NOT NULL REFERENCES flexbridge.users(id),
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      auth_version integer NOT NULL,
      program text NOT NULL CHECK(length(btrim(program)) BETWEEN 1 AND 250),
      start_date date NOT NULL,
      end_date date CHECK(end_date IS NULL OR end_date>=start_date),
      student_ref_digest text CHECK(student_ref_digest IS NULL OR student_ref_digest ~ '^[0-9a-f]{64}$'),
      evidence_note text NOT NULL CHECK(length(evidence_note)<=4000),
      file_ids jsonb NOT NULL CHECK(jsonb_typeof(file_ids)='array' AND jsonb_array_length(file_ids)<=5),
      file_snapshots jsonb NOT NULL CHECK(jsonb_typeof(file_snapshots)='object'),
      PRIMARY KEY(case_id,revision)
    );
    CREATE TABLE flexbridge.enrollment_events (
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      enrollment_id uuid NOT NULL REFERENCES flexbridge.enrollment_origins(enrollment_id),
      case_id uuid REFERENCES flexbridge.enrollment_origins(case_id),
      revision integer CHECK(revision>0),
      action text NOT NULL CHECK(action IN ('CLAIM','APPROVE','REJECT','NEEDS_INFO','END','WITHDRAW')),
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),
      auth_version integer NOT NULL,
      platform_grant_id uuid REFERENCES flexbridge.platform_role_grants(id),
      reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 15 AND 2000),
      idempotency_key text,
      request_fingerprint text,
      receipt jsonb NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(receipt)='object'),
      FOREIGN KEY(case_id,revision) REFERENCES flexbridge.enrollment_submissions(case_id,revision),
      CHECK((action IN ('END','WITHDRAW') AND idempotency_key IS NOT NULL
        AND length(idempotency_key) BETWEEN 8 AND 128 AND request_fingerprint IS NOT NULL
        AND request_fingerprint ~ '^[0-9a-f]{64}$' AND platform_grant_id IS NULL)
        OR (action IN ('CLAIM','APPROVE','REJECT','NEEDS_INFO') AND platform_grant_id IS NOT NULL
          AND case_id IS NOT NULL AND revision IS NOT NULL AND idempotency_key IS NULL AND request_fingerprint IS NULL)),
      UNIQUE(actor_id,idempotency_key)
    );
    CREATE UNIQUE INDEX uq_enrollment_revision_decision ON flexbridge.enrollment_events(case_id,revision)
      WHERE action IN ('APPROVE','REJECT','NEEDS_INFO');
    CREATE UNIQUE INDEX uq_enrollment_revision_claim ON flexbridge.enrollment_events(case_id,revision) WHERE action='CLAIM';
    CREATE UNIQUE INDEX uq_enrollment_terminal_event ON flexbridge.enrollment_events(enrollment_id) WHERE action IN ('END','WITHDRAW');
    CREATE INDEX ix_enrollment_origin_candidate ON flexbridge.enrollment_origins(candidate_id,enrollment_id);

    CREATE TRIGGER immutable_enrollment_origins BEFORE UPDATE OR DELETE ON flexbridge.enrollment_origins
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_enrollment_submissions BEFORE UPDATE OR DELETE ON flexbridge.enrollment_submissions
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_enrollment_events BEFORE UPDATE OR DELETE ON flexbridge.enrollment_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();

    CREATE FUNCTION flexbridge.enrollment_actor_current(actor uuid,sid uuid,version integer,need_mfa boolean)
    RETURNS boolean LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM users u JOIN sessions s ON s.user_id=u.id
        WHERE u.id=actor AND u.status='ACTIVE' AND u.auth_version=version AND s.id=sid
          AND s.auth_version=u.auth_version AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()
          AND (s.assurance='MFA' OR (NOT need_mfa AND NOT institution_sensitive_account(u.id))))
    $$;

    CREATE FUNCTION flexbridge.guard_enrollment_origin() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.origin<>'PUBLIC' OR NOT EXISTS(SELECT 1 FROM enrollments e
        JOIN candidate_profiles p ON p.id=e.candidate_id JOIN verification_cases c ON c.id=NEW.case_id
        WHERE e.id=NEW.enrollment_id AND e.candidate_id=NEW.candidate_id AND e.institution_id=NEW.institution_id
          AND p.user_id=NEW.actor_user_id AND e.status IN ('DECLARED','PENDING')
          AND e.verification_case_id=c.id AND c.enrollment_id=e.id AND c.requester_id=p.user_id
          AND c.kind='ENROLLMENT' AND c.status IN ('DRAFT','PENDING') AND c.current_revision=1) THEN
        RAISE EXCEPTION 'Enrollment origin must be a new own public request; legacy set is closed' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_enrollment_origin BEFORE INSERT ON flexbridge.enrollment_origins
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_enrollment_origin();

    CREATE FUNCTION flexbridge.enrollment_files_match(cid uuid,rev integer) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM enrollment_submissions v JOIN enrollment_origins o ON o.case_id=v.case_id
        WHERE v.case_id=cid AND v.revision=rev AND jsonb_array_length(v.file_ids)>0
          AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements_text(v.file_ids) requested(id)
            LEFT JOIN files f ON f.id=requested.id::uuid
            WHERE f.id IS NULL OR f.owner_user_id<>o.actor_user_id OR f.scan_status<>'CLEAN'
              OR f.deleted_at IS NOT NULL OR f.mime_type<>'application/pdf' OR f.storage_version_id IS NULL
              OR v.file_snapshots->requested.id IS DISTINCT FROM jsonb_build_object(
                'sha256',f.sha256,'object_version',f.object_version,'storage_key',f.storage_key,'byte_size',f.byte_size,
                'storage_bucket',f.storage_bucket,'storage_version_id',f.storage_version_id,'storage_etag',f.storage_etag)))
    $$;

    CREATE FUNCTION flexbridge.guard_enrollment_submission() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE o enrollment_origins%ROWTYPE; c verification_cases%ROWTYPE; fid uuid; f files%ROWTYPE;
    BEGIN
      SELECT * INTO o FROM enrollment_origins WHERE case_id=NEW.case_id;
      SELECT * INTO c FROM verification_cases WHERE id=NEW.case_id;
      IF o.origin IS DISTINCT FROM 'PUBLIC' OR NEW.submitted_by_id IS DISTINCT FROM o.actor_user_id
        OR NEW.revision NOT BETWEEN c.current_revision AND c.current_revision+1
        OR c.status NOT IN ('DRAFT','PENDING','NEEDS_INFO','REJECTED')
        OR NOT enrollment_actor_current(NEW.submitted_by_id,NEW.session_id,NEW.auth_version,false) THEN
        RAISE EXCEPTION 'Enrollment submission authority or revision mismatch' USING ERRCODE='23514';
      END IF;
      IF jsonb_typeof(NEW.file_ids) IS DISTINCT FROM 'array' OR jsonb_typeof(NEW.file_snapshots) IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'Enrollment evidence shape invalid' USING ERRCODE='23514';
      END IF;
      IF jsonb_array_length(NEW.file_ids)<>(SELECT count(DISTINCT value) FROM jsonb_array_elements_text(NEW.file_ids))
        OR jsonb_array_length(NEW.file_ids)<>(SELECT count(*) FROM jsonb_object_keys(NEW.file_snapshots))
        OR (jsonb_array_length(NEW.file_ids)>0 AND length(btrim(NEW.evidence_note))<15) THEN
        RAISE EXCEPTION 'Enrollment evidence set invalid' USING ERRCODE='23514';
      END IF;
      FOR fid IN SELECT value::uuid FROM jsonb_array_elements_text(NEW.file_ids) ORDER BY value LOOP
        SELECT * INTO f FROM files WHERE id=fid FOR SHARE;
        IF f.id IS NULL OR f.owner_user_id<>o.actor_user_id OR f.scan_status<>'CLEAN'
          OR f.deleted_at IS NOT NULL OR f.mime_type<>'application/pdf' OR f.storage_version_id IS NULL
          OR NEW.file_snapshots->fid::text IS DISTINCT FROM jsonb_build_object(
            'sha256',f.sha256,'object_version',f.object_version,'storage_key',f.storage_key,'byte_size',f.byte_size,
            'storage_bucket',f.storage_bucket,'storage_version_id',f.storage_version_id,'storage_etag',f.storage_etag) THEN
          RAISE EXCEPTION 'Enrollment evidence is not current owned CLEAN pinned material' USING ERRCODE='23514';
        END IF;
      END LOOP;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_enrollment_submission BEFORE INSERT ON flexbridge.enrollment_submissions
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_enrollment_submission();

    CREATE FUNCTION flexbridge.guard_enrollment_event() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE o enrollment_origins%ROWTYPE; c verification_cases%ROWTYPE; e enrollments%ROWTYPE;
    BEGIN
      SELECT * INTO o FROM enrollment_origins WHERE enrollment_id=NEW.enrollment_id;
      SELECT * INTO e FROM enrollments WHERE id=NEW.enrollment_id;
      SELECT * INTO c FROM verification_cases WHERE id=o.case_id;
      IF o.enrollment_id IS NULL OR NEW.case_id IS DISTINCT FROM o.case_id
        OR (o.origin='PUBLIC' AND NEW.revision IS DISTINCT FROM c.current_revision)
        OR (o.origin='LEGACY_IMPORT' AND NEW.revision IS NOT NULL) THEN
        RAISE EXCEPTION 'Enrollment event subject or revision mismatch' USING ERRCODE='23514';
      END IF;
      IF NEW.action IN ('END','WITHDRAW') THEN
        IF NEW.actor_id<>o.actor_user_id OR NOT enrollment_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version,false)
          OR e.status IN ('ENDED','WITHDRAWN')
          OR (NEW.action='END' AND e.status<>'VERIFIED') OR (NEW.action='WITHDRAW' AND e.status='VERIFIED')
          OR NEW.receipt->>'enrollment_id' IS DISTINCT FROM e.id::text
          OR NEW.receipt->>'status' IS DISTINCT FROM (CASE WHEN NEW.action='END' THEN 'ENDED' ELSE 'WITHDRAWN' END)
          OR NOT NEW.receipt ? 'end_date' THEN
          RAISE EXCEPTION 'Enrollment own terminal event invalid' USING ERRCODE='23514';
        END IF;
      ELSE
        IF o.origin<>'PUBLIC' OR NEW.actor_id=o.actor_user_id
          OR NOT enrollment_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version,true)
          OR NOT EXISTS(SELECT 1 FROM platform_role_grants g JOIN role_catalog r ON r.id=g.role_id
            WHERE g.id=NEW.platform_grant_id AND g.user_id=NEW.actor_id AND g.revoked_at IS NULL
              AND g.expires_at>clock_timestamp() AND r.code='MODERATOR' AND r.scope_kind='PLATFORM')
          OR NOT EXISTS(SELECT 1 FROM enrollment_submissions v WHERE v.case_id=c.id AND v.revision=c.current_revision
            AND jsonb_array_length(v.file_ids)>0) THEN
          RAISE EXCEPTION 'Enrollment independent moderator authority invalid' USING ERRCODE='23514';
        END IF;
        IF NEW.action='CLAIM' THEN
          IF c.status NOT IN ('PENDING','IN_REVIEW','NEEDS_INFO') OR
            (c.assigned_reviewer_id IS NOT NULL AND c.assigned_reviewer_id<>NEW.actor_id) THEN
            RAISE EXCEPTION 'Enrollment claim state invalid' USING ERRCODE='23514';
          END IF;
        ELSIF c.status<>'IN_REVIEW' OR c.assigned_reviewer_id IS DISTINCT FROM NEW.actor_id THEN
          RAISE EXCEPTION 'Enrollment assigned review required' USING ERRCODE='23514';
        END IF;
        IF NEW.action='APPROVE' AND (NOT enrollment_files_match(c.id,c.current_revision)
          OR NOT EXISTS(SELECT 1 FROM institutions i JOIN users u ON u.id=o.actor_user_id
            WHERE i.id=o.institution_id AND i.status='VERIFIED' AND u.status='ACTIVE')) THEN
          RAISE EXCEPTION 'Enrollment approval material is stale' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_enrollment_event BEFORE INSERT ON flexbridge.enrollment_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_enrollment_event();

    CREATE FUNCTION flexbridge.guard_enrollment_case() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE o enrollment_origins%ROWTYPE;
    BEGIN
      SELECT * INTO o FROM enrollment_origins WHERE case_id=OLD.id;
      IF o.enrollment_id IS NULL THEN RETURN NEW; END IF;
      IF ROW(NEW.requester_id,NEW.kind,NEW.enrollment_id,NEW.candidate_id,NEW.institution_id,NEW.organization_id,NEW.appointment_id)
        IS DISTINCT FROM ROW(OLD.requester_id,OLD.kind,OLD.enrollment_id,OLD.candidate_id,OLD.institution_id,OLD.organization_id,OLD.appointment_id)
        OR NEW.current_revision NOT BETWEEN OLD.current_revision AND OLD.current_revision+1 THEN
        RAISE EXCEPTION 'Enrollment case identity or revision invalid' USING ERRCODE='23514';
      END IF;
      IF NEW.current_revision<>OLD.current_revision AND (OLD.status NOT IN ('DRAFT','NEEDS_INFO','REJECTED')
        OR NEW.status<>'PENDING' OR NEW.assigned_reviewer_id IS NOT NULL OR NEW.decision_reason IS NOT NULL OR NEW.decided_at IS NOT NULL) THEN
        RAISE EXCEPTION 'Enrollment resubmission transition invalid' USING ERRCODE='23514';
      END IF;
      IF NEW.status='DRAFT' THEN
        IF OLD.status<>'DRAFT' THEN RAISE EXCEPTION 'Enrollment cannot return to draft' USING ERRCODE='23514'; END IF;
      ELSIF NEW.status='PENDING' THEN
        IF NOT EXISTS(SELECT 1 FROM enrollment_submissions v WHERE v.case_id=NEW.id AND v.revision=NEW.current_revision
          AND jsonb_array_length(v.file_ids)>0) THEN
          RAISE EXCEPTION 'Enrollment pending revision missing' USING ERRCODE='23514';
        END IF;
      ELSIF NEW.status='IN_REVIEW' THEN
        IF NOT EXISTS(SELECT 1 FROM enrollment_events d WHERE d.case_id=NEW.id AND d.revision=NEW.current_revision
          AND d.action='CLAIM' AND d.actor_id=NEW.assigned_reviewer_id) THEN
          RAISE EXCEPTION 'Enrollment claim proof missing' USING ERRCODE='23514';
        END IF;
      ELSIF NEW.status IN ('APPROVED','REJECTED','NEEDS_INFO') THEN
        IF NOT EXISTS(SELECT 1 FROM enrollment_events d WHERE d.case_id=NEW.id AND d.revision=NEW.current_revision
          AND d.action=CASE NEW.status WHEN 'APPROVED' THEN 'APPROVE' WHEN 'REJECTED' THEN 'REJECT' ELSE 'NEEDS_INFO' END
          AND d.actor_id=NEW.assigned_reviewer_id AND d.reason=NEW.decision_reason AND d.created_at=NEW.decided_at) THEN
          RAISE EXCEPTION 'Enrollment decision proof missing' USING ERRCODE='23514';
        END IF;
      ELSIF NEW.status='CANCELLED' THEN
        IF NOT EXISTS(SELECT 1 FROM enrollment_events d WHERE d.enrollment_id=o.enrollment_id AND d.action='WITHDRAW') THEN
          RAISE EXCEPTION 'Enrollment withdrawal proof missing' USING ERRCODE='23514';
        END IF;
      ELSE RAISE EXCEPTION 'Enrollment case status invalid' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_enrollment_case BEFORE UPDATE ON flexbridge.verification_cases
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_enrollment_case();

    CREATE FUNCTION flexbridge.guard_enrollment_state() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE o enrollment_origins%ROWTYPE;
    BEGIN
      SELECT * INTO o FROM enrollment_origins WHERE enrollment_id=NEW.id;
      IF TG_OP='UPDATE' AND o.enrollment_id IS NOT NULL THEN
        IF ROW(NEW.candidate_id,NEW.institution_id,NEW.verification_case_id,NEW.created_at)
          IS DISTINCT FROM ROW(OLD.candidate_id,OLD.institution_id,OLD.verification_case_id,OLD.created_at)
          OR (OLD.status IN ('ENDED','WITHDRAWN') AND ROW(NEW.program,NEW.start_date,NEW.end_date,NEW.status,NEW.student_ref_digest)
            IS DISTINCT FROM ROW(OLD.program,OLD.start_date,OLD.end_date,OLD.status,OLD.student_ref_digest))
          OR (OLD.status='VERIFIED' AND ROW(NEW.program,NEW.start_date,NEW.student_ref_digest)
            IS DISTINCT FROM ROW(OLD.program,OLD.start_date,OLD.student_ref_digest))
          OR (OLD.status='VERIFIED' AND NEW.end_date IS DISTINCT FROM OLD.end_date AND NEW.status<>'ENDED') THEN
          RAISE EXCEPTION 'Enrollment identity/approved history cannot be rewritten' USING ERRCODE='23514';
        END IF;
        IF NEW.status IN ('ENDED','WITHDRAWN') AND OLD.status IS DISTINCT FROM NEW.status THEN
          IF NOT EXISTS(SELECT 1 FROM enrollment_events d WHERE d.enrollment_id=NEW.id
            AND d.action=CASE NEW.status WHEN 'ENDED' THEN 'END' ELSE 'WITHDRAW' END
            AND d.receipt->'end_date' IS NOT DISTINCT FROM COALESCE(to_jsonb(NEW.end_date),'null'::jsonb)) THEN
            RAISE EXCEPTION 'Enrollment terminal receipt missing' USING ERRCODE='23514';
          END IF;
        END IF;
      END IF;
      IF NEW.status='VERIFIED' THEN
        IF TG_OP='INSERT' OR o.enrollment_id IS NULL THEN
          RAISE EXCEPTION 'New VERIFIED enrollment requires exact approval proof' USING ERRCODE='23514';
        END IF;
        IF o.origin='LEGACY_IMPORT' THEN
          IF OLD.status<>'VERIFIED' OR o.initial_snapshot->>'status' IS DISTINCT FROM 'VERIFIED' THEN
            RAISE EXCEPTION 'Legacy enrollment cannot be promoted or resurrected' USING ERRCODE='23514';
          END IF;
        ELSIF NOT EXISTS(SELECT 1 FROM verification_cases c JOIN enrollment_submissions v
          ON v.case_id=c.id AND v.revision=c.current_revision JOIN enrollment_events d
          ON d.case_id=v.case_id AND d.revision=v.revision AND d.action='APPROVE'
          WHERE c.id=o.case_id AND c.status='APPROVED' AND c.enrollment_id=NEW.id
            AND NEW.program=v.program AND NEW.start_date=v.start_date AND NEW.end_date IS NOT DISTINCT FROM v.end_date
            AND NEW.student_ref_digest IS NOT DISTINCT FROM v.student_ref_digest) THEN
          RAISE EXCEPTION 'Enrollment approved revision mismatch' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_enrollment_state BEFORE INSERT OR UPDATE ON flexbridge.enrollments
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_enrollment_state();

    CREATE FUNCTION flexbridge.enrollment_is_current(eid uuid) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM enrollments e JOIN enrollment_origins o ON o.enrollment_id=e.id
        JOIN institutions i ON i.id=e.institution_id WHERE e.id=eid AND e.status='VERIFIED' AND i.status='VERIFIED'
          AND e.start_date<=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date
          AND (e.end_date IS NULL OR e.end_date>=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date)
          AND ((o.origin='LEGACY_IMPORT' AND o.initial_snapshot->>'status'='VERIFIED') OR
            (o.origin='PUBLIC' AND EXISTS(SELECT 1 FROM verification_cases c JOIN enrollment_events d
              ON d.case_id=c.id AND d.revision=c.current_revision AND d.action='APPROVE'
              WHERE c.id=o.case_id AND c.enrollment_id=e.id AND c.status='APPROVED'))))
    $$;
    """)


def downgrade():
    raise RuntimeError('Enrollment evidence/history needs a reviewed data-preserving rollback plan')
