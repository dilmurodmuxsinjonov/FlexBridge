# AUTH-CODEX-003 — initial moderation transaction authority

Separate confirmed defect from organization PR49, implemented only after49 merged.

Changed-state old-source evidence:

- `initial_junit.xml`:2 failed,12.78s on ef4a94b. Actual HTTP session revoke or trusted
  SQL MODERATOR revoke completed; paused decision still201/REJECTED/one action.
- `expanded_initial_junit.xml`:8 failed,31.82s on104c436. Session/MFA-disable/account/
  auth_version/platform-grant revoke/expiry changes and actual opportunity-lock waits.
- `lock_initial_junit.xml`:2 failed,10.71s, a repeat subset with before-cursor SQL
  observation replacing the service-preflight signal. The lock holder uses a separate
  engine connection, so HTTP does not inherit its transaction ContextVar. This is
  preexisting authenticated in-flight authority, not anonymous access.

One service and its single production API caller now pass actual ActorContext, acquire
the opportunity lock and then call the existing moderator_authority before revision,
policy/write effects. User/session/grant locks last through commit/rollback. The global
middleware already requires MODERATOR MFA. Self-author, DRAFT, case/action/audit and
appeal provenance remain; no migration/dependency/endpoint change. Expiry is checked
at the post-lock boundary, not frozen through commit by a row lock.

Actual read-only Copilot planning review completed exit0 (view/glob/grep; no writes,
shell/MCP/export). It confirmed caller scope/order and stated the expiry boundary.
It did not run tests or verify SHA; model identity was not independently reported.
Native22 passed,87.69s,0 failure/error/skip,1 framework warning: changed-state8,
opposite serialization3, parallel single effect1, cached-role/self-author denial2,
valid decision controls2, rollback3 and invalid internal sessions3. Affected suites,
complete CI and pinned code review are pending. No package
acceptance or pilot readiness is claimed. Direct database writers/trusted fixtures
and live providers/browser/DR are outside this bounded evidence.
