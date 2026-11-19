No concrete P1/P2 findings in the reviewed delta.

Nomination, acceptance, and revocation enqueue notices in their service transactions; replay paths
return without creating another intent. The worker checks the claim token and applies the inbox row
and outbox acknowledgement in one transaction. Notice projections resolve the candidate from the
placement and validate the event against assignment, proof, consent, or revocation history; they do
not return arbitrary outbox payloads. Academic notices remain distinct from mentor notices.

The import keeps canonical history unchanged and leaves incompatible supervision links unbound;
academic_teacher_current requires exact supervision, enrollment, and institution matches. The legacy
acceptance path relies on an already-recorded accepted timestamp and current matching authority; it
does not fabricate consent. Imported assignments do not automatically qualify a placement to start.
Compose and the worker default include the academic topic.

This was a read-only static review; I did not execute tests or runtime probes. The unimplemented
098/099/105 queues and full R1/pilot acceptance remain out of scope. The existing startup
readiness-gate deployment caveat is not newly certified; ordinary Teacher PASSWORD policy is
unchanged.

