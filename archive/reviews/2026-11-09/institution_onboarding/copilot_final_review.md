Findings

 1. Low — repeated reviewer claims create duplicate audit events. In
backend/app/services/institution_onboarding.py:533-542, a case already assigned to the same reviewer
is accepted, then updated_at is rewritten and INSTITUTION_REVIEW_CLAIMED is appended again. This
conflicts with backend/INSTITUTION_ONBOARDING.md:58-59’s retry guarantee. Return the existing claim
receipt without writing or auditing when the same reviewer retries.
 2. Clarify revision expiry semantics. RevisionInput makes agreement_valid_to optional
(backend/app/api/v1/institution_onboarding.py:28,41-42); resubmission treats a missing value as None
and creates a new agreement version with no end date
(backend/app/services/institution_onboarding.py:478-480), potentially reusing the prior signed file.
If omission is meant to preserve the existing term, distinguish omitted from explicitly unbounded
and retain the prior value. The documentation does not establish which meaning is intended.
 3. Conditional storage-integrity gap, not a demonstrated public exploit. Downloads compare the
database snapshot’s hash/version fields, then presign a GET by storage key alone
(backend/app/services/institution_onboarding.py:415-418,580-583;
backend/app/adapters/storage.py:34-35). The normal pipeline uses content-addressed private keys,
which mitigates ordinary overwrites, but the presigned response itself is not bound to the recorded
object version. Confirm that storage enforces immutable keys, or bind retrieval to a supported
version identifier; the source does not establish the live provider’s overwrite guarantees.

Prior findings: Both are closed in the current source. IAMHTTPMiddleware now covers the institution
route families, and migration 0011’s consent guard requires MFA for sensitive platform,
organization, and current institution-coordinator accounts while preserving ordinary teacher-only
PASSWORD consent. The dispatcher routes institution cases through the institution-specific service.
I found no additional concrete identity-retargeting, bootstrap-reopening, stale-consent activation,
or grant-resurrection defect, and no new deadlock defect in the reviewed lock paths.

This was source analysis only: I did not run tests or verify the Git SHA/model, and this review does
not certify legal identity or pilot readiness.

