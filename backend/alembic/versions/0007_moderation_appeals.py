"""Pinned appeal requests with independent review and immutable decision history."""
from alembic import op

revision='0007_moderation_appeals'
down_revision='0006_retention_evaluations'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    CREATE TRIGGER trg_immutable_moderation_actions BEFORE UPDATE OR DELETE
      ON flexbridge.moderation_actions FOR EACH ROW
      EXECUTE FUNCTION flexbridge.fn_block_append_only_mutation();
    CREATE TABLE flexbridge.moderation_appeal_requests (
      case_id uuid PRIMARY KEY REFERENCES flexbridge.moderation_cases(id),
      created_at timestamptz NOT NULL,
      original_action_id uuid NOT NULL UNIQUE REFERENCES flexbridge.moderation_actions(id),
      opportunity_id uuid NOT NULL REFERENCES flexbridge.opportunities(id),
      revision_id uuid NOT NULL REFERENCES flexbridge.opportunity_revisions(id),
      appellant_id uuid NOT NULL REFERENCES flexbridge.users(id),
      reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 15 AND 4000),
      revision_snapshot jsonb NOT NULL CHECK(jsonb_typeof(revision_snapshot)='object'
        AND octet_length(revision_snapshot::text)<=524288),
      original_decision jsonb NOT NULL CHECK(jsonb_typeof(original_decision)='object'
        AND octet_length(original_decision::text)<=524288),
      status text NOT NULL CHECK(status IN ('OPEN','ASSIGNED','RESOLVED')),
      reviewer_id uuid REFERENCES flexbridge.users(id),
      decision text CHECK(decision IN ('UPHOLD','REOPEN')),
      decision_reason text, resolved_at timestamptz,
      CHECK(reviewer_id IS NULL OR reviewer_id<>appellant_id),
      CHECK((status='OPEN' AND reviewer_id IS NULL AND decision IS NULL AND decision_reason IS NULL AND resolved_at IS NULL)
        OR (status='ASSIGNED' AND reviewer_id IS NOT NULL AND decision IS NULL AND decision_reason IS NULL AND resolved_at IS NULL)
        OR (status='RESOLVED' AND reviewer_id IS NOT NULL AND decision IS NOT NULL
          AND decision_reason IS NOT NULL AND length(btrim(decision_reason)) BETWEEN 15 AND 4000 AND resolved_at IS NOT NULL)));
    CREATE INDEX ix_moderation_appeal_queue ON flexbridge.moderation_appeal_requests(status,case_id);
    CREATE FUNCTION flexbridge.moderation_revision_snapshot(target uuid) RETURNS jsonb
    LANGUAGE sql STABLE SET search_path=pg_catalog,flexbridge AS $$
      SELECT jsonb_build_object('revision',to_jsonb(r)||jsonb_build_object(
          'salary_min',r.salary_min::text,'salary_max',r.salary_max::text),
        'opportunity_skills',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY s.id)
          FROM opportunity_skills s WHERE s.revision_id=r.id),'[]'::jsonb),
        'opportunity_shifts',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY s.id)
          FROM opportunity_shifts s WHERE s.revision_id=r.id),'[]'::jsonb))
      FROM opportunity_revisions r WHERE r.id=target
    $$;
    CREATE FUNCTION flexbridge.moderation_decision_snapshot(target uuid) RETURNS jsonb
    LANGUAGE sql STABLE SET search_path=pg_catalog,flexbridge AS $$
      SELECT jsonb_build_object('action',to_jsonb(a),'policy_category',c.category)
      FROM moderation_actions a JOIN moderation_cases c ON c.id=a.case_id WHERE a.id=target
    $$;
    CREATE FUNCTION flexbridge.guard_moderation_appeal() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,flexbridge AS $$
    DECLARE original_actor uuid; original_target uuid; revision_author uuid; target_org uuid;
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'Appeal history cannot be deleted' USING ERRCODE='23514';
      END IF;
      IF TG_OP='UPDATE' THEN
        IF ROW(NEW.case_id,NEW.created_at,NEW.original_action_id,NEW.opportunity_id,NEW.revision_id,
               NEW.appellant_id,NEW.reason,NEW.revision_snapshot,NEW.original_decision) IS DISTINCT FROM
           ROW(OLD.case_id,OLD.created_at,OLD.original_action_id,OLD.opportunity_id,OLD.revision_id,
               OLD.appellant_id,OLD.reason,OLD.revision_snapshot,OLD.original_decision) THEN
          RAISE EXCEPTION 'Appeal request and evidence are immutable' USING ERRCODE='23514';
        END IF;
        IF NOT ((OLD.status='OPEN' AND NEW.status='ASSIGNED') OR
                (OLD.status='ASSIGNED' AND NEW.status='RESOLVED' AND NEW.reviewer_id=OLD.reviewer_id)) THEN
          RAISE EXCEPTION 'Invalid appeal transition' USING ERRCODE='23514';
        END IF;
      ELSIF NEW.status<>'OPEN' THEN
        RAISE EXCEPTION 'Appeals must start OPEN' USING ERRCODE='23514';
      END IF;
      SELECT a.actor_id,c.opportunity_id INTO original_actor,original_target
        FROM moderation_actions a JOIN moderation_cases c ON c.id=a.case_id
        WHERE a.id=NEW.original_action_id AND a.action='REJECT';
      SELECT r.author_id,o.organization_id INTO revision_author,target_org
        FROM opportunity_revisions r JOIN opportunities o ON o.id=r.opportunity_id
        WHERE r.id=NEW.revision_id AND o.id=NEW.opportunity_id;
      IF original_actor IS NULL OR original_target IS DISTINCT FROM NEW.opportunity_id OR revision_author IS NULL
        OR NOT EXISTS(SELECT 1 FROM moderation_cases c WHERE c.id=NEW.case_id
          AND c.opportunity_id=NEW.opportunity_id AND c.reporter_id=NEW.appellant_id) THEN
        RAISE EXCEPTION 'Appeal target mismatch' USING ERRCODE='23514';
      END IF;
      IF NEW.reviewer_id IS NOT NULL AND (NEW.reviewer_id IN (original_actor,revision_author,NEW.appellant_id)
        OR EXISTS(SELECT 1 FROM org_memberships m WHERE m.organization_id=target_org AND m.user_id=NEW.reviewer_id)) THEN
        RAISE EXCEPTION 'Appeal reviewer must be independent' USING ERRCODE='23514';
      END IF;
      IF TG_OP='INSERT' OR NEW.status='RESOLVED' THEN
        IF NOT EXISTS(SELECT 1 FROM opportunities o WHERE o.id=NEW.opportunity_id
          AND o.status='REJECTED' AND o.current_revision_id=NEW.revision_id)
          OR NEW.original_action_id IS DISTINCT FROM
            (SELECT a.id FROM moderation_actions a JOIN moderation_cases c ON c.id=a.case_id
             WHERE c.opportunity_id=NEW.opportunity_id AND a.action IN ('APPROVE','REJECT')
             ORDER BY a.occurred_at DESC,a.created_at DESC,a.id DESC LIMIT 1)
          OR NEW.revision_snapshot IS DISTINCT FROM moderation_revision_snapshot(NEW.revision_id)
          OR NEW.original_decision IS DISTINCT FROM moderation_decision_snapshot(NEW.original_action_id) THEN
          RAISE EXCEPTION 'Appeal decision or evidence is stale' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_moderation_appeal BEFORE INSERT OR UPDATE OR DELETE
      ON flexbridge.moderation_appeal_requests FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_moderation_appeal();
    """)


def downgrade():
    raise RuntimeError('Appeal and decision history require reviewed forward recovery')
