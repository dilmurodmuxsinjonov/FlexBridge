# FIX-CODEX-001 — bajarilgan tuzatishlar

2026-11-07, Asia/Tashkent. Boshlang‘ich commit: `1460ab8`.
Tarmoq: `fix/codex-rev003-remediation`. O‘zgarishlar lokal ish papkasida; push/deploy bajarilmadi.

REV-003da ko‘rsatilgan xavfsizlik, moliyaviy holat, migratsiya va worker xatolari uchun
runtime tuzatishlar kiritildi. Oldingi review fayllari saqlangan. Bu paket butun R1 mahsuloti
yoki barcha 42 ta acceptance mezoni qabul qilinganini bildirmaydi.

## Xato va tuzatish dalili

| REV-003 topilmasi | Endi qanday bajariladi | Regressiya dalili |
| --- | --- | --- |
| Test tashkilot IDsi OPEN breakerni o‘chirishi | Runtime fixture IDlari olib tashlandi; tashkilot UUID va haqiqiy scoped grant kerak; guard har qanday yozuvdan oldin | OPENda 503, order/invoice soni o‘zgarmaydi; `child-org` UUID sifatida rad qilinadi |
| Soxta literal HMAC imzosi | Konfiguratsiyadagi sir, aniq JSON protokoli, SHA-256 HMAC, vaqt chegarasi va event dedupe | Literal rad etiladi; takroriy imzolangan callback bitta ledger/entitlement beradi |
| To‘lanmagan invoicega refund | Faqat CAPTURED payment; mablag‘ rezervi, lock; requester va ikki FINANCE approver alohida autentifikatsiya qilinadi | Pending refund rad etiladi; bir approver ikkinchi tasdiqni bera olmaydi; parallel rezerv limitdan oshmaydi |
| Digest ham Bearer sifatida ishlashi | Public session UUID, maxfiy opaque token va uning digest ustuni alohida | Raw digest, `sha256:digest` va public UUID bilan 401; haqiqiy access_token bilan 200 |
| Expired sessiya fallbacki | Memory fallback olib tashlandi; barcha API yozuvlarida DB expiry/revocation tekshiruvi | Expired token order, e’lon va legacy confirmation yozuvlarida ham 401 |
| EMPLOYER bilan begona org tasdig‘i | Public register faqat CANDIDATE; vakolat target tashkilotning aktiv membership/grantidan olinadi | Public privilege olish 403; begona org roli boshqa tashkilot amaliga o‘tmaydi |
| Legacy confirm-start va victim draft | Legacy va canonical yo‘llar umumiy service ownership guardidan o‘tadi; oddiy job engagement hamda internship placement alohida jadvallarda | Sessiyasiz confirmation 401; begona tashkilot 403; begona draft yozilishidan oldin 403 va DBda 0 log |
| PDF namuna matniga qarab CLEAN | Haqiqiy S3 baytlari + pinned ETag; clamd INSTREAM; strict pypdf parser; killable child va limitlar; private obyekt yozilgandan keyingina CLEAN | Turli buzilgan PDF rad etiladi, toza PDF o‘tadi, JavaScript PDF bloklanadi; AV nosozligida CLEAN bo‘lmaydi |
| Faqat jadval nomlari bo‘lgan DB | `create_all` olib tashlandi; kanonik PostgreSQL SQL haqiqiy Alembic migratsiyasida bajariladi; typed repository | Yangi PostgreSQL DBda 96 jadval, real FK/CHECK/triggerlar; manfiy/orphan payment va immutable update rad etiladi |
| Payment boshqa processda yo‘qolishi | Orders/invoices/payment/event/entitlement/refund/idempotency/ledger SQL jadvallarda | Ikkinchi Python process birinchi process paymentini tasdiqlaydi |
| Alembic exit 0, ammo DDL yo‘q | `context.configure`, transaction va `run_migrations` haqiqatan chaqiriladi | Har test sessiyasi yangi DB yaratib `0002_security_runtime`gacha migratsiya qiladi; revision hamda jadvallar tekshiriladi |
| 50 processed qator ortidagi outbox och qolishi | PENDING filtri LIMITdan oldin; SKIP LOCKED + lease + claim token; real handler natijasidan keyin ack | 60 processed qator ortidagi vazifa ishlaydi; effect xatosi pending qoladi; stale token natijasi qo‘llanmaydi |
| Docker context va dependency yetishmasligi | Root build context, SQL/spec COPY, yagona dependency fayli, psycopg/parser/AV-storage klientlari; migration-before-start; non-root OS user | YAML va build tarkibi tekshirildi, Python wheel yig‘ildi; Docker runtime sinalmadi |

Qo‘shimcha tekshiruvlarda quyidagilar ham tuzatildi:

- PostgreSQL trigger funksiyalarining `search_path`i mahkamlandi; API ulanishida ham invariantlar ishlaydi.
- Availability va shift uchun haqiqiy GiST EXCLUDE constraintlar qo‘shildi; parallel yozuvlar ham DBda himoyalanadi.
- Submitted logning summary/statusini bevosita SQL orqali o‘zgartirish ham bloklandi.
- Public MFAdan keyingi enrollment proof va shifrlangan TOTP saqlash qo‘shildi; eski PHC hash tengligini almashtiruvchi subclasslar chiqarildi.
- Single-post pause/resume kreditni qayta sarflamaydi. Bir tashkilotdagi parallel nashrlarda 5 slot limiti org lock bilan saqlanadi.
- Refundning entitlementni bekor qilishi nashr bilan bir xil org lockdan o‘tadi. Bunga alohida PostgreSQL lock-wait regressiyasi qo‘shildi.
- Membership tasdig‘i va moderatsiya qarori xotiradagi lug‘at o‘rniga saqlanadi; actor server sessiyasidan olinadi.
- Readiness endi tarixiy JSON yoki `FLEXBRIDGE_EXTERNAL_SERVICES_VERIFIED=1` bilan yoqilmaydi. Retention endpointi haqiqiy tozalash qilmasa `dry_run/NOT_EXECUTED` qaytaradi.

## Bajarilgan tekshiruvlar

Yakuniy test natijasi `summary.json`, `junit.xml` va `pytest_stdout.txt`da saqlanadi.
Birinchi to‘liq yurish: **60 passed, 1 dependency deprecation warning, 206.70s**.
Qo‘shimcha refund lock tuzatishidan keyin maqsadli yurish: **3 passed, 58 deselected, 11.68s**.
Yakuniy to‘liq qayta yurish: **61 passed, 1 dependency warning, 189.91s**;
exit 0, errors/failures/skipped — 0. Runner umumiy vaqti 191.75s.
Native uvicorn + haqiqiy HTTP orqali qo‘shimcha **4/4 smoke** o‘tdi:
DB konfiguratsiyasiz liveness 200, readiness 503, sessiyasiz finance 401,
DBsiz register 503. Dalil: `http_smoke.json`. Server sinovdan keyin to‘xtatildi.

Test muhiti: Windows, Python 3.12, native PostgreSQL 17.11. Test fixture alohida tasodifiy
`flexbridge_test_*` DB yaratadi, migratsiya qiladi va oxirida o‘chiradi. Mavjud foydalanuvchi
DBsi yoki real foydalanuvchi ma’lumotiga tegilmadi. DB lock/constraint/concurrency va child
process sinovlari haqiqiy PostgreSQLda bajarildi. Asosiy HTTP tekshiruvlari TestClient orqali;
alohida to‘rtta smoke tekshiruvi native uvicorn serverida bajarildi.

S3 uchun botocore Stubber va aniq test doubles; gateway uchun HTTP test double ishlatildi.
ClamAV INSTREAM haqiqiy lokal TCP oqimi orqali tekshirildi, ammo qarshi tomonda test serveri
bo‘lgan. Bu dalillar real MinIO/ClamAV/bank provayderining ishlaganini bildirmaydi.

`git diff --check`, Python compile, Compose/CI YAML o‘qilishi va `pip wheel --no-deps
--no-build-isolation ./backend` tekshirildi. Docker bu muhitda mavjud emas. Wheel build
tekshiruvi mustaqil wheel deploymentini tasdiqlamaydi: runtime kanonik SQL/model artefaktlari
bilan repository/Docker tarkibida ishlatiladi.

## Eski testlar bilan munosabat

12 ta prototype test moduli o‘chirilmagan: `legacy_tests/*.py.txt`da aynan saqlangan;
`manifest.json`dagi SHA-256lar tekshirildi. Ular eski in-memory/sessiya/PDF/provider
shartnomalariga bog‘langan. Ularning ayrim kutilmalari topilgan bypasslarni o‘zi talab qilgan.
Yangi regressiyalar o‘sha kirish qiymatlariga maxsus production shart kiritmaydi.
Retention policy testlari saqlandi; audit uchun endi haqiqiy user UUID ishlatiladi.
Yangi test natijasi eski 39 ta test qayta o‘tdi degan da’vo emas.

## Qolgan chegaralar va ishga tushirish

`contracts.json`: **132 canonical shartnoma, 21 explicit handler, 111 ta 501 handler**.
Explicit handler borligi ham uning barcha acceptance mezonlari bajarilganini bildirmaydi.
Qolgan 111 endpoint bu tuzatish paketida yozib chiqilmadi. UI/browser, to‘liq ta’lim/supervision,
real retention purge/backup va restore drill sinovlari bajarilmadi. `pilot_ready` shu sabab
false; mahsulot hali pilot/productionga to‘liq qabul qilinmaydi.

HMAC — aniq custom adapter protokoli; Payme/Click bank integratsiyasi deb ko‘rsatilmaydi.
Real provider/S3/ClamAV va Linux container sandbox staging sinovi kerak. Dastlabki operator
grantlarini berish va P1 hodisasidan tiklash uchun nazorat qilinadigan operatsion jarayon
ham deployment ishlarining bir qismi. Compose owner kalitlari lokal development uchun;
production runtime hisoblarini alohida eng kam vakolat bilan tayyorlash kerak.

Eski SQLite/JSONni yangi sxemaga jim ko‘chirish yoki o‘chirish bajarilmadi. Mavjud o‘rnatish
uchun backup va alohida tekshirilgan data migration kerak. Migratsiyani bo‘sh PostgreSQLda
boshlash, kerakli secretlarni sozlash va API/worker ishlatish tartibi:
[`backend/README.md`](../../../backend/README.md).
Takroriy lokal test runner: [`scripts/Test-Backend.ps1`](../../../scripts/Test-Backend.ps1).

Parser konfiguratsiyasining rasmiy manbasi:
[pypdf Configuration](https://pypdf.readthedocs.io/en/latest/modules/configuration.html).
Antivirus oqimi uchun:
[ClamAV scanning](https://docs.clamav.net/manual/Usage/Scanning.html).
