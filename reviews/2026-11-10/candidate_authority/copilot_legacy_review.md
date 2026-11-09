Confirmed: both POST /candidates/{candidate_id}/availability-rules and .../availability-exceptions
check the actor’s candidate ID at the route, but pass only candidate_id to the service. Each service
method locks the supplied profile ID without deriving it from the actor or checking the current
session, then inserts. That leaves a direct-service bypass and a gap after the route’s separate
scope check.

The minimal addition is to pass the real ActorContext into both services. In the write transaction,
derive and lock the actor’s own profile, verify its ID matches the supplied candidate_id, then call
account_authority after the profile lock and before inserting. Translate authorization errors
through the existing API handling. Keep the existing date, interval, and EXCLUDE behavior, including
AVAILABLE_EXTRA mapping to AVAILABLE. Update the direct-service calls in test_candidate.py and
test_contracts.py to use actual fixture sessions—or use clearly labeled raw-DB setup where
appropriate—with no actorless human-service compatibility path.

Lock and response risks: the human schedule-read wrapper should use READ COMMITTED, lock the actor’s
profile FOR SHARE, check account_authority, and call get_schedule before leaving that transaction.
Its nested read_snapshot reuses the current connection rather than starting REPEATABLE READ; that is
acceptable only if every schedule writer takes the same profile lock. The replacement methods
currently call get_schedule after their write transaction commits, leaving an unguarded post-commit
response read. Render the schedule before releasing that transaction. Keep internal
read_snapshot/load_snapshot matching behavior unchanged, and preserve the profile → user/session
lock order; do not establish a stale REPEATABLE READ snapshot before the authority check.

Missing tests: exercise both POST routes with logout completing while the request waits on a profile
lock, asserting rejection and no inserted row; test a direct service call with another candidate’s
ID; and cover current/revoked/expired sessions plus both lock orderings. Retain tests for interval
conflicts, validation, and the AVAILABLE_EXTRA alias. Existing direct calls are useful functional
coverage but do not prove transaction-bound authority.

This is a read-only source review, not a claim of completed implementation or SHA, model, or pilot
certification.
