Finding — stale revision replay can falsely acknowledge changed evidence (P2). In
backend/app/services/enrollments.py:195–200, a retry with expected_revision one behind returns
success when the proposal fields match, but it does not compare the submitted revision’s pinned
file_snapshots with the file’s current snapshot. Reproduce by submitting a file, changing its stored
version/hash, then retrying the same revision request: the API returns the existing revision as
successful without accepting the changed material. The approval path later rejects stale evidence,
so this is not an approval bypass, but the replay response is misleading and breaks the documented
identical-material guarantee.

Coverage gap — enrollment self-review is not exercised. The service rejects a requester claiming
their own case, and the SQL event guard also enforces independence, but the enrollment lifecycle
tests use separate requester and moderator identities
(backend/tests/security/test_enrollments.py:26–31, 53–57). There is no enrollment-specific
acceptance test proving a requester who also has moderator authority cannot claim or decide their
own case without writing an event or audit.

I found no direct-VERIFIED or legacy-resurrection bypass in the reviewed public paths; direct
database administration remains a trusted boundary. This was a read-only source review: I did not
run tests, and full current CI and broader final acceptance remain unverified.
