One P2 found: backend/alembic/versions/0014_placement_admission.py:12–15 checks only that
pg_get_functiondef contains one CURRENT_DATE, then replaces that token wherever it occurs. If the
reviewed diary predicate changes but still contains one occurrence—for example, from v_local_date >
CURRENT_DATE to v_local_date > CURRENT_DATE + 1—the migration proceeds instead of failing on an
unexpected expression, potentially changing the date boundary silently. Check the exact expected
predicate and replace only that expression; verify the rest of the function definition is unchanged.

I found no other concrete P1/P2 in the bounded source review. The admission paths recheck current
authority after their material locks; replay returns current rows with historical receipts; notice
delivery is transactional, fenced, and derives its recipient from the placement candidate; inbox
projections do not return arbitrary outbox payloads. These are source opinions, not execution
certification.

The test sources include real HTTP intake/nomination cases with trusted bulk-created upstream
metadata, plus worker rollback/fencing, foreign-access, pagination, and wait-then-session-revocation
cases. The 105-item inbox pagination fixture uses direct SQL, and the 105 intake/nomination cases
do not exercise public upstream setup. I did not run or certify these tests or the separately
reported dual-timezone SQL evidence.

Remaining work is as noted: academic pending-placement admission and conversion of 63 legacy
fixtures; API-051/088 completion and dispute flows; and full diary policy/authority, exports,
frontend, provider, legal, DR, and pilot work. API-031 remains transactional in-app basics, not full
channel or preference support.

