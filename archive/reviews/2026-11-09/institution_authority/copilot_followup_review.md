The two previously reported defects appear resolved, and I found no concrete remaining defect or
deadlock in the fixes. At the business-authority boundary, review rechecks current sensitive roles
and requires MFA, covering the direct-service dual-role case and a sensitive grant arriving after
HTTP preflight. Review also checks that the submitted revision author owns the placement candidate
before actor authority is evaluated. This does not imply static dual-role HTTP previously bypassed
middleware; it was already blocked there.

Evidence gap: I did not run tests. The new cases and teacher-only control reportedly passed locally,
but full native93 and complete CI remain pending. The imported-author case uses trusted corrupted
fixture data, not evidence of a public mutation path. No pilot attestation or onboarding, admission,
or official-grade API claim is supported.

