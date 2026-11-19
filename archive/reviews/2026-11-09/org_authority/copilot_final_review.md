Source review found no concrete production defect in the changed lock path: contact locking uses the
identity service’s key, only lock contention maps to INVITATION_BUSY_RETRY, and the exception
propagates through the transaction context for rollback. org_authority’s default behavior and the
invitation MFA/role checks remain unchanged.

There is an important race-test gap: in test_invitation_contact_order.py:22,53 and
test_invitation_contact_races.py:31–32, the event is signaled before original_invite attempts the
advisory lock. The coordinator can release the contact holder first, so those tests do not
deterministically establish contention. Signal after the database try-lock attempt completes. Also,
the changed-identity test covers an initially absent contact becoming present, but not an existing
target changing between the initial read and target pin; invitations.py:81 rechecks that identity,
but that branch lacks a corresponding changed-input test.

This is a source-only review; it does not certify the pilot or claim test or SHA verification.

