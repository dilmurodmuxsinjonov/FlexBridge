 1. P1 — Keep API-098 authorization as two separate scopes. The contract permits coordinators and
teachers, but not the same institution-wide view: coordinators should see only supervisions they
personally own and whose agreement, enrollment, and exact opaque purpose remain current; teachers
should see only placements tied to their personally accepted original assignment, with current
original grant/appointment and consent for the revision’s exact terms_id.
academic_supervision_current() checks current supervision and purpose, but not the caller’s
ownership or current coordinator proof; add those predicates. Do not equate any current TEACHER role
with assignment authority, or allow a person to view their own diary through another role (DB-052).
Sources: API-098 in api_kontraktlari.csv and model; DB-029/034/052; 0015_academic_admission.py;
academic_admission.py::material/teacher.
 2. P1 — Make API-099 represent only genuinely current student choices. Require a pending
academic-required placement, no existing binding, and the student’s latest request across all
institutions—not merely the latest request for the requested institution. Tie the request to its
owner’s candidate profile, same placement, institution and enrollment; require the enrollment still
verified/current and the request’s terms_id to match the placement’s current terms. Otherwise a
superseded request or changed plan can expose a stale school selection. Return only
assignment-enabling data: placement/request identifiers and revision, enrollment identifier, minimal
student identity, and current eligible agreement/purpose options (or an existing source for those
options). Never return application/job details, documents, or legal-basis text. Sources:
PG-040.S02/API-099; DB-015/029/034; academic_admission.py::_bind/request_student.
 3. P1 — Make API-105 a list of eligible submitted revisions, not a diary-detail endpoint. Require a
real SUBMITTED revision joined through its daily log to the same eligible academic placement;
exclude drafts and reject self-view. The coordinator branch must tie the placement’s binding to that
actor’s current supervision, exact enrollment and purpose, and current agreement scope. The teacher
branch must use the original teacher proof plus personal acceptance for that revision’s exact terms
version—not just accepted_at or a current TEACHER role. Project only revision/log/placement
identifiers, date, revision number and submission time, plus minimal student identity and purpose as
needed. Do not include summary/task text, evidence, payroll, or job/application fields. Sources:
PG-042.S02/API-105; CAP-021; DB-049/052/055/056; academic_teacher_current() in
0015_academic_admission.py; internship_logs.py::review_academic.
 4. P1 — Preserve business-lock order and make the final query authoritative. For 098/099, lock the
institution before account/session/role authority. For global API-105, first derive candidate
institution IDs from the caller’s relevant supervision/assignment hints, sort and lock them, then
authorize; constrain the final eligibility query to those locked IDs. Never discover and lock a
newly appeared institution after authorization. Hold the current session and exact scoped grants
through response, and run pagination/cursor-anchor checks against the same final eligibility query.
Avoid loading broad rows and filtering in Python or adding late business-row locks. This is
especially important because institution_authority() checks session authority before its scoped role
check, while own_assignments() uses account_authority() before listing and is not a suitable queue
pattern. Require MFA for coordinator access to 099; retain PASSWORD for a teacher-only account
unless another current sensitive role requires MFA. Sources: authority.py, institution_scope.py,
academic_admission.py::own_assignments, pagination.py.
 5. P2 — Add a distinct source-derived student notice when supervision is created.
create_supervision() currently records the responsibility and audit event but queues no notice;
existing academic_notices.py covers teacher nomination/acceptance/revocation and is not a
substitute. Before enabling the private coordinator views, create an in-app notice atomically from
the supervision’s immutable origin, deriving the recipient through the enrollment/candidate
relationship. Since no placement may exist yet, support a nullable placement_id; keep the payload
minimal and do not expose legal-basis text. Sources: academic_admission.py::create_supervision,
academic_notices.py, DB-086/087.
 6. P2 — Keep this unit’s completion claim bounded. The current academic routes contain no handlers
for 098/099/105. Registering these queues does not deliver API-106’s detailed academic view or
API-107/108 actions; those remain subsequent work. Private responses should also be non-cacheable,
with cursors unable to anchor to rows that no longer satisfy current eligibility. Sources:
backend/app/api/v1/academic_admission.py, API-106/107/108, AC-029.

