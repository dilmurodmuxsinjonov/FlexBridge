# ORG-CODEX-003C1 — existing-staff OWNER continuity with two independent reviewers

Planning only, after003B acceptance. Canonical DB-006 includes last-owner recovery;
DB-027 requires independent review and append-only ownership history. IAM cryptographic
same-account recovery already exists. This slice handles an existing active staff
member seeking OWNER continuity when current owners cannot provide the ordinary003A
request. It does not claim to prove legal authority or account inaccessibility in code.

The applicant is always the authenticated current-MFA user themselves, already an active
HR/HOST_COORDINATOR/MENTOR/BILLING member in that VERIFIED organization, not already an
OWNER. They supply their own current verified contact and owned clean PDF evidence.
No arbitrary target account, new membership, client role or claimed paid/approved flag.
Their explicit consent binds revision/contact/security/exact staff grant and lasts24h.
An immutable request pins the organization, applicant and original active OWNER roster.
Keep at most one open continuity request per organization under the organization lock.

An independently assigned current-MFA MODERATOR reviews the evidence and records a
reasoned recommendation. A different current-MFA COMPLIANCE actor, also unrelated to
the organization and applicant, reviews the same revision and independently authorizes
final approval. A user holding both roles cannot supply both decisions. Recommendation
does not create a grant. NEEDS_INFO/resubmission and stale consent require fresh evidence
revision/consent and discard earlier recommendation. Withdrawal/rejection/cancellation
preserves history and never grants OWNER.

Finalization rechecks exact active applicant staff grant/account/contact/consent, current
unchanged original OWNER roster, current reviewer roles/independence, assigned moderator,
same revision/recommendation and clean owned evidence under organization -> case locks
and authority row locks. Commit one new OWNER grant, a canonical ownership event, case,
canonical recovery-request status and audit atomically. Preserve previous OWNER grants,
memberships and staff roles; no account/contact merge or automatic owner removal.
Roster/grant replacement invalidates old intent and requires a new request. A new grant
must never be justified by stale recommendation or revived old staff authority.

Use canonical recovery_requests for durable tracking plus scoped helper proof records.
Explicit operator dispatch must precede generic fallback; finalization is dedicated to
COMPLIANCE and cannot be invoked by generic moderator APPROVE. Existing initial,
additional and departure SQL proofs retain their meaning. A dedicated recovery proof
must check both independent reviewers, exact consent/revision/roster/applicant and final
grant/event attribution. Direct DB writers remain trusted, bearer MFA/contact HMAC is
verified by the API. Private queues/details/evidence expose only assigned scope.

Test no grant before both decisions, wrong account/org/staff role/MFA, same reviewer,
unassigned review, stale contact/grant/security/revision/roster/recommendation, actual
revoke-reinvite-regrant, concurrency/retry/conflict, cancellation/finalization races,
failure rollback, immutable proof/history, populated upgrade, persistence, complete
PostgreSQL CI and pinned read-only source review.

Human reviewers must assess the supplied authority evidence; fixtures do not establish
identity or a legal recovery policy. No live registry/notifications/browser or production
approval is inferred. Applicants without existing staff access and manual same-account
identity recovery remain separate follow-ups. pilot_ready remains false; EDU follows.
