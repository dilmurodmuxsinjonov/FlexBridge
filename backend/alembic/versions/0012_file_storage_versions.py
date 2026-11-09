"""Explicit storage provenance; legacy ambiguity is preserved, never backfilled."""
from alembic import op

revision = '0012_file_storage_versions'
down_revision = '0011_institution_onboarding'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE flexbridge.files ADD COLUMN storage_bucket text;
    ALTER TABLE flexbridge.files ADD COLUMN storage_version_id text;
    ALTER TABLE flexbridge.files ADD COLUMN storage_etag text;
    ALTER TABLE flexbridge.files ADD CONSTRAINT chk_file_storage_reference CHECK (
      (storage_bucket IS NULL AND storage_version_id IS NULL AND storage_etag IS NULL)
      OR (storage_bucket IS NOT NULL AND storage_bucket<>'' AND storage_bucket=btrim(storage_bucket)
        AND storage_version_id IS NOT NULL AND storage_version_id<>'' AND storage_version_id=btrim(storage_version_id)
        AND lower(storage_version_id)<>'null'
        AND storage_etag IS NOT NULL AND storage_etag<>'' AND storage_etag=btrim(storage_etag)
        AND (scan_status<>'CLEAN' OR (object_version IS NOT NULL AND object_version=storage_version_id))
        AND (scan_status<>'SCANNING' OR (object_version IS NOT NULL AND object_version=storage_etag))));

    CREATE FUNCTION flexbridge.guard_file_storage_reference() RETURNS trigger
    LANGUAGE plpgsql SET search_path=flexbridge,pg_temp AS $$
    BEGIN
      IF NEW.scan_status IN ('SCANNING','CLEAN') AND NEW.storage_version_id IS NULL THEN
        IF TG_OP='INSERT' THEN
          RAISE EXCEPTION 'New scanned files require explicit storage provenance' USING ERRCODE='23514';
        ELSIF ROW(NEW.scan_status,NEW.storage_key,NEW.byte_size,NEW.sha256,NEW.object_version,
            NEW.storage_bucket,NEW.storage_version_id,NEW.storage_etag)
          IS DISTINCT FROM ROW(OLD.scan_status,OLD.storage_key,OLD.byte_size,OLD.sha256,OLD.object_version,
            OLD.storage_bucket,OLD.storage_version_id,OLD.storage_etag) THEN
          RAISE EXCEPTION 'Scanned file provenance cannot be removed or guessed' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_file_storage_reference BEFORE INSERT OR UPDATE ON flexbridge.files
      FOR EACH ROW EXECUTE FUNCTION flexbridge.guard_file_storage_reference();
    """)


def downgrade():
    raise RuntimeError('Stored object provenance requires an explicit data-preserving rollback plan')
