Review: The plan is appropriately bounded to the seven candidate self-service paths. In the reviewed
code, the routes receive ActorContext but pass only user_id to the profile, skills, CV, and
availability-write services. Those services lock business rows but do not perform transaction-bound
authority checks. Profile GET reads without a lock or final check; private schedule GET resolves the
candidate ID separately, then reads in REPEATABLE READ. These paths therefore do not close the
reported in-flight revocation gap. The supplied HTTP-wait observations are consistent with that
concern, but I have not independently certified the pinned SHA or those observations.

Recommendations: Pass the real ActorContext through each in-scope service method; do not retain a
user-ID-only fallback for human calls. In each same transaction, acquire business locks first, then
call account_authority and hold it through the read or through business and audit writes to commit.
For CV operations, preserve the order profile → file → user → session; other self-service writes use
profile → user → session. Logout and security rotation already take user before session, so avoid
adding any path that takes user/session before profile/file. account_authority applies current
database roles and the existing sensitive-role MFA rule; do not rely on cached ActorContext.roles.

For profile GET and /me/availability schedule GET, use an explicit human-read wrapper: in a normal
READ COMMITTED transaction, lock the owner’s profile row for share, check authority, then read the
result. The profile lock serializes against the replacement writers’ profile-row locks, keeping the
schedule rows consistent without checking authority against an old repeatable-read snapshot. Keep
load_snapshot and read_snapshot unchanged for matching/internal consumers. Also keep internal
schedule rendering distinct from this human wrapper: get_profile is nested inside profile/skills
writes via the shared transaction, while availability replacement currently calls get_schedule after
its write transaction commits.

Update direct-service test setup to supply an actor: the current direct replace_rules call in
tests/security/test_candidate.py (the concurrent snapshot test) is the identified fixture update.
Preserve active-skill verification invalidation, CV ownership and pinned storage provenance,
availability interval/exclusion behavior, and matching’s consistent snapshot and query-count
controls.

Risks and coverage: Add real PostgreSQL wait tests in both serialization directions for the writes
and private reads, including completed logout, expiry/auth-version change, and
current-role/sensitive-MFA cases. Assert rejected requests leave business and audit state unchanged;
retain audit rollback, availability/matching snapshot, and no-N+1 regressions. The existing green
candidate/storage tests and the CV-metadata probe do not establish this authority fix. Keep catalog,
applications, and other domains out of scope; they need separate reviews.
