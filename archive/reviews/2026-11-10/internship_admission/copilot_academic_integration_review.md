No concrete P1 integration defect or missing bearer/auth-scope check found. The academic router is
registered (main.py:163); the shared authentication boundary protects non-public API routes
(main.py:64–88), and the privacy middleware covers the academic endpoints (iam_http.py:14). The
assignment acceptance route is wired through placement admission to the academic service. Ordinary
TEACHER PASSWORD authentication remains consistent with the documented sensitive-role policy.

Unresolved P2 privacy gap: candidate notices for academic viewer changes are explicitly still
pending (ACADEMIC_ADMISSION.md:69–70). The service allows nomination on an ACTIVE placement
(academic_admission.py:165–174); after the old assignment is revoked, a newly nominated teacher can
accept on that active placement (academic_admission.py:218) and review submitted logs
(internship_logs.py:61–75). The nomination path records proof and audit evidence
(academic_admission.py:184–194), but does not issue a candidate notice. This is a notice/oversight
gap, not evidence that an unscoped user can access records: the teacher’s original current authority
and assignment are still checked.

Startup-head caveat: academic tables are registered in storage (storage.py:120–121), and
init_storage() requires revision 0015_academic_admission (storage.py:156–161). That check is reached
through readiness, not an app-start hook (main.py:189–195; readiness.py:8–15). If deployment does
not gate traffic on readiness, an old-schema process could start and then fail on academic requests;
the deployment behavior is not established by these files.

The migration test seeds legacy rows before upgrading to head and compares history across the
upgrade (test_academic_migration.py:53–75); it does not forge LEGACY_IMPORT rows after upgrade.
Lifecycle tests exercise HTTP paths, authority changes, rollback, and current-school choice, but do
not cover viewer-change notices or active-placement reassignment. This is a source review only; I
did not run tests. Imported ACTIVE history preservation and administrative setup metadata do not
establish legal/provider identity or pilot acceptance.

