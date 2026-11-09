# Codex decisions after actual source-plan review

2026-11-10. Issue65 starts from merged PR64/1b2bbbf; no host admission code accepted
yet. Copilot read-only plan review exited0 at clean source08b4129. It did not run
the supplied probes or certify SHA/model/pilot. Initial three HTTP/PG probes all
failed13.64s; only published/role metadata was trusted setup. Keep those exact
artifacts. The HR nomination remains unaccepted, not immediate diary authority.

## First functional unit

Implement reachable general-host internship intake and personal acceptance, then
the separately scoped academic supervision/teacher unit. An academic internship
cannot become ACTIVE in this first unit while its teacher/school admission is
missing. Source1.3:120 requires PLANNED from accepted internship and candidate,
host and personally accepted current mentor before general ACTIVE.

Canonical scope: API030 own placement list,048 own candidate terms acceptance,
050 current plan view,051 personally assigned MENTOR acceptance,069 host placement
list,087 mentor nomination,088 host ACTIVATE/CANCEL and089 own mentor assignments.
051's TEACHER branch and088 completion decisions remain explicitly unimplemented
until the academic/completion units; registering a handler is not complete contract
acceptance. Do not claim all CAP018 or pilot from this first unit.

Necessary helpers: existing POST /placements intake, pre-activation versioned plan
write and mentor revoke. Legacy placement confirmation/mentor aliases must use the
same actual-actor service. No UID-only fallback or accepting an unspecified latest
terms version; callers provide exact terms/version and retry key. Existing job
engagement confirmation and unfinished application/offer-capacity/cooldown remain
explicit separate scopes; ordinary jobs never acquire new placement/diary rights.

## State/proof and scope

- Derive candidate, host and internship family from the exact accepted offer /
  application / attempt / original revision. Client redundant IDs must agree.
  New placement is PLANNED. Derive academic-required server-side from the original
  opportunity; no client academic/verified/ACTIVE flag. Current verified host
  capability and current OWNER/HOST_COORDINATOR scope are required for host acts.
- Keep terms and tasks immutable by version. Candidate acceptance pins the exact
  current terms. Host ACTIVATE is the explicit host acceptance plus initial
  activation decision in one transaction; it cannot impersonate candidate/mentor.
  Pre-activation new terms require fresh candidate and mentor version consents.
  Active plan amendment/completion are later lifecycle units, not silent edits.
- Nomination requires current same-host MENTOR, not mere membership. Pin original
  grant identity in immutable nomination proof. Acceptance checks personally named
  membership/user/current original grant and exact plan; revoke/regrant cannot
  revive an old accepted assignment. Host may also mentor if independently holding
  that role, but the candidate cannot act as their own mentor/other-party approver.
- Preserve ordinary PASSWORD for MENTOR/HOST_COORDINATOR where the existing global
  sensitive-role policy allows it. OWNER or another sensitive role still needs MFA.
  Use account_authority plus scoped org authority, not a new blanket MFA policy.
- Persist source/idempotency, exact candidate/host/mentor consent and start/revoke
  events with atomic canonical projections/audit. A recorded intent persists after
  later logout; every new human call rechecks current authority. Historical replay
  receipts must not falsely claim new current activation or invent another start.
- Forward0014 preserves all existing canonical history, explicitly classifies
  legacy origin/eligibility and does not fabricate consent. Wrong old job placements
  remain historical without granting diary/academic access or new verified starts.
  New raw ACTIVE/accepted projection changes require proof. Fixtures must use real
  internship/current-session flows, not renamed job kinds or post-upgrade fake
  legacy markers solely to pass assertions.

## Lock and integration decisions

New host operations derive scope, then lock organization -> offer/intake or
placement -> terms -> assignment/material -> current user/session -> current scoped
grant. Pin another user's target role NOWAIT to avoid cross-user cycles. Sorted
resource locks and existing same-host business locks serialize grant changes.
No host-only method may take an institution lock after placement. Later academic
admission must derive institution first and reconcile all existing academic paths
before adding institution/org/placement shared locks. Do not call a new blocking
org lock from the current academic helper while it already holds placement.

Diary writes/read/review must reject ordinary-job placements and unproved new
activation. Accepted-mentor private access also checks the original current role,
without extending institutional or payroll scope. Keep school/teacher admission
explicitly pending rather than satisfying its ACTIVE gate by a client flag.
Private new/legacy path families need no-store/body protection. Responses expose
only owned/named/host-scoped minimal plan/placement data; no unrelated applications,
salary base or private evidence is opened by a role label.

Required evidence: end-to-end general internship intake -> versioned plan -> own
candidate accept -> actual named mentor accept -> host activation, negative class/
scope/side/version/role/current-session cases, original-grant revocation/regrant,
replay/concurrent accept/revoke/start, rollback and populated upgrade preservation /
failure rollback; old diary/academic/engagement/candidate suites, complete latest
CI, pinned peer review, manifest/HISOBOT/journals/handoff. Follow-on academic unit
must bind pending placement/enrollment/supervision before teacher acceptance, then
extend activation gating; exports/diary completion/full pilot remain unproven.
