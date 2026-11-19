Three real HTTP/PostgreSQL probes on pinned08b4129 failed13.64s:

- An accepted PART_TIME_JOB offer creates a placement201, despite the placement
  contract being internship-only. The created row was observed in PostgreSQL.
- A general INTERNSHIP becomes ACTIVE200 after only candidate+host confirmations,
  with zero mentor assignments. Personal current-mentor acceptance is missing.
- An active HR-only member is nominated as mentor201; the service checks membership
  but does not require the scoped MENTOR role. The row remains unaccepted; this is
  not a demonstrated immediate mentor-review privilege grant.

All setup applications/offers/offer response/placement/confirmation/nomination used
actual HTTP and sessions. Published-opportunity/role metadata is trusted setup;
no anonymous/foreign/live exploitation or real legal identity claim. Exact scripts
and raw XML are retained locally and will be committed in the implementation branch.

Implement a reachable host internship admission foundation: internship-only exact
accepted offer/application/candidate/host binding, immutable versioned terms,
current candidate/host acceptance, nomination of a current same-host MENTOR and
that person's exact assignment acceptance. ACTIVE requires all current proofs;
caller flags or confirmation on behalf of another person do not qualify.
Use actual ActorContext/current account/session/scoped assurance after business
locks through commit in new canonical handlers and legacy aliases, with persisted
idempotency/accept/revoke history and original-grant binding to prevent resurrection.

Source sequence is being refined by actual read-only architecture review. Canonical
API048/050/051 and necessary host plan/mentor/revoke helpers are the next target.
Keep ordinary job engagements separate. Preserve legacy/history without faking
internship kinds, mentor consent or verified starts to satisfy existing tests.
Update old PART_TIME placement fixtures to legitimate internship/acceptance flows.

Acceptance: actual full positive admission and role/side/version/expiry/scoped
negative HTTP; no mentor/no consent and PART_TIME denial; revocation/regrant,
current session waits, replay/concurrent accept/revoke/start and audit rollback;
populated upgrade/history/failure rollback; old diary/academic/engagement/candidate
regressions; full matching-head PostgreSQL CI, pinned source review/evidence/handoff.

Source: CAP017/018, canonical DB049/050/051/054, INV08 and API048/050/051.
Dependency: PR64 enrollment final matching-head acceptance. Then continue intended
EDU enrollment supervision/purpose/legal agreement and academic102/103/104 with
personal teacher acceptance, avoiding the existing ACTIVE-before-teacher cycle.
This issue does not claim all offer/capacity/application/cooldown/engagement/diary/
export/frontend/live-provider/legal/DR or overall pilot acceptance.
