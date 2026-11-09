Private download authorization previously signed GET by key after checking DB metadata.
This change binds quarantine scans and private downloads to explicit bucket,
VersionId and ETag references, so provider-admin same-key replacement cannot retarget
a recorded file. No ETag inference or key-only legacy fallback is allowed.

Forward0012 preserves ambiguous legacy files and accepted authority/history while
requiring complete provenance on new SCANNING/CLEAN writes. New CV/evidence and
EDU revision snapshots require explicit references. Old pending evidence needs an
explicit new reviewed/accepted revision; migration does not fabricate provenance.
Source/event/result comparisons complement existing outbox claim_token fencing.
Readiness requires live Enabled versioning. Failed provider calls map generic503;
scoped signing failure rolls audit back. External retries can leave orphan versions.

Validated source b251644fa2c00439cde495ae52ebc3c85b629d40 passed complete757-test
Linux PostgreSQL+actual localhost MinIO CI twice: push42687285321 in530.01s and
PR42687299361 in513.04s. All25 new storage cases are included. Native expanded27
passed44.51s; old affected240 had239 passed/1 invalid SCANNING fixture, then corrected
candidate44 passed43.39s. Both prior afd343a CI failures were exactly that fixture;
production guards were retained. Source review and fixture-delta review exited0
with no concrete scoped defect. Overlapping counts are not summed. All red/harness/
unexplained provider failure stages, exact source manifest and limits are retained
in reviews/2026-11-10/storage_versioning/HISOBOT.md. Evidence-head checks follow.

Actual S3 cases cover replacement/tampering/deletion, suspended writes, source changes,
stale FILE_SCAN/apply rollback/retry and live versioning readiness. AV is explicitly
doubled; PDF/S3/PG are actual. Pinned MinIO matches compose for reproducibility, not
production support/security certification. Live IAM/retention remain separate.

Issue #59 is a confirmed separate authenticated file-session revocation race, the
next package; this storage fix does not close it. Antigravity handoff/setup notes
also record that Docker/WSL installation is incomplete after native administrator
launch was canceled. Runtime0012/111 tables, canonical94,49 explicit/83 placeholders.
No live provider/identity/legal/DR or pilot acceptance claim.

Closes #57
