# Implementation & Verification Plan: Rating Appeals (API-058 / CAP-028 / DB-067 / AC-025)

## 1. Goal
Implement canonical endpoint `POST /api/v1/ratings/{id}/appeals` for ratings dispute resolution, adhering to:
- Capability `CAP-028` (`RATING_APPEAL`).
- Database table `DB-067` (`flexbridge.rating_appeals`).
- Acceptance criteria `AC-025` (`RAT-05: E’tiroz va search ta’siri`).

## 2. Invariants & Scope
1. **Party to Rating ("Baho tomoni")**: Only affected parties (target user, rater, or target organization representatives) may submit an appeal. Unrelated third parties are rejected (403 Forbidden).
2. **14-Day Appeal Window**: Appeal must be submitted within 14 calendar days of publication. Stale appeals are rejected (422 Unprocessable Entity).
3. **Anti-Duplication**: Prevents duplicate pending appeals for the same rating revision.
4. **Moderation Queue & Independent Review (DB-078)**: Queues appeal in `moderation_cases` (`category="FACTUAL_DISPUTE"`). Prohibits self-review (`reviewer != appellant` and `reviewer != rater`, AC-028).
5. **Aggregate Recomputation**: Marks disputed rating as `UNDER_APPEAL` and automatically recalculates published rating aggregate: if valid count drops below 5 ($n < 5$), score is withheld (`WITHHELD_INSUFFICIENT_SAMPLE`).
6. **Audit Trail**: Every appeal submission and resolution generates an immutable audit event (`RATING_APPEAL_SUBMITTED`, `RATING_APPEAL_RESOLVED`).

## 3. Verification Plan
- Unit and contract tests: `test_rating_appeals_api058.py` (9 tests).
- Adversarial and boundary tests: `test_rating_appeals_adversarial.py` (6 tests).
- Combined ratings regression suite: 29 tests total.
- Database: Disposable PostgreSQL test container (`127.0.0.1:55440`), zero mutations on `pg_live`.
- Target branch: `integration/r1-agent-collaboration`. Main strictly frozen.
