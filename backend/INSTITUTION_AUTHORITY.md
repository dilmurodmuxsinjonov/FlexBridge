# Current institutional authority gate

Issue #53 covers the existing academic write paths. It does not implement the
institution intake, first-coordinator grant, appointment acceptance, academic
admission, official grading or export workflows. Canonical registration remains
an inventory rather than acceptance evidence; the project is not pilot-ready.

`institution_scope_query` supplies the same effective role predicate to session
role labels, `require_institution` and transaction-bound authority. A role needs an
active user, verified institution, accepted active membership, nonrevoked
INSTITUTION COORDINATOR/TEACHER grant, and the linked active, personally accepted
appointment for that exact user and institution. Acceptance cannot be in the
future. Appointment dates include both endpoints in Asia/Tashkent. Invalid legacy
links confer no rights and remain available as historical records. An imported
nullable verification-case link is not fabricated legal verification.

Academic create, revoke and diary review require the real ActorContext. The
service acquires institution and business-row locks before checking the current
active user/session, auth version and effective role under FOR SHARE locks.
Coordinators require MFA; an ordinary teacher PASSWORD session can review its
accepted assignment. Cached role labels and a caller user UUID alone grant no
write authority. Shared MFA behavior remains in force for finance and ownership.

Creation locks institution -> placement -> supervision -> enrollment/agreement,
then actor/session and coordinator authority. The supervision must belong to that
coordinator. An independently assigned target must currently hold TEACHER in the
same institution. Target authority locks use NOWAIT: contention returns
INSTITUTION_AUTHORITY_BUSY_RETRY (409) and rolls back the entire transaction,
allowing a clean retry without waiting on a foreign user's security mutation.

Review/revoke lock institution -> placement -> supervision -> assignment; review
then locks the log and enrollment/agreement before actor authority. Institution
locking serializes these existing academic mutations. Review checks the exact
placement/log/assignment, current verified candidate enrollment, active agreement
and enabled supervision purpose/legal basis, accepted nonrevoked supervision and
assignment, and a submitted revision. Only an active academic placement qualifies.
Self-assignment and self-review are forbidden. Diary review does not accept an
official grade; that requires its separate future workflow. Workplace reviews
retain their existing service path. Revocation can remove access after the target
teacher or parent agreement expires; it still requires current coordinator MFA.

Creation, first revocation and review append audit events in the same database
transaction. Repeated revocation retains the original timestamp and audit event.
An authority/security update completed before the guarded boundary denies the
write; one beginning after authority locks waits for commit/rollback. Clock dates
and expiry are evaluated at that boundary, not frozen until commit.

Tests use migrated disposable PostgreSQL databases and actual sessions. Imported
scope/document metadata and administrative role mutations are trusted fixture
setup, not proof of real document truth, identity, legal consent or provider
integration. Native lock tests observe pg_blocking_pids for the held backend and
isolated pending request; they do not claim a separately traced HTTP backend PID.
