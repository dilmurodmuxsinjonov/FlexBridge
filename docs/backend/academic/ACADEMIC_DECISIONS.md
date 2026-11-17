# Placement-wide academic conclusion contract (Issue76)

Implemented in migration `0018_academic_decisions` (`128` runtime tables: `94` canonical
`v1.4` tables plus `34` security/outbox/proof/guard tables). Baseline red contract probe
(`404`/`501`, `2 failed in 21.45s`) is preserved in review history; post-implementation
native contract and security suites pass against disposable PostgreSQL.

CAP024/PG043.S03/API108 records the personally accepted original Teacher's final
academic conclusion for the placement. API107 remains feedback on a revision.
The conclusion binds the entire current diary/review set; selecting one reviewed
revision cannot conceal another pending current log. New explicit decision names
are ACADEMIC_REVIEW_COMPLETE and ACADEMIC_REVISION_REQUIRED, with sideTEACHER.
These names are a technical choice, not an enum mandated by the primary model.

GET `/api/v1/placements/{id}/academic-decision-context?academic_assignment_id=...`
uses actual current teacher/session/exact plan consent/current purpose. Its minimal
private response contains plan IDs/version, the server-derived basis digest,
counts, academic_review_complete, new_conclusion_allowed, current_conclusion and
advisory_only. It exposes no diary summary, attachment/storage URL, legal basis or
internal staff/session/grant proof. Full diary detail stays under API106 scope.

POST `/api/v1/placements/{id}/academic-decisions` takes academic_assignment_id,
terms_id, version, expected_basis_digest, decision, reason and idempotency_key.
The strict body rejects extra official grade/credit/signature/export/actor fields.
Positive requires a nonempty whole current set: each current revision is submitted
on current terms by the actual candidate and has own PUBLIC REVIEWED academic
proof, with no pending or NEEDS_REVISION. Negative can record unmet review work.
It does not certify required hours, workplace approval, institutional credit or
official grading/signature and does not transition placement to COMPLETED.

The context digest is a precondition. New changed basis returns412; a positive on
pending current academic work returns409. One PUBLIC conclusion per assignment/
terms/basis prevents conflicting duplicate new intent. Changed same-key payload
conflicts; exact replay returns the original canonical receipt, without new effects.

Actor/key advisory intent precedes business and authority locks. Current placement
and sorted diary/revision/review locks keep the complete basis consistent, including
app/FK insert waits. READ COMMITTED is required. Current account/session, original
grant/appointment, purpose and exact requested-plan consent are checked after waits
and before replay. Ordinary Teacher PASSWORD remains permitted by the existing
sensitive-role policy; a sensitive role appearing during waits requires MFA.
Only new intent requires ACTIVE/current plan/current digest. Historical receipts
can replay after pointer/plan/cancel changes only under current original relationship
and exact historical-plan consent; they cannot approve the new current diary basis.

The new immutable proof captures exact canonical receipt/current whole basis,
source/consent/current-authority evidence, nonce/fingerprint and actual audit. UTC
snapshots are stable across connection timezones. Database-owned top-transaction
audit stamping permits savepoints and rejects old-transaction audit reuse. Immediate
and deferred guards reject missing/mismatched proof or authority/source changes.
Legacy canonical rows are retained verbatim without invented teacher/session intent;
HOST activation/cancel producers retain their own existing authority flow.

The internal basis_current predicate measures content consistency, not permission
from a historical session. Logout does not erase a committed conclusion. Future
completion/export/read callers must enforce current caller authority and the
remaining CAP025 conditions separately. FullR1/Issue67/pilot remain open.

Main/master frozen764fb984. All new PRs/verified merges target integration only.
