# AUTH-CODEX-004 — refund approval transaction authority

Confirmed on5856dc6, three native PostgreSQL/HTTP regressions failed (8.77s):
first finance approval after actual own-session revoke completed200 still wrote
PENDING_SECOND_APPROVAL; second approval after session revoke or trusted administrative
FINANCE-grant revocation still200/APPROVED and enqueued one REFUND_EXECUTE event.
This proves unauthorized-after-revocation approval/queueing, not an executed transfer
or anonymous access. HMAC capture and administrative role setup are synthetic fixtures.

Prioritize this money-affecting confirmed residual after initial-moderation #48/PR50,
before EDU. Keep it a separate branch/PR and retain old failed evidence. Refund approval
currently accepts only actor_id, role preflight precedes its row lock, and no session
can be rechecked inside the service. Pass actual ActorContext from canonical API116,
take business locks then existing current-MFA FINANCE platform_authority, hold through
commit and preserve two independent finance approvers/requester separation, captured
payment/refund limits, audit/outbox atomicity and circuit-breaker ordering.

Planning/source review must check sibling order/payment/refund-request mutations that
also reconstruct ActorContext(user_id,'',()), without mixing unrelated publish/HR policy
or provider webhook semantics. State exact bounded scope; do not claim all billing or
every API hardened. Valid current-MFA controls, actual session/security/role changes
while waiting, reverse serialization, two-stage replay/concurrency and audit/outbox
rollback, old billing/IAM regressions/full CI/pinned review are required. No real payment
provider/merchant integration, live secret rotation or pilot acceptance is established.

Sibling repro on the same5856 source:5 further failures (12.06s) while actual organization
row lock is held and actual own-session DELETE completes200: legacy/canonical order
creation still201 with an extra order/invoice; payment intent200 with another pending
attempt; legacy/canonical refund request201 with an extra reservation. So bounded scope
is four human money service methods: create_order_and_invoice, process_payment_attempt,
request_refund and approve_refund; API callers in billing.py and canonical_routes.py.
All existing human roles here (OWNER/BILLING/FINANCE) already require MFA globally.
Require actual actor/session at service boundary with no optional user_id bypass.
Quota publish/transition and trusted HMAC callbacks remain separate, preserving their
existing assurance and provider policies. Existing direct service test helpers must
pass their real fixture ActorContext; do not weaken guards to retain old test signatures.
