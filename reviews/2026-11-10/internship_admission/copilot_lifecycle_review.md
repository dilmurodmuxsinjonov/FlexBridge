No concrete P1/P2 regression found in the requested source-review scope. Source reasoning indicates
the HTTP placement routes use the admission service for creation, consent, mentor acceptance, plan
publication, activation, and revocation; I found no alternate HTTP placement-projection write path.
The migration also adds database guards for the reviewed admission records. Privileged direct SQL is
a separate boundary, and those guards should not be read as a blanket guarantee against every
possible database write.

Material test gaps: test_admission_current_actor.py covers logout during waits, but I found no
equivalent concurrency coverage for mentor-grant revocation/regrant or organization-role changes
during admission. The tests also exercise only selected direct-SQL guard failures and a small set of
legacy migration rows; retry behavior under contention and duplicate consent submissions with a new
idempotency key lack focused coverage. This is source review only; I did not execute tests or
certify runtime behavior.

