Both P2 findings are addressed; I found no remaining concrete P1/P2 coverage gap in this narrow
review.

In academic_review_observer.py:18–24, each worker sets and resets its request label around the
synchronous TestClient call, and the SQLAlchemy listener is removed in finally. The hook at lines
13–17 uses the DBAPI cursor to set transaction-local application_name; it doesn’t rewrite the
original statement. The wait query at lines 27–37 looks up labeled backends in pg_stat_activity and
requires actual lock waits with blockers. This supports the propagation and cleanup design; it is
source review, not runtime confirmation.

The same-placement sequence in test_academic_reviews.py:87–97 is accurately limited: request A is
first observed waiting at the held intent lock (line 90), then request B is submitted and both
backends must be in actual database lock waits (lines 91–93). It does not assert B is waiting at the
intent lock; because both requests target the same placement, B may be waiting on a scoped row lock
held by A. The cross-placement test provides the stronger intent-lock evidence: distinct
institutions and hosts (line 35), two requests under the same held actor/key lock, and both observed
at advisory intent locks with distinct PIDs (lines 57–63). The legacy/current unauthenticated
control now targets both routes and requires 401 (lines 93–99); the authenticated legacy-session
checks still require the consent guard on both routes (lines 120–136).

I make no claim about the running four-test selection’s result, full CI, SHA/model status, or
pilot/legal certification. The broader R1/API108 and other gates you listed remain open.

