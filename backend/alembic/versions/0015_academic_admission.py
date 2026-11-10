"""Bind pending academic internships to school scope and personal teacher evidence."""
from alembic import op

revision='0015_academic_admission'
down_revision='0014_placement_admission'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    CREATE FUNCTION flexbridge.academic_grant_current(actor uuid,inst uuid,gid uuid,role_code text) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM institution_role_grants g JOIN institution_memberships m ON m.id=g.membership_id
        JOIN institution_appointments a ON a.id=g.appointment_id JOIN institutions i ON i.id=m.institution_id
        JOIN role_catalog r ON r.id=g.role_id JOIN users u ON u.id=m.user_id
        WHERE g.id=gid AND g.revoked_at IS NULL AND m.user_id=actor AND u.status='ACTIVE'
          AND m.institution_id=inst AND m.status='ACTIVE' AND m.revoked_at IS NULL
          AND m.accepted_at<=clock_timestamp() AND i.status='VERIFIED'
          AND a.institution_id=inst AND a.user_id=actor AND a.status='ACTIVE' AND a.accepted_at<=clock_timestamp()
          AND a.valid_from<=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date
          AND (a.valid_to IS NULL OR a.valid_to>=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date)
          AND r.scope_kind='INSTITUTION' AND r.code=role_code)
    $$;
    CREATE TABLE flexbridge.supervision_origins (
      supervision_id uuid PRIMARY KEY REFERENCES flexbridge.student_supervisions(id),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),origin text NOT NULL CHECK(origin IN ('PUBLIC','LEGACY_IMPORT')),
      initial_snapshot jsonb NOT NULL CHECK(jsonb_typeof(initial_snapshot)='object'),
      actor_id uuid REFERENCES flexbridge.users(id),session_id uuid REFERENCES flexbridge.sessions(id),auth_version integer,
      coordinator_grant_id uuid REFERENCES flexbridge.institution_role_grants(id),idempotency_key text,request_fingerprint text,receipt jsonb,
      UNIQUE(actor_id,idempotency_key),
      CHECK((origin='PUBLIC' AND actor_id IS NOT NULL AND session_id IS NOT NULL AND auth_version IS NOT NULL
        AND coordinator_grant_id IS NOT NULL AND idempotency_key IS NOT NULL AND length(idempotency_key) BETWEEN 8 AND 128
        AND request_fingerprint IS NOT NULL AND request_fingerprint ~ '^[0-9a-f]{64}$' AND receipt IS NOT NULL AND jsonb_typeof(receipt)='object')
        OR (origin='LEGACY_IMPORT' AND actor_id IS NULL AND session_id IS NULL AND auth_version IS NULL
          AND coordinator_grant_id IS NULL AND idempotency_key IS NULL AND request_fingerprint IS NULL AND receipt IS NULL))
    );
    INSERT INTO flexbridge.supervision_origins(supervision_id,origin,initial_snapshot)
      SELECT s.id,'LEGACY_IMPORT',to_jsonb(s) FROM flexbridge.student_supervisions s;
    CREATE TABLE flexbridge.placement_academic_bindings (
      placement_id uuid PRIMARY KEY REFERENCES flexbridge.placement_intakes(placement_id),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),origin text NOT NULL CHECK(origin IN ('PUBLIC','LEGACY_IMPORT')),
      institution_id uuid NOT NULL REFERENCES flexbridge.institutions(id),enrollment_id uuid NOT NULL,
      supervision_id uuid,terms_id uuid,
      initial_snapshot jsonb NOT NULL CHECK(jsonb_typeof(initial_snapshot)='object'),
      scope_snapshot jsonb NOT NULL CHECK(jsonb_typeof(scope_snapshot)='object'),
      actor_id uuid REFERENCES flexbridge.users(id),session_id uuid REFERENCES flexbridge.sessions(id),auth_version integer,
      coordinator_grant_id uuid REFERENCES flexbridge.institution_role_grants(id),idempotency_key text,request_fingerprint text,receipt jsonb,
      FOREIGN KEY(enrollment_id,institution_id) REFERENCES flexbridge.enrollments(id,institution_id),
      FOREIGN KEY(supervision_id,institution_id) REFERENCES flexbridge.student_supervisions(id,institution_id),
      FOREIGN KEY(terms_id,placement_id) REFERENCES flexbridge.placement_terms(id,placement_id),
      UNIQUE(actor_id,idempotency_key),
      CHECK((origin='PUBLIC' AND supervision_id IS NOT NULL AND terms_id IS NOT NULL AND actor_id IS NOT NULL
        AND session_id IS NOT NULL AND auth_version IS NOT NULL AND coordinator_grant_id IS NOT NULL
        AND idempotency_key IS NOT NULL AND length(idempotency_key) BETWEEN 8 AND 128
        AND request_fingerprint IS NOT NULL AND request_fingerprint ~ '^[0-9a-f]{64}$' AND receipt IS NOT NULL AND jsonb_typeof(receipt)='object')
        OR (origin='LEGACY_IMPORT' AND actor_id IS NULL AND session_id IS NULL AND auth_version IS NULL
          AND coordinator_grant_id IS NULL AND idempotency_key IS NULL AND request_fingerprint IS NULL AND receipt IS NULL))
    );
    INSERT INTO flexbridge.placement_academic_bindings(placement_id,origin,institution_id,enrollment_id,supervision_id,
      terms_id,initial_snapshot,scope_snapshot)
      SELECT p.id,'LEGACY_IMPORT',e.institution_id,e.id,
        CASE WHEN (SELECT count(DISTINCT a.supervision_id) FROM flexbridge.academic_assignments a WHERE a.placement_id=p.id)=1
          THEN (SELECT a.supervision_id FROM flexbridge.academic_assignments a JOIN flexbridge.student_supervisions s ON s.id=a.supervision_id
            WHERE a.placement_id=p.id AND a.institution_id=e.institution_id AND s.institution_id=e.institution_id
              AND s.enrollment_id=e.id LIMIT 1) END,
        p.current_terms_id,to_jsonb(p),jsonb_build_object('enrollment',to_jsonb(e))
      FROM flexbridge.placements p JOIN flexbridge.enrollments e ON e.id=p.enrollment_id WHERE p.academic_track;
    CREATE TABLE flexbridge.academic_assignment_proofs (
      assignment_id uuid PRIMARY KEY REFERENCES flexbridge.academic_assignments(id),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),origin text NOT NULL CHECK(origin IN ('PUBLIC','LEGACY_IMPORT')),
      placement_id uuid NOT NULL REFERENCES flexbridge.placement_academic_bindings(placement_id),
      teacher_user_id uuid NOT NULL REFERENCES flexbridge.users(id),teacher_grant_id uuid REFERENCES flexbridge.institution_role_grants(id),
      teacher_appointment_id uuid REFERENCES flexbridge.institution_appointments(id),
      initial_snapshot jsonb NOT NULL CHECK(jsonb_typeof(initial_snapshot)='object'),
      actor_id uuid REFERENCES flexbridge.users(id),session_id uuid REFERENCES flexbridge.sessions(id),auth_version integer,
      coordinator_grant_id uuid REFERENCES flexbridge.institution_role_grants(id),idempotency_key text,request_fingerprint text,receipt jsonb,
      FOREIGN KEY(assignment_id,placement_id) REFERENCES flexbridge.academic_assignments(id,placement_id),UNIQUE(actor_id,idempotency_key),
      CHECK((origin='PUBLIC' AND teacher_grant_id IS NOT NULL AND teacher_appointment_id IS NOT NULL AND actor_id IS NOT NULL
        AND session_id IS NOT NULL AND auth_version IS NOT NULL AND coordinator_grant_id IS NOT NULL
        AND idempotency_key IS NOT NULL AND length(idempotency_key) BETWEEN 8 AND 128
        AND request_fingerprint IS NOT NULL AND request_fingerprint ~ '^[0-9a-f]{64}$' AND receipt IS NOT NULL AND jsonb_typeof(receipt)='object')
        OR (origin='LEGACY_IMPORT' AND actor_id IS NULL AND session_id IS NULL AND auth_version IS NULL
          AND coordinator_grant_id IS NULL AND idempotency_key IS NULL AND request_fingerprint IS NULL AND receipt IS NULL))
    );
    INSERT INTO flexbridge.academic_assignment_proofs(assignment_id,origin,placement_id,teacher_user_id,teacher_grant_id,
      teacher_appointment_id,initial_snapshot)
      SELECT a.id,'LEGACY_IMPORT',a.placement_id,m.user_id,imported_authority.gid,imported_authority.appointment,to_jsonb(a)
      FROM flexbridge.academic_assignments a JOIN flexbridge.institution_memberships m ON m.id=a.teacher_membership_id
      JOIN flexbridge.placement_academic_bindings b ON b.placement_id=a.placement_id
      LEFT JOIN LATERAL(SELECT min(g.id::text)::uuid AS gid,min(g.appointment_id::text)::uuid AS appointment
        FROM flexbridge.institution_role_grants g WHERE g.membership_id=m.id
          AND flexbridge.academic_grant_current(m.user_id,a.institution_id,g.id,'TEACHER') HAVING count(*)=1) imported_authority ON true;
    CREATE TABLE flexbridge.academic_assignment_consents (
      id uuid PRIMARY KEY,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      placement_id uuid NOT NULL REFERENCES flexbridge.placement_academic_bindings(placement_id),
      assignment_id uuid NOT NULL REFERENCES flexbridge.academic_assignment_proofs(assignment_id),terms_id uuid NOT NULL,
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),auth_version integer NOT NULL,
      teacher_grant_id uuid NOT NULL REFERENCES flexbridge.institution_role_grants(id),
      teacher_appointment_id uuid NOT NULL REFERENCES flexbridge.institution_appointments(id),
      idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL CHECK(request_fingerprint ~ '^[0-9a-f]{64}$'),
      receipt jsonb NOT NULL CHECK(jsonb_typeof(receipt)='object'),
      FOREIGN KEY(assignment_id,placement_id) REFERENCES flexbridge.academic_assignments(id,placement_id),
      FOREIGN KEY(terms_id,placement_id) REFERENCES flexbridge.placement_terms(id,placement_id),
      UNIQUE(actor_id,idempotency_key),UNIQUE(assignment_id,terms_id)
    );
    CREATE TABLE flexbridge.academic_assignment_events (
      id uuid PRIMARY KEY,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      placement_id uuid NOT NULL REFERENCES flexbridge.placements(id),
      assignment_id uuid NOT NULL REFERENCES flexbridge.academic_assignments(id),
      action text NOT NULL CHECK(action='REVOKE'),actor_id uuid NOT NULL REFERENCES flexbridge.users(id),
      session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),auth_version integer NOT NULL,
      coordinator_grant_id uuid NOT NULL REFERENCES flexbridge.institution_role_grants(id),
      idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL CHECK(request_fingerprint ~ '^[0-9a-f]{64}$'),
      receipt jsonb NOT NULL CHECK(jsonb_typeof(receipt)='object'),
      FOREIGN KEY(assignment_id,placement_id) REFERENCES flexbridge.academic_assignments(id,placement_id),
      UNIQUE(actor_id,idempotency_key),UNIQUE(assignment_id)
    );
    CREATE TABLE flexbridge.student_academic_requests (
      id uuid PRIMARY KEY,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      placement_id uuid NOT NULL REFERENCES flexbridge.placement_intakes(placement_id),revision integer NOT NULL CHECK(revision>0),
      institution_id uuid NOT NULL REFERENCES flexbridge.institutions(id),enrollment_id uuid NOT NULL,terms_id uuid NOT NULL,
      actor_id uuid NOT NULL REFERENCES flexbridge.users(id),session_id uuid NOT NULL REFERENCES flexbridge.sessions(id),auth_version integer NOT NULL,
      idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 8 AND 128),
      request_fingerprint text NOT NULL CHECK(request_fingerprint ~ '^[0-9a-f]{64}$'),
      receipt jsonb NOT NULL CHECK(jsonb_typeof(receipt)='object'),
      FOREIGN KEY(enrollment_id,institution_id) REFERENCES flexbridge.enrollments(id,institution_id),
      FOREIGN KEY(terms_id,placement_id) REFERENCES flexbridge.placement_terms(id,placement_id),
      UNIQUE(placement_id,revision),UNIQUE(actor_id,idempotency_key)
    );
    CREATE FUNCTION flexbridge.guard_student_academic_request() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ DECLARE p placements; BEGIN
      SELECT * INTO p FROM placements WHERE id=NEW.placement_id FOR UPDATE;
      IF p.status NOT IN ('PLANNED','PENDING_START_CONFIRMATION') OR p.current_terms_id IS DISTINCT FROM NEW.terms_id
        OR EXISTS(SELECT 1 FROM placement_academic_bindings b WHERE b.placement_id=p.id)
        OR NEW.revision<>(SELECT coalesce(max(r.revision),0)+1 FROM student_academic_requests r WHERE r.placement_id=p.id)
        OR NOT EXISTS(SELECT 1 FROM candidate_profiles c JOIN enrollments e ON e.candidate_id=c.id
          JOIN placement_intakes i ON i.placement_id=p.id WHERE c.id=p.candidate_id AND c.user_id=NEW.actor_id
            AND e.id=NEW.enrollment_id AND e.institution_id=NEW.institution_id AND i.academic_required AND enrollment_is_current(e.id))
        OR NOT placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
      THEN RAISE EXCEPTION 'academic school selection requires personal current student and exact verified enrollment' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_student_academic_request BEFORE INSERT ON flexbridge.student_academic_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_student_academic_request();

    CREATE FUNCTION flexbridge.academic_supervision_current(sid uuid,candidate uuid) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM student_supervisions s JOIN supervision_origins o ON o.supervision_id=s.id
        JOIN enrollments e ON e.id=s.enrollment_id JOIN institution_agreements a ON a.id=s.agreement_id
        JOIN institutions i ON i.id=s.institution_id
        WHERE s.id=sid AND e.candidate_id=candidate AND e.institution_id=s.institution_id AND a.institution_id=s.institution_id
          AND i.status='VERIFIED' AND enrollment_is_current(e.id) AND s.status='ACTIVE' AND s.revoked_at IS NULL
          AND s.accepted_at<=clock_timestamp() AND s.accepted_at=(o.initial_snapshot->>'accepted_at')::timestamptz
          AND s.enrollment_id=(o.initial_snapshot->>'enrollment_id')::uuid
          AND s.coordinator_membership_id=(o.initial_snapshot->>'coordinator_membership_id')::uuid
          AND s.agreement_id=(o.initial_snapshot->>'agreement_id')::uuid
          AND s.purpose=o.initial_snapshot->>'purpose' AND s.legal_basis=o.initial_snapshot->>'legal_basis'
          AND length(btrim(s.legal_basis))>0 AND a.status='ACTIVE'
          AND a.valid_from<=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date
          AND (a.valid_to IS NULL OR a.valid_to>=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date)
          AND ((jsonb_typeof(a.purposes)='array' AND a.purposes ? s.purpose)
            OR (jsonb_typeof(a.purposes)='object' AND a.purposes->s.purpose='true'::jsonb)))
    $$;
    CREATE FUNCTION flexbridge.guard_supervision_origin() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.origin<>'PUBLIC' THEN RAISE EXCEPTION 'supervision legacy set is closed' USING ERRCODE='23514'; END IF;
      IF NOT EXISTS(SELECT 1 FROM student_supervisions s JOIN enrollments e ON e.id=s.enrollment_id
        JOIN institution_memberships m ON m.id=s.coordinator_membership_id JOIN institution_agreements a ON a.id=s.agreement_id
        WHERE s.id=NEW.supervision_id AND m.user_id=NEW.actor_id AND m.institution_id=s.institution_id
          AND e.institution_id=s.institution_id AND a.institution_id=s.institution_id AND enrollment_is_current(e.id)
          AND s.status='ACTIVE' AND s.accepted_at<=clock_timestamp() AND s.revoked_at IS NULL
          AND length(btrim(s.legal_basis))>0 AND a.status='ACTIVE'
          AND a.valid_from<=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date
          AND (a.valid_to IS NULL OR a.valid_to>=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date)
          AND ((jsonb_typeof(a.purposes)='array' AND a.purposes ? s.purpose)
            OR (jsonb_typeof(a.purposes)='object' AND a.purposes->s.purpose='true'::jsonb))
          AND NEW.initial_snapshot=to_jsonb(s) AND placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
          AND academic_grant_current(NEW.actor_id,s.institution_id,NEW.coordinator_grant_id,'COORDINATOR'))
      THEN RAISE EXCEPTION 'supervision requires current exact coordinator and school scope' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_supervision_origin BEFORE INSERT ON flexbridge.supervision_origins
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_supervision_origin();
    CREATE FUNCTION flexbridge.guard_academic_binding() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.origin<>'PUBLIC' THEN RAISE EXCEPTION 'academic binding legacy set is closed' USING ERRCODE='23514'; END IF;
      IF NOT EXISTS(SELECT 1 FROM placements p JOIN placement_intakes i ON i.placement_id=p.id
        JOIN student_supervisions s ON s.id=NEW.supervision_id JOIN institution_memberships m ON m.id=s.coordinator_membership_id
        JOIN placement_terms t ON t.id=NEW.terms_id
        WHERE p.id=NEW.placement_id AND i.academic_required AND p.status IN ('PLANNED','PENDING_START_CONFIRMATION')
          AND NOT p.academic_track AND p.enrollment_id IS NULL AND p.current_terms_id=t.id AND t.placement_id=p.id
          AND s.institution_id=NEW.institution_id AND s.enrollment_id=NEW.enrollment_id AND m.user_id=NEW.actor_id
          AND EXISTS(SELECT 1 FROM student_academic_requests r WHERE r.placement_id=p.id AND r.enrollment_id=NEW.enrollment_id
            AND r.institution_id=NEW.institution_id AND NOT EXISTS(SELECT 1 FROM student_academic_requests newer
              WHERE newer.placement_id=p.id AND newer.revision>r.revision))
          AND academic_supervision_current(s.id,p.candidate_id) AND NEW.initial_snapshot=to_jsonb(p)
          AND t.terms_snapshot->'academic_scope'=NEW.scope_snapshot
          AND NEW.scope_snapshot->>'institution_id'=NEW.institution_id::text
          AND NEW.scope_snapshot->>'enrollment_id'=NEW.enrollment_id::text
          AND NEW.scope_snapshot->>'supervision_id'=NEW.supervision_id::text
          AND NEW.scope_snapshot->>'agreement_id'=s.agreement_id::text
          AND NEW.scope_snapshot->>'purpose'=s.purpose AND NEW.scope_snapshot->>'legal_basis'=s.legal_basis
          AND placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
          AND academic_grant_current(NEW.actor_id,NEW.institution_id,NEW.coordinator_grant_id,'COORDINATOR'))
      THEN RAISE EXCEPTION 'academic binding requires pending exact school scope and coordinator proof' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_academic_binding BEFORE INSERT ON flexbridge.placement_academic_bindings
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_academic_binding();
    CREATE FUNCTION flexbridge.guard_academic_assignment_proof() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NEW.origin<>'PUBLIC' THEN RAISE EXCEPTION 'academic assignment legacy set is closed' USING ERRCODE='23514'; END IF;
      IF NOT EXISTS(SELECT 1 FROM academic_assignments a JOIN placement_academic_bindings b ON b.placement_id=a.placement_id
        JOIN placements p ON p.id=a.placement_id JOIN candidate_profiles c ON c.id=p.candidate_id
        JOIN student_supervisions s ON s.id=a.supervision_id JOIN institution_memberships cm ON cm.id=s.coordinator_membership_id
        JOIN institution_memberships tm ON tm.id=a.teacher_membership_id JOIN institution_role_grants tg ON tg.id=NEW.teacher_grant_id
        WHERE a.id=NEW.assignment_id AND p.id=NEW.placement_id AND p.academic_track AND p.enrollment_id=b.enrollment_id
          AND a.institution_id=b.institution_id AND a.institution_id=s.institution_id AND b.supervision_id=s.id
          AND academic_supervision_current(s.id,p.candidate_id) AND cm.user_id=NEW.actor_id AND cm.user_id<>tm.user_id
          AND tm.user_id=NEW.teacher_user_id AND tm.user_id<>c.user_id AND tg.membership_id=tm.id
          AND tg.appointment_id=NEW.teacher_appointment_id AND a.assigned_by_id=NEW.actor_id
          AND a.accepted_at IS NULL AND a.revoked_at IS NULL AND NEW.initial_snapshot=to_jsonb(a)
          AND p.status IN ('PLANNED','PENDING_START_CONFIRMATION','ACTIVE')
          AND placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
          AND academic_grant_current(NEW.actor_id,a.institution_id,NEW.coordinator_grant_id,'COORDINATOR')
          AND academic_grant_current(NEW.teacher_user_id,a.institution_id,NEW.teacher_grant_id,'TEACHER'))
      THEN RAISE EXCEPTION 'academic nomination requires exact current coordinator and original teacher scope' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_academic_assignment_proof BEFORE INSERT ON flexbridge.academic_assignment_proofs
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_academic_assignment_proof();
    CREATE FUNCTION flexbridge.guard_academic_consent() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM academic_assignment_proofs q JOIN academic_assignments a ON a.id=q.assignment_id
        JOIN placements p ON p.id=a.placement_id JOIN placement_academic_bindings b ON b.placement_id=p.id
        WHERE q.assignment_id=NEW.assignment_id AND p.id=NEW.placement_id AND p.current_terms_id=NEW.terms_id
          AND p.status IN ('PLANNED','PENDING_START_CONFIRMATION','ACTIVE') AND p.academic_track
          AND q.teacher_user_id=NEW.actor_id AND q.teacher_grant_id=NEW.teacher_grant_id
          AND q.teacher_appointment_id=NEW.teacher_appointment_id AND a.revoked_at IS NULL
          AND a.supervision_id=b.supervision_id AND academic_supervision_current(a.supervision_id,p.candidate_id)
          AND placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
          AND academic_grant_current(NEW.actor_id,a.institution_id,NEW.teacher_grant_id,'TEACHER'))
      THEN RAISE EXCEPTION 'teacher consent requires personal current original assignment scope' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_academic_consent BEFORE INSERT ON flexbridge.academic_assignment_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_academic_consent();
    CREATE FUNCTION flexbridge.guard_academic_revoke() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF NOT EXISTS(SELECT 1 FROM academic_assignments a WHERE a.id=NEW.assignment_id AND a.placement_id=NEW.placement_id
        AND a.revoked_at IS NULL AND placement_actor_current(NEW.actor_id,NEW.session_id,NEW.auth_version)
        AND academic_grant_current(NEW.actor_id,a.institution_id,NEW.coordinator_grant_id,'COORDINATOR'))
      THEN RAISE EXCEPTION 'academic revoke requires current school coordinator proof' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_academic_revoke BEFORE INSERT ON flexbridge.academic_assignment_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_academic_revoke();

    CREATE FUNCTION flexbridge.academic_teacher_current(aid uuid,tid uuid) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM academic_assignments a JOIN academic_assignment_proofs q ON q.assignment_id=a.id
        JOIN placements p ON p.id=a.placement_id JOIN placement_academic_bindings b ON b.placement_id=p.id
        JOIN student_supervisions s ON s.id=a.supervision_id JOIN institution_agreements agreement ON agreement.id=s.agreement_id
        WHERE a.id=aid AND p.academic_track AND p.enrollment_id=b.enrollment_id
          AND a.supervision_id=b.supervision_id AND s.enrollment_id=b.enrollment_id AND s.institution_id=b.institution_id
          AND a.institution_id=b.institution_id AND a.revoked_at IS NULL AND a.accepted_at<=clock_timestamp()
          AND academic_supervision_current(a.supervision_id,p.candidate_id)
          AND (b.origin='LEGACY_IMPORT' OR (b.scope_snapshot->>'agreement_id'=agreement.id::text
            AND (b.scope_snapshot->>'agreement_version')::integer=agreement.version))
          AND academic_grant_current(q.teacher_user_id,a.institution_id,q.teacher_grant_id,'TEACHER')
          AND ((q.origin='LEGACY_IMPORT' AND q.initial_snapshot->>'accepted_at' IS NOT NULL
            AND a.accepted_at=(q.initial_snapshot->>'accepted_at')::timestamptz)
            OR (q.origin='PUBLIC' AND EXISTS(SELECT 1 FROM academic_assignment_consents c WHERE c.assignment_id=a.id
              AND c.terms_id=tid AND c.actor_id=q.teacher_user_id AND c.teacher_grant_id=q.teacher_grant_id))))
    $$;
    CREATE FUNCTION flexbridge.academic_placement_ready(pid uuid,tid uuid) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM placements p JOIN placement_academic_bindings b ON b.placement_id=p.id
        JOIN student_supervisions s ON s.id=b.supervision_id JOIN placement_terms t ON t.id=tid
        JOIN institution_agreements agreement ON agreement.id=s.agreement_id
        WHERE p.id=pid AND b.origin='PUBLIC' AND p.academic_track AND p.enrollment_id=b.enrollment_id
          AND t.placement_id=p.id AND p.current_terms_id=tid AND t.terms_snapshot->'academic_scope'=b.scope_snapshot
          AND academic_supervision_current(s.id,p.candidate_id)
          AND b.scope_snapshot->>'agreement_id'=agreement.id::text AND (b.scope_snapshot->>'agreement_version')::integer=agreement.version
          AND academic_grant_current(b.actor_id,b.institution_id,b.coordinator_grant_id,'COORDINATOR')
          AND EXISTS(SELECT 1 FROM academic_assignments a WHERE a.placement_id=p.id AND a.supervision_id=s.id
            AND academic_teacher_current(a.id,tid)))
    $$;
    CREATE OR REPLACE FUNCTION flexbridge.placement_ready_for_start(pid uuid,tid uuid) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(SELECT 1 FROM placements p JOIN placement_intakes i ON i.placement_id=p.id
        JOIN offers o ON o.id=i.offer_id JOIN opportunity_revisions r ON r.id=i.revision_id
        JOIN applications app ON app.id=p.application_id JOIN application_attempts t ON t.id=i.attempt_id
        JOIN opportunities v ON v.id=r.opportunity_id JOIN candidate_profiles c ON c.id=p.candidate_id
        WHERE p.id=pid AND p.current_terms_id=tid AND v.kind='INTERNSHIP'
          AND ((NOT i.academic_required AND NOT p.academic_track AND r.contract_type='INTERNSHIP_AGREEMENT')
            OR (i.academic_required AND r.contract_type='ACADEMIC_TRIPARTITE' AND academic_placement_ready(pid,tid)))
          AND o.id=p.offer_id AND o.application_id=p.application_id AND v.organization_id=p.organization_id
          AND o.revision_id=r.id AND o.attempt_id=t.id AND t.application_id=app.id AND t.revision_id=r.id
          AND t.opportunity_id=app.opportunity_id AND r.opportunity_id=app.opportunity_id AND app.candidate_id=p.candidate_id
          AND EXISTS(SELECT 1 FROM placement_consents x WHERE x.placement_id=p.id AND x.terms_id=tid AND x.side='CANDIDATE' AND x.actor_id=c.user_id)
          AND EXISTS(SELECT 1 FROM placement_consents x JOIN mentor_assignments a ON a.id=x.assignment_id
            JOIN mentor_assignment_proofs q ON q.assignment_id=a.id JOIN org_memberships m ON m.id=a.membership_id
            JOIN org_role_grants g ON g.id=q.mentor_grant_id JOIN role_catalog z ON z.id=g.role_id JOIN users u ON u.id=m.user_id
            WHERE x.placement_id=p.id AND x.terms_id=tid AND x.side='MENTOR' AND a.placement_id=p.id
              AND a.accepted_at IS NOT NULL AND a.revoked_at IS NULL AND m.id=g.membership_id AND m.organization_id=p.organization_id
              AND m.user_id=x.actor_id AND m.status='ACTIVE' AND m.revoked_at IS NULL AND u.status='ACTIVE' AND m.user_id<>c.user_id
              AND g.revoked_at IS NULL AND g.id=x.org_grant_id AND q.mentor_user_id=x.actor_id AND z.scope_kind='ORG' AND z.code='MENTOR'))
    $$;

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
    CREATE FUNCTION flexbridge.guard_academic_assignment_history() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'academic assignment history is immutable' USING ERRCODE='23514'; END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.accepted_at IS NOT NULL OR NEW.revoked_at IS NOT NULL
        THEN RAISE EXCEPTION 'new academic nomination cannot invent acceptance' USING ERRCODE='23514'; END IF;
        RETURN NEW;
      END IF;
      IF (to_jsonb(NEW)-ARRAY['updated_at','accepted_at','revoked_at']) IS DISTINCT FROM
        (to_jsonb(OLD)-ARRAY['updated_at','accepted_at','revoked_at'])
      THEN RAISE EXCEPTION 'academic nomination is immutable' USING ERRCODE='23514'; END IF;
      IF NEW.accepted_at IS DISTINCT FROM OLD.accepted_at AND (OLD.accepted_at IS NOT NULL OR NOT EXISTS(
        SELECT 1 FROM academic_assignment_consents c WHERE c.assignment_id=NEW.id AND c.created_at=NEW.accepted_at))
      THEN RAISE EXCEPTION 'academic acceptance requires personal evidence' USING ERRCODE='23514'; END IF;
      IF NEW.revoked_at IS DISTINCT FROM OLD.revoked_at AND (OLD.revoked_at IS NOT NULL OR NOT EXISTS(
        SELECT 1 FROM academic_assignment_events e WHERE e.assignment_id=NEW.id AND e.created_at=NEW.revoked_at))
      THEN RAISE EXCEPTION 'academic revocation requires coordinator evidence' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valid_academic_assignment_history BEFORE INSERT OR UPDATE OR DELETE ON flexbridge.academic_assignments
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_academic_assignment_history();
    CREATE OR REPLACE FUNCTION flexbridge.guard_plan_task_insert() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$ DECLARE pid uuid; BEGIN
      SELECT p.id INTO pid FROM placements p JOIN placement_terms t ON t.placement_id=p.id
        WHERE t.id=NEW.terms_id AND p.current_terms_id=t.id AND p.status IN ('PLANNED','PENDING_START_CONFIRMATION') FOR UPDATE OF p;
      IF pid IS NULL OR EXISTS(SELECT 1 FROM placement_consents c WHERE c.terms_id=NEW.terms_id)
        OR EXISTS(SELECT 1 FROM academic_assignment_consents c WHERE c.terms_id=NEW.terms_id)
        OR EXISTS(SELECT 1 FROM placement_academic_bindings b WHERE b.terms_id=NEW.terms_id)
        OR EXISTS(SELECT 1 FROM placement_admission_events e WHERE e.terms_id=NEW.terms_id AND e.action='PLAN_PUBLISHED')
      THEN RAISE EXCEPTION 'published plan tasks are immutable' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER immutable_supervision_origins BEFORE UPDATE OR DELETE ON flexbridge.supervision_origins
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_student_academic_requests BEFORE UPDATE OR DELETE ON flexbridge.student_academic_requests
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_academic_bindings BEFORE UPDATE OR DELETE ON flexbridge.placement_academic_bindings
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_academic_assignment_proofs BEFORE UPDATE OR DELETE ON flexbridge.academic_assignment_proofs
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_academic_assignment_consents BEFORE UPDATE OR DELETE ON flexbridge.academic_assignment_consents
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TRIGGER immutable_academic_assignment_events BEFORE UPDATE OR DELETE ON flexbridge.academic_assignment_events
      FOR EACH ROW EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    """)


def downgrade():
    raise RuntimeError('Academic proof/history needs a reviewed data-preserving rollback plan')
