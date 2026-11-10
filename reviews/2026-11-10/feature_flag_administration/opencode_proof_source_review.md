## P1/P2 Defect Analysis Summary

Found **6 defects** across the migration and service code:

### P1 Severity (2 issues)

**1. Savepoint/ROLLBACK Losing Proof State** (`0017_feature_flag_administration.py:89-100`)
- `feature_flag_admin_current()` is `VOLATILE` with independent `clock_timestamp()` calls for session/grant expiry checks
- If transaction experiences delay between `_admin_authority` evaluation and commit, the function's triple `clock_timestamp()` calls can reject valid changes
- Directly breaks `test_current_admin_change_and_audit_work_inside_a_real_savepoint`

**2. ADMIN Authority Not Current at Commit** (`0017_feature_flag_administration.py:215` / `feature_flag_admin.py:506-510`)
- `_admin_authority` captures single `decided_at = func.clock_timestamp()`
- But `guard_feature_flag_change_event` trigger checks `NEW.decided_at>clock_timestamp()` independently
- Creates consistency gap: valid MFA ADMIN changes rejected at commit due to minor transaction delays

### P2 Severity (4 issues)

**3. Same-Transaction Audit Stamp Trust** (`0017_feature_flag_administration.py:193-200, 247-253`)
- `stamp_feature_flag_audit_event` sets `scope_snapshot->_feature_flag_top_xid` at insert time
- Same-tx check compares against `CAST(pg_current_xact_id() AS text)` at validation time
- Nested savepoints create xid timing mismatch → false rejections or cross-transaction reuse

**4. Version Chain Breakage** (`0017_feature_flag_administration.py:62`)
- `UNIQUE(prior_event_id)` constraint blocks chain reordering/correction
- Once a version chain has a misordered event, the system cannot self-correct without manual DB surgery

**5. Receipt Equality Check Always Fails** (`0017_feature_flag_administration.py:253-261`)
- OR'd conditions: JSONB `-` operator comparison (`condition 1`) OR timestamp cast comparison (`condition 2`)
- If condition 1 returns TRUE (likely due to JSONB representation differences), **ALL** events are rejected
- Makes it impossible to insert any new `feature_flag_change_events`

**6. Legacy Quarantine - Overly Restrictive Origin Guard** (`0017_feature_flag_administration.py:165-167`)
- `guard_feature_flag_origin` trigger blocks ALL `LEGACY_IMPORT` origin inserts after initial capture
- Forces all new enablements through PUBLIC origin, contradicting the documented design that "Legacy values never become certified enablement"
- Makes LEGACY_IMPORT origin path permanently inaccessible after migration 0017

---
**Total**: 2 P1 + 4 P2 defects. All rooted in migration 0017 SQL logic and `feature_flag_admin.py` service interaction across the PostgreSQL trigger/constraint layer.
