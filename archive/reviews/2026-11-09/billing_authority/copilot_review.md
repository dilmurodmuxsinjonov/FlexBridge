The four-method scope and six route callers look sufficient; I see no source dependency requiring a
migration, provider change, or change to callback/worker semantics. One lock-placement detail should
be explicit: preserve breaker SHARE → organization lock, then acquire each relevant target lock
before checking authority. That means invoice row before org_authority in process_payment_attempt,
captured payment-attempt row before it in request_refund, and refund row before
platform_authority(..., 'FINANCE') in approve_refund. For order creation, the organization lock is
the relevant business lock, so check authority after it. Keep the existing org-first order: the
webhook and refund worker also acquire organization locks before their billing rows, so reversing
that order risks a lock cycle.

The source shows the underlying gaps: these service methods synthesize ActorContext with an empty
session ID and rely on non-locking require_org/require_platform checks; approval checks finance
authority before waiting on the refund row. The proposed real-context, transaction-bound authority
checks address those gaps. Keep the service checks authoritative rather than relying on the
canonical refund route’s existing require_org precheck. Preserve idempotency identity and digests;
same-target requests serialize on the organization lock, while conflicting cross-organization key
reuse must continue to fail rather than mutate.

Use real MFA fixture contexts in the direct service tests. Focused coverage should include revoked
session and revoked role after a blocked target lock, expiry while waiting, replay and
payload-conflict behavior, concurrent refund reservation limits, and two distinct finance approvers
with exactly one execution event. Expiry boundary: session and grant expiry are checked when the
authority query runs after the blocking locks; a transaction authorized before expiry can still
finish if expiry occurs before commit. No new deadlock is apparent with the lock ordering above. The
reported HTTP failures and SHA are not independently verified in this source-only review.

