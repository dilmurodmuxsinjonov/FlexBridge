Concrete defect — coordinator MFA can be bypassed through the teacher role. review_academic requests
TEACHER authority (backend/app/services/internship_logs.py:100), while institution_authority
requires MFA only if the selected grant is COORDINATOR (backend/app/services/authority.py:62-65). A
user with both effective roles and no enrolled factor can receive a PASSWORD session; login marks
sensitive roles as needing MFA enrollment but still issues that session
(backend/app/services/identity.py:147-159). That session can review logs via the teacher grant,
contrary to the stated coordinator MFA policy (backend/IAM.md:90). Require MFA when the actor also
holds effective coordinator authority, while retaining password-only review for teacher-only users;
add a dual-role regression test. The existing password-teacher test (test_academic_authority.py:113)
does not cover this case.

Residual evidence gaps, not confirmed defects: The source shows business-row locks before authority
checks, reverse serialization tests, and a NOWAIT rollback test; I found no definite deadlock in the
reviewed paths. Those tests are running, so I cannot report outcomes. Review also relies on draft
creation having enforced candidate ownership: it checks the log’s placement and rejects teacher
self-review, but does not independently verify that the revision author belongs to that placement’s
candidate (internship_logs.py:92-105; _owned checks ownership at :129-134). No mismatch test is
present; if imported or legacy revisions are in scope, validate that author-to-candidate binding at
review. The documented gate uses trusted imported fixtures and explicitly leaves institution intake,
appointment acceptance, academic admission, official grading, and export workflows outside scope;
it is not pilot-readiness evidence.

