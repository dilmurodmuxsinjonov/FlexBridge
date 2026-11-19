I’ll trace the scoped transaction paths and their authority/lock helpers, then compare the review
notes and focused tests for concrete reachable gaps.

The main stale-authority paths appear transaction-bound. I found a separate lock-order cycle around
invitation contact validation and account contact rebinding; I’m pinning down its exact methods and
whether it is reachable through public flows.

Finding — reachable PostgreSQL deadlock in invitation acceptance. InvitationService.accept locks the
recipient’s active user row through mfa_authority before calling _contact, which then waits for the
contact advisory lock (invitations.py:116–137, authority.py:7–15, invitations.py:103–114).
Meanwhile, public account registration can hold that same contact lock and then request the old
contact owner’s user row FOR UPDATE through identity_service.register → _bind_contact →
rotate_security (identity.py:94–103, 110–120; auth.py:145–149). When the old owner is the invitation
recipient, those waits form a cycle; PostgreSQL will abort one transaction. This is a
code-established race, not a reproduced deadlock; expected impact is a failed/retryable request, not
an authority bypass or partial commit. The sequential contact-recycling test does not cover this
interleaving. A concurrent acceptance/contact-rebind regression test is warranted.

I found no other concrete bypass or atomicity failure in the scoped paths reviewed: organization
mutations and governance member create/approve perform transaction-bound MFA checks, and acceptance
checks the recipient’s contact plus the inviter’s current organization authority. Initial
opportunity moderation remains out of scope as requested. This was read-only view/glob/rg review: I
did not run tests, reproduce the race, or independently verify the pinned SHA; the recorded 69-test
result is not pilot acceptance.

