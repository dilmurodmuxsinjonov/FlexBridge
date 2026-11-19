P2 — New feedback can be written against a legacy assignment without accepted exact-plan consent.
The 0015 migration backfills legacy assignments as LEGACY_IMPORT and creates no
academic_assignment_consents rows (backend/alembic/versions/0015_academic_admission.py:85–105; the
migration test confirms no consent rows at backend/tests/security/test_academic_migration.py:72–76).
Yet academic_teacher_current treats a legacy assignment as current based on its old accepted_at
matching the imported snapshot, without requiring consent for the revision’s terms
(0015_academic_admission.py:263–278). The review service skips the plan-scope comparison for legacy
bindings and relies on that predicate (backend/app/services/academic_reviews.py:42–46); the 0016
proof guard also explicitly permits a legacy binding
(backend/alembic/versions/0016_academic_reviews.py:59–61).

Exploit sequence: On an already-active legacy academic placement with an unambiguously identified,
still-authorized original teacher and an accepted assignment, that teacher submits a review for a
candidate-authored submitted revision through either API alias. The shared writer records a new
PUBLIC review and proof even though the teacher never accepted that exact plan’s terms. This
conflicts with the plan’s requirement for the actual named teacher’s accepted exact-plan consent
(reviews/2026-11-10/academic_reviews/PLAN.md:8–10). Do not fabricate historical consent; block new
public feedback on legacy scope unless a supported process establishes exact consent.

I found no other proven P1/P2 in the requested source surfaces. In particular, the alias passes
expected_revision_id to the shared writer, and a stale pointer blocks a new intent; the
existing-receipt path follows current authority checks
(backend/app/services/internship_logs.py:61–66; backend/app/services/academic_reviews.py:45–60).
That is source-level evidence, not full CI evidence.

This is a read-only source review. The stated initial4passed34.36s is limited evidence; the expanded
run is still in progress, and no full new-writer CI was provided. Trusted staff/document fixtures
and an administrative future-amendment pointer are not public amendment or legal certification.
API108, durable official grade/sign policy, attachment sharing, candidate diary authority,
completion/frontend/live/legal/DR, and full R1 remain open; no execution, SHA, model, or pilot
certification is established.

