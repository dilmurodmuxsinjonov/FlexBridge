The changes address both test-gap recommendations. In test_invitation_contact_order.py:21-23,53-55
and test_invitation_contact_races.py:31-34, the contention event is signaled in finally after the
original nonblocking contact-lock attempt; the binder proceeds only after that signal. The tests
assert the exact 409 INVITATION_BUSY_RETRY response and successful binding/registration, with no
partial invitation or membership grant.

The new existing-contact race in test_invitation_contact_races.py:91-118 pauses before
lock_target_user, completes an HTTP contact rebind, then checks the retry response, no stale
invitation, and that a fresh invitation targets and admits the new holder. The separate
absent-to-present case remains at lines 67-88. I found no concrete remaining test or production
issue in the requested scope. I did not run tests or independently verify the pinned SHA.

