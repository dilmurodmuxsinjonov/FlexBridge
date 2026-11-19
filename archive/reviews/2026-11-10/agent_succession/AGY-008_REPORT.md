# AGY008 / Issue #67 Continuation: Minimum `API-108` Academic Conclusion Contract (Read-Only Design)

- **Workspace & Branch**: `D:/Codex/FlexBridge-agents/antigravity` on `agent/antigravity-r1` (`83548d3`); `main`/`master` frozen at `764fb984`; only `integration/r1-agent-collaboration` receives future PRs/merges.
- **Prerequisite State**: `0017_feature_flag_administration` (`PR73`) is in CI (`42765774283` / `42765782879`) and not yet merged. `academic_official_export` and the other 4 locked/R2 flags remain durably `OFF` (disable-only in R1).

---

## 1. Verified Source Facts (Exact Line References)

1. **Personal Teacher Authority & Scope**:
   - [`FlexBridge_toliq_topshiriq.md`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L32-L67) (`#L32`, `#L49-L51`, `#L55`, `#L67`, `#L120-L122`) and [`CAP-024`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L573-L581) (`#L573-L581`) restrict `LOG_ACADEMIC` to `TEACHER` within a personally accepted `academic_assignment` (`DB-052`) under an active same-institution appointment (`INV-03` `#L239`, `INV-08` `#L244`, `INV-10` `#L246`, `INV-15` `#L251`, `INV-16` `#L252`).
   - Teacher replacement never transfers prior authorship (`#L122`), and self-review via another role is forbidden (`#L67`, `#L246`).
2. **Independence from Workplace Approval, Official Grading & Completion**:
   - [`FlexBridge_toliq_topshiriq.md`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L130-L135) (`#L132`, `#L134`, `#L299`, `#L303`), [`PG-043.S03`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L1165-L1174) (`#L1168-L1172`), [`AC-019`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L1340-L1344) (`#L1340-L1344`), [`AC-020`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L1346-L1350) (`#L1346-L1350`), and [`API-108`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_4/FlexBridge_model_1_4.json#L13407-L13418) (`#L13407-L13418`):
     - `API-108` is `POST /api/v1/placements/{id}/academic-decisions` (`cap: LOG_ACADEMIC`, `operation_roles: ["TEACHER"]`, tables `DB-060, DB-052, DB-056, DB-054`).
     - Workplace (`DRAFT/SUBMITTED/APPROVED/RETURNED`, `DB-059`) and academic (`NOT_REVIEWED/REVIEWED/NEEDS_REVISION`, `DB-060`) tracks are separate (`#L132`, `#L578`).
     - Official grade, signature, credit, or export requires a separate institutional agreement and durable flag (`academic_official_export`, locked `OFF` in [`0017_feature_flag_administration.py`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/alembic/versions/0017_feature_flag_administration.py#L64-L82) `#L64-L82`).
     - Placement completion (`COMPLETED`, [`CAP-025`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L583-L591) `#L583-L591`, `#L134`, [`AC-020`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L1346-L1350)) is a separate multi-condition workflow requiring planned tasks/hours (`DB-050`, `DB-057`), closure of material `RETURNED` logs (`DB-055..059`), host conclusion, and academic conclusion.
3. **Canonical Schema (`DB-052`, `DB-054`, `DB-055..060`)**:
   - [`DB-054 placement_decisions`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_4/FlexBridge_model_1_4.json#L4508-L4590) (`#L4508-L4590`; [`FlexBridge_1_4_schema.sql`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_4/FlexBridge_1_4_schema.sql#L787-L798) `#L787-L798`, `#L1625-L1630`) defines `(id, created_at, updated_at, placement_id, actor_id, side, decision, terms_id, reason, decided_at)` with `text` `side`/`decision` and **no canonical SQL enum/check**, no composite FK `(terms_id, placement_id)`, and no immutability trigger yet. Rule (`#L4587`): verify side authority and plan version; not `COMPLETED` until completion conditions close.
   - Currently only [`placement_admission.py`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/services/placement_admission.py#L254-L255) (`#L254-L255`) inserts into `placement_decisions` (`side='HOST'`, `decision IN ('ACTIVATE','CANCEL')`).
   - [`DB-052 academic_assignments`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_4/FlexBridge_model_1_4.json#L4335-L4427) (`#L4335-L4427`), [`DB-055 daily_logs`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_4/FlexBridge_model_1_4.json#L4592-L4658), [`DB-056 log_revisions`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_4/FlexBridge_model_1_4.json#L4660-L4768), [`DB-057 log_task_entries`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_4/FlexBridge_model_1_4.json#L4770-L4848), [`DB-059 workplace_log_reviews`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_4/FlexBridge_model_1_4.json#L4906-L4981), and [`DB-060 academic_log_reviews`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_4/FlexBridge_model_1_4.json#L4983-L5058) store assignment and revision-level diary/review records.

---

## 2. Narrow Contract & New Design Choices vs. Unresolved Semantics

1. **Advisory Teacher Statement vs. Automated Readiness Check**:
   - An *automated readiness check* would assert that required hours (`DB-050.required_minutes`), task entries (`DB-057`), workplace approvals (`DB-059`), and zero open `RETURNED` logs are satisfied—requiring a full lock across all placement logs/workplace reviews and conflating [`CAP-024`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L573-L581) with [`CAP-025`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L583-L591).
   - **Chosen Minimum Contract (New Technical Design)**: `API-108` records an immutable, **nonofficial teacher advisory conclusion** in `DB-054` pinned to an explicit current teacher-reviewed submitted revision (`basis_review_id` + `basis_revision_id` across `DB-060`/`DB-056`) under the current accepted plan (`expected_terms_id`, `DB-050`) and personal assignment (`expected_assignment_id`, `DB-052`). It attests only to the teacher's pedagogical conclusion for that plan/revision basis—never certifying task hours, workplace approval, absence of other/future `RETURNED` logs, official grade/signature/credit, or `COMPLETED` status.
2. **Explicit New Vocabulary (Not Source-Mandated)**:
   - Canonical `DB-054` values: `side = 'TEACHER'`, `decision IN ('ACADEMIC_CONCLUSION_RECORDED', 'ACADEMIC_REVISION_REQUIRED')` (never `READY`, `COMPLETED`, `APPROVED`, or `ACTIVATE`), `terms_id = p.current_terms_id`, `reason = required trimmed text (1..2000 chars)`.
   - Request contract (`POST /api/v1/placements/{placement_id}/academic-decisions`, required `Idempotency-Key` 8..128 chars, `extra='forbid'`):
     - Fields: `expected_assignment_id`, `expected_terms_id`, `basis_review_id`, `basis_revision_id`, `decision`, `reason`.
     - Any grade, score, credit, signature, or official export attribute is rejected (`422`), and `academic_official_export` must be `OFF` (`409` if ever enabled without an official contract).
   - **Basis Coherence**: `basis_review_id` (`DB-060`) must belong to `placement_id`, `expected_assignment_id`, and `basis_revision_id` (`DB-056`); `basis_revision_id` must be the `current_revision_id` of its `daily_logs` row with `status = 'SUBMITTED'` and `terms_id = expected_terms_id`. `ACADEMIC_CONCLUSION_RECORDED` requires `review.decision = 'REVIEWED'`; `ACADEMIC_REVISION_REQUIRED` requires `review.decision = 'NEEDS_REVISION'`.

---

## 3. Forward `0018` Schema, Legacy Capture, Lock Order & Provenance

1. **Forward Migration `0018_academic_decisions` (only after `0017` acceptance)**:
   - Keeps canonical 94 tables unchanged; adds runtime table `flexbridge.academic_decision_proofs` (`127` runtime tables after `0017`'s `126`):
     - `decision_id uuid PRIMARY KEY REFERENCES flexbridge.placement_decisions(id)`
     - `created_at timestamptz NOT NULL DEFAULT clock_timestamp()`
     - `origin text NOT NULL CHECK (origin IN ('PUBLIC','LEGACY_IMPORT'))`
     - `initial_snapshot jsonb NOT NULL CHECK (jsonb_typeof(initial_snapshot)='object')`
     - `placement_id uuid`, `assignment_id uuid`, `terms_id uuid`, `basis_review_id uuid`, `basis_revision_id uuid`, `actor_id uuid`, `session_id uuid`, `auth_version integer`, `teacher_grant_id uuid`, `teacher_appointment_id uuid`
     - `assignment_proof_snapshot jsonb`, `consent_snapshot jsonb`, `basis_review_snapshot jsonb`, `basis_revision_snapshot jsonb`
     - `idempotency_key text`, `request_fingerprint text`, `receipt jsonb`
     - `UNIQUE (actor_id, idempotency_key)` and `UNIQUE (placement_id, assignment_id, terms_id, basis_review_id) WHERE origin = 'PUBLIC'`.
   - **Data-Preserving Legacy Capture**: Existing `placement_decisions` rows not backed by `placement_admission_events(decision_id)` are captured into `academic_decision_proofs(decision_id, origin='LEGACY_IMPORT', initial_snapshot=to_jsonb(d))` with all provenance columns `NULL` (zero invented human/session/teacher consent). `LEGACY_IMPORT` closes immediately in `guard_academic_decision_proof()`.
   - **SQL Triggers & Guards**:
     - `immutable_placement_decisions` and `immutable_academic_decision_proofs` (`BEFORE UPDATE OR DELETE` calling `fn_block_append_only_mutation()`).
     - Deferred constraint trigger `placement_decision_requires_proof` (`AFTER INSERT ON placement_decisions DEFERRABLE INITIALLY DEFERRED`): requires either (`NEW.side = 'HOST'` AND `NEW.decision IN ('ACTIVATE','CANCEL')` AND `EXISTS (SELECT 1 FROM placement_admission_events WHERE decision_id = NEW.id)`) OR (`NEW.side = 'TEACHER'` AND `NEW.decision IN ('ACADEMIC_CONCLUSION_RECORDED','ACADEMIC_REVISION_REQUIRED')` AND `EXISTS (SELECT 1 FROM academic_decision_proofs WHERE decision_id = NEW.id AND origin = 'PUBLIC')`).
     - `guard_academic_decision_proof` (`BEFORE INSERT ON academic_decision_proofs`): enforces `p.status = 'ACTIVE'`, `p.current_terms_id = NEW.terms_id`, `d.placement_id = p.id`, `d.terms_id = NEW.terms_id`, `d.actor_id = NEW.actor_id`, `d.decided_at <= clock_timestamp()`, `q.teacher_user_id = NEW.actor_id`, `NEW.actor_id <> c.user_id`, `q.teacher_grant_id = NEW.teacher_grant_id`, `q.teacher_appointment_id = NEW.teacher_appointment_id`, `academic_teacher_current(a.id, NEW.terms_id)`, personal `academic_assignment_consents` match (`assignment_id, terms_id, actor_id, teacher_grant_id, teacher_appointment_id`), `academic_review_proofs(review_id = NEW.basis_review_id, origin = 'PUBLIC')` match, `l.current_revision_id = r.id`, `r.status = 'SUBMITTED'`, `r.terms_id = NEW.terms_id`, `b.origin='LEGACY_IMPORT' OR current_terms.terms_snapshot->'academic_scope'=b.scope_snapshot`, `placement_actor_current(NEW.actor_id, NEW.session_id, NEW.auth_version)`, `NOT EXISTS (SELECT 1 FROM feature_flags WHERE code='academic_official_export' AND enabled)`, and exact snapshot/receipt equality (`NEW.receipt = to_jsonb(d)`).
2. **Exact Lock Order, Reauth/MFA & Replay Semantics**:
   - **Lock Order**: `institutions` -> `organizations` -> `placements` -> `placement_terms(current_terms_id)` -> `internship_supervisions` -> `student_enrollments` -> `internship_agreements` -> sorted `academic_assignments` (`FOR UPDATE`) -> `daily_logs` -> `log_revisions(basis_revision_id)` -> `academic_log_reviews(basis_review_id)` (`FOR UPDATE`) -> `users(actor_id)` + `pg_advisory_xact_lock(hashtextextended(actor_id || ':' || key, 0))` -> `users(candidate_user_id)` + `candidate_profiles` -> original `institution_role_grants(teacher_grant_id)` + `institution_appointments(teacher_appointment_id)` + `feature_flags('academic_official_export')` (`FOR SHARE`).
   - **Current Authority & MFA**: [`require_current_session`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/services/authority.py#L54-L66) and [`sensitive_roles_for_user`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/services/authority.py#L31-L51) run *after* all locks. Ordinary teacher `PASSWORD` sessions remain valid; if any sensitive role is held or granted during lock waits, `MFA` is required (`403`). No `X-User-Id` fallback (`401`).
   - **Replay & Concurrency**: Current session, active parent chain, original teacher grant/appointment, and exact-plan personal consent are verified *before* idempotency lookup (`academic_decision_proofs` + `idempotency_keys`). Revoked session/grant/appointment/assignment cannot replay an old receipt (`401`/`403`). Same key + different fingerprint returns `409`; same key + matching fingerprint under valid current authority replays the original receipt without inserting a duplicate decision, even if the log pointer advanced after the original commit. Decision, proof, `idempotency_keys`, and [`record_audit_event`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/services/academic_reviews.py#L81-L85) commit atomically.

---

## 4. Canonical Reader Interactions

- Today no reader queries `placement_decisions`; [`placement_admission.py`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/services/placement_admission.py#L254-L255) is its only writer.
- Every future reader (`CAP-025` completion checks, placement decision history, exports) **must** filter `placement_decisions.side` and join the authoritative proof table (`side = 'HOST'` + `placement_admission_events` vs. `side = 'TEACHER'` + `academic_decision_proofs WHERE origin = 'PUBLIC'`). This prevents an advisory `TEACHER` row from being misread as `HOST` activation/cancellation or automatic `COMPLETED`, and prevents `LEGACY_IMPORT` rows from satisfying live completion gates.

---

## 5. Concrete File Ownership & Native Acceptance Plan

- **Owned Files (post-`PR73` merge)**:
  - `backend/alembic/versions/0018_academic_decisions.py`
  - `backend/app/db/academic_decisions.py`, [`backend/app/db/models.py`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/db/models.py), [`backend/app/db/storage.py`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/db/storage.py)
  - `backend/app/services/academic_decisions.py`, [`backend/app/api/v1/academic_admission.py`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/api/v1/academic_admission.py), `backend/ACADEMIC_DECISIONS.md`
  - `backend/tests/integration/test_academic_decisions.py`
- **Native Acceptance Plan**:
  1. HTTP positive (`ACADEMIC_CONCLUSION_RECORDED`, `ACADEMIC_REVISION_REQUIRED`), exact idempotent replay, same-key payload mismatch (`409`), duplicate new-key same-basis (`409`).
  2. Rejections: stale `expected_terms_id`/`expected_assignment_id`/superseded `current_revision_id` (`409`), mismatched review decision (`409`), official grade/signature fields (`422`), `X-User-Id` fallback (`401`), coordinator/mentor/borrowed assignment/self-review (`403`), legacy assignment without `academic_assignment_consents` (`403`).
  3. Real two-session PostgreSQL lock waits observed via `pg_locks` (`wait_event_type = 'Lock'`) for concurrent same-key serialization, session/grant/assignment revocation during lock wait (`401`/`403`), and sensitive-role grant during lock wait requiring `MFA` (`403`).
  4. Direct SQL immutability/proof-trigger rollback, audit failure rollback, and populated `0017 -> 0018` upgrade preserving legacy `placement_decisions` rows as `LEGACY_IMPORT`.

---

## 6. Unresolved Primary Requirements & Next Bounded Task

- **Unresolved Primary Requirements**: Official grading/signature schema and institutional agreement binding (`academic_official_export` stays locked `OFF`), [`CAP-025`](file:///D:/Codex/FlexBridge-agents/antigravity/specs/v1_3/FlexBridge_toliq_topshiriq.md#L583-L591) `COMPLETED` state transition engine (combining hours, zero open `RETURNED` logs, host conclusion, and teacher conclusion), legacy `API-051` acceptance notification worker probe ([`NEXT.md`](file:///D:/Codex/FlexBridge-agents/antigravity/reviews/2026-11-10/academic_reviews/NEXT.md#L12-L18) `#L12-L18`), candidate diary current authority, evidence attachment scan/sharing, and frontend/pilot readiness.
- **Next Bounded Task**: Complete `PR73` (`0017_feature_flag_administration`) exact-head CI verification and merge into `integration/r1-agent-collaboration`, then either run the bounded `API-051` legacy acceptance notification probe or implement `0018_academic_decisions` + `API-108` on a fresh branch off `integration/r1-agent-collaboration`.
