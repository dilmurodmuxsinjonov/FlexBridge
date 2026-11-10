Closes #77

### Summary
- Enforces post-wait `ActorContext`, `READ COMMITTED` transaction isolation, candidate profile ownership lock, global sensitive-role MFA re-evaluation (`account_authority`), and fresh-clock `flexbridge.placement_actor_current` session validity **after** all business (`placements`, `daily_logs`, `log_revisions`) and authority row-lock waits in candidate diary writes (`save`, `submit`, and legacy combined create/submit).
- Prevents a diary write that was already authenticated by HTTP middleware from succeeding after its session is concurrently logged out or expires while waiting on a PostgreSQL lock.
- Preserves the initial red reproduction (`initial_logout_wait_junit.xml`) and first partial test run (`broader_current_authority_first.xml`).

### Verification & Multi-Agent Review
- **Disposable PostgreSQL Native Tests**:
  - `backend/tests/security/test_diary_postwait_session_probe.py`: **`20 passed in 160.46s`** (`postwait_session_probe.xml`).
- **Independent Static Reviews**:
  - **OpenCode (`opencode/nemotron-3.5-lightning-free`)**: `reviews/2026-11-10/diary_current_auth/opencode_source_review.md` (`0` P1/P2 defects).
  - **GitHub Copilot CLI (`1.0.108`)**: `reviews/2026-11-10/diary_current_auth/copilot_source_review.md` (`0` actionable vulnerabilities).
- **Target Branch**: `integration/r1-agent-collaboration` (`main` remains frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6`).
