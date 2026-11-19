The three reported P2 failures are addressed in the current source; I found no additional concrete
P1/P2 in the requested files. The corrective native selection is still in progress, so this is a
source review—not evidence that the fixes pass execution.

 - Expired session during intent-lock wait: backend/tests/security/test_academic_reviews.py:213–228
reproduces the sequence: create a receipt, set the session to expire, hold the matching advisory
lock, start a replay, wait past expiry, then release the lock. The reported failure was a 201 replay
instead of
  401. Current backend/app/services/academic_reviews.py:36–41 waits for the intent lock, then
rechecks material, teacher authority, and account/session authority; receipt lookup follows at lines
60–62. That ordering addresses the stale-session replay. I see no obvious lock-order cycle in this
path: assignment business locks precede the intent lock, and no second placement is acquired
afterward. Runtime deadlock behavior remains unverified.
 - Mismatched SQL receipt: backend/tests/security/test_academic_reviews.py:232–244 constructs a
receipt with altered feedback. The guard now requires NEW.receipt=to_jsonb(review) at
backend/alembic/versions/0016_academic_reviews.py:65–68, while the service derives its receipt from
the canonical review snapshot. This closes the reported discrepancy at the SQL boundary.
 - Legacy assignment without exact consent: backend/app/services/academic_reviews.py:52–60 requires
consent matching assignment, revision terms, actor, grant, and appointment before replay lookup or
write. The SQL guard independently requires the matching consent at
backend/alembic/versions/0016_academic_reviews.py:60–62, including for legacy bindings. The
migration regression at backend/tests/security/test_academic_review_migration.py:72–92 verifies that
the legacy assignment can still be current with a valid session but has no consent, and rejects a
PUBLIC proof. That test exercises the SQL guard; the in-progress native selection is needed to
establish the service-path result against a migrated legacy fixture.

Historical handling remains consistent with the plan: 0016 captures existing review rows as
LEGACY_IMPORT without fabricating consent (0016_academic_reviews.py:36–44); the migration tests
preserve prior values and test rollback on a failed upgrade
(test_academic_review_migration.py:32–64). The review/proof immutability and deferred proof
requirement are present at 0016_academic_reviews.py:74–86, and audit insertion remains in the same
service transaction.

I do not certify the running selection, a full CI run, SHA/model, or legal/provider/pilot readiness.
Full R1 and API108, durable grade/sign policy, evidence sharing, candidate diary, completion,
frontend, providers, legal, and DR work remain open.

