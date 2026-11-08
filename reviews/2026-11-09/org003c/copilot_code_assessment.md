# Review findings and changed-input evidence

Copilot CLI's read-only pinned fa40e54749dd6300e866f1ecc9a9833497bd4585 review
completed exit0 with view/glob/grep, writes/shell/MCP/export disabled. Model identity
was not independently reported. The raw response is copilot_code_review.md.

Confirmed lifecycle defect: matching intake replay returned before pending liveness
checks. A revoked contact or original staff grant could still produce a pending
receipt, with tracking unchanged. Approval paths already checked freshness. Three
new regression cases failed against fa40e54; one finalized receipt case passed.
initial_replay_junit.xml preserves that result. The previous263 native and393 CI
passes did not cover these newly added cases and were insufficient to accept this
behavior.

ef4a94b61e5fbd67f0b370fe816a20bb858d630a now locks the existing case after the org,
locks current users, prunes stale pending intent and returns an idempotent closed
receipt. Finalized receipts remain read-only. The tested isolated tree was committed
as ef4a94b, then fast-forwarded into the task branch without changing the running
fa40e54 baseline. Post-fix native9 passed,43.74s: four replay cases, three negative
review outcomes, account reset-proof isolation and the existing parallel full flow.
Complete final401-test CI42534534532/42534538671 passed,219.40s/257.95s.
Follow-up source review completed exit0 with no concrete replay/outcome defect.
The reviewer did not run tests or verify SHA; Codex checked the tree and CI separately.

Coverage gaps from the review were addressed with explicit MODERATOR REJECT and
COMPLIANCE REJECT/NEEDS_INFO tracking/audit/retry tests, and an account reset proof
misrouting fixture that cannot change credentials/auth_version or continuity status.
No public continuity endpoint issues account reset/status continuations. Internal
misrouting fixtures are defense tests, not a claimed external exploit.

Baseline native263 passed,0 failures/errors/skips,857.152s on fa40e54; this is not a
claim that all263 native cases were rerun after the six-line replay change. Final
complete PostgreSQL CI verifies the full updated suite. Second-process service read
does not establish HTTP bearer transport; legal identity and live providers remain
outside the evidence. SQL writers are trusted. Pilot remains false.
