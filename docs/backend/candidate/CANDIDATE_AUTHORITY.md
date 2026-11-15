# Current-session authority for candidate self-service

Issue61 follows merged PR60. PR62 mergedb94da55 after final7fb411b complete895 CI
passed twice547.44s/582.45s; review finding closed. This is bounded backend acceptance,
not pilot or live-provider/legal identity acceptance. No migration, dependency or
canonical handler is added: migrated runtime0012/111 tables and canonical94 remain.

Nine human API paths receive the actual ActorContext in their services: profile
GET/PATCH, skills PATCH, CV link/unlink, weekly availability replacement, date
exceptions replacement, private schedule GET and the two legacy candidate-ID
availability-add POST paths. A user/candidate ID alone cannot authorize them.
The legacy services derive and lock the actor's own profile and compare the supplied
candidate ID before inserting. Existing route scope checks remain as preflight.

Writes acquire the owning profile lock, then any CV material file lock, then shared
account_authority checks current active account/session/user binding, auth version,
revocation/expiry and current sensitive-role MFA. Current roles come from PostgreSQL;
cached role labels cannot waive assurance. Ordinary PASSWORD, teacher-only and
current sensitive MFA retain existing policy. CV unlink also checks authority, even
though there is no new file to lock. Existing CLEAN/nondeleted/owner and explicit
bucket/VersionId/ETag checks remain for CV linking.

Human service transactions require actual READ COMMITTED. A caller's frozen outer
REPEATABLE READ snapshot is rejected before candidate business reads/writes, so it
cannot silently freeze current-role authorization. Private profile/schedule wrappers
take the owner profile FOR SHARE, check current authority and render their result
inside that transaction. All canonical and legacy schedule writers take the same
profile lock before their changes, so the guarded private read sees one whole
schedule. Replacement responses are rendered before releasing their write transaction.
Internal get_schedule/read_snapshot/load_snapshot behavior remains for matching;
its existing consistent multi-query snapshot and query-count behavior is preserved.
It is not a user-ID-only human authorization compatibility path.

Legacy availability additions now record candidate audit events atomically with
their inserted rows, alongside existing canonical profile/skills/CV/replacement
audits. Failure rolls the business change and audit back together. Active skill
catalog requirements and verification invalidation, exact own file binding,
EXCLUDE/range/date/timezone/adjacent merging and AVAILABLE_EXTRA->AVAILABLE alias
behavior remain. Profile, skill and schedule client flags do not grant formal roles
or independent verification.

If logout/security changes commit while a request waits for profile/file material,
the final guard denies it. If the request holds authority first, logout waits for
commit. Expiry is evaluated at the guarded boundary; locks do not freeze clock time
through commit. Guards remain held through returned private reads and business/
audit writes. No sessionless direct-service fixture is used to bypass the policy.

Evidence distinguishes physical waits from controlled setup. The independent
pre-fix source370d9c3 probes observed actual HTTP logout200 and holder PID SQL waits:
seven writes still200/201 with changed rows, two private reads200 with own candidate
data. Old plain SELECT reads used a table lock; writes used the actual profile row.
New wrappers/operations are tested on profile row waits and CV material file waits,
reverse actual logout serialization, role/security/expiry, current PASSWORD/MFA,
forged sessions/foreign targets, nullable CV unlink, audit rollback, legacy writer/
private schedule serialization and outer-snapshot rejection. Holder PID is tied to
an isolated pending request via pg_blocking_pids; a unique HTTP backend PID is not
claimed. Skill/CV/import metadata are trusted fixtures, not real scanning or legal
verification. Source review, actual execution and green full CI remain separate gates.

Original red probes and their overlapping diagnostic runs, planning reviews,
subsequent native/current-source CI evidence and limitations are stored in
reviews/2026-11-10/candidate_authority. The original plan covered seven paths; Codex's
caller audit added the two legacy paths, and a separate actual follow-up review
covered them. Earlier reviews are not retroactively represented as nine-path review.

This does not close all authority boundaries: generic skills catalog, matching/
job application and other domains require their explicit audit/acceptance scopes.
Remaining R1 APIs/AC, frontend, live IAM/provider/retention/credential rotation,
DR/legal identity and overall pilot readiness remain open. Handler registration
49 explicit/83 placeholders is not a functional/security acceptance percentage.
