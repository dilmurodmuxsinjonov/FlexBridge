Closes #76

### Summary
- Implements placement-wide nonofficial advisory teacher academic conclusions (`API-108`: `POST /api/v1/placements/{id}/academic-decisions` and `GET /api/v1/placements/{id}/academic-decision-context`) over the complete current diary/revision/academic-review basis (`CAP-024`, `PG-043.S03`, `DB-054`).
- Adds migration `0018_academic_decisions` (`flexbridge.academic_decision_proofs`, `128` total runtime tables in `flexbridge`), preserving existing `placement_decisions` rows verbatim as `LEGACY_IMPORT` and enforcing immediate + deferred PostgreSQL triggers, top-transaction `pg_current_xact_id()` audit stamping, and append-only immutability.
- Enforces `READ COMMITTED`, actor/key advisory locking before business/authority locks, sorted diary/revision/review row locking, post-wait session/MFA/teacher/consent re-evaluation, idempotent replay survival across later pointer/plan/cancel changes, and strict `ACADEMIC_REVIEW_COMPLETE` vs. `ACADEMIC_REVISION_REQUIRED` invariants without mutating placement status to `COMPLETED` or fabricating official grades/credits.

### Verification & Multi-Agent Review
- **Disposable PostgreSQL Native Tests**:
  - `test_academic_conclusion_contract.py`: **`6 passed in 77.674s`** (`contract_first_implementation.xml`)
  - `test_academic_decisions_api108.py`: **`9 passed in 112.642s`** (`agent_security_fixture_corrected.xml`)
  - Migration & regression suites updated and verified for `0018_academic_decisions` (`128` tables).
- **Independent Static Reviews**:
  - **Antigravity (`AGY-015`)**: `reviews/2026-11-10/academic_conclusions/antigravity_source_review.md` (`0` P1/P2 defects)
  - **GitHub Copilot CLI (`1.0.108`)**: `reviews/2026-11-10/academic_conclusions/copilot_source_review.md` (`0` P1/P2 defects)
  - **OpenCode (`opencode/nemotron-3.5-lightning-free`)**: `reviews/2026-11-10/academic_conclusions/opencode_source_review.md`
- **Target Branch**: `integration/r1-agent-collaboration` (`main` remains frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6`).
