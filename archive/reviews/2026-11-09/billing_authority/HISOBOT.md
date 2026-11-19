# AUTH-CODEX-004 — human money transaction authority

Implemented separately after initial moderation PR50 merged (a13caf4).

Old5856dc6 independent PostgreSQL/HTTP evidence:

- initial_junit.xml:3 failed,8.77s. Actual refund row-lock wait plus completed finance
  session revoke or trusted FINANCE-grant revoke; first still200/PENDING_SECOND_APPROVAL,
  second200/APPROVED with one REFUND_EXECUTE event. No real transfer was executed.
- checkout_initial_junit.xml:5 failed,12.06s. Actual organization lock plus completed
  own-session DELETE200, then legacy/canonical order201 adds order/invoice, payment
  intent200 adds pending attempt, legacy/canonical refund201 adds reservation.
- target_initial_junit.xml:3 failed,9.68s, repeated payment/refund subset using actual
  invoice/captured-attempt row locks. These overlaps are not distinct vulnerabilities.

Four services and six route callers now require actual ActorContext. Breaker/business
ordering, current user/MFA/role metadata held through commit, user-scoped idempotency,
captured funds limits, independent finance stages and audit/outbox atomicity remain.
Default prices, schema and trusted provider callback/worker policy are unchanged.
Direct-service test helpers now pass actual fixture sessions; no optional user-ID
runtime bypass was introduced to retain old signatures. Scope/expiry boundary is in
backend/BILLING_AUTHORITY.md; quota publish/transition remains separate.

Native75 passed,101.21s,0 failure/error/skip,1 framework warning. Actual lower-level
business waits, public session/MFA management, trusted account/auth_version/role/expiry
changes, opposite commit serialization, valid controls/receipts, rollback, service
session/cache boundaries, parallel reservation/approval and requester separation pass.
Signed capture still works after human logout. Native timings include Windows cleanup,
not API performance. Old7 affected modules137 passed,149.62s,0 failure/error/skip,
1 framework warning on the same d88ebaf source. Both full579 CI42563376429/42563380627
passed429.74s/381.18s. Pinned source review found no concrete implementation defect but
requested role revoke on matching order/payment replays.895fb8c adds those2 and a fresh
actual HTTP MFA login receipt control; native3 passed9.03s. No runtime source changed.

Follow-up test review requested explicit PostgreSQL wait proof beyond before-cursor/
unfinished-future observation.1368ee5 adds4 test lines: capture independent blocker PID
and wait for pg_blocking_pids to report a blocked backend BEFORE authority changes.
Both pre-authority wait paths (36 variants) and reverse-order tests now observe actual
wait graphs. Final native78 passed104.23s,0 failure/error/skip,1 framework warning.
These78 rerun earlier75+3; do not sum them as distinct coverage. Old137 belong to the
same unchanged runtime on d88. Final wait-graph review exit0 confirms the requested gap
closed. The helper observes any backend blocked by the unique holder, not an explicit
HTTP-request backend PID; the reviewer considers the isolated target/one pending request
a reasonable proof. Strict request-PID correlation is not claimed.

Final full582 CI42564327339/42564331479 passed437.43s/441.90s on1368ee5.
Evidence-only head checks/merge remain; no overall pilot acceptance is claimed.

Actual read-only Copilot planning review exit0 is saved (copilot_exit.txt): four-method/
six-caller scope, breaker/org/target-before-authority ordering, receipt/idempotency
identity and expiry boundary. It did not run tests or verify SHA; model identity was
not independently reported. HMAC capture and administrative grants are trusted synthetic
fixtures; no public role provisioning/live payment/browser/DR acceptance is claimed.
