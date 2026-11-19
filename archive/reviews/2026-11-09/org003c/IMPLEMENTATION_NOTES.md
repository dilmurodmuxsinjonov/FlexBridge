# Implementation boundary and pending work

Source base e2dd6a16d2cad41642be8ce1a311167515646ecf (PR44 merged). Branch45,
Issue45. These notes began before implementation; runtime, SQL and56 new tests now
exist, with final old-module regression/CI/pinned code review still pending. Both actual Copilot plan
reviews completed exit0, no independently reported model. Apply REJA.md plus addendum.

Proposed0010_owner_continuity: two helper tables, runtime107/canonical94. Requests
immutable: case PK, unique canonical recovery ID, org/applicant/member/staff grant,
original auth_version/MFA session, own contact/HMAC/verified timestamp, created/24h
expiry, exact sorted active OWNER roster JSONB, original file IDs/note, actor/key and
payload fingerprint. Consent is the current-MFA self-request, fixed revision1.

Events immutable: id, case, stage MODERATOR/COMPLIANCE, action CLAIM/RECOMMEND/APPROVE/
REJECT/NEEDS_INFO, actor, authority_grant_id, auth_version, current session_id, created,
claim_id for decisions, reason. Partial unique(case,stage) separately for CLAIM and
non-CLAIM. Decision references its own stage claim; exact role grant and security
version cannot revive after replacement. Only COMPLIANCE APPROVE has result_owner_grant_id
and ownership_event_id; the event FK is deferred. Session authority is checked when
each event is written; historical recommendation does not require staying logged in,
but its exact role grant, user status/security version and expiry must remain current.

Use a SQL roster function returning JSONB ordered by grant ID with exact user/member/
grant/auth_version tuples, active users/members/OWNER grants. Optional excluded member
supports final proof after inserting the applicant's grant. Service first compares full
roster before insertion, then SQL proof compares original roster excluding applicant.
Hold all original user/member/grant rows FOR SHARE through commit. No old role removal.

Unique partial index on verification_cases(organization_id) for this kind and two open
states enforces one pending case. A before-update guard fixes kind/org/requester and
revision1 and allowed transitions. A deferred case/tracking proof validates helper
linkage/status mapping, MOD recommendation for WAITING_COMPLIANCE and full final proof
for APPROVED. Account tracking maps APPROVED->COMPLETED, every other state unchanged;
kind ORG_OWNER_CONTINUITY, reviewer_id stays NULL. No account continuations for it.
identity.py status/complete must check ACCOUNT_ACCESS explicitly.

Null-previous owner event guard must gain explicit case-kind dispatch to a dedicated
continuity proof, preserving the existing initial/addition predicates unchanged and
unknown kinds fail-closed. Copy the original concrete function body into0010 with a
narrow continuity branch; do not patch arbitrary installed SQL with string replace.
Departure guard/trigger remains unchanged. Final grant and event are attributed to
COMPLIANCE; canonical assigned_reviewer_id may hold the MODERATOR but is insufficient
as final proof. Two actual claim/decision records establish quorum.

Service liveness: under org->case locks, an authorized applicant/current OWNER/current
stage operator can expire consent, changed applicant/roster, or invalid stage claims.
Update case/tracking/audit atomically and return a minimal closed receipt after commit;
raising inside the UOW would roll closure back. A valid staff intake may close a truly
expired/stale pending org case before creating a replacement. Private stage detail/files
still needs its own exact claimed current role grant and current MFA. No reassignment.

Positive moderator recommendation and finalization revalidate the original live intent.
Finalization also rechecks the original moderator's live exact role/security version,
distinct compliance claim and current MFA. One UOW: insert new OWNER grant, final event
record carrying exact grant/event IDs, canonical ownership event previous=NULL, case
APPROVED, tracking COMPLETED, audit. Event effective_at can use new grant.created_at.
No grant before both independent decisions. Matching final replay is a receipt, with
current authorization, not re-executing live pending conditions after already committed.

Withdraw/OWNER objection need current MFA and correct participant/OWNER; same business
locks, one terminal tracking/case/audit transaction. OWNER inspection is minimal pending
metadata, no applicant evidence. Applicant own history remains readable with current
MFA even if staff grant later revoked, without organization authority. Queue filters
reviewer org membership history/applicant/other reviewer; detail/evidence needs own claim.

Generic organizations.submit rejects continuity kind AND case_id targeting it, including
NEEDS_INFO; kind excluded from generic review queue/claim/decide. Dedicated APIs and
private middleware only. Explicit typed storage maps helpers. Tests must cover old
IAM/addition/departure/appeal proofs along with new quorum/race/revocation/rollback/
immutability/persistence/populated upgrade; no fake identity/provider/browser claims.
