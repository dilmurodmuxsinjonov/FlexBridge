Candidate profile/skills/CV and availability writes pass only a user ID to the
service, and private profile/schedule reads lack a transaction-bound current-session
check. On isolated pinned370d9c32229f023537ff1cdacc77bc53f8bb3c30 (PR60 source),
actual HTTP requests were observed waiting on PostgreSQL, actual DELETE session200
completed, then all5 writes still returned200 and changed candidate business/audit
rows. Profile/skills/CV/rules/exceptions post-state observation failed5 tests9.35s;
the prior response-only5 failed10.01s overlaps and is not additional unique coverage.

Private profile and schedule GET probes also returned200 with the owner's candidate
ID after completed logout (2 failed7.45s,5 write cases deselected). Writes waited on
the actual candidate-profile row; the old plain SELECT reads used an actual table
lock. Holder PID pg_blocking_pids is observed; no separately traced HTTP backendPID
is claimed. CV metadata is a trusted fixture, not actual document scanning or public
metadata mutation. This is an authenticated in-flight revocation issue, not anonymous
or cross-user disclosure, and does not imply every other endpoint is affected.

After PR60, implement a bounded9-path candidate self-service authority package:
profile GET/PATCH, skills PATCH, CV link/unlink, availability rule replacement,
exception replacement and private schedule GET, plus both legacy candidate-ID
availability-add POST routes. Pass real ActorContext and reuse
account_authority after business/material locks, held through reads/writes/audit.
Preserve current PASSWORD/teacher-only and global sensitive MFA behavior, own-only
scope, active catalog and skill-verification rules, CV exact storage provenance,
range/EXCLUDE semantics, snapshot consistency and efficient matching.

Keep internal schedule/matching reads explicitly distinct from human session APIs;
no user-ID-only compatibility fallback for human writes. Do not hold a frozen
REPEATABLE READ snapshot over final authority if it could see a pre-revoke state.
Plan lock ordering for profile/file->user/session and guarded read/snapshot behavior.
Add actual logout/security/expiry/current-role wait and reverse serialization,
no-write/audit rollback, wrong-session/current PASSWORD/MFA controls and existing
matching/availability regressions. Publish source/CI evidence and update handoff.
Generic skills catalog, job applications and other domains need explicit separate
audit scopes rather than claiming this9-path package closes all authority gaps.
No migration/canonical handler or pilot/live-provider/identity certification claim.

Additional same-feature caller audit: the two legacy POST availability-add routes
also discard ActorContext before calling add_availability_rule/exception. Actual
profile-row wait plus completed logout yielded201 and new availability rows in
both cases (2 failed7.35s,7 other cases deselected). Their existing owner-ID routing
check does not recheck current session after the wait. These two callers are now
explicitly included so the new canonical guards cannot be bypassed via sibling
paths. Preserve their current interval/date/AVAILABLE_EXTRA alias contract, exact
own-candidate binding and profile serialization; no actorless human compatibility.
