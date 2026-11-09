An initial moderation request could pass its role preflight, wait for the opportunity and still write a decision after session/account/MFA/role authority had been revoked. Eight changed-state regressions reproduced the stale201 result; actual opportunity-lock tests use independent PostgreSQL connections.

Pass the real ActorContext into the service and acquire existing moderator_authority after locking the opportunity, before reading its revision or making policy/write effects. Preserve the existing global MODERATOR MFA policy, self-author/DRAFT checks, case/action/audit atomicity and appeal provenance. Database security/role changes serialize with the held authority; expiry is evaluated at the post-lock authorization boundary.

Native22 new tests passed (87.69s), covering completed changes, actual business-lock waits, opposite session/MFA/grant commit serialization, current authority controls, concurrent single effect, write/audit rollback and service session/cache boundaries. Old moderation/appeal/IAM suites, full502-test CI and pinned source review remain pending. No endpoint, dependency or migration added; canonical46 explicit/86 placeholders and pilotfalse remain. Trusted SQL administrative fixtures are not public provisioning, and live providers/browser/DR are outside this evidence.

Closes #48
