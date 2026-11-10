I could not read D:\Codex\FlexBridge-plans\edu\ACADEMIC_RECORDS_PLAN.md; the view tool denied
access. This review is therefore grounded in the repo’s
reviews\2026-11-10\internship_admission\NEXT_ACADEMIC_UNIT.md and ACADEMIC_QUEUES_PLAN.md, plus the
source/specs below—not a verification of that external plan’s exact wording.

Ordered implementation decisions

 1. Keep API-106 read eligibility separate from review-write eligibility. API-105’s queue is
intentionally limited to current submitted revisions on ACTIVE placements; don’t reuse that filter
for API-106. Resolve the requested immutable revision directly, verify it is submitted, and
authorize against the caller’s current, exact supervision/purpose or original personally accepted
teacher assignment for that revision’s terms. A later revision becoming the log pointer must not
hide an otherwise readable historical submission. Conversely, API-107 must independently enforce
write eligibility: current original teacher authority, personal acceptance for the exact revision
terms, non-self review, submitted revision, and the required live academic scope. Cancellation
should not erase the source relation or historical read path, but must not make an ineligible review
writable. Sources: academic_views.py::review_queue; internship_logs.py::review_academic and
::_academic_binding; 0015_academic_admission.py::academic_supervision_current /
academic_teacher_current; CAP-021 and API-105/106/107.
 2. Make revision identity and retries explicit, including on the legacy alias. The current
/daily-logs/{daily_log_id}/academic-reviews handler accepts no expected revision or nonce, and
review_academic resolves daily_logs.current_revision_id at write time. That can review text the
caller did not see if the pointer changed after their read. Require an expected revision ID and
idempotency nonce on the alias; compare the expected ID to the submitted target and reject mismatch
rather than silently following the pointer. API-107’s revision path already names the target, but
still needs a durable same-nonce/same-payload replay receipt and changed-payload conflict handling.
DB-060’s (revision_id, academic_assignment_id) uniqueness prevents duplicate inserts; it does not
define safe replay or provide a nonce. Sources:
app\api\v1\internship_logs.py::AcademicLogReviewRequest and submit_academic_review_endpoint;
internship_logs.py::review_academic; DB-060 in specs\v1_3\baza_lugati.md and
specs\v1_4\FlexBridge_1_4_schema.sql.
 3. Resolve the review-vocabulary mismatch without rewriting history. DB-060 specifies REVIEWED /
NEEDS_REVISION; API-107’s CSV says the same. The existing service accepts APPROVED, REJECTED, and
CHANGES_REQUESTED. Do not normalize existing rows or expand the new API based on that
implementation. Decide the supported new-write vocabulary from the primary contract, preserve all
stored review values verbatim, and make any legacy compatibility explicit and read-only unless a
source-defined conversion exists. Sources: CAP-024; API-107 in specs\v1_3\api_kontraktlari.csv;
DB-060 prose; internship_logs.py::review_academic.
 4. Do not turn API-108 into an inferred grading or lifecycle gate. CAP-024 says academic review is
separate from workplace approval and that official grading/signature needs a separate agreement.
API-108’s contract mentions an official grade/sign flag and agreement, but the reviewed sources do
not define its decision vocabulary or authoritative semantics. Keep advisory review distinct from
placement completion, host decisions, and mentor approval; do not infer enums, legal effect, or a
flag-controlled grading gate. Do not use the in-memory FeatureFlagService for such a gate. Teacher
PASSWORD remains valid unless the existing sensitive-role policy requires MFA. Sources: CAP-024;
API-108 in api_kontraktlari.csv; DB-054 / DB-060; feature_flags.py; existing PASSWORD acceptance
control in tests\security\test_academic_authority.py.
 5. Keep every read and write narrowly tied to the source relation. Preserve exact student,
placement, enrollment, supervision, purpose, assignment, and revision/terms links; cancellation must
not delete or broaden those links. Do not widen a revision lookup to other students, jobs,
applications, payroll, or files. API-106 should expose only the scoped diary detail the contract
supports; do not invent DB-058.visibility values or provide evidence/file URLs absent an explicit
policy and separate file authorization. The file service currently issues downloads only to the file
owner. Sources: CAP-021; DB-055/056/057/058/060;
files_quarantine.py::issue_signed_download_url_api_x03.
 6. Preserve the established lock order and recheck hints. Derive institution IDs from non-sensitive
hints, lock institution before organization and placement, then lock the exact academic material
and log/revision rows, and only then pin current session/account authority and the exact scoped
grant through commit. Revalidate that hint-derived institution/placement/assignment/revision links
have not changed; never acquire a late institution lock after organization or placement locks. Keep
log writes and review writes ordered placement → daily log → revision, and serialize review/decision
against revocation, cancellation, and plan changes. Avoid an ACTIVE-only read helper that would
defeat historical API-106 access. Sources: academic_admission.py::locked, locked_assignment,
teacher; placement_admission.py::host_decision; internship_logs.py::review_academic;
academic_views.py::review_queue; NEXT_ACADEMIC_UNIT.md lock-order note.
 7. Constrain 0016 to additive, history-preserving work. Preserve canonical
DB-052/054/056/058/059/060 rows, IDs, timestamps, comments, and exact stored vocabulary. Do not
manufacture legacy consent or decisions, rewrite source history, or use migration as an excuse to
infer past intent. Any added replay evidence or constraints need to work with populated history; a
failed upgrade must roll back fully to 0015 without partial DDL/data effects. Sources:
0015_academic_admission.py upgrade and immutable-history guards; 0014_placement_admission.py;
DB-052/054/056/058/059/060 in FlexBridge_1_4_schema.sql.

Required tests for the implementation: API-106 reads an older submitted revision after pointer
change and after placement cancellation only while the exact current-purpose relationship remains
valid; deny drafts, self-view, wrong student/placement, stale or revoked scope, wrong teacher/terms,
and cross-job/payroll/file access. For both APIs 107 and 108, cover same-nonce replay, nonce reuse
with changed payload, stale expected revision, concurrent pointer change/revoke/cancel, duplicate
submissions, exact decision vocabulary, current sensitive-role MFA changes during waits, and
ordinary Teacher PASSWORD. Exercise lock-order races and stale-hint retry behavior. For 0016,
upgrade populated canonical history and force a mid-upgrade failure, then confirm exact rollback and
unchanged historical review/decision rows. No tests were run; this was planning-only.

