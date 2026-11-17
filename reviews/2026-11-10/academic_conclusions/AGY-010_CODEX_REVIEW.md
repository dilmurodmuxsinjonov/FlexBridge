# AGY010 disposition / real placement-wide API108 scope

Actual SUCCESS/exit0/requested GeminiArgonHigh, reported field absent,
conversation1793568b-746f-4223-98f7-9f60ed33bb35,426.59s. Static plan only.
Metadata corrections (127->128, no imaginary HOST decision_id/audit API) accepted.
Codex verified academic_teacher_current does not require current_terms_id=tid,
so historical-plan replay is feasible with current material/original teacher and
exact old consent, even after pointer/plan/cancel changes; new writes stay current.

Single basis_review_id cannot stand for a placement-wide final teacher conclusion.
CAP024/PG043.S03 and primary diary/completion prose require a separate placement
conclusion. Renaming a revision review would leave that end state incomplete.
The fixed implementation contract therefore uses the FULL current diary/review
set under a server-derived digest, not one selected reviewed revision.

New technical design: scoped contextGET returns minimal counts/plan/digest; POST
requires exact expected_basis_digest, actual current teacher/terms/nonce. Positive
ACADEMIC_REVIEW_COMPLETE requires a nonempty complete current diary set where all
current revisions are submitted on current terms and own PUBLIC academic reviews
are REVIEWED, no pending/NEEDS_REVISION. Negative ACADEMIC_REVISION_REQUIRED records
unmet academic review work. Neither certifies required hours/workplace/grade/credit
or completes placement. One immutable conclusion per assignment/terms/basis.
Same-top-transaction actual audit is explicitly bound to the new proof. New guards
preserve HOST admission and old canonical rows without invented authority.

Actor/key intent precedes all business/authority locks; current placement lock and
sorted current log/revision/review locks serialize candidates/teachers/phantoms.
Actual current role/MFA checks after waits and before replay; new current-plan/
ACTIVE/basis eligibility only after replay. READ COMMITTED required. SQL commit
rechecks and stable UTC snapshots. basis_current is content consistency only,
not today's authorization or permission from a historical session; logout does
not erase a committed conclusion. Future completion must enforce its own gates.

Issue76 / Codex worktree D:/Codex/FlexBridge-work/academic-conclusions from accepted
integrationd72462e7. AGY014 owns exactly four NEW files (migration/db/service/test)
in existing isolated agent worktree, compile-only first. Codex owns contract tests,
shared storage/router wiring, source review/native evidence and integration.
