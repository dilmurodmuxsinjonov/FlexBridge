Owner file services previously received only user IDs after middleware checks.
A request waiting on its file row could complete202/SCANNING and queue a scan even
after actual logout200. This change passes real ActorContext through initiation,
completion and owner download and rechecks current account/session/auth version,
revocation/expiry and existing current-role MFA inside the guarded transaction.

Owned file business locks precede user/session locks and provider work; initiation
authorizes before presign/insert. The unchanged onboarding account_authority policy
is shared from authority.py. Ordinary PASSWORD/current sensitive MFA, own-file scope,
short exact-version URLs, source/lease fences and provider rollback remain. The
trusted worker continues an already recorded upload after logout independently of
that revoked owner session. No user-ID-only human compatibility bypass.

Validated source370d9c32229f023537ff1cdacc77bc53f8bb3c30 passed complete785-test
Linux PostgreSQL+actual MinIO CI twice: push42697954266 in534.16s and PR42697965001
in458.37s. New27 native passed36.60s; affected storage/EDU72 passed102.01s including
actual S3 logout->scanCLEAN/old token401. Source review exited0, no scoped findings.
Red old-source15, initial invalid self-grant fixture stage, physical wait versus
entry barrier and all source/execution limits are separated in HISOBOT.md. Native
counts overlap; full785 is baseline757+27 new authority+1 new S3 case. Evidence-head
checks follow before matching-head merge.

Issue #61 independently confirms candidate/CV/schedule and legacy availability
session gaps on the same source; it is the next9-path package, not claimed fixed
by785 green tests. AV is explicitly doubled in S3 integration. Separate freshclam/
actual benign-PDF local adapter setup passed; no service/detection/pipeline/live
certification. Docker/WSL admin install remains incomplete. Antigravity handoff
and journals record these limits and exact next work.

No migration/contract/dependency change: runtime0012/111 tables, canonical94 and49
explicit/83 placeholders. No overall pilot or live-provider/legal/DR acceptance.

Closes #59
