Institution roles previously survived expired, revoked, unaccepted or mismatched
appointments. Auth role labels and scope checks now share one effective-grant
predicate, and existing academic create/revoke/review services recheck the actual
session and current scoped authority after business locks.

All current sensitive roles retain the global MFA requirement, including a teacher
who gains coordinator authority while the request waits on a business lock.
Teacher-only users can use PASSWORD sessions for accepted assignments. Target
teacher authority uses NOWAIT with atomic 409 retry. Current academic
enrollment/agreement/purpose bindings, revision-author/candidate identity,
separation of duties and audit rollback are enforced. No new privileged
intake/grant API or migration is exposed.

Corrected old-source role probes: 8 failed, 1 valid control passed. Initial academic
59 and existing affected authority128 cases passed on native PostgreSQL. Source
review identified further MFA/legacy-author gaps: three probes failed on the prior
runtime, then those three and the ordinary-teacher control passed after the fix.
Final native93 passed273.95s on2c3f2e1; read-only follow-up source review found the
findings resolved and no concrete remaining defect/deadlock. Both complete
PostgreSQL CI runs passed675 tests (418.26s/346.12s) on2c3f2e1. Evidence-only head
checks and matching-head merge follow separately. Full evidence is in
reviews/2026-11-09/institution_authority/HISOBOT.md.
Overlapping runs are not added as distinct coverage. This is a draft, not a
pilot-readiness or legal-document certification claim. API017/096/097 remain
placeholders; canonical handler inventory remains 46 explicit / 86 placeholders.

Closes #53
