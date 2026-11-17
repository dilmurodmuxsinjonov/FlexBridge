# Issue77 Security Source Review - Read-Only (OpenCode `opencode/nemotron-3.5-lightning-free`)

Based on the attached bundle diff, here are the identified P1/P2 issues with evidence:

## P1: Session Expiry Bypass After Lock Waits (Critical — Resolved by Diff)

**Location**: `backend/app/services/internship_logs.py:115-118` and `backend/app/services/internship_logs.py:231-234`

**Evidence**:
- Old code: `author_id=actor.user_id` passed directly without rechecking session validity after database locks
- New code: `_current_diary_author()` re-evaluates `flexbridge.placement_actor_current(CAST(:uid AS uuid),CAST(:sid AS uuid),:v)` **after** acquiring candidate_profile row lock and calling `account_authority(conn,actor)`
- Comment explicitly states: *"A session row lock can itself wait beyond expires_at. Re-evaluate against the DB clock after every authority wait, not a pre-wait bound now()"*

**Consequence**: Without this recheck, a session could expire during lock wait, allowing writes with stale session tokens. The `placement_actor_current` function checks `s.expires_at>clock_timestamp()` among other conditions.

## P2: Transaction Isolation Safety (High — Resolved by Diff)

**Location**: `backend/app/services/internship_logs.py:101-103` and `backend/app/services/internship_logs.py:217-219`

**Evidence**:
- New `_diary_read_committed(conn)` check raises `DIARY_ISOLATION_UNSAFE` if transaction isolation != 'read committed'
- Without this, phantom reads could bypass ownership checks between SELECT FOR UPDATE and actual write

## P3: Actor UUID Validation (Medium — Resolved by Diff)

**Location**: `backend/app/services/internship_logs.py:92-98` and `backend/app/services/internship_logs.py:208-214`

**Evidence**:
- `_diary_actor_id(actor)` now validates both `actor.user_id` and `actor.session_id` as UUIDs
- Raises `AUTH_REQUIRED` (401) if either fails validation
- Previously only `author_id=actor.user_id` was used without session_id validation

## Scope Changes

- API endpoints (`canonical_routes.py:37-40`, `:48-50`, `internship_logs.py:61-62`) now pass `actor=actor` instead of `author_id=actor.user_id`, enabling the new validation chain
- `_current_diary_author()` is called **after** `_owned()` and `_diary_read_committed()`, establishing correct lock order: business locks -> isolation check -> authority re-evaluation -> session expiry check

**No schema changes.** All changes preserve valid current candidate operations.

---

*Note: This is a static source review. No execution or pilot certification performed.*
