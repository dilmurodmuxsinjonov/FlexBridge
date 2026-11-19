# Issue #77: Candidate Diary Post-Wait Session & Current Authority Re-evaluation

## 1. Root Cause & Baseline Red Probe (`initial_logout_wait_junit.xml`)
- **Vulnerability**: When a candidate diary write (`PUT /api/v1/placements/{id}/logs/{date}`, `POST /api/v1/placements/{id}/logs/{date}/submit`, or legacy `POST /api/v1/placements/{id}/logs`) waited on a PostgreSQL row lock (`placements`, `daily_logs`, or `log_revisions` `FOR UPDATE`) and the candidate's session was concurrently logged out (`DELETE /api/v1/me/sessions/{id}` -> `200`) or expired while waiting, the waiting request still succeeded (`200`) because session validity was only checked in HTTP middleware before acquiring database locks.
- **Preserved Failure Artifact**: `reviews/2026-11-10/diary_current_auth/initial_logout_wait_junit.xml` (`1 failed in 15.107s`).

## 2. Scoped Fix (`feature/77-diary-current-authority`)
- **`backend/app/services/internship_logs.py`**:
  - Added `_diary_read_committed(conn)` to require `READ COMMITTED` transaction isolation (`503 DIARY_ISOLATION_UNSAFE` on `REPEATABLE READ` / `SERIALIZABLE`).
  - Added `_diary_actor_id(actor)` and `_current_diary_author(conn, placement, actor)` which locks `candidate_profiles` (`FOR UPDATE`), verifies ownership (`placement['candidate_id']`), calls `account_authority(conn, actor)` (enforcing current user/session/global sensitive-role MFA), and then re-evaluates `flexbridge.placement_actor_current(CAST(:uid AS uuid), CAST(:sid AS uuid), :v)` against the fresh database `clock_timestamp()` **after** all business and authority row-lock waits.
- **`backend/app/api/v1/canonical_routes.py` & `backend/app/api/v1/internship_logs.py`**:
  - Updated all three diary write routes to pass `actor=actor` (`ActorContext`) instead of raw `author_id=actor.user_id`.
- **`backend/tests/security/test_academic_authority.py` & `backend/tests/security/test_contracts.py`**:
  - Updated direct service test callers to pass `actor=ActorContext(...)`.

## 3. Multi-Agent Independent Review & Native PostgreSQL Verification
- **OpenCode (`opencode/nemotron-3.5-lightning-free`)**: Completed static read-only security review (`opencode_source_review.md`), confirming `0` remaining P1/P2 vulnerabilities and verifying the lock order (`business locks -> READ COMMITTED check -> candidate_profile lock -> account_authority -> post-wait placement_actor_current`).
- **GitHub Copilot CLI (`copilot 1.0.108`)**: Completed static read-only security review (`copilot_source_review.md`), reporting `No actionable security vulnerabilities found in the reviewed changes`.
- **Disposable PostgreSQL Native Tests**:
  - `postwait_session_probe.xml` (`tests/security/test_diary_postwait_session_probe.py`): **`20 passed in 160.46s`** (covering parent placement lock waits, daily_log lock waits, log_revision lock waits, session lock expiry waits, direct service actor/session binding, valid candidate writes across `save`/`submit`/`combined`, and stale isolation rejection).
- **Schema**: Unchanged (`0017_feature_flag_administration`, `127` runtime tables on this branch prior to merging with `0018_academic_decisions`).
- **Branch Policy**: `main` remains strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6`. Target branch is `integration/r1-agent-collaboration`.
