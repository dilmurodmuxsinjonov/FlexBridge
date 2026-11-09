# Initial moderation review and evidence boundary

Actual read-only Copilot planning, pinned code and final delta reviews used view/glob/
grep, with writes/shell/MCP/export disabled. Planning and final exit0 were observed;
the initial code-review shell status was unavailable after a later user turn, so only
its retained output is claimed. Model identity was not independently reported. Reviewers
did not run tests or independently verify SHA; Codex checked source trees and validation.

Initial source review found no concrete reachable bypass, regression or deadlock in
the scoped fix. It requested that current-grant revoke/expiry be exercised while
actually waiting on the opportunity row, in addition to paused-before-query cases.
08626bf adds those2 variants. Native24 passed37.93s and final read-only review confirms
the gap closed with no concrete remaining issue in that scope. No runtime source
changed after5856dc6. Full final504 CI42561301163/42561304587 passed383.65s/391.71s.
Evidence-only head checks and merge remain.

Native5856 new22/old affected93 and final086 native24 are separate evidence. Final24
reruns22 and adds2; they are not summed as distinct coverage. Initial failure subsets
also overlap and demonstrate changed-state regression, not a count of independent
vulnerabilities. Actual session/MFA HTTP and trusted administrative SQL mutations are
distinguished. Expiry is evaluated at the post-lock guard, not guaranteed through commit
by freezing time. No live/browser/provider/DR/pilot certification follows.

The separately reproduced refund approval race (Issue51) remains open and has not been
resolved by this initial-moderation change. A queued execution is not an executed refund.
