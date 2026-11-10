# Implementation & Review Plan: API-057 Candidate & User Rating View

## 1. Objectives & Scope
- **Contract**: `API-057` (`GET /api/v1/me/ratings`) under capability `RATING_SUBMIT` (`CAP-027`, `specs/v1_4/FlexBridge_model_1_4.json`, line 12613, `contracts/r1_api_matrix.csv`, line 58).
- **Issue**: #88
- **Branch**: `feature/88-user-ratings-view`
- **Target Base Branch**: strictly `integration/r1-agent-collaboration` (`f69e2fd2ce414d7c0f1e8e89f6645395be368cf5`).
- **Main Status**: strictly **FROZEN** at `764fb98496fa40857acb07844fd09fcafa99b7d6`.

## 2. Architecture & Invariants
1. **Feature Flag Administration**:
   - Reads global feature flag `ratings` via `FeatureFlagService.is_enabled('ratings')`. In R1, `ratings` is locked to `enabled=False` by database trigger `guard_feature_flag_row()` from `0017_feature_flag_administration.py`. The endpoint reflects this state cleanly without crashing.
2. **Confidentiality & Privacy Threshold (`AC-023` / RAT-03)**:
   - For users with sample size $n < 5$, the aggregate numerical score is withheld (`score: null`, `score_status: "WITHHELD_INSUFFICIENT_SAMPLE"`, with explicit explanation).
   - Unrated users receive `sample_size: 0`, `score: null`, `score_status: "UNRATED"` (distinct from a score of 0.0).
   - Once $n \ge 5$, the computed score is revealed (`score_status: "PUBLISHED"`).
3. **Double-Blind Anti-Retaliation Window (`AC-024` / RAT-04)**:
   - Ratings received remain blinded (`status: "BLINDED_PENDING_WINDOW"`) with rater identity redacted until the 14-day blind window elapses (`publish_after <= now()`).
4. **Author Transparency & Relations (`AC-022` / RAT-02)**:
   - Authors see full details of reviews they submitted.
   - Completed placements/engagements are surfaced as eligible relations.
