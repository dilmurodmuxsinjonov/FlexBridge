Institution appointments currently fall through to501. This draft implements
authenticated options, current-MFA claim intake and private status, with independent
assigned moderator review and named revision-bound consent before role activation.
New identities claim a first COORDINATOR role; existing current coordinators can
request a TEACHER. Client role flags and email domains do not grant authority.

Forward0011 adds immutable request/revision/consent/decision records, normalized
registry uniqueness and structural/history guards, preserving malformed legacy rows
while closing their invalid effective grants. Canonical baseline94 is historical;
runtime111 includes the forward extensions. Evidence snapshots bind file hashes and
object versions. Teacher-only PASSWORD behavior remains; privileged actors use MFA.

Explicit same-case resubmission, revocation and scoped file views preserve history
and require fresh consent/review after a new revision. Revoked membership history
coexists with a new active membership. Original grant replacement, recycled contacts,
changed identity/documents and stale caller sessions cannot activate the old intent.
Busy contact/foreign-user cases return atomic409/retry.

The full new native PostgreSQL package passed52 tests in236.82s, including populated
upgrade/collision rollback, both approval/consent orders, replay, private data,
concurrent registry claims, real session lock waits in both orders and audit rollback.
Prototype691 CI passed twice, but subsequent pinned source review identified private
middleware omissions and a separate DB consent MFA policy gap. Three independent
probes failed on that runtime; the fixes and expanded platform/ORG/institution
sensitive-role regressions are included in the52. Public HTTP consent was already
MFA-protected; direct DB setup is trusted and is not claimed as a public exploit.

Affected old modules, full current source review and complete CI are still running.
Overlapping validation counts are not added as unique coverage. This draft is not
ready to merge, pilot-ready or a legal identity/document/signature/provider certification.

Closes #55
