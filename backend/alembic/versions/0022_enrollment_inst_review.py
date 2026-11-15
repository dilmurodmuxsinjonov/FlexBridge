"""Let the student's own university coordinator review enrollment (until HEMIS).

Product decision (user, 2026-11-16): a student's status is confirmed by staff of
the university the student claims, not only by platform moderators, until a
HEMIS/registry integration exists. Every other invariant of 0013 is kept:
independent reviewer (never the requester), claim before decision, current MFA
session, current revision with evidence, and fresh material on approval.

Each review event records exactly one authority proof:
- platform_grant_id: a current PLATFORM MODERATOR grant (unchanged), or
- institution_grant_id: a current INSTITUTION COORDINATOR grant of the
  enrollment's own institution, backed by an accepted, in-date appointment and an
  active, accepted membership of a VERIFIED institution.
"""
from alembic import op

revision = '0022_enrollment_inst_review'
down_revision = '0021_candidate_portal_extension'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE flexbridge.enrollment_events
      ADD COLUMN institution_grant_id uuid REFERENCES flexbridge.institution_role_grants(id);

    DO $$ DECLARE n text; BEGIN
      SELECT conname INTO n FROM pg_constraint
        WHERE conrelid='flexbridge.enrollment_events'::regclass AND contype='c'
          AND pg_get_constraintdef(oid) LIKE '%platform_grant_id IS NOT NULL%';
      IF n IS NULL THEN RAISE EXCEPTION 'enrollment_events authority shape check not found'; END IF;
      EXECUTE format('ALTER TABLE flexbridge.enrollment_events DROP CONSTRAINT %I', n);
    END $$;

    ALTER TABLE flexbridge.enrollment_events ADD CONSTRAINT enrollment_events_authority_shape CHECK(
      (action IN ('END','WITHDRAW') AND idempotency_key IS NOT NULL
        AND length(idempotency_key) BETWEEN 8 AND 128 AND request_fingerprint IS NOT NULL
        AND request_fingerprint ~ '^[0-9a-f]{64}$' AND platform_grant_id IS NULL AND institution_grant_id IS NULL)
      OR (action IN ('CLAIM','APPROVE','REJECT','NEEDS_INFO')
        AND ((platform_grant_id IS NOT NULL) <> (institution_grant_id IS NOT NULL))
        AND case_id IS NOT NULL AND revision IS NOT NULL AND idempotency_key IS NULL AND request_fingerprint IS NULL));

    CREATE OR REPLACE FUNCTION flexbridge.enrollment_institution_reviewer_current(
      p_grant uuid, p_actor uuid, p_inst uuid) RETURNS boolean
    LANGUAGE sql VOLATILE SET search_path=pg_catalog,flexbridge AS $$
      SELECT EXISTS(
        SELECT 1 FROM institution_role_grants g
          JOIN institution_memberships m ON m.id=g.membership_id
          JOIN role_catalog r ON r.id=g.role_id
          JOIN institution_appointments a ON a.id=g.appointment_id
          JOIN institutions i ON i.id=m.institution_id
          JOIN users u ON u.id=m.user_id
        WHERE g.id=p_grant AND m.user_id=p_actor AND m.institution_id=p_inst
          AND u.status='ACTIVE' AND i.status='VERIFIED'
          AND m.status='ACTIVE' AND m.revoked_at IS NULL
          AND m.accepted_at IS NOT NULL AND m.accepted_at<=clock_timestamp()
          AND g.revoked_at IS NULL AND r.code='COORDINATOR' AND r.scope_kind='INSTITUTION'
          AND a.user_id=m.user_id AND a.institution_id=m.institution_id AND a.status='ACTIVE'
          AND a.accepted_at IS NOT NULL AND a.accepted_at<=clock_timestamp()
          AND a.valid_from<=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date
          AND (a.valid_to IS NULL OR a.valid_to>=(clock_timestamp() AT TIME ZONE 'Asia/Tashkent')::date))
    $$;

    CREATE OR REPLACE FUNCTION flexbridge.guard_enrollment_event() RETURNS trigger
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
          OR NOT (
            (NEW.platform_grant_id IS NOT NULL AND EXISTS(SELECT 1 FROM platform_role_grants g JOIN role_catalog r ON r.id=g.role_id
              WHERE g.id=NEW.platform_grant_id AND g.user_id=NEW.actor_id AND g.revoked_at IS NULL
                AND g.expires_at>clock_timestamp() AND r.code='MODERATOR' AND r.scope_kind='PLATFORM'))
            OR (NEW.institution_grant_id IS NOT NULL
              AND enrollment_institution_reviewer_current(NEW.institution_grant_id,NEW.actor_id,o.institution_id)))
          OR NOT EXISTS(SELECT 1 FROM enrollment_submissions v WHERE v.case_id=c.id AND v.revision=c.current_revision
            AND jsonb_array_length(v.file_ids)>0) THEN
          RAISE EXCEPTION 'Enrollment independent reviewer authority invalid' USING ERRCODE='23514';
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
    """)


def downgrade():
    raise RuntimeError('Enrollment review proofs are append-only; a rollback needs a reviewed data-preserving plan')
