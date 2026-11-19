One remaining test gap: test_admin_state_changes_are_rechecked_after_target_wait observes
before_cursor_execute and checks that the request future is unfinished, but neither proves
PostgreSQL has started blocking that request on the held row. The role revocation could commit
before the request actually waits, so these two new replay cases do not conclusively establish
revocation during a real wait. Capture the blocker connection’s PID and use the existing
wait_for_blocker(pid) helper before revoking the role.

The fresh-session positive control does cover actual logout, password-and-TOTP login to a different
session, matching order and captured-payment receipts, and unchanged money snapshots. No other
concrete gap found in this test delta.

