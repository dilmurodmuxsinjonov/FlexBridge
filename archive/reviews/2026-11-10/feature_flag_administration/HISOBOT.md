# Issue72 durable feature flag state administration

Root feature/72-durable-feature-flags starts at accepted integratione5068a07.
Main/master remain frozen764fb984. This package administers durable global state
under actual current ADMIN/MFA authority; it does not wire downstream business gates.
See backend/FEATURE_FLAG_ADMINISTRATION.md and PLAN.md for exact scope/ownership.

Final native49passed1warning214.83s plus disjoint proof-controls6passed23.09s,
55distinct cases. Six actual HTTP PostgreSQL waiter/blocker observations persist
in JUnit properties. Core receipts, current sessions/grants, protected/R2/alias
denial, strict inputs, SQL proof/audit rollback, cross-process/timezone reads,
populated upgrade/rollback, availability failure, savepoints, forged audit stamp,
receipt/digest rejection, real expiry at outer commit and unsafe isolation are covered.
The framework TestClient deprecation warning remains.

Real initial failures are retained: SQLNULL vs JSONnull (2HTTPfail + diagnostic),
false flag availability and child-xmin/root-xid mismatch (2fail), implicit ambient
read poisoning (1fail). Corrections preserve exact guards and actual auth/audit.
Initial broad49 had47pass/2fixture-expectation errors: existing self-grant CHECK
rejects before the service, legacy invalidschema before deferred proof. Stronger
tests exercise exact intended guards; focused2pass then full49pass. No runtime
exception was introduced to satisfy test literals. Temporary diagnostic source
removed after its safe primary-error evidence was retained.

Actual AGY tasks003–006 produced owned drafts/fixes/tests; reports and receipts
distinguish requested from unexposed reported model. Claude quota fallback happened
in004; Gemini's stale ERROR envelope is disclosed, not labelled clean SUCCESS.
Codex independently executed every native result reported here. Source opinions
are separate: Copilot service5file exit0/noP1P2; final migration review attempts
could not start due model-list/account retrieval. OpenCode snapshot opinion
completed; six findings were individually checked/rejected with reasons in
OPENCODE_FINDING_ASSESSMENT.md. AGY007 final read-only review is pending.
Raw CLI logs/secrets/runtime data remain outside publication. Source copy hashes
pin19files; current source/index/commit pins follow in source_manifest.json.

Draft until matching-head full GitHub CI, current feedback and final source
acceptance pass. Merge ONLY into integration/r1-agent-collaboration. FullR1,
Issue67/API108/downstream gates/frontend/providers/legal/DR/pilot remain open.

Registration count correction (LOG-079): actual OpenAPI operation inventory on clean accepted PR71/source726ef299 gives70explicit/62placeholder of132; current source gives71explicit/61placeholder. Only API121 changes registration. Earlier69/63 journal figures were stale. This is registration, not functional coverage; API031 remains local-only and other partial workflows/fullR1/pilot remain unaccepted.
