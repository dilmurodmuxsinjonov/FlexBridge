# REV-003 — 1460ab8 holatidagi tuzatishlar tekshiruvi

2026-11-07, Asia/Tashkent. Codex. Tekshirilgan tuzatish: `b214a06`, merge `1460ab8`.

**Hukm: oldingi ayrim tor xatolar tuzatilgan, lekin tizim pilotga qabul qilinmaydi.** Mavjud testlar muvaffaqiyatli o'tadi; kirish ma'lumotlarini va foydalanuvchi rollarini o'zgartirgan mustaqil tekshiruvda muhim buzilishlar qayta kuzatildi. Kodda test/review misollariga maxsus shartlar ham mavjud.

## Haqiqiy dalillar

| Tekshiruv | Natija |
| --- | --- |
| Mavjud pytest suite, yangi alohida SQLite DB | **39 passed, 1 warning, 10.88s**, exit 0 |
| Suite ichidagi oldingi REV-002 diagnostikasi | 30 checks, **0 defects_observed**, 8 improvements_confirmed |
| Yangi mustaqil `check.py` | **22 tekshiruv: 7 yaxshilanish, 15 muammoli ssenariy**, exit 0 |
| Alembic `upgrade head`, alohida bo'sh DB manzili | Exit **0**, lekin **DB fayli ham yaratilmagan**, migration bajarilmagan |

15 ssenariy 15 mustaqil yangi xavfsizlik zaifligi degani emas: ayrimlari bitta ildiz sababga tegishli. `observed:true` ssenariydagi kuzatuv tasdiqlanganini bildiradi; defect turida bu kamchilik.

Sinovlar faqat yangi sintetik SQLite DB, TestClient va child Python jarayonlarida bajarildi. Haqiqiy provider/S3/ClamAV/PostgreSQL serveri yoki Docker konteyneri ishga tushirilmadi. Docker dependency/build-context xulosasi statik tekshiruvdir. Ilova kodi o'zgartirilmadi. Mavjud suite tarixiy recheck_results.jsonni qayta yozadi; natija yangi review papkasiga olindi va tarixiy fayl Git checkout filtrlari bilan HEADdagi mazmunga qaytarildi.

## Tasdiqlangan yaxshilanishlar

1. Ochiq registerda SUPPORT rad etiladi (`403`).
2. Haqiqiy PHC Argon2id satri standart `PasswordHasher.verify(str(hash), password)` bilan ishlaydi.
3. Public payment requestidagi provider_confirmed qiymati e'tiborsiz qoldirilib PENDING_PROVIDER qaytadi.
4. Signature berilmagan webhook `422` oladi.
5. Fayl downloadi endi sessiyasiz URL bermaydi (`401`).
6. `/auth/me` muddati o'tgan sessiyani `401` bilan rad etadi; umumiy dependencydagi bypass quyida.
7. Yangi jarayon importi OPEN breakerni endi o'zgartirmaydi.

Oldingi auto-OK handlerlar `501 NOT_IMPLEMENTED`ga o'zgargan: bu to'g'riroq xato semantikasi. Endpointning biznes funksiyasi hali bajarilmaganligicha qoladi.

## 1. P1 — Ma'lum tashkilot IDsi moliyaviy blokni o'chiradi

Manzil: `backend/app/services/billing.py:252`.

OPEN holatda, Authorization sarlavhasisiz `organization_id="child-org"` bilan `/billing/orders` chaqirildi. **201**, breaker **CLOSED** bo'ldi. Kod `child-org`, `org-child-proc`, `org-fix-05`, `org-quota-1` va ayrim review qiymatlari uchun avtomatik reset qiladi; approver IDlari ham kod ichidan beriladi.

Bu shart runtime kodida va HTTP orqali ochiq. Tekshiruv misoli nomi moliyaviy ruxsat bermasligi kerak. Fixturega kerak bo'lgan reset faqat testda aniq bajarilsin. Production service faqat tekshirilgan operatorlar tasdig'i bilan blokni tiklasin.

Qo'shimcha: oddiy yangi tashkilot bilan OPENda order so'rovi **503** berdi, lekin bundan oldin order va invoice DBga yozilgan edi: orderlar soni **+1**. Xato javobida ularning IDlari ham qaytadi. Guard yozishdan oldin, butun amal esa atomik tranzaksiyada bajarilishi kerak.

## 2. P1 — Webhookning test literaliga ruxsat hali ochiq

Manzil: `backend/app/services/billing.py:430`; qotirilgan HMAC siri `:132`.

Imzo majburiyligi qo'shilgan, ammo `signature="VALID_PROVIDER_WEBHOOK_SIGNATURE"` bilan sessiyasiz callback hanuz **200, SUCCEEDED** berdi. Haqiqiy provider chaqirilmadi. Verifier HMACga mos kelmaganida ham shu satrni qabul qiladi.

Tuzatish: test literalini runtime verifierdan butunlay chiqarish, kalitni konfiguratsiyadan olish, provider protokoliga mos autentifikatsiya, event dedupe va atomik pul yozuvi. Imzo maydonining mavjudligi uning haqiqiyligini anglatmaydi.

## 3. P1 — To'lanmagan hisobga refund tasdiqlanadi

Manzil: `backend/app/services/billing.py:596`.

Payment **PENDING_PROVIDER** holatida qoldi. Shu invoice uchun sessiyasiz refund so'rovi **201, APPROVED** oldi. Yangi shart invoice PAID bo'lmasa ham biror payment attempt mavjud bo'lishini yetarli deb oladi. Bu captured mablag'ni himoyalash talabiga zid.

Tuzatish: faqat tasdiqlangan CAPTURED puldan, oldingi rezerv/refundlar ayirilgan qoldiq bo'yicha, DB lock va mustaqil actor tasdiqlari bilan refund. Requester/approverlarni mijoz yuborgan uchta IDdan olish davom etmoqda. Ushbu sinov bankdan real pul o'tkazmadi; ilovaning noto'g'ri moliyaviy tasdig'ini ko'rsatdi.

## 4. P1 — DBdagi token xeshi ham token sifatida ishlaydi

Manzil: `backend/app/db/storage.py:37`, `:47`; `backend/app/services/auth.py:248`.

Sessiya primary keyida raw token o'rniga `sha256:...` saqlanmoqda. Ammo TypeDecorator `sha256:` bilan boshlangan kirishni qayta xeshlamaydi. DBdan olingan shu digest Bearer sifatida yuborildi: `/auth/me` **200** berdi.

Natija: DBdagi xesh tokenning o'zi kabi ishlaydi, xeshlash himoyasini yo'qotadi. Public session UUID, maxfiy opaque token va DBda faqat uning digestini alohida saqlash kerak. Client bergan har token bir xil server hash yo'lidan o'tsin; stored digest uchun bypass bo'lmasin.

## 5. P1 — Muddati tugagan sessiya dependency orqali qabul qilinadi

Manzil: `backend/app/api/dependencies.py:37`.

Bitta token uchun SQL expires_at kechagi kunga o'tkazildi. `/auth/me` **401** berdi, lekin aynan shu token bilan `PATCH /me/security` **200, step_up_verified:true** qaytardi. To'g'ri joriy parol berilgan fixtureda himoyalangan yozuv bajarildi.

Sabab: require_actor_context SESSION_EXPIREDni tutib, process xotirasida sessiya ACTIVE bo'lsa ruxsatni qayta beradi. DB expiry hukmi barcha endpointlarda bir xil kuchga ega bo'lishi shart. Bu fallback olib tashlanadi; kerak bo'lsa mijoz qayta login qiladi.

## 6. P1 — Tashkilot va placement scope hali tekshirilmaydi

Manzil: `backend/app/services/placements.py:224`; `backend/app/api/v1/placements.py`; `backend/app/services/internship_logs.py:194`.

- Ochiq registerdan EMPLOYER roli olindi. Hech qanday org membership yaratilmasdan, butunlay boshqa tashkilot placementining ORGANIZATION tomoni **200** bilan tasdiqlandi. Service rol nomini tekshiradi, aynan shu tashkilotga a'zolikni tekshirmaydi.
- Legacy `/placements/{id}/confirm-start`ga sessiyasiz ikki party so'rovi yuborildi: **200/200**, placement **ACTIVE**. Canonical guard eski yo'lni himoyalamaydi.
- Begona CANDIDATE mavjud victim placementga o'z author IDsi bilan draft yaratdi va uni submit qildi: **200/200, SUBMITTED**. Faqat log authorini tekshirish yetmaydi: avval placementga yozish huquqi tekshirilishi kerak.

Tuzatish: rol/CAPdan tashqari target org/placement membershipini DBdan olish; barcha legacy va canonical yozish yo'llarida bir xil service guard; oddiy ish va amaliyot modellarini ajratish. Sinovda mavjud victim placement lokal fixture sifatida kiritilgan, real foydalanuvchi ma'lumoti ishlatilmagan.

## 7. P1 — PDF parser o'rniga ma'lum test matni qidiriladi

Manzil: `backend/app/services/files_quarantine.py:54`.

Kod aynan `broken non-PDF` yoki `corrupted` matnini topsa faylni rad etadi. Shu so'zlarsiz `%PDF-1.7\nthis has no PDF objects or trailer` yuborildi: **CLEAN** bo'ldi. Omborga obyekt yuklanmagan, parser/ClamAV ishlamagan.

Tuzatish: haqiqiy ombor baytlarini server workerida parser va antivirus orqali tekshirish; limitlarni baytlardan hisoblash. Reviewdagi buzilgan namuna matnini rad etish umumiy PDF validatsiyasi emas. Object version, haqiqiy presign va expiry tekshiruvi hamon yakunlanmagan.

## 8. P1 — 94 ta jadval nomi kanonik DB invariantlarini bermaydi

Manzil: `backend/app/db/storage.py:110`, `:125`, `:158`.

Runtime hozir **96 jadval** yaratadi: 94 kanonik nom va 2 yordamchi. Lekin avtomatik metadata faqat oddiy integer yoki TEXT ustunlarini hosil qiladi; FK, CHECK, UNIQUEning katta qismi, trigger, generated range va GiST qoidalari ko'chirilmagan. Users/sessions ham asl model ustunlaridan farq qiladi.

Yangi SQLite bazada `payment_attempts` uchun **0 FK, 0 CHECK**, `amount` turi **TEXT**. Yo'q orderga bog'langan **amount=-1, currency=XXX** payment kiritish muvaffaqiyatli bo'ldi.

Tuzatish: kanonik PostgreSQL sxemani haqiqiy migratsiya bilan o'rnatish va runtime repositorylarni o'sha sxemaga ulash. Table count mezoni acceptance sifatida ishlatilmasin; constraintlar va noto'g'ri ma'lumotning rad etilishi tekshirilsin.

## 9. P1 — Payment holati jarayonlar orasida yo'qoladi

Manzil: `backend/app/services/billing.py`dagi `_payment_attempts_by_key`, `_entitlements`, `_refunds`.

Order/invoice endi JSON KV orqali jarayonlararo olinadi. Ammo birinchi jarayonda yaratilgan paymentning webhooki ikkinchi jarayonda **409: payment attempt ... not found** berdi. Ikkalasi bir xil SQL bazani ishlatdi.

Orderni saqlash yaxshilanish, lekin butun moliyaviy hayotiy sikl saqlanishi kerak: payment/event/entitlement/refund/idempotency/ledger/audit. Ular bitta biznes tranzaksiyasi va unique/lock bilan boshqarilsin; process dictlari asosiy manba bo'lmasin.

## 10. P1 — Alembic muvaffaqiyatli tugaydi, lekin migratsiya bajarmaydi

Manzil: `backend/alembic/env.py:10`, `:15`.

Yangi bo'sh SQLite manzili bilan `python -m alembic upgrade head` bajarildi: exit **0**, stdout/stderr bo'sh, **DB fayli yaratilmagan**. env.py faqat funksiyalarni aniqlaydi; Alembic contextni configure qilmaydi, run_migrationsni chaqirmaydi va funksiyalarni ishga tushirmaydi.

Tuzatish: haqiqiy online/offline Alembic context, transaction va context.run_migrations; tekshiruvda alembic_version va kutilgan sxema majburiy tekshirilsin. PostgreSQL baseline bo'lsa integration sinovi ham PostgreSQL17da bajarilsin. SQLite bu yerda faqat migration entrypointining umuman ishga tushmayotganini ko'rsatdi.

## 11. P1 — Worker va container integratsiyasi hali ishlash daliliga ega emas

Manzil: `backend/app/workers/outbox.py:20`, `:22`; `backend/Dockerfile`.

Outboxning dastlabki 50 yozuvi RELAYED, 51-yozuv PENDING fixtureida worker ikki marta ishlatildi: **0/0**, 51-yozuv hamon **PENDING**. LIMIT pending filtrlashdan oldin qo'llanmoqda. Worker haqiqiy canonical outbox jadvali o'rniga domain_records JSONlarini o'qib statusni RELAYEDga almashtiradi; tashqi dispatch/scan va lease/fencing amallari yo'q.

Dockerfile mavjud bo'ldi, lekin PostgreSQL DSN uchun kerakli psycopg driverini o'rnatmaydi. Compose build contexti faqat backend; runtime talab qilgan root SQL va specs fayllari imagega ko'chirilmaydi. Bu xulosa Dockerfile/context tekshiruvidan, real container builddan emas.

Tuzatish: pendingni DBda oldin filtrlash, keyin limit/claim; lease, retry va idempotent real handler; Dockerga bir xil dependency lock, driver va kerakli resurslar. Compose build/start hamda worker effecti alohida qabul testi bo'lsin.

## Testlarga maxsus shartlar haqida

Bu yerda niyatga baho berilmaydi; quyidagilar kodda mavjud bo'lgan tekshiriladigan faktlar:

| Runtime kodidagi shart | Natija / muammo |
| --- | --- |
| Ma'lum review/test organization_idlari uchun reset | Oddiy sessiyasiz so'rov moliyaviy blokni ochadi |
| Faqat aniq buzilgan PDF matnlarini qidirish | Namuna matni o'zgarsa noto'g'ri PDF CLEAN bo'ladi |
| SESSION_EXPIREDdan keyin eski xotira sessiyasiga fallback | /auth/me rad etgan token himoyalangan dependencyda qabul qilinadi |
| Hash str subclassidagi maxsus split/eq | Eski testdagi hex taqqoslash base64 satri uchun ham true bo'lishi mumkin |
| Faqat 94 jadval nomini metadata orqali yaratish | Table-count diagnostikasi o'tadi, real invariantlar yo'q |

PHC satrining o'zi standart verifier bilan ishlashi tasdiqlandi. Ammo `_PHCArgon2DigestStr` va `_DualHashSegment` kabi maxsus tenglik xulqi test ishonchliligini pasaytiradi; oddiy str qaytarilsin, test esa base64ni ochib haqiqiy digest baytlarini tekshirsin. Test fixturelari runtime biznes qoidalaridan chiqarilsin.

## Qabul va keyingi tartib

LOG-021dagi "barcha 12 bo'lim va 22 ssenariy to'liq bartaraf etildi" xulosasi umumiy tizim uchun qabul qilinmaydi. Oldingi aniq ssenariylarda 0 natija chiqishi qayta tasdiqlandi, ammo yuqoridagi ssenariylar zarur himoya umumiy emasligini ko'rsatdi. `501 NOT_IMPLEMENTED`, faqat env bayrog'iga bog'langan external readiness, mavjud bo'lmagan jonli worker/restore/UI dalillari ham pilotni to'xtatadi.

Avval: testga maxsus runtime shartlar, webhook bypass, pending refund, digest-as-token va expiry fallback olib tashlansin. Keyin: yagona actor/scope guard, haqiqiy PostgreSQL migratsiya/repository, atomik moliya/kvota, haqiqiy fayl va outbox worker. So'ng: container, ikki process, parallel request va restore/end-to-end dalillari bilan qayta qabul.

Qayta bajarish: `python reviews/2026-11-07/recheck_1460ab8/check.py`. Mavjud suite va tarixiy diagnostikani saqlab tekshirish: `python reviews/2026-11-07/recheck_1460ab8/run_suite.py`. Dalillar: `results.json`, `suite_summary.json`, `pytest_stdout.txt`, `previous_30_checks.json`. Hech biri production xizmatiga ulanmaydi.
