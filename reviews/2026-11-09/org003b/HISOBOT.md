# ORG-CODEX-003B — existing OWNER successor va departure

Current-MFA OWNER o'z OWNER grantidan chiqishni so'raydi. Named successor shu
tashkilotdagi mavjud active OWNER bo'lishi, MFA/current verified-contact bilan exact
revisionga rozilik berishi va assigned independent MODERATOR tasdiqlashi kerak.
Faqat requester OWNER grant revoked bo'ladi; membership/staff rollari saqlanadi.
Canonical previous/new membership event, case va audit bir tranzaksiyada.

Original requester/successor grant IDs immutable proposalda pin qilinadi. Grantni
revoke/regrant eski so'rovni qayta faollashtirmaydi; yangi proposal kerak. Dalil revisioni
yangi rozilik talab qiladi. Historical receiptni original participants current MFA bilan
o'qiy oladi; tashkilotga yangi vakolat berilmaydi. Matching retry faqat existing natija.

Joriy dalil:

- Native migration smoke1 passed,4.62s.
- Initial HTTP/race/rollback subset10 passed,1 framework warning,36.51s.
- Kengaytirilgan same module34 passed,1 warning,112.80s: wrong actor/role/org/MFA,
  current authority/contact/security/evidence, privacy, forged generic case/payload,
  parallel retries, opposite transfers va revoke race, immutable history/audit rollback.
- History/security refresh/second-process6 yangi testi passed,1 warning,23.89s. Complete
  collected suite337. Final source bilan umumiy native/CI natija quyida.
- Populated0008->0009:103->105 tables; old addition proof function matni, revoked grant
  va ownership event saqlandi; fresh grant distinct, duplicate active/event mutation
  rad etildi. Ikki initial fixture xatosi (missing MODERATOR catalog va self-granted
  platform role) initial_upgrade.jsonda, migration success deb sanalmadi. Runtime
  constraintlar ularni o'tkazish uchun yumshatilmadi.

003A existing proof function o'zgarmadi. Previous membership bo'lmagan event existing
triggerdan; previous membership bo'lgani dedicated transfer proofdan o'tadi. Transfer
proof exact source revoked_at/effective_at, original current successor, case/revision/
latest consent va independent reviewer metadata'ni tekshiradi. SQL relational integrity;
actual bearer/MFA/contact HMAC APIda, direct DB writers trusted.

Copilot read-only planning review source/prompt asosida exit0 berdi; tashqi plan fayliga
access denied bo'lgan. Pinned284b297 code review ham exit0; confirmed HTTP kamchilik
topilmadi. Second-process xizmat o'qishi HTTP bearer testi emasligi va har bir raw SQL
predicate alohida fault-injection bilan tekshirilmagani assessmentda yozildi. Hech qaysi
model identity mustaqil aniqlanmadi. Implementation Codexda, review test sertifikati emas.

284b297 uchun complete337-test GitHub CI42525017488/42525078474 ikkovi ham successful:
337 passed,1 warning,177.26s/152.69s. Shu source bilan final affected8 native modul
**160 passed**,0 failures/errors/skips,1 warning,566.41s; `affected_junit.xml`.
Native vaqtiga Windows disposable DB cleanup ham kiradi; bu API tezligi benchmarki emas.
Source manifest Git blob SHA256 bilan; contracts inventory46 explicit/86 placeholder,
missing0 va summary shu katalogda. Evidence-only commit uchun final checks/merge qolgan.

TestClient, synthetic role/contact/CLEAN PDF metadata va dedicated disposable native
PostgreSQL ishlatildi. Legal identity, registry, live contact delivery, browser yoki
production/DR certification emas.003C inaccessible-owner recovery alohida qoladi;
EDU va boshqa86 canonical placeholder hali ochiq. **pilot_ready false**.
