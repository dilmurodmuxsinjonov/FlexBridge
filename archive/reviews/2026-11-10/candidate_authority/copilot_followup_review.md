Finding closed. The test drives every KINDS entry, including both CV link and unlink variants, with
the reviewed teacher’s headers; it asserts the expected success status for each request and for both
schedule resets. I found no skipped path, masked failure, or concrete regression in the delta.

One precision: the role assertion checks that TEACHER is present and COORDINATOR absent; it does not
assert an exact role set. The test also reads the session’s PASSWORD assurance. The reported
expanded run was not independently verified here; this does not certify a full native rerun,
provider behavior, or pilot readiness.
