I’ll trace the nine candidate/availability entry paths and their transaction, actor, lock, and audit
behavior against the specified acceptance criteria, then report only concrete defects or material
gaps.

No concrete source defect found in the nine candidate/availability paths reviewed. The services pass
ActorContext, lock the owner’s profile before checking current user/session state, and—when linking
a CV—lock and validate the owner’s file before the authority check. The private reads render under
the guarded transaction; replacements render before it ends. The legacy availability paths bind the
supplied candidate ID to the locked owner profile and append audit events in the same transaction.
The matching snapshot helpers remain unchanged.

Material acceptance gap (P2, test coverage):
test_current_password_or_sensitive_mfa_actor_retains_scope covers all paths for ordinary PASSWORD
and MODERATOR/MFA actors, but the teacher-only PASSWORD control at
backend/tests/security/test_candidate_authority.py:244 covers only profile GET/PATCH, schedule GET,
and CV linking. It does not exercise skills, either replacement, CV unlink, or either legacy add as
a TEACHER. The shared guard logic makes this a coverage gap, not evidence of a source bug.

This is source analysis only: I did not run tests or independently verify the pinned SHA. The prior
execution results and full-CI status in the prompt remain unverified here; this review does not
certify pilot readiness or the separate skills/matching/application scopes.
