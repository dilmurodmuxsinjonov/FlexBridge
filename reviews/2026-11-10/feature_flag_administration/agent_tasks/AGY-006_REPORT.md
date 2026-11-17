### AGY006 / Issue 72: Focused Proof-Control Regression Draft

**Owned File**: [backend/tests/security/test_feature_flag_proof_controls.py](file:///D:/Codex/FlexBridge-agents/antigravity/backend/tests/security/test_feature_flag_proof_controls.py) (new file created; all other files remain frozen).

#### Implemented Controls
1. **Exact Receipt & Digest DB Guard Rejections** (`test_event_insert_guard_rejects_corrupted_receipt_before_version_unique_check`, `test_event_insert_guard_rejects_wrong_after_digest_before_version_unique_check`):
   - First creates a baseline valid ADMIN event via [`flag_admin_service.administer`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/services/feature_flag_admin.py#L122-L155).
   - In a new transaction, copies that event with a new UUID and genuine same-transaction audit event via [`AppendOnlyAuditStore`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/core/audit.py#L11-L22) matching metadata/source/actor.
   - Parameterizes receipt corruptions (`wrong_enabled`, `extra_key`, `missing_decided_at`) asserting specific trigger rejection: `feature flag event requires the exact minimal receipt`.
   - Tests corrupted `after_digest` asserting specific trigger rejection: `feature flag event must equal the canonical flag state`.
   - Verifies the `BEFORE INSERT` guard fires prior to table-level `UNIQUE(flag_id, version)` constraint evaluation, preserves SQL `null()` for optional snapshot/digest columns, and asserts zero events or audits persist after rollback.

2. **Real Clock Expiry Before Outer Commit** (`test_real_clock_expiry_after_valid_event_insertion_fails_outer_commit`):
   - Labels trusted fixture mutation: sets `platform_role_grants.expires_at` to the near future (`clock_timestamp() + interval '1.5 seconds'`).
   - Inserts valid change while grant is active (`receipt['version'] == 1`).
   - Bounds wait via PostgreSQL `clock_timestamp()` polling (bounded to 8 seconds).
   - Outer commit fails on deferred constraint trigger [`feature_flag_event_current_at_commit`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/alembic/versions/0017_feature_flag_administration.py#L267-L284) (`feature flag change requires current ADMIN authority at commit`).
   - Verifies rollback: no `feature_flags`, origins, events, or audits survive.

3. **REPEATABLE READ Outer Isolation Rejection** (`test_repeatable_read_outer_transaction_fails_isolation_unsafe_with_no_effects`):
   - Uses [`storage.transaction`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/db/storage.py#L167-L179) `ContextVar` joining and executes `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ` before any queries.
   - Asserts failure: 503 `FEATURE_FLAG_ISOLATION_UNSAFE` via [`GovernanceError`](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/services/governance.py).
   - Asserts no side effects survive.

#### Verification & Compile
- Syntax & Bytecode Compilation: `python -m py_compile backend/tests/security/test_feature_flag_proof_controls.py` exited `0`.
- AST validation passed (`ast.parse` exit `0`).

#### Limitations & Boundary
- No native test execution was run on the shared runner; reserved for Codex.
- No git commits, tags, branch switches, or mutations outside the single owned file.
- Full R1/API-108/downstream business gates/frontend/legal/providers/DR/pilot remain open.
