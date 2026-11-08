# AUTH-CODEX-002 — organization transaction authority

Old runtime ef4a94b independent changed-state evidence:

- `initial_junit.xml`: API075 actual own-session DELETE completes200 after transient
  MFA, but pending membership revoke still completes200/REVOKED;1 failed,11.76s.
- `expanded_initial_junit.xml`:15 request variants,14 failed/1 passed,54.64s.
  The changed profile patch passed because a second nested MFA preflight observed
  this particular revocation timing. It does not protect a wait after that preflight.
  Download failed with503 because live storage was not configured; that alone does
  not establish a private URL was returned.
- `download_initial_junit.xml`: explicit synthetic URL-signing adapter,1 failed,
  8.80s; stale download reached signing and returned200. No live S3 acceptance claim.
- `wait_initial_junit.xml`: actual organization row lock held on an independent
  connection; HTTP own-session revoke or MFA-disable committed before lock release.
  API075 still200/REVOKED in both cases;2 failed,10.73s. The lock connection does not
  set the service transaction ContextVar, so HTTP calls do not inherit that transaction.

The fix reuses mfa_authority/org_authority after business locks and holds current
user/session/scoped authority through the UOW. Governance member services receive
the actual ActorContext. Registration/join/bootstrap and invitation recipient role
semantics remain. Historical grants/migrations are unchanged. Exact scope is documented
in backend/ORGANIZATION_AUTHORITY.md. Native changed-state43 passed,153.14s and
transactions26 passed,94.88s (1 framework warning each). Actual security changes while
waiting for an independently held org row lock are denied; opposite session/MFA and
scoped-grant revocations wait on PostgreSQL locks until the authorized commit. Eight
injected audit failures leave no business/audit effect. Direct service calls with
absent/foreign/unknown sessions cannot create membership. Old affected modules and
final source review/full CI are pending; no package acceptance is claimed yet.

Initial transaction test harness run:17 passed/9 failed,95.26s,
`initial_transactions_junit.xml`. Eight tests incorrectly expected injected RuntimeError
to escape HTTP; the existing application maps it to503 DEPENDENCY_UNAVAILABLE. They now
assert that exact response plus full business/audit rollback. A direct-service test used
an empty string as a UUID and produced DataError; an absent session is now represented
by None. Unknown valid UUID and another user's session remain separate cases. These
are test-harness corrections; no runtime check or SQL constraint was weakened.

Actual read-only Copilot CLI scope review completed exit0 using view/glob/grep, with
writes/shell/MCP/export disabled. It did not run tests; model identity was not independently
reported. Initial moderation risk from that review was independently reproduced by
Codex in2 tests and tracked separately in #48. Not included in this fix. Pilotfalse.
