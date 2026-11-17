# Issue #76: Placement-Wide Advisory Teacher Academic Conclusions (`API-108` / `CAP-024`)

## 1. Scope & Contract Implemented
- **Migration `0018_academic_decisions` (`backend/alembic/versions/0018_academic_decisions.py`)**:
  - Adds `flexbridge.academic_decision_proofs` (`128` total runtime tables in `flexbridge`: `94` canonical `v1.4` tables + `34` security/outbox/proof/guard tables).
  - Captures existing `placement_decisions` rows verbatim as `LEGACY_IMPORT` with `NULL` provenance columns during `upgrade()`, then closes the legacy set via `guard_academic_decision_proof()`.
  - Adds `flexbridge.academic_decision_basis(pid, aid)`, `flexbridge.academic_decision_digest(value)`, and `flexbridge.academic_decision_basis_current(did)` (content-only consistency check).
  - Enforces DB-owned top-level transaction audit stamping (`stamp_academic_decision_audit_event` using `pg_current_xact_id()`), immediate row guards (`valid_placement_decision_row`, `valid_academic_decision_proof`), deferred commit guards (`academic_decision_requires_proof`, `academic_decision_current_at_commit`), and append-only immutability triggers (`immutable_placement_decisions`, `immutable_academic_decision_proofs`).
- **Typed Table & Service (`backend/app/db/academic_decisions.py`, `backend/app/services/academic_decisions.py`)**:
  - Implements `AcademicDecisionService.context()` and `AcademicDecisionService.conclude()` with `READ COMMITTED` enforcement, actor/key advisory lock (`pg_advisory_xact_lock`) first, assignment + sorted `daily_logs`/`log_revisions`/`academic_log_reviews` row locks, post-wait authority/session/MFA/exact-consent verification, idempotent replay (`request_record`), and positive conclusion (`ACADEMIC_REVIEW_COMPLETE`) whole-placement completeness validation.
- **API Endpoints (`backend/app/api/v1/academic_decisions.py`, `backend/app/main.py`, `backend/app/db/storage.py`)**:
  - Wires `GET /api/v1/placements/{id}/academic-decision-context` and `POST /api/v1/placements/{id}/academic-decisions` (`API-108`, bringing explicit non-placeholder route registrations from `71/132` to `72/132`).

## 2. Multi-Agent Collaboration & Independent Reviews
- **Antigravity (`AGY-008`, `AGY-010`, `AGY-014`, `AGY-015`)**: Authored initial/revised designs, implemented the 4 core files (`0018_academic_decisions.py`, `db/academic_decisions.py`, `services/academic_decisions.py`, `test_academic_decisions_api108.py`), and completed static read-only source review (`antigravity_source_review.md`).
- **Codex**: Wired `api/v1/academic_decisions.py`, `db/storage.py`, `main.py`, `ACADEMIC_DECISIONS.md`, and `test_academic_conclusion_contract.py`; verified disposable PostgreSQL schema (`schema_probe.json`).
- **GitHub Copilot CLI (`1.0.108`)**: Completed independent read-only security review (`copilot_source_review.md`), finding `0` P1/P2 defects.
- **OpenCode (`opencode/nemotron-3.5-lightning-free`)**: Completed independent read-only security review (`opencode_source_review.md`, `exit_code = 0`). All 6 static observations were evaluated against the SQL/service source and rejected as non-defects with direct source proof:
  1. `basis IS NULL` only occurs when placement/assignment FKs do not match ( zero daily logs still produce a non-null JSONB object via `LEFT JOIN LATERAL (...) logs ON true` + `COALESCE`).
  2. `reviewed_count` (`public_reviewed_count=1 AND public_needs_revision_count=0`) and `needs_revision_count` (`public_needs_revision_count>=1 AND public_reviewed_count=0`) are mutually exclusive per `daily_logs` row, so `pending_count` can never be negative.
  3. `NEW.actor_id <> c.user_id` is an intentional segregation-of-duties rule preventing self-supervision.
  4. `basis_snapshot` is verified equal to `flexbridge.academic_decision_basis(...)` before casting `academic_review_complete`.
  5. `origin == 'PUBLIC'` in `context()` is required by contract (`LEGACY_IMPORT` rows have `NULL` `assignment_id`/`basis_digest` and never fabricate basis-bound conclusions).
  6. Concurrent writes serialize on `academic_service.locked_assignment()` (`placements` + `academic_assignments` `FOR UPDATE`) and the partial unique index `uq_academic_decision_proof_basis`.

## 3. Native Disposable PostgreSQL Verification
- `schema_probe.json`: `actual_head = 0018_academic_decisions`, `actual_tables = 128`, `proof_rows = 0`.
- `contract_first_implementation.xml` (`test_academic_conclusion_contract.py`): **`6 passed in 77.674s`**.
- `agent_security_fixture_corrected.xml` (`test_academic_decisions_api108.py`): **`9 passed in 112.642s`**.
- `migration_and_regressions.xml` (`test_academic_migration.py`, `test_academic_review_migration.py`, `test_enrollment_migration.py`, `test_regressions.py`): **`44 passed in 271.82s`**.
- `academic_suite_regressions.xml` (`test_academic_admission.py`, `test_academic_authority.py`, `test_academic_reviews.py`): **`95 passed in 676.46s`**.
- **Branch Policy**: `main` remains frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6`. All PRs target `integration/r1-agent-collaboration`.
