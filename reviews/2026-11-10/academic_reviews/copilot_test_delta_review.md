I’ll inspect the two current test files and the referenced scope/review notes, then assess whether
the changed assertions or test setup leave concrete authorization, auditing, connection-context, or
concurrency gaps.

Review outcome: the session-revocation assertion is correct: it requires the legitimate logout audit
event while still requiring zero review/proof rows. The legacy test keeps the alternate engine
selected through login and HTTP requests, then restores it before database cleanup. Its
actual-session and read-200/write-403 claims are supported by the test flow. I found no concrete
runtime P1/P2 defect from these tests alone.

Two coverage gaps remain:

 - P2 — concurrency tests do not establish database overlap (test_academic_reviews.py:80–92;
test_academic_review_intents.py:20–61). The barriers synchronize thread start, but the requests may
reach the service serially. The expected 201/409 outcomes can therefore pass without exercising the
contested lock or check/insert race. The cross-placement setup correctly uses distinct institutions
and hosts; it still needs evidence both requests are in flight at the relevant database operation,
as the lock-wait tests establish with wait_for_blocker.
 - P2 — no unauthenticated request targets the alias (test_academic_review_intents.py:81–89). The
401 assertion covers only /api/v1/log-revisions/.../academic-reviews. The alias is exercised with
authenticated users, including the legacy-consent denial, but that does not independently establish
its unauthenticated behavior.

The second-institution teacher appointment/grant is trusted database fixture setup, not external
identity certification; the test’s HTTP claims should be read within that boundary. No edits or
execution were performed.

