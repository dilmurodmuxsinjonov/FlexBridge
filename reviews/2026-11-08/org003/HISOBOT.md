# ORG-CODEX-003A — qo'shimcha OWNER backend tekshiruvi

Existing active staff membershipga OWNER qo'shish uchun current-MFA OWNER so'rovi,
named targetning current-MFA/current verified-contact roziligi va assigned independent
MODERATOR reviewi alohida bajariladi. Rozilik revisionga bog'langan va24h; yangi dalil
yangi rozilik talab qiladi. Req/target/org immutable, role clientdan olinmaydi.

API110ning explicit owner branchi current requester/target authority, account security,
current contact/HMAC, latest consent, exact revision va owned CLEAN evidence'ni tekshiradi.
Bir SQL tranzaksiyada grant, ownership event, case decision va audit yoziladi. Scope
actor/grant/session/contact locklari commitgacha turadi. REJECT, NEEDS_INFO, target decline,
requester cancel va ularning race holatlari OWNER bermaydi. Targetning boshqa staff rollari
saqlanadi. Pending queue va private evidence assigned scope bilan ajratilgan.

Native PostgreSQL tekshiruvlari:

- Initial migration1 va initial flows3 passed; birinchi OWNER onboarding ham regressiyada.
- Security subset24, transaction subset13 va post-review selected3 passed.
- Barcha ta'sirlangan owner/onboarding/invitation/appeal modullari bir yurishda
  **118 passed**,1 framework warning,259.37s; `affected_junit.xml`.
- Oxirgi history-index/NULL-filter qo'shimchasidan keyin migration/invitation follow-up
  **2 passed**,1 warning,9.97s; `history_index_junit.xml`. Bu kichik qo'shimchadan keyin
  butun118 native suite o'zgarmas final snapshotda qayta o'tdi deb ko'rsatilmaydi.
  Final committed complete GitHub295-test CI alohida qayd etiladi.
- Parallel submit/consent/approval single effect; cancel/revoke bilan serialization;
  grant/event/audit failure va deferred proof failure rollback; immutable request/consent/
  evidence/history, revoked grant preservation, duplicate active grant rejection;
  second Python process read. TestClient HTTP va trusted synthetic role/contact/CLEAN-file
  metadata ishlatildi; browser, native API restart yoki live contact delivery deb talqin qilinmaydi.
- Final source uchun fresh0007->0008 populated upgrade:101->103 runtime table,
  revoked grant va ownership event aynan saqlandi, yangi active grant alohida ID,
  duplicate active grant/ownership event mutation bloklandi. `verify_upgrade.py`, `upgrade.json`.
  Bu privileged SQL index probe; HTTP orqali grant yoki legal identity tasdig'i emas.

Actual read-only Copilot CLI review0953ebd detached worktreeda bajarildi (exit0, model
mustaqil aniqlanmadi). HTTP owner bypass topilmadi; invitation reactivation tarixni
yo'qotishi tasdiqlandi va tuzatildi. Fresh invite endi revoked qatorni qayta yozmaydi.
SQL guardga active moderator metadata qo'shildi. Actual MFA va contact HMAC APIda
tekshiriladi; direct database writers trusted. Trigger opaque HTTP callerni autentifikatsiya
qilmaydi va app HMAC keyni bilmaydi. `copilot_code_review.md`/assessment boundaryni ajratadi.

bc6e1d6 uchun complete295 test GitHub CI42502191120da o'tdi. Keyin grantni revoke/regrant
qilganda eski requester so'rovi va target roziligi qayta amal qilishi ikki yangi test bilan
aniqlandi: initial_grant_boundaries_junit.xml,2 failed. Bu295-test yashil natija yangi
ketma-ketliklarni qamramagan. So'rov immutable requester_grant_idga, rozilik exact
target_staff_grant_idga bog'landi; SQL relational proof ham shu grantlarni tekshiradi.
Eski OWNER granti bekor bo'lsa yangi so'rov, staff granti bekor bo'lsa yangi rozilik kerak.
Yangi ruxsat bilan qonuniy qayta davom etish ham tekshirildi:2 passed,11.40s,
grant_boundaries_junit.xml. Final f118e23e2a0d2d48d08a6ad8fd500f5a43bca9d2 uchun
**120 affected passed**,0 failure/error/skip,282.714s (`final_affected_junit.xml`).
Complete GitHub PostgreSQL CI42503498638: **297 passed**,1 warning,190.18s.
PR42 ochildi. Final read-only Copilot delta review f118e23da exit0; tasdiqlangan HTTP
kamchilik topilmadi, invitation replay attribution concern assessmentda saqlandi.
0007->0008 populated upgrade final source bilan yana o'tdi. Birinchi urinish lokal
test server ishlamagani sabab to'xtatildi va muvaffaqiyat deb sanalmadi; dedicated server
tiklangach replay o'tdi. Source manifest Git blob bytes bilan, summary va contracts
inventari shu katalogda. Evidence-only final checks va merge keyingi GitHub dalili.

Current canonical46 explicit /
86 placeholder statistikasi o'zgarmaydi; yangi ownership helperlari bu132 ro'yxatdan tashqari.
Canonical94 table modeli o'zgarmadi; runtime103. Guide: backend/OWNER_ADDITIONS.md.
Transfer/recovery003B, frontend, providers, production DB provisioning, DR va barcha42 AC
hali qabul qilinmagan. **pilot_ready false**.
