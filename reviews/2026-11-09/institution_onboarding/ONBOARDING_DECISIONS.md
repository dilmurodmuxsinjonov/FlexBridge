# EDU-CODEX-001B — Codex scope decisions after planning review

Planning only; prerequisite PR54 is not yet merged. Read-only Copilot planning
exit0 is retained separately; it is advice, not executed code or acceptance.

Bound the next package to first-institution/first-COORDINATOR and reviewed TEACHER
appointments requested by an existing coordinator. Additional coordinators,
institution recovery, student admission/enrollment/supervision/exports/official
grades remain later work. A known verified institution never regains first-claim
bootstrap because its coordinator expires or is revoked. No role by domain alone.

API017 options require a signed-in session and return generic requirements only.
An ungranted PASSWORD account can read them; the existing global sensitive-account
MFA restriction still applies. API096 requires current MFA for submitters. New
registry identity yields a first-coordinator claim; an existing institution needs
current scoped COORDINATOR authority to request a TEACHER. Server state fixes the
mode and grant type; client input cannot select platform privileges. Rejected or
NEEDS_INFO own claims use explicit same-case resubmission rules, not a fresh
institution. API097 returns requester/named-appointee metadata only. The requesting
coordinator already satisfies requester scope; do not add broad access to every
appointment or reviewer evidence for other institutional coordinators.

Initially staff targets must have a registered account and verified contact. Pin
the exact target user/contact rather than discovering accounts through a public
directory, returning invitation tokens to a coordinator, or silently following a
recycled contact to a new user. Missing/ineligible contacts produce generic
unavailability. Inbox/acceptance require the named account and current contact;
coordinator acceptance needs MFA, teacher-only acceptance retains baseline
assurance. Every consent binds case revision, named user/contact and proposed
role/dates/agreement/legal-basis/evidence snapshot. New revisions invalidate earlier
consent for activation while preserving history. Role grants need both independent
approval and valid named consent for that exact revision. Approval is human review
evidence, not platform verification of legal identity, signature or document truth.

Case anchoring: DB019 has num_nonnulls(...)=1. Anchor an institution appointment
case on appointment_id only, not simultaneously institution_id and appointment_id.
Resolve institution through the appointment and immutable submission. Create
pending institution -> pending appointment -> case -> appointment's nullable case
link in one transaction. Review dispatch must recognize the EDU case kind before
entering organization-only `_operator_case` logic. Preserve organization dispatch,
separate assigned queues/details/downloads and explicit unsupported-case rejection.

Three business days is a weekday-based Tashkent first-response target, not expiry
or automatic review/consent. Keep the original target on NEEDS_INFO and record
each revision/response timestamp. Holiday calendars are not specified; document
this limitation rather than suggesting a statutory deadline. Appointment dates
govern staff authority; agreement dates/purposes independently govern academic use.
First-coordinator activation must have currently valid appointment dates; do not
mark an institution verified while its only coordinator is still future-dated.

Use registry identity normalization and a transaction advisory lock before
institution/case/appointment business locks, then user-before-session authority.
For foreign users/contact ownership, use NOWAIT and the existing exact try-advisory
contact-lock key with re-read; contention is atomic409/retry. Guard helpers must
never wait on foreign-user/contact locks while retaining an opposing authority
lock. Current institution state, submitter authority, target security/contact,
evidence and accepted revision are rechecked at activation, not only preflight.

The planner's schema advice needs adaptation to this repository: canonical v1.4
currently has94 tables, while runtime has107 due to extension migrations. New
immutable submission/consent records can remain explicitly documented runtime
extensions, consistent with owner-governance packages. Do not silently redefine
the canonical table inventory or duplicate metadata tables. Update canonical
constraint descriptions/SQL only where the actual structural change belongs;
keep standalone canonical schema load and upgrade behavior distinct.

A narrow forward migration must seed institutional roles, prevent new structurally
mismatched membership/appointment/user/institution/role grants, and preserve legacy
history. Prefer explicit structural triggers/constraints with clear revocation and
legacy handling rather than inventing legal approval for old rows. Revoke invalid
legacy effective grants without deleting their evidence or repointing appointments.
Do not require validating a NOT VALID FK across unrepairable preserved legacy rows
without an explicit strategy. Preflight normalized registry collisions and stop
for reconciliation rather than auto-merging institutions. Test a populated0010
upgrade, malformed legacy role history, failed collision upgrade rollback, fresh
head, exact new grant constraints and immutable proof records. Old tests that
intentionally manufacture malformed current rows may need a pre-upgrade fixture;
never weaken runtime constraints just to keep those probes insertable.

Evidence access: reuse owned CLEAN/nondeleted PDF eligibility for new uploads, and
current institution-scoped agreement references for existing reviewed agreements.
Do not demand that a new coordinator own an old institution agreement's file.
Named acceptance must expose an intelligible minimal revision snapshot. If file
viewing is needed, use a narrowly authorized requester/named-appointee appointment
download helper with current session/contact, exact revision/file scope, scan checks
and audit; do not weaken general owner-only file downloads or expose all moderator
evidence. No live provider, delivery or legally valid signature is claimed.

Before source changes: write a concrete service/API/migration plan with these
choices, queue an issue, and begin from merged PR54. Codex owns implementation;
external agents remain read-only reviewers. Validate meaningful first/staff
success, MFA/IDOR/contact/consent/revision/independence/role-scope failures, true
row-lock waits in both orders, dedupe, populated migration, audit rollback and
affected modules before complete PostgreSQL CI and pinned source review.
