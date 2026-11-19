# Codex verification of AGY-001 (2026-11-10)

Actual CLI checkpoint returned SUCCESS in conversation
3ed58526-4a7c-4e8e-b905-42568c7d3e41. Requested model gemini-4-argon-high;
CLI does not expose a reported model field, so no separate model certificate.
Agent worktree remains clean. The report is design/source opinion, not tests.

Accepted source facts independently checked in local primary sources/runtime:
CAP037/ADMIN, API121 vs122, DB092 columns and four protected default-OFF codes;
RAM/UID prototype and R2 readiness consumer; current platform_authority requires
MFA/current expiring ADMIN but returns no grant identity; immutable provenance
patterns and actual0016/125 baseline. Source API/version standard requires explicit
intent and distinguishes409 conflicting request from412 stale version. The agent
declared older migrations/archive uninspected; no coverage is inferred there.

Do not implement the full proposed AGY-002 yet. Required revisions:

1. Explicitly serialize absent flags (code-scoped advisory lock) and same actor/
   nonce across DIFFERENT flag codes before current authority. Row FOR UPDATE on
   a missing row locks nothing. Include measured actual HTTP backend lock waits.
2. Capture the exact locked current ADMIN grant, not the None return of current
   platform_authority. Store actual session/auth version and DB-proof grant.
3. Keep origins/initial imported snapshots immutable; do not upsert LEGACY_IMPORT
   provenance into PUBLIC and erase capture history. New actual ADMIN events can
   certify current state while initial provenance remains unchanged. Last event/
   state/version may be derived under serialized mutation, no fake bootstrap user.
4. Return the identical stored receipt on replay; do not flip idempotent_replay
   False->True inside the historical receipt. Current auth is required to replay,
   but committed configuration need not disappear when its original author logs out.
5. Choose fail-closed protected enablement until real prerequisites exist. The old
   R1_PAID_ORG_PLANS name must not be an unprotected alias for paid_checkout.
   Restrict rule_schema to a server-owned global schema, no arbitrary client keys,
   and no R2/org override enablement in R1. State is never sufficient for business
   capability/legal/provider authorization; downstream enforcement is separate work.
6. Put new tests in backend/tests/security/ for this repository's active conventions;
   keep archived tests untouched. Bound code ownership and maximum report size.
   A stale version should follow the source412 standard; key conflict409.

Next task AGY-002 is a narrow independent security revision of these design points,
not production implementation. Main/master stay frozen; all PRs target
integration/r1-agent-collaboration. Actual implementation gets a later explicit
owned-file task after Codex checks the revised contract.
