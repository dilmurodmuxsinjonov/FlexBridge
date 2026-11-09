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

Prototype native intake8 and activation12 passed, including both prerequisite orders,
independence/private scope and receipt replay; runs overlap. Initial populated upgrade
and collision/history4 passed; latest membership-history constraints need final rerun.
Resubmission/revocation/file-view helpers, broader races/migration/affected tests,
pinned source review and full CI are still in progress. This draft is not ready to
merge, pilot-ready or a legal identity/document/signature/provider certification.

Closes #55
