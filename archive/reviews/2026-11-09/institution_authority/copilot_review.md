Review outcome: A bounded institution / first-coordinator / staff-appointment package is feasible,
but actual institutional role grants should be gated on prerequisite authorization fixes. No
implementation was made. Finish human-money PR52 before EDU runtime work.

Source-backed requirements: v1.3 says a role choice starts a request, not authority; a domain alone
is insufficient; formal appointment needs independent platform review, personal acceptance, and an
agreement/legal basis. It proposes a three-business-day first-response target and requires
NEEDS_INFO to add a revision to the same request without erasing history. CAP-019 and PG-039 carry
those requirements forward. The v1.4 model provides institutions (DB-028), agreements (DB-029),
memberships/grants (DB-030/031), appointments/invitations (DB-032/033), and verification
cases/evidence (DB-019/020). Those records support the flow, but cannot prove real identity,
document truth, or legal signature.

Key authorization gap: auth.roles_for() and require_institution() grant role labels from active
membership/grant rows, but do not validate membership acceptance, the linked appointment’s status
and date window, its personal acceptance, or that its user and institution match the membership.
DB-031’s “active official appointment” rule is descriptive; the SQL primarily enforces independent
foreign keys, not those relationships or role scope. The internship service uses
require_institution() for coordinator assignment, while its teacher and review checks likewise do
not establish appointment validity. As written, current rights do not enforce appointment
status/dates and personal acceptance.

There is also a bootstrap authorization conflict to resolve: API-017/096/097 label the actor
COORDINATOR, although a first coordinator has no such grant yet. API-065 is a useful precedent:
despite its operation-role labels, organization self-intake requires MFA and deduplicates identity
without first requiring an OWNER grant. Apply the same distinction between claim/request and granted
role to EDU; never accept a client role flag as authority. The canonical-route fallback currently
registers unimplemented APIs as authenticated 501 handlers, so API-017/096/097 need explicit
handlers and server-side dispatch before onboarding is exposed.

Recommended bounded scope: after PR52, stage EDU work with an authorization-hardening gate before
enabling any new real institutional grants. Keep the onboarding package together, using explicit
service paths for (a) first-institution/first-coordinator claim and (b) staff appointment under an
existing, scoped coordinator. Scope the changes to backend/app/services/auth.py,
backend/app/api/dependencies.py, backend/app/services/internship_logs.py, the governance service/API
paths, explicit API-017/096/097 handlers in backend/app/api/v1/canonical_routes.py, and a dedicated
institution-onboarding service. Keep the v1.4 model and SQL aligned, with a forward migration for
constraints/backfill; use DB-019/020 revisions and evidence, DB-028/029, and DB-030–033. API-097
should expose only the requester’s case/appointment or a properly scoped staff request—not reviewer
evidence to arbitrary coordinators. Reviewer operations should be a separate, independently
authorized path.

For first claims, serialize normalized registry-code dedupe and lock the institution/case rows in
the transaction, following the organization tax-ID advisory-lock pattern. Do not create a second
institution for a known registry code. A known institution with no active authority must not regain
bootstrap through a fresh self-claim; use a distinct, independently reviewed recovery path that
preserves the institution and its history. Require the current account’s verified contact, MFA for
privileged submission, evidence owned by the submitter and eligible for review, and explicit
personal acceptance bound to the named user. Staff appointments should use the existing
invitation/contact-digest pattern, with one-time acceptance by the named user. Resolve the request
type from server-side institution and actor state, not a submitted COORDINATOR/TEACHER flag.

Grant only after independent review and named-user acceptance, with institution, user, role scope,
status, and validity dates cross-checked. Recheck those conditions in roles_for(),
require_institution(), and the service transaction that performs sensitive work; avoid a separate
check-then-write authorization window. Revoke/suspend atomically and ensure subsequent requests lose
authority. Preserve the existing globally sensitive COORDINATOR MFA gate; require MFA explicitly
for ungranted first-claim submission. Do not add a blanket MFA requirement to ordinary TEACHER reads
or weaken the privileged coordinator gate.

DB-029’s purpose and validity dates should gate the academic uses they cover; DB-032’s validity
dates should gate appointment authority. Treat the three-business-day value as a response target,
not a consent expiry or automatic acceptance. A resubmission should increment the same case revision
and retain prior evidence/decisions. Use current contact-lock and transaction patterns from
identity handling. The agreement file and moderator decision are review evidence—not platform
certification of its legal validity.

Acceptance criteria for Codex: test first-claim creation and concurrent duplicate registry
submissions; existing-institution staff requests versus bootstrap/recovery; rejection of
domain-only, wrong-user/contact, unverified-file, missing-MFA, self-review, and
mismatched-institution/user cases; no role grant before both review and personal acceptance;
same-case NEEDS_INFO revision history; date-bound access and revoke behavior across subsequent
requests; and legacy history/fixture handling without runtime test bypasses. Fixtures should
represent valid appointments rather than relying on permissive authorization.

Preserve API-094’s billing behavior and the current API-107 baseline. Student enrollment,
supervision, exports, grades, and other academic flows remain later scope; this review does not
establish them as ready. Unresolved: whether API-017 options are public or require a signed-in
account, and the precise re-review/SLA clock after a NEEDS_INFO revision; neither changes the rule
that the SLA is not consent expiry. No tests, SHA verification, or pilot acceptance are claimed.

