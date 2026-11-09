Yes. The delta closes the requested wait-proof gap: both pre-authority test paths now wait until
PostgreSQL reports a backend blocked by the captured target-row lock holder, before changing
authority. The wait-graph check covers the request cases, including the matching-role replays.

One precision limit: wait_for_blocker checks for any backend blocked by that holder, rather than
identifying the HTTP request’s backend specifically. In these isolated tests, the held target row
makes that a reasonable proof; if the requirement is strict request-to-waiter correlation, the
helper would need to check the request backend PID. I did not independently verify the pinned SHA or
test results.

