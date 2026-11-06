# FlexBridge — bosqichlar va bajarilish holati

Yangilangan: 2026-11-07 — Antigravity (`Gemini 4 Argon (High)`). Hozirgi holat: `S1.1..S1.4`, `S2.1.1` va `S2.1.2` bajarilib `Tekshiruvda` holatiga topshirildi (`DEFERRABLE` siklik FK tranzaksiya boshqaruvchisi, `audit_events`/`consent_events`/`billing_ledger` append-only himoyachisi va P1 moliya circuit-breaker `pytest`da `11/11` o'tdi); navbatdagi qadam — `S2.1.3` (`retention_policies` `DB-083` v1 va `feature_flags` `DB-092` servisi).

Holatlar: `Rejada`, `Jarayonda`, `Tekshiruvda`, `Tuzatish kerak`, `Bajarildi`, `Bloklangan`. Bloklangan bandda sabab va ochish sharti yoziladi. Mas'uli tayinlanmagan ish boshlanmagan hisoblanadi.

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
| S2.1 | Loyiha asosi va DB migratsiyalari | Jarayonda (`S2.1.1`, `S2.1.2` Tekshiruvda, navbatdagi `S2.1.3`) | Manbadagi sxema, constraint va tranzaksiyalar |
| S2.2 | Hisob, sessiya, tashkilot va vakolatlar | Rejada | Rol/scope, o'zini tasdiqlamaslik, revoke |
| S2.3 | Nomzod profili va bo'sh vaqt | Rejada | Vaqt intervallari va istisnolar |
| S2.4 | E'lon, smena va moslik | Rejada | Shartnoma, maosh shartlari, ALL/ANY; AC-039 |
| S2.5 | Ariza, suhbat, taklif, ish boshlanishi | Rejada | Holat o'tishlari va ikki tomon tasdig'i |
| S2.6 | Akademik amaliyot, tayinlov, kundalik | Rejada | Mentor/o'qituvchi ajratilishi, AC-040 |
| S2.7 | Xususiy fayllar, karantin, eksport | Rejada | Scan holati, ruxsat va signed URL; AC-042 |
| S2.8 | Tarif, kvota, to'lov va qaytarish | Rejada | Parallel limit, pul yaxlitligi, dual-control |
| S2.9 | Moderatsiya, audit va saqlash siyosati | Rejada | Scope, o'zgarmas tarix, asoslangan retention; AC-041 |
| S2.10 | Pilotga tayyorgarlik va operatsiyalar | Rejada | Mavjud AC talablari, tiklash, alert va qo'llab-quvvatlash dalillari |

### S2.1 va S2.2 bo'yicha maydalangan kichik ish paketlari (`S1.4` natijasi)

| Kichik ID | Kichik vazifa nomi | Holat | Mas'ul | Tegiladigan fayllar | Qabul va sinov mezoni |
| --- | --- | --- | --- | --- | --- |
| S2.1.1 | Backend ilova asosi, konfiguratsiya, `API-X05/X06` health va 1.4 DB migratsiya/invariant sinov paketi | Tekshiruvda | Antigravity (`Gemini 4 Argon (High)`) | `backend/pyproject.toml`, `backend/requirements.txt`, `backend/app/core/config.py`, `backend/app/db/schema.py`, `backend/app/main.py`, `backend/tests/test_s2_1_1_foundation.py` | FastAPI `/api/v1/health/live`, `/api/v1/health/ready`, `/api/v1/meta/schema-summary` ishlaydi; `pytest` (`6/6 passed`) orqali 94 jadval, 935 maydon, 214 FK va 17/17 PostgreSQL invariantlari avtomatik tekshirildi (Issue `#5`) |
| S2.1.2 | Tranzaksiya boshqaruvchisi (`SET CONSTRAINTS ALL IMMEDIATE` / `DEFERRABLE`), `audit_events` append-only yordamchisi va P1 circuit-breaker | Tekshiruvda | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/db/session.py`, `backend/app/core/audit.py`, `backend/app/core/circuit_breaker.py`, `backend/tests/test_s2_1_2_transactions_audit.py` | Siklik FK (`opportunity ↔ revision`, `thread ↔ message`) bitta atomik tranzaksiyada yozildi; `audit_events`, `consent_events`, `billing_ledger` va revision o'zgarmasligi hamda P1 moliya circuit-breaker `pytest`da (`11/11 passed`) tasdiqlandi (Issue `#7`) |
| S2.1.3 | `retention_policies` (`DB-083` v1 — 8 toifa) va `feature_flags` (`DB-092`) servisi | Rejada — navbatdagi | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/retention.py`, `backend/app/services/feature_flags.py`, `backend/tests/test_s2_1_3_retention_flags.py` | 8 ta huquqiy saqlash muddati (`30 kun` .. `75 yil`) va feature flag holatlari API hamda servis darajasida tekshiriladi |
| S2.2.1 | Autentifikatsiya, sessiya, Argon2id/TOTP va L1+Redis darhol revoke (`INV-15`, `AC-017`) | Rejada | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/auth.py`, `backend/app/api/v1/auth.py`, `backend/tests/test_s2_2_1_auth_revoke.py` | Parol/TOTP tekshiruvi, 15s kesh + event-driven revoke: sessiya bekor qilingan zahoti himoyalangan endpoint `401 AUTH_REVOKED` qaytaradi (`AC-017`) |
| S2.2.2 | Tashkilot a'zoligi, ikki shaxs qoidasi (`INV-11`) va `API-060` / `API-061` scope tekshiruvi (`INV-12`, `AC-041`) | Rejada | Antigravity (`Gemini 4 Argon (High)`) | `backend/app/services/governance.py`, `backend/app/api/v1/governance.py`, `backend/tests/test_s2_2_2_dual_control_scope.py` | O'z-o'zini tasdiqlash rad etiladi (`409 SELF_APPROVAL_FORBIDDEN`), begona korxona/muassasa obyekti `403 SCOPE_VIOLATION` oladi (`AC-041`) |

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
- Holat: `Tekshiruvda`
- Maqsad / doira / bog'liq vazifalar: `D:\FlexBridge` katalogidagi barcha manbalarni o'qib, 14 ta rol, ish va akademik amaliyot oqimlari (`S2.2..S2.10`), DB jadvallari/invariantlar (`INV-01..15`), API ruxsatlari, qabul mezonlari (`AC-017`, `AC-039..042`) va yetishmayotgan artefaktlar (`1.3` va `1.4` SQL/Atlas) holatini manbalarga bog'lab xaritaga tushirish (`S0.1..S0.4` ga tayanadi; `S1.2..S1.4` uchun asos bo'ladi).
- Tegiladigan fayllar: `05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md`, `01_AI_XOTIRASI_VA_QOIDALAR.md`, `02_TEXNIK_MODELLAR.md`, `03_BOSQICHLAR_VA_HOLAT.md`, `04_TAKLIFLAR_VA_TANLOVLAR.md`, `.gitignore`
- Qabul mezonlari: Ish/amaliyot oqimlari, 14 rol, mavjud AC/INV talablari va bo'shliqlar aniq manba sahifasi/qatori bilan bog'langan; topilgan `1.3` artefaktlar SHA-256 orqali tekshirilgan; ochiq tanlovlar uchun takliflar `04-fayl`ga yozilgan.
- Bajarilgan qism / qolgan qism: Barcha 5 ta manba (jumladan 27 slaydlik `.pptx` XML/notes) o'qildi; `05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md` tuzildi; lokal `D:\Codex\2026-10-26\sh\outputs\FlexBridge\` katalogidagi 41/41 ta `1.3` artefakt topildi va SHA-256 tekshiruvidan o'tkazildi. Qolgan qism: Codex tekshiruvi va foydalanuvchining `T-007`/`T-008` bo'yicha qarori.
- Tekshiruv dalili: `pypdf` (9 sahifa 1.4 PDF), `zipfile`+`xml.etree.ElementTree` (27 slayd `.pptx`), `checksums.json` SHA-256 tekshiruvi (`40/41` katalogda + `1/41` zip ichida, `reference_errors: 0`), GitHub Issue `#1` va PR.
- Codex xulosasi / tuzatishlar: `Kutilmoqda (Tekshiruvda)`
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
- Holat: `Tekshiruvda`
- Maqsad / doira / bog'liq vazifalar: `backend/` katalogida Python FastAPI ilova asosini (`app/core/config.py`, `app/db/schema.py`, `app/main.py`) yaratish, `API-X05` (`GET /api/v1/health/live`), `API-X06` (`GET /api/v1/health/ready`) va `GET /api/v1/meta/schema-summary` endpointlarini ishga tushirish hamda `pytest` orqali 94 jadval, 935 maydon, 214 FK, 8 ta retention policy (`DB-083`) va 17/17 PostgreSQL invariantlarini tekshirish (`S1.2..S1.4` ga tayanadi; `S2.1.2` uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/pyproject.toml`, `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/db/__init__.py`, `backend/app/db/schema.py`, `backend/app/main.py`, `backend/tests/test_s2_1_1_foundation.py`
- Qabul mezonlari: `API-X05` va `API-X06` endpointlari `200 OK` qaytaradi; PgBouncer (`80/20/400`), L1/Redis kesh (`15s`), signed URL (`60s`), PDF strukturaviy filtri (`50 bet / 5000 obyekt / 20 MB`, 8 ta taqiqlangan token) konfiguratsiyalari hamda 1.4 DB sxemasi `pytest` sinovidan 100% o'tadi.
- Bajarilgan qism / qolgan qism: Barcha 9 ta backend fayli yaratildi va `pytest` (`6/6 passed`) muvaffaqiyatli bajarildi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `6 passed in 0.62s`.
- Codex xulosasi / tuzatishlar: `Kutilmoqda (Tekshiruvda)`
- Keyingi kichik qadam: `S2.1.2` — Tranzaksiya boshqaruvchisi (`DEFERRABLE` / `SET CONSTRAINTS ALL IMMEDIATE`), `audit_events` append-only yordamchisi va P1 moliya circuit-breaker modulini yaratish.

### S2.1.2 — Tranzaksiya boshqaruvchisi (`DEFERRABLE`), `audit_events` append-only va P1 circuit-breaker (GitHub Issue #7)

- ID / nom: `S2.1.2` / Tranzaksiya boshqaruvchisi (`SET CONSTRAINTS ALL IMMEDIATE` / `DEFERRABLE`), `audit_events` append-only yordamchisi va P1 circuit-breaker
- Bosqich / manba: `S2.1` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (3.4, 6 va 7-bo'limlar; `INV-06`, `INV-11`, `INV-13`, `INV-16`)
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-07T00:08:22+05:00`
- Holat: `Tekshiruvda`
- Maqsad / doira / bog'liq vazifalar: Siklik FK juftliklari (`opportunities ↔ opportunity_revisions`, `daily_logs ↔ log_revisions`, `threads ↔ messages`) uchun `DEFERRABLE INITIALLY DEFERRED` va `SET CONSTRAINTS ALL IMMEDIATE` atomik tranzaksiya boshqaruvchisini (`app/db/session.py`), `audit_events`/`consent_events`/`billing_ledger` append-only hamda revision o'zgarmaslik himoyachisini (`app/core/audit.py`) va P1 moliya circuit-breaker modulini (`app/core/circuit_breaker.py`) yaratib `pytest`da tekshirish (`S2.1.1` ga tayanadi; `S2.1.3` va `S2.2..S2.9` uchun asos bo'ladi).
- Tegiladigan fayllar: `backend/app/db/session.py`, `backend/app/core/audit.py`, `backend/app/core/circuit_breaker.py`, `backend/tests/test_s2_1_2_transactions_audit.py`
- Qabul mezonlari: Siklik FK yozuvlari bitta atomik tranzaksiya ichida `SET CONSTRAINTS ALL IMMEDIATE` bilan muvaffaqiyatli yoziladi, uzilgan FK bo'lsa to'liq `ROLLBACK` bo'ladi; `audit_events`, `consent_events`, `billing_ledger` da `UPDATE`/`DELETE` `23514` bilan rad etiladi; P1 circuit-breaker `OPEN` holatda moliya operatsiyalarini bloklaydi va tiklashda ikki shaxs (`actor_id != second_approver_id`) talab qiladi.
- Bajarilgan qism / qolgan qism: Barcha 4 ta fayl yaratildi va `pytest` (`11/11 passed`) muvaffaqiyatli o'tdi. Qolgan qism: Codex tekshiruvi.
- Tekshiruv dalili: `python -m pytest D:\FlexBridge\backend -v` → `11 passed in 0.84s`.
- Codex xulosasi / tuzatishlar: `Kutilmoqda (Tekshiruvda)`
- Keyingi kichik qadam: `S2.1.3` — `retention_policies` (`DB-083` v1 — 8 toifa) va `feature_flags` (`DB-092`) servisini yaratish.
