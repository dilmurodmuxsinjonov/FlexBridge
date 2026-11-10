# Issue76 API-108 Security Source Review

Based on read-only analysis of the two bundle parts, here are the identified P1/P2 defects with source evidence:

## P1 Issues

### 1. `guard_academic_decision_proof` trigger: NULL basis_snapshot risk
- **File**: `backend/alembic/versions/0018_academic_decisions.py:363-365`
- **Issue**: `academic_decision_basis()` can return NULL if underlying tables lack required data. `NULL IS DISTINCT FROM basis` is always TRUE, so the trigger would unconditionally raise an exception, making it impossible to insert new proofs when basis cannot be computed.
- **Consequence**: Insert of any `academic_decision_proofs` row would fail when basis is NULL, blocking all new conclusions.

### 2. `academic_decision_basis` function: potential negative pending_count
- **File**: `backend/alembic/versions/0018_academic_decisions.py:176`
- **Issue**: `pending_count = log_count - reviewed_count - needs_revision_count` could produce negative values if `reviewed_count + needs_revision_count > log_count` due to data inconsistency.
- **Consequence**: Misleading pending_count in basis snapshots.

## P2 Issues

### 3. `guard_academic_decision_proof` trigger: actor_id != c.user_id check
- **File**: `backend/alembic/versions/0018_academic_decisions.py:398`
- **Issue**: `AND NEW.actor_id<>c.user_id` ensures the teacher/actor is not the candidate user, but the inequality semantics should be verified against intent—could be intentional or a logic bug.
- **Consequence**: Unclear if this is deliberate design or unintended constraint.

### 4. `academic_decision_basis_current` / `guard_academic_decision_proof`: basis_snapshot key access
- **File**: `backend/alembic/versions/0018_academic_decisions.py:313-314, 418-419`
- **Issue**: `CAST(dp.basis_snapshot->>'academic_review_complete' AS boolean)` and similar accesses could fail if the key is missing from the JSONB, though mitigated by OR conditions with `d.decision='ACADEMIC_REVISION_REQUIRED'`.
- **Consequence**: Edge-case risk when basis_snapshot lacks expected keys.

### 5. `context` method: only queries PUBLIC origin proofs
- **File**: `backend/app/services/academic_decisions.py:214-221`
- **Issue**: The existing-conclusion lookup filters `proofs.c.origin == 'PUBLIC'`, entirely excluding LEGACY_IMPORT proofs from consideration.
- **Consequence**: May miss current conclusions if system relies on LEGACY_IMPORT provenance.

### 6. `conclude` method: narrow TOCTOU window between proof check and insert
- **File**: `backend/app/services/academic_decisions.py:308-316`
- **Issue**: Although advisory lock and deferred guards help, there remains a narrow window between the existing-proof check and the insert where a concurrent transaction could interfere.
- **Consequence**: Rare race condition possible despite safeguards.

No test commands were executed during this review.