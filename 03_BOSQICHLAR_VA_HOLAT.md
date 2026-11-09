# FlexBridge — bosqichlar va bajarilish holati

Yangilangan2026-11-10 - Codex. PR62 mergedb94da5516102ee880f0dd10bd429b95b78ea5b9d/Issue61 closed; final7fb411b full895 CI547.44s/582.45s passed. Issue63 enrollment lifecycle implementation starts on feature/63-enrollment-verification. Accepted runtime0012/111,49 explicit83 placeholder/pilotfalse; proposed0013 not accepted yet. Antigravity handoff current; pg_live stopped02:38, isolated testPG55440 active; Docker/WSL admin install incomplete.

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

- Holat: `Jarayonda`; mas'ul Codex, actual read-only architecture reviewer Copilot CLI exit0. feature/63-enrollment-verification from mergedb94da55. Source-first plan/decisions/review and PR62 final metadata: reviews/2026-11-10/enrollment_verification.
- Doira: canonical027/034 own declaration/submission/history, detail/end/revision helpers; explicit existing moderator queue/claim/detail/file/decision dispatch. Education optional, DECLARED never eligible; current VERIFIED only exact new public approved proof or explicitly captured pre-upgrade VERIFIED imports. Same-case revision/decision history, version-pinned private files, source1-weekday response target, terminal end/withdraw preserving ordinary profile/application/academic history.
- Fayllar: forward0013 and typed enrollment proof metadata, enrollment service/API, academic effective predicate/real-session fixture, operator dispatch/private middleware, migration/lifecycle/security/transaction regressions, backend guide/review artifacts and01/02/03/handoff. Canonical historical94 unchanged; actual runtime helper count after migration test, not assumed acceptance.
- Qabul: actual PG fresh/populated legacy/history/rollback/proof guards; own lifecycle/scopes/flags/current assurance/session waits; independent assigned exact revision review/version checks; replay/concurrency/end-vs-review/audit rollback; old affected suites, complete matching-head CI, pinned actual review and handoff. Legacy origin cannot be inserted after migration; new raw VERIFIED insert/promotion denied. New academic fixtures use real-session enrollment review, no test-only legacy bypass.
- Chegara: roles_for unchanged, broader matching/application eligibility, accepted supervision/teacher assignment/export/signatures and frontend/live identity/providers/DR/pilot remain explicit open scopes. R2 freelance absent. Current63 source not accepted; runtime implementation starts with schema/proof layer.

- LOG-062:0013/schema114 loaded on disposable PG; typed origins/revisions/events/current predicate implemented. Own027/034/detail/revision/end, explicit operator dispatch/private evidence and academic integration prototype connected. Initial schema failures were strict startup-head and fixture issues, all retained. Corrected SQL/proof3 passed17.45s; HTTP lifecycle8 passed24.75s. Actual transaction/security12 passed36.23s. Academic+updated positive63 initial62 passed/1 raw-date fixture rejected237.93s; actual end plus separate expired-enrollment creation test and SQL immutable-date assertion targeted3 passed13.43s. Runtime guard retained; stages overlap. Source/full CI/peer review and remaining acceptance tests pending, not Bajarildi/pilot. Exact history in enrollment_verification/IMPLEMENTATION_NOTES.md.

- LOG-062 follow-up: d36059b prototype/draftPR64, both CI42710013191/42710023813 and isolated actual read-only code review in progress. Later legacy HTTP3 passed35.10s, test-only delta: populated0012 trusted imports with real sessions ->0013 actual own end/replay for current/future verified and pending states, profile/history preserved/no fabricated case. Native counts overlap, full current acceptance pending.
