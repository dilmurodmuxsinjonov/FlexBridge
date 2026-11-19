I’ll independently trace the named specifications and the placement, mentor, authority, enrollment,
and academic service/API paths, then compare the evidence to the proposed sequencing.

Decision: accept the direction, but make the first package a reachable host internship lifecycle—not
a generic placement patch. The source supports separating job engagements from internships and
requiring personal, current-scope acceptance. The proposed sequence needs one important correction:
an academic internship must not become ACTIVE before teacher acceptance, even though a general
internship can activate without academic supervision.

Ordered packages

 1. Separate ordinary jobs from placements and diaries. DB-049 says placements are for INTERNSHIP;
AC-016 says a PART_TIME job has no diary. The actual create_placement accepts any accepted offer,
while diary ownership checks ACTIVE but not opportunity kind. Reject new ordinary-job placements and
block job diaries; keep ordinary work in job_engagements and its API-046 confirmation flow. Don’t
imply that this also completes application, offer-capacity, or cooldown behavior.
 2. Deliver the reachable host internship lifecycle under CAP-017 / CAP-018. Wire the actual
placement-creation route to an accepted internship offer, then provide the host and mentor surfaces
needed to use it: API-069 placement list, API-087 mentor nomination, API-089 mentor’s own
assignments, API-050 current plan/terms view, API-048 candidate’s own terms acceptance, API-051
acceptance by the personally assigned mentor, and API-088 host activation. The ACTIVE gate for a
general internship should require candidate and host acceptance of the current terms plus an
accepted, current mentor assignment. Nomination must require an active MENTOR grant in that same
host—not merely active organization membership. Keep host authority to the specified OWNER /
HOST_COORDINATOR scope.
 Keep the terms snapshot/version immutable; bind each acceptance to its exact current terms version
and actor. The model also has acceptance timestamps on DB-050, so treat those, if retained, as
one-way projections—not as mutable terms content. A revised terms version requires fresh
acceptances; revoked assignments stay historical, and a regrant creates a new assignment with no
inherited acceptance. The current /confirm-start path is not a substitute for the canonical
candidate, mentor, and host actions.
 3. Then add academic admission without the ACTIVE circularity. Implement API-098, API-099, and
API-101 for own-institution supervision, and API-104, API-102, API-051, and API-103 for the
teacher’s assignment, personal acceptance, and revocation. Keep enrollment currentness, institution,
agreement, purpose, and legal-basis checks exact. A bounded implementation choice is for API-102 to
bind a still-pending placement to the enrollment in the selected supervision and create the teacher
assignment atomically; derive academic status server-side, never from a client flag. Permit
assignment and acceptance before activation, then let API-088 activate an academic placement only
when the current terms, mentor, supervision, enrollment, agreement, and personally accepted teacher
assignment all pass. Preserve the existing prohibition on coordinator self-assignment and teacher
self-review. The current assignment helper requires an already ACTIVE, academic-track placement, so
simply wiring API-102 to it cannot create this path.
 4. Preserve provenance and revoke semantics across upgrades. Keep legacy rows and enrollment
history, but don’t treat a legacy placement’s status alone as proof of a new verified start.
Enrollment currentness is more specific: migration 0013 accepts a temporally current verified
enrollment only when its origin is a currently approved public review or a verified legacy-import
snapshot. Reuse that predicate; don’t replace it with a bare VERIFIED check or invalidate legitimate
legacy enrollment history. For assignment access, retain the original scoped grant identity (or
equivalent immutable authority evidence): the current mentor assignment stores a membership ID,
which alone cannot distinguish a revoked role grant from a later regrant on that membership.

Material contradictions in the proposal/source: API-048, API-050, API-051, API-087, API-088, and the
academic APIs currently fall through to generated 501 handlers; the working mentor-creation route
checks membership but not MENTOR, and there is no personal mentor acceptance route. Actual placement
creation sets academic_track=False, and its final service boundary receives only a user ID, not the
current ActorContext; a synthetic actor is then used for host authorization. Academic assignment
creation/review exists only on the internship-log service path, with no public supervision/binding
route. The institution agreement path currently supports ACADEMIC_VIEW; keep that agreement purpose,
exact enrollment-scoped supervision purpose, current agreement/version, and nonblank legal basis
aligned—don’t invent broader or institution-wide access.

Treat the lock sequence as an implementation choice that must be reconciled before coding: the
enrollment service locks institution → candidate profile → enrollment → verification case; academic
assignment/review and institution onboarding acquire overlapping business rows in different orders.
Standardize business/material locks first—including sorted file locks—then current account/session,
then the current scoped membership/grant; refactor existing callers that conflict rather than
relying on require_org’s separate transaction as in-transaction authority.

Replace fixtures that create ordinary-job placements or mutate academic/accepted fields directly
with real job-engagement or session-bound internship/academic flows. Keep exports, diary/review
completion, capacity/cooldown, and full R1/pilot claims outside these packages. This review is
source-only: I did not independently verify the supplied probe observations, and PR64’s final CI
remains pending.
