# OPS-CODEX-002: independent opportunity rejection appeals

Status: planned; no implementation or acceptance is claimed here.

Sources: specs/v1_3/FlexBridge_toliq_topshiriq.md sections CAP-032/CAP-033, decision/evidence/revision history, AC-031; canonical DB-078 moderation_cases and DB-079 moderation_actions, API-111. The earlier combined appeal helper was not the canonical rating_appeals workflow. Rating appeals, scam hiding and legal purge remain separate requirements.

Deliverable: a real authenticated organization appellant submits an appeal against the latest REJECT decision on its opportunity. Identity comes from the session, not supplied appellant_id. Preserve the original decision and revision; add an explicit helper table linked to a new canonical moderation case and the immutable original action. One appeal per original decision, request reason and actor immutable.

An independent current-MFA moderator claims the case and alone can decide. Reject the original moderator, appellant, revision author and organization participants. Recheck current grants/assignment on decision; stale revision/status returns conflict. Canonical API-111 handles the assigned appeal case action. UPHOLD leaves REJECTED; REOPEN returns the pinned opportunity to DRAFT for ordinary independent review and paid publishing. It must not mark an opportunity paid, approved or published itself. Existing applications, accepted relations and evidence remain intact.

Use PostgreSQL locks in organization -> opportunity -> appeal order, one audit/state/action transaction, idempotent retries and strict DTOs. Add no-store/body bounds to new private paths. Require distinct appellant submission, assignment and review requests; no actor/reviewer spoofing in submission.

Acceptance: changed-user/org/MFA/role-revocation/assignment negative cases, original-moderator and organization-conflict rejection, parallel claim/decision races, request/action immutability, replay/payload conflict, audit rollback, second-process persistence, stale-revision conflict, existing relation/evidence preservation, populated upgrade and full GitHub PostgreSQL CI. Actual browser/provider/DR or full AC-031 certification is not inferred from these checks.
