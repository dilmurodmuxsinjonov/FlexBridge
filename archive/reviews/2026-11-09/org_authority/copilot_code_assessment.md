# Source findings, reproduction and changed-input validation

Actual Copilot CLI scope/code/follow-up/test-delta reviews used view/glob/grep only,
with writes/shell/MCP/export disabled; all completed exit0. No model identity was
independently reported. Reviewers did not run tests or independently verify SHA.
Codex verified Git trees/SHAs, implemented and ran the native/CI validation separately.

The 104c436 review found the acceptance/contact-recycling advisory-lock/user-lock cycle.
Codex independently reproduced the analogous create/public-bind cycle: binding201,
invitation503. A new regression failed even though native69 and both full470 CI were
green. The original suite was insufficient to accept that interleaving. No authority
bypass or partial commit was demonstrated; the confirmed defect was a request failure
from a database lock cycle.

17a0b66 keeps current MFA/session/org authority and uses nonblocking contact acquisition,
NOWAIT for other-account target/inviter locks, exact contact-identity recheck and409
INVITATION_BUSY_RETRY with UOW rollback. Native29 passed: new contact4 plus old invite20,
and public OTP/register/bind5. Default org_authority behavior remains unchanged.

Follow-up source review found no concrete production defect but requested two test
improvements. 7386da2 signals contention after the database try-lock and adds existing
contact replacement before the target pin; the separate absent-to-present case stays.
Native10 contact cases passed. Final delta review confirms both recommendations were
addressed and found no concrete remaining issue in its requested scope. Runtime source
is identical to17a0b66. Final full480 CI42537111572/42537115610 passed on7386da2,
358.80s/311.51s. Evidence-only head checks and merge remain.

Baseline104 native43/26/187, patch17 native24/5 and final738 native10 are separate
evidence. They overlap (20 old invitation and9 contact cases) and are not summed as
distinct coverage or claimed as one final native full-suite run. Initial test-harness
9 failures are retained: expected HTTP503 mapping and absent UUID representation were
corrected; runtime constraints were not weakened. XML stack-trace trailing spaces were
normalized for Git; failure counts/messages remain.

Issue48 initial moderation race is separately reproduced and remains open. Test delivery
and signing adapters, trusted role/contact/CLEAN-file fixtures and direct DB authority
do not establish live provider/browser/DR/legal identity or overall pilot acceptance.
