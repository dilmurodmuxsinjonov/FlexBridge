# Own education history and enrollment verification

Issue63 is being implemented and validated. This guide describes the prototype,
not accepted pilot, live identity verification or production deployment. Runtime
0013 has been loaded on disposable PostgreSQL:114 tables; canonical v1.4 remains94.

Canonical API027 POST and API034 GET `/api/v1/me/enrollments` replace their
placeholders. Authenticated own detail, `/{id}/verification` and `/{id}/end`
helpers complete the lifecycle. Strict DTOs reject caller-controlled candidate,
status, reviewer or verified fields. The optional student reference is HMAC-bound
to purpose/user/institution; raw reference and digest are not returned in views.
No PINFL, diploma or education entry is required for ordinary candidate access.

A record without evidence is DECLARED, with a DRAFT case outside moderator queues.
Submitting current owned CLEAN PDF evidence creates a PENDING revision. Every
public case has only enrollment_id as its subject; candidate/institution are
derived from that enrollment. Revisions pin the complete explicit storage
bucket/VersionId/ETag and content metadata. File URLs and storage locators are not
exposed through own education history. The ordinary owner download boundary remains.

Existing operator API109/110 and claim/detail/file helpers explicitly dispatch
ENROLLMENT to this service. Current MFA/MODERATOR authority and an independent
assigned reviewer are mandatory. Exact revision, reason, current institution,
active requester and matching owned CLEAN file material are rechecked before a
new approval. NEEDS_INFO or rejection can add a new revision to the same case;
previous decisions remain immutable. A claim retry does not append a second audit.
The first-response target is one weekday (source1.3:69), with no holiday calendar
or live escalation acceptance. Due time never approves a request.

Own submit intent persists after later logout; review is asynchronous and uses
the current reviewer's session. A fresh approval requires an active requester,
not the original intake session still being logged in. A recorded accepted
decision is historical proof: later evidence unavailability does not erase it.
New approval and current file delivery still recheck material. Replayed decisions
return the immutable decision receipt rather than creating a fresh approval.

Own views derive `current_student` from effective status, local dates, current
VERIFIED institution and exact approved public proof or the captured import set.
The role label function roles_for is unchanged. Current-student display is not
independent authority for matching, applications, exports or academic review.
Academic binding checks the same database enrollment predicate under its existing
business locks; other parent/agreement/purpose/teacher checks remain mandatory.

Forward0013 captures exact existing rows as LEGACY_IMPORT without inventing a
reviewer or evidence. Only rows already VERIFIED at upgrade retain their prior
current eligibility. The marker set is closed after capture. New legacy markers,
unproved new VERIFIED inserts/promotions, and legacy resurrection are rejected.
Immutable origin/revision/event records and exact new case decisions protect
public transitions. Direct database administration is trusted; session metadata
in SQL proof is not independently authenticated bearer evidence or legal truth.

Program/institution/start or approved end-date extensions require a fresh entry.
End/withdraw is a terminal reduction, with persisted idempotency fingerprint and
receipt. It preserves prior approval/proposal, profile, applications and old
academic relationships. A future-start cancellation preserves valid original
dates and reduces effective status; it never writes end_date before start_date.
Own create/end replay keys do not create extra writes/audits; conflicting bodies
return409. Revision replay is bound to expected revision and identical material.
The replay path locks and compares current file snapshots before current account
authority, so an old request cannot acknowledge a changed file version as accepted.

All human service methods receive actual ActorContext, reject frozen outer
REPEATABLE READ contexts and apply current account/assurance. Mutation/review/end
order is institution -> candidate profile -> enrollment -> case -> material files
-> current user/session/platform authority, held through commit. New paths do not
take academic locks after enrollment. Own informational reads hold profile SHARE,
current account/session and one joined result projection. Approval takes a
nonblocking shared requester-account pin after reviewer authority. Errors roll
back business/proof/audit together. Own responses have no-store/no-cache/
no-referrer and the existing body bound. Ordinary PASSWORD/teacher policy remains.

Initial schema and HTTP lifecycle results are in
reviews/2026-11-10/enrollment_verification. Actual CLEAN metadata in those tests
is a trusted fixture; one presigner is explicitly doubled. These tests do not
claim real storage, scanning, document truth, full academic admission or all R1 AC.
Full security/concurrency/affected suites, current complete CI, pinned source review
and final evidence are still required. Broader student/job eligibility, supervision/
accepted teacher assignment/export/signatures, frontend/live identity/providers/DR
and overall pilot acceptance remain open. pg_live has not been started or migrated.
