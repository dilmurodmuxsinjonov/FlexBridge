# Current-session authority for owner file operations

Issue59/PR60 merged73d3565 after final935742d full785 CI passed525.26s/469.37s.
This backend acceptance follows merged storage-version PR58 and is bounded to
the owner file methods. It is not pilot, public identity, legal or live-provider acceptance.

Upload initiation, upload completion and owner download now receive the actual
ActorContext. A user ID alone cannot authorize these methods. The existing server
middleware and dependency still perform preflight authentication; the service also
rechecks current active account, exact session/user, auth version, revocation and
expiry at its transaction authorization boundary.

The account_authority helper is extracted from institution onboarding unchanged.
It reads current roles from PostgreSQL and preserves the existing global sensitive-
role MFA policy. Cached actor role labels cannot override it. Ordinary non-sensitive
PASSWORD accounts retain file access; current sensitive actors need MFA. Onboarding
imports the shared helper and retains its existing scoped actor checks.

Initiation authorizes inside a transaction before presigning PUT or inserting the
file intent. Completion locks the owned file row, authorizes before HEAD, then checks
state/size/provider version and atomically updates the file and queues its scan.
Download locks the owned file, authorizes, checks CLEAN/nondeleted/exact stored
reference and presigns GET. Authority locks remain held through provider work and
transaction commit. Ownership is still exact; no cross-user file permission is added.

If logout/security changes commit before the guard, the request is denied without
provider signing or business writes. If the request obtains authority locks first,
logout waits for its commit. This is a PostgreSQL serialization guarantee at the
guarded boundary, not a clock freeze through arbitrary provider delay. Expiry is
checked when authorizing after any business wait. Provider failure rolls back rows
and outbox events; already issued external URLs cannot be rolled back. They retain
their short signed lifetime and exact version binding from PR58.

Scanning is a trusted asynchronous system operation on an already recorded upload.
Logging out does not erase that recorded intent or require a fabricated owner
session for the worker. The source/version and claim-token fences, AV/PDF checks,
retry behavior and CLEAN publication remain. A logged-out old token cannot obtain
a fresh owner download even when the stored scan subsequently succeeds.

Native regression evidence separates physical waits from synthetic barriers:
completion is held on a real file row; the pre-fix download's plain SELECT was held
using an actual file-table lock; initiation uses a service-entry barrier after real
HTTP authentication because there is no existing business row. Holder PID waits
use pg_blocking_pids with an isolated pending request; a separately traced HTTP
backend PID is not claimed. Security/role SQL setup is trusted administrative test
data. HEAD/presign doubles in authority tests are not actual S3/AV evidence. The
existing actual MinIO integration and its added logout/worker case run separately.

This package changes three file methods/callers and shares existing account policy.
Candidate/CV profile, skill, availability and other actor-id-only self-service paths
are an explicit separate audit scope. No claim is made that every session authority
boundary is now covered. No migration/new canonical handler is added: runtime0012/
111 tables and canonical94,49 explicit/83 placeholder registrations remain.
Evidence, source review and full current CI are recorded in
reviews/2026-11-10/files_authority. Older green tests never substitute for these
newly reproduced post-preflight denial/race cases.
