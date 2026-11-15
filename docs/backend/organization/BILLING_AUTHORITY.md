# Human money authority

The human order, payment-intent, refund-request and refund-approval services require
the authenticated ActorContext, including its actual session. They do not accept an
optional sessionless user-ID compatibility path. The three legacy billing routes and
canonical094/095/116 pass that context; persisted purchaser/requester/approver and
idempotency identities still use actor.user_id.

Authority is checked after the blocking business rows and held through the UOW:

| Operation | Lock/check order |
| --- | --- |
| Create order/invoice | Breaker SHARE, organization, current user/MFA/OWNER-or-BILLING scope, catalog/idempotency/write |
| Payment intent | Breaker SHARE, organization, invoice, current user/MFA/OWNER-or-BILLING scope, idempotency/attempt |
| Refund request | Breaker SHARE, organization, captured payment attempt, current user/MFA/OWNER-or-BILLING scope, reservation limit/write |
| Finance approval | Breaker SHARE, refund, current user/MFA/FINANCE platform scope, independent-stage checks/status/outbox/audit |

Those human roles already require MFA in global policy. A completed logout, security
rotation or account/grant change before the authority boundary denies the request,
including matching idempotent receipts. If authority is held first, competing database
revocation waits until commit/rollback. Expiry is evaluated at authorization; locks do
not freeze time through the rest of the transaction.

Existing user-scoped idempotency keys/digests, immutable price snapshots, captured-only
refund limits and three distinct requester/approver IDs are preserved. Two valid finance
approvals produce one execution event. A write/audit failure rolls back the associated
billing/idempotency/outbox effects. A queued REFUND_EXECUTE is not a real transfer.

Signed provider callbacks retain their system authentication and remain valid after
the original payer logs out. No provider/price/schema/worker policy is changed. Quota
publish/transition has a different HR/HOST_COORDINATOR assurance policy and is outside
this bounded fix; this is not a claim that every billing or application API is hardened.

Tests use disposable PostgreSQL, actual HTTP logout/MFA-disable, independent blocking
connections and explicit administrative SQL state changes. Direct service fixtures pass
their real MFA session contexts. HMAC captures and administrative grants are synthetic;
no live merchant/provider, secret rotation, browser/hardware/DR or pilot acceptance is
established. Direct database writers remain trusted.
