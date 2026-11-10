# OpenCode Peer Code Review: Rating Appeals (API-058 / Issue #90)

**Reviewer**: OpenCode Peer Review Agent  
**Date**: 2026-11-10  
**Target Branch**: `integration/r1-agent-collaboration`  
**Verdict**: **APPROVED**

---

### Multi-Axis Assessment

1. **Architecture & Clean Code**:
   - `UserRatingsService` maintains cohesive single responsibility for ratings, revisions, scoring aggregates, and appeals.
   - Leverages established `account_authority`, `table`, `transaction`, and `insert_row` patterns.
   - Clean separation of concern between route declaration, input validation, domain logic, and aggregate recomputation.

2. **Domain Logic & Invariants**:
   - **`AC-025` ($n < 5$ Privacy Gate)**: Proves that when a rating is disputed, its exclusion from active calculation immediately updates the aggregate, withholding score if valid ratings drop below 5.
   - **`AC-028` (Self-Review Prohibition)**: Explicit conflict guard prevents an appellant or rater from acting as their own dispute judge.
   - **Timezone Safety**: Enforces UTC timezone comparison on `publish_after` and `appeal_deadline`.

3. **Performance & Concurrency**:
   - Uses `with_for_update()` during appeal resolution to prevent race conditions on dispute outcomes.
   - Idempotent replay short-circuits redundant database writes.

4. **Integration Policy**:
   - Main branch freeze strictly maintained (`764fb98496fa40857acb07844fd09fcafa99b7d6` untouched).
   - Target branch is `integration/r1-agent-collaboration`.
