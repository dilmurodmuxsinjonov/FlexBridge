# Explicit versions for scanned private objects

Issue57 / draft PR58 introduces forward0012_file_storage_versions. This package is
under validation. It does not certify live infrastructure, provider retention,
antivirus updates, identity/legal evidence or pilot readiness.

Files record storage_bucket, storage_version_id and storage_etag separately.
Legacy object_version is retained; it previously mixed quarantine ETags and private
VersionIds. Migration never guesses which kind it held. Canonical baseline94 is
unchanged and the runtime still has111 tables. New SCANNING/CLEAN writes need an
explicit complete reference. Empty/whitespace/literal-null VersionIds, partial
references and removal of provenance fail. Legacy metadata/history remains stored.

Upload completion checks length and requires HEAD's actual non-null VersionId and
ETag. It stores that reference and pins key/size/bucket/version/ETag in the scan
event. The worker reads that exact VersionId with IfMatch and rejects mismatched
provider response metadata or unexpected length. It scans those bytes, computes
SHA256 and writes a content-addressed private key. Private PUT must return its own
explicit reference; an ETag never substitutes for VersionId. Missing provenance,
provider outage or suspended/unversioned writes cannot publish CLEAN or acknowledge
the pending scan as successful.

The existing outbox claim_token fence is checked under its row lock before result
application. Source references are also compared before scanning and at application.
A stale worker/new generation cannot replace the current file reference. An external
PUT can succeed before application fails or a lease is lost; retries can leave
unreferenced private versions. There is no exactly-once external PUT or purge claim.
The existing five-attempt outbox limit remains; reconciliation is not automatic.

Every owner, organization staff/reviewer, owner-continuity and institution named/
reviewer download passes the stored reference to the signer. URLs select VersionId
and expire60 seconds later. The configured bucket must still match the stored one;
configuration changes do not silently move old references. Provider exceptions are
mapped to a generic503 without raw responses or keys. Scoped authorization and
audit writes remain in their existing transactions; failed signing rolls audit back.

New formal evidence, CV linking and institution revision snapshots require explicit
provenance. An old pending institution snapshot cannot approve/activate merely
because its old hash/object_version still matches. Requesters need an explicit new
revision and new review/personal acceptance. In a real legacy database, upload fresh
material with new file IDs first. Unknown legacy files and queued scans cannot be
silently repaired from a current HEAD or guessed ETag. Existing accepted grants,
decisions, consent and history are not revoked or rewritten by this migration.
Recovery of inaccessible historical bytes needs a separately reviewed process with
actual hash/scan/provenance evidence. No automatic historical recovery is supplied.

Readiness reads actual bucket versioning and requires Status=Enabled as well as
bucket access. This is read-only and does not prove all write/read/retention/IAM
guarantees. Deployment needs GetBucketVersioning, GetObjectVersion/HEAD access and
private PUT permissions. Use a dedicated least-privilege identity; actual credential
rotation and production policy deployment remain separate. Administrators may still
delete retained versions. Retrieval then fails instead of selecting replacement
bytes. Version pinning does not replace retention/Object Lock or deployment review.

## Reproducible checks

Use the project interpreter and an isolated PostgreSQL server with createdb rights:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe scripts/prepare_test_minio.py --directory D:/Codex/.tools/minio-2025-02-18
$env:MINIO_TEST_BINARY='D:/Codex/.tools/minio-2025-02-18/minio.exe'
$env:FLEXBRIDGE_TEST_ADMIN_URL='postgresql+psycopg://flexbridge_test@127.0.0.1:55440/postgres'
.venv/Scripts/python.exe -m pytest backend -q --junitxml=backend/.data/junit.xml
```

The installer verifies publisher-pinned SHA256. Tests start a disposable localhost
MinIO with generated credentials/random ports, create isolated buckets/databases,
and stop only their own process. CI prepares the Linux binary and runs the same
tests without optional skips. Missing binary configuration fails rather than
silently skipping actual S3 evidence. The pinned release matches existing compose
for reproducibility; this is not a current production support/security assessment.

Actual integration covers presigned PUT, exact source scanning and private GET,
same-key replacement, signature tampering, delete markers/version deletion,
suspended writes, source-generation changes, stale scan leases, apply failure/retry
and live Enabled/Suspended/missing-bucket readiness. PDF parsing is actual; antivirus
is an explicit test double in these S3 cases. No credentials or presigned URLs are
published. Earlier red provider observation, harness failures, scoped/native results
and later pinned source/CI reviews are recorded separately in
reviews/2026-11-10/storage_versioning. Do not add overlapping run counts.

Primary protocol references:
https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html
https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
https://docs.aws.amazon.com/AmazonS3/latest/developerguide/postVersions.html
