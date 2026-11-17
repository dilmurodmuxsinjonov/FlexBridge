# AGY014 / Issue76: implement actual placement-wide academic conclusion draft

You are not alone. D:/Codex/FlexBridge-agents/antigravity, agent/antigravity-r1,
ACTUAL HEAD accepted integrationd72462e7, runtime0017/127,canonical94. Preserve
AGENTS.md/protocol Q016 WIP; Codex remains coordinator. Main/master FROZEN764fb984.
All future PRs/merges integration-only. No Git/GitHub/other agents/install/live/
provider/.env/.data/credentials actions. No native tests until Codex wires files.

OWN ONLY FOUR NEW FILES:
backend/alembic/versions/0018_academic_decisions.py
backend/app/db/academic_decisions.py
backend/app/services/academic_decisions.py
backend/tests/security/test_academic_decisions_api108.py
Do not edit existing shared modules/tests/fixtures/policy. Compile these4 with
D:/FlexBridge/.venv/Scripts/python.exe if allowed, report actual result. No native
tests. Codex owns storage/router wiring, independent contract tests/docs/review.

Read actual metadata/helpers/spec CAP024/PG043.S03/diary completion prose and
AGY-010_CODEX_REVIEW.md (explicit allowed D:/Codex/FlexBridge-agents file).
This FIXED contract supersedes the single-review basis proposal: API108 records
a PLACEMENT-WIDE nonofficial teacher conclusion on the ENTIRE current diary set,
not an alias for API107. Official grades/credit/signature/export remain unavailable.

INTERFACE:
- AcademicDecisionService, singleton academic_decision_service.
- context(actor,placement_id,assignment_id) -> minimal dict: placement_id,
  academic_assignment_id,terms_id,version (terms),basis_digest,log_count,
  submitted_count,reviewed_count,needs_revision_count,pending_count,
  academic_review_complete (bool),new_conclusion_allowed (ACTIVE only),
  current_conclusion (matching PUBLIC canonical receipt orNone),advisory_only=True.
  No raw diary text/task/files/legal basis/staff session/grant in response.
- conclude(*,actor,placement_id,assignment_id,terms_id,version,expected_basis_digest,
  decision,reason,idempotency_key) -> exact stored canonical DB054 snapshot only.
- intent_lock_key(actor_id,key) -> 'academic-decision:'+actor_id+':'+key, exported.
- db register_tables(metadata,types), exact one helper academic_decision_proofs.

NEW DECISIONS (design, not canonical source enums): side='TEACHER',
ACADEMIC_REVIEW_COMPLETE or ACADEMIC_REVISION_REQUIRED. Reason trimmed1..2000,
nonce8..128, expected_basis_digest64lowerhex, strict integer planversion>0.
Positive requires NONEMPTY complete current diary: every daily_log's current
revision is actual candidate-authored SUBMITTED (submitted_at<=DBclock), belongs
to this placement and currentterms, and has own assignment PUBLIC academic review
proof/REVIEWED with no PUBLIC NEEDS_REVISION/conflicts. Missing/draft/oldterms/
unproved review cannot yield positive. Negative can record pending work, even
empty diary. No hours/workplace/grade/credit/completion certification or mutation.
Do NOT read raw official flags or require themOFF for this nonofficial action.

FULL BASIS / STALE INTENT:
Create stable UTC SQL academic_decision_basis(pid,aid) JSONB of full current plan
snapshot, assignment/source snapshot, and ALL current daily_logs sorted byid,
their current revision snapshots (including missing ones), and ALL relevant
academic reviews/proof snapshots for that assignment/revision sorted byid. No
single selected review. Full PUBLIC reviews only certify REVIEWED; retain legacy
history without certifying it. Internal basis may contain diary text; never HTTP.
Digest via SHA256 of canonical JSONB text in SQL. Export SQL helpers as needed.
context returns counts+digest from that exact server basis, not client counters.
Positive complete iff log_count>0 and reviewed_count==log_count. Pending count
=logcount-reviewed-needsrevision, disjoint categories; oldterms/drafts are pending.
POST new intent after authority/replay checks requires current terms/version,
ACTIVE and matching expected digest; stale basis412 ACADEMIC_BASIS_CHANGED,
positive pending409 ACADEMIC_REVIEWS_PENDING. Duplicate new-key same assignment/
terms/basis409 ACADEMIC_CONCLUSION_ALREADY_RECORDED. Changed same-key intent409.

LOCKS / CURRENT AUTHORITY / REPLAY:
Require actual READ COMMITTED for both methods (503 ACADEMIC_DECISION_ISOLATION_UNSAFE
otherwise). POST actor/key advisory FIRST, before business/actorFK/authority locks.
Then use actual academic_service.locked_assignment for institution->org->placement/
currentterms->supervision/enrollment/agreement/assignment, lock requested terms,
ALL current daily_logs sorted, current log_revisions sorted and relevant reviews
sorted. Existing candidate writers lock placement first; FK inserts also wait.
No fabricated names/columns. After ALL waits: material(), teacher(), final
account_authority(), actual SQL placement_actor_current/academic_teacher_current
using requested exact terms, exact original grant AND appointment, explicit
personal consent even LEGACY assignment, revision author/placement linkage.
Ordinary current Teacher PASSWORD remains valid; sensitive roles appearing while
waiting must require MFA. SQL clock after waits, not cached before waiting.
context requires currentterms consent. POST current material/original teacher/
session/purpose/exact requested old consent precedes request_record replay lookup;
old exact receipt can replay after pointer/plan/cancel changes when that current
relationship remains valid. New currentbasis/currentplan/ACTIVE checks only AFTER
lookup. Return identical old receipt with no new decision/audit. Never rebuild
authority from UID or original session snapshot.

SCHEMA / GUARDS / HISTORY / ATOMIC AUDIT:
Forward0018 from0017, exactly ONE helper -> measured128 expected, not claimed yet.
Proof PKdecision_id FKDB054; created_at,origin,initial_snapshot canonical;
PUBLIC placement/assignment/terms/terms_version, actual actor/session/auth_version,
teacher_grant_id/teacher_appointment_id, teacher_consent_id+consent_snapshot,
assignment_proof_snapshot,basis_snapshot,basis_digest, audit_event_id(unique FK),
nonce/fingerprint/exact canonical receipt. UNIQUE(actor_id,key), partial UNIQUE
(assignment_id,terms_id,basis_digest) forPUBLIC. Require every PUBLIC field actually
nonNULL/typevalid; LEGACY provenance must be NULL. Capture ALL old DB054 rows
verbatim as LEGACY_IMPORT with no invented teacher/session/intent and closecapture.
Stable UTC snapshot function for DB054/plan/basis/proof comparisons (avoid session
TimeZone mismatches); use CAST not colon/percent hazards in op.execute strings.
Append-only DB054/proof; new TEACHER rows only new vocabulary/reason and require
matching PUBLIC proof at commit. New teacher vocabulary with nonTEACHER side
rejected; preserve all unrelated HOST producer semantics, no imaginary event
decision_id linkage. Legacy canonical rows remain exact, no current auth invented.

Same transaction REAL audit: service order decision->AppendOnlyAuditStore append
action ACADEMIC_DECISION_RECORDED objecttype placement_decision/objectkeydecisionid,
metadata sourceAPI108/assignment/terms/basis_digest ->proof. DB-owned narrowly
scoped audit BEFORE INSERT stamp _academic_decision_top_xid=pg_current_xact_id text,
unconditionally overrides caller stamp, other actions untouched. Proof guard
checks exact actor/action/object/metadata +sameTOPtxn (savepoint-safe), actual
canonical receipt/snapshots/basis/digest/current authority/consent. Deferred commit
recheck current source+plan+basis+authority so late expiry/source change rolls back.
Failure after audit rolls back all. No weakened guards/test-name/literal exceptions.

Provide internal SQL academic_decision_basis_current(decision_id) content check:
PUBLIC proof canonical/basis matches current source (not auth derived from old
session). Logout must not erase a committed conclusion. This is not a grant for
future completion/read; caller still checks current authority/remaining CAP025.

TEST DRAFT: reuse actual ready/Teacher PASSWORD HTTP fixtures; trusted staff
metadata labelled. Positive/negative, ALL-LOG pending denial/stale digest after
new draft, same receipt/newkey conflict, current/foreign/self/revoked/MFA afterwait,
actual observed actor-key/parent waits with PIDs/blockers, rollback/audit SQLproof,
savepoint, timezone, populated0017->0018 and failure rollback/HOST compatibility.
Codex has separate independent full-set contract tests; don't edit them. No new
fake MFA sessions, no synthetic grade/provider acceptance. Return <=900words
actual four files/compile/interfaces/risks; no claimed native tests/fullR1/pilot.
