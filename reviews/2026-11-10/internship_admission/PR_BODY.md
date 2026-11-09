Work in progress: internship admission currently accepts ordinary-job placements,
allows general ACTIVE without a mentor, and nominates non-MENTOR staff. Initial
actual HTTP/SQL probes3 failed13.64s; exact evidence is retained.

This first change binds placement intake and mentor nomination to actual current
host account/session/scoped authority after business locks, requires current host
capability and internship kind/contract, and requires a current same-host MENTOR
grant for nomination. Ordinary-job diary creation is also rejected. Valid existing
fixtures now use real internships and actual-session actors.

Initial guards2 passed/1 failed11.21s: kind and role denials are fixed; personally
accepted mentor/activation remains an open failing regression. Actual logout waits
and formal Teacher PASSWORD control3 passed12.79s; selected diary/academic2 passed
10.75s. Counts overlap. This draft does not claim complete CI or admission acceptance.

Still required in this package: forward proof/history migration; versioned terms,
candidate and named mentor acceptance, private own/host/named views, canonical
admission routes and safe activation/cancel/revoke; regrant/replay/concurrency/
rollback/upgrade and full affected/current CI/source review. Academic teacher and
completion follow-on scopes stay explicit in DECISIONS.md. No live pg_live work,
frontend/legal identity/providers/DR or pilot acceptance.

Enrollment PR64/Issue63 merged1b2bbbf after final08b full930 twice541.51s/651.09s.
Final receipts and extra unchanged-source Teacher control are preserved here.

Closes #65
