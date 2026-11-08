# Existing-staff OWNER continuity

This bounded backend flow adds OWNER for an existing staff self-applicant after two
independent procedural reviews. Human reviewers assess authority evidence; software
does not establish legal identity, document truth or actual owner inaccessibility.
Existing OWNER grants, memberships and staff roles remain. No account/contact merge.
Zero-active-OWNER, no-staff and manual same-account identity recovery remain separate.

1. An active HR/HOST_COORDINATOR/MENTOR/BILLING member with current MFA sends
   `POST /api/v1/organizations/{org}/owner-continuity` with `Idempotency-Key`, their
   own verified `contact_id`, owned CLEAN PDF `file_ids` and `evidence_note`. They
   cannot already be OWNER or select another target. The VERIFIED org must have a
   nonempty active OWNER roster. Consent, original staff grant, security version,
   contact binding, evidence and exact OWNER roster are pinned for at most24h.
2. A current MFA MODERATOR uses the dedicated
   `/api/v1/operator/owner-continuity/moderator/cases` queue, claims the case, reads
   its scoped detail/evidence and decides RECOMMEND, REJECT or NEEDS_INFO.
   RECOMMEND only moves to WAITING_COMPLIANCE; it never creates a grant.
3. A different current MFA COMPLIANCE actor uses the corresponding `compliance`
   queue/claim/detail/decision endpoints. Only their APPROVE can create OWNER.
   The two reviewers must be different accounts even if either holds both roles;
   neither may have organization membership history or be the applicant. Claims
   pin exact role grants and security versions. No reassignment in this slice.
4. Approval checks original current intent, roster and both stage authorities under
   locks, then commits one OWNER grant, canonical ownership event, final decision,
   case, recovery tracking and audit together. Grant/event attribution is COMPLIANCE.
   Concurrent retries produce one effect and matching retries return a receipt.

States are WAITING_MODERATOR, WAITING_COMPLIANCE, APPROVED, REJECTED, NEEDS_INFO,
CANCELLED and EXPIRED. Revision is always1. NEEDS_INFO is terminal: new evidence or
stale consent/authority/roster requires a new request and new idempotency key, with
both reviews starting again. Expired or replaced staff/reviewer grants cannot revive
old intent. An authorized read/action/intake closes stale pending cases and their
tracking atomically; no background expiry scheduler is claimed.

The applicant reads `/api/v1/owner-continuity/{id}` and can POST its `/withdraw`
endpoint with a reason. A current MFA OWNER sees minimal pending metadata at the
organization GET endpoint and can POST
`/organizations/{org}/owner-continuity/{id}/object`. Objection and withdrawal race
approval under the same organization/case locks; committed approval cannot be undone
by a later objection. OWNER inspection does not expose applicant evidence. Private
review detail/evidence requires the exact current claimed role grant and MFA.

Canonical recovery tracking uses ORG_OWNER_CONTINUITY, with reviewer_id unused;
independent authority lives in immutable helper events. APPROVED maps to tracking
COMPLETED, other state names match. No account recovery continuations are issued;
account status/reset handlers require ACCOUNT_ACCESS. Generic verification review
and resubmission cannot act on continuity cases, including disguised case-ID requests.

Migration0010 adds two helper tables (runtime107, canonical94 unchanged), exact roster
functions, one-open-case uniqueness, fixed-revision/transition/state-link guards and
immutable proof/history. The null-previous ownership proof explicitly dispatches this
kind before the preserved initial/addition branch; departure proof is unchanged.
SQL verifies relational quorum/current role/contact/roster/grant metadata. Direct
database writers are trusted; actual bearer MFA and contact HMAC belong to the API.

Results and initial failures are retained in reviews/2026-11-09/org003c. TestClient,
synthetic role/contact/CLEAN-file metadata and a second-process service read do not
certify live delivery, browser authentication, registry identity, production or DR.
Pilot remains false. Production reviewer provisioning and human recovery policy are
outside this software test evidence.
