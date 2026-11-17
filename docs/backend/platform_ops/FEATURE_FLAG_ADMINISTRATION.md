# Global feature flag state administration

API121 is `PATCH /api/v1/operator/feature-flags/{code}`. A current platform ADMIN
grant, actual MFA session and active account are required. An actor UUID or
client role/MFA header cannot provide authority. Grants expire and cannot be
self-granted. The request is private (`Cache-Control: no-store`).

Send `Idempotency-Key` (8–128 printable ASCII characters) and `If-Match: "0"`
for a first public event. Later changes require the latest event version in
quoted If-Match. Missing/malformed headers return400; stale versions return412;
reusing an actor's key for another payload/code returns409. The strict body
contains only `enabled` (a JSON boolean) and `reason` (trimmed15–2000 characters).
No organization scope or client-defined rule schema is accepted.

The mutable canonical DB092 row is backed by immutable initial origins and
append-only change events. Draft migration0017 adds those two helper tables
(127 runtime tables;94 canonical tables). It preserves existing rows verbatim
as LEGACY_IMPORT snapshots. Legacy true values without a new current-ADMIN
event are ineffective. Migration capture closes immediately, and legacy origins
are never rewritten to PUBLIC. A new PUBLIC origin requires its first proof.

Each event stores exact actor/session/auth version/grant, version chain, before
and after snapshots/digests, immutable minimal receipt and same-transaction audit.
The state, proof and audit roll back together. PostgreSQL validates canonical
state equality, append-only history and current authority at commit. UTC snapshot
rendering avoids session-timezone differences.

Business locks precede authority locks: actor/key advisory, code advisory,
existing flag row, then user/session/exact ADMIN grant. Mutations require READ
COMMITTED and re-evaluate expiry after waits. Replays require current ADMIN
authority and return the identical original receipt without a new event. A valid
configuration survives the original author's logout; old credentials do not.

Only R1_PART_TIME_JOBS, R1_GENERAL_INTERNSHIPS and R1_ACADEMIC_INTERNSHIPS can
be enabled by this state workflow. Missing, unknown, legacy-only, mismatched or
unavailable state reads OFF. Reads query PostgreSQL without a process-local cache.

The protected ratings, academic_official_export, WhatsApp and paid_checkout flags
remain disable-only until their separate business prerequisites are implemented.
R2_FREELANCE_MARKETPLACE remains disable-only under Q011. R1_PAID_ORG_PLANS is
a read-only legacy alias to paid_checkout and cannot enable payments. An ordinary
flag's true state does not authorize a tenant action or replace capability,
agreement, provider or session checks.

Pilot readiness explicitly probes the actual proof-backed flag read, even when
R2 is always disabled. AVAILABLE means that query succeeded; STORAGE_UNAVAILABLE
and DATABASE_UNAVAILABLE are distinct from a disabled flag. The report continues
to return `pilot_ready: false`. No UI, downstream business gate, live provider,
official signature/grade/export, legal, disaster recovery or pilot acceptance is
claimed by this state administration unit.

All development targets integration/r1-agent-collaboration. Main/master remain
frozen at764fb984 until the user explicitly lifts Q015.
