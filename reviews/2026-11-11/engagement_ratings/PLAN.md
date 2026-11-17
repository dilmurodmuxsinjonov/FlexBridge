# Implementation & Verification Plan: Mutual Double-Blind Engagement Ratings & Placement Acceptance

- **Issue**: #108 (`feat(ratings): implement mutual double-blind engagement ratings API-047 and placement acceptance API-048`)
- **Dedicated Branch**: `feature/108-engagement-ratings`
- **Target Integration Branch**: `integration/r1-agent-collaboration`
- **Frozen Main SHA**: `764fb98496fa40857acb07844fd09fcafa99b7d6` (strictly untouched)
- **Database Scope**: Isolated PostgreSQL instance on port `55440`; `pg_live` untouched.

---

## 1. Capabilities & Contracts

| Contract ID | HTTP Verb & Path | Capability | Required Roles | Key Business Invariants |
|---|---|---|---|---|
| **API-047** | `POST /api/v1/engagements/{id}/ratings` | `CAP-027` (Rating Submission) | `CANDIDATE`, `STUDENT`, `HR`, `HOST_COORDINATOR`, `OWNER` | AC-024 (Bilateral Double-Blind hold until dual submission or 14-day window), AC-023 (n >= 5 privacy threshold), Uniform 404 IDOR defense, row-level locking with `with_for_update()`, status must be `COMPLETED` (409 on active/pending). |
| **API-048** | `POST /api/v1/placements/{id}/accept` | `CAP-018` (Placement Acceptance) | `CANDIDATE`, `STUDENT` | Candidate formally accepts terms of academic placement plan; verified identity, plan version match, idempotency fingerprint, returns `contract_id: "API-048"`. |

---

## 2. Architecture & Database Interactions

1. **DB-064 (`rating_submissions`)**:
   - `placement_id = NULL`, `engagement_id = <uuid>`
   - `rater_id = actor.user_id`
   - Candidate rater: `target_user_id = NULL`, `target_org_id = opp.organization_id`
   - Employer rater: `target_user_id = cand.user_id`, `target_org_id = NULL`
   - Initial submission: `status = 'PENDING_BLIND'`, `publish_after = now() + 14 days`
   - Dual submission (peer already submitted): both transition to `status = 'PUBLISHED'`, `publish_after = now()`
2. **DB-065 (`rating_revisions`)**:
   - Immutable snapshot of rubric family, version, and scale bounds at time of submission.
3. **DB-066 (`rating_scores`)**:
   - Discrete scores per rubric criterion with strict range validation (`scale_min..scale_max`).
4. **AppendOnlyAuditStore**:
   - Appends immutable audit entry `ENGAGEMENT_RATING_SUBMITTED` with rater, target, status, and metadata.

---

## 3. Stage 2 (Freelancing) Decoupling & Extension Hooks

- Strictly **NO** freelance business logic (no escrow, no order disputes, no milestones, no wallet transfers) in R1.
- Clear extension points preserved:
  * `job_engagements.terms_snapshot`: JSONB container accommodates future gig terms without relational migrations.
  * `engagement_confirmations.action`: milestone hooks prepared for future stage 2.
  * `rating_submissions.engagement_id`: shared evaluation table decoupled from job contract type.

---

## 4. Test Evidence

- `backend/tests/security/test_engagement_ratings_api047.py`: 8 passed in 36.08s (100% green).
- `backend/tests/security/test_engagement_ratings_adversarial.py`: 10 passed in 48.14s (100% green).
- Full regression suite (`test_user_ratings_api057.py`, `test_rating_appeals_api058.py`, `test_job_engagements_api045_api046.py`): 28 passed in 161.42s (100% green).
- Total distinct tests verified: 46 / 46 PASSED.
