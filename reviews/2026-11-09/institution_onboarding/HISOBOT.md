# EDU-CODEX-001B — reviewed institution onboarding

Issue55 / PR56. Validated source: `eadac1149ba66d8e34f77190c21f1c6211183a65`.
Complete migrated PostgreSQL backend CI passed732 tests on this exact head:
PR42672853806 in450.27s and push42672846232 attempt2 in508.64s, one framework
deprecation warning each. Saved metadata includes head, job, attempt and actual log
summary. Evidence-only head checks and matching-head merge are separate steps.
This is bounded backend validation, not pilot or live-provider acceptance.

API017/096/097 implement signed-in requirements, current-MFA intake and private
case status. First-institution claims request the submitting user's first
COORDINATOR appointment. An existing current coordinator can request a named
registered TEACHER. Independent assigned moderator approval and exact-revision
personal acceptance are both necessary before activation, in either order. Client
roles, paid flags or domains do not grant authority; a known institution without
current authority cannot reopen bootstrap. Ordinary teacher-only PASSWORD sessions
retain their existing scope; globally sensitive actors require current MFA.

Explicit revisions, decline, revocation and scoped document views preserve history.
Stale contacts/security/documents, a replaced original coordinator grant, wrong
revision and expired pending consent cannot activate an old proposal. Consent is
valid24 hours; the three-weekday first-response target is separate. Omitted end
dates preserve previous limits; explicit null needs new approval and consent.
Matching retries return receipts without duplicate grants or audit events. Current
authority is rechecked after business locks using the actual session and held until
commit; foreign authority/contact contention returns atomic409/retry. Logout
invalidates further session actions; explicit decline/revocation withdraws recorded
intent. Logout does not silently retract already recorded intent.

Forward0011 adds four append-only proof tables: runtime111, historical canonical94.
Normalized registry collisions abort the upgrade for explicit reconciliation.
Invalid structural legacy grants are closed with migration audit provenance;
valid trusted history is retained without fabricated review/consent. Grant identity,
revocation and parent bindings are protected; revoked membership history can coexist
with one new active membership. The baseline SQL/model was not rewritten.

Validation is separated rather than added into an inflated coverage total:

- On40e5ea3 the whole new native package52 passed236.823s, including populated
  upgrade/collision rollback, security, concurrency and transaction modules. Nine
  affected old modules303 passed891.982s. Full727 CI passed twice at that stage.
- Actual read-only Copilot reviews identified missing private-response/body-limit
  coverage and a trusted direct-SQL sensitive-consent MFA gap in the earlier3a0f917
  prototype. Three independent probes failed there; fixes and expanded sensitive
  role regressions are retained. Public HTTP consent already required MFA.
- The40e5ea3 follow-up probes failed2: duplicate claim audit and omitted end-date
  semantics. Fixes include explicit-null and terminal receipt controls. The
  pre-contact-fix native55 passed165.333s. It is not a final57-case native run.
- Codex separately reproduced a contact-presence oracle on40e5ea3: an authenticated
  ungranted claimant received different403 codes for known/missing recipient contacts.
  This was not an anonymous write or grant bypass. Recipient lookup now follows
  current coordinator authority, eligible owned materials and own verified contact.
  Foreign agreement selection is institution-scoped; errors follow requester checks.
  Privacy/onboarding/concurrency21 passed64.795s. Final privacy/follow-up/Tashkent
  scope36 passed86.459s. Test date fixtures use business timezone, not host date.
- Final source contains57 new cases; complete732-test CI above covers them and
  the675-test merged baseline. Overlapping native runs are not unique totals.
  Final read-only Copilot follow-up exited0, confirmed earlier findings closed and
  found no concrete remaining regression in the requested scope. It did not run
  tests, verify Git SHA, independently attest its model or certify pilot. Codex
  pinned the worktree and collected actual execution/source evidence.
- Earlier9fc6c5a runs and first eadac11 push attempt failed at GitHub startup
  before any job/test with an Internal server error annotation. Records are retained
  separately. Successful second push attempt is not a first-attempt success or a
  fix to an application test failure.

Native tests use disposable PostgreSQL databases, actual HTTP sessions and observed
pg_blocking_pids waits. The holder PID is correlated with an isolated pending
request; a separately traced HTTP backend PID is not claimed. Trusted administrative
contact/document/import fixtures and mocked storage are not actual identity, legal
signature, scanning, browser, delivery or live-provider evidence. Harness mistakes
and red probes are retained alongside passing XML in native_results.json.

The application writes content-addressed private keys and compares recorded document
hash/version metadata before issuing scoped60-second URLs. Current presigned GETs
still address a key, not a provider VersionId. This conditional retrieval-integrity
limitation is open as Issue57, an integration gate before broader live-provider/pilot
claims; no public overwrite exploit is demonstrated.

source_manifest.json hashes pinned Git blob bytes. contracts.json records132
canonical registrations:49 explicit,83 placeholders,0 missing. Registration is not
functional/security acceptance. Additional coordinator delegation, recovery, student
intake/enrollment/supervision, exports/official grades, frontend, live credentials/
providers, DR and overall acceptance remain open. Pilot remains false.
