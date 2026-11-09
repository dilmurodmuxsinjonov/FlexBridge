I’ll trace the requested service/API/DB/migration paths and tests, then follow the authority,
identity, and storage helpers they rely on. I’ll keep this read-only and distinguish verified code
paths from hypotheses.

Finding — P2: onboarding routes miss the private-response and body-size middleware. The new
endpoints are defined at api/v1/institution_onboarding.py:41–63, but core/iam_http.py:8–15 only
wraps listed prefixes; it includes organizations and the operator queue, not
/api/v1/institution-onboarding, /api/v1/institution-appointments, or
/api/v1/me/institution-appointments. As a result, these authenticated routes bypass that
middleware’s 128 KB request-body cap and no-store/no-cache/no-referrer response headers
(iam_http.py:45–50). In particular, status and inbox responses contain private appointment and
decision information (services/institution_onboarding.py:138–160, 376–383). Add the onboarding
prefixes to the middleware scope. This is not an authentication bypass: main.py:68–75 applies the
API authentication boundary, and the services perform their own authority checks.

DB-guard hardening gap, not a demonstrated public exploit: 0011_institution_onboarding.py:219
permits a PASSWORD session for any TEACHER consent, without checking whether that user also holds a
sensitive platform role. The HTTP service does check current sensitive roles at
services/institution_onboarding.py:58–60, so the inspected public consent path enforces MFA; a
trusted direct database insert could still record PASSWORD consent for a TEACHER who is also, for
example, a MODERATOR, and that proof could later be consumed during normal approval. If the trigger
is intended as an independent security invariant, align it with the service check; otherwise treat
DB writes as trusted and do not claim the trigger enforces this policy.

In the inspected public service paths, exact-revision consent, reviewer independence,
current-session/MFA checks, named-user/contact pinning, requester-grant revalidation, evidence
snapshots, and no-resurrection replay checks are present. The migration also preserves valid legacy
appointments without fabricated approval and closes structurally mismatched grants. This was a
read-only source review: I did not verify the commit SHA or run tests.

