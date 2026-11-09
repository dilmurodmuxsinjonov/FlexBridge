# Codex implementation decisions after planning review

Read-only Copilot retry completed with observed exit0. The initial invocation lost
its exec handle at continuation, had no matching live CLI process/output/exit file,
and is recorded as interrupted, not as a completed review. No model identity,
execution, SHA or pilot certification is inferred from either invocation.

- Explicit version/ETag, fail-closed legacy, readiness and real provider assertions
  are accepted recommendations. Also bind storage_bucket in the reference; VersionId
  is scoped to bucket/key. A changed configured bucket must fail closed instead of
  using old provenance to sign a different bucket. Do not bind the literal private
  endpoint URL, because the intentional public endpoint differs.
- The review's fencing concern is narrowed by actual code: outbox.py already locks
  and compares claim_token before calling apply in the same transaction. That is
  the existing worker-attempt fence; apply_scan is not a standalone public worker
  entry point. Do not invent an unneeded second attempt counter or claim the fence
  is absent. Add a real FILE_SCAN stale-token regression, not only a generic FENCE
  event. Bind scan results to the source key/version/ETag/size and require that source
  still matches at application; different source generations must never publish a
  stale result. Failed result application can leave an orphaned private version;
  retry must still scan the pinned quarantine source and publish only a fenced result.
- Preserve legacy rows byte-for-byte where relevant, including accepted grants,
  decisions and immutable snapshots. New downloads/approvals with unknown provenance
  fail closed. Explicit reupload/new pending revision is needed; no guessed backfill,
  implicit rejection or revocation of already accepted historical authority.
- Source can be versioned at upload completion and bucket versioning later suspended:
  exact-version source GET still must read that source, but a private PUT without a
  new immutable version must not publish CLEAN. Missing and literal null are both
  rejected. The actual MinIO suspended PUT omitted VersionId (not literal "null");
  AWS's literal-null case also needs a deterministic SDK response regression.
- Readiness is a read-only live Enabled check, plus existing bucket availability.
  No environment flag or successful HEAD substitutes for that check. Provider
  availability and version retention/deletion permissions still need deployment
  acceptance; this package does not prevent an administrator deleting old versions.
  Such deletion must fail retrieval, never silently select replacement bytes.

Proceed only after PR56's exact latest head CI/merge. Root Codex owns app/migration/
test/CI/docs changes. Copilot owns no files and its output is source analysis only.
