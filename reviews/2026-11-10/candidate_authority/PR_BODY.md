Candidate self-service previously passed user IDs after preflight authentication.
Actual completed logout after a PostgreSQL wait still allowed profile/skills/CV and
availability writes, private profile/schedule reads, and both legacy availability
POST routes. This draft passes real ActorContext through all9 human paths, derives
own scope and checks current account/session/assurance after profile/file material
locks, with no user-ID-only human fallback.

Private reads hold profile FOR SHARE in READ COMMITTED through current authority and
rendering. Writes hold profile (plus CV file for linking), current authority and
atomic audit through commit/response rendering. CV unlink also authorizes. A frozen
outer REPEATABLE READ human boundary fails closed; internal matching get_schedule/
read_snapshot/load_snapshot remains unchanged. Legacy paths preserve own-ID/date/
EXCLUDE/AVAILABLE_EXTRA semantics and gain atomic candidate audit. Actual-session
fixtures replace old actorless service setup. Existing skill verification and
explicit CV storage provenance remain.

Pinned old-source combined9 red probes failed17.20s (actual HTTP/logout/SQL waits;
trusted CV metadata, no anonymous/foreign/live claim). Initial new109 native had
107 passed/2 test exception-class failures318.07s; runtime correctly returned legacy
scope403, no guard relaxed. Corrected2 plus actual formal Teacher-only PASSWORD
control3 passed12.18s. New suite110 is not claimed as a complete native110 pass.
Old affected modules are running; source-pinned review and complete current CI
remain required. Red/harness/stage evidence is retained separately, counts overlap.

PR60 merged73d3565 after final935742d complete785 CI passed525.26s/469.37s. This
package adds no migration/canonical handler/dependency: runtime0012/111, canonical94,
49 explicit/83 placeholders. Generic catalog/matching/job applications and other
domains remain explicit separate scopes; no global security or pilot certificate.
Antigravity handoff and project journals are current. Docker/WSL system installation
remains incomplete, pg_live was stopped at02:14; tests use isolated PostgreSQL.

Closes #61
