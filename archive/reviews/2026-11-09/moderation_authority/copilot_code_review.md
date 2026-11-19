No concrete reachable bypass, introduced regression, or deadlock found in the initial moderation
path. The API’s platform-role preflight and global MFA middleware preserve existing policy; inside
the service, the opportunity is locked before current session/MFA and moderator authority are
checked, then revision, self-author, and state checks precede writes. The action, case, opportunity
update, and audit write share a transaction. Appeal provenance also appears consistent with the
immutable action history and linked case.

Non-blocking test gap: test_real_opportunity_lock_wait_rechecks_security covers session revocation
and MFA disablement during a real opportunity-lock wait, but not role revocation or expiry. Those
changes are covered by a test paused before the actual row-lock query, so the role recheck at the
real wait boundary is less directly exercised. Extending the real-lock test to include role and
role-expiry changes would close that gap.

The trusted SQL fixtures demonstrate database-state behavior; they do not establish public
role-provisioning flows. Expiry is evaluated at the post-lock authorization check, not guaranteed
through commit. I did not infer live, browser, provider, or disaster-recovery behavior from this
source review.

