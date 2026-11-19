# ORG-CODEX-003C1 — fixed-revision staff OWNER continuity

Plan only, after003B acceptance. Human reviewers assess authority evidence; software
does not prove identity, legal authority or actual owner inaccessibility. Existing
IAM same-account recovery stays separate. Preserve all existing OWNER/member grants.

Current-MFA applicant is the target themselves, already active HR/HOST_COORDINATOR/
MENTOR/BILLING in a VERIFIED org, not OWNER. Own current verified contact, clean owned
PDFs and reason required. Immutable proposal pins applicant/member/exact staff grant,
auth_version, contact/HMAC/verified timestamp, consent24h, evidence IDs/note and revision1.
Snapshot a nonempty active OWNER roster: active users, active nonrevoked memberships,
active OWNER grants; sorted exact grant/member/user IDs and user auth_version. Current
roster must remain identical until approval. Organization lock before case or snapshot.
One open request per org; rate limits; close expired case atomically before replacement.

Canonical recovery_requests is only tracking: kind ORG_OWNER_CONTINUITY, user=applicant,
reviewer_id=NULL, first evidence ID, uniquely helper-linked to verification case/org.
No account RECOVERY_STATUS/RESET continuation issued for this kind. Account recovery
status and completion explicitly filter ACCOUNT_ACCESS. Actual two-review authority
is in dedicated append-only proof rows, never inferred from the canonical tracking row.

States WAITING_MODERATOR -> WAITING_COMPLIANCE -> APPROVED. REJECTED, NEEDS_INFO,
CANCELLED, EXPIRED terminal. Fixed revision1, no resubmission or consent renewal. New
evidence or stale consent/grant/contact/roster/security requires closure/new proposal,
starting both reviews again. Case/recovery tracking statuses share the same UOW.

Continuity-specific stage queues/claim/detail/evidence/decision endpoints. Exclude kind
from generic REVIEW_KINDS so generic claim/APPROVE cannot grant. One immutable claim
per stage with actor/exact role grant/auth_version/MFA session; one immutable decision
per stage; organization -> case locks. Current stage role and MFA, no org membership
history, different applicant/other reviewer, including if same account holds both roles.
No reassignment; revoked/replaced claim grant cannot revive. MODERATOR RECOMMEND moves
only to WAITING_COMPLIANCE, or REJECT/NEEDS_INFO closes. Claimed distinct COMPLIANCE
APPROVE alone finalizes; REJECT/NEEDS_INFO closes. No grant on claim/recommendation.
Role grant expiry uses current time, not recorded claim time.

Queue minimal; private detail/files require own stage claim and current role/MFA.
Matching finalized decision retry returns same receipt after current authorization,
without repeat effects. Applicant may read own history with current MFA and withdraw
pending intent. Current-MFA OWNER can inspect and OBJECT to pending continuity, closing
without a grant. Other org access retains existing role checks. No raw contacts or
HMAC/session/grant proof identifiers in reports.

Final COMPLIANCE UOW locks org -> case, then rechecks and holds all current authority
rows: applicant original staff grant/account/security, unchanged active roster,
fresh original consent/contact/HMAC and owned CLEAN original evidence; exact assigned
MODERATOR recommendation for revision1 with still-current original platform grant and
user security version; distinct assigned COMPLIANCE current claim/MFA/role/independence.
Insert one OWNER grant attributed to COMPLIANCE, canonical event previous=NULL with
approved_by=COMPLIANCE, case APPROVED, recovery tracking COMPLETED, final immutable
decision and audit atomically. Final active roster equals snapshot plus applicant.
No old OWNER/member/staff revocation or account/contact merge.

Explicitly dispatch ORG_OWNER_CONTINUITY in the null-previous event guard to a dedicated
SQL recovery proof before the unchanged-in-meaning initial/addition branch; departure
guard remains. New SQL proof validates both exact independent claims/decisions and
current roles/security, original roster excluding newly granted applicant, consent/
revision/applicant/contact, canonical recovery linkage/status and final grant/event
attribution. API verifies actual bearer MFA and contact HMAC; direct DB writers trusted.
Rerun old proof regressions and populated upgrade preservation, not just new tests.

Acceptance: no grant before both reviewers; wrong actor/org/role/MFA/same reviewer with
both roles; generic bypass; unassigned privacy; stale exact authority/security/contact/
consent/roster; actual revoke-reinvite-reviewed-regrant; concurrent retries/conflicts,
withdraw/owner objection versus finalization; fault/deferred-proof rollback; immutable
history; second-process persistence; populated upgrade; affected old IAM/addition/
departure/appeal suites, full PostgreSQL CI, pinned read-only review. Report actual
synthetic/TestClient boundaries. No live identity/registry/notifications/browser/DR.

Zero-active-OWNER/no-staff cases and manual same-account identity recovery remain
separate. No legal policy certification or pilot acceptance; pilot_ready false.

## Revised review addendum

- Both actual planning reviews are retained. Initial review rejected underspecified
  quorum/state/proof routing; this revision adopts its fixed-revision narrower slice.
- Generic submit must reject both explicit kind and a case_id pointing to continuity,
  before any generic resubmission. SQL enforces revision1, immutable case identity,
  permitted state transitions and a unique open continuity case per organization.
- A lost/expired/replaced stage grant or changed reviewer security version expires the
  pending case and tracking together, freeing the org for another request. A legitimate
  participant/current OWNER/current stage operator triggers that liveness check under
  org/case locks. Return a minimal truthful closed receipt after commit, not an exception
  inside the UOW that would roll the closure back. Private evidence still needs the
  exact current claimed grant and MFA. Decision authority is recorded separately.
- Every case state maps to the same named recovery tracking status, except APPROVED
  maps to COMPLETED. Tracking kind/user/contact/evidence/reviewer identity cannot change.
- Owner objection is one terminal locked case/tracking/audit transaction competing with
  finalization. Owner inspection is minimal pending metadata, not applicant evidence.
- Storage metadata describes helper tables explicitly; canonical94-table specification
  remains fixed. Runtime helpers do not increase canonical handler acceptance counts.
