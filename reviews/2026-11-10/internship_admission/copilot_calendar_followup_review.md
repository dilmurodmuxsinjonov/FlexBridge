No remaining concrete P1/P2 found in this corrective delta. The exact-predicate check rejects the
CURRENT_DATE + 1 and >= CURRENT_DATE drift cases, while the rewrite replaces only the reviewed full
predicate. Comparing the resulting function definition with that constructed rewrite guards against
unintended changes elsewhere in the definition.

The populated-upgrade tests also assert that a later failure rolls back the function change and new
tables, and that rejected predicate drift leaves the prior function and history unchanged. This is a
source-only review: I did not run tests or certify runtime behavior. The broader admission work
remains open; this is not a merge or pilot claim.

