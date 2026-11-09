I’ll compare the proposed package with the pinned local specs and the current service, schema, and
dispatcher implementations, then return a bounded sequence and the concrete conflicts—without
changing files or running commands.

The key architectural constraint is clear: public API-027/034 and operator verification actions are
currently contract placeholders, while the academic runtime already treats VERIFIED as an
authority-bearing status. I’m checking the live institutional review patterns and schema constraints
now to distinguish reusable mechanics from assumptions that do not fit enrollment.

Verdict: The package is implementable, but it needs three decisions before coding: an explicit
legacy eligibility rule, a proof/history shape beyond DB-019/020, and a lock order compatible with
academic consumers. Start only after PR62’s final-head CI is accepted; this review does not treat it
as accepted.

Concrete gaps and contradictions

 - API-027 and API-034 are not implemented: the canonical router supplies 501 placeholders. API-109
and API-110 are live in organizations.py; queue results combine organization and institution
services, while claim/detail/download/decision dispatches by case kind. A new enrollment kind would
fall through to the organization service and be rejected. Add an explicit enrollment-service branch,
and revalidate kind and subject inside that service’s transaction—the route’s preliminary case read
is not authority.
 - VERIFIED is already consequential: _academic_binding accepts it when the enrollment dates are
current, without requiring a linked case or evidence. Conversely, roles_for does not derive STUDENT.
Keep those concepts separate: a status may satisfy the existing academic predicate; a role label
must not grant authority.
 - DB-019 requires exactly one subject. For an enrollment case, set enrollment_id only; derive
candidate ownership through the enrollment. DB-020 evidence rows are append-only, but carry only
case/revision/file/note—not an immutable file snapshot. DB-019’s current decision fields are
mutable, and DB-015 has no idempotency record. A forward migration therefore needs typed,
append-only revision/evidence snapshots and decision history, plus persisted idempotency
key/fingerprint/receipt. Preserve the existing one-subject constraint and the canonical 94-table
baseline.
 - Existing academic operations lock institution, then placement/supervision (and assignment where
applicable), then enrollment and agreement, before current actor authority. The proposed
candidate/enrollment-first ordering can conflict if a new path later takes academic locks. Also,
newly approved enrollment status must be synchronized with the exact current evidence revision; the
status alone cannot prove which revision was reviewed.
 - The source’s proposed first-response target for candidate documents is one working day, with
escalation when overdue. The institution-onboarding three-day helper is not the enrollment policy.
Due time must never imply approval.

Bounded sequence and decisions

 1. After PR62 acceptance, define 0013 around DB-015/019/020: append-only typed enrollment revision
and decision records, pinned evidence snapshots, and idempotent request receipts. Require new public
VERIFIED writes to have an approved matching case, candidate/enrollment scope, and exact reviewed
revision.
 2. Implement own API-027/034 and bounded detail/end/revision lifecycle. Education stays optional;
declaration without evidence is non-eligible. Require a verified institution for evidence-backed
verification; keep student reference purpose-bound and digest-only. Use a new enrollment for
approved program/institution changes or extensions; never erase old history.
 3. Extend the operator queue and explicit claim/detail/private-download/decision dispatch. Require
current MFA/MODERATOR authority, assigned independent reviewer, matching revision and reason;
recheck current CLEAN file ownership and bucket/VersionId/ETag snapshot before approval. NEEDS_INFO
adds a revision to the same case and preserves earlier decisions. No auto-approval.
 4. Keep roles_for unchanged in this package; defer STUDENT-label work to eligibility consumers.
Derive any current-student indicator from the agreed eligibility predicate and local date, never
from a declaration or role label. Existing academic consumers still need their own acceptance
changes where not already guarded.

Lock order: institution row(s), UUID-sorted; any touched academic rows in existing order—placements,
supervisions, assignments, each UUID-sorted; candidate profile; enrollment; agreement if needed;
verification case; revision/evidence rows; file rows; then current user/session/MFA/grant authority,
held through commit. Do not lock an enrollment and then reach back for academic rows. For own
reads, derive candidate scope inside the transaction before disclosure.

Legacy policy: Preserve the exact pre-migration VERIFIED rows as an explicit, marked compatibility
set for current academic behavior; do not invent review cases or evidence for them, and do not
present them as publicly reviewed. New public approvals require full proof. Preserve all history and
imported rows; no destructive cleanup.
