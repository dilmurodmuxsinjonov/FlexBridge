# Opportunity rejection appeals

This package supports appeals against the latest `REJECT` decision on an organization's
opportunity. It implements that scope of API-111; other moderation actions, scam hiding,
public abuse reports and rating appeals remain separate work. It does not certify all AC-031.

1. An active OWNER, HR or HOST_COORDINATOR with MFA posts `{"reason":"..."}` to
   `/api/v1/moderation/actions/{original_action_id}/appeals`. The session determines the
   appellant. The target must still be REJECTED and the action must be its latest decision.
   A dedicated case and immutable request pin the original action, current revision and
   its content/skills/shifts and the original rejection rationale. Monetary snapshot fields use decimal strings. The reason must contain 15–4000 nonblank characters.
2. An MFA-authenticated MODERATOR reads the minimal queue at
   `GET /api/v1/operator/moderation-appeals?limit=50&after={case_uuid}`. Queue entries expose
   case ID, creation time, status and due target; they do not expose appeal text or evidence.
   Claim with `POST /api/v1/operator/moderation-cases/{case_id}/claim` and an empty JSON object.
   The original moderator, appellant, revision author and anyone with any organization
   membership history are ineligible. This conservative rule includes revoked memberships.
3. The assigned moderator reads the pinned evidence through
   `GET /api/v1/moderation-appeals/{case_id}`. The appellant may read their own request/history.
   Another moderator cannot read it before assignment. Current operator grants, MFA and
   independence are rechecked within the transaction and authority rows are held until commit; revocation or a new organization conflict blocks review.
4. API-111, `POST /api/v1/operator/moderation-cases/{case_id}/actions`, accepts only
   `{"decision":"UPHOLD|REOPEN","reason":"..."}` for these cases. The reason uses the same
   bounds. UPHOLD leaves REJECTED. REOPEN returns DRAFT; ordinary independent moderation
   approval, payment and publishing limits still apply. A changed revision, content,
   decision or opportunity state returns409 without resolving the appeal.

Parallel claims choose one reviewer. Same-actor/same-reason submission retries return the
existing case; a changed request conflicts. Matching final-decision retries return the
historical result, while changed decisions/reasons conflict. Decision, canonical case,
append-only appealed action, opportunity state and audit commit in one transaction.
Original requests, snapshots and moderation actions reject SQL mutation/deletion. SQL also checks the exact pinned evidence/current latest decision at submission and resolution. Snapshot byte limits use PostgreSQL JSONB rendering, including Unicode and escape characters.
Relations, accepted offers and application evidence are preserved.

Migration0007 adds `moderation_appeal_requests` (runtime101, canonical94 unchanged) and an
append-only trigger on existing moderation actions. A forward recovery process is required
instead of destructive downgrade. The 48-hour due field is an operational target inherited
from moderation cases; no holiday/SLA certification or external legal approval is implied.
Private responses use no-store and request bodies are bounded. The removed combined
`/operations/moderation-appeals` helper continues to return410.
