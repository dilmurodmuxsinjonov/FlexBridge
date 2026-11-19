# REV-004 — FlexBridge joriy holatini ko'rib chiqish

2026-11-07, Asia/Tashkent. Tekshiruvchi: Codex. Tarmoq:
`fix/codex-rev003-remediation`, HEAD `1460ab8`, ko'p sonli saqlanmagan/commit qilinmagan
ishchi o'zgarishlar bilan. Xulosa aynan ishchi katalogga tegishli; faqat HEADga emas.

**Hukm: backendning ishlaydigan qismlari bor, R1 mahsulot hali pilotga tayyor emas.**
Joriy regressiya: **107 passed, 1 warning, 127.28s**, exit 0. Alohida diagnostika
uchta P2 kamchilikni ko'rsatdi. Mavjud testlar bu holatlarni qamramagan.

## Aniqlangan kamchiliklar

### 1. P2 — Moslik hisobida mavjudlik qoidasining amal qilish muddati e'tiborsiz

Manba: `backend/app/services/availability.py:193`–198.
Filtr faqat candidate, weekday va is_activega qaraydi. `valid_from` va `valid_to`
tekshirilmaydi, hatto `check_date` berilgan bo'lsa ham.

Haqiqiy PostgreSQLdagi natija: `check_date=2026-11-07` uchun 2026-11-06da tugagan
qoida ham, 2026-11-08da boshlanadigan qoida ham `available=True` qaytardi.
Natijada nomzod shu kunda bo'sh bo'lmagan smenaga mos deb ko'rsatilishi mumkin.

Tuzatish yo'nalishi: samarali sanani aniq belgilash, active qoidalarni
`valid_from <= effective_date` va `valid_to IS NULL OR valid_to >= effective_date`
bo'yicha SQLda filtrlash; boshlanish/tugash chegaralari uchun regressiya qo'shish.

### 2. P2 — Stipendiyali amaliyot lentada soatbay ish haqi deb ko'rsatiladi

Manba: `backend/app/services/opportunities.py:114`–116.
`revisions` xususiyati barcha `is_paid=True` yozuvlarni `HOURLY`ga aylantiradi.
`STIPEND` bilan yaratilgan yozuvning `salary_period=MONTH` qiymati hisobga olinmaydi.

Haqiqiy PostgreSQLdagi natija: `STIPEND`, 500000 so'm, `INTERNSHIP_AGREEMENT`
bilan yaratilgan va fixture sifatida nashr qilingan amaliyot lentada
`compensation_type=HOURLY` qaytardi. Bu to'lov turini noto'g'ri ko'rsatadi;
ushbu probe haqiqiy to'lov yoki nashrga ruxsat oqimini tekshirmaydi.

Tuzatish yo'nalishi: compensation turini salary_period/contract bilan izchil
tiklash yoki modelda aniq saqlash; HOURLY/STIPEND/UNPAID_ACADEMIC uchun feed testi.

### 3. P2 — Lenta hisobida takroriy filtrsiz jadval o'qishlar bor

Manbalar: `backend/app/services/opportunities.py:220`–225,
`backend/app/services/availability.py:86`–93 va 193–222.

Har bir e'londa barcha revision va shiftlar qayta yuklanadi; har bir smenada
barcha nomzodlarning availability qoidalari va istisnolari qayta o'qiladi.
WHERE orqali cheklash o'rniga Python ichida filtrlash bajariladi.

SQLAlchemy query instrumentatsiyasi: bitta published e'lon, bitta smena va
check_date bilan bitta matching chaqiruvida **6 ta SELECT, barchasi WHEREsiz**.
Ko'p e'lon/smenada so'rovlar va ko'chirilayotgan satrlar soni ortadi. Bu
query dalili; yuklama testi yoki o'lchangan production kechikishi emas.

Tuzatish yo'nalishi: candidate/date/status/revision bo'yicha SQL filtrlar,
tegishli yozuvlarni bir marta batch olish va pagination/chegaralangan natija.

## Amalga oshirish holati

- Mahsulot: 18+ nomzodlar uchun yarim stavkali ish va amaliyot. Frilans R2ga qoldirilgan.
- FastAPI, SQLAlchemy, PostgreSQL, uchta Alembic migratsiyasi, autentifikatsiya,
  OTP/MFA/passkey/recovery, moliya va fayl adapterlari, workerlar mavjud.
- Canonical modelda 132 API: **27 explicit handler, 105 ta 501 placeholder**, yo'qolgan
  method/path yo'q. Handler mavjudligi to'liq acceptance bajarilganini bildirmaydi.
- Rejalashtirilgan Next.js frontend bu repositoryda hali mavjud emas.
- `pilot_ready=False`; barcha 42 AC bo'yicha E2E va backup/restore dalili hali yo'q.
- SMS/email va to'lovning jonli provayderi, haqiqiy browser/hardware passkey,
  MinIO/ClamAV va Docker deployment staging ushbu ko'rib chiqishda tekshirilmadi.

## Dalil va takrorlash

- Asosiy buyruq: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Test-Backend.ps1`.
  Python 3.12.10, native PostgreSQL 17.11, alohida disposable test bazasi.
  Natija `validation.json`da. Ogohlantirish: Starlette TestClient uchun httpx deprecation.
- Qo'shimcha diagnostika: `probe.py`; alohida random PostgreSQL bazasini yaratib,
  migratsiya va mavjud test fixturelarini ishlatadi, yakunda bazani o'chiradi.
  `FLEXBRIDGE_TEST_ADMIN_URL` alohida test serveriga yo'naltirilishi kerak.
  Natijalar `probe_results.json`da; sir/tokenlar yozilmagan.
- Diagnostikada privilege setup va opportunity publication SQL fixture orqali;
  matching va availability haqiqiy xizmat funksiyalari va haqiqiy PostgreSQL bilan.
- API inventari OpenAPI method/pathlarini canonical model bilan solishtiradi;
  placeholderlar generatorning `canonical_api_` operationIdsi orqali ajratiladi.
- `git diff --check` muvaffaqiyatli; Gitning LF/CRLF bildirishnomalari bor.
- Ishlatilgan test serveri to'xtatildi. Mavjud loyiha bazalari va ilova kodi o'zgartirilmadi.
  Ushbu reviewda faqat review artefaktlari va 01/03 jurnallar yangilandi.

## Keyingi kichik paket

`CAN-CODEX-001`dan oldin yuqoridagi matching/compensation xatolarini tuzatish va
tegishli regressiyalarni qo'shish. So'ng profil/malaka, CV bog'lash, canonical
availability va yo'l buferi bo'limini mavjud reja bo'yicha davom ettirish.
