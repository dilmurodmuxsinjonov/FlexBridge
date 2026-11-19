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

104c436 source review also found an invitation acceptance/contact-recycling lock cycle.
Codex independently reproduced the analogous invitation-create/public bind cycle:
contact bind201 but invitation503,1 failed/38.04s (`contact_lock_initial_junit.xml`).
The previous69 green cases did not cover it. Both full470 CI42536321623/42536326963
passed on104,343.40s/352.70s; that does not accept this newly found race.

17a0b66 fixes it in an isolated worktree while old affected tests keep running on104:
contact advisory acquisition never waits while holding user authority; target user and
inviter authority use NOWAIT where another account may be held; exact target identity
is re-read before any invitation/FK write. A conflict yields409 INVITATION_BUSY_RETRY
and rolls back the UOW. Current actor MFA/role checks remain. Default org_authority
behavior is unchanged. No identity-service policy change.

Patch native24 passed,127.96s (new4 plus old invitation20), and public-contact5 passed,
40.02s. These5 use actual HTTP challenge/consume and register/contact-bind; only delivery
gateway is replaced. Create/accept vs register/bind, existing target/inviter user locks,
newly discovered contact target, fresh retry and no partial grant/invite were verified.
29 patch cases are separate from104 native69/old affected baseline. Old affected8
modules completed187 passed,642.05s on104; root source stayed unchanged during this run
and only then fast-forwarded to17a0b66. Both full479 CI42536888052/42536892278 passed.

Pinned follow-up review exit0 found no concrete production defect. It requested that
race events signal after the try-lock attempt (making observed contention explicit)
and that an existing contact changing before the target pin be tested as well as a
previously absent contact appearing. Both test refinements passed native10,42.19s on
7386da2; runtime guards remain unchanged from17a0b66. The new contact test uses public OTP proof/bind and verifies
409/no invitation, then fresh retry targets and admits the new holder. Final7386da2
full480-test CI42537111572/42537115610 passed,358.80s/311.51s. No failures/errors/skips.

Actual final test-delta review exit0 confirms both recommendations addressed and no
concrete remaining issue in the requested scope. It did not run tests/verify SHA;
Codex checks the pinned source tree and full CI separately. Native test timing includes
Windows database cleanup and is not an API performance measurement.
