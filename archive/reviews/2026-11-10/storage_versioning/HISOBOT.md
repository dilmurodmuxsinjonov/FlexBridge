# STORAGE-CODEX-001 — explicit object versions

Issue57 / PR58. Validated source: b251644fa2c00439cde495ae52ebc3c85b629d40.
Runtime is unchanged from afd343ab749a1a2131172e662769ff8fb2369d2c; b251644
corrects the trusted SCANNING test fixture and records evidence/history only.
Complete Linux PostgreSQL+actual localhost MinIO CI passed757 tests on the exact
b251644 head: push42687285321 in530.01s and PR42687299361 in513.04s, one framework
warning per run. Metadata includes attempts, jobs and actual pytest log summaries.
Evidence-head checks and matching-head merge follow separately. Pilot remains false.

Previously, key-only URLs could retrieve a newer object at the same key despite
metadata comparison. An independent actual MinIO observation on the prior runtime
confirmed a trusted provider administrator's overwrite changed issued-URL bytes;
an explicit VersionId URL retained the original. This is not a demonstrated public
overwrite or authentication exploit. The raw red probe/result/exit are retained.

Forward0012 adds explicit bucket/VersionId/ETag columns and new-write guards without
guessing legacy object_version provenance. Canonical94/runtime111 table counts do
not change. Existing file values, accepted authority, decisions and immutable proof
history are preserved. Unknown legacy references cannot download, link a new CV or
support new evidence/activation. Actual reupload and explicit new revision are needed;
no historical backfill, review/consent fabrication or silent role revocation occurs.

Completion pins HEAD's exact version/ETag and size in the file and queued event.
The worker reads that version with IfMatch, verifies provider response identity and
length, scans those bytes and requires an explicit non-null private PUT version.
Source comparison and the existing outbox claim_token fence protect result
application. Successful PUT followed by failed apply/lost lease may leave orphaned
versions; no exactly-once external PUT, retention or purge guarantee is claimed.

All six private signing callers pass exact stored references; scoped checks, short
URLs and audit rollback remain. EDU revision snapshots also pin explicit provenance;
an old snapshot needs a new reviewed/accepted revision. A changed configured bucket
fails closed. Readiness reads live Enabled versioning; it does not certify actual
deployment IAM/write/read/retention. Provider errors return generic503 without raw
provider data. Version deletion fails retrieval rather than selecting replacement.

Validation stages are retained separately; overlapping counts are not added:

- Initial runtime30 passed44.77s before later source-event/unique-fixture/CV changes.
- Initial actual S3 integration3 passed/3 failed15.39s: all three failures were the
  harness's aggregate_id lookup rather than the real aggregate_key. No guard relaxed.
- Initial expanded22 yielded19 passed/3 failed36.37s: UUID/string representation,
  factory misuse and one stale-token retry ClientError. That provider error produced
  no CLEAN/ack. Its operation/code were not captured then; no cause or invented
  production fix is asserted. Diagnostic follow-up4 passed17.68s and later integration
  passed; a transient unexplained earlier provider failure remains in the evidence.
- Expanded27 passed44.51s: new25 storage cases plus existing2 private views, including
  actual7 MinIO scenarios, populated0011 upgrade, reference/DB guards, old snapshot
  rejection/fresh revision acceptance and scoped signing/audit rollback. AV was an
  explicit test double; S3, PostgreSQL and PDF parsing were actual.
- Fifteen affected old modules240 yielded239 passed/1 fixture failure350.06s.
  New0012 correctly rejected a SCANNING fixture without provenance. The fixture now
  models quarantine VersionId/ETag, with object_version=ETag; its existing non-CLEAN
  CV denial assertion is preserved. Entire candidate44 passed43.39s after correction.
  The preceding collection0-test filename typo is a harness artifact, not coverage.
- Both afd343a full runs failed exactly that SCANNING fixture:756 passed/1 failed
  in460.99s/431.52s. Current full757 runs above pass after the fixture-only correction.
  The757 comprises merged baseline732 and new25; it is not a sum of native stages.
- Actual read-only Copilot source review exited0 and found no concrete defect in
  the version-binding scope. REVIEW_CONTEXT.md qualifies its actual root cwd/source
  cleanliness; the literal prompt/output are retained. A later isolated read-only
  review exited0 and found the fixture delta retained its negative CV assertions;
  that output is in the adjacent files_authority evidence folder. The agent did not
  run tests, verify SHA, attest model identity or certify pilot. Codex independently
  checked source diff/manifest and actual local/CI execution.

Actual CI installs the publisher-hash-pinned Linux MinIO executable and runs the S3
tests without optional skips. Local Windows tests use the same release matching
existing compose. This is reproducibility, not current production support/security
certification for that release. Generated credentials/URLs are not published.
The installer and test server do not install system services or modify live buckets.

Important residual: Issue59 independently confirms current-session authority missing
in the three owner file services. On pinned afd343a, actual HTTP completion waited
on the real file row, actual logout200 completed, then the request resumed202,
SCANNING and queued1 event. The native1 red probe33.57s uses synthetic HEAD/presign,
actual sessions/logout/SQL waits. This is authenticated in-flight authority, not
anonymous/foreign access or actual scanning/provider behavior. It is preserved in
reviews/2026-11-10/files_authority and is the next package after PR58. Storage
version binding does not imply session-authority acceptance. Candidate/CV sibling
self-service authority remains a separately explicit audit scope.

source_manifest.json hashes pinned Git blob bytes. contracts.json remains132 total:
49 explicit/83 placeholders/0 missing; registration is not functional acceptance.
Windows tooling is separately recorded: isolated project venv works, but Docker/WSL
installation did not finish after native administrator launch was canceled. No
automatic reboot or Docker engine readiness is claimed. ANTIGRAVITY_HANDOFF.md and
the project journals identify remaining setup and work. Frontend, remaining R1
contracts/AC, actual live providers/credential rotation/legal identity and DR remain
open; this package is not a pilot acceptance certificate.
