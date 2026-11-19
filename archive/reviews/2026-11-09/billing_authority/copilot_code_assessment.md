# Human money review and observed boundaries

Actual Copilot CLI planning/code/replay-delta/wait-graph reviews used view/glob/grep
only, with writes/shell/MCP/export disabled. All exit0 were observed and saved. No
model identity was independently reported. Reviewers did not run tests or independently
verify SHA; Codex checked pinned Git trees and validation separately.

The d88 code review found no concrete implementation defect in the four human methods
or six callers: business rows precede current MFA/scoped authority and claims/state
errors; audit/outbox share the transaction. It requested matching replay after grant
revocation, supplementing existing logout/MFA replay and new-request role cases.

895fb8c adds exactly those2 role cases and an actual logout/password+TOTP/new-session
positive receipt test, all3 native passed. Follow-up requested direct wait-graph proof
rather than relying only on before_cursor_execute and unfinished future.1368ee5 adds
blocker PID/wait_for_blocker before authority changes, strengthening all36 pre-authority
wait variants. Native full78 passed104.23s. Runtime has not changed from d88.

Final review confirms wait proof closed. Precision boundary: wait_for_blocker matches
any backend blocked by that holder, without the request backend PID. Isolated database,
one pending request and its uniquely held target row make this reasonable evidence;
strict request-to-PID attribution is not claimed. This is a test-proof improvement,
not a demonstrated production bypass. No new concrete implementation defect was found.

Baseline75/old137, intermediate3 and final78 overlap and are not summed as unique
coverage. Initial refund3/checkout5/target-repeat3 failures are changed-state evidence,
with repeated paths explicitly identified. Prior full579 CI passed; final full582 CI
42564327339/42564331479 passed437.43s/441.90s. Evidence-only checks/merge remain.
Publication hygiene and registration inventory do not certify acceptance.

Completed first-stage approvals keep the existing historical decision policy; no new
retroactive policy is invented. Expiry is evaluated at the post-lock guard; row locks
do not freeze time. Direct DB writers/HMAC/admin fixtures remain trusted. Quota publish/
transition, live merchant/provider/secret rotation/browser/hardware/DR/pilot are outside
this bounded fix. Queued REFUND_EXECUTE is not proof of a real executed transfer.
