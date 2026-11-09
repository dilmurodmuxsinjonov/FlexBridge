# Issue57 — explicit S3 versions for scanned private files

Planning only. Do not change the application until PR56 evidence head is merged.
Baseline source4ffbe96 has the same runtime as eadac11. Disposable localhost MinIO
matching compose's pinned2025-02-18 release demonstrated that the application URL
issued before a trusted provider-admin overwrite reads the replacement, while an
explicit VersionId URL reads the original. No public overwrite path is demonstrated.
The red assertion and hashes are saved without URLs/credentials. This is actual
storage observation, not an antivirus or live deployment acceptance claim.

Proposed implementation boundaries (review before implementation):

1. Forward0012 preserves every legacy file/proof/history row and ambiguous
   object_version values. Add separate storage_version_id and storage_etag columns;
   never infer a VersionId from a historical ETag or invent provenance. Pair/format
   checks reject empty/whitespace/null version IDs. Decide a new-write trigger that
   requires provenance on entering SCANNING/CLEAN without blocking metadata-only
   changes to preserved legacy rows. Canonical model/baseline94 unchanged, runtime
   count remains111. Upgrade test populated0011 and downgrade preservation policy.
2. Complete-upload pins HEAD's explicit non-null VersionId and ETag for quarantine;
   absence/null fails closed before scan enqueue. Worker reads that exact version
   plus IfMatch and size limit. Private write returns a typed explicit reference;
   no ETag fallback. No version/no provider success means no CLEAN/ack. Scanning
   checks and lease fencing remain. Retried effects may leave unreferenced versions;
   no claim of deletion/retention or exactly-once external PUT.
3. Every private GET signer requires an explicit version ID (owner, ORG staff/
   reviewer, owner continuity, EDU named/reviewer). Centralize clean/reference
   validation and preserve authorization, audit rollback and60-second lifetimes.
   No key-only compatibility fallback, even for legacy CLEAN records. Public
   response must not expose internal keys, credentials/provider errors.
4. New evidence eligibility and EDU revision snapshots pin explicit version/ETag.
   Existing immutable snapshots are not rewritten: old pending evidence cannot
   approve/activate until an explicit new revision with newly uploaded material.
   Already accepted authority/history is not silently revoked by this schema change.
   Document legacy download unavailability/re-upload requirements; recovery/backfill
   needs separate reviewed bytes/hash/scan provenance, not a guessed migration.
5. Readiness checks actual bucket versioning Enabled, not only head_bucket or an
   environment assertion. Readiness is read-only, not a full provider certification.
   Document GetObjectVersion/HeadObject/get-bucket-versioning and least-privilege
   app credentials; actual deployment credentials/IAM changes remain separate.
6. Meaningful PostgreSQL regressions cover provenance migration, fail-closed legacy,
   NULL/ETag provider responses, scan/outbox failure/replay/fencing, scoped downloads
   passing the exact recorded reference, old snapshot rejection, unchanged auth/
   consent/ordinary-teacher behavior. Update trusted CLEAN test fixtures explicitly,
   without weakening guards or pretending fixtures are actual scanned data.
7. Actual disposable MinIO integration covers presigned PUT, completion/scan/apply,
   actual presigned download after same-key replacement, tampered version denial,
   delete-marker/current version and suspended/unversioned failure, owner/scope
   denial and pending outbox on provider failure. AV can be an explicit test double;
   PDF parser and S3 requests must be actual. Check deletion fails closed. Keep
   credentials in memory and redact all presigned URLs from evidence/logs.
8. Make the real integration reproducible in CI without optional skips: install the
   pinned publisher binary for the runner OS with verified SHA256; test fixture starts
   it on localhost random ports with generated credentials and stops only its own
   process. Existing app compose version unchanged in this bounded package. No Docker
   Desktop/WSL install, system-wide service or live bucket modification is needed.

Primary references consulted2026-11-10:

- https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html
  A VersionId selects a particular object version and needs GetObjectVersion.
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
  IfNoneMatch only protects the current key state; it is not historical version pinning.
- https://docs.aws.amazon.com/AmazonS3/latest/developerguide/postVersions.html
  Versioning suspension/null is not an immutable version guarantee.
- https://github.com/minio/minio/releases/tag/RELEASE.2025-02-18T16-25-55Z
  Existing compose version's actual publisher assets used after dl.min.io returned410.

This plan does not certify the old pinned MinIO release as currently supported or
recommend it for new production deployment; dependency maintenance is a separate
infra concern. No pilot, live credentials, identity or legal certification claim.
