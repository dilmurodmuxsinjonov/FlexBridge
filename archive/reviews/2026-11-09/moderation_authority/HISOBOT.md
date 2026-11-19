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
valid decision controls2, rollback3 and invalid internal sessions3. Affected5 modules
93 passed,367.138s,0 failure/error/skip. Both full502 CI42538509986/42538515162 passed,
378.85s/349.18s on5856dc6. Native times include Windows database cleanup, not API latency.

Actual pinned code-review output found no concrete production defect and requested
role revoke/expiry during the real row-lock wait in addition to the existing paused
pre-query cases. The prior CLI shell session was no longer available when the user
continued; its review output is retained, original exit status is not claimed.
08626bf changes only that parameter list, keeping runtime identical. Final native24
passed37.93s,0 failure/error/skip; these rerun the old22 and add2. The test server had
stopped between user turns; it was restarted before this run, not counted as test success.
Follow-up actual read-only review completed exit0 (`copilot_final_exit.txt`) and confirms
the gap closed, with no concrete remaining issue in its requested scope. Codex checks
SHA/tree and CI separately; the reviewer did not run tests or verify SHA.

Final full504 CI42561301163/42561304587 passed,383.65s/391.71s on08626bf.
Evidence-only head checks/merge remain. Direct database writers/trusted
fixtures and live providers/browser/DR remain outside evidence; pilotfalse.

Separate critical residual confirmed in3 independent native/HTTP refund probes:
after actual finance session revoke or trusted FINANCE-grant revoke, paused first/second
approval still200; second becameAPPROVED and enqueuedREFUND_EXECUTE. No real transfer
was executed. Tracked in Issue51; this moderation fix does not resolve it. Prioritize
51 before EDU after this package's final checks/merge.

Same-source sibling probe also reproduced5 failures,12.06s: actual session revoke
completed while organization lock was held, but legacy/canonical order/refund requests
and payment intent still wrote new rows. Issue51 scope is the four human money methods
and their six route callers; quota publish/transition and trusted HMAC callbacks are
excluded. Actual read-only Copilot planning review exit0 confirms target-lock-before-
authority and breaker/organization ordering, no additional schema/provider dependency.
