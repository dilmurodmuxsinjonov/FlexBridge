No concrete implementation defect found in the four human money methods. The source preserves
breaker → organization/target-lock → current-authority ordering, with authority checks before replay
claims and state-dependent errors. All six route callers pass ActorContext; refund approval keeps
the refund lock before FINANCE authority and commits its audit/outbox effects in the same
transaction. The canonical refund route has an earlier non-locking scope precheck, but the service
still performs the authoritative check after its business locks.

Test-coverage gap: role invalidation while waiting is tested for new order/payment requests, but not
for matching idempotent replays. test_admin_state_changes_are_rechecked_after_target_wait covers
only order, payment, refund, and approve_second
(backend/tests/security/test_billing_authority.py:115); replay cases are covered in the
logout/MFA-disable test instead (:94). Add order_replay and payment_replay with a completed grant
revocation while blocked, asserting denial and no effects. The implementation appears to enforce
this already—the checks precede _claim in backend/app/services/billing.py:69-74, 133-136—so this is
a regression-coverage gap, not a demonstrated bypass.

This was a source-only review; I did not run tests or independently verify the SHA.

