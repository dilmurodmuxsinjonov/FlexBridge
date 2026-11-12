# FlexBridge — bosqichlar va bajarilish holati

Current LOG-109 / Organization Entitlements & Billing Overview Implemented & Merged (Issue #122, PR #123, commit b36f13f, merge commit 85bb0b6, API-070, API-093, CAP-025, CAP-026, CAP-029, DB-080..084) (2026-11-12): Organization entitlements and billing overview lifecycle workflows implemented, verified, tested, and squash-merged into integration/r1-agent-collaboration; Issue #122 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-070 (GET /api/v1/organizations/{id}/entitlements) provides organization tier entitlement checks, active subscription period, real-time active vacancy counting (filtering out closed/archived opportunities), remaining vacancies, candidate application allowances, and feature flags with explicit contract_id API-070 stamp. API-093 (GET /api/v1/organizations/{id}/billing) provides comprehensive billing overview including active plan details, invoice history with payment status and settlement timestamps, recent orders and order statuses, current billing contacts, payment method identifiers, and aggregate billing lifetime spend with explicit contract_id API-093 stamp. Uniform 404 IDOR anti-enumeration defense returns 404 ORGANIZATION_NOT_FOUND to unauthenticated callers, cross-tenant callers, non-member candidates, or invalid UUIDs. Role boundaries strictly enforced: restricted to active OWNER, HR, and platform ADMIN/FINANCE under CAP-025, CAP-026, CAP-029. 15/15 unit, contract, and adversarial tests passed 100% green on isolated PostgreSQL port 55440; 16/16 contract regression tests passed in test_contracts.py; GitHub Actions CI passed (runs 43201371056 [18m0s pass], 43201379692 [23m27s pass], 43201371205 [16s pass], 43201379733 [17s pass]). Copilot CLI 1.0.109 and OpenCode 1.18.29 consensus reviews approved (reviews/2026-11-12/billing_entitlements/). All 5 swarm agents (@whitebox, @blackbox, @watcher, @guardian, and @auditor) unanimously endorsed. Total canonical contract coverage: 120/132 implemented (90.9%). Total project empirical readiness: 96.5% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 120/132 canonical contracts, 220/233 functional endpoints, 124 test files with 1,602 automated tests). Stage 2 freelance isolation strictly maintained with clean decoupled extension points.

Current LOG-108 / Academic Reviews & Teacher Review Queue Implemented & Merged (Issue #120, PR #121, commit 712c5c0, merge commit 6a97432, API-105, API-106, API-107, CAP-022, CAP-024, AC-028, SEC-01, DB-052, DB-060) (2026-11-12): Teacher review queue alias, academic log revision snapshot, and review decision verification package completed, verified, and squash-merged into integration/r1-agent-collaboration; Issue #120 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-105 (GET /api/v1/me/academic-review-queue and alias /api/v1/me/teacher-review-queue) returns submitted daily logs for teacher's active accepted assignments under CAP-024 (ACADEMIC_VIEW) with keyset cursor pagination over (submitted_at ASC, id ASC) and zero cross-teacher leakage. API-106 (GET /api/v1/log-revisions/{revision}/academic) provides academic snapshot of daily log, task entries, and evidence with strict visibility scoping (HOST_AND_ACADEMIC and ACADEMIC_ONLY exposed; employer-confidential HOST_ONLY concealed) and uniform 404 IDOR anti-enumeration defense. API-107 (POST /api/v1/log-revisions/{revision}/academic-reviews) enforces AC-028 / SEC-01 self-review prohibition (returns 403 SELF_REVIEW_FORBIDDEN / REVISION_AUTHOR_FORBIDDEN if candidate attempts to review own log), database trigger fn_guard_log_revisions immutability conformance (submitted revisions remain immutable; decisions persisted exclusively in academic_log_reviews with cryptographic proofs in academic_review_proofs), dual-track review independence (DB-060: academic reviews and workplace mentor reviews are orthogonal and neither overwrites the other), row-level advisory transaction locks (pg_advisory_xact_lock), and append-only audit logging to AppendOnlyAuditStore. IAMHTTPMiddleware updated with Cache-Control: no-store, Pragma: no-cache, Referrer-Policy: no-referrer for teacher review queue. 42/42 academic security, queue, and review tests passed 100% green on isolated PostgreSQL port 55440; GitHub Actions CI passed (runs 43123410305 [19m40s pass], 43123437296 [27m30s pass], 43123410094 [16s pass], 43123437314 [18s pass]). Copilot CLI 1.0.109 and OpenCode 1.18.29 consensus reviews approved (reviews/2026-11-12/academic_reviews/). All 5 swarm agents (@whitebox, @blackbox, @watcher, @guardian, and @auditor) unanimously endorsed. Total canonical contract coverage: 118/132 implemented (89.4%). Total project empirical readiness: 95.8% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 118/132 canonical contracts, 218/233 functional endpoints, 123 test files with 1,587 automated tests). Stage 2 freelance isolation strictly maintained with clean decoupled extension points.

Current LOG-107 / Workplace Reviews & Mentor Review Queue Implemented & Merged (Issue #118, PR #119, commit 80c599b, merge commit 6ef1807, API-090, API-091, API-092, CAP-021, CAP-023, AC-028, SEC-01, AC-019, AC-016, DB-057..059) (2026-11-12): Workplace mentor review queue, daily log revision snapshot, and review decision submission lifecycle workflows implemented, verified, tested, and squash-merged into integration/r1-agent-collaboration; Issue #118 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-090 (GET /api/v1/me/mentor-review-queue) returns pending submitted daily logs for mentor's active, accepted assignments with keyset cursor pagination over (submitted_at ASC, id ASC) and 3-day escalation tracking (due_at = submitted_at + 3 days, is_escalated = True). Zero cross-mentor leakage. Response stamped with contract_id API-090. API-091 (GET /api/v1/log-revisions/{revision}/workplace) provides daily log snapshot, tasks, duration, visible evidence (HOST_AND_ACADEMIC / HOST_ONLY; concealing ACADEMIC_ONLY), and review decision history with uniform 404 IDOR anti-enumeration defense. Response stamped with contract_id API-091. API-092 (POST /api/v1/log-revisions/{revision}/workplace-reviews) enforces AC-028 / SEC-01 self-review prohibition (returns 403 SELF_REVIEW_FORBIDDEN if actor is placement candidate or log author), database trigger fn_guard_log_revisions immutability conformance (submitted revisions are immutable; decisions are persisted exclusively in workplace_log_reviews), atomic row-locking via with_for_update(of=(t_p, t_dl, t_rev)), draft log review rejection (409 SUBMITTED_REVISION_REQUIRED), idempotent repeat handling, and audit logging to AppendOnlyAuditStore. Response stamped with contract_id API-092. 11/11 new unit, contract, and adversarial tests passed 100% green on isolated PostgreSQL port 55440; 31 placement log and evidence regression tests passed (42/42 total green); GitHub Actions CI passed (runs 43117413056, 43117445779, 43117413055, 43117445778). Copilot CLI 1.0.109 and OpenCode 1.18.29 consensus reviews approved (reviews/2026-11-12/workplace_reviews/). All 5 swarm agents (@whitebox, @blackbox, @watcher, @guardian, and @auditor) unanimously endorsed. Total canonical contract coverage: 118/132 implemented (89.4%). Total project empirical readiness: 95.1% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 118/132 canonical contracts, 218/233 functional endpoints, 122 test files with 1,586 automated tests). Stage 2 freelance isolation strictly maintained with clean decoupled extension points.

Current LOG-106 / Application Review, HR State Machine Transitions & Candidate Attempt Snapshot Implemented & Merged (Issue #116, PR #117, commit 5ec07ef, merge commit ce972b6, API-082, API-083, API-084, CAP-008, AC-012, INV-01, DB-041..043) (2026-11-12): Application review and HR state machine transitions lifecycle package implemented, verified, tested, and squash-merged into integration/r1-agent-collaboration; Issue #116 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-082 (GET /api/v1/opportunities/{id}/applications) provides scoped application listings for specific opportunities ("Boshqa e’lon nomzodlari ochilmaydi", zero cross-opportunity leaks) with keyset cursor pagination over (created_at DESC, id DESC), status filtering, and uniform 404 IDOR anti-enumeration defense. Role check strictly enforces active OWNER, HR, and HOST_COORDINATOR (restricted to INTERNSHIP; returns 403 on PART_TIME). Response stamped with contract_id API-082. API-083 (POST /api/v1/applications/{id}/transition) enforces strict state machine transitions (SUBMITTED -> REVIEWING -> SHORTLISTED / INVITED_TO_INTERVIEW / OFFER_PENDING / REJECTED) with atomic row-locking via with_for_update(). Disallowed transitions return 409 INVALID_APPLICATION_TRANSITION; terminal states return 409 APPLICATION_TERMINAL_STATE. Automatic capacity release invariant: if transition is REJECTED and occupied capacity was active, atomically decrements occupied_count and stamps released_at = now(). Appends audit trail to flexbridge.application_events and AppendOnlyAuditStore. Response stamped with contract_id API-083. API-084 (GET /api/v1/applications/{id}/hr) provides candidate attempt snapshot at submission time, schedule match score, and events timeline with uniform 404 IDOR defense. Response stamped with contract_id API-084. 12/12 new unit, security, and adversarial tests passed 100% green on isolated PostgreSQL port 55440; 21 opportunity and candidate regression tests passed (33/33 total green in 121s); GitHub Actions CI passed (runs 43109343083, 43109380018). Copilot CLI 1.0.109 and OpenCode 1.18.29 consensus reviews approved (reviews/2026-11-12/application_review_hr/). All 5 swarm agents (@whitebox, @blackbox, @watcher, @guardian, and @auditor) unanimously endorsed. Total canonical contract coverage: 115/132 implemented (87.1%). Total project empirical readiness: 94.2% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 115/132 canonical contracts, 215/233 functional endpoints, 120 test files with 1,575 automated tests). Stage 2 freelance isolation strictly maintained with clean decoupled extension points.

Current LOG-105 / Opportunity Drafting, Terms & Shift Schedule Configuration Implemented & Merged (Issue #114, PR #115, commit 3f2fa68, merge commit 34a7bc6, API-078, API-079, API-080, CAP-016, AC-008, INV-02, DB-035..038) (2026-11-12): Opportunity drafting and revisions lifecycle package implemented, verified, tested, and squash-merged into integration/r1-agent-collaboration; Issue #114 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-078 (PUT /api/v1/opportunities/{id}/draft) updates core metadata (title, description, region, work_mode, eligibility, contract_type, program_required) and enforces capacity bounds (capacity > 0 and capacity >= occupied_count; lowering below occupied returns 409 CAPACITY_LESS_THAN_OCCUPIED) with explicit contract_id API-078 stamp. API-079 (PUT /api/v1/opportunities/{id}/draft/terms) enforces labor law invariants (PART_TIME requires is_paid == True and salary_min > 0, unpaid returns 422 UNPAID_PART_TIME_FORBIDDEN; INTERNSHIP permits unpaid; salary_max >= salary_min, end_date >= start_date) with explicit contract_id API-079 stamp. API-080 (PUT /api/v1/opportunities/{id}/draft/schedule) configures schedule_policy (STRICT/NEGOTIABLE) and shift_match_mode (ALL/ANY), atomically replaces shifts, and enforces INV-02 shift overlap protection (overlapping intervals within same group and weekday return 409 OVERLAPPING_OPPORTUNITY_SHIFT) with explicit contract_id API-080 stamp. AC-008 Immutability Invariant: only status == 'DRAFT' can be modified; non-draft mutations return 409 OPPORTUNITY_NOT_DRAFT. Uniform 404 IDOR anti-enumeration defense returns 404 OPPORTUNITY_NOT_FOUND to unauthorized or cross-tenant callers. Role boundaries strictly enforced: HOST_COORDINATOR limited to INTERNSHIP (403 on PART_TIME). 11/11 new unit and adversarial tests passed 100% green on isolated PostgreSQL port 55440; 21/21 regressions passed (32/32 total green in 105s); GitHub Actions CI passed (runs 43100054708, 43099992235). Copilot CLI 1.0.109 and OpenCode 1.18.29 consensus reviews approved (reviews/2026-11-12/opportunity_drafting/). All 5 swarm agents (@whitebox, @blackbox, @watcher, @guardian, and @auditor) unanimously endorsed. Total canonical contract coverage: 112/132 implemented (84.8%). Total project empirical readiness: 93.6% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 112/132 canonical contracts, 212/233 functional endpoints, 119 test files with 1,563 automated tests). Stage 2 freelance isolation strictly maintained with clean decoupled extension points.

Current LOG-104 / Public Opportunities Discovery, Onboarding Options, Services & Pricing Catalog, Help & Policies CMS Implemented & Merged (2026-11-12): Public Opportunities Discovery, Onboarding Options, and Knowledge Catalog Package (API-001, API-002, API-011, API-012, API-013, API-014, CAP-001, CAP-002, CAP-039, DB-035..038, DB-018) implemented, verified, tested, and squash-merged into integration/r1-agent-collaboration (PR #113, commit 41c6cb2); Issue #112 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-001 (GET /api/v1/opportunities) provides public search across verified organizations and published opportunities with stable keyset cursor pagination over (published_at DESC, id DESC), real-time vacancies_available calculation, parameterized filters, and uniform 400 INVALID_CURSOR error handling. API-002 (GET /api/v1/onboarding/options) provides public onboarding paths with strict Stage 2 Freelance isolation (status: 'PLANNED', stage: 2, is_active: false). API-011 (GET /api/v1/services/public) and API-012 (GET /api/v1/prices/public) expose service catalogs and tariff pricing aligned with billing. API-013 (GET /api/v1/help/{document}) and API-014 (GET /api/v1/policies/{document}) provide versioned Markdown CMS document serving. 13 new unit, security, and adversarial tests passed 100% green on isolated PostgreSQL port 55440; GitHub Actions CI passed (jobs 130757724895, 130757724688, 130757461819, 130757460314). Copilot CLI 1.0.109 and OpenCode reviews approved (reviews/2026-11-11/public_discovery/). All 5 swarm agents (@whitebox, @blackbox, @watcher, @guardian, and @auditor) unanimously endorsed. Total canonical contract coverage: 109/132 implemented (82.6%). Total project empirical readiness: 93.5% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 109/132 canonical contracts, 209/233 functional endpoints, 117 test files with 1,552 automated tests). Stage 2 freelance isolation strictly maintained with clean decoupled extension points.

Current LOG-103 / Organization HR Dashboard, Public Opportunities, Rating Summary & Placement Canonicalization Implemented & Merged (2026-11-11): Organization HR Dashboard, Public Opportunities, Public Rating Summary, and Placement Plan Canonicalization Package (API-068, API-009, API-010, API-050, API-051, API-030, API-069, API-089, CAP-015, CAP-040, AC-023, DB-035..038, DB-044, DB-047, DB-064..066) implemented, verified, tested, and squash-merged into integration/r1-agent-collaboration (PR #111, commit 222ec5e); Issue #110 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-068 (GET /api/v1/organizations/{org}/dashboard) aggregates single-transaction metric counts across opportunities, applications, job engagements, and upcoming interviews with uniform 404 anti-enumeration IDOR protection, restricted to active OWNER, HR, and HOST_COORDINATOR roles under CAP-015. API-009 (GET /api/v1/organizations/{id}/opportunities) provides public listing of verified organization's published opportunities with keyset cursor pagination over (created_at DESC, id DESC) and vacancies_available computation. API-010 (GET /api/v1/organizations/{id}/rating-summary) provides public organization ratings enforcing AC-023 differential privacy threshold (scores withheld as WITHHELD_INSUFFICIENT_SAMPLE when n < 5; UNRATED when n == 0), CAP-040 feature flag adherence, and deterministic ordering over (window_end DESC, computed_at DESC, created_at DESC). API-050, API-051, API-030, API-069, API-089 canonicalized with explicit contract_id stamps. 23 new unit, contract, and adversarial tests passed 100% green on isolated PostgreSQL port 55440; GitHub Actions CI passed (runs 43061689448, 43061751278, 43061751330). Copilot CLI 1.0.109 (exit 0) and OpenCode (exit 0) reviews approved (reviews/2026-11-11/organization_dashboard/). All 5 swarm agents (@whitebox, @blackbox, @watcher, @guardian, and @auditor) unanimously endorsed. Total canonical contract coverage: 103/132 implemented (78.0%). Total project empirical readiness: 91.2% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 103/132 canonical contracts, 203/233 functional endpoints, 114 test files with 1,539 automated tests). Stage 2 freelance isolation strictly maintained with clean decoupled extension points.

Current LOG-102 / Mutual Double-Blind Ratings & Placement Acceptance Implemented & Merged (2026-11-11): Mutual Double-Blind Engagement Ratings & Placement Terms Acceptance Package (API-047, API-048, CAP-027, CAP-018, AC-024, AC-023, DB-064..066) implemented, verified, tested, and squash-merged into integration/r1-agent-collaboration (PR #109, commit 9da01b4cbd58c8dcadacbcbd81c4632491c20533); Issue #108 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-047 (POST /api/v1/engagements/{id}/ratings) enforces AC-024 Bilateral Double-Blind Evaluation (ratings held in PENDING_BLIND with 14-day hold until mutual submission unblinds both simultaneously to PUBLISHED; anti-retaliation 100%), AC-023 Privacy Threshold (n >= 5 required to unmask scores; withheld otherwise), uniform 404 IDOR protection, atomic with_for_update() row lock, completed status verification (409 on active/disputed), and AppendOnlyAuditStore audit logging. API-048 (POST /api/v1/placements/{id}/accept) canonicalized with contract_id receipt metadata. 18 new unit, contract, and adversarial tests passed 100% green; full regression suite (46 distinct tests) passed against isolated PostgreSQL 17 on port 55440. All 1,470+ backend regression tests passed on GitHub Actions CI (runs 42977477754 and 42977545315). Zero mutations to main, pg_live untouched. Copilot (exit 0) and OpenCode (exit 0) reviews approved (reviews/2026-11-11/engagement_ratings/). All 5 swarm agents (@whitebox, @blackbox, @watcher, @guardian, and @auditor) completed deep audit and endorsed. Total project empirical readiness: 89.5% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 100/132 canonical contracts [75.8%], 200/233 functional endpoints [85.8%], 111 test files with 1,516 automated tests). Clean decoupling from freelance scope preserved for Stage 2.

Current LOG-101 / Dual-Confirmed Job Engagements Implemented & Merged (2026-11-11): Dual-Confirmed Job Engagements Package (API-045, API-046, CAP-012, AC-014, AC-016, DB-047, DB-048) implemented, verified, tested, and squash-merged into integration/r1-agent-collaboration (PR #107, commit c40515d824ca2841b54e3493f6202a8453e7e0a1); Issue #106 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-045 (GET /api/v1/me/engagements/{id}) provides engagement details, confirmations timeline, pending sides, and server-side party detection with uniform 404 IDOR protection. API-046 (POST /api/v1/engagements/{id}/confirmations) enforces AC-014 (status transitions to ACTIVE only after BOTH CANDIDATE and EMPLOYER confirm CONFIRM_START; dispute sets DISPUTED; dual CONFIRM_END sets COMPLETED) under atomic with_for_update() row lock and anti-spoofing party check (403). 21/21 contract, regression, and security tests green on isolated PostgreSQL port 55440. All 1,470 backend regression tests passed on GitHub Actions CI. Zero mutations to main, pg_live untouched. Copilot and OpenCode reviews approved (reviews/2026-11-11/job_engagements/). Total project empirical readiness: 88.2% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 98/132 canonical contracts [74.2%], 199/233 functional endpoints [85.4%], 109 test files with 1,450 automated tests). Pure R1 scope maintained without freelance logic.

Current LOG-100 / Interviews and Offers Acceptance Package Implemented & Verified (2026-11-11): Interviews & Offers Acceptance Package (API-042, API-043, API-085, API-086, CAP-009, CAP-011, AC-012, DB-044..046, DB-047) implemented, tested, and reviewed on dedicated branch feature/104-interviews-and-offers (Issue #104) targeting integration/r1-agent-collaboration. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. 11/11 unit, concurrency, security, and invariant tests passed 100% green on isolated PostgreSQL (port 55440); AC-012 concurrency invariant strictly verified (two parallel accepts on 1 vacancy produce exactly one 200 ACCEPTED and one 409 CAPACITY_EXHAUSTED; occupied_count never exceeds capacity). Zero mutations to main, pg_live untouched. Copilot and OpenCode consensus reviews approved (reviews/2026-11-11/interviews_and_offers/). Total project empirical readiness: 86.4% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 96/132 canonical contracts [72.7%], 197/233 functional endpoints [84.5%], 108 test files with 786 automated tests). Clean decoupling from freelance scope preserved.

Current LOG-099 / PR #103 Squash-Merged & Supervisor Opus Audit (2026-11-11): PR #103 (Candidate Applications, Reapply, Summary, History, Withdraw — API-006, API-029, API-039, API-040, API-041, API-044, CAP-007) successfully squash-merged into integration/r1-agent-collaboration (commit 4d9a5e5fa7571253459c77174dbd2f404fa3e93a) after GitHub Actions CI (runs 42958112103 and 42958088775) passed 100% green; Issue #102 closed. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. Chief Supervisor (@supervisor, Claude Opus 4.6 Thinking) completed independent read-only audit: Architecture 9/10, Race-Conditions 9/10, Security 9/10, Overall 8.6/10. Total project empirical readiness: 84.9% weighted completion (130/130 DB tables, 20 Alembic migrations, 16/16 invariants, 92/132 canonical contracts [69.7%], 193/233 functional endpoints [82.8%], 107 test files with 775 automated tests). Zero mutations to main, pg_live untouched. Proceeding to Interviews & Offers Response package (API-042, API-043, CAP-009, CAP-011).

Current LOG-098 / User Break — All Work Cleanly Frozen (2026-11-11 09:21:30): User commanded short break ("qisqa tanafus qilamiz toliq ishlar maksimal tohtash mumkun bolgan joyida muzlatilsin"). All background tasks stopped, 4-agent swarm placed in standby/quiescence. Safe checkpoint: Issue #102 Candidate Applications & Reapply System (API-006, API-029, API-039, API-040, API-041, API-044, CAP-007) is 100% implemented on branch feature/102-candidate-applications (commit 68efad2); PR #103 opened targeting integration/r1-agent-collaboration; 23/23 tests green (100% pass in 113.26s/137.08s on port 55440); Copilot and OpenCode consensus verified; all 4 swarm agents (Whitebox, Blackbox, Watcher, Guardian) approved & endorsed. Working tree clean. GitHub Actions CI running in background. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. Zero mutations to main, pg_live untouched. Ready for instant resume upon user return.

Current LOG-097 / Candidate Applications & Reapply System Implemented & Verified (2026-11-11): Candidate Applications & Reapply package (API-006, API-029, API-039, API-040, API-041, API-044, CAP-007, DB-041..043) implemented, verified, and tested on branch feature/102-candidate-applications (Issue #102) targeting integration/r1-agent-collaboration. Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. 23/23 unit, contract, and adversarial security tests passed on disposable PostgreSQL 17 (port 55440); GitHub Copilot CLI 1.0.109 and OpenCode reviews approved. Zero mutations to main, pg_live untouched. Total project empirical readiness: 83.1% weighted completion (100% DB schema/20 migrations, 100% invariants/crypto/auth, 69.7% canonical contracts implemented, 80.0% platform capabilities active, 107 test files with 775 automated tests).

Current LOG-096 / API-005 & API-031 Opportunity Details & Notification Inbox (2026-11-11): API-005 (GET /api/v1/opportunities/{id}, DB-035..038, DB-021, DB-013, CAP-001) and API-031 (GET /api/v1/me/notifications, DB-085..088, CAP-031) implemented, tested, and reviewed on branch feature/100-opportunity-details-and-notifications targeting integration/r1-agent-collaboration (PR #101, commit 0b3418c). Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. API-005 supports public/guest view for PUBLISHED and CLOSED opportunities, with strict 404 isolation for DRAFT/PENDING_MODERATION (only visible to owning org staff or platform admin/moderator). Vacancies available strictly evaluates to 0 for CLOSED, PAUSED, or expired opportunities (otherwise max(0, capacity - occupied_count)). API-031 provides inbox listing with outerjoin on outbox_events, keyset cursor pagination, entity scopes, and is_read status computation. 34/34 unit, security, and adversarial tests passed on disposable PostgreSQL (port 55440); 26/26 domain regression tests passed (60/60 total green). GitHub Copilot CLI 1.0.109 and OpenCode reviews approved. Zero mutations to main.

Current LOG-084 / Q016 Master Takeover / Issues 76 & 77 (2026-11-10): after Codex reached its hard usage limit at 2026-11-10T07:17:47Z and the user explicitly instructed Antigravity to continue with Copilot and OpenCode collaboration, coordinator_state.json switched to owner=ANTIGRAVITY, generation=1 (conversation 37bc4c57-80dc-42b9-8186-86d25bbe262a). Main/master remain strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6; all PRs and verified merges target integration/r1-agent-collaboration (currently ca1685cb after PR75 merge). On Issue77 (feature/77-diary-current-authority), test_diary_postwait_session_probe.py UUID/str comparison was fixed and verified 20/20 passed (160.46s) plus 79/79 caller regressions passed (578.76s) on disposable PostgreSQL, with independent static reviews by both Copilot CLI (1.0.108, exit 0) and OpenCode (opencode/nemotron-3.5-lightning-free, exit 0); published as PR78 (head 47d8ff6) targeting integration/r1-agent-collaboration. On Issue76 (feature/76-academic-conclusions, API-108 placement-wide advisory academic conclusions, migration 0018_academic_decisions / 128 runtime tables, 72/132 explicit routes), disposable PostgreSQL verified 6/6 contract tests (77.67s), 9/9 API-108 security tests (112.64s), 44/44 migration/regression tests (271.82s), and 95/95 academic suite tests (676.46s); independent static reviews completed by Antigravity (AGY-015), Copilot CLI (exit 0, 0 P1/P2), and OpenCode (exit 0, 6 static observations evaluated and rejected against SQL/service proofs in HISOBOT.md). Full matching-head CI required before integration merge; Full R1/Issue67/pilot remain open, pg_live untouched.

Current LOG-083 / Issue76: accepted runtime0017/127,canonical94, integrationd72462e7; main/master frozen764fb984 and ONLY integration is a new PR/merge target. Codex owns feature/76-academic-conclusions in D:/Codex/FlexBridge-work/academic-conclusions, Q016 coordinator remainsCODEX. AGY010 metadata/replay corrections verified against actual helpers, but a single reviewed revision cannot represent placement-wide final academic conclusion. Fixed new technical contract uses entire current diary/review basis, minimal private GETcontext/digest and strict POST precondition; positive ACADEMIC_REVIEW_COMPLETE requires nonempty complete current submitted/ownPUBLICREVIEWED set; negative records unmet academic review. Hours/workplace/grade/signature/credit/COMPLETED remain separate. Actor/key advisory before business/authority, actual postwait current teacher/session/purpose/exactplan consent before replay; currentbasis/currentplan/ACTIVE only for new intent. Historical exact receipt after pointer/plan/cancel change only under current original relationship/exact old consent. UTC immutable provenance/sameTOPtxn real audit/commit guards/legacy capture; preserve HOST writes. AGY014 actually dispatched requested GeminiArgonHigh in isolated agent worktree for ONLY4NEW migration/db/service/security-test files, compile-only first; Codex owns shared wiring and independent contract tests. Initial native actualHTTP contract red2failed1warning21.45s: context404, API108 placeholder501; retained in initial_contract_red.xml. No new implementation/native success or128schema claim yet. Independent tests now cover ALL-log pending/stale basis, historical replay not approving new basis, logout without resurrecting old session, and no workplace/COMPLETED effect. ParentPR75 Q016 own Windows checks passed; backend checks still pending, published b722 frozen. FullR1/Issue67/API108/pilot remains open, pg_live untouched.

Current LOG-081 / Q016 / Issue74: PR73 accepted ONLY into integrationd72462e705df5d45a91963679301bb377b3755c5 after exact83548d3 complete1142 CI twice665.73s/905.46s, source19/native55/AGY007 static review and empty current feedback; Issue72 closed. Main/master remain frozen764fb984. Root feature/74-antigravity-master preserved7Q016 WIP files. Agent fast-forwarded accepted integration after preserving exactly19owned source paths in retained stashfdfa4669 and checking normalized hashes;2policy WIP files preserved. User Q016 conditional successor task AGY009 actuallySUCCESS/standby accepted, Codex still owner. Corrected timeout/quota classifier uses real structured CLI outcomes, rejects stderr echo/stale0exitERROR, explicit generation-checked handback added;10protocol outcome checks and real two-process exclusive lock pass without live takeover/state change. AGY011 actual sandbox Git/GH/config/worker/loopback denials led to removing only optional --sandbox; AGY012 ordinary auto read smoke passed all5 commands. No dangerous permission-skip flag or actual master launch; future mutation approval/worker model auth not certified. Automatic authoritative Codex quota detection is unavailable, explicit supplied trigger required. AGY008 API108 design returned but concrete count/imaginarycolumn/rawflag/lock/replay/API-name errors rejected; correction required before implementation. FullR1/Issue67/API108/pilot remain open. See successor protocol/CURRENT_HANDOFF.json; inspect coordinator ownership before mutations.

Current Q016 / LOG-080 (2026-11-10): user explicitly authorizes Antigravity to take over the whole ongoing workflow, including Copilot/OpenCode management, if Codex reaches its real limit. Codex remains current master until explicit takeover; do not infer quota from silence/timeout. ANTIGRAVITY_MASTER_PROTOCOL.md and D:/Codex/FlexBridge-agents/CURRENT_HANDOFF.json preserve exact state, frozen main, task ownership, proof/CI gates and next work. Prepared Start-AntigravityMaster.ps1 uses an exclusive runner lock/coordinator owner; automatic Codex quota detection is unavailable and is not claimed. A host-blocked Codex needs the prepared terminal command to trigger takeover. Current PR73 draft83548d3 targets ONLY integratione506; native55passed and finalAGY007 static noP1P2/source19hashes verified, fullCI42765774283/42765782879 still pending. AGY008 read-only API108 planning is in flight. Main/master remain frozen764fb984; fullR1/pilot remain open. Before mutations inspect coordinator_state.json; Antigravity ownership fences Codex until orderly explicit handback. Q016 policy/handoff changes are WIP separate from published PR73 source.

Registration count correction (LOG-079): actual OpenAPI operation inventory on clean accepted PR71/source726ef299 gives70explicit/62placeholder of132; current source gives71explicit/61placeholder. Only API121 changes registration. Earlier69/63 journal figures were stale. This is registration, not functional coverage; API031 remains local-only and other partial workflows/fullR1/pilot remain unaccepted.

Current LOG-079 / Issue72: main/master FROZEN764fb984; only integration/r1-agent-collaboration is eligible for new PRs/verified merges. Root feature72 and agent branch remain based at accepted integratione5068a07 (PR71 full1090twice; Issue70 closed). Durable API121 state administration draft0017/127,canonical94 is now wired; protected4/R2/paidalias remain fail-closed and downstream business gates are not implemented by this unit. Genuine SQLNULL, false readiness, savepoint audit xmin and implicit ambient-read defects were corrected without weakening guards. Stronger final native49passed1warning214.83s plus disjoint proof-control6passed23.09s (55distinctcases), actual HTTP waiter/blocker properties6 retained. Initial broad47pass2fixtureexpectationfail and all earlier reds remain; those two tests strengthened, focused2passed14.00s. AGY005 actualSUCCESS GeminiArgonHigh and AGY006 actualSUCCESS GeminiFlashHigh, reported-model fields absent; all claimed native execution is Codex's independent run. AGY004 real Sonnet/Opus quota->Gemini edits verified despite stale statusERROR, no cleanSUCCESS claim. Copilot five-file service review exit0/noP1P2 with unchanged pins; two final migration review launches unavailable due account/model-list retrieval (not quota). OpenCode completed source-only3file opinion; six findings individually rejected against source/primaryPG docs/actual tests in OPENCODE_FINDING_ASSESSMENT.md. AGY007 final read-only18file review actually running on requested GeminiArgonHigh; no outcome claimed.19source/doc/test files copied to root with baseline/hash preservation. Publication hygiene passed1026files/0errors before latest evidence updates (not security certification). Integration-target draft/full matching-head CI/current feedback/final source acceptance still pending. FullR1/Issue67/API108/frontend/downstream gates/legal/providers/DR/pilot open, pg_live untouched.

Current LOG-078 / Issue72 (2026-11-10): main/master remain FROZEN764fb984; accepted integratione5068a07 only. Root feature72 and isolated agent branch remain based there. AGY005 SUCCESS/exit0 (requested GeminiArgonHigh, model field absent, conversation29bbe3b4) changed ONLY0017 to DB-owned top-level xid8 audit stamping. Independent compile and corrected native11passed32.43s prove defined savepoint/rollback/old-audit/forged-stamp/read-availability scope. Additional genuine implicit-ambient read error was red1failed6.26s then corrected1passed5.79s. HTTP boundaries5passed21.20s. Broad native49cases had47passed/2fixture-expectation failures215.10s: existing chk_platform_grant_not_self blocks forged self-grant before service; legacy invalid schema blocks before deferred unproved guard. Codex strengthened those exact tests without weakening production; focused2passed14.00s. Actual HTTP PostgreSQL waiter/blocker evidence now persists in JUnit properties. Full corrected broad selection remains pending. Actual Copilot five-file service review exit0/noP1P2 with unchanged pins; two later migration/test review launches failed model-list/account retrieval (not quota), no completed opinion claimed. OpenCode independent three-file read-only snapshot review running after a preserved initial CLI argument-order error. AGY006 actually requested listed GeminiFlashHigh for ONE new proof-control test file; no native tests or completed report claimed yet. Main has not moved; PR71 accepted integration only1090twice and Issue70 closed. New source copy/root/full CI/review/integration acceptance pending; full R1/Issue67/API108/downstream business gates/frontend/legal/providers/DR/pilot open, pg_live untouched.

Current LOG-077 / Issue72 (2026-11-10): MAIN/MASTER remain frozen764fb98496fa40857acb07844fd09fcafa99b7d6. PR71 MERGED ONLY INTO integration/r1-agent-collaboration at e5068a07bc4b94f9238883b80e817fd62cc6e709 after exact726ef299 full1090 CI twice866.78s/879.18s; Issue70 closed. Root feature/72-durable-feature-flags and isolated agent/antigravity-r1 both start at integratione506, existing WIP preserved. AGY003 completed four owned files, independently compiled. Actual draft0017 fresh schema127 observed; canonical94 unchanged. Real initial2 HTTP failures exposed PythonNone/JSONnull; corrected to SQLNULL and actual MFA relogin with required logout audit preserved; corrected positives2passed10.12s. Frozen-head compatibility11passed90.83s. Copilot source review found two P2s, both reproduced2failed8.422s: false flag-storage AVAILABLE and audit xmin rejecting genuine savepoints. Codex actual-query readiness correction has6passed plus2 still-failing savepoint cases26.21s (selection matched module filename; NOT a fully green suite). AGY004 hit real Sonnet/Opus quota, switched to Gemini; Gemini exit0/statusERROR contained a stale quota error despite verified owned-file edits, so no clean CLI SUCCESS is claimed. AGY005 is now actually requested on listed gemini-4-argon-high with fresh task context, ONLY0017 migration ownership for DB-owned top-level xid8 audit stamping. Codex owns wiring/tests/service read probe. Source/runtime/full new-head CI/review/integration acceptance still pending. FullR1/Issue67/API108/business gates/providers/legal/DR/pilot remain open; pg_live untouched. Historical progress below is retained, not current state.

Current LOG-076 / Issue72: Q015 still freezes main/master764fb984; all new PRs/merges target integration/r1-agent-collaboration. PR71 notice/policy draft726ef299 is OPEN against integration, full CI42759350885/42759342959 pending; final native10passed77.82s/hygiene978/0. AGY002 returned SUCCESS (requested claude-opus-5-5-high, reported model unexposed, no quota). Codex rejected pre-business actor-FK intent insertion (implicit user lock), invalid two-argument advisory signature and unexecuted50-repetition claim. Fixed contract: actor/key advisory -> code advisory -> flag row -> exact current ADMIN/MFA/grant; immutable origins+events, strict global schema, protected/R2 lockout and paid alias fail-closed. AGY003 is actually dispatched (requested claude-sonnet-5-5-high) for ONLY four NEW migration/db/service/security-test files in isolated agent worktree. Phase1 is draft/compile only; no native flag tests or shared wiring claimed. Codex owns storage/router/operations/legacy-helper wiring and review. Real quota fallback is bounded through CLI-listed alternatives; timeout does not trigger duplicate work. Latest live receipts/tasks under D:/Codex/FlexBridge-agents. Full R1/Issue67/API108/pilot open.

Current Q015 / LOG-075 cycle: AGY-001 returned SUCCESS in actual conversation3ed58526; requested gemini-4-argon-high, reported-model field absent. Isolated worktree remained clean. Codex independently verified primary ADMIN/CAP037/API121/DB092/runtime facts and returned six concrete design corrections (missing-row/cross-code locks, exact grant, immutable legacy origin, identical receipts, paid alias/default-off/R2 schema, current security tests). AGY-002 focused security revision is now actually requested with listed claude-opus-5-5-high; a bounded controller automatically switches suitable listed models only on an actual quota/limit. No quota has been inferred from the earlier timeout. All new PRs/merges target integration/r1-agent-collaboration; main/master frozen764fb984. Guard/source opinion and manual claims stay limited. Issue70 final10native passed77.82s; its integration-target PR/full exact-head CI still pending. Main release/full R1/API108/pilot not accepted.

Current LOG-075 / Q015: user added actual agy collaboration, task-based model selection and quota fallback, and froze main/master. All new PRs/merges target integration/r1-agent-collaboration, created/pushed from764fb984 (PR69 was merged before the restriction). Root AGENTS.md records the policy; isolated AGY workspace D:/Codex/FlexBridge-agents/antigravity; branch agent/antigravity-r1. Shared repo-local push hook rejects main/master; GitHub API merges additionally require explicit PR-base verification. AGY-001 architecture task requested actual listed gemini-4-argon-high, conversation3ed58526; first CLI print timed out while turn continued, not a quota. Same-conversation checkpoint pending. Do not claim a completed AGY report/model certification yet. Issue70 notice final10passed77.82s, source review/runtime unchanged plus explicit one-field test correction. Parent API107 PR69 accepted764fb984 after exact2928425 complete1084 twice723.27/692.20. Current notice/policy PR must target integration; full R1/Issue67/API108/pilot open, pg_live untouched.

Current LOG-073 publication: API106 PR68 accepted1f717899/exact53b complete1047 twice618.75/873.95. Issue67 remains open. Current API107 writer source7 files + tests/helpers9 pinned from actual corrective and final observed-test reviews (all exit0). Native runtime37passed303.85s plus overlapping latest observed SQL/noauth4passed60.90s; real HTTP PID/blocker chains preserved in JUnit. Three genuine red defects corrected, fixture logout audit kept, all failed stages retained. Draft0016/125, accepted0015/124,canonical94. Registration69 explicit63 placeholders/132 is not functionality. New writer draft/full exact-head CI/current GitHub feedback pending; API108 and all remaining R1/pilot open. Codex owns feature/67-academic-review-write; next concrete work: NEXT.md.

Current LOG-073: API106 PR68 merged1f717899242e97e7c1fce3cddda2df44dd7953b1 after exact53b complete1047 CI twice618.75s/873.95s, five source/test pins and empty current feedback; Issue67 stays OPEN. Accepted0015/124,canonical94. Codex owns feature/67-academic-review-write from that identical accepted tree: API107/new REVIEWED/NEEDS_REVISION, strict alias expected revision/nonce, forward0016 immutable review/session/grant/plan/source evidence. Three actual red cases (expiry during intent wait, mismatched receipt, legacy without exact plan consent) corrected; focused5passed95.10s. Initial broad97passed1fixture-audit-count failure633.64s is not final-current evidence; actual logout audit remains required. Current full writer selection/source follow-up/new-head CI still required. No pilot/full R1 acceptance, no pg_live change. See academic_reviews/PLAN.md and HISOBOT.md.

Current LOG-072: PR66 mergedc429/Issue65 closed after exact5ae complete1038 twice879.34s/845.71s,47 code/test/config blobs and current feedback/source audit. Accepted runtime0015/124,canonical94. Issue67/feature67 current API106 minimum exact submitted history read, final9 native passed70.44s/source opinion exit0; full new draft CI still required.107/108/forward0016/legacy revision+nonce and all remaining R1 open. See backend/ACADEMIC_RECORDS.md and academic_records/HISOBOT; pilot not accepted.

Current LOG-072: Issue67 / feature/67-academic-records from5ae9f22. Codex owns new academic_records service/API/tests/docs. Primary source and acceptance are recorded before implementation in reviews/2026-11-10/academic_records/PLAN.md. Parent PR66 full CI still running; no main merge or pilot claim. Read-only plan reviewer could read repository sources but denied the external D: plan path; its output records that limitation. The plan is now copied into this repository for subsequent exact review.

Current LOG-071: Codex is implementing source098/099/105 scoped institutional views and distinct coordinator notices on feature/65 from df87515. Files/responsibility/acceptance are recorded before source changes in internship_admission/ACADEMIC_QUEUES_PLAN.md. Full parentdf87515 CI42743318591/42743326614 both passed1015; current queue matching-head CI remains pending; PR66 remains draft, full R1/pilot not accepted.

Yangilangan2026-11-10 - Codex. PR64 merged1b2bbbfed70dc9a68b6de52cdd91fb0f9c41351f/Issue63 closed after final08b4129 complete930 CI541.51s/651.09s, source/follow-up reviews. Additional unchanged-source formal Teacher PASSWORD lifecycle1 passed10.14s. Current feature/65-internship-admission builds host admission after3 independently confirmed old-domain gaps. Accepted runtime0013/114, canonical51 explicit81 placeholder, not functional coverage/pilot. pg_live untouched; Docker/WSL admin install incomplete.

Holatlar: `Rejada`, `Jarayonda`, `Tekshiruvda`, `Tuzatish kerak`, `Bajarildi`, `Bloklangan`. Bloklangan bandda sabab va ochish sharti yoziladi. Mas'uli tayinlanmagan ish boshlanmagan hisoblanadi.

## GH-CODEX-001 — Lokal tuzatishlarni GitHub bilan sinxronlash

- Holat: `Bajarildi` (GitHub baseline sinxronlash, pilot qabuli emas); mas'ul: Codex; read-only reviewer Copilot CLI. Q-013 asosida uzluksiz ketma-ket ish davom etadi.
- Doira: current tested baseline, public secret/artifact gate, GitHub Issue -> commit/branch -> draft PR -> CI -> review. Oldingi modified/untracked fayllar bir-biriga bog'liq snapshot sifatida saqlanadi; mavjud ish yo'qotilmaydi.
- Fayllar: tekshirilgan backend/migration/test/infra/review snapshoti, publication gate, 01/03/04 jurnallar. Boshqa paketlar PR/CI dalili olingach alohida branchlarda.
- Qabul: raw credentials/state fayllari public repoga tushmaydi; legacy test arxivi manifesti mos; current runtime test-magic literal yo'q; branch/commit/PR/checklar bilan natija qayta bajariladi. Keyingi: OPS-CODEX-001 retention/appeal persistence, so'ng ORG-003/EDU.
- Natija: Issue35 yopildi; PR36 merged, merge1ac0d99. Copilot topgan OWNER bypassi131c72bda yopildi; final snapshot203 test, ikkala PostgreSQL GitHub CI successful. Review/assessment/manifest: reviews/2026-11-08/github_sync; LOG-029. Keyingi Issue37 jarayonda.

## OPS-CODEX-001 — Durable retention evaluations va yolg'on executionni to'xtatish

- Holat: `Bajarildi` (backend paket); mas'ul Codex, peer reviewer read-only Copilot CLI. Issue37 yopildi, PR38 merge7a1cd33. Final0b2866b uchun ikkala GitHub CI successful, complete224 test; native final subset24 passed. Actual purge/legal approval va pilot qabuli emas.
- Doira: SQLda atomik auditlangan, idempotent dry-run baholash yozuvlari va cross-process read; client sanog'i haqiqiy scanned/deleted counterga aylanmaydi. Nonpersistent combined appeal resolution fail-closed qilinadi; alohida durable appeal workflow OPS-CODEX-002ga.
- Fayllar: operations/retention service/API, 0006 migration/storage, SQL regressiyalar, qo'llanma va reviews/2026-11-08/ops001; 01/02/03. Hech qanday actual purge yoki legal approval da'vosi yo'q.
- Qabul: PostgreSQL persist/restart, two-process read, role/MFA/revocation, idempotent concurrency/payload-conflict, immutable evaluation va audit atomicity; GitHub CI. Keyin OPS-CODEX-002, ORG-003 va EDU.

## OPS-CODEX-002 — Alohida appellant va mustaqil review oqimi

- Holat: `Bajarildi` (qo'llangan backend scope); mas'ul Codex; actual read-only reviewer GitHub Copilot CLI, modeli mustaqil aniqlanmadi. Issue39 yopildi, PR40 merge6b28ac5. Final1616fbc ikkala CI successful; native source c46ff70 bilan bir xil.
- Doira: latest opportunity REJECT uchun session-bound haqiqiy appellant, immutable request/revision/original-rationale snapshot, mustaqil assigned moderator; atomik UPHOLD/REOPEN. REOPEN faqat DRAFTga, oddiy moderation/payment/publish cheklovlari saqlanadi. Rating/scam/public-report workflow to'liq qabuli emas.
- Fayllar: moderation_appeals service/API, 0007 migration/storage, canonical API111 integration, private HTTP boundary, security regressiyalar va backend/MODERATION_APPEALS.md; 01/02/03 va reviews/2026-11-08/ops002.
- Qabul: current rol/MFA/session va revocation interleaving, PostgreSQL authority lock/commit serialization, independent assignment, concurrency/replay/conflict, immutable exact SQL evidence, size/decimal precision, stale decision/content, audit rollback, second-process read va existing relation preservation; populated upgrade va full CI.
- Dalil: post-review selected25 passed; authority-lock2 passed; c46ff70 native250 passed,0 failure/error/skip,1 framework warning,586.00s va complete250 test ikkala GitHub CI successful. HISOBOT.md/source_manifest/full_junit/summary shu review katalogida. Evidence-only commit/check va merge yakuni qolgan. Dastlabki fixture lookup va 401/403 test expectation xatolari alohida dalillarda saqlandi; runtime ularni o'tkazish uchun yumshatilmadi.
- Jurnal tuzatishi: oldingi marker bo'yicha avtomatik qo'shish PowerShell ASCII pipe sabab ishlamagan; vazifa bo'limi hozir tiklandi. REJA.md, GitHub Issue39 va source/evidence tarixi saqlangan.

## REV-004 — Joriy ishchi katalogni umumiy ko'rib chiqish (2026-11-07)

- Holat: `Bajarildi` (umumiy review; mahsulot qabuli emas); mas'ul: Codex.
- Topshiriq: foydalanuvchi “loyihani korib chiq” dedi. Doira: tuzilma, mavjud implementatsiya, regressiya va topilgan mantiqiy kamchiliklarni tekshirish.
- Tegiladigan fayllar: `reviews/2026-11-07/overview/*`, 01 va 03 boshqaruv jurnallari. Mavjud ilova o'zgarishlari saqlanadi.
- Qabul mezoni: joriy API inventari, haqiqiy test natijasi, takrorlanadigan kamchilik dalili va tayyorlik bahosi.
- Natija: `reviews/2026-11-07/overview/HISOBOT.md`; 107 passed, 1 warning, 127.28s. Alohida PostgreSQL probe: amal qilish sanalari e'tiborsiz, STIPEND -> HOURLY, bitta matchingda 6 filtrsiz SELECT. API inventari: 27 explicit / 105 placeholder / 132 canonical. Ilova kodi o'zgartirilmadi; tuzatishlar keyingi paketga.

## FIX-CODEX-002 — REV-004 matching tuzatishlari

- Holat: `Bajarildi` (CAN bilan birga umumiy regressiyadan o'tdi); mas'ul: Codex. Foydalanuvchi “davon ettir” deb davom ettirishni topshirdi.
- Maqsad: amal sanalarini hisobga olish, STIPEND turini saqlash, matchingdagi takroriy filtrsiz o'qishlarni yo'qotish.
- Fayllar: `backend/app/services/availability.py`, `backend/app/services/opportunities.py`, matching regressiyalari, 01/03 jurnallar, `reviews/2026-11-07/can/*`.
- Qabul: o'tgan/kelajak/boundary sanalar, stipend feed, nomzod bo'yicha SQL filtr va e'lon soniga bog'liq bo'lmagan batch query soni; keyin CAN-CODEX-001 alohida bosqichda.
- Dalil: matching/availability bo'yicha 8 passed, 27 deselected, 1 warning, 14.25s. Uch e'lon uchun ham 4 SELECT; barchasi WHERE bilan. Amal muddati inclusive chegaralari va boshqa nomzod filtri tekshirildi.

## REV-001 — Codex mustaqil baholash (2026-11-07)

- Holat: `Bajarildi` (baholash yakunlandi; mahsulot qabul qilinmadi).
- Natija: 13 ta ustuvor kamchilik; 17/17 salbiy probe; hisobot: `reviews/2026-11-07/BAHOLASH.md`.
- Mas'ul: Codex; sessiya/modelning aniq identifikatori mavjud emas.
- Doira: `8bb0ad2` holatidagi S1/S2 natijalarini kod, kanonik v1.4 model, mavjud testlar va lokal salbiy ssenariylar orqali baholash.
- Tegiladigan fayllar: `reviews/2026-11-07/*`, ushbu holat fayli va `01_AI_XOTIRASI_VA_QOIDALAR.md`; ilova kodi o'zgartirilmaydi.
- Qabul mezoni: qayta bajariladigan dalillar, ustuvor kamchiliklar va tayyorlik bahosi bilan hisobot. Tekshirilmagan talablar bajarilgan deb belgilanmaydi.

## TD-001 — Tuzatishlar bo'yicha texnik qo'llanma (2026-11-07)

- Holat: `Bajarildi` (texnik tushuntirish; ilova tuzatishlari boshlangani emas).
- Mas'ul: Codex; foydalanuvchi har bir tuzatish aynan qanday bajarilishini to'liq tushuntirishni so'radi.
- Doira: REV-001 kamchiliklarini mavjud v1.4 SQL/API bilan bog'langan arxitektura, tranzaksiya, xavfsizlik, worker va qabul testlari darajasida tushuntirish.
- Tegiladigan fayllar: `reviews/2026-11-07/TUZATISH_TEXNIK_QOLLANMA.md`, 01 va 03 boshqaruv fayllari.
- Qabul mezoni: har paketda ketma-ket bajarish, fayl mas'uliyati, xato holatlari va o'lchanadigan yakun mezoni; tavsiya bilan amalga oshirilgan ish aniq ajratiladi. Ilova kodi ushbu tushuntirish doirasida o'zgartirilmaydi.
- Natija: `reviews/2026-11-07/TUZATISH_TEXNIK_QOLLANMA.md` — 19 bo'lim, 14 ta taklif etilgan FIX paketi. PostgreSQL, SQLAlchemy, FastAPI, PgBouncer, Psycopg, S3, Redis va pypdf rasmiy manbalari bilan texnik tafsilotlar tekshirildi. Jadvaldagi 13 API method/path v1.4 modeliga mosligi va hujjat tuzilishi avtomatik tekshirildi; `git diff --check` xatosiz.

## REV-002 — Tuzatishlarni mustaqil qayta tekshirish (2026-11-07)

- Holat: `Bajarildi` (qayta tekshiruv yakunlandi; tuzatishlar to'liq qabul qilinmadi).
- Mas'ul: Codex; tekshirilayotgan commit `984fec5` (`aa8fd9b` tuzatishlari).
- Doira: R-01..R-13 va FIX-01..14 bo'yicha haqiqiy bajarilish, original probe cheklovlari va kengaytirilgan salbiy ssenariylar.
- Tegiladigan fayllar: `reviews/2026-11-07/recheck_984fec5/*`, 01 va 03 boshqaruv fayllari; ilova kodi o'zgartirilmaydi.
- Qabul mezoni: yopilgan/qisman/ochiq bandlar, qayta bajariladigan dalillar, mavjud test natijasi va pilotga tayyorlik hukmi. Sinovlar alohida sintetik SQLite bazalarda bajariladi.
- Natija: `reviews/2026-11-07/recheck_984fec5/QAYTA_BAHOLASH.md`; 38 passed, original 0/17, kengaytirilgan 30 holat (8 yaxshilanish, 22 kamchilik ssenariysi). Original R-11/12/13ning asosiy tekshiruvlari tuzatilgan; R-01/02/04/07 ochiq, qolganlari qisman. FIX paketlari va S2 aggregate holatlari `Tuzatish kerak`.
- Aniqlashtirish: original 17 probe acceptance suite emas; precondition bajarilmaganida ham defect_observed false bo'lishi mumkin. 132 marshrut imzosining o'zi biznes implementatsiyasi dalili emas. Bu hukm oldingi LOG-019 topshirish da'volarini qayta tekshirish natijasi bilan chegaralaydi.

## REV-003 — So'nggi tuzatishlarni mustaqil tekshirish (2026-11-07)

- Holat: `Bajarildi` (tekshiruv yakunlandi, mahsulot pilotga qabul qilinmadi).
- Mas'ul: Codex; commit `1460ab8`, tuzatish `b214a06`.
- Doira: REV-002 natijalarini takrorlash, kirish qiymatlarini o'zgartirib umumiy himoyani, sessiya, pul, scope, DB constraint va migratsiya bajarilishini tekshirish.
- Tegiladigan fayllar: `reviews/2026-11-07/recheck_1460ab8/*`, 01/03 jurnallar; ilova kodi o'zgartirilmaydi.
- Qabul mezoni: sinovlarda o'tgan aniq tuzatishlar va qolgan kamchiliklarni qayta bajariladigan dalil bilan ajratish; eski diagnostika fayllari saqlanadi.
- Natija: `reviews/2026-11-07/recheck_1460ab8/HISOBOT.md`, `results.json`, `suite_summary.json`. 39 passed (10.88s); oldingi 30 tekshiruv 0 defect/8 improvement; yangi 22 tekshiruv 7 yaxshilanish/15 kamchilik ssenariysi. Bu sonlar mustaqil bug soni yoki tayyorlik foizi emas.
- Hukm: LOG-021dagi barcha bo'limlar to'liq bartaraf etilgani haqidagi xulosa qabul qilinmadi. Runtime test qiymatlariga maxsus shartlar, imzo/refund/sessiya/scope bypasslari, haqiqiy invariant va migratsiya yo'qligi hisobotda dalillangan. Ilova kodi o'zgartirilmadi.

## FIX-CODEX-001 — REV-003 tuzatishlari

- Holat: `Bajarildi` (REV-003 tuzatish paketi va regressiya; butun S2/pilot qabuli emas); mas'ul: Codex. Foydalanuvchi topilgan xatolarni Codexning o'zi tuzatishini topshirdi.
- Tarmoq: `fix/codex-rev003-remediation`; oldingi review o'zgarishlari saqlanadi.
- Doira: testga maxsus shartlar va auth/payment/scope bypasslarini olib tashlash; haqiqiy DB migratsiyasi/constraint, moliyaviy persistence, fayl parseri/worker, outbox va container packagingni tuzatish.
- Fayllar: backend app/migrations/tests/dependencylar, infra, 01/03 jurnallar va yangi tasdiqlash hisoboti.
- Qabul: umumiy salbiy/ijobiy regressiya, ikki jarayon/parallel amallar, haqiqiy PostgreSQL migratsiyasi va invariantlar. Tashqi provayder/ombor tekshirilmagan bo'lsa ochiq ko'rsatiladi, tayyor deb belgilanmaydi.
- Natija: `reviews/2026-11-07/codex_fix/HISOBOT.md`, `summary.json`, `junit.xml`, `http_smoke.json`. 61 passed / 0 failure / 0 error / 0 skip; 1 framework deprecation warning; 189.91s. Ikkinchi process capture, parallel order/refund/5-slot, scoped grant, outbox real handler/fencing va PDF tekshirildi. S3/gateway test double, ClamAV lokal TCP fixture orqali; jonli servis va Docker ishlashi da'vo qilinmaydi.
- Ishga tushirish: `backend/README.md`, `scripts/Test-Backend.ps1`, PostgreSQL CI workflow. 12 eski prototype test fayli SHA-256 manifest bilan arxivda saqlanib, SQL-backed regressiyalarga almashtirildi; bu eski 39 test qayta o'tdi degani emas.
- Qolgan doira: 132 canonical kontraktdan 21 explicit handler va 111 ta 501 bor; barcha 42 AC, real provider/S3/ClamAV, UI, retention purge, backup/restore va production provisioning qabul qilinmagan. S2 aggregate holatlari `Tuzatish kerak` bo'lib qoladi. Oldingi SQLite ma'lumotlari avtomatik ko'chirilmadi/o'chirilmadi.

## IAM-CODEX-001 — IAMni ketma-ket to'ldirish

- Holat: `Bajarildi` (backend paketi; jonli provider/browser/UI qabuli emas); mas'ul: Codex. Foydalanuvchi bo'limlarni birin-ketin tayyorlashni davom ettirishni topshirdi; birinchi navbat IAM.
- Doira: 5 daqiqalik telefon/email OTP, yetkazish adapteri/outbox, rate-limit/resend/single-use, yangi raqam egasini eski hisobdan ajratish, mustaqil omil bilan recovery, MFA bosqichi va passkey backendini to'ldirish. Qolgan modullar bu paketga kiritilmaydi.
- Fayllar: IAM services/API/adapters/workers, qo'shimcha Alembic migratsiyasi, typed storage, IAM testlar va hujjatlar. Oldingi FIX-CODEX-001 o'zgarishlari saqlanadi.
- Qabul mezoni: to'g'ri/noto'g'ri/eskirgan/takroriy OTP, resend/parallel urinish/rate-limit, recycled-phone isolation, ruxsatsiz recovery, sessiyalarni revoke qilish va haqiqiy kriptografik passkey verification; PostgreSQL regressiyasi. Jonli SMS/email yoki browser passkey sinalmasa alohida ko'rsatiladi.
- Natija: `reviews/2026-11-07/iam/HISOBOT.md`, `summary.json`, `junit.xml`, `upgrade.json`. **107 passed, 1 framework warning, 345.29s**, exit 0, error/failure/skip 0. 46 yangi IAM/HTTP test holati, ikkinchi process proofi, native API + alohida worker + lokal TLS gateway va 0002->0003 upgrade tekshirildi.
- Qo'llanma: `backend/IAM.md`; texnologiya va konfiguratsiya 02-fayl hamda `infra/.env.example`da. Haqiqiy SMS/email yuborilmadi, hardware/browser passkey va Docker runtime sinalmadi. Manual omilsiz recovery OPSda qoladi; avtomatik approval yo'q.
- Inventar: 132 canonical kontraktdan 27 explicit handler, 105 ta 501; qolgan modullar to'liq tayyor deb belgilanmaydi. API-017 institution onboarding EDUga tegishli.

## CAN-CODEX-001 — Nomzod profili va mavjudlik

- Holat: `Bajarildi` (backend paketi; pilot/browser/provider qabuli emas); mas'ul: Codex. FIX-CODEX-002 maqsadli tekshiruvidan keyin olindi.
- Doira: profil/malaka, CVni nomzodga ulash, canonical availability/exception APIlari, yo'l buferi va tegishli salbiy/ijobiy testlar. Talabalikni rasmiy tasdiqlash EDU bilan bog'lanadi.
- Fayllar: candidate API/service, availability/schedule/opportunities, canonical matching handleri, main/middleware, SQL-backed testlar, backend qo'llanma, 01/03 jurnallar va `reviews/2026-11-07/can/*`.
- Qabul: actor bo'yicha profil/CV/skill isolation, self-declared/verified ajratish, CLEAN private CV, atomik jadval almashtirish/union/exception, 28 kun/commute/yarim tun, MATCH/CONFLICT/UNKNOWN, bounded/scoped querylar va to'liq PostgreSQL regressiyasi. EDU/verifikatsiya workflow, HR CV sharing va frontend alohida qoladi.
- Natija: `reviews/2026-11-07/can/HISOBOT.md`; umumiy 150 passed / 1 warning / 459.33s; so'nggi generic-preview metadata tuzatishidan keyin CAN 44 passed / 1 warning / 123.53s. Failure/error/skip 0. Natijalar ustma-ust, qo'shilmaydi. To'liq suite oxirgi metadata o'zgarishidan keyin qayta takrorlanmadi; tegishli barcha CAN testlari qayta o'tdi.
- Inventar: 132 canonical / 33 explicit / 99 ta501 / missing0. Yangi dependency/DDL yo'q, schema 0003 va 98 jadval saqlandi. Test bazalari tozalandi, dedicated server to'xtatildi. Qo'llanma `backend/CANDIDATE.md`.
- Chegara: R1 jadval zonasi Asia/Tashkent; CV-specific retention/linked-file-aware purge, skill review submission, HR CV sharing, frontend va real integratsiya/restore staging keyingi bo'limlarda.

## ORG-CODEX-001 — Tashkilot onboarding va tekshiruv

- Holat: `Bajarildi` (backend paketi; butun ORG/pilot qabuli emas); mas'ul: Codex. Foydalanuvchi “davon etamiz” deb davom ettirishni topshirdi.
- Doira: organization onboarding, STIR dedupe, capability holati va dastlabki boshqaruvchining mustaqil tekshiruv/approval oqimi; o'zini vakolatli deb ro'yxatdan o'tkazish yo'q. Tegishli canonical APIlar va qabul mezonlari ish boshlanishida asl manbalardan aniqlanadi.
- Fayllar: yangi organization API/service, 0004 migration va storage metadata, publish capability guard, tegishli governance lock/revocation, PostgreSQL testlar/fixturelar, qo'llanma, 01/02/03 va `reviews/2026-11-07/org/*`.
- Qabul: normalize qilingan STIR uchun parallel dedupe, pending membership vakolat bermasligi, mustaqil assigned MODERATOR/MFA va revisionli evidence, JOB_EMPLOYER/INTERNSHIP_HOST alohida approval, material editning case orqali o'tishi, begona dalil himoyasi, oxirgi OWNERni parallel revoke himoyasi va to'liq regressiya. Taklif/invitationlar hamda ownership transfer keyingi kichik paketda.
- Natija: `reviews/2026-11-07/org/HISOBOT.md`; 179 passed / 1 warning / 562.85s / exit0, failure/error/skip0. Native API 10/10; populated 0003->0004 upgrade va normalized collision rollback tekshirildi. 42 explicit / 90 ta501 / 132 canonical. Head0004/runtime99. 2026-11-08 hashlar/natija qayta tasdiqlandi, test bazalari yo'q, server to'xtatildi.

## ORG-CODEX-002 — Kontaktga bog'langan 24h invitationlar

- Holat: `Bajarildi` (organization invitation backend paketi; butun ORG/pilot qabuli emas); mas'ul: Codex. Foydalanuvchi 2026-11-08 “DAVOM ETTIR” dedi.
- Doira: API-024/025/074, explicit HR/HOST_COORDINATOR/MENTOR/BILLING role, hashed 24h token, verified-contact va recycled-contact pin, idempotent accept, revoke/supersede, inviter/current scope/MFA va URL tokenlarini access logdan yashirish.
- Fayllar: invitation API/service, 0005 migration/storage, org revoke bilan integratsiya, private middleware/auth boundary, PostgreSQL testlar, qo'llanma va `reviews/2026-11-08/org_invitations/*`; 01/02/03 jurnallar.
- Qabul: to'g'ri/begona/expired/revoked/superseded token, parallel accept, aniq rol/owner bypass taqiqi, inviter revoke, contact recycling, stale link reactivation taqiqi va regressiya. Avvalgi keng ORG-002 rejasi kichik paketga bo'lindi: ownership qo'shish/transfer/recovery ORG-CODEX-003ga qoladi.
- Natija: `reviews/2026-11-08/org_invitations/HISOBOT.md`, 198 passed / 1 warning / 217.28s / exit0, failure/error/skip0; native6/6 va access-log token redaction, populated0004->0005 legacy-history upgrade. 45 explicit / 87 ta501 / missing0; runtime99/head0005. Qo'llanma backend/INVITATIONS.md. SMS/email real yuborilmadi; institution invitation alohida qoladi.

## ORG-CODEX-003 — Mustaqil ownership boshqaruvi

- Holat: `Jarayonda`; kichik paketlarga ajratildi: ORG-CODEX-003A qo'shimcha OWNER backend paketi merged;003B existing-OWNER vorisga departure Jarayonda;003C inaccessible-owner recovery Rejada.
- Doira: qo'shimcha OWNER, owner transfer/recovery uchun tashkilot topshirig'i va yangi vakilning mustaqil tekshiruv/roziligi, append-only ownership history va parallel last-owner himoyasi. Asl talab va qabul mezonlari ish boshlanishida aniqlanadi; keyin EDU.

## ORG-CODEX-003A — Existing staff uchun mustaqil qo'shimcha OWNER

- Holat: `Bajarildi` (chegaralangan backend paketi); mas'ul Codex; Issue41 yopildi, PR42 merge9c20547. Actual Copilot CLI read-only review0953ebd va final f118e23 follow-up. bc6e1d6 full295-test CI o'tganidan keyin2 yangi lifecycle testi stale requester/target grantni topdi. Grant-ID binding tuzatildi: final f118e23 native120 passed,0 failure/error/skip,282.714s; complete297-test CI42503498638 successful. Evidence-only final fcf4bed uchun ikkala CI42524063221/42524065800 successful. Transfer/recovery doiraga kirmaydi.
- Doira: current-MFA OWNER so'rovi, shu tashkilotdagi active staff membership targeti, named-target MFA/current verified-contact roziligi, revision-bound dalil va assigned independent MODERATOR approval. Bir tranzaksiyada OWNER grant + append-only ownership event + case + audit. Generic staff/invitation yo'li OWNER bermaydi.
- Fayllar: yangi ownership service/API/migration/tests/guide, organization operator dispatch, shared authority helper, invitation service/test regrant history, 01/02/03 va reviews/2026-11-08/org003. Oldingi revoked grantlar jim reactivation bilan qayta yozilmaydi; faol-grant uniqueness migratsiyasi qo'llandi. Copilot topgan invitation reactivation shu paketda tuzatiladi. SQL guardlar relational integrity; bearer/MFA va contact HMAC API authority chegarasida tekshiriladi, direct DB writers trusted.
- Qabul: REJA.md. Copilot CLI actual read-only planning reviewi bajarildi; bu implementatsiya yoki acceptance dalili emas. Transfer/recovery003Bga, so'ng EDU.

## ORG-CODEX-003B — Mavjud OWNER vorisga vakolatdan chiqish

- Holat: `Bajarildi` (chegaralangan backend paketi); mas'ul Codex; Issue43 yopildi, PR44 mergee2dd6a1. Source284b297 final native160 passed,0 failure/error/skip,1 warning,566.41s; ikkala full337-test CI42525017488/42525078474 successful. Evidence-only910d6cf uchun final CI42525960850/42525965774 ham337 passed (231.43s/209.11s). Actual pinned Copilot code review exit0, confirmed HTTP defect topilmadi; coverage chegaralari assessmentda. Doira va qabul: reviews/2026-11-09/org003b/REJA.md. Planning review tashqi plan faylini access denied sabab to'liq o'qimagan; source/prompt scope aniq yozilgan.
- Current-MFA OWNER faqat o'z OWNER grantidan chiqishni so'raydi; shu tashkilotdagi boshqa mavjud OWNER MFA/contact bilan rozilik beradi; assigned independent MODERATOR current-MFA bilan tasdiqlaydi. Grant qo'shilmaydi; requesterning membership va boshqa rollari saqlanadi. Barcha tomonning original grantlari, revision/security/contact/evidence yangiligi tekshiriladi.
- Fayllar: alohida service/API,0009 migration/storage, explicit operator dispatch/private HTTP, SQL regressiyalar/guide va01/02/03. Oldingi003A proof ma'nosi saqlanadi; transfer eventida previous membership va exact revoked grant bo'ladi. Concurrency/rollback/last-owner continuity, immutable history, populated upgrade, affected/full CI va pinned peer review talab qilinadi.003C recovery va pilot qabuli doiradan tashqari.

## ORG-CODEX-003C1 — Fixed-revision existing-staff OWNER continuity

- Holat: `Bajarildi` (chegaralangan backend paketi); mas'ul Codex; Issue45 yopildi, PR46 mergef726ab6. Doira/qabul: reviews/2026-11-09/org003c/REJA.md va addendum. Runtime0010/107 jadval; populated upgrade105->107 va old proof/history preservation o'tdi. fa40e54 native263 va full393 CI o'tganidan keyin Copilot stale matching replay kamchiligini topdi;3 yangi regression failed. ef4a94b tuzatishi native9 va ikkala full401 CI42534534532/42534538671 bilan o'tdi; follow-up read-only review concrete defect topmadi. Native263 old baseline ekanligi alohida yozildi. Evidence-only d78e028 final CI42535393068/42535396524 ham401 passed,304.52s/311.64s. API075 session-revocation race alohida Issue47; pilotfalse.
- Existing active staff MFA bilan faqat o'ziga murojaat qiladi; contact/consent/evidence/original grant/OWNER roster immutable. Fixed revision1; MODERATOR tavsiyasi va boshqa COMPLIANCE yakuniy tasdig'i kerak. Eski OWNER grantlari saqlanadi. Generic verification yo'llari bu case'ni approve/resubmit qila olmaydi; account recovery kind alohida.
- Fayllar: dedicated continuity service/API,0010 migration/storage, IAM kind filter, private HTTP, SQL regressiyalar/guide va01/02/03. Expired/revoked claim closure, owner objection, quorum/roster/replay/race/rollback va old proof regression majburiy. Real identity/legal authority, zero-active-owner/no-staff recovery, live provider/UI/DR va pilot qabuli doiradan tashqarida.

## AUTH-CODEX-002 — Organization amallarida joriy vakolatni commitgacha ushlash

- Holat: `Bajarildi` (chegaralangan backend paketi); Codex; Issue47 closed, PR49 merge203863d. Reja/dalil: reviews/2026-11-09/org_authority. Old source changed-state failures va reviewdan keyingi contact deadlock reproduksiyasi saqlandi.104c436 native43/26/187/full470,17a0b66 contact fix native29/full479,7386da2 testdelta native10/full480 alohida. Pinned reviewlar concrete remaining issue topmadi. Final source CI42537111572/42537115610 passed358.80s/311.51s; evidence-only bdd8b19 CI42537714800/42537717767 ham480 passed307.01s/358.28s. Pilotfalse.
- Register/submit/patch/revoke/private join detail/download, invitation create/accept/replay/revoke va member request/approve current-MFA/session/accountni business lockdan keyin tekshiradi. Org authority grantlari ham transaction-bound. Governance servisiga actual ActorContext beriladi, user_iddan sessionsiz actor yasalmaydi. Oldindan o'tgan bekor qilish rad etadi; vakolat avval bloklansa, bekor qilish commitni kutadi. Yangi MFA siyosati, migration yoki grant tarixini almashtirish yo'q.
- Qabul: changed-state HTTP va actual DB lock wait, teskari commit serialization, scoped grants va rollback; old org/invite/ownership/appeal/IAM/full PostgreSQL CI va pinned peer review. Initial opportunity moderation race separately confirmed2 failed/Issue48; bu paket uni tuzatdi deb aytilmaydi. Pilotfalse; keyin48 va EDU.

## AUTH-CODEX-003 — Initial opportunity moderation authority

- Holat: `Bajarildi` (chegaralangan backend paketi); Codex; Issue48 closed, PR50 mergea13caf4. Reja/dalil reviews/2026-11-09/moderation_authority.5856dc6 native22/old93/full502;08626bf test-only delta native24/full504 passed383.65s/391.71s. Native24 eski22ni takrorlaydi. Final pinned review gap closed, concrete remaining issue yo'q. Evidence2d30b7f CI42562123636/42562127723 ham504 passed405.83s/381.81s. Initial failure dalillari/scopes saqlanadi; pilotfalse.
- API actual ActorContextni beradi; service opportunity rowni bloklagach existing current-MFA moderator_authorityni oladi. Existing role/MFA siyosati, self-author/DRAFT/revision, case/action/audit atomikligi saqlanadi; synthetic actor olib tashlandi. Expiry boundary va time/row-lock farqi guideda. Boshqa domain, live/browser/DR va umumiy pilot qabuli yo'q. Yangi confirmed refund authority race Issue51 (3 failed, approval/outbox navbati; real transfer emas) EDUdan oldin tuzatiladi.

## AUTH-CODEX-004 — Human money transaction authority

- Holat: `Bajarildi` (chegaralangan backend paketi); Codex; Issue51 closed, PR52 merged d480012. Reja/dalil reviews/2026-11-09/billing_authority. Old5856 refund3/org-wait5/target-repeat3 failures saqlandi. d88ebaf native75/old137 va ikkala full579 CI passed. Code review production defect topmadi;895fb8c replay-role+fresh MFA3 cases passed9.03s.1368ee5 actual wait graphs bilan test proofni kuchaytirdi; final78 native passed104.23s, wait review gap closed. Runtime d88 bilan aynan bir xil; full582 CI42564327339/42564331479 ham passed437.43s/441.90s. Final evidence ee72769 full582 CI42565434404/42565439840 passed427.47s/444.08s va matching-head merge bajarildi. Overlapping native runs distinct total emas. No sessionless fallback/schema/provider change, pilotfalse.
- Funds/idempotency/price/dual control/audit/outbox saqlanadi; signed callback logoutdan keyin ishlashi positive control. Quota publish/transitiondagi boshqa assurance o'zgarmadi. Synthetic HMAC/admin grant fixtures actual merchant/provider/secret rotation/browser/DR/pilot emas. Scope va expiry boundary guideda; keyin EDU.

## EDU-CODEX-001A — Institutional authority prerequisite

- Holat: `Bajarildi` (chegaralangan backend paketi); Codex; Issue53 closed, PR54 merge85dbb0e. Reja va saqlangan probe dalillari reviews/2026-11-09/institution_authority. Eski1368 source corrected probe8 failed/1 valid control passed17.77s: appointment validity/identity/acceptance cheklovlari ishlamagan. Dastlabki9 fixture TypeError alohida, security finding emas. Initial predicate fix9 passed17.28s; bu keyingi butun paketning final qabuli emas.
- Shared effective role query va actual session/role locks existing academic create/revoke/reviewga qo‘llandi. Initial academic59 native passed267.27s, old affected128 passed362.14s. Actual Copilot exit0 review dual-role MFA service gapini topdi; middleware static dual role uchun ishlaydi, lekin post-preflight grant actual HTTP201 bilan tasdiqlandi. Imported revision-author binding ham qo‘shildi; old runtime3 new regressions failed51.04s. Fix2c3f2e1da current sensitive roles MFA va author/candidate tekshiruvi bor; delta4 passed38.59s, exact-source final93 passed273.95s. Read-only follow-up exit0 findings resolved/no concrete remaining defect. Both complete675 CI42620428502/42620435667 passed418.26s/346.12s. Evidence-only checks/matching-head merge qolgan; overlapping runs unique count sifatida qo‘shilmaydi. Fixture scope/document metadata trusted import, yangi public intake/acceptance/admission API yoki legal certification emas. API017/096/097 hali501. Keyingi paket EDU-CODEX-001B; pilotfalse.

## EDU-CODEX-001B — Reviewed institution onboarding

- Holat: `Bajarildi` (chegaralangan backend paketi); Codex; Issue55 closed/PR56 merge12cd30746a2412afba326adc3025782638029900, source eadac1149ba66d8e34f77190c21f1c6211183a65. API017/096/097, firstCOORD/currentCOORD requestedTEACHER, independent review+exact-revision named consent, explicit revisions/revoke/private files va forward0011 bajarildi. Runtime111/canonical94,49 explicit/83 placeholder. Final4ffbe96 head ikkala732 CI42679916814/42679929206 passed383.64s/463.87s; matching-head merge bajarildi.
- Native52 passed236.823s va old affected303 passed891.982s40e source bosqichida; post-review55 passed165.333s old contact fixdan avval; privacy/followup/Tashkent36 passed86.459s final source bilan. Overlap total emas. Final complete732 CI42672853806/42672846232 attempt2 passed450.27s/508.64s. Old prototype/privacy/SQL-MFA/retry probes va fixes, startup-server errors, real wait graph dalillari HISOBOT.md ichida. Actual read-only Copilot follow-up exit0 findings closed; agent test/SHA/pilot certify qilmagan.
- Keyingi Issue57: actual private GET provider version binding; hozir metadata snapshots/content-addressed keys actual provider immutability proof emas. Additional coordinator/recovery/student admission/export/grade/frontend/live identity/legal/provider certification alohida; pilotfalse.

## S0 — Umumiy ish xotirasini tayyorlash

| ID | Kichik bo'lim | Holat | Mas'ul | Qabul dalili |
| --- | --- | --- | --- | --- |
| S0.1 | Mavjud matnlar va 1.4 texnik PDFni o'qish | Bajarildi | Codex | 3 matn manbasi va 9 sahifalik PDF matni o'qildi |
| S0.2 | AI rollari, mas'uliyat va topshirish qoidalari | Bajarildi | Codex | 01-fayl |
| S0.3 | Texnik tanlovlarni manbadan ajratish | Bajarildi | Codex | 02-faylda ma'lum va noma'lum tanlovlar ajratildi |
| S0.4 | Bosqichlar va qarorlar jurnali | Bajarildi | Codex | 03 va 04-fayllar; fayllar mavjudligi va havolalar tekshiruvi |

## S1 — Talablar va kichik ish paketlari

| ID | Kichik bo'lim | Holat | Mas'ul | Qabul mezoni |
| --- | --- | --- | --- | --- |
| S1.1 | Mavjud talablar va manbalar xaritasi | Tekshiruvda | Antigravity (`Gemini 4 Argon (High)`) | Ish/amaliyot oqimlari, rollar, mavjud AC va bo'shliqlar manba bilan bog'lanadi (`05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md`, Issue `#1`) |
| S1.2 | Yetishmayotgan SQL, 1.3 TZ va atlasni olish yoki tiklash doirasini kelishish | Tekshiruvda | Antigravity (`Gemini 4 Argon (High)`) | `specs/v1_3/` (25 fayl SHA-256 tasdiqlandi) ko'chirildi; `specs/v1_4/FlexBridge_1_4_schema.sql` va `FlexBridge_model_1_4.json` (94 jadval, 935 maydon, 214 FK) yaratilib PGlite/PostgreSQL da 17/17 invariant sinovidan o'tdi (Issue `#3`) |
| S1.3 | Ochiq texnik tanlovlarni alohida taklif qilish | Tekshiruvda | Antigravity (`Gemini 4 Argon (High)`) | `T-007` va `T-008` 04-faylda (`Q-010` bilan tanlandi) va tanlangan vositalar 02-faylda aks etdi (Issue `#3`) |
| S1.4 | Birinchi kichik amalga oshirish paketini tayyorlash | Tekshiruvda | Antigravity (`Gemini 4 Argon (High)`) | `S2.1` (`S2.1.1..S2.1.3`) va `S2.2` (`S2.2.1..S2.2.2`) kichik vazifa paketlari maqsad, fayllar, bog'liqlik va sinov mezonlari bilan rejalashtirildi (Issue `#3`) |

## S2 — R1 dasturlash uchun dastlabki ish bo'limlari

Quyidagi bo'limlar reja, bajarilgan funksiyalar emas. Har biri boshlanishidan oldin S2.1.1 kabi kichik vazifalarga bo'linadi. Butun bo'lim bitta katta topshiriqda yozilmaydi.

| ID | Bo'lim | Holat | Tekshiruv yo'nalishi |
| --- | --- | --- | --- |
| S2.1 | Loyiha asosi va DB migratsiyalari | Tuzatish kerak (`REV-003`) | Manbadagi sxema, constraint va tranzaksiyalar |
| S2.2 | Hisob, sessiya, tashkilot va vakolatlar | Tuzatish kerak (`REV-003`) | Rol/scope, o'zini tasdiqlamaslik, revoke |
| S2.3 | Nomzod profili va bo'sh vaqt | Tuzatish kerak (`REV-003`) | Vaqt intervallari va istisnolar |
| S2.4 | E'lon, smena va moslik | Tuzatish kerak (`REV-003`) | Shartnoma, maosh shartlari, ALL/ANY; AC-039 |
| S2.5 | Ariza, suhbat, taklif, ish boshlanishi | Tuzatish kerak (`REV-003`) | Holat o'tishlari va ikki tomon tasdig'i |
| S2.6 | Akademik amaliyot, tayinlov, kundalik | Tuzatish kerak (`REV-003`) | Mentor/o'qituvchi ajratilishi, AC-040 |
| S2.7 | Xususiy fayllar, karantin, eksport | Tuzatish kerak (`REV-003`) | Scan holati, ruxsat va signed URL; AC-042 |
| S2.8 | Tarif, kvota, to'lov va qaytarish | Tuzatish kerak (`REV-003`) | Parallel limit, pul yaxlitligi, dual-control |
| S2.9 | Moderatsiya, audit va saqlash siyosati | Tuzatish kerak (`REV-003`) | Scope, o'zgarmas tarix, asoslangan retention; AC-041 |
| S2.10 | Pilotga tayyorgarlik va operatsiyalar | Tuzatish kerak (`REV-003`) | Mavjud AC talablari, tiklash, alert va qo'llab-quvvatlash dalillari |

### S2.1 va S2.2 bo'yicha maydalangan kichik ish paketlari (`S1.4` natijasi)

| Kichik ID | Kichik vazifa nomi | Holat | Mas'ul | Tegiladigan fayllar | Qabul va sinov mezoni |
| --- | --- | --- | --- | --- | --- |
| S2.1.1 | Backend ilova asosi, konfiguratsiya, `API-X05/X06` health va 1.4 DB migratsiya/invariant sinov paketi | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/pyproject.toml`, `backend/requirements.txt`, `backend/app/core/config.py`, `backend/app/db/schema.py`, `backend/app/main.py`, `backend/tests/test_s2_1_1_foundation.py` | FastAPI `/api/v1/health/live`, `/api/v1/health/ready`, `/api/v1/meta/schema-summary` ishlaydi; `pytest` (`38/38 passed`) orqali 94 jadval, 935 maydon, 214 FK va 17/17 PostgreSQL invariantlari avtomatik tekshirildi (Issue `#5`, `#31`) |
| S2.1.2 | Tranzaksiya boshqaruvchisi (`SET CONSTRAINTS ALL IMMEDIATE` / `DEFERRABLE`), `audit_events` append-only yordamchisi va P1 circuit-breaker | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/db/session.py`, `backend/app/core/audit.py`, `backend/app/core/circuit_breaker.py`, `backend/tests/test_s2_1_2_transactions_audit.py` | Siklik FK (`opportunity ↔ revision`, `thread ↔ message`) bitta atomik tranzaksiyada yozildi; `audit_events`, `consent_events`, `billing_ledger`, revision o'zgarmasligi va umumiy DB-backed P1 circuit-breaker (`503`) `pytest`da tasdiqlandi (Issue `#7`, `#31`) |
| S2.1.3 | `retention_policies` (`DB-083` v1 — 8 toifa) va `feature_flags` (`DB-092`) servisi | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/retention.py`, `backend/app/services/feature_flags.py`, `backend/tests/test_s2_1_3_retention_flags.py` | 8 ta huquqiy saqlash muddati (`1 kun` .. `5 yil` / `23-kun ogohlantirish`) va `DB-092` feature flag holatlari `pytest`da (`14/14 passed`) tekshirildi (Issue `#9`) |
| S2.2.1 | Autentifikatsiya, sessiya, Argon2id/TOTP va L1+Redis darhol revoke (`INV-15`, `AC-017`) | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/auth.py`, `backend/app/api/v1/auth.py`, `backend/tests/test_s2_2_1_auth_revoke.py` | Haqiqiy `argon2-cffi` Argon2id, base32/hex TOTP, 18+ talabi, SQL sessiya saqlash (`subprocess` lararo umumiy) va darhol revoke (`401 AUTH_REVOKED`) tasdiqlandi (Issue `#11`, `#31`) |
| S2.2.2 | Tashkilot a'zoligi, ikki shaxs qoidasi (`INV-11`) va `API-060` / `API-061` scope tekshiruvi (`INV-12`, `AC-041`) | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/governance.py`, `backend/app/api/v1/governance.py`, `backend/tests/test_s2_2_2_dual_control_scope.py` | Server-side `ActorContext` (`Bearer`), o'z-o'zini tasdiqlamaslik (`409`), begona korxona/muassasa `403`, kanonik `API-060`/`061`/`073` va moderatsiya asoslari `pytest`da tasdiqlandi (Issue `#13`, `#31`) |
| S2.3.1 | Nomzod profili, `int4range(start_minute, end_minute, '[)')` bo'sh vaqt qoidalari va istisnolar (`INV-01`) | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/availability.py`, `backend/app/api/v1/availability.py`, `backend/tests/test_s2_3_1_availability.py` | Ustma-ust tushuvchi `[)` intervallar `409` (`23P01`) bilan rad etildi, tutash (`[540, 720)` + `[720, 900)`) intervallar `[540, 900)` sifatida birlashdi (`R-13`, Issue `#15`, `#31`) |
| S2.4.1 | E'lon reviziyasi (`contract_type`, maosh matritsasi), `group_code` smena guruhi va `API-003` (`ALL`/`ANY`) moslik dvigateli (`INV-02`, `INV-03`, `AC-039`) | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/opportunities.py`, `backend/app/api/v1/opportunities.py`, `backend/tests/test_s2_4_1_matching_ac_039.py` | Majburiy `contract_type` (`422`), 5 slot kvotasi (`409`), kanonik `API-003` (`POST /api/v1/matching/preview`) va `ALL`/`ANY` moslik tasdiqlandi (`AC-039`, Issue `#17`, `#31`) |
| S2.5.1 | Ariza, suhbat, taklif, ikki tomon tasdiqlagan ish boshlanishi (`placements`) va `INV-08` cross-table FK | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/placements.py`, `backend/app/api/v1/placements.py`, `backend/tests/test_s2_5_1_placements_inv_08.py` | `INV-08` composite FK (`409` / `23503`), `API-043` nomzod javobi va `API-046` ikki tomonlama ish boshlanishi tasdig'i (`pytest`, Issue `#19`, `#31`) |
| S2.6.1 | Akademik amaliyot, tayinlov, kundalik (`daily_logs`, `log_revisions`) va mentor vs o'qituvchi bahosi ajratilishi (`INV-09`, `AC-040`) | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/internship_logs.py`, `backend/app/api/v1/internship_logs.py`, `backend/tests/test_s2_6_1_internship_diary_ac_040.py` | `0 < total_minutes <= 480` va placement mavjudligi tekshiruvi (`422`, `R-08`), `API-054`/`API-056` hamda mentor vs o'qituvchi bahosi ajratilishi (`AC-040`, Issue `#21`, `#31`) |
| S2.7.1 | Xususiy fayllar, `quarantine/` skaneri (`ClamAV` + `pypdf` 8 ta token / `50 bet / 5000 obyekt / 20 MB`) va 60s signed URL (`INV-14`, `AC-042`) | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/files_quarantine.py`, `backend/app/api/v1/files.py`, `backend/tests/test_s2_7_1_files_quarantine_ac_042.py` | Sticky `QUARANTINED`, `%PDF-` header tekshiruvi, begona foydalanuvchiga `403 FILE_ACCESS_DENIED` (`R-04`) va 60s signed URL (`AC-042`, Issue `#23`, `#31`) |
| S2.8.1 | Tarif (`SINGLE_POST_30D`, `ORG_PLAN_30D` 5 parallel slot), to'lov idempotentligi (`DB-072`) va dual-control qaytarish (`INV-04`, `INV-05`, `INV-10`, `AC-042`) | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/billing.py`, `backend/app/api/v1/billing.py`, `backend/tests/test_s2_8_1_billing_quota_ac_042.py` | Provayder webhook tasdig'i (`API-X04`, `R-02`), payload-bound `idempotency_key` (`R-10`), jami refund shifti (`R-06`), tarif amal qilish muddati (`R-11`) va 5 slot kvotasi (`AC-042`, Issue `#25`, `#31`) |
| S2.9.1 | Moderatsiya, audit va huquqiy saqlash (`DB-083..086`) yagona tekshiruv oqimi (`AC-041`) | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/operations.py`, `backend/app/api/v1/operations.py`, `backend/tests/test_s2_9_s2_10_pilot_readiness.py` | Moderatsiya apellyatsiyasi (`INV-11`, `AC-041`), o'zgarmas audit zanjiri va retention ijrosi (`DB-084`) `pytest`da (`38/38 passed`, Issue `#27`, `#31`) tasdiqlandi |
| S2.10.1 | R1 Pilot operatsion tayyorgarlik, zaxira/tiklash (`RPO=24s`, `RTO=4s`) va 42 AC yagona hisobot paketi | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/operations.py`, `backend/app/api/v1/operations.py`, `backend/tests/test_s2_9_s2_10_pilot_readiness.py` | Umumiy P1 circuit-breaker (`OPEN` bo'lganda `pilot_ready=False`, `R-09`), `R2_FREELANCE_MARKETPLACE=False` (`Q-011`) va `0/17` salbiy probe (`pytest` `38/38 passed`, Issue `#27`, `#31`) |

### `TD-001` asosida bajarilgan tuzatish paketlari (`FIX-01..FIX-14`, GitHub Issue #31)

Manba: `reviews/2026-11-07/TUZATISH_TEXNIK_QOLLANMA.md` (18-bo'lim). `LOG-019` doirasida barcha 14 ta paket kodda va regressiya testlarida amalga oshirilib, `reproduce_findings.py` dagi 17/17 salbiy probe bartaraf etildi (`defects_observed: 0`) va `Codex` qayta tekshiruvi uchun `Tekshiruvda` holatiga o'tkazildi.

| Paket ID | Ko'lam va modul mas'uliyati | Bog'liq `REV-001` xatolari | Holat | Mas'ul | Yakun va qabul mezoni |
| --- | --- | --- | --- | --- | --- |
| `FIX-01` | `contracts/r1_api_matrix.csv`, model/AC izchilligi, 132 ta kanonik API marshruti (`canonical_routes.py`) | `R-07` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `contracts/r1_api_matrix.csv` tuzildi; OpenAPI da 132/132 kanonik API marshruti (`API-001..124`, `API-X01..X08`) mavjudligi tasdiqlandi |
| `FIX-02` | `infra/compose.yaml`, SQLAlchemy 2.0 saqlash dvigateli (`app/db/storage.py`), Alembic baseline (`0001_v1_4_baseline_and_td001_fixes.py`) | `R-03` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `infra/compose.yaml` (PG17, PgBouncer, Redis, MinIO, ClamAV), Alembic baseline va jarayonlararo SQLite WAL saqlash dvigateli ulandi |
| `FIX-03` | `app/services/auth.py`, `app/api/dependencies.py` (`ActorContext`), haqiqiy `argon2-cffi` Argon2id, base32/hex TOTP, `API-060`, `API-061` | `R-01`, `R-03`, `R-12` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | Haqiqiy RFC 9106 Argon2id (`Type.ID`), ochiq registerda `SUPER_ADMIN` bloklandi (`403`), 2 ta jarayonda umumiy SQL sessiya (`200 OK`) |
| `FIX-04` | Server-side `ActorContext` (`Authorization: Bearer`), `API-073` (`organizations/{org}/memberships`), primary SQL + L1 darhol revoke (`INV-15`) | `R-01`, `R-03` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | Autentifikatsiyasiz admin amali `401 AUTH_REQUIRED` bilan rad etiladi; sessiya revoke qilingan zahoti `401 AUTH_REVOKED` qaytadi |
| `FIX-05` | Provayder webhook tasdig'i (`API-X04` `/api/v1/webhooks/payments/{provider}`), `PENDING_PROVIDER` holati va payload-bound `idempotency_key` | `R-02`, `R-10` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | Webhook tasdig'isiz to'lov `PENDING_PROVIDER` bo'lib qoladi; bir xil `idempotency_key` + boshqa payload `409 IDEMPOTENCY_CONFLICT` qaytaradi |
| `FIX-06` | `API-081` (`POST /api/v1/opportunities/{id}/publish`), majburiy `contract_type` (`AC-039`), 5 slot kvotasi (`AC-042`) va tarif muddati (`valid_until`) | `R-05`, `R-11` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `contract_type` berilmasa `422`; muddati o'tgan tarif yoki >5 aktiv e'lon `409` bilan bloklanadi |
| `FIX-07` | Jami qaytarishlar shifti (`sum(approved_refunds) + amount_uzs <= invoice.amount_uzs`) va 3 shaxs dual-control (`INV-05`, `INV-11`, `INV-12`) | `R-01`, `R-06` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | Ikki marta `599 000 UZS` refund so'ralganda 2-so'rov `409` bilan rad etiladi (`[201, 409]`) |
| `FIX-08` | Sticky `QUARANTINED` holati, `%PDF-` sarlavha tekshiruvi, `sha256`, File ACL (`403 FILE_ACCESS_DENIED`) va 60s signed URL (`API-X01..X03`) | `R-04` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | Karantindagi fayl qayta scan bilan tozalanmaydi; begona foydalanuvchi `/download` so'rasa `403` oladi |
| `FIX-09` | Tutash bo'sh vaqt intervallarini birlashtirish (`merge_adjacent_intervals`: `[540,720)+[720,900)=[540,900)`) va `API-003` (`POST /api/v1/matching/preview`) | `R-07`, `R-13` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `[540, 720)` va `[720, 900)` qoidalari `[540, 900)` smenani to'liq qoplaydi (`covered: true`) |
| `FIX-10` | `API-043` (`POST /api/v1/offers/{id}/respond`) va `API-046` (`POST /api/v1/engagements/{id}/confirmations`) autentifikatsiyalangan ishtirokchi tekshiruvi | `R-01` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | Taklif va ish boshlanishi tasdig'i `ActorContext` orqali tekshiriladi |
| `FIX-11` | `API-054` (`PUT /placements/{id}/logs/{date}`), `API-056` (`POST /logs/{id}/submit`), `0 < total_minutes <= 480` va placement mavjudligi tekshiruvi | `R-07`, `R-08` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `total_minutes: -1` yoki mavjud bo'lmagan placement `422` (`status: REJECTED`) qaytaradi |
| `FIX-12` | Moderatsiya apellyatsiyasi (`INV-11`, `AC-041`) va retention ijrosi (`DB-084`) | `R-01` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | Apellyatsiya va retention tekshiruvlari `pytest`da tasdiqlandi |
| `FIX-13` | Umumiy SQL-backed `FinanceCircuitBreaker` (`circuit_breaker_state`), global `503 P1_FINANCE_CIRCUIT_OPEN` handler va `pilot_ready` bog'liqligi | `R-09` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | Operations breaker yoqilganda billing `503` qaytaradi; billing breaker yoqilganda `pilot_ready: false` bo'ladi |
| `FIX-14` | `backend/tests/test_fix_01_to_14_remediation.py` va `reviews/2026-11-07/reproduce_findings.py` (17/17 salbiy probe regressiya sinovi) | `R-01..R-13` | Tuzatish kerak (`REV-003`) | Antigravity (`Gemini 4 Argon (High)`) | `pytest` `38/38 passed`; `reproduce_findings.py` da `defects_observed: 0` (`0/17` xato) |

## Mahsulotning uzoq muddatli bosqichlari

Manba: `FlexBridge_kelgusi_bosqichlar.md`. Davrlar loyiha boshlanishiga nisbatan ishchi taklif; kalendar muddat yoki tayyorlik kafolati emas. Barcha R bosqichlar hozir `Rejada`.

| Bosqich | Taklif davri | Ichki bo'limlar | Keyingi bosqichga o'tish sharti |
| --- | --- | --- | --- |
| R1 — Ish va amaliyot | 1–6-oy | Talablarni aniqlash; asosiy oqimlar; bepul pilot; tayyor bo'lsa pullik tarif; fikrlar asosida tuzatish | Asosiy oqimlar, korxona javobi, ikki tomon tasdiqlagan ish boshlanishi va haqiqiy to'lov dalili |
| R2 — Frilans sinovi | 7–9-oy | Tanlangan xizmatlar; paket/buyurtma; bosqichli topshirish; qabul; nizo/qaytarish | Talab va ijrochilar, qabul mezoni, hisob-kitob va huquqiy yo'l tayyor |
| R3 — Hududlar va korporativ dasturlar | 10–12-oy | Hudud tanlash; portfolio; malaka topshiriqlari; korporativ tanlovlar | Pilot sifati, takror buyurtma/to'lov, nizo jarayoni va haqiqiy e'lonlar |
| R4 — Respublika va mobil xizmat | 13–18-oy | Qamrov; mobil ilova; ko'p muassasa; ruxsatli integratsiyalar | O'lchangan talab, alohida jamoa/budjet va xizmat sifati |
| R5 — Xalqaro masofaviy xizmat | 19–24-oy | Bozor va til; mijoz yordami; masofaviy ish/buyurtma; to'lov | Bozor talabi va tegishli shartnoma, soliq, valyuta hamda ma'lumot talablari tekshirilgan |

## Har bir kichik vazifa kartasi

```text
ID / nom:
Bosqich / manba:
Mas'ul AI / model / boshlanish:
Holat:
Maqsad / doira / bog'liq vazifalar:
Tegiladigan fayllar:
Qabul mezonlari:
Bajarilgan qism / qolgan qism:
Tekshiruv dalili:
Codex xulosasi / tuzatishlar:
Keyingi kichik qadam:
```

### S1.1 — Mavjud talablar va manbalar xaritasi (GitHub Issue #1)

- ID / nom: `S1.1` / Mavjud talablar va manbalar xaritasi
- Bosqich / manba: `S1` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf`, `FlexBridge_Ustoz_uchun_loyiha_izohi.md`, `FlexBridge_kelgusi_bosqichlar.md`, `FlexBridge_Investorlar_uchun.pptx`, `Oqish_tartibi.txt`
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-06T23:21:15+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: `D:\FlexBridge` katalogidagi barcha manbalarni o'qib, 14 ta rol, ish va akademik amaliyot oqimlari (`S2.2..S2.10`), DB jadvallari/invariantlar (`INV-01..15`), API ruxsatlari, qabul mezonlari (`AC-017`, `AC-039..042`) va yetishmayotgan artefaktlar (`1.3` va `1.4` SQL/Atlas) holatini manbalarga bog'lab xaritaga tushirish (`S0.1..S0.4` ga tayanadi; `S1.2..S1.4` uchun asos bo'ladi).
- Tegiladigan fayllar: `05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md`, `01_AI_XOTIRASI_VA_QOIDALAR.md`, `02_TEXNIK_MODELLAR.md`, `03_BOSQICHLAR_VA_HOLAT.md`, `04_TAKLIFLAR_VA_TANLOVLAR.md`, `.gitignore`
- Qabul mezonlari: Ish/amaliyot oqimlari, 14 rol, mavjud AC/INV talablari va bo'shliqlar aniq manba sahifasi/qatori bilan bog'langan; topilgan `1.3` artefaktlar SHA-256 orqali tekshirilgan; ochiq tanlovlar uchun takliflar `04-fayl`ga yozilgan.
- Bajarilgan qism / qolgan qism: Barcha 5 ta manba (jumladan 27 slaydlik `.pptx` XML/notes) o'qildi; `05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md` tuzildi; lokal `D:\Codex\2026-10-26\sh\outputs\FlexBridge\` katalogidagi 41/41 ta `1.3` artefakt topildi va SHA-256 tekshiruvidan o'tkazildi. Qolgan qism: Codex tekshiruvi va foydalanuvchining `T-007`/`T-008` bo'yicha qarori.
- Tekshiruv dalili: `pypdf` (9 sahifa 1.4 PDF), `zipfile`+`xml.etree.ElementTree` (27 slayd `.pptx`), `checksums.json` SHA-256 tekshiruvi (`40/41` katalogda + `1/41` zip ichida, `reference_errors: 0`), GitHub Issue `#1` va PR.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: Codex `S1.1` ni tekshiradi; foydalanuvchi `T-007` va `T-008` takliflarini tasdiqlagach `S1.2` (`1.3` artefaktlarni `D:\FlexBridge`ga ko'chirish va `FlexBridge_1_4_schema.sql` ni yaratib PostgreSQL/PGlite da sinash) bajariladi.

### S1.2 — 1.3 artefaktlarni tiklash va `FlexBridge_1_4_schema.sql` ni yaratib tekshirish (GitHub Issue #3)

- ID / nom: `S1.2` / Yetishmayotgan SQL, 1.3 TZ va atlasni olish hamda `FlexBridge_1_4_schema.sql` yaratish
- Bosqich / manba: `S1` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf`, `D:\Codex\2026-10-26\sh\outputs\FlexBridge\`, `T-007` (`Q-010`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-06T23:39:52+05:00`
- Holat: `Tekshiruvda`
- Maqsad / doira / bog'liq vazifalar: Lokal diskda topilgan `1.3` spetsifikatsiyalarini `D:\FlexBridge\specs\v1_3\` ga ko'chirish, SHA-256 nazorat summasini tekshirish, `1.4 PDF` dagi barcha yangi ustun, FK, `int4range`, `GiST EXCLUDE`, composite FK va `audit_events` triggerlarini qo'llab `specs/v1_4/FlexBridge_1_4_schema.sql` va `specs/v1_4/FlexBridge_model_1_4.json` ni yaratish hamda PostgreSQL dvigatelida sinovdan o'tkazish (`S1.1` ga tayanadi, `S2.1` uchun baza yaratadi).
- Tegiladigan fayllar: `specs/v1_3/*`, `specs/v1_4/build_v1_4_specs.py`, `specs/v1_4/FlexBridge_model_1_4.json`, `specs/v1_4/FlexBridge_1_4_schema.sql`, `FlexBridge_1_4_schema.sql`, `specs/v1_4/verify_v1_4_schema.mjs`, `specs/v1_4/v1_4_schema_verification.json`
- Qabul mezonlari: 94 ta jadval, 935 ta maydon, 214 ta model FK, 14 ta rol, 40 ta CAP, 48 ta sahifa, 124+8 ta API kontrakti va 42 ta AC to'liq bog'langan (`reference_errors: 0`); `FlexBridge_1_4_schema.sql` PostgreSQL (`btree_gist`) ichida xatosiz yuklanadi va 17/17 invariant sinovidan o'tadi.
- Bajarilgan qism / qolgan qism: 25 ta `1.3` fayl ko'chirildi va SHA-256 tekshirildi; `FlexBridge_1_4_schema.sql` va `FlexBridge_model_1_4.json` yaratildi; `verify_v1_4_schema.mjs` orqali 17/17 invariant real PostgreSQL (PGlite 0.5.15 / PG 18.6 WASM) da tekshirildi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python D:\FlexBridge\specs\v1_4\build_v1_4_specs.py` va `node D:\FlexBridge\specs\v1_4\verify_v1_4_schema.mjs` (`all_checks_passed: true`, `17/17` passed), `specs/v1_4/v1_4_schema_verification.json`.
- Codex xulosasi / tuzatishlar: `Kutilmoqda (Tekshiruvda)`
- Keyingi kichik qadam: `S2.1.1` backend ilova asosi va 1.4 DB migratsiya/sinov paketini yaratish.

### S1.3 — Ochiq texnik tanlovlarni rasmiylashtirish (`Q-010` / `T-008`, GitHub Issue #3)

- ID / nom: `S1.3` / Ochiq texnik tanlovlarni alohida taklif qilish va qayd etish
- Bosqich / manba: `S1` / `02_TEXNIK_MODELLAR.md`, `04_TAKLIFLAR_VA_TANLOVLAR.md`, `Q-010`, `T-008`
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-06T23:39:52+05:00`
- Holat: `Tekshiruvda`
- Maqsad / doira / bog'liq vazifalar: Foydalanuvchining `Q-010` qarori asosida `T-007` (Variant A) va `T-008` (Variant A: Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2, Next.js + Tailwind CSS, Redis, MinIO/S3, ClamAV + `pypdf`, Argon2id + PyOTP + WebAuthn) tanlovlarini `02-fayl` va `04-fayl`da rasmiylashtirish.
- Tegiladigan fayllar: `02_TEXNIK_MODELLAR.md`, `04_TAKLIFLAR_VA_TANLOVLAR.md`
- Qabul mezonlari: `O-002` va `O-003` ochiq masalalari `Q-010` qarori bilan yopilgan, `02-fayl` va `04-fayl` o'zaro izchil.
- Bajarilgan qism / qolgan qism: To'liq bajarildi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `git diff 02_TEXNIK_MODELLAR.md 04_TAKLIFLAR_VA_TANLOVLAR.md`.
- Codex xulosasi / tuzatishlar: `Kutilmoqda (Tekshiruvda)`
- Keyingi kichik qadam: `S2.1.1` da tanlangan FastAPI + PostgreSQL stekini ishga tushirish.

### S1.4 — Birinchi kichik amalga oshirish paketlarini (`S2.1.1..S2.2.2`) tayyorlash (GitHub Issue #3)

- ID / nom: `S1.4` / Birinchi kichik amalga oshirish paketini tayyorlash
- Bosqich / manba: `S1` / `03_BOSQICHLAR_VA_HOLAT.md`, `05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md`
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-06T23:55:00+05:00`
- Holat: `Tekshiruvda`
- Maqsad / doira / bog'liq vazifalar: `S2.1` va `S2.2` bo'limlarini bitta katta kod to'plami qilmasdan, har biri alohida tekshiriladigan kichik paketlarga (`S2.1.1`, `S2.1.2`, `S2.1.3`, `S2.2.1`, `S2.2.2`) ajratish hamda har birining fayllari va qabul mezonlarini belgilash.
- Tegiladigan fayllar: `03_BOSQICHLAR_VA_HOLAT.md`, `01_AI_XOTIRASI_VA_QOIDALAR.md`
- Qabul mezonlari: Har bir kichik paket uchun aniq ID, maqsad, tegiladigan fayllar va avtomatlashtirilgan sinov mezoni `03-fayl`da ko'rsatilgan.
- Bajarilgan qism / qolgan qism: `S2.1.1..S2.2.2` jadvali `03-fayl`ga kiritildi. Qolgan qism: Codex tekshiruvi va `S2.1.1` ni amalga oshirish.
- Tekshiruv dalili: `03_BOSQICHLAR_VA_HOLAT.md` dagi kichik paketlar jadvali.
- Codex xulosasi / tuzatishlar: `Kutilmoqda (Tekshiruvda)`
- Keyingi kichik qadam: `S2.1.1` (GitHub Issue `#5`) ni boshlash.

### S2.1.1 — Backend ilova asosi, konfiguratsiya, `API-X05/X06` health va 1.4 DB migratsiya/invariant sinov paketi (GitHub Issue #5)

- ID / nom: `S2.1.1` / Backend ilova asosi, konfiguratsiya, `API-X05/X06` health va 1.4 DB migratsiya/invariant sinov paketi
- Bosqich / manba: `S2.1` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (5–8-betlar), `specs/v1_4/FlexBridge_1_4_schema.sql`, `specs/v1_4/FlexBridge_model_1_4.json`
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:02:01+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: `backend/` katalogida Python FastAPI ilova asosini (`app/core/config.py`, `app/db/schema.py`, `app/main.py`) yaratish, `API-X05` (`GET /api/v1/health/live`), `API-X06` (`GET /api/v1/health/ready`) va `GET /api/v1/meta/schema-summary` endpointlarini ishga tushirish hamda `pytest` orqali 94 jadval, 935 maydon, 214 FK, 8 ta retention policy (`DB-083`) va 17/17 PostgreSQL invariantlarini tekshirish (`S1.2..S1.4` ga tayanadi; `S2.1.2` uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/pyproject.toml`, `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/db/__init__.py`, `backend/app/db/schema.py`, `backend/app/main.py`, `backend/tests/test_s2_1_1_foundation.py`
- Qabul mezonlari: `API-X05` va `API-X06` endpointlari `200 OK` qaytaradi; PgBouncer (`80/20/400`), L1/Redis kesh (`15s`), signed URL (`60s`), PDF strukturaviy filtri (`50 bet / 5000 obyekt / 20 MB`, 8 ta taqiqlangan token) konfiguratsiyalari hamda 1.4 DB sxemasi `pytest` sinovidan 100% o'tadi.
- Bajarilgan qism / qolgan qism: Barcha 9 ta backend fayli yaratildi va `pytest` (`6/6 passed`) muvaffaqiyatli bajarildi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `6 passed in 0.62s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.1.2` — Tranzaksiya boshqaruvchisi (`DEFERRABLE` / `SET CONSTRAINTS ALL IMMEDIATE`), `audit_events` append-only yordamchisi va P1 moliya circuit-breaker modulini yaratish.

### S2.1.2 — Tranzaksiya boshqaruvchisi (`DEFERRABLE`), `audit_events` append-only va P1 circuit-breaker (GitHub Issue #7)

- ID / nom: `S2.1.2` / Tranzaksiya boshqaruvchisi (`SET CONSTRAINTS ALL IMMEDIATE` / `DEFERRABLE`), `audit_events` append-only yordamchisi va P1 circuit-breaker
- Bosqich / manba: `S2.1` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (3.4, 6 va 7-bo'limlar; `INV-06`, `INV-11`, `INV-13`, `INV-16`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:08:22+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: Siklik FK juftliklari (`opportunities ↔ opportunity_revisions`, `daily_logs ↔ log_revisions`, `threads ↔ messages`) uchun `DEFERRABLE INITIALLY DEFERRED` va `SET CONSTRAINTS ALL IMMEDIATE` atomik tranzaksiya boshqaruvchisini (`app/db/session.py`), `audit_events`/`consent_events`/`billing_ledger` append-only hamda revision o'zgarmaslik himoyachisini (`app/core/audit.py`) va P1 moliya circuit-breaker modulini (`app/core/circuit_breaker.py`) yaratib `pytest`da tekshirish (`S2.1.1` ga tayanadi; `S2.1.3` va `S2.2..S2.9` uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/app/db/session.py`, `backend/app/core/audit.py`, `backend/app/core/circuit_breaker.py`, `backend/tests/test_s2_1_2_transactions_audit.py`
- Qabul mezonlari: Siklik FK yozuvlari bitta atomik tranzaksiya ichida `SET CONSTRAINTS ALL IMMEDIATE` bilan muvaffaqiyatli yoziladi, uzilgan FK bo'lsa to'liq `ROLLBACK` bo'ladi; `audit_events`, `consent_events`, `billing_ledger` da `UPDATE`/`DELETE` `23514` bilan rad etiladi; P1 circuit-breaker `OPEN` holatda moliya operatsiyalarini bloklaydi va tiklashda ikki shaxs (`actor_id != second_approver_id`) talab qiladi.
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi va `pytest` (`11/11 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `11 passed in 0.84s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.1.3` — `retention_policies` (`DB-083` v1 — 8 toifa) va `feature_flags` (`DB-092`) servisini yaratish.

### S2.1.3 — `retention_policies` (`DB-083` v1 — 8 toifa) va `feature_flags` (`DB-092`) servisi (GitHub Issue #9)

- ID / nom: `S2.1.3` / `retention_policies` (`DB-083` v1 — 8 toifa) va `feature_flags` (`DB-092`) servisi
- Bosqich / manba: `S2.1` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (6-bet, `DB-083`, `DB-084`, `DB-092`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:10:35+05:00`
- Holat: `Tekshiruvda`
- Maqsad / doira / bog'liq vazifalar: `DB-083 retention_policies` 8 ta huquqiy saqlash toifasi, `UNPUBLISHED_DRAFT` 23-kun ogohlantirish va 30-kun tozalash hamda `chk_retention_legal_basis` qoidalarini (`app/services/retention.py`) va `DB-092 feature_flags` R1/R2 bosqichli funksiyalarini (`app/services/feature_flags.py`) amalga oshirib `pytest`da tekshirish (`S2.1.2` ga tayanadi; `S2.1` ni yakunlaydi).
- Tegiladigan fayllar: `backend/app/services/__init__.py`, `backend/app/services/retention.py`, `backend/app/services/feature_flags.py`, `backend/tests/test_s2_1_3_retention_flags.py`
- Qabul mezonlari: 8 ta saqlash toifasi hayotiy sikli (`RETAIN`, `WARN_EXPIRING`, `PURGE_DUE` / `ANONYMIZE_PII`) va `legal_basis >= 10` belgili tekshiruvi ishlaydi; R1 bayroqlari yoqilgan va R2 frilans bayrog'i o'chiq holatda boshqariladi hamda har o'zgarish `audit_events` ga yoziladi.
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi va `pytest` (`14/14 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `14 passed in 0.81s`.
- Codex xulosasi / tuzatishlar: `Kutilmoqda (Tekshiruvda)`
- Keyingi kichik qadam: `S2.2.1` — Autentifikatsiya, sessiya, Argon2id/TOTP va L1+Redis darhol revoke (`INV-15`, `AC-017`) paketini yaratish.

### S2.2.1 — Autentifikatsiya, sessiya, Argon2id/TOTP va L1+Redis darhol revoke (`INV-15`, `AC-017`, GitHub Issue #11)

- ID / nom: `S2.2.1` / Autentifikatsiya, sessiya, Argon2id/TOTP va L1+Redis darhol revoke (`INV-15`, `AC-017`)
- Bosqich / manba: `S2.2` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (5-bet, `INV-15`, `AC-017`, `DB-001`, `DB-004`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:13:40+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: 18+ foydalanuvchi ro'yxatdan o'tishi, Argon2id parol xeshi, RFC 6238 TOTP ikki bosqichli tasdiqlash hamda 15s L1/Redis ruxsat keshidan sessiya/rol/a'zolik bekor qilingan zahoti darhol (`0ms`) o'chirish (`INV-15`, `AC-017`) xizmatini (`app/services/auth.py`, `app/api/v1/auth.py`) yaratish va `pytest`da tekshirish (`S2.1` ga tayanadi; `S2.2.2` uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/app/services/auth.py`, `backend/app/api/__init__.py`, `backend/app/api/v1/__init__.py`, `backend/app/api/v1/auth.py`, `backend/app/main.py`, `backend/tests/test_s2_2_1_auth_revoke.py`
- Qabul mezonlari: 18+ tasdig'isiz ro'yxatdan o'tish `422 ADULT_DECLARATION_REQUIRED` qaytaradi; TOTP yoqilganda to'g'ri 6 xonali RFC 6238 kod talab qilinadi; faol sessiya bekor qilingan zahoti `/api/v1/auth/me` 15 soniya kutmasdan darhol `401 AUTH_REVOKED` qaytaradi (`AC-017`).
- Bajarilgan qism / qolgan qism: Barcha 6 ta fayl yaratildi/yangilandi va `pytest` (`17/17 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `17 passed in 1.19s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.2.2` — Tashkilot a'zoligi, ikki shaxs qoidasi (`INV-11`) va `API-060` / `API-061` scope tekshiruvi (`INV-12`, `AC-041`).

### S2.2.2 — Tashkilot a'zoligi, ikki shaxs qoidasi (`INV-11`) va `API-060` / `API-061` scope tekshiruvi (`INV-12`, `AC-041`, GitHub Issue #13)

- ID / nom: `S2.2.2` / Tashkilot a'zoligi, ikki shaxs qoidasi (`INV-11`) va `API-060` / `API-061` scope tekshiruvi (`INV-12`, `AC-041`)
- Bosqich / manba: `S2.2` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (3.3, 4 va 6-bo'limlar; `INV-09`, `INV-11`, `INV-12`, `API-060`, `API-061`, `AC-041`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:16:56+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: Tashkilot a'zoligini tasdiqlashda Ikki shaxs qoidasi (`created_by != approved_by`, `409 SELF_APPROVAL_FORBIDDEN`), tashkilotlararo scope chegarasi (`403 SCOPE_VIOLATION`), `API-060` (`POST /api/v1/internships/academic-assignments` — faqat `INST_INTERNSHIP_COORDINATOR` va `SUPER_ADMIN`) va `API-061` (`PATCH /api/v1/internships/academic-assignments/{id}` — muassasa va biriktirilgan rahbar tekshiruvi) hamda moderatsiya asoslari (`policy_code`, `reason_code`, `justification >= 15`) xizmatini (`app/services/governance.py`, `app/api/v1/governance.py`) yaratib `pytest`da tekshirish (`S2.2.1` ga tayanadi; `S2.2` ni yakunlaydi).
- Tegiladigan fayllar: `backend/app/services/governance.py`, `backend/app/api/v1/governance.py`, `backend/app/main.py`, `backend/tests/test_s2_2_2_dual_control_scope.py`
- Qabul mezonlari: O'z-o'zini tasdiqlash `409 SELF_APPROVAL_FORBIDDEN` bilan rad etiladi; begona tashkilot yoki muassasa obyekti `403 SCOPE_VIOLATION` oladi; `API-060` da `ACADEMIC_SUPERVISOR` `403 FORBIDDEN_ROLE_FOR_API_060` oladi; moderatsiya amali kamida 15 belgili izohsiz `422` qaytaradi (`AC-041`).
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi/yangilandi va `pytest` (`20/20 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `20 passed in 1.28s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.3.1` — Nomzod profili, `int4range(start_minute, end_minute, '[)')` bo'sh vaqt qoidalari va istisnolari (`INV-01`).

### S2.3.1 — Nomzod profili, `int4range(start_minute, end_minute, '[)')` bo'sh vaqt qoidalari va istisnolari (`INV-01`, GitHub Issue #15)

- ID / nom: `S2.3.1` / Nomzod profili, `int4range(start_minute, end_minute, '[)')` bo'sh vaqt qoidalari va istisnolari (`INV-01`)
- Bosqich / manba: `S2.3` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (3.1-bo'lim, `INV-01`, `DB-013`, `DB-014`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:20:19+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: Yarim-ochiq `[start_minute, end_minute)` (`int4range`) qoidalari va sana istisnolari (`availability_rules`, `availability_exceptions`) hamda ustma-ust tushishni (`&&`) bloklovchi `INV-01` xizmatini (`app/services/availability.py`, `app/api/v1/availability.py`) yaratish va `pytest`da tekshirish (`S2.2` ga tayanadi; `S2.4.1` moslik dvigateli uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/app/services/availability.py`, `backend/app/api/v1/availability.py`, `backend/app/main.py`, `backend/tests/test_s2_3_1_availability.py`
- Qabul mezonlari: `0 <= start_minute < end_minute <= 1440` chegarasi tekshiriladi; bir xil `(candidate_id, weekday)` yoki `(candidate_id, exception_date)` uchun ustma-ust tushuvchi interval `409` (`23P01`) bilan rad etiladi, ketma-ket (`[540, 720)` va `[720, 900)`) intervallar qabul qilinadi.
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi/yangilandi va `pytest` (`22/22 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `22 passed in 1.28s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.4.1` — E'lon reviziyasi (`contract_type`, maosh matritsasi), `group_code` smena guruhi va `API-003` (`ALL`/`ANY`) moslik dvigateli (`INV-02`, `INV-03`, `AC-039`).

### S2.4.1 — E'lon reviziyasi (`contract_type`, maosh matritsasi), `group_code` smena guruhi va `API-003` (`ALL`/`ANY`) moslik dvigateli (`INV-02`, `INV-03`, `AC-039`, GitHub Issue #17)

- ID / nom: `S2.4.1` / E'lon reviziyasi (`contract_type`, maosh matritsasi), `group_code` smena guruhi va `API-003` (`ALL`/`ANY`) moslik dvigateli
- Bosqich / manba: `S2.4` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (2–4 va 8-betlar; `INV-02`, `INV-03`, `API-003`, `AC-039`, `DB-026`, `DB-027`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:23:38+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: `opportunity_revisions` (`DB-026`) uchun `contract_type` va maosh (`HOURLY`/`STIPEND`/`UNPAID_ACADEMIC`) matritsasini (`INV-03`, `AC-039`), `opportunity_shifts` (`DB-027`) uchun `group_code` va ustma-ust tushmaslik qoidasini (`INV-02`, `23P01`) hamda `API-003` (`GET /api/v1/opportunities/feed`) `ALL_SHIFTS_IN_GROUP` vs `ANY_SHIFT_IN_GROUP` moslik dvigatelini (`app/services/opportunities.py`, `app/api/v1/opportunities.py`) yaratish va `pytest`da tekshirish (`S2.3.1` ga tayanadi; `S2.5.1` uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/app/services/opportunities.py`, `backend/app/api/v1/opportunities.py`, `backend/app/main.py`, `backend/tests/test_s2_4_1_matching_ac_039.py`
- Qabul mezonlari: Noto'g'ri `contract_type` yoki maosh kombinatsiyasi `422` (`23514`) bilan rad etiladi; bir xil `group_code` ichida ustma-ust smena `409` (`23P01`) oladi; `ALL_SHIFTS_IN_GROUP` faqat barcha smenalari qoplangan `group_code`ni, `ANY_SHIFT_IN_GROUP` esa kamida 1 ta smenasi qoplangan e'lonni qaytaradi va `UNAVAILABLE` istisno kunida moslikdan chiqaradi (`AC-039`).
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi/yangilandi va `pytest` (`24/24 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `24 passed in 1.32s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.5.1` — Ariza, suhbat, taklif, ikki tomon tasdiqlagan ish boshlanishi (`placements`) va `INV-08` cross-table FK.

### S2.5.1 — Ariza, suhbat, taklif, ikki tomon tasdiqlagan ish boshlanishi (`placements`) va `INV-08` cross-table FK (GitHub Issue #19)

- ID / nom: `S2.5.1` / Ariza, suhbat, taklif, ikki tomon tasdiqlagan ish boshlanishi (`placements`) va `INV-08` cross-table FK
- Bosqich / manba: `S2.5` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (3.3-bo'lim `INV-08`, `DB-031`, `DB-032`, `DB-038`, `DB-041`), `FlexBridge_Ustoz_uchun_loyiha_izohi.md`
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:26:35+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: `applications`, `application_attempts`, `offers` va `placements` jadvallari o'rtasidagi `INV-08` composite FK (`23503`) tekshiruvlarini hamda nomzod va korxona ikki tomonlama ish boshlanishini tasdiqlash (`PENDING_START_CONFIRMATION` -> `ACTIVE`) oqimini (`app/services/placements.py`, `app/api/v1/placements.py`) yaratish va `pytest`da tekshirish (`S2.4.1` ga tayanadi; `S2.6.1` amaliyot kundaligi uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/app/services/placements.py`, `backend/app/api/v1/placements.py`, `backend/app/main.py`, `backend/tests/test_s2_5_1_placements_inv_08.py`
- Qabul mezonlari: `application_attempts` va `placements` boshqa e'longa bog'langan `opportunity_id` bilan yuborilsa `409` (`23503`) qaytaradi; `placements` faqat ikkala tomon (`CANDIDATE` va `ORGANIZATION`) tasdiqlagandan keyin `ACTIVE` holatga o'tadi.
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi/yangilandi va `pytest` (`26/26 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `26 passed in 1.41s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.6.1` — Akademik amaliyot, tayinlov, kundalik (`daily_logs`, `log_revisions`) va mentor vs o'qituvchi bahosi ajratilishi (`INV-09`, `AC-040`).

### S2.6.1 — Akademik amaliyot, tayinlov, kundalik (`daily_logs`, `log_revisions`) va mentor vs o'qituvchi bahosi ajratilishi (`INV-09`, `AC-040`, GitHub Issue #21)

- ID / nom: `S2.6.1` / Akademik amaliyot, tayinlov, kundalik (`daily_logs`, `log_revisions`) va mentor vs o'qituvchi bahosi ajratilishi (`INV-09`, `AC-040`)
- Bosqich / manba: `S2.6` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (3.3 va 8-bo'limlar; `INV-09`, `AC-040`, `DB-043`, `DB-046`, `DB-049`, `DB-052`, `DB-053`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:30:08+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: `daily_logs`, `log_revisions`, `workplace_log_reviews` (`DB-052`) va `academic_log_reviews` (`DB-053`) jadvallarida korxona mentori hamda oliygoh/texnikum o'qituvchisi baholarini alohida yuritish va `INV-09` composite FK (`23503`) tekshiruvini (`app/services/internship_logs.py`, `app/api/v1/internship_logs.py`) amalga oshirish (`S2.5.1` ga tayanadi; `S2.7.1` uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/app/services/internship_logs.py`, `backend/app/api/v1/internship_logs.py`, `backend/app/main.py`, `backend/tests/test_s2_6_1_internship_diary_ac_040.py`
- Qabul mezonlari: `workplace_log_reviews` va `academic_log_reviews` bir-birining ustiga yozilmasdan alohida saqlanadi; boshqa `placement_id` ga tegishli mentor yoki akademik rahbar kundalikni baholamoqchi bo'lsa `409` (`23503`) qaytariladi (`AC-040`).
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi/yangilandi va `pytest` (`27/27 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `27 passed in 1.44s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.7.1` — Xususiy fayllar, `quarantine/` skaneri (`ClamAV` + `pypdf` 8 ta token / `50 bet / 5000 obyekt / 20 MB`) va 60s signed URL (`INV-14`, `AC-042`).

### S2.7.1 — Xususiy fayllar, `quarantine/` skaneri (`ClamAV` + `pypdf` 8 ta token) va 60s signed URL (`INV-14`, `AC-042`, GitHub Issue #23)

- ID / nom: `S2.7.1` / Xususiy fayllar, `quarantine/` skaneri (`ClamAV` + `pypdf` 8 ta token / `50 bet / 5000 obyekt / 20 MB`) va 60s signed URL (`INV-14`, `AC-042`)
- Bosqich / manba: `S2.7` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (5 va 8-bo'limlar; `INV-14`, `AC-042`, `DB-018`, `API-X01..X03`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:32:57+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: Yangi yuklangan fayllarni `quarantine/` prefiksi va `PENDING_SCAN` holatida saqlash, `ClamAV` imzosi hamda `pypdf` strukturaviy filtri (`50 bet / 5000 obyekt / 20 MB` va 8 ta taqiqlangan token: `/JS`, `/JavaScript`, `/AA`, `/OpenAction`, `/Launch`, `/EmbeddedFiles`, `/RichMedia`, `/XFA`) orqali tekshirish va faqat `CLEAN` (`PRIVATE_READY`) fayllar uchun 60 soniyalik signed URL (`API-X03`) berish (`app/services/files_quarantine.py`, `app/api/v1/files.py`).
- Tegiladigan fayllar: `backend/app/services/files_quarantine.py`, `backend/app/api/v1/files.py`, `backend/app/main.py`, `backend/tests/test_s2_7_1_files_quarantine_ac_042.py`
- Qabul mezonlari: `PENDING_SCAN` yoki `QUARANTINED` fayl uchun `API-X03` (`/download`) chaqirilganda `409 FILE_NOT_CLEAN_FOR_DOWNLOAD` qaytadi va signed URL berilmaydi (`AC-042`); toza PDF `CLEAN` holatga o'tib 60s signed URL oladi.
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi/yangilandi va `pytest` (`28/28 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `28 passed in 1.48s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.8.1` — Tarif (`SINGLE_POST_30D`, `ORG_PLAN_30D` 5 parallel slot), to'lov idempotentligi (`DB-072`) va dual-control qaytarish (`INV-04`, `INV-05`, `INV-10`, `AC-042`).

### S2.8.1 — Tarif (`SINGLE_POST_30D`, `ORG_PLAN_30D` 5 parallel slot), to'lov idempotentligi (`DB-072`) va dual-control qaytarish (`INV-04`, `INV-05`, `INV-10`, `AC-042`, GitHub Issue #25)

- ID / nom: `S2.8.1` / Tarif (`SINGLE_POST_30D`, `ORG_PLAN_30D` 5 parallel slot), to'lov idempotentligi (`DB-072`) va dual-control qaytarish (`INV-04`, `INV-05`, `INV-10`, `AC-042`)
- Bosqich / manba: `S2.8` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (3.2, 6, 7 va 8-bo'limlar; `INV-04`, `INV-05`, `INV-10`, `INV-11`, `AC-042`, `DB-069..073`, `API-073`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:36:01+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: `SINGLE_POST_30D` (`149 000 UZS`, 1 ta e'lon) va `ORG_PLAN_30D` (`599 000 UZS`, 5 ta parallel faol e'lon kvotasi, `INV-04`) tariflarini, `AC-042` slot tekshiruvini (5 ta faol `PUBLISHED` e'lon to'lganda 6-chisini `409 CONCURRENT_QUOTA_REACHED` bilan bloklash va 1 tasi `CLOSED` bo'lgach ochish), `DB-072 payment_attempts` idempotentlik kalitini (`API-073`) hamda `DB-073 refunds` (`refund <= invoice` va `INV-11` dual-control) modulini (`app/services/billing.py`, `app/api/v1/billing.py`) amalga oshirish (`S2.7.1` ga tayanadi; `S2.9.1` va `S2.10.1` uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/app/services/billing.py`, `backend/app/api/v1/billing.py`, `backend/app/main.py`, `backend/tests/test_s2_8_1_billing_quota_ac_042.py`
- Qabul mezonlari: `ORG_PLAN_30D` da 5 ta e'lon `PUBLISHED` bo'lib turganda 6-chisini nashr etish `409 CONCURRENT_QUOTA_REACHED` qaytaradi, 1 tasi `CLOSED` qilingach 6-e'lon nashr etiladi (`AC-042`); bir xil `idempotency_key` takrorlanganda ikkinchi marta pul yechilmaydi; `refund > invoice` (`INV-05`) yoki o'z-o'zini tasdiqlagan refund (`INV-11`) `409` bilan rad etiladi.
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi/yangilandi va `pytest` (`30/30 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `30 passed in 1.46s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: `S2.9.1` va `S2.10.1` — Moderatsiya/Audit/Retention zanjiri (`AC-041`) va R1 Pilot operatsion tayyorgarlik hisoboti (`AC-001..042`).

### S2.9.1 va S2.10.1 — Moderatsiya/Audit/Retention zanjiri (`AC-041`) va R1 Pilot operatsion tayyorgarlik hisoboti (`AC-001..042`, GitHub Issue #27)

- ID / nom: `S2.9.1` & `S2.10.1` / Moderatsiya, audit, retention ijrosi (`DB-082`, `DB-084`, `AC-041`) va R1 Pilot operatsion tayyorgarlik hisoboti (`AC-001..042`, `Q-011`)
- Bosqich / manba: `S2.9`, `S2.10` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (6, 7 va 8-bo'limlar; `INV-11`, `INV-13`, `AC-041`, `DB-079..086`, `DB-092`), `Q-011`
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:41:29+05:00`
- Holat: `Tuzatish kerak` (`REV-001`)
- Maqsad / doira / bog'liq vazifalar: `DB-082 moderation_appeals` da dastlabki moderatordan farqli apellyatsiya tekshiruvchisini (`original_moderator_id != appeal_reviewer_id`, `INV-11`) va kamida 15 belgili qaror izohini (`AC-041`), `DB-084 retention_executions` oqimini hamda `GET /api/v1/operations/pilot-readiness` endpointi orqali `RPO=24 soat`, `RTO=4 soat`, P1 circuit-breaker `CLOSED`, 94 jadval / 17/17 PostgreSQL invariantlari, 42 ta AC va `Q-011` (`R2_FREELANCE_MARKETPLACE=False`) chegarasini tekshirish (`S2.8.1` ga tayanadi; `S2` R1 dasturlash paketlarini yakunlaydi).
- Tegiladigan fayllar: `backend/app/services/operations.py`, `backend/app/api/v1/operations.py`, `backend/app/main.py`, `backend/tests/test_s2_9_s2_10_pilot_readiness.py`
- Qabul mezonlari: O'z moderatsiya qarori ustidan tushgan apellyatsiyani ko'rib chiqish `409` (`INV-11`) bilan rad etiladi; `UNPUBLISHED_DRAFT` 25-kunida `WARN_EXPIRING` retention ijrosi yoziladi (`DB-084`); `/api/v1/operations/pilot-readiness` `pilot_ready: true` va `R2_FREELANCE_MARKETPLACE: false` qaytaradi.
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi/yangilandi va `pytest` (`32/32 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `32 passed in 1.44s`.
- Codex xulosasi / tuzatishlar: `REV-001` - qabul qilinmadi; sabablar va qayta tekshirish mezonlari `reviews/2026-11-07/BAHOLASH.md` ichida. Mavjud testlar o'tishi to'liq integratsiyani tasdiqlamaydi.
- Keyingi kichik qadam: Codex tomonidan `S1.1..S1.4` va `S2.1.1..S2.10.1` paketlarini ko'rib chiqish va qabul qilish (`Tekshiruvda` -> `Bajarildi`).

## STORAGE-CODEX-001 - Private object version binding (Issue57)

- Holat: `Bajarildi` (storage-version backend scope); Codex; PR58 merge04ffd42e40ac3a475728c203f5da1583023629e4/Issue57 closed. Final408b3cd full757 twice375.77s/507.07s.0012 va current storage pipeline accepted within scope. Reja/qarorlar/read-only Copilot exit0 va localhost MinIO proof reviews/2026-11-10/storage_versioning. Trusted provider-admin overwrite old key-only URL baytlarini almashtiradi; explicit VersionId URL originalni qaytaradi. Public overwrite exploit/live/AV claim emas.
- Implementatsiya: explicit bucket/version/ETag provenance va no-inference legacy policy; exact source scan/private GET; existing outbox fence/source compare; all6 signer callers/EDU snapshots; Enabled readiness; populated upgrade/native/real provider integration/current CI/review. Accepted role/proof history saqlanadi; unknown provenance yangi approval/download uchun fail closed. Tafsilot ANTIGRAVITY_HANDOFF.md va DECISIONS.md.
- Muhit: project .venv installed/pip check0, native smoke3 passed8.51s. Docker/WSL installers D: da hash/publisher verified, ammo Docker actual exit1 (VMP disabled), WSL MSIX0x80073D28 (admin required); installed/engine-ready emas. Native feature elevation launch canceled (OS: operation was canceled by the user), script ishga tushmagan; automatic reboot yo'q. scripts/setup_windows_dependencies.ps1 syntax valid; elevated branch hali execution proofga ega emas. Q-014 va handoff ayni holatni saqlaydi; codingni native PG/MinIO bilan davom ettirish mumkin.

- LOG-055: new25 storage+old2 private-view27 native passed44.51s; old initial/harness/diagnostic stages alohida artifacts. Actual MinIO integration7 shu27 ichida, AV double/PDF+S3+PG actual. Old affected suites, pinned source review va latest complete CI keyingi qabul gate; draft pilotfalse.

- LOG-055 sourceafd code review exit0 found no concrete version-binding defect (actual root cwd/source cleanliness qualified in REVIEW_CONTEXT.md). Native240:239 passed/1 SCANNING fixture failure350.06s; actual new schema guard retained, fixture corrected and candidate44 passed43.39s. Full current CI remains required. Issue59 separate actual authority probe failed1;57 does not close it.

## AUTH-CODEX-005 - Owner file current-session authority (Issue59)

- Holat: `Bajarildi` (bounded owner-file backend scope); Codex, PR60 merged73d3565968d26c8d1f31c420febd36a3549649d5/Issue59 closed; final935742d785 CI525.26s/469.37s. Actual pinnedafd HTTP/native probe1 failed33.57s: file-row wait observed, logout200 completes, then stale complete202/SCANNING/event1. Authenticated in-flight issue, anonymous/foreign data claim emas; storage mocked. Evidence reviews/2026-11-10/files_authority.
- Doira: upload intent/complete/owner download actual ActorContext, current account/session/existing sensitive MFA after business locks and thru commit, no sessionless fallback; version/source/outbox/ownership guarantees preserved. Ordinary PASSWORD unchanged. Candidate/CV sibling scope alohida audit qilinadi. Planning peer review, both authority orderings/security/expiry/rollback/provider integration/full CI kerak; pilotfalse.

- LOG-056: exact b251644 full757 Linux PG/actual MinIO CI42687285321/42687299361 passed530.01s/513.04s. Source/fixture reviews exit0; scoped findings none. Native counts/failures/limits separated in HISOBOT.md. Evidence-only checks/merge remain;59 next, pilotfalse.

- LOG-057:59 actualActorContext/shared account guard implementation initial27 passed36.60s; affected native running, source review/full CI remain. Freshclam exit0 and actual local clamd benign431-byte PDF adapter smoke passed; daemon stopped, no service/detection/live/pilot claim.

- LOG-057 follow-up: current affected72 passed102.01s incl actual8 MinIO cases,0fail/error/skip; current full CI/source review not yet accepted.

- LOG-058:59 exact370d9c3 complete785 CI42697954266/42697965001 passed534.16s/458.37s,1 framework warning. Isolated source review exit0 no scoped findings. Source manifests/HISOBOT/native stages separate; evidence-only checks/merge remain. Same-source candidate9 red cases do not disappear because current full785 is green.

## AUTH-CODEX-006 - Candidate self-service authority (Issue61)

- Holat: `Bajarildi` (bounded candidate backend authority); PR62 mergedb94da5516102ee880f0dd10bd429b95b78ea5b9d/Issue61 closed, final7fb411b895 CI547.44s/582.45s. Codex,9-path code/no UID-only fallback. Pinned370d9c3 actual HTTP/PG combined9 failed17.20s:5 canonical writes+2 private GET+2 legacy availability adds after observed waits/logout200 still200/201, actual business changes/private own-candidate result. Not anonymous/foreign exploitation. Earlier5/5/2/2 overlap; evidence reviews/2026-11-10/candidate_authority.
- Plan initial7 then explicit legacy2 scope review both actual read-only Copilot exit0; no test/SHA/model/pilot certification. RealActorContext, profile/file before current account guards, READ COMMITTED profile SHARE private reads, write response beforecommit; matching internal read_snapshot preserved. All9 human callers covered without actorless fallback, interval/EXCLUDE/AVAILABLE_EXTRA and skill/CV verification unchanged. Sourcebc4f95e/testdelta a31b084, full final-head CI required. Next61 acceptance then EDU; pilotfalse.

- LOG-059:61 READ COMMITTED human boundary, profile SHARE read guards/material write guards, same-transaction responses, actual actors and atomic legacy audits implemented. Existing internal matching snapshot unchanged; new109 initial native running, old direct fixtures real sessions, ordinary policy unchanged.

- LOG-059 follow-up: initial109 new native107 passed/2 exception-class harness failures318.07s; actual legacy403 scope guards correct. Test expectation corrected, no runtime change; fixed2+formal TeacherPASSWORD case3 passed12.18s. Suite now110, not yet full native110/CI acceptance. Old affected candidate/contracts/regressions running.

- LOG-060: old affected88 passed215.63s. Actual isolated bc4 source review exit0 found no implementation defect and a P2 teacher PASSWORD test-coverage gap. Same formal teacher positive expanded to all10 operation variants,1 passed8.45s; a31 follow-up review exit0 closed finding. No runtime delta; pinned manifest/contracts/native results and HISOBOT saved. Source CI42703218978/42703231479 still in progress at report snapshot; final evidence-head two complete checks/merge remain. pg_live stopped02:38, testPG55440 active, no live deployment.

## EDU-CODEX-002 - Own enrollment history and independent verification (Issue63)

- Holat: `Bajarildi` (bounded enrollment backend); PR64 merge1b2bbbf/Issue63 closed, final08b4129 full930 twice541.51s/651.09s. Codex, actual read-only planning/source/follow-up Copilot exit0. Source/test pina92, runtime revieweddbc; extra unchanged-source Teacher PASSWORD full own enrollment1 passed10.14s. Final metadata/extra probe in internship_admission/PR64_ACCEPTANCE.md. Full R1/pilot not accepted.
- Doira: canonical027/034 own declaration/submission/history, detail/end/revision helpers; explicit existing moderator queue/claim/detail/file/decision dispatch. Education optional, DECLARED never eligible; current VERIFIED only exact new public approved proof or explicitly captured pre-upgrade VERIFIED imports. Same-case revision/decision history, version-pinned private files, source1-weekday response target, terminal end/withdraw preserving ordinary profile/application/academic history.
- Fayllar: forward0013 and typed enrollment proof metadata, enrollment service/API, academic effective predicate/real-session fixture, operator dispatch/private middleware, migration/lifecycle/security/transaction regressions, backend guide/review artifacts and01/02/03/handoff. Canonical historical94 unchanged; actual runtime helper count after migration test, not assumed acceptance.
- Qabul: actual PG fresh/populated legacy/history/rollback/proof guards; own lifecycle/scopes/flags/current assurance/session waits; independent assigned exact revision review/version checks; replay/concurrency/end-vs-review/audit rollback; old affected suites, complete matching-head CI, pinned actual review and handoff. Legacy origin cannot be inserted after migration; new raw VERIFIED insert/promotion denied. New academic fixtures use real-session enrollment review, no test-only legacy bypass.
- Chegara: roles_for unchanged, broader matching/application eligibility, accepted supervision/teacher assignment/export/signatures and frontend/live identity/providers/DR/pilot remain explicit open scopes. R2 freelance absent. Current63 source not accepted; runtime implementation starts with schema/proof layer.

- LOG-062:0013/schema114 loaded on disposable PG; typed origins/revisions/events/current predicate implemented. Own027/034/detail/revision/end, explicit operator dispatch/private evidence and academic integration prototype connected. Initial schema failures were strict startup-head and fixture issues, all retained. Corrected SQL/proof3 passed17.45s; HTTP lifecycle8 passed24.75s. Actual transaction/security12 passed36.23s. Academic+updated positive63 initial62 passed/1 raw-date fixture rejected237.93s; actual end plus separate expired-enrollment creation test and SQL immutable-date assertion targeted3 passed13.43s. Runtime guard retained; stages overlap. Source/full CI/peer review and remaining acceptance tests pending, not Bajarildi/pilot. Exact history in enrollment_verification/IMPLEMENTATION_NOTES.md.

- LOG-062 follow-up: d36059b prototype/draftPR64, both CI42710013191/42710023813 and isolated actual read-only code review in progress. Later legacy HTTP3 passed35.10s, test-only delta: populated0012 trusted imports with real sessions ->0013 actual own end/replay for current/future verified and pending states, profile/history preserved/no fabricated case. Native counts overlap, full current acceptance pending.

- LOG-063: actual pinned d360 code review exit0 found P2 revision replay false acknowledgment and self-review coverage gap. Exact-runtime new2 repro1 failed/1 passed11.12s: replay changed metadata still202/no extra effect, self-review already blocked. Replay now locks/pins files before current account guard and compares full snapshot; unchanged replay remains idempotent, changed409. Review+initial lifecycle10 passed31.80s; actual replay filewait/logout and ordinary application history/service access2 passed13.84s. Full latest CI/follow-up review still required; no approval-bypass claim, pilotfalse.

- LOG-064: initial d360 full922 CI42710013191/42710023813 passed547.75s/516.38s; does not accept later fix. Actual dbc narrow follow-up exit0 P2 appears closed/no concrete delta regression/lock inversion. New populated upgrade collision/rollback1 passed12.93s, test-onlya92 preserving prior version/full row/preexisting table and rolling back captured origins. Source/app/test/config SHA256 manifest/HISOBOT/native results/current contracts51/81 captured againsta92; latest evidence-head full checks still required. Canonical registration is not acceptance, no live deploy/pilot.

## INT-CODEX-001 - Reachable host internship admission (Issue65)

- Holat: `Jarayonda`; mas'ul Codex, actual read-only source-plan reviewer Copilot CLI exit0 at08b. feature/65-internship-admission from actual origin/main1b2bbbf. Plan/decisions/probes: reviews/2026-11-10/internship_admission. Native3 failed13.64s with actual HTTP/SQL changes: PART_TIME placement201, INTERNSHIP ACTIVE without mentor200, HR-only nomination201 (unaccepted). Trusted publication/role setup, no anonymous/live or immediate review grant claim.
- Doira: canonical030/048/050/051 MENTOR/069/087/088 ACTIVATE-CANCEL/089; actual-session intake, immutable versioned plan, candidate+current named mentor acceptance and explicit host activation. New ordinary jobs cannot become placements/diaries. Derive academic-required server-side and block academic activation until following supervision/teacher unit. No UID-only legacy alias or unspecified-current-version acceptance.
- Fayllar: forward0014 and typed admission/consent/assignment/event proofs, host admission service/API, placements/internship-log aliases and diary/mentor guards, private middleware, legitimate internship/acceptance fixtures, new lifecycle/security/migration regressions, backend guide and01/02/03/handoff. Record actual runtime count after execution, not assumed.
- Qabul: real full general internship path; role/side/kind/version/session/regrant/replay/concurrency/rollback/upgrade/failure evidence, old diary/academic/engagement/candidate regressions, latest complete CI and pinned source review/manifests. Existing wrong imported history preserved without invented consent/new verified starts. Teacher branch/academic intake and completion/exports/full APP flow remain explicit follow-ups; registration not complete contract acceptance.

- LOG-066 historical snapshot: first intake/nomination guards2 passed/1 missing-mentor failed11.21s; actor/Teacher3 passed12.79s and diary/academic2 passed10.75s. Subsequent LOG-067 below supersedes the implementation state, while preserving these exact artifacts.
- LOG-067 current draft:0014 executed118 tables; exact PUBLIC/closed LEGACY_IMPORT intake, original mentor grant proof, versioned personal candidate/mentor consent, host ACTIVATE/CANCEL/revoke and immutable plan/task history. Canonical030/048/050/051-MENTOR/069/087/088-partial/089 plus actual-session legacy aliases/private projections. Broad host native37 passed156.15s, plan correction/rollback2 passed19.83s overlap; populated upgrade/failure rollback included. Real public authority revocation/concurrent retries and ordinary PASSWORD mentor/host controls passed. Source review Copilot exit0 plus task-history follow-up exit0; no model/SHA/runtime certification.
- Keep Jarayonda: affected old integration47 passed/1 academic fixture failed148.70s, old UID-only confirm setup must become genuine pending-placement school/teacher admission. Intake/nomination retry receipts, pagination, candidate viewer notification and full current CI/source acceptance still required. Details in backend/PLACEMENT_ADMISSION.md and reviews/2026-11-10/internship_admission/NEXT_ACADEMIC_UNIT.md. Accepted main remains0013/114; no65 closure/merge/pilot claim.
- Additional workplace review positive/old-grant regrant denial2 passed13.19s. Check old SQL CURRENT_DATE versus explicit Asia/Tashkent service dates on UTC PostgreSQL before claiming Linux/UTC integration; currently a source inference, not a reproduced UTC failure.
- LOG-068 supersedes those host TODOs: intake/nomination retries, >100 scoped pages and candidate in-app viewer notices implemented with real worker source/fence/rollback/current-read checks. Calendar defect reproduced and corrected; exact-predicate drift P2 reproduced and corrected,9 UTC controls passed121.47s. Final broad current UTC stage is host_utc_final; raw failures/setup error and review exits/hashes retained. New API031 basics bring registration60/72 of132, not full notification/pilot acceptance. Main worker/config includes only the added local topic; no provider delivery claim.
- Final current UTC host selection115 passed457.42s,0failure/error/skip,1framework warning. Source/config unchanged during the run; final raw JUnit/source_followup_manifest retained. Academic admission is excluded and still required before full current CI/merge acceptance; do not mark INT-CODEX-001 Bajarildi yet.
- Continue Jarayonda with real pending academic admission and63 old academic fixture cases; exact85065b1 CI66failed901passed twice599.03s/735.52s remains recorded red, not relabelled. Actual existing academic helper locks institution before placement; next unit reconciles org/host activation hints and teacher original-grant proof. See NEXT_ACADEMIC_UNIT.md and current Antigravity block. Full R1 including completion/diary/export/frontend/live/legal/DR remains open.


### INT-CODEX-001 LOG-069 - current academic core supersedes host-only TODOs

- Holat: Jarayonda/Tekshiruvda; Codex owns feature/65-internship-admission, Issue65/PR66 open/draft.0015/124 native disposable PostgreSQL, canonical94 unchanged, accepted main0013/114. Student latest own verified-school choice -> exact current coordinator/supervision/agreement binding/new plan -> named original teacher personal version consent -> common host start is implemented. New current institutional list/queue/privacy/notice work still required; do not mark this unit Bajarildi.
- Actual current stages: new HTTP5passed23.30s, corrected old authority63passed148.52s, lifecycle9passed24.59s, populated upgrade3passed35.34s, overlapping. Initial failures and corrected controls retained. Additional current affected tests/integration review and complete latest-head CI still pending. Published89fda9d CI remains63failed924passed twice, saved exact evidence. Registration64/68 of132 is registration only, no full API/pilot acceptance.
- Next ordered requirements and limits: backend/ACADEMIC_ADMISSION.md, internship_admission/NEXT_ACADEMIC_UNIT.md and current ANTIGRAVITY_HANDOFF. Full R1 objective remains active. No pg_live migration/live provider/Docker/admin/reboot action in this unit.


- LOG-070 final current correction stage:34 native UTC tests passed199.22s,0failure/error/skip,1framework warning. Exact academic HTTP/lifecycle, populated/mismatched legacy upgrade, active teacher notice/logout/fence/rollback/source controls plus mentor notices; runtime/config frozen across run. Actual corrective read-only Copilot exit0/no concrete delta P1/P2, scope hashes retained. Earlier63/86 stages predate corrective delta and are not summed. Current exact-head full CI and institution queues098/099/105/more R1 work remain; keep PR66 draft. Source/index publication receipt: internship_admission/source_academic_manifest.json.


- LOG-071 current:098/099/105 exact current scoped lists and option/assignment metadata helpers, distinct coordinator creation/binding notices, stale-choice exact-plan guard, post-role-pin current MFA policy. Native current21passed139.56s and notice5passed41.18s overlap; broad56passed1failed363.15s was a lease-reset boundary fixture, corrected explicit-expiry all notice groups15passed73.87s with worker semantics unchanged.9-file current read-only source opinion exit0/no actionable P1/P2, frozen hashes retained. Parentdf87515 full1015 twice549.23s/740.08s does not accept this current source. Registration67/65 of132 is registration only,0015/124 unchanged; latest CI/source pin and detailed106/107/108/full R1 remain. See backend/ACADEMIC_VIEWS.md, source_academic_views_manifest and current handoff.


## EDU-CODEX-API107 / LOG-073 - exact revision academic feedback

- Holat: Tekshiruvda, writer draft publication/current-head full CI; mas'ul Codex,
  read-only source/test reviewer Copilot CLI. Issue67/API108 hali ochiq.
- Fayllar: API2, DB metadata/storage2, service2, forward0016; tests/helpers9,
  backend/ACADEMIC_REVIEWS.md, academic_reviews evidence/source_manifest va4 journals.
- Qabul: original personally accepted Teacher exact plan/revision, current
  session/MFA after waits, nonce conflict/replay/concurrency, immutable original
  history/proof/receipt, SQL/audit/upgrade rollback. Native37 current runtime and
  latest4 observed delta passed, preserved red/fixture stages not hidden. All16
  source/test blobs need current pin; full exact-head CI/current feedback before
  ordinary merge. No official grade/completion/workplace substitution.
- Keyingi: NEXT.md legacy acceptance notice probe, API121 durable privileged flags,
  source-consistent API108 nonofficial conclusion, remaining original R1 and pilot
  acceptance. Registration69/63 is not functional percentage or pilot acceptance.


## EDU-CODEX-LEGACY-NOTICE / LOG-074 - Issue70

- Holat: Jarayonda; parent PR69/2928425 exact CI hali ishlamoqda, qabul emas.
- Mas'ul Codex; keyingi Copilot source review faqat o'qish. Fayllar:
  academic_notices.py, test_academic_legacy_notices.py, legacy_academic_notices
  dalil/hujjatlari va root journals/handoff. Boshqa writer kodi muzlatilgan.
- Maqsad: retained legacy assignmentga yangi actual personal exact-plan consent
  berilganda local candidate notice worker orqali ishlashini birinchi actual
  populated HTTP/worker test bilan ko'rsatish; tasdiqlangan xatoni tor tuzatish.
- Qabul: receipt replay/logout/own minimum inbox, forged legacy nomination deny,
  worker atomic failure/fence/retry, current PUBLIC regressions, source pins va
  matching-head full CI. Reja: legacy_academic_notices/PLAN.md. No live/grade/
  signature/completion/pilot acceptance. Issue67/API108 va full R1 ochiq.


## OPS-CODEX-FLAGS / LOG-076 - Issue72, isolated draft phase

- Holat Jarayonda. AGY003 owns ONLY new0017_feature_flag_administration.py,
  db/feature_flag_admin.py, services/feature_flag_admin.py and security/
  test_feature_flag_admin_api121.py in its agent worktree. Codex owns shared
  storage/router/private middleware/operations/old-RAM helper integration.
- Actual requested coding model claude-sonnet-5-5-high; model receipt must be
  checked, no model identity inferred. No phase1 native HTTP claim; compile only.
- Qabul: current real ADMIN/MFA/expiry, missing-row/cross-code observed locks,
  immutable legacy initial snapshots, exact event/state/receipt/audit, protected/
  R2/paid alias disabled, UTC snapshots, actual populated rollback and full exact
  integration-target CI. Proposed2 helpers/127 tables are not measured yet.
- PR71 parent has separate pending CI; no main merge. Keep current feature70
  source frozen remotely. When integration accepts it, create root Issue72 branch
  from actual integration, preserving these live notes; verify/copy agent owned
  diff and Codex wiring without reverting another writer. Full R1 remains active.

## PLACEMENT-ANTIGRAVITY-API049 / LOG-086 - Issue80, PR81: Placement Completion Requests & Two-Sided Closure

- Holat: Bajarildi va qabul qilindi. PR #81 `integration/r1-agent-collaboration`ga
  squash merge qilindi (commit: `278a5d243e38d5ab6da65a18821346321940c0a9`),
  Issue #80 yopildi. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6`.
- Mas'ul: Antigravity (Q016 master succession ostida); peer reviews: GitHub Copilot CLI
  va OpenCode CLI (ikkalasi ham approved/passed).
- Foydalanilgan yangiliklar:
  * Alembic migration `0019_placement_completions`: `flexbridge.placement_completion_requests`
    table ('PENDING_HOST', 'PENDING_CANDIDATE', 'COMPLETED', 'REJECTED', 'SUPERSEDED'),
    `guard_placement_start()` trigger funksiyasi yangilandi (`COMPLETION_REQUESTED -> ACTIVE`
    rejeksiyada qaytishga ruxsat, 0015 academic validation to'liq saqlangan).
  * `PlacementCompletionService` (API-049 / CAP-022):
    - Oracle probing himoyasi: authorization check terms versiyasi tekshiruvidan oldin bajariladi.
    - Idempotency replay xavfsizligi: status prekonditsiyalaridan oldin tekshiriladi, client
      retries completed placement uchun xatosiz replay beradi.
    - CTE izolyatsiyasi: `submitted_logs` orqali daqiqalar aggregation qilinadi, ko'p reviewlar
      bilan Cartesian ko'payish xavfi bartaraf etildi.
    - Ikki tomonlama rozilik: Candidate va Host/Mentor ikkalasi tasdiqlaganda `COMPLETED`,
      rad etilganda barcha avvalgi kutuvchi so'rovlar `SUPERSEDED` bo'lib, placement `ACTIVE`ga qaytadi.
  * Endpoint: `POST /api/v1/placements/{placement_id}/completion-requests`.
- Testlar: `test_placement_completion_api049.py` 11/11 passed, jami 55/55 migration/regression passed.
  GitHub Actions CI (`backend` va `protocol`) to'liq yashil.


## PLACEMENT-ANTIGRAVITY-API052 / LOG-087 - Issue #82: Single Placement Report Export (API-052 / CAP-026)

- **Holat**: Bajarildi va integratsiya qilindi (PR #83 merged into `integration/r1-agent-collaboration` commit `c8d7f8d748ee5b1f688a8dc40a698cd8335e079e`). Branch `feature/82-placement-report-exports`, base `integration/r1-agent-collaboration`. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork (Milestone 1 Worker & Challengers, Milestone 2 Worker & Reviewers).
- **Qilingan ishlar va yechimlar**:
  * **Actor Resolution Precedence Fix (Issue #82)**:
    `backend/app/services/placement_export.py:resolve_export_actor` funksiyasida tashkiliy vakolat (`org_authority` tekshiruvi: `'OWNER'`, `'HOST_COORDINATOR'`, `'HR'`) mentorlik tekshiruvidan oldinga o'tkazildi. Bu dual-role host egalarining xatolik bilan `'MENTOR'` deb tan olinishini to'liq bartaraf etdi va ularni qonuniy ravishda `'HOST'` sifatida resolve bo'lishini ta'minladi. Mustaqil mentorlar esa `'MENTOR'` bo'lib qoladi.
  * **Alembic Migration `0020_placement_exports`**:
    `flexbridge.placement_exports` jadvali va uning indekslari (`(placement_id, created_at DESC)` va unique `(placement_id, idempotency_key)`) yaratildi. Jami runtime jadvallar soni 130 taga yetdi.
  * **Endpoint & Servis**:
    `POST /api/v1/placements/{placement_id}/exports` implementatsiya qilindi. PDF va JSON formatlari qo'llab-quvvatlandi.
  * **Files & Audit integratsiyasi**:
    Fayllar `flexbridge.files` jadvalida `retention_class='PRIVATE_EXPORT_FILE'` va 24 soatlik amal qilish muddati bilan saqlanadi (DB-018). Har bir eksport amali `flexbridge.audit_events` jadvaliga `action='REPORT_EXPORT'` bilan atomik yoziladi (DB-089).
  * **Xavfsizlik & Idempotentlik**:
    Oracle probing oldini oluvchi priority authorization, actor-bound idempotent replay (begona actor uchun 403, farqli payload uchun 409), va rasmiy ogohlantiruvchi diskleymer (`CAP-026`).
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 11/11 contract & security testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_placement_exports_api052.py`).
  * 22/22 adversarial stress va multi-tenant izolyatsiya testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_placement_exports_adversarial.py`).
  * 1/1 migratsiya regressiya testi muvaffaqiyatli o'tdi (130 ta jadval tekshiruvi, `test_actual_migration_and_constraints`).
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.108 review: `reviews/2026-11-10/placement_exports/COPILOT_REVIEW.md` (host-owner resolution fix tasdiqlandi; lifecycle/presigned-url tavsiyalari qayd etildi).
  * OpenCode CLI 1.18.29 & Peer Review: `reviews/2026-11-10/placement_exports/OPENCODE_REVIEW.md` (5-axis bo'yicha tasdiqlandi).
  * Review sintezi: `reviews/2026-11-10/placement_exports/REVIEW_SUMMARY.md`.


## PLACEMENT-ANTIGRAVITY-API053 / LOG-088 - Issue #84: Single Placement Diary Logs View (API-053 / CAP-022 / PG-022.S01)

- **Holat**: Bajarildi va to'liq tasdiqlandi (PR ochish va integratsiyaga tayyor). Branch `feature/84-placement-diary-logs`, base `integration/r1-agent-collaboration`. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork & Autonomous Execution.
- **Qilingan ishlar va yechimlar**:
  * **Servis (`backend/app/services/placement_logs.py`)**:
    `PlacementLogsService.get_placement_logs_api_053` metodi yaratildi:
    - Multi-stakeholder vakolat tekshiruvi: Candidate, Host Organization (`OWNER`, `HOST_COORDINATOR`, `HR`), Workplace Mentor, Academic Teacher, Institutional Coordinator.
    - Qoralama (Draft) maxfiyligi: Faqat nomzod o'zining `DRAFT` va `SUBMITTED` loglarini ko'ra oladi; boshqa barcha manfaatdor tomonlar faqat `SUBMITTED` loglarni ko'radi.
    - Anti-probing & Oracle himoyasi: Begona yoki ruxsatsiz rollar `status=DRAFT` bo'yicha qidirganda xatolik berilmaydi, bo'sh sahifa (`total: 0, items: []`) qaytariladi.
    - Yuqori unumdorlik (Anti-N+1): Bitta joinli so'rov orqali `daily_logs` va `log_revisions` olinadi; vazifalar va taqrizlar `IN (...)` hamda korrelyatsiyalangan skalyar subquery orqali paketlab olinadi.
    - Filtrlash va sahifalash: `from_date`, `to_date`, `status`, `page`, `page_size`, `include_tasks`, `include_reviews` to'liq nazorat qilinadi (422 xatolar tekshiruvi bilan).
  * **FastAPI Endpoint (`backend/app/api/v1/placements.py`)**:
    `GET /api/v1/placements/{placement_id}/logs` yo'nalishi ulandi.
  * **Delegatsiya interfeysi (`backend/app/services/internship_logs.py`)**:
    `InternshipLogService.get_placement_logs_api_053` yo'naltiruvchi metodi qo'shildi.
  * **Kanonik marshrutlar xaritasi (`backend/app/api/v1/canonical_routes.py`)**:
    `API-053` docstringga qayd etildi.
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 15/15 shartnoma va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_placement_logs_api053.py`).
  * 5/5 adversarial va SQL injection testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_placement_logs_adversarial.py`).
  * 130 ta jadval schema regressiyasi 100% buzilmaganligi tasdiqlandi.
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.109 review: `reviews/2026-11-10/placement_logs/COPILOT_REVIEW.md` (0 xavfsizlik zaifligi, High confidence).
  * OpenCode CLI 1.18.29 & Peer Review: `reviews/2026-11-10/placement_logs/OPENCODE_REVIEW.md` (5-axis bo'yicha tasdiqlandi).
  * Review sintezi: `reviews/2026-11-10/placement_logs/REVIEW_SUMMARY.md`.

## DIARY-ANTIGRAVITY-API055 - Task Entry Evidence Attachment (Issue #86)

- **Holat**: Bajarildi va to'liq tasdiqlandi. Branch `feature/86-log-entry-evidence`, base `integration/r1-agent-collaboration`. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork & Autonomous Execution.
- **Qilingan ishlar va yechimlar**:
  * **Servis (`backend/app/services/internship_logs.py`)**:
    - `attach_task_evidence_api_055`: Topshiriq dalili (evidence) biriktirish metodi yaratildi.
    - Konkurentlik himoyasi: `daily_logs`, `log_revisions`, va `log_task_entries` jadvallari bitta so'rovda `.with_for_update(of=(t_dl, t_rev, t_te))` orqali qulflanadi (API-056 topshirish bilan race condition to'liq bartaraf qilindi).
    - Eski qoralama himoyasi: faqat amaldagi qoralamaga dalil qo'shish mumkin (`current_revision_id == revision_id`); eskirgan qoralama versiyalarga dalil qo'shish 409 xatosi bilan to'siladi.
    - Xavfsiz fayl tekshiruvi: faqat antivirus va PDF strukturasi tekshiruvidan o'tgan toza (`scan_status == 'CLEAN'`) va muallifga tegishli fayllar qabul qilinadi (`PENDING_SCAN` va `QUARANTINED` 422 bilan rad etiladi).
    - Maxfiylik segregatsiyasi: o'qituvchilar va koordinatorlarga faqat akademik auditoriyaga ruxsat berilgan dalillar (`HOST_AND_ACADEMIC`, `ACADEMIC_ONLY`, `PUBLIC`) ko'rsatiladi; korxona ichki maxfiy dalillari (`HOST_ONLY`, `PRIVATE_HOST_EVIDENCE`) akademik foydalanuvchilardan to'liq yashiriladi.
    - `get_task_entry_evidence_api_055`: Foydalanuvchi roliga qarab filtrlangan dalillar ro'yxatini qaytaradi.
  * **Kanonik marshrutlar (`backend/app/api/v1/canonical_routes.py`)**:
    - `POST /api/v1/log-entries/{id}/evidence` (API-055, status 201).
    - `GET /api/v1/log-entries/{id}/evidence` (dalillar ro'yxati va umumiy soni).
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 16/16 shartnoma va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_log_evidence_api055.py`).
  * 6/6 adversarial va SQL injection testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_log_evidence_adversarial.py`).
  * 20/20 API-053 regressiyalari to'liq o'tdi.
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.109: Ikkita muhim masala aniqlandi (lock tartibi konkurentligi va fail-closed maxfiylik filtrlash), ikkalasi ham to'liq tuzatildi va testlar bilan isbotlandi (`reviews/2026-11-10/log_evidence/COPILOT_REVIEW.md`).
  * OpenCode CLI & Peer Review: 5-axis bo'yicha to'liq tasdiqlandi (`reviews/2026-11-10/log_evidence/OPENCODE_REVIEW.md`).
  * Review sintezi: `reviews/2026-11-10/log_evidence/REVIEW_SUMMARY.md`.

## DIARY-ANTIGRAVITY-API057 - Personal Ratings View & Double-Blind Anti-Retaliation (Issue #88)

- **Holat**: Bajarildi va to'liq tasdiqlandi. Branch `feature/88-user-ratings-view`, base `integration/r1-agent-collaboration`. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork & Autonomous Execution.
- **Qilingan ishlar va yechimlar**:
  * **Servis (`backend/app/services/user_ratings.py`)**:
    - `get_my_ratings_api_057`: Foydalanuvchining shaxsiy baholari, agregati, berilgan va olingan baholari ko'rinishi yaratildi.
    - $n < 5$ Maxfiylik chegarasi (`AC-023` / RAT-03): $n < 5$ holatida umumiy ball yashiriladi (`score: null`, `score_status: "WITHHELD_INSUFFICIENT_SAMPLE"`), bu orqali oz sonli amaliyotlarda baholovchi shaxsini fosh qilish xavfi yo'qotildi.
    - Baholanmagan vs Nol farqi (`AC-023`): Yangi foydalanuvchilar uchun noto'g'ri 0.0 o'rniga `sample_size: 0`, `score: null`, `score_status: "UNRATED"` qaytariladi.
    - Ikki tomonlama 14-kunlik Double-Blind himoyasi (`AC-024` / RAT-04): 14-kunlik o'zaro baholash oynasida olingan baholar uchun baholovchi shaxsi (`rater_id: None`) va matnli izoh (`comment: None`) yashiriladi (`status: "BLINDED_PENDING_WINDOW"`). Muddat tugagach, to'liq ma'lumot ochiladi.
    - O'z baholari va munosib munosabatlar (`AC-022`): Foydalanuvchi o'zi yozgan baholarni to'liq ko'radi va yakunlangan (`COMPLETED`) amaliyotlar munosib munosabat sifatida ko'rsatiladi.
  * **Kanonik marshrutlar (`backend/app/api/v1/canonical_routes.py`)**:
    - `GET /api/v1/me/ratings` (API-057, status 200).
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 9/9 shartnoma va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_user_ratings_api057.py`).
  * 5/5 adversarial va cross-user izolyatsiya testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_user_ratings_adversarial.py`).
  * 37/37 API-053 va API-055 regressiyalari to'liq o'tdi. Jami 51/51 test yashil.
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.109: APPROVED (`reviews/2026-11-10/user_ratings/COPILOT_REVIEW.md`).
  * OpenCode Peer Review: 5-axis bo'yicha to'liq tasdiqlandi (`reviews/2026-11-10/user_ratings/OPENCODE_REVIEW.md`).
  * Review sintezi: `reviews/2026-11-10/user_ratings/REVIEW_SUMMARY.md`.

## DIARY-ANTIGRAVITY-API058 - Rating Appeal Submission (Issue #90)

- **Holat**: Bajarildi va to'liq tasdiqlandi. Branch `feature/90-rating-appeals`, base `integration/r1-agent-collaboration`. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork & Autonomous Execution.
- **Qilingan ishlar va yechimlar**:
  * **Servis (`backend/app/services/user_ratings.py`)**:
    - `submit_rating_appeal_api_058`: Baholashga rasmiy e'tiroz (appeal) berish metodi amalga oshirildi.
    - Baho tomoni vakolati (`AC-025`): Faqat baholangan foydalanuvchi (`target_user_id`), baholovchi (`rater_id`), baholangan korxona vakili yoki platforma moderatori e'tiroz bera oladi. Begona uchinchi shaxslar 403 Forbidden bilan to'siladi.
    - 14-kunlik e'tiroz oynasi (`AC-025` / RAT-05): Baho nashr qilingan / ochilgan vaqtdan boshlab 14 kalendar kun davomida e'tiroz berish mumkin. Muddat o'tgach, 422 Unprocessable Entity xatosi qaytariladi.
    - Moderatsiya navbati va mustaqil ko'rib chiqish (`DB-078`, `AC-028`): E'tiroz `moderation_cases` jadvaliga navbatga qo'yiladi. Ko'rib chiquvchi o'z-o'zini tasdiqlashi (appellant yoki rater bo'lishi) qat'iyan taqiqlanadi (`APPEAL_REVIEWER_CONFLICT` 403).
    - Dublikatdan himoya: Bir xil sabab bilan qayta murojaat qilinganda idempotent 200/201 javob qaytariladi; ko'rib chiqilayotgan e'tiroz ustiga boshqa sabab bilan murojaat 409 Conflict bilan to'siladi.
    - Agregatni qayta hisoblash ($n < 5$ yashirish): E'tiroz berilgan baho `UNDER_APPEAL` holatiga o'tkazilib, aktiv agregatdan chiqariladi. Agar qolgan toza baholar soni 5 tadan kamayib ketsa ($n < 5$), umumiy ball darhol yashiriladi (`WITHHELD_INSUFFICIENT_SAMPLE`).
    - Audit jurnali: Har bir e'tiroz yuborilishi va hal qilinishi `AppendOnlyAuditStore` orqali o'zgarmas `audit_events` jadvaliga yoziladi.
  * **Kanonik marshrutlar (`backend/app/api/v1/canonical_routes.py`)**:
    - `POST /api/v1/ratings/{id}/appeals` (API-058, status 201).
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 9/9 shartnoma va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_rating_appeals_api058.py`).
  * 6/6 adversarial va chegara testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_rating_appeals_adversarial.py`).
  * 29/29 butun reyting sohasi (API-057 va API-058) regressiya testlari to'liq o'tdi (153.43s).
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.109: APPROVED (`reviews/2026-11-10/rating_appeals/COPILOT_REVIEW.md`).
  * OpenCode Peer Review: 5-axis bo'yicha to'liq tasdiqlandi (`reviews/2026-11-10/rating_appeals/OPENCODE_REVIEW.md`).
  * Review sintezi: `reviews/2026-11-10/rating_appeals/REVIEW_SUMMARY.md`.

## DIARY-ANTIGRAVITY-API059 - User Notification Preferences (Issue #92)

- **Holat**: Bajarildi va to'liq tasdiqlandi. Branch `feature/92-notification-preferences`, base `integration/r1-agent-collaboration`. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork & Autonomous Execution.
- **Qilingan ishlar va yechimlar**:
  * **Servis (`backend/app/services/notification_preferences.py`)**:
    - `get_preferences` va `update_preferences_api_059`: Foydalanuvchi bildirishnoma sozlamalarini ko'rish va yangilash xizmati yaratildi.
    - Tanqidiy yetkazib berish himoyasi (`AC-030` / OPS-01): `TRANSACTIONAL` va `SECURITY` bildirishnomalarini barcha kanallarda butunlay o'chirib qo'yish qat'iyan taqiqlandi (kamida bitta kanal ochiq qolishi shart). Hamma kanallarni o'chirishga urinish 422 Unprocessable Entity (`TRANSACTIONAL_NOTIFICATION_CANNOT_BE_DISABLED`) bilan to'siladi.
    - Huquqiy rozilik qaydi (`DB-011` / DB-085): Marketing bildirishnomalari (`purpose == 'MARKETING'`) o'zgartirilganda o'zgarmas `consent_events` jadvaliga `action: GRANTED` yoki `action: REVOKED` yozuvi saqlanadi va `consent_event_id` bog'lanadi.
    - Tizim standartlarini birlashtirish: Baza jadvalida hali yaratilmagan kanallar uchun standart xavfsiz sozlamalar birlashtirib qaytariladi.
    - Audit jurnali: Har bir o'zgarish `AppendOnlyAuditStore` orqali `NOTIFICATION_PREFERENCES_UPDATED` voqeasi bilan qayd etiladi.
  * **Kanonik marshrutlar (`backend/app/api/v1/canonical_routes.py`)**:
    - `PUT /api/v1/me/notification-preferences` (API-059, status 200).
    - `GET /api/v1/me/notification-preferences` (API-059, status 200).
  * **Test shartnomalari (`backend/tests/security/test_contracts.py`)**:
    - Amalga oshirilmagan shartnoma tekshiruvi `API-062` (`POST /api/v1/me/privacy-requests`) ga yo'naltirilib, 501 regressiya tekshiruvi saqlab qolindi.
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 8/8 shartnoma va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_notification_preferences_api059.py`).
  * 6/6 adversarial va chegara testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_notification_preferences_adversarial.py`).
  * 16/16 shartnoma regressiya testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_contracts.py`).
  * Jami 48/48 test yashil.
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.109: APPROVED (`reviews/2026-11-10/notification_preferences/COPILOT_REVIEW.md`).
  * OpenCode Peer Review: 5-axis bo'yicha to'liq tasdiqlandi (`reviews/2026-11-10/notification_preferences/OPENCODE_REVIEW.md`).
  * Review sintezi: `reviews/2026-11-10/notification_preferences/REVIEW_SUMMARY.md`.

## DIARY-ANTIGRAVITY-API062 - User Privacy Requests (Issue #94)

- **Holat**: Bajarildi va to'liq tasdiqlandi. Branch `feature/94-privacy-requests`, base `integration/r1-agent-collaboration`. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork & Autonomous Execution.
- **Qilingan ishlar va yechimlar**:
  * **Servis (`backend/app/services/privacy.py`)**:
    - `create_privacy_request_api_062` va `get_my_privacy_requests`: Foydalanuvchi ma'lumotlariga oid so'rovlarni (eksport, o'chirish, to'g'rilash) yuborish va ko'rish xizmati yaratildi.
    - Legal Hold tekshiruvi (`AC-031` / DB-084): Ma'lumotlarni o'chirish (`DELETE`) so'ralganda faol sud yoki moderatsiya cheklovi (`legal_holds`) mavjud bo'lsa, o'chirish rad etiladi (422 Unprocessable Entity `LEGAL_HOLD_ACTIVE`). Eksport so'rovi esa ochiq qoladi.
    - Dublikatdan himoya: Bir xil turdagi so'rov `PENDING` yoki `IN_PROGRESS` holatida turganda yangi so'rov 409 Conflict (`PRIVACY_REQUEST_ALREADY_PENDING`) bilan to'siladi.
    - Qonuniy muddat hisobi: Qonuniy 30-kunlik ijro muddati (`due_at = created_at + 30 kun`) avtomatik belgilanadi.
    - Audit jurnali: Har bir so'rov `AppendOnlyAuditStore` orqali `PRIVACY_REQUEST_CREATED` voqeasi bilan qayd etiladi.
  * **Kanonik marshrutlar (`backend/app/api/v1/canonical_routes.py`)**:
    - `POST /api/v1/me/privacy-requests` (API-062, status 201).
    - `GET /api/v1/me/privacy-requests` (API-062, status 200).
  * **Test shartnomalari (`backend/tests/security/test_contracts.py`)**:
    - Amalga oshirilmagan shartnoma tekshiruvi `API-063` (`GET /api/v1/me/support-tickets`) ga ko'chirildi.
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 8/8 shartnoma va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_privacy_requests_api062.py`).
  * 6/6 adversarial va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_privacy_requests_adversarial.py`).
  * 16/16 shartnoma regressiya testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_contracts.py`).
  * 8/8 bildirishnoma sozlamalari regressiya testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_notification_preferences_api059.py`).
  * Jami 38/38 test yashil (237.84s).
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.109: APPROVED (`reviews/2026-11-10/privacy_requests/COPILOT_REVIEW.md`).
  * OpenCode Peer Review: 5-axis bo'yicha to'liq tasdiqlandi (`reviews/2026-11-10/privacy_requests/OPENCODE_REVIEW.md`).
  * Review sintezi: `reviews/2026-11-10/privacy_requests/REVIEW_SUMMARY.md`.

## DIARY-ANTIGRAVITY-API063-064 - User Support Tickets & Messaging (Issue #96)

- **Holat**: Bajarildi va to'liq tasdiqlandi. Branch `feature/96-support-tickets`, base `integration/r1-agent-collaboration`. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork & Autonomous Execution.
- **Qilingan ishlar va yechimlar**:
  * **Servis (`backend/app/services/support_tickets.py`)**:
    - `create_ticket`, `get_my_tickets`, `post_message` va `get_ticket_messages` metodlari amalga oshirildi.
    - Ichki qaydlar himoyasi (`AC-032` / DB-081): Oddiy foydalanuvchilar ichki xizmat qaydlarini (`internal = True`) ko'ra olmaydi va yoza olmaydi. Operatorlar va adminlar esa to'liq ichki qaydlarni boshqara oladi.
    - Avtomatik SLA hisobi: Muhimlik darajasiga ko'ra birinchi javob muddati (`first_response_due_at`: URGENT 4h, HIGH 12h, NORMAL 24h, LOW 48h) avtomatik belgilanadi.
    - Holatlar almashinuvi: Foydalanuvchi javob yozganda status `PENDING_SUPPORT`, xodim javob yozganda `PENDING_USER` holatiga o'tadi. Yopilgan (`CLOSED`) ticketga yangi xabar yozish 409 Conflict bilan to'siladi.
    - Anti-N+1 so'rovlar: Xabarlar soni skaljar subquery orqali bir martalik so'rovda hisoblanadi.
    - Audit jurnali: Har bir yangi ticket va xabar `AppendOnlyAuditStore` orqali `audit_events` jadvaliga yoziladi.
  * **Kanonik marshrutlar (`backend/app/api/v1/canonical_routes.py`)**:
    - `GET /api/v1/me/support-tickets` (API-063, status 200).
    - `POST /api/v1/me/support-tickets` (status 201).
    - `POST /api/v1/support-tickets/{id}/messages` (API-064, status 201).
    - `GET /api/v1/support-tickets/{id}/messages` (status 200).
  * **Test shartnomalari (`backend/tests/security/test_contracts.py`)**:
    - Amalga oshirilmagan shartnoma tekshiruvi `API-068` (`GET /api/v1/organizations/{org}/entitlements`) ga ko'chirildi.
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 8/8 shartnoma va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_support_tickets_api063_064.py`).
  * 6/6 adversarial va chegara testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_support_tickets_adversarial.py`).
  * 16/16 shartnoma regressiya testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_contracts.py`).
  * 14/14 maxfiylik regressiya testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_privacy_requests_api062.py`, `test_privacy_requests_adversarial.py`).
  * Jami 44/44 test yashil.
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.109: APPROVED (`reviews/2026-11-10/support_tickets/COPILOT_REVIEW.md`).
  * OpenCode Peer Review: 5-axis bo'yicha to'liq tasdiqlandi (`reviews/2026-11-10/support_tickets/OPENCODE_REVIEW.md`).
  * Review sintezi: `reviews/2026-11-10/support_tickets/REVIEW_SUMMARY.md`.


## DIARY-ANTIGRAVITY-API004-037-038 - Candidate Saved Opportunities (Issue #98)

- **Holat**: Bajarildi va to'liq tasdiqlandi. Branch `feature/98-saved-opportunities`, base `integration/r1-agent-collaboration`. `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork & Autonomous Execution.
- **Qilingan ishlar va yechimlar**:
  * **Servis (`backend/app/services/saved_opportunities.py`)**:
    - `save_opportunity`, `get_my_saved_opportunities` va `delete_saved_opportunity` metodlari amalga oshirildi.
    - Nomzod izolyatsiyasi: Faqat nomzod profili mavjud foydalanuvchilar (`candidate_id_for`) e'lon saqlay oladi; boshqa nomzod nomidan saqlash (`CANDIDATE_ACCESS_DENIED`) yoki boshqaning saqlangan e'lonini o'chirish (`SAVED_OPPORTUNITY_ACCESS_DENIED`) 403 bilan qat'iy to'siladi.
    - Idempotentlik va Toggle (`API-004`): Bir xil e'lonni qayta saqlash xatosiz mavjud yozuvni qaytaradi (200 OK). `toggle=True` yuborilganda esa mavjud bo'lsa o'chiradi (200 OK), bo'lmasa saqlaydi (201 Created).
    - Yopilgan e'lon statusi saqlanishi (`API-037` / CAP-006): Saqlangan e'lonlar ro'yxatida e'lonning original holati (`CLOSED`, `ARCHIVED`) va `is_closed` boolean belgisi ko'rsatiladi.
    - Idempotent o'chirish (`API-038`): `saved_opportunities.id` yoki `opportunity_id` orqali o'chirishni qo'llab-quvvatlaydi; takroriy o'chirish 204 No Content qaytaradi (`repeat204`).
    - Baza va Audit: `flexbridge.saved_opportunities` (DB-040) jadvaliga yoziladi, har bir amal `AppendOnlyAuditStore` orqali `audit_events` jadvaliga qayd etiladi.
  * **Kanonik marshrutlar (`backend/app/api/v1/canonical_routes.py`)**:
    - `POST /api/v1/saved-opportunities` (API-004, status 201/200).
    - `GET /api/v1/me/saved-opportunities` (API-037, status 200).
    - `DELETE /api/v1/me/saved-opportunities/{id}` (API-038, status 204).
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 9/9 shartnoma va funksional testlar muvaffaqiyatli o'tdi (`backend/tests/security/test_saved_opportunities_api004_037_038.py`).
  * 7/7 adversarial va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_saved_opportunities_adversarial.py`).
  * 40/40 kanonik regressiya testlari muvaffaqiyatli o'tdi (`test_contracts.py`, `test_notification_preferences_api059.py`, `test_privacy_requests_api062.py`, `test_support_tickets_api063_064.py`).
  * Jami 56/56 test yashil.
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.109: APPROVED (`reviews/2026-11-10/saved_opportunities/COPILOT_REVIEW.md`).
  * OpenCode Peer Review: 5-axis bo'yicha to'liq tasdiqlandi (`reviews/2026-11-10/saved_opportunities/OPENCODE_REVIEW.md`).
  * Review sintezi: `reviews/2026-11-10/saved_opportunities/REVIEW_SUMMARY.md`.


## DIARY-ANTIGRAVITY-API005-031 - Opportunity Details & Notification Inbox (Issue #100)

- **Holat**: Bajarildi va to'liq tasdiqlandi. Branch `feature/100-opportunity-details-and-notifications`, base `integration/r1-agent-collaboration` (PR #101, commit `0b3418c`). `main`/`master` strictly frozen at `764fb98496fa40857acb07844fd09fcafa99b7d6` (Q-015 / AGENTS.md).
- **Mas'ul**: Antigravity Teamwork & Autonomous Execution.
- **Qilingan ishlar va yechimlar**:
  * **E'lon tafsilotlari servisi (`backend/app/services/opportunities.py`)**:
    - `get_opportunity_detail` metodi `API-005` (CAP-001) talablariga mos ravishda to'liq amalga oshirildi.
    - Ochiqlik chegaralari: `PUBLISHED` va `CLOSED` e'lonlar hamma uchun (mehmonlar `GUEST` va nomzodlar) ochiq. Qoralamalar (`DRAFT`, `PENDING_MODERATION`, `ARCHIVED`) faqat tegishli tashkilot a'zolari (`OWNER`, `HR`, `HOST_COORDINATOR`) yoki platforma ma'murlariga (`ADMIN`, `MODERATOR`) ko'rinadi; boshqa barcha so'rovchilar uchun 404 (`OPPORTUNITY_NOT_FOUND`) qaytariladi.
    - O'zgarmas nusxa ma'lumotlari: amaldagi reviziya shartnomasi (`LABOR_PART_TIME`, `CIVIL_GPC`, `INTERNSHIP_AGREEMENT`, `ACADEMIC_TRIPARTITE`), ish tartibi, maosh matritsasi, malaka talablari (`opportunity_skills` + `skills`) va smena jadvallari (`opportunity_shifts`).
    - Haqiqiy vaqt hisobi: `vacancies_available = max(0, capacity - occupied_count) if is_active_open else 0` (yopiq `CLOSED`, to'xtatilgan `PAUSED` yoki muddati o'tgan e'lonlar uchun qat'iy 0). UUID kiritmasi xavfsiz tekshiriladi (404 himoyasi).
    - Marshrut: `GET /api/v1/opportunities/{id}` `backend/app/api/v1/canonical_routes.py` ga `optional_actor_context` bilan ulandi.
  * **Bildirishnomalar inboksi servisi (`backend/app/services/mentor_notices.py`)**:
    - `NotificationService.own` metodi `API-031` (CAP-031) doirasida yaxshilandi.
    - `outerjoin` qo'llanildi: `outbox_events` bilan bog'lanmagan yoki qayta ishlangan bildirishnomalar inboksdan yo'qolib qolmaydi.
    - Bog'langan obyekt identifikatorlari: `opportunity_id`, `application_id`, `ticket_id`, `placement_id` to'liq satr (UUID string) ko'rinishida qaytariladi.
    - Hisoblangan `is_read` (True/False) belgisi va `read_at` vaqti qaytariladi.
    - Keyset kursor paginatsiyasi (`limit`, `after`, `next_after`) kursor xavfsizligi bilan ishlaydi.
- **Test natijalari (Izolyatsiyalangan PostgreSQL 17 test klasterida, `FLEXBRIDGE_TEST_ADMIN_URL` port 55440, pg_live tegilmadi)**:
  * 15/15 shartnoma va funksional testlar muvaffaqiyatli o'tdi (`backend/tests/security/test_opportunity_details_api005.py`).
  * 9/9 bildirishnoma inbosi va paginatsiya testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_notification_inbox_api031.py`).
  * 5/5 e'lon tafsilotlari adversarial va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_opportunity_details_adversarial.py`).
  * 5/5 bildirishnoma inbosi adversarial va xavfsizlik testlari muvaffaqiyatli o'tdi (`backend/tests/security/test_notification_inbox_adversarial.py`).
  * 26/26 kanonik regressiya testlari muvaffaqiyatli o'tdi (`test_mentor_notices.py`, `test_academic_notices.py`, `test_supervision_notices.py`, `test_admission_pagination.py`, `test_saved_opportunities_api004_037_038.py`).
  * Jami 60/60 test yashil.
- **Multi-Agent Code Reviews**:
  * GitHub Copilot CLI 1.0.109: APPROVED (`reviews/2026-11-11/opportunity_and_notifications/COPILOT_REVIEW.md`).
  * OpenCode Peer Review: 5-axis bo'yicha to'liq tasdiqlandi (`reviews/2026-11-11/opportunity_and_notifications/OPENCODE_REVIEW.md`).
  * Review sintezi: `reviews/2026-11-11/opportunity_and_notifications/REVIEW_SUMMARY.md`.
