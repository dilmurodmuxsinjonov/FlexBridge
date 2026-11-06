# REV-001 — FlexBridge ishlariga mustaqil baho

2026-11-07, Asia/Tashkent. Tekshiruvchi: Codex. Ko'rilgan commit: `8bb0ad2`.

**Umumiy baho: 4/10. Pilotga chiqarishga tayyor emas.** Hujjatlar, SQL sxema va ayrim biznes qoidalari bo'yicha foydali asos yaratilgan. Backend hozircha xotirada ishlaydigan prototip; tasdiqlangan infratuzilma va API kontraktlari bilan integratsiya yakunlanmagan. Bu baho ekspert xulosasi; tayyorlik foizi emas.

| Yo'nalish | Baho | Asos |
| --- | --- | --- |
| Hujjatlar va ishni qismlarga ajratish | 8/10 | Talablar xaritasi, kichik vazifalar, qarorlar va Git tarixi mavjud; keyingi jurnallarda AC/API raqamlari chalkashgan |
| SQL sxema | 8/10 | PGlite/PostgreSQL dvigatelida 17/17 sinov qayta o'tdi; backend bu sxemadan foydalanmaydi |
| Backendning amaliy ishlashi | 4/10 | Router va servislar ajratilgan; haqiqiy saqlash, to'liq oqimlar va kontraktga mos APIlar yetishmaydi |
| Xavfsizlik | 2/10 | Mijoz rol va actor IDlarini o'zi beradi; muhim endpointlarda sessiya/ruxsat tekshiruvi yo'q |
| Pilot va operatsion tayyorlik | 2/10 | Readiness deklarativ; DB/Redis/S3/ClamAV holati va backup/restore dalillarini tekshirmaydi |

## Tekshiruv va uning chegarasi

- `cd backend; python -m pytest -q`: **32 passed**, 1 deprecation warning, 1.54 s. Bu mavjud testlarning haqiqiy natijasi; barcha mahsulot talablari qabul qilinganini bildirmaydi.
- Mavjud `verify_v1_4_schema.mjs` qayta bajarildi: **17/17**, PGlite 0.5.15 / PostgreSQL 18.6 WASM. Kanonik hisobot o'zgartirilmadi; yangi natija `schema_verification.json` ichida.
- SQL introspeksiyasi: **94 jadval, 935 oddiy + 4 generated ustun, 233 FK constraint**. Modeldagi **214 FK** metadata soni bilan DB constraint soni bir xil tushuncha emas; ularni bir xil deb taqdim etmaslik kerak.
- `reproduce_findings.py`: **17/17 salbiy tekshiruvda kamchilik kuzatildi**. `defect_observed: true` xato qayta ko'rsatilganini anglatadi. Bu muvaffaqiyatli qabul testi emas.
- Salbiy tekshiruvlar lokal FastAPI TestClient va alohida servis fixturelari orqali bajarildi. Tashqi to'lov, haqiqiy S3 yuklash/yuklab olish yoki production server sinovdan o'tkazilmadi. Mavjud 1.4 JSON modeli, SQL, talablar xaritasi va boshqaruv hujjatlari solishtirildi; PDF/PPTX manbalari boshidan to'liq qayta audit qilinmadi.
- Ilova kodi o'zgartirilmadi. Ushbu hisobot, qayta tekshirish vositalari va loyiha jurnallari yangilandi.

## Ustuvor kamchiliklar

P1 — pilotdan oldin tuzatilishi zarur. P2 — to'g'rilik, integratsiya yoki ishlatishdagi muhim kamchilik.

### R-01 — P1: vakolat mijoz yuborgan qiymatlarga ishonadi

Manzil: `backend/app/api/v1/auth.py:19`, `backend/app/api/v1/governance.py:26`, `backend/app/services/auth.py:74`.

Ochiq register so'rovi `roles: ["SUPER_ADMIN"]` bilan `201` qaytardi. Akademik tayinlovning mavjud supervision fixturei uchun Authorization sarlavhasisiz, bodyda `actor_role: "SUPER_ADMIN"` va uydirma actor ID yuborib `201` olindi. Fayl, billing va placement endpointlarida ham server sessiyasidan actor olish mexanizmi yo'q. Alohida `/auth/me` himoyasi qolgan routerlarni himoyalamaydi.

Tuzatish: umumiy authentication dependency, kanonik rol/CAP va obyekt scope tekshiruvi; actorni sessiyadan olish; ochiq ro'yxatdan o'tishda imtiyozli rol berishni taqiqlash. Ikki shaxs tasdig'i alohida autentifikatsiyalangan amallar bo'lishi kerak.

### R-02 — P1: provayder tasdig'isiz to'lov muvaffaqiyatli hisoblanadi

Manzil: `backend/app/services/billing.py:186`, `backend/app/api/v1/billing.py:84`.

Authorization yoki provayder chaqiruvisiz buyurtma yaratib, invoice summasini qayta yuborish `SUCCEEDED` va faol entitlement berdi. Bu kod real pul yechmaydi; muammo — to'lov bo'lmaganida ham pullik xizmatni faollashtirishi.

Tuzatish: tekshirilgan provayder javobi/webhookidan keyingina invoice va entitlementni bitta DB tranzaksiyasida yangilash; mock adapterini aniq test muhitiga ajratish.

### R-03 — P1: ilova ma'lumotlari bazada saqlanmaydi

Manzil: `backend/app/db/session.py:28`, `backend/app/services/auth.py:65`, `backend/app/services/billing.py:116`.

UnitOfWork, foydalanuvchilar, sessiyalar, arizalar, to'lovlar va audit oddiy Python dict/listlarda. `sql_trace`ga `BEGIN/COMMIT` matnini yozish SQL tranzaksiyasi emas. Alohida Python jarayoni yaratgan sessiya ikkinchi jarayonda `401` oldi. Restart ma'lumotni yo'qotadi; bir nechta worker umumiy holatni ko'rmaydi. Redis invalidation ham amalga oshirilmagan.

Tuzatish: PostgreSQL repository/SQLAlchemy sessiyalari, migratsiyalar, atomik biznes tranzaksiyalari, DB constraintlari va umumiy Redis keshi. Restart va ikki workerli oqim bilan tekshirish.

### R-04 — P1: karantin va xususiy fayl himoyasi haqiqiy faylni tekshirmaydi

Manzil: `backend/app/services/files_quarantine.py:25`, `:88`, `:121`.

ClamAV chaqiruvi yoki pypdf parseri yo'q: EICAR matni va tokenlar oddiy qidiriladi, sahifa/obyekt/hajmni mijoz beradi. Fayl yuklamasdan `/JavaScript` bilan karantinga olingan yozuvni `not even a PDF` matnini qayta yuborib `CLEAN` qilish mumkin bo'ldi. Boshqa requester ID bilan, sessiyasiz download URL ham berildi (`200`).

URL faqat `storage.flexbridge.local` matni; S3 imzolash integratsiyasi yo'q. Imzoda absolyut amal qilish vaqti qatnashmaydi, faqat doimiy `60` bor. Amaldagi omborda 60 soniyadan keyin yuklab olish rad etilishi tasdiqlanmagan.

Tuzatish: worker obyekt omboridagi haqiqiy baytlarni o'qisin, ClamAV+pypdf bilan tekshirsin, server hisoblagan limitlarni qo'llasin; sessiya va file ACLdan keyin omborning haqiqiy presigned URLini bersin.

### R-05 — P1: e'lon yaratish kvotani chetlab o'tadi

Manzil: `backend/app/services/opportunities.py:102`, `backend/app/api/v1/opportunities.py:24`, `backend/app/services/billing.py:292`.

`/opportunities/revisions` odatda `published=True` va billing tekshiruvisiz PUBLISHED e'lon yaratadi. Tarif olmagan bitta tashkilot uchun 6 ta so'rovning barchasi `201`, 6 ta e'lon PUBLISHED bo'ldi. `contract_type`ni bermaslik ham `201`; AC-039 bu holatda `422` talab qiladi.

Tuzatish: yagona nashr tranzaksiyasiga entitlement, moderatsiya, shartnoma va kvota tekshiruvlarini birlashtirish; parallel publishda DB lock/atomik kvota kafolati. Alohida billing dictidagi slotlar haqiqiy e'lon holatining o'rnini bosmasin.

### R-06 — P1: jami qaytarish to'langan summadan oshadi

Manzil: `backend/app/services/billing.py:403`.

599 000 UZS invoice uchun 599 000 UZSdan ikki refund ham `201` oldi: jami **1 198 000 UZS**. Har refund alohida invoice summasi bilan solishtiriladi, oldingi qaytarishlar hisoblanmaydi. SQLdagi jami captured summani himoyalovchi trigger mavjud, lekin API bazaga ulanmagani uchun ishlamaydi.

Tuzatish: captured minus oldingi refundlar bo'yicha qoldiqni DB tranzaksiyasida bloklab tekshirish, qaytarish idempotentligi va autentifikatsiyalangan tasdiqlar.

### R-07 — P1: kanonik API va AC talablari boshqa amallar bilan almashtirilgan

Manba: `specs/v1_4/FlexBridge_model_1_4.json` (`apis`, `acceptance`); `backend/app/api/v1/governance.py:82` va mavjud testlar.

| ID | Kanonik talab | Hozirgi kod/test |
| --- | --- | --- |
| API-003 | POST `/api/v1/matching/preview`, MATCH/CONFLICT/UNKNOWN | GET `/api/v1/opportunities/feed` |
| API-060 | PATCH `/api/v1/me/security`, step-up | Akademik tayinlov yaratish deb nomlangan |
| API-061 | DELETE `/api/v1/me/sessions/{id}`, faqat o'z sessiyasi | Akademik tayinlovni yangilash deb nomlangan |
| API-073 | GET `/api/v1/organizations/{org}/memberships` | Billing idempotentligiga havola sifatida ishlatilgan |
| AC-017 | Kundalik sana/daqiqa/vaqt kesishmasi | Sessiya revoke testi deb yozilgan |
| AC-040 | 0-daqiqa draft, WORKED submit va timed-entry overlap | Asosan mentor/akademik baholar ajratilishi bilan tekshirilgan |

OpenAPI method+path tekshiruvida 132 kanonik kontraktdan 5 tasining imzosi mos keldi: API-015, API-018, API-X03, API-X05, API-X06. Bu **tayyorlik foizi emas**: ro'yxatda keyingi bosqich kontraktlari ham bor, imzo mosligi esa xulq to'g'riligini isbotlamaydi. Ammo yuqoridagi uch asosiy R1 kontrakti mavjud emasligi aniq.

Tuzatish: kanonik model asosida R1 endpoint/rol/CAP/AC xaritasi; har mezon uchun tegishli salbiy va ijobiy integratsiya dalili. AC soni `42` ekanini tekshirish barcha 42 AC bajarilganini tekshirmaydi.

### R-08 — P1: kundalik submit qoidalarini API bajarmaydi

Manzil: `backend/app/services/internship_logs.py:68`.

Yo'q placement va `total_minutes=-1` bilan `/internship-logs/daily-logs` `201`, holat `SUBMITTED` qaytardi. Draft/task-entry/submit bosqichlari, kun limiti va sana tekshiruvlari bu oqimda bajarilmaydi. SQLdagi AC-040 himoyasi prototip APIga ta'sir qilmaydi.

Tuzatish: haqiqiy placement/author scope, draft va submit oqimlari, task-entrylardan hisoblangan jami vaqt va DB triggerlari bilan ishlash.

### R-09 — P1: circuit-breaker va readiness turli holatlarni ko'radi

Manzil: `backend/app/services/billing.py:120`, `backend/app/services/operations.py:62`, `:166`, `backend/app/main.py:57`.

Operations breaker OPEN bo'lganda billing buyurtmasi `201` oldi. Billing breakeri OPEN, operations CLOSED bo'lganda esa `pilot_ready:true` qaytdi. Billingning o'z breakeri ochiq holatda API kutilgan `503 P1_FINANCE_CIRCUIT_OPEN` o'rniga **500** qaytardi.

Readiness saqlangan JSON hisobot va model sonlarini o'qiydi; joriy DB/Redis/S3/skanerga ulanmaydi. RPO=24h/RTO=4h — qaytarilgan maqsadlar, tiklash sinovi dalili emas.

Tuzatish: umumiy saqlanadigan breaker holati va HTTP exception handler; xizmatlarning haqiqiy readinessi, backup/restore mashqi va R1 AC dalillariga bog'langan chiqarish mezoni.

### R-10 — P2: idempotency boshqa to'lovni muvaffaqiyatli deb qaytarishi mumkin

Manzil: `backend/app/services/billing.py:202`.

Oldingi kalitni boshqa invoice, boshqa actor, `amount_uzs=1`, `currency_code=USD` bilan qayta yuborish `200` va eski SUCCEEDED yozuvni qaytardi. Tekshiruvlardan oldin faqat global kalit bo'yicha replay qilinadi.

Tuzatish: provayder/tashkilot scopei va so'rov fingerprintini saqlash; bir kalitga boshqa payload kelsa conflict; DB unique constraint va atomik bajarish.

### R-11 — P2: tarif muddati tekshirilmaydi

Manzil: `backend/app/services/billing.py:292`.

Fixtureda `valid_until` kechagi kunga o'tkazilgach publish baribir `200` oldi. `status`, `valid_from`, `valid_until` tekshiruvlari yo'q; refund ham entitlementni bekor qilmaydi.

Tuzatish: publish vaqtida tarifning amaldagi holati va muddatini tekshirish; muddat/refund hayotiy sikli va integratsiya testi.

### R-12 — P2: Argon2id deb belgilangan xesh aslida PBKDF2

Manzil: `backend/app/services/auth.py:35`.

`argon2id_v1$...` qaytariladi, hisob esa `hashlib.pbkdf2_hmac('sha256', ..., 120000)`. Qayta hisoblash bilan tasdiqlandi. Bu tasdiqlangan Argon2id stekiga mos emas va keyingi migratsiyani chalkashtiradi.

Tuzatish: haqiqiy Argon2id kutubxonasi va format/verifikator; kerak bo'lsa eski xeshni aniq PBKDF2 formati sifatida tanib, login paytida yangilash.

### R-13 — P2: tutash bo'sh vaqtlar yagona qamrov deb olinmaydi

Manzil: `backend/app/services/availability.py:165`.

Qabul qilingan `[540,720)` va `[720,900)` intervallar nomzodning `[540,900)` smenasiga mos emas (`False`) deb topildi. Algoritm butun smenani bitta rule ichidan qidiradi. `AVAILABLE_EXTRA` istisnolari ham moslikni kengaytirishda ishlatilmaydi.

Tuzatish: tegishli kun intervallarini birlashtirish, qo'shimcha vaqtni qo'shish, band vaqtni ayirish va keyin to'liq smena qamrovini tekshirish.

## Qo'shimcha cheklovlar

- `operations.execute_retention_job` mijoz bergan age/countdan hisobot yaratadi; haqiqiy yozuvlarni qidirmaydi, o'chirmaydi yoki anonimlashtirmaydi. `records_actioned` bajarilgan ish dalili emas.
- `placements.create_offer` taklifni darhol ACCEPTED qiladi; ikki tomon tasdig'i endpointi actorni tekshirmasdan bodydagi `party`ni oladi. Bu haqiqiy mustaqil ikki tomon roziligi emas.
- Tekshirilgan Git daraxtida Next.js frontend, Docker Compose, ishchi queue/worker va deploy/CI konfiguratsiyasi yo'q. S2.10 uchun end-to-end pilot yoki tiklash dalili topilmadi.
- SQL verifieri tashqi `D:/Codex/.../node_modules/@electric-sql/pglite` yo'liga bog'langan; yangi kompyuterda takrorlash uchun dependencylarni loyiha ichida rasmiylashtirish kerak.
- S1 artefaktlarining to'liq manbaga mosligi hamda 42 ACning hammasi mustaqil ravishda qabul qilinmadi. Oldingi `Tekshiruvda` yozuvlari avtomatik `Bajarildi`ga o'tkazilmaydi.

## Tuzatish ketma-ketligi

1. R1 kanonik API/AC xaritasini tiklash; prototip, real integratsiya va qabul dalilini ajratish.
2. PostgreSQL migratsiyasi/repository va server authentication/CAP/scope qatlamini ulash.
3. To'lov, refund va e'lon kvotasini yagona atomik oqimda ishlatish.
4. Haqiqiy S3+ClamAV+pypdf workerini va xususiy fayl ACLini ulash.
5. Kundalik/moslik/placement oqimlarini kanonik talablarga qaytarish.
6. Umumiy breaker, readiness, backup/restore va asosiy foydalanuvchi oqimini tekshirib pilotni qayta baholash.

Qayta bajarish (repo ildizidan): `python reviews/2026-11-07/reproduce_findings.py`; sxema uchun `powershell -NoProfile -File reviews/2026-11-07/reproduce_schema.ps1`. Skriptlar faqat lokal, sintetik ma'lumotdan foydalanadi. Kamchiliklar tuzatilgach, salbiy probe skriptining `defect_observed` mezonlari ham regressiya testlariga moslashtiriladi.
