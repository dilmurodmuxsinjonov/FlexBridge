Source-only review: I found no concrete P1/P2 defect in the retained-scope notice path. The current
source separates nomination from acceptance: NOMINATED requires a PUBLIC proof
(academic_notices.py:36–41); ACCEPTED requires a consent row matching the assignment, placement,
original teacher, grant, and appointment (:42–51). The admission path records that consent and
queues its notice in the same transaction (academic_admission.py:214–239), while migration 0015
validates the actor’s current exact-term consent and makes the evidence immutable
(0015_academic_admission.py:236–250, 378). Notice delivery does not require the author’s session to
remain active. The outbox worker’s transaction and claim-token fence also support rollback and retry
after apply failure or a stale claim (workers/outbox.py:34–54).

Coverage gap, not an observed defect: the new legacy tests exercise valid acceptance and rejection
of an imported nomination, but not a forged ACCEPTED envelope with missing or mismatched consent
evidence (test_academic_legacy_notices.py:65–104). The source checks those relationships; a focused
denial/no-inbox test would protect that branch. This is a source opinion only, not execution or
SHA/full-CI certification.

