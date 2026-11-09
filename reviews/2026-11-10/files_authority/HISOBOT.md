# AUTH-CODEX-005 — owner file transaction authority

Issue59 / draft PR60. Validated source370d9c32229f023537ff1cdacc77bc53f8bb3c30.
Complete Linux PostgreSQL+actual MinIO CI passed785 tests on this exact head:
push42697954266 in534.16s and PR42697965001 in458.37s, one framework warning each.
Saved metadata binds run/attempt/jobs/head and actual pytest summaries. Evidence-only
head checks and matching-head merge follow separately; this is bounded backend
validation, not pilot acceptance or closure of all session-authority boundaries.

Upload initiation, completion and owner download now take actualActorContext and
recheck current account/session/user binding, auth version, revocation, expiry and
existing global sensitive-role assurance inside their transaction. Current roles
come from PostgreSQL, not cached labels. There is no user-ID-only human fallback.
The unchanged onboarding account_authority policy is shared from authority.py;
ordinary PASSWORD/teacher-only and current sensitive MFA retain their behavior.

Completion/download take owned file business locks before current user/session
authority and provider work; initiation authorizes before presign/insert. Locks
remain through commit. Provider failure rolls rows/outbox back. Current ownership,
CLEAN/nondeleted references, short version-pinned GETs and source/lease fences remain.
Expiry is evaluated at the guarded boundary; PostgreSQL locks do not freeze wall
clock through arbitrary provider delay. A recorded authenticated upload remains a
trusted asynchronous scan after logout; no fake worker user session is manufactured.

Evidence stages are separated rather than added as inflated unique coverage:

- Initial pinnedafd343a HTTP/native probe failed1 in33.57s: pending completion was
  observed waiting on the actual file-row holder; actual logout200 completed; the
  request still resumed202, SCANNING and queued1 scan. HEAD/presign were explicit
  test doubles, not S3/AV execution or anonymous/cross-user exploitation.
- Expanded b251644 probes initially failed15 in22.767s. Twelve were actual denial
  assertions; three were invalid self-grant fixture writes correctly rejected by
  chk_platform_grant_not_self. Distinct trusted grantor correction did not relax the
  production constraint. Corrected15 failed19.269s with201/202/200 responses across
  three methods and logout/expiry/auth-version/suspension/late sensitive role.
  Original and corrected probes overlap. The captured corrected probe is explicitly
  reconstructed from the preserved initial plus recorded fixture correction; no
  historical byte hash is claimed. Later tests count HEAD calls and add MFA controls.
- Initial new27 native passed36.60s: all stale denials, reverse actual logout waits,
  current PASSWORD/MFA controls, forged-session rejection and provider rollback.
  Affected storage/EDU72 native passed102.01s, including actual8 MinIO cases and
  recorded-upload logout->scanCLEAN/original bytes/old owner token401.
- The full785 above contains merged baseline757 plus27 new authority cases and1
  added S3 worker/logout case. Native subsets and repeated diagnostic runs are not
  added to that total. Missing MinIO setup fails, never silently skips real S3 tests.
- Actual isolated read-only Copilot source review exited0 and reported no findings
  in the requested file-authority scope. Its output distinguishes source review
  from executed tests, current-source SHA, model identity and pilot certification.
  Codex checked the clean detached worktree and collected native/CI/source evidence.

Wait claims are precise: completion uses an actual row lock; the old download plain
SELECT was held by an actual file-table lock. Initiation has no existing business
row and uses a service-entry Event barrier after real HTTP authentication; no SQL
wait is claimed there. Reverse cases observe holder PID through pg_blocking_pids
with one isolated pending request, not a separately traced HTTP backend PID.
Administrative state/role changes and CV/document metadata are trusted fixtures.

The S3 tests use actual localhost MinIO requests/PDF parsing with an explicit AV
double. Separate Q-014 local setup used the official freshclam updater (exit0) to
download databases and actual INSTREAM adapter against a temporary localhost clamd
accepted a generated benign431-byte PDF. The owned daemon stopped. That observation
does not certify malware detection, an ongoing service, full pipeline or live Linux
production behavior, and does not rewrite the older mocked-AV test scopes.
Docker/WSL installation remains incomplete after canceled native administrator launch.

Confirmed next scope: Issue61. On this same370d9c3 source, nine independent candidate
self-service probes still failed17.20s after actual logout200 and observed SQL waits:
five canonical writes, two private profile/schedule reads and two legacy availability
adds. Writes changed candidate business/audit rows; private reads returned own
candidate data. This is authenticated in-flight authority, not anonymous/foreign
disclosure. Earlier response-only5, post-state5, read2 and legacy2 overlap these9.
Legacy siblings are included in the next plan so new canonical guards cannot be
evaded through alternate human callers. Initial7-path and follow-up9-path planning
reviews are retained honestly; no61 implementation is claimed in this package.
Evidence: reviews/2026-11-10/candidate_authority. Current green785 does not close61.

No migration/dependency/canonical handler added. Tested migrated schema remains0012/
111 tables, historical canonical94; registration49 explicit/83 placeholders is not
functional acceptance. source_manifest hashes pinned Git blobs and contracts.json
is registration inventory. Candidate authority61, remaining R1 contracts/AC, frontend,
actual live IAM/provider/retention/identity/legal evidence and DR remain open.
ANTIGRAVITY_HANDOFF.md and project journals identify exact next steps. Pilotfalse.
