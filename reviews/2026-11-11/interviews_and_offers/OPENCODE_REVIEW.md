# OpenCode Architecture & Security Review: Interviews and Offers (API-042 / API-043)

## Review Date: 2026-11-11
## Reviewer: OpenCode Consensus Evaluator
## Target: `backend/app/services/interviews_and_offers.py`, `backend/app/api/v1/canonical_routes.py`

### Architectural Review:

1. **Transactional Boundaries and Anti-Pattern Avoidance**:
   - Every mutating operation is enclosed in a dedicated `with transaction() as conn:` block.
   - No cross-request state is leaked.
   - The connection lifecycle is properly managed, avoiding orphaned transactions or connection exhaustion under heavy load.

2. **Schema & Model Compliance (`FlexBridge_model_1_4.json`)**:
   - `interviews` (DB-044): `starts_at`, `ends_at`, `mode`, `status`, `version`, `organizer_membership_id`, `application_id`.
   - `interview_responses` (DB-045): `interview_id`, `user_id`, `response`, `responded_at`.
   - `offers` (DB-046): `application_id`, `attempt_id`, `revision_id`, `issuer_membership_id`, `terms_snapshot`, `status`, `expires_at`, `accepted_at`, `idempotency_key`.
   - `job_engagements` (DB-047): Created for non-internship opportunities (`kind != 'INTERNSHIP'`), initialized with `PENDING_START_CONFIRMATION` for downstream `API-046` dual start confirmation.

3. **Freelance Decoupling (User Strategic Rule)**:
   - Zero freelance logic or premature escrow handling is included in R1.
   - Clean extension points preserved for R2.

### Verdict:
- **PASS**: Architecture is fully compliant with FlexBridge v1.4 specification and consensus guidelines.
