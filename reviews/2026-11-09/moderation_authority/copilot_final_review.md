I’ll inspect the committed diff’s relevant test and moderation code using read-only file search,
then assess whether the actual row-lock test covers the stated gap.

The role-expiry gap is closed: the real opportunity-row-lock test now exercises both grant
revocation and expiry, commits the authority change while the independent blocker still holds the
opportunity lock, and checks for a denied response with no moderation-state or audit changes.

I found no concrete remaining defect or necessary test gap in the initial-moderation scope. The
separately reported refund-approval race is outside this change and remains unaddressed here. This
was a source review only; I did not verify the pinned SHA or run tests.

