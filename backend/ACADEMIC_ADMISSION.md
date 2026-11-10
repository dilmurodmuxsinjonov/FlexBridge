# Pending academic admission

This draft extends host admission with a reachable school and teacher flow before
ACTIVE. It is not full institutional workflow or pilot acceptance. Accepted main
remains0013/114; draft0015 executes124 tables in disposable PostgreSQL. The94-table
canonical model stays intact; six new0015 helper tables store admission evidence.
No migration was applied to pg_live.

1. The candidate POSTs `/placements/{id}/academic-requests` with their own current
   verified enrollment, current terms/version and retry key. This records the
   student's institution choice, not final acceptance of an unseen school plan.
   Before binding, another explicit request can supersede the choice. Only the
   latest choice is eligible; another school cannot capture the pending placement.
2. A current formal COORDINATOR with current MFA POSTs `/student-supervisions` for
   that institution's verified enrollment, active agreement, explicitly enabled
   purpose and legal basis. Its accepted_at records coordinator responsibility;
   it does not claim student consent or legally verified identity.
3. That supervision's coordinator POSTs `/placements/{id}/academic-assignments`
   naming a current formal TEACHER member in the same institution. This binds the
   latest student's exact enrollment/school and creates a new plan version with
   server-derived agreement/version/purpose/basis. The original opportunity intake
   must require academic admission. Client academic_track/ACTIVE flags cannot bind
   a normal job or bypass admission. The teacher cannot be the candidate or nominator.
4. The named teacher GETs `/me/academic-assignments`, reads the minimal plan and
   personally accepts the exact terms/version at API051 with assignment_kind
   TEACHER and a retry key. PASSWORD is valid for an ordinary teacher; the existing
   current sensitive-role policy still requires MFA when applicable. Neither a
   coordinator nor host can give the teacher's personal consent.
5. Candidate and original current mentor personally accept that same plan. Only
   then can a current authorized host ACTIVATE. Current exact enrollment,
   supervision, agreement/version, original coordinator grant and personally
   accepted original teacher appointment/grant are required in service and SQL.
   New plan versions require new personal consents. Regrant/reappointment cannot
   revive the original assignment. Current teacher diary review uses these proofs.

Nomination aliases use the same service and strict UUID/retry-key DTOs. API103
revokes through current institution coordinator authority. Cleanup still works
when the teacher, placement or parent academic scope is no longer eligible. The
legacy PATCH REVOKED alias uses a stable server-generated cleanup key. Revocation
is permanent; a new nomination and personal acceptance are needed for new access.
Historical receipts acknowledge recorded intent without restarting a cancelled
placement or resurrecting a revoked nomination. New requests always authenticate
the actual current actor. Timestamp projections use consistent UTC strings.

Academic paths derive the institution before locking institution -> organization
-> placement -> plan/academic material -> current account/session -> scoped grant.
Another user's authority uses NOWAIT. Host/plan paths detect a school binding that
appeared across their scope hint and return retry rather than taking a late
institution lock. Audit, plan replacement, canonical projection and immutable
evidence commit or roll back together.

0015 captures a closed set of pre-upgrade supervision/academic histories without
inventing student requests, new teacher consents, sessions or coordinator actions.
An unambiguous current teacher grant is captured for historical compatibility;
ambiguous/missing authority stays NULL and cannot become eligible after regrant.
Existing ACTIVE decisions are preserved. Imported pending placements do not gain
automatic activation from this capture; reviewed re-admission remains follow-on
work. New LEGACY_IMPORT inserts, proof mutation and canonical consent forgery fail.
The populated upgrade tests compare full canonical history and exercise real DDL
collision rollback to0014, including preserved start-function definitions.

Observed stages are retained separately in internship_admission: new HTTP5 passed
23.30s; old authority63 initially56passed7failed, then63passed148.52s; lifecycle
initial8passed1failed42.92s (fixture violated the existing unconditional grant
history unique key), corrected9passed24.59s; populated upgrade3passed35.34s.
Counts overlap. New lifecycle cases and affected host/contract regression are being
validated separately. Read-only Copilot source opinion is not runtime certification.

LOG-070 adds transactional in-app teacher nomination/acceptance/revocation notices,
including active teacher replacement. The worker derives candidate recipient and
minimal TEACHER history from immutable canonical proof, using a separate local
topic and fenced atomic inbox/ack. No external provider delivery is claimed. Initial
active replacement red1failed24.95s -> academic1+mentor6passed35.80s; extended
controls are separately recorded. Another real legacy edge probe2failed29.83s
showed mismatched enrollment and cross-school supervision imports. The corrected
import leaves incompatible supervision NULL and denies teacher eligibility unless
the binding institution/enrollment/supervision match, preserving canonical history.
The earlier affected86passed453.18s stage predates these corrections.

Still required in Issue65: scoped institution/supervision/review queues and notices
for new coordinator viewers when those private views are enabled, more lifecycle/
race/retry/legacy cleanup controls and
complete matching-head CI/review acceptance. API088 completion/dispute, amendments,
full diary candidate authority, reports/exports, frontend, live provider/legal/DR
acceptance and the full R1 objective remain open. No dependency or live rollout
is introduced by this draft.

Current corrective selection34passed199.22s,0failure/error/skip,1framework warning,
frozen runtime/config; corrective read-only Copilot exit0/no concrete delta P1/P2.
These are selected native checks, not complete matching-head CI or pilot acceptance.
Source/index receipt is source_academic_manifest.json in internship_admission.
