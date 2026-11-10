I'll start by reading the existing interfaces I have to match.
I have the interfaces I need. Now I'll write the four owned files, starting with the migration.
# AGY-003 phase 1: draft report

I wrote the four owned files, and they compile. Nothing has been run beyond that. The migration, the service and every test are unexecuted drafts. I did not edit any existing file and made no Git changes.

## Files created
1. [0017_feature_flag_administration.py](file:///D:/Codex/FlexBridge-agents/antigravity/backend/alembic/versions/0017_feature_flag_administration.py)
2. [feature_flag_admin.py](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/db/feature_flag_admin.py) (`register_tables(metadata, types)`)
3. [feature_flag_admin.py](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/services/feature_flag_admin.py) (`FeatureFlagAdministrationService`, singleton `flag_admin_service`)
4. [test_feature_flag_admin_api121.py](file:///D:/Codex/FlexBridge-agents/antigravity/backend/tests/security/test_feature_flag_admin_api121.py)

## Verification
I ran `D:/FlexBridge/.venv/Scripts/python.exe -m py_compile` on the four paths. It exited with code 0.

`git status` could not run. It failed with `unable to access 'C:/Users/dilmu/.gitconfig': Permission denied`, so I have no diff or status to show.

## Implementation decisions
- **Schema:** exactly two new tables.
  - `feature_flag_origins` is immutable. The migration captures every existing row as `LEGACY_IMPORT` using `feature_flag_snapshot(f)`. It invents no actor and no event, and capture closes immediately afterwards.
  - `feature_flag_change_events` is append-only. It holds the proof for each change: the actor, session, `auth_version`, exact grant, `UNIQUE(actor_id, idempotency_key)`, `UNIQUE(flag_id, version)`, the prior-event chain, before/after snapshots with digests, the audit FK and the exact receipt.
  - The helper functions `feature_flag_snapshot` (with `SET TimeZone TO 'UTC'`), `feature_flag_digest`, `feature_flag_state_valid` and `feature_flag_admin_current` back the guards.
- **Guards on `feature_flags`:**
  - Delete is blocked. `id`, `code` and `created_at` cannot change.
  - Only valid server-owned states are accepted. This means the catalog codes, the exact schema `{"schema_version":1,"scope":"GLOBAL"}`, and no `enabled=true` on the protected flags or R2.
  - A deferred trigger checks at commit that each row equals its latest event's `after_snapshot`. A captured legacy row with no events must equal its initial snapshot. Raw SQL therefore cannot create an effective ON.
- **Public origins:** a new `PUBLIC` origin must preserve its exact initial snapshot and have a version-1 event by commit. A legacy origin is never rewritten.
- **Event guard:**
  - It re-checks authority against `clock_timestamp()`: an active user, an MFA session with a matching `auth_version`, and a non-self-granted ADMIN/PLATFORM grant.
  - It checks canonical-state equality, the version chain, the same-transaction audit row (`xmin = txid`) and the exact receipt. A deferred trigger repeats the authority check at commit.
- **Service lock order:**
  1. Actor+key advisory lock.
  2. Code advisory lock.
  3. `feature_flags` row `FOR UPDATE`.
  4. `users`, then `sessions`, then the exact grant, all `FOR SHARE`, with the grant chosen by `ORDER BY expires_at DESC, id`.
  - Both advisory locks are a single `hashtextextended` BIGINT. The service requires `READ COMMITTED` and checks session and grant expiry against `clock_timestamp()` after all waits.
- **Replay and errors:** replay needs the current ADMIN actor and returns the stored receipt untouched, before the policy and version checks.
  - The key-reuse conflict is 409 `IDEMPOTENCY_KEY_REUSED` and a stale version is 412 `STALE_FEATURE_FLAG_VERSION`.
  - The alias is 409 `FEATURE_FLAG_ALIAS_READ_ONLY` and an unknown code is 404.
  - The protected flags return 409 `FEATURE_PREREQUISITES_UNMET` and R2 returns 409 `R2_FEATURE_OUT_OF_R1_SCOPE`.
- **`effective_enabled`:** a single SQL read with no cache. It is true only for the three R1 stage flags with a valid latest event whose state matches the row. Missing, legacy-only, mismatched, protected, R2, alias and unknown codes are all false. A storage failure is logged and also returns false. When the caller passes a `conn`, the read runs in a savepoint.
- **Receipt:** it holds exactly `flag_id`, `event_id`, `audit_event_id`, `code`, `enabled`, `effective_enabled`, `version`, `reason` and `decided_at`. Session, grant and `auth_version` stay in the proof row and the audit metadata only.
- **Audit:** I used the existing `AppendOnlyAuditStore.append_audit_event` and its returned `['id']`. The event ID travels in `metadata`, so the audit row is tied to the event.

## Tests drafted
The test file has 14 test functions, some parametrized (parameter counts are in the list):
- receipt replay after author logout and with a new session
- 7 authority mutations plus 4 actor-identity cases
- protected flag lockout (4 flags) and R2/alias/unknown/schema denials
- raw-SQL bypass attempts
- audit rollback after the audit insert
- timezone independence of the snapshot
- a cross-process read
- missing-row and cross-code lock waits (the missing-row test runs 3 rounds), checked with the diagnostic observer
- grant and session expiry during a real lock wait
- a populated 0016→0017 upgrade, a DDL-collision rollback, and a legacy-row certification case

## Concerns
1. **Pre-authority locks:** the actor/key and code locks are taken before authority is checked, as you specified. Any authenticated caller can therefore hold bounded locks for catalog codes and arbitrary keys. Codex should add a rate limit or a cheap role pre-check in the router.
2. **Session-id comparison:** the service compares `actor.session_id` as a string UUID. It denies the actor if the value is missing or not a UUID.
3. **Audit `xmin` check:** it assumes no savepoint around the audit insert and no subtransaction. If Codex's wiring uses one, it will reject valid writes.
4. **Commit-time errors:** deferred-trigger errors are mapped to `GovernanceError` only when `administer` owns the transaction. Under an outer unit of work they surface as a raw `IntegrityError`.
5. **Second MFA session:** the test inserts a session row directly instead of doing a second real TOTP login. TOTP replay protection may reject a second login within the same window, and I did not verify this.
6. **Lock check:** the cross-code test asserts that blocked requests hold no `users`, `sessions` or grant locks. It will fail if the HTTP stack holds an earlier open transaction.
7. **Router assumptions:** the HTTP tests assume `If-Match: "<n>"` and error bodies shaped like `detail.code`.
8. **Table count:** the upgrade test asserts the table count rises by exactly 2. The 127 total is therefore a measurement the run will produce, not something I claim.
9. **Revision ID:** `0017_feature_flag_administration` is exactly 32 characters, the default `alembic_version` width. If that column was never widened, the migration will not fit.
10. **R1 stage defaults:** the earlier contradiction stays open. The three R1 flags read as OFF until an admin certifies them.

## Wiring Codex needs
- Call `register_tables` from [storage.py](file:///D:/Codex/FlexBridge-agents/antigravity/backend/app/db/storage.py) with `metadata` and `_TYPES`.
- Change the `init_storage()` head from `0016_academic_reviews` to `0017_feature_flag_administration`. Until that changes, `conftest` cannot start any test.
- Mount `PATCH /api/v1/operator/feature-flags/{code}` ahead of the 501 stub.
  - It parses `Idempotency-Key` and `If-Match` and returns 400 on a missing or malformed header.
  - It sends the body `{enabled, reason}` with `extra=forbid`.
  - It calls `flag_admin_service.administer` and rate-limits the caller.
- Replace the RAM flag read in `operations.py` with `effective_enabled`.
- Update the 125-table expectations.

This does not certify full R1, API-108, providers, legal requirements or the pilot. The unit administers flag state only. It adds no paid, rating, official-export or WhatsApp authorization.

I'm stopping here and waiting for the next task.
