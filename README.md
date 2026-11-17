# FlexBridge v1.4 — Milliy Talabalar va Yosh Mutaxassislar Smenali Bandlik Platformasi

![FlexBridge Architecture](https://img.shields.io/badge/Architecture-v1.4_PDF-blue?style=flat-square)
![Staging Suites](https://img.shields.io/badge/Staging_Suites-28%2F28_GREEN-emerald?style=flat-square)
![Frontend](https://img.shields.io/badge/Frontend-Next.js_16.4.6-black?style=flat-square)
![Backend](https://img.shields.io/badge/Backend-FastAPI_Python_3.12-teal?style=flat-square)
![Database](https://img.shields.io/badge/Database-PostgreSQL_17_+_PgBouncer-indigo?style=flat-square)
![Legal](https://img.shields.io/badge/Legal-O'zR_MK_118--modda-orange?style=flat-square)

FlexBridge — oliy ta'lim muassasalari talabalari va yosh mutaxassislarni dars jadvaliga mos smenali ish o‘rinlari, kafolatlangan rasmiy amaliyot bazalari va mentorlik tizimi bilan bog‘lovchi yagona milliy platforma. Tizim O‘zbekiston Respublikasi Mehnat Kodeksining 118-moddasi (o‘qishdan bo‘sh vaqtda ishlash kafolatlari) va Oliy ta'lim HEMIS axborot tizimi standartlariga to‘liq muvofiq ishlab chiqilgan.

---

> **Bo'limlar bo'yicha ish (2026-11-17)**: frontend — [`frontend/AGENTS.md`](frontend/AGENTS.md) va [`docs/frontend/`](docs/frontend/README.md); backend — [`backend/AGENTS.md`](backend/AGENTS.md) va [`docs/backend/`](docs/backend/README.md); staging va brauzer E2E — [`docs/operations/STAGING_VA_E2E.md`](docs/operations/STAGING_VA_E2E.md); hujjatlar xaritasi va AI xotirasi tartibi — [`docs/README.md`](docs/README.md).

## 1. Loyiha Mundarijasi & Fayllar Xaritasi

Loyiha qat'iy modulli arxitekturaga ega bo‘lib, **kod (`frontend/` va `backend/`)** hamda **hujjatlar (`docs/`)** to‘liq alohida papkalarga ajratilgan:

```
FlexBridge/
├── README.md                               # Asosiy repository qo'llanmasi (ushbu fayl)
├── AGENTS.md                               # Multi-agent hamkorlik protokoli va muzlatilgan main qoidasi
│
├── frontend/                               # Next.js 16.4.6 App Router frontend & Server-Side BFF (Faqat Frontend kodlari)
│   ├── src/app/                            # 72 ta sahifa va BFF API yo'nalishlari
│   │   ├── api/auth/                       # Login, logout, me, mfa sessiya boshqaruvi
│   │   ├── api/bff/                        # Tenant-chegaralangan va ommaviy BFF proxy yo'nalishlari
│   │   ├── nomzod/                         # Nomzod/Talaba yagona kabineti (Portfolio, Sertifikat, Rezyume PDF va b.)
│   │   ├── employer/                       # Ish beruvchi tashkilot kabineti (Kanban, Aqlli qidiruv, Billing, Jamoa)
│   │   ├── university/                     # OTM/Kafedra koordinator kabineti (Kundaliklar, Xulosalar, Analitika)
│   │   ├── operator/                       # Tizim operatori (SOC audit, break-glass, moliya)
│   │   ├── ishlar/[id]/                    # Vakansiya tafsilotlari va ariza topshirish oqimi
│   │   ├── kirish/                         # Mustaqil xavfsiz kirish sahifasi (MFA challenge bilan)
│   │   ├── royxatdan-otish/                # 3-bosqichli onboarding (SMS va Telegram Bot tasdig'i bilan)
│   │   ├── shartlar/                       # Foydalanish shartlari va yuridik qoidalar CMS
│   │   ├── maxfiylik/                      # Maxfiylik va Cookie siyosati CMS (AC-023)
│   │   └── haqida/                         # Platforma arxitekturasi va matching engine qo'llanmasi
│   ├── src/components/                     # Qayta ishlatiluvchi UI komponentlar (Navbar, Footer, Modallar)
│   ├── src/lib/                            # TypeScript API SDK va HttpOnly sessiya xavfsizligi
│   └── README.md                           # Frontend arxitekturasi qo'llanmasi
│
├── backend/                                # FastAPI Python 3.12 kanonik backend (Faqat Backend kodlari)
│   ├── app/api/v1/                         # 132+ kanonik REST endpointlar (API-001..API-125)
│   ├── app/core/                           # IAM xavfsizligi, AES shifrlash, WAF va tokenlar
│   ├── app/db/                             # SQLAlchemy 2.0 ombori, tranzaksiyalar va pgbouncer adapter
│   ├── app/services/                       # Domen xizmatlari (identifikatsiya, Telegram bot, jadval, amaliyot, billing)
│   ├── app/workers/                        # Tranzaksiyaviy outbox va identity delivery workerlari
│   ├── alembic/                            # 21 ta ketma-ket PostgreSQL 17 migratsiyalar
│   ├── tests/                              # Backend xavfsizlik va unit testlari
│   ├── FlexBridge_1_4_schema.sql           # Kanonik DDL sxemasi (PostgreSQL 17, 8 ta retention policy)
│   └── README.md                           # Backend ishga tushirish va validatsiya qo'llanmasi
│
├── docs/                                   # Barcha loyiha hujjatlari (.md, .pdf, .pptx, .txt) — ichki papkalarga bo'lingan
│   ├── journals/                           # 01..05 AI xotirasi, texnik modellar, bosqichlar va qarorlar jurnallari
│   ├── protocols/                          # ANTIGRAVITY_HANDOFF.md va ANTIGRAVITY_MASTER_PROTOCOL.md
│   ├── presentations/                      # Texnik topshiriq PDF, Investorlar taqdimoti va Ustoz uchun izohlar
│   ├── backend/                            # Backend domen hujjatlari (academic, candidate, organization, security_iam, platform_ops)
│   └── README.md                           # Hujjatlar katalogi xaritasi
│
├── infra/                                  # Docker Staging Orkestratsiyasi
│   ├── compose.yaml                        # 8 ta konteyner (backend, postgres, pgbouncer, minio, clamav, frontend, outbox, identity)
│   └── .env                                # Izolyatsiyalangan staging konfiguratsiyasi
│
├── scripts/                                # Avtomatlashtirilgan Staging Testlari & Regressiya
│   ├── run_all_staging_tests.py            # Barcha 28 ta test to'plamini ketma-ket yurgazuvchi master runner
│   ├── test_*_staging.py                   # 28 ta domen bo'yicha mustaqil staging test skriptlari
│   └── README.md                           # Sinov to'plamlari katalogi va yo'riqnomasi
│
├── specs/                                  # Tizim spetsifikatsiyalari va JSON modellari
│   ├── v1_3/                               # 1.3 texnik atlas va ma'lumotlar lug'ati
│   └── v1_4/FlexBridge_model_1_4.json      # To'liq mashinada o'qiluvchi 1.4 kanonik modeli
│
├── contracts/                              # R1 API shartnomalar matritsasi (r1_api_matrix.csv)
└── reviews/                                # Audit va PR tekshiruv hisobotlari
    └── 2026-11-*/                          # Har bir PR va milestone bo'yicha hujjatlashtirilgan auditlar
```

---

## 2. Platforma Portallari & Sahifalar Katalogi

| Bo‘lim | URL | Tavsif | Asosiy Shartnomalar |
| :--- | :--- | :--- | :--- |
| **Ommaviy E’lonlar** | `/` | Bo‘sh ish o‘rinlari qidiruvi, filtrlar va dars jadvaliga moslik ko‘rsatkichlari | `API-001`, `API-005` |
| **Vakansiya Tafsiloti** | `/ishlar/[id]` | Vakansiya shartlari, talablar, ariza topshirish va saqlash (bookmark) | `API-005`, `API-006` |
| **Tizimga Kirish** | `/kirish` | Telefon/Pochta orqali kirish, 2FA/TOTP tasdiqlash va rolli yo‘naltirish | `API-060`, `CAP-002` |
| **Ro‘yxatdan O‘tish** | `/royxatdan-otish` | 3-qadamli onboarding sehrgari (Rol, SMS OTP, profil, 12+ belgili parol) | `API-002`, `CAP-002` |
| **Nomzod Boshqaruv** | `/nomzod` | Profil ma’lumotlari, ko‘nikmalar, haftalik dars jadvali va OTM birikishi | `API-026`, `API-028`, `API-032` |
| **Nomzod Arizalari** | `/nomzod/arizalar` | Yuborilgan arizalar holati, intervyu javoblari, bekor qilish va qayta topshirish | `API-029`, `API-039`, `API-042` |
| **Nomzod Shartnomalari**| `/nomzod/shartnomalar`| Takliflar (Offers), ikki tomonlama tasdiq (Engagements) va amaliyot rejasi | `API-043`, `API-045`, `API-050` |
| **Amaliyot Kundaligi** | `/nomzod/kundalik` | Kunlik topshiriqlar, ish vaqti hisobi (8-soatlik limit), topshirish va sharhlar | `API-030`, `API-053`, `API-054` |
| **Nomzod Baholari** | `/nomzod/baholar` | Ikki tomonlama maxfiy baholash (Double-Blind), sharhlar va apellyatsiya | `API-047`, `API-057`, `API-058` |
| **Saqlangan E’lonlar** | `/nomzod/saqlanganlar` | Foydalanuvchi qiziqqan e’lonlar ro‘yxati (Bookmarks) | `API-004`, `API-037` |
| **Bildirishnomalar** | `/nomzod/bildirishnomalar`| Tizim xabarlari, filtrlash va bir marta bosishda o‘qilganlik tasdig‘i | `API-038`, `API-031` |
| **Xavfsizlik Markazi** | `/nomzod/xavfsizlik` | Parolni yangilash, 2FA (TOTP), 8 ta favqulodda zaxira kodi va sessiyalar | `API-060`, `API-061` |
| **Yordam & Maxfiylik** | `/nomzod/yordam` | Texnik murojaatlar (Tickets), GDPR huquqlari va bildirishnoma sozlamalari | `API-062`, `API-063`, `API-059` |
| **Ish Beruvchi Portali**| `/employer` | Kanban arizalar voronkasi, vakansiyalar, mentor biriktiruvi, hisob-kitob | `API-068`, `API-070`, `API-090` |
| **Universitet Portali** | `/university` | Kundaliklar navbati, amaliyot xulosalari, o‘qituvchilar taqsimoti, eksportlar | `API-100`, `API-105`, `API-108` |
| **Operator Portali** | `/operator` | SOC audit stream, verifikatsiya, 4-ko‘z break-glass, moliya solishtiruvi | `API-109`, `API-118`, `API-119` |
| **Foydalanish Shartlari**| `/shartlar` | Ommaviy litsenziya shartlari, AUP va xolis baholash reglamenti | `API-014`, `CAP-039` |
| **Maxfiylik Siyosati** | `/maxfiylik` | AC-023 differensial maxfiylik, cookie fayllari va ma’lumotlarni o‘chirish | `API-014`, `CAP-039` |
| **Platforma Haqida** | `/haqida` | Tizim arxitekturasi, matching engine tamoyillari va foydalanuvchi qo‘llanmalari | `API-013`, `CAP-039` |

---

## 3. Tezkor Ishga Tushirish (Quick Start)

### A. Docker Staging Stack (Mahalliy Ishga Tushirish)

FlexBridge to‘liq ishlab chiqarish muhitiga o‘xshash konteynerlashgan infrastrukturaga ega:

```powershell
# 1. Konteynerlarni ishga tushirish
docker compose -f infra/compose.yaml up -d

# 2. Barcha 8 ta konteyner holatini tekshirish
docker compose -f infra/compose.yaml ps
```

Ishlayotgan servislar:
- **Frontend**: `http://127.0.0.1:3000` (Next.js 16 SSR & BFF)
- **Backend**: `http://127.0.0.1:8000` (FastAPI Swagger `/docs`)
- **PgBouncer**: `127.0.0.1:5432` (PostgreSQL 17 tranzaksion pooling)
- **MinIO**: `http://127.0.0.1:9000` (S3 mos ob'ektlar xotirasi)
- **ClamAV**: `127.0.0.1:3310` (Virus va troyanlarga qarshi skanerlash)

### B. To‘liq Regressiya Testlarini Ishga Tushirish (28/28 Suites)

```powershell
# Master test runner yordamida barcha 28 ta to'plamni yurgazish:
python scripts/run_all_staging_tests.py
```

Kutilayotgan natija:
```
================================================================================
  REGRESSION RUN SUMMARY (Total Time: ~67s)
================================================================================
  SUCCESS: ALL 28 TEST SUITES PASSED 100% GREEN!
```

---

## 4. Arxitektura & Xavfsizlik Qoidalari

1. **Muzlatilgan `main` Tarmog‘i (Strict Invariant)**:
   - `origin/main` tarmog‘i commit `764fb98496fa40857acb07844fd09fcafa99b7d6` darajasida qat'iy muzlatilgan.
   - Barcha yangi ishlar faqat `integration/r1-agent-collaboration` tarmog‘iga PR orqali qo‘shiladi.
2. **`pg_live` Mutatsiyasi Taqiqi**:
   - Jonli ishlab chiqarish bazasiga (`backend/.data/pg_live`) hech qanday so‘rov yoki o‘zgartirish kiritilmaydi. Barcha testlar faqat PgBouncer (`127.0.0.1:5432/flexbridge`) orqali izolyatsiyalangan holda ishlaydi.
3. **BFF Xavfsizlik Qatlami**:
   - Brauzer klientlari to‘g‘ridan-to‘g‘ri backend bearer tokenlarini ko‘rmaydi.
   - Barcha autentifikatsiya AES-256-GCM bilan shifrlangan `HttpOnly` (`flexbridge_session`) kuki orqali amalga oshiriladi.
   - Mutatsiyaviy amallar `verifyCsrfOrigin` orqali CSRF hujumlaridan to‘liq himoyalangan.
