# REV-002 — Tuzatishlarning mustaqil qayta tekshiruvi

2026-11-07, Asia/Tashkent. Codex. Tekshirilgan commit: `984fec5`; tuzatish commit: `aa8fd9b`.

**Hukm: foydali qisman tuzatishlar bor, lekin R-01..R-13 va FIX-01..14 to'liq yopilmagan. Pilotga qabul qilinmaydi.** `38 passed`, `0/17` va `132/132` natijalari o'z chegarasida qayta tasdiqlandi; ular haqiqiy biznes oqimlari va infratuzilma tayyorligini isbotlamaydi.

## Haqiqiy tekshiruv natijalari

- Toza, alohida SQLite bazada `python -m pytest -q`: **38 passed, 1 warning, 5.18s**.
- Original `reproduce_findings.py` shartlari o'zgartirilmasdan, faqat chiqish fayli yangi papkaga yo'naltirib bajarildi: **17 probe, defects_observed=0**. Original skript semantikasiga ko'ra exit code **1**; bu mahsulot testlari muvaffaqiyatsiz degani emas. U hali "hamma kamchilik kuzatildi" holatini kutadigan diagnostik skript.
- Mustaqil `recheck.py`: **30 tekshiruv — 8 yaxshilanish tasdiqlandi, 22 salbiy ssenariyda kamchilik kuzatildi**. 22 soni 22 ta mustaqil yangi bug degani emas; ayrim ssenariylar bitta ildiz muammoga tegishli.
- Sinovlar yangi sintetik SQLite fayllarida, lokal TestClient, servis fixturelari va alohida Python jarayonlarida bajarildi. PostgreSQL/Redis/MinIO/ClamAV, haqiqiy provider va brauzer oqimi ishga tushirilmadi. Docker/psql buyruqlari tekshiruv shellida topilmadi. Sxema SQLi bu tuzatishda o'zgarmagan; uning avvalgi 17/17 PGlite sinovi qayta bajarilmadi.
- Ilova kodi va original probe shartlari o'zgartirilmadi. Yangi review dalillari hamda 01/03 jurnallar yangilandi.

## Tasdiqlangan yaxshilanishlar

1. Ochiq registerda SUPER_ADMIN rad etiladi (`403`). Biroq barcha kanonik imtiyozli rollar va scope himoyasi yopilmagan.
2. Oddiy payment requesti default holatda PENDING_PROVIDER bo'ladi. Biroq mijoz uni aylanib o'ta oladi.
3. Ketma-ket ikki to'liq refund: birinchi `201`, ikkinchi `409`; jami ceiling qo'shilgan.
4. ACTIVE, lekin muddati o'tgan entitlement publishda `409` oladi.
5. Bir idempotency keyga boshqa summa yuborish `409 IDEMPOTENCY_CONFLICT` oladi.
6. Tutash availability intervallari to'g'ri birlashtiriladi.
7. Parol haqiqatan Argon2id bilan hisoblanadi; mustaqil low-level hisob bilan mosligi tekshirildi.
8. Shu jarayonda breaker OPEN bo'lsa moliyaviy endpoint `503` qaytaradi. Sessiya boshqa jarayonga SQL orqali o'tishi ham mavjud test va original probeda tasdiqlangan.

## Original R-01..R-13 holati

| Band | Hukm | Izoh |
| --- | --- | --- |
| R-01 vakolat | Ochiq | Legacy endpointlar himoyasiz; SUPPORT self-register; step-up soxta; scope chetlab o'tiladi |
| R-02 to'lov | Ochiq | provider_confirmed=true yoki imzosiz callback orqali SUCCEEDED |
| R-03 saqlash | Qisman | User/session SQLga o'tgan; order, refund, fayl va biznes holati hamon dictda; kanonik PostgreSQLga ulanmagan |
| R-04 fayl | Ochiq | Sticky quarantine va ACL taqqoslash qo'shilgan; haqiqiy scan/ombor yo'q, requester_id soxtalashtiriladi |
| R-05 kvota | Qisman | Majburiy contract_type va lokal 5-limit bor; tarifsiz 5 e'lon ochiladi, DB locking yo'q |
| R-06 refund | Qisman | Ketma-ket jami limit bor; haqiqiy approval/scope, atomiklik va parallel himoya yo'q |
| R-07 API/AC | Ochiq | Marshrut imzolari ko'paygan, ko'plab handler faqat OK qaytaradi; request/response va xulq bajarilmagan |
| R-08 kundalik | Qisman | Manfiy daqiqa rad; 0-draft ham rad, begona author submiti va task/overlap qoidalari ochiq |
| R-09 breaker/readiness | Qisman | Umumiy SQL holati va 503 bor; yangi process uni CLOSED qiladi, readiness hali deklarativ |
| R-10 idempotency | Qisman | Fingerprint qo'shilgan; process xotirasida va client actor IDiga bog'langan, durable/atomic emas |
| R-11 tarif muddati | Asosiy tekshiruv tuzatilgan | ACTIVE entitlementning expiry/future/status tekshiruvi bor; boshqa publish bypassi R-05da qoladi |
| R-12 xesh algoritmi | Asosiy tekshiruv tuzatilgan | Argon2id haqiqiy; standart PHC format bilan moslik muammosi alohida quyida |
| R-13 tutash vaqt | Asosiy tekshiruv tuzatilgan | Interval union ishlaydi; butun matching engine to'g'ri degani emas |

## P1 — Paymentni mijozning o'zi tasdiqlay oladi

Manzil: `backend/app/api/v1/billing.py:28`, `:84`; `backend/app/services/billing.py:236`, `:266`; `backend/app/api/v1/canonical_routes.py:90`; `backend/app/services/billing.py:340`.

- Authorization sarlavhasisiz payment bodyga `provider_confirmed:true` yuborildi: **200, SUCCEEDED**, faol entitlement.
- Yangi pending payment uchun webhook bodyda signature umuman berilmadi: **200, SUCCEEDED**.
- Sabab: public request provider_confirmedni servicega uzatadi; webhook requestining signature defaulti `VALID_PROVIDER_WEBHOOK_SIGNATURE`, verifier shu literalni ham qabul qiladi. HMAC siri ham kodda qotirilgan.

Tuzatish: public DTOdan provider_confirmedni olib tashlash; callbackda default/test-bypassni olib tashlash; faqat providerga tegishli tekshirilgan autentifikatsiya; test adapteri production handleriga ta'sir qilmasin. Pul holati haqiqiy transaction/event orqali atomik yangilansin.

## P1 — Auth/scope va MFA to'liq ishlamaydi

Manzil: `backend/app/services/auth.py:31`, `:343`; `backend/app/api/v1/auth.py:81`, `:104`.

- `roles:["SUPPORT"]` bilan ochiq register **201** qaytardi. Kanonik operator roli denylistdan tushib qolgan.
- SQL sessiyaning expires_at qiymati kechagi kunga o'tkazildi; `/auth/me` hali **200**. validate_session expiry vaqtini tekshirmaydi.
- `PATCH /me/security`ga noto'g'ri `000000` kodi yuborildi: **200, step_up_verified:true, totp_enabled:true**. DBdagi TOTP siri esa o'zgarmadi. Endpoint faqat muvaffaqiyatni qaytaradi.
- Legacy `/auth/sessions/{id}/revoke` Authorization talab qilmaydi: soxta actor_id bilan **200**, keyingi haqiqiy `/auth/me` **401** bo'ldi. Canonical owner-checkni eski endpoint orqali chetlash mumkin.

Tuzatish: ochiq registerda aniq allowlist/onboarding; barcha yozuvchi endpointlarga actor+CAP+scope; expiry tekshiruvi; step-upni tekshirish va haqiqiy sozlama yangilashi; legacy routega ham bir xil himoya yoki uni olib tashlash.

## P1 — Yangi jarayon moliyaviy blokirovkani avtomatik ochadi

Manzil: `backend/app/core/circuit_breaker.py:91`.

Natija: asosiy jarayon breakerini OPEN qildi. Xuddi shu DBni ishlatadigan yangi jarayonda `app.main` import qilindi. **OPEN -> CLOSED** va incident maydonlari tozalandi; asosiy jarayon ham CLOSEDni ko'rdi.

Sabab: modul importida shartsiz `_write_breaker_row(state="CLOSED", ...)` bajariladi. Worker restart yoki autoscaling xavfsizlik blokirovkasini o'chiradi.

Tuzatish: faqat satr yo'q bo'lsa boshlang'ich holat yaratish; mavjud OPEN hech qachon startupda reset bo'lmasin. Reset alohida vakolatli ikki tomonli amal, audit va tranzaksiya bilan.

## P1 — 132 marshrut funksional bajarilish emas

Manzil: `backend/app/api/v1/canonical_routes.py:295`, `:321`.

`register_remaining_canonical_model_routes` modeldan handler yaratib, actor/method/path va `status:OK` qaytaradi. CAP, obyekt scopei va biznes amali bajarilmaydi.

Oddiy CANDIDATE tokeni bilan mavjud bo'lmagan refund uchun `/operator/refunds/does-not-exist/approve` chaqirildi: **200, API-116, status:OK**. Bu real refund bajarilgani emas; bajarilmagan approvalni muvaffaqiyatli ko'rsatadigan placeholder.

Shuning uchun 132/132 method/path mosligi backend kontraktlari bajarilganini anglatmaydi. Request/response validation, role/scope, DBdagi natija va xato semantikasi alohida sinovdan o'tishi kerak. Hali yozilmagan endpoint muvaffaqiyatni soxtalashtirmasin; holati aniq NOT_IMPLEMENTED bo'lsin va qabul qilingan deb hisoblanmasin.

## P1 — Haqiqiy biznes ma'lumotlari umumiy DBga ulanmagan

Manzil: `backend/app/db/storage.py:25`, `:29`, `:99`; `backend/app/services/billing.py:116`.

- Compose `DATABASE_URL` beradi, runtime faqat `FLEXBRIDGE_DATABASE_URL`ni o'qiydi. Faqat DATABASE_URL berilgan child tekshiruvi **sqlite** schemeini tanladi.
- Toza runtime DBda **4 jadval** yaratildi: circuit_breaker_state, domain_records, sessions, users. Kanonik flexbridge sxemasi ishlatilmaydi; users/sessions ustunlari ham kanonik sxemadan farq qiladi.
- Order boshqa jarayonda yaratildi, shu DBli asosiy jarayonda uning paymenti yuborildi: **409 Invoice not found**. Billing dictlari umumiy saqlashga ulanmagan.
- save/load_domain_record yordamchilari bor, ammo biznes xizmatlarida ulardan foydalanish topilmadi. UnitOfWork hamon in-memory; audit va ledger hamon dictda.

Tuzatish: bitta rasmiy DSN, haqiqiy PostgreSQL17 migration/repository va biznes tranzaksiyalari; auth ham kanonik sessions/users bilan moslashtirilsin. JSON KV yordamchisi mavjudligi invariantli domen jadvallariga integratsiya o'rnini bosmaydi.

## P1 — Fayl tekshiruvi va egani aniqlash chetlab o'tiladi

Manzil: `backend/app/services/files_quarantine.py:25`, `:105`, `:139`; `backend/app/api/v1/files.py:58`.

- Faqat `%PDF-1.7 broken non-PDF body` yuborildi: **CLEAN**. Obyekt omboriga fayl yuklanmagan, haqiqiy parser/ClamAV chaqirilmagan.
- Download queryga haqiqiy owner IDni yozishning o'zi yetdi: sessiyasiz **200** va signed_url. ACL requester_idni joriy actor bilan bog'lamaydi.
- Signed URLga exp qo'shilgan, ammo haqiqiy ombor/proxy verifikatori va SDK presign hali yo'q.

Tuzatish: requester actor sessiyadan; owner/assignment ACL DBdan; haqiqiy ombor bayti, ClamAV+pypdf worker, resurs limitlari va tekshirilgan object version; haqiqiy presigned GET. Sticky quarantine faqat bitta tor bypassni yopgan.

## P1 — Begona amaliyot va kundalikni o'zgartirish mumkin

Manzil: `backend/app/services/placements.py:224`, `:231`; `backend/app/services/internship_logs.py:240`; `backend/app/api/v1/canonical_routes.py:205`, `:245`.

Mavjud victim placement fixtureiga boshqa CANDIDATE tokeni bilan ketma-ket `party:CANDIDATE`, `party:ORGANIZATION` yuborildi: ikkisi ham **200**, placement **ACTIVE** bo'ldi. Party hali mijozdan olinadi; actor haqiqiy nomzod/korxona a'zosi ekanligi tekshirilmaydi. Canonical engagement yo'li hamon placements ustida ishlaydi.

Shu unrelated candidate boshqa authorning DRAFT logini submit qildi: **200, SUBMITTED**. Service author_idni tekshirmasdan placement/date bo'yicha yozuvni yangilaydi.

Tuzatish: parent obyektlardan haqiqiy scope va actor munosabatini olish; job_engagement/placement oqimlarini ajratish; bodydagi partyga ishonmaslik; log author/placement/terms/revisionni tekshirish va DB lock bilan o'zgartirish.

## P1 — AC-040 va matchingning asosiy talablari hali buziladi

Manzil: `backend/app/services/internship_logs.py:194`, `backend/app/api/v1/canonical_routes.py:231`; `backend/app/services/opportunities.py:319`.

- Mavjud placementga 0-daqiqali WORKED draft **422** oldi; AC-040 draft uchun **200** talab qiladi. Draft ham submitning `total_minutes > 0` validatoriga yuborilgan.
- Tasks faqat summaga aylantiriladi; ularning timed entrylari va kesishma himoyasi real DBga yozilmaydi.
- Bitta guruhda 2 zarur smena, nomzod faqat bittasiga mos. ANY rejimi baribir e'lonni mos deb topdi. Talab bitta to'liq guruhni qoplash edi.
- Canonical preview checked_to=+28 kun yozadi, lekin hisob faqat eski feed chaqiruvi; 28 kunlik haqiqiy occurrence, commute va validity hisoblanmaydi.

Tuzatish: draft va submit validatorlarini ajratish; task entrylarni haqiqiy yozish; to'liq group/28 kunlik moslik algoritmi va ma'lumot yo'qligida UNKNOWN.

## P1 — Tarifsiz nashr, atomiklik va parallel sinovlar

Manzil: `backend/app/services/opportunities.py:137`; `backend/app/services/billing.py:376`.

Sessiyasiz va tarifsiz tashkilot uchun contract_type ko'rsatilgan 5 revision yuborildi: **5 x 201**, hammasi PUBLISHED. "Entitlement yo'q" holatida service bepul 5-limitga o'tadi; bu tasdiqlangan tarif tekshiruvi emas.

Kvota/refund/idempotency hisoblari process dictlarida. Yangi testdagi `for` loop parallel DB tranzaksiyasi sinovi emas. Ketma-ket refund ceiling yaxshilangan, ammo requester+approver IDlari hali bitta unauthenticated requestdan olinadi; mustaqil approval bajarilmagan.

Tuzatish: yagona publish yo'li, haqiqiy entitlement, tashkilot/payment satri locki, umumiy DB tranzaksiyasi va alohida ulanish/jarayonlarda bir vaqtda boshlanadigan testlar.

## P1 — Compose, migration va operatsion ishlar yakunlanmagan

Repo ichida `backend/Dockerfile`, `backend/app/workers/outbox.py`, `backend/alembic.ini`, `backend/alembic/env.py` yo'q. Compose backendni build qilishni va yo'q worker modulini ishga tushirishni buyuradi. Alembicda bitta revision fayli bor, ammo ishga tushadigan muhit sozlanmagan. PostgreSQL sxema migratsiyasi runtime users/sessions modeliga ham mos emas.

Frontend/CI, real queue/scan worker, backup/restore dalili va real retention ijrosi topilmadi. `/operations/pilot-readiness` tashqi servislar ishga tushirilmagan muhitda **pilot_ready:true** qaytardi. FIX-12/13/14 tugallangan deb qabul qilinmaydi.

## P2 — Token saqlash va Argon2 formati

Manzil: `backend/app/services/auth.py:65`, `:80`, `:195`; `backend/app/db/storage.py:48`.

Argon2idning kriptografik hisobi to'g'ri, ammo PHCga o'xshash formatda salt/digest standart encodingda emas. `argon2.PasswordHasher().verify` **VerificationError** berdi. Standart kutubxona hash/verify APIlari va qayta xeshlash siyosatidan foydalanish kerak.

Raw Bearer token sessions.session_id primary keyida ochiq saqlanadi; yonidagi token_digest uni yashirmaydi. DBni o'qigan kishi token sifatida primary keydan foydalana oladi. Alohida public session UUID va faqat hash bo'yicha izlanadigan maxfiy token ishlatish kerak. TOTP siri ham oddiy matnli SQL ustunda saqlanmoqda.

## Nega original 0/17 barcha xatolar yopilganini ko'rsatmadi

Original skript tor diagnostika edi. U hech qachon barcha qabul mezonlarini to'liq tekshiradigan acceptance suite bo'lmagan. Ushbu qayta tekshiruvda uning chegaralari aniqlandi:

- Refund probe eski paymentni avval to'langan deb qabul qiladi. Endi payment PENDING bo'lgani uchun refundlar 409; bu probeda jami refund chegarasi umuman mashq qilinmaydi. Yangi tekshiruv haqiqiy confirmed fixture bilan alohida tekshirdi.
- Publish probe contract_typeni bermaydi. Yangi validator 422 berishi bilan 6 e'lon ham yaratilmaydi; tarif/kvota yo'li tekshirilmay qoladi. Yangi so'rov contract_type bilan 5 bepul PUBLISHEDni ko'rsatdi.
- Fayl probe birinchi karantindan keyin qayta skanni tekshiradi. Sticky status uni yopadi, lekin yangi header-only soxta PDF va owner query spoofi tekshirilmagan edi.
- 132/132 route imzosi biznes natijasini tekshirmaydi; auto-OK handlerlar bu mezondan o'tadi.

Original skript o'zgartirilmagan; yangi dalillar kengaytirilgan qayta tekshiruvdan olingan. Qabul testlarida har doim zarur old shart tasdiqlanib, xavfsiz rad javobi bilan birga to'g'ri amalning haqiqiy natijasi ham tekshirilishi kerak.

## Keyingi tuzatishlar

1. Provider bypass va signature defaultini olib tashlash; public eski endpointlarga actor/CAP/scope qo'llash.
2. Startup breaker resetini olib tashlash; session expiry, haqiqiy MFA va author/party tekshiruvlari.
3. Auto-OK handlerlarni haqiqiy implementatsiyadan ajratish; R1 kontraktlarini alohida qabul qilish.
4. Kanonik PostgreSQL repository, migration, haqiqiy fayl/worker va atomik pul/kvota amallari.
5. AC-040, full-group matching, parallel test, ishga tushadigan Compose va real restore/end-to-end dalili.

Qayta bajarish: `python reviews/2026-11-07/recheck_984fec5/recheck.py`. Har safar yangi SQLite fayli ishlatiladi. Dalillar: `recheck_results.json`; original diagnostika: `original_probe_results.json`, `original_run_summary.json`. Baholashni takrorlash sintetik ma'lumot bilan amalga oshiriladi; bu skript production serverga qarshi ishlatilmaydi.
