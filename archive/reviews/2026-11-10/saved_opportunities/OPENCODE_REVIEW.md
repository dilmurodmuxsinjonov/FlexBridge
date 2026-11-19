# OpenCode Verification Review: Candidate Saved Opportunities (API-004, API-037, API-038)

## Review Metadata
- **Branch**: `feature/98-saved-opportunities`
- **Target**: `integration/r1-agent-collaboration`
- **Contracts**: `API-004` (POST /api/v1/saved-opportunities), `API-037` (GET /api/v1/me/saved-opportunities), `API-038` (DELETE /api/v1/me/saved-opportunities/{id})
- **Reviewer**: OpenCode Quality & Static Analysis Agent

---

## 1. Static Typing & Schema Conformance
- `SaveOpportunityPayload` validates `opportunity_id: UUID`, optional `candidate_id: UUID`, and optional `toggle: bool`.
- `_validate_uuid` shields database queries from malformed string syntax, ensuring 422 Unprocessable Entity instead of raw database 500 exceptions.
- Route signatures match canonical OpenAPI specifications and contract matrix.

---

## 2. Security Test Evidence
- Functional suite: `backend/tests/security/test_saved_opportunities_api004_037_038.py` (9/9 passed).
- Adversarial suite: `backend/tests/security/test_saved_opportunities_adversarial.py` (7/7 passed).
- Total empirical coverage: 16/16 green tests in 72.90s against isolated PostgreSQL test cluster.
- Regressions: 40/40 passed in 173.20s across all active canonical contracts.

---

## Conclusion
**APPROVED**: Ready for Pull Request creation targeting `integration/r1-agent-collaboration`.
