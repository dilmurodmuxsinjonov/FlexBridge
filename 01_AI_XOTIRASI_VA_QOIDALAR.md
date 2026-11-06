# FlexBridge — AI xotirasi va ish qoidalari

Boshlanish: 2026-11-06. Ushbu to'rtta boshqaruv fayli barcha AIlar uchun umumiy ish xotirasidir.

## O'qish tartibi va manbalar

1. Shu fayl — rollar, mas'uliyat, ish tartibi va ish tarixi.
2. `02_TEXNIK_MODELLAR.md` — hujjatlarda ko'rsatilgan texnik vositalar va model tanlovlari.
3. `03_BOSQICHLAR_VA_HOLAT.md` — bajarilgan, joriy va keyingi ishlar.
4. `04_TAKLIFLAR_VA_TANLOVLAR.md` — takliflar va foydalanuvchi qarorlari.

Asosiy loyiha manbalari:
- `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` — 2026-11-05, texnik aniqlashtirishlar, DB/API tuzatishlari va AC-039..042.
- `FlexBridge_Ustoz_uchun_loyiha_izohi.md` — 2026-10-30, mahsulot maqsadi, foydalanuvchilar va biznes oqimlari.
- `FlexBridge_kelgusi_bosqichlar.md` — 2026-10-30, R1–R5 ishchi rivojlanish rejasi.
- `Oqish_tartibi.txt` — materiallar vazifasi va moliyaviy farazlar chegarasi.

Texnik tafovutlarda 1.4 hujjatidagi aniq tuzatish asos bo'ladi. U barcha avvalgi spetsifikatsiyalar o'rnini to'liq bosadi deb taxmin qilinmaydi. Foydalanuvchining keyingi aniq qarori tegishli eski qarorni almashtiradi; o'zgarish tarixi saqlanadi. Ziddiyat yoki yetishmayotgan talab taxmin bilan yopilmaydi, ochiq masala sifatida yoziladi.

## Rollar va mas'uliyat

- Foydalanuvchi — mahsulot egasi; takliflarni tanlaydi va doirani belgilaydi.
- Amalga oshiruvchi AI — asosiy dasturlashni bajaradi; o'z o'zgarishi, xatosi, tekshiruvi va topshirilgan qism uchun mas'ul. Hozircha nomi tayinlanmagan. (2026-11-06 yangilanishi, Q-009: amalga oshiruvchi AI sifatida `Antigravity`, model `Gemini 4 Argon (High)`, sessiya `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` ish boshladi.)
- Codex — tekshiruvchi va tuzatish kirituvchi. Talabga moslikni tekshiradi, xatolarni dalil bilan qayd etadi, zarur tuzatishni kiritadi va qayta tekshiradi. Hozirgi topshiriq doirasida asosiy ilova yozilmaydi.
- Har bir AI o'z haqiqiy nomi/CLI nomi, sessiya identifikatori va mavjud bo'lsa aniq model nomini yozadi. Noma'lum model taxmin qilinmaydi.
- Boshqa AI qatnashgani faqat u amalda ishlagan bo'lsa qayd etiladi. Ushbu tayyorlashda faqat Codex ishladi.

## Majburiy ish tartibi

1. Ish boshlashdan oldin to'rtta fayl va vazifaga tegishli asl manbalarni o'qing.
2. Bitta kichik vazifani ID bilan oling; maqsad, qabul mezoni, mas'ul va tegiladigan fayllarni 03-faylda yozing. Boshqa AI band qilgan faylni kelishmasdan tahrirlamang.
3. Butun tizimni yoki barcha modullarni birdan yozmang. Har topshiriq bitta tekshiriladigan kichik natija bersin: talab → o'zgarish → tegishli tekshiruv → topshirish.
4. O'z ishingiz tugaganda shu faylga o'z nomingiz bilan yozuv qo'shing, 03-fayldagi holatni yangilang. Texnik tanlov o'zgarsa 02-fayl, yangi taklif yoki qaror bo'lsa 04-fayl ham yangilanadi.
5. Amalga oshiruvchi topshirgan ish avval `Tekshiruvda` bo'ladi. Codex qabul mezonini va tegishli tekshiruv natijasini ko'rganidan keyin `Bajarildi` qiladi. Muammo bo'lsa `Tuzatish kerak` holati va aniq kamchilik yoziladi.
6. Tekshirilmagan ishni tayyor, ishlatilmagan modelni ishlatilgan, taklifni foydalanuvchi tanlovi deb yozmang. Buyruq ishga tushmagan bo'lsa sababi yozilsin.
7. Oldingi yozuvlarni o'chirmang; xato yozuvga tuzatish yozuvi qo'shing. Topshirishda qolgan ish va keyingi AI uchun davom nuqtasini ko'rsating.
8. Ish fayllari va natijalar `D:\FlexBridge` ichida saqlanadi. Maxfiy kalit, token, parol yoki shaxsiy dalil faylining mazmunini bu jurnallarga yozmang.

## Loyiha bo'yicha eslab qolish kerak bo'lgan asoslar

- FlexBridge: 18+ nomzodlar uchun vaqt va malakaga mos yarim stavkali ish, umumiy va akademik amaliyot. Frilans keyingi bosqich (`Q-011`, 2026-11-07: foydalanuvchi alohida eslatdi — keyinchalik `R2` da frilanserlik qo'shiladi, lekin hozir `R1` da frilanserlik qo'shilmaydi; arxitektura va `R2_FREELANCE_MARKETPLACE=False` bayrog'i keyingi kengayishga tayyor turadi).
- Ish va akademik amaliyot alohida oqimlar; mentorning ish xulosasi bilan o'qituvchining akademik xulosasi ajratiladi.
- Nomzodning ish qidirishi va arizasi bepul; oddiy ish maoshidan ulush olinmaydi.
- Hozir papkada ilova kodi, ishga tushirish konfiguratsiyasi yoki amaldagi mahsulot dalili yo'q.
- 1.4 PDF 94 jadval, 935 maydon, 214 FK, 14 rol, 40 CAP, 48 sahifa va 42 AC haqida ma'lumot beradi. Bu sonlar hujjat bayonoti, mavjud kod tekshiruvi natijasi emas.
- PDFda tilga olingan `FlexBridge_1_4_schema.sql`, 1.3 to'liq texnik topshirig'i va Baza/API atlasi papkada mavjud emas. To'liq sxema va APIlar taxminan tiklanmaydi.
- 1.4 hujjatidagi retention va huquqiy muvofiqlik bayonotlari mustaqil tekshirilmagan; bu fayllar ularni huquqiy tasdiq deb belgilamaydi.

## Har bir AI uchun yozuv shakli

```text
Yozuv ID / sana-vaqt va vaqt zonasi:
AI / sessiya / model (noma'lum bo'lsa shunday yozing):
Vazifa ID / rol:
Boshlang'ich holat va maqsad:
Qilingan ish / o'zgargan fayllar:
Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
Muammo va cheklov:
Topshirilgan holat / keyingi qadam:
Tekshiruvchi AI / tekshiruv natijasi:
```

## Ish tarixi

### LOG-001 — 2026-11-06, Asia/Tashkent — Codex

- Rol: tekshiruvchi va hujjatlarni tayyorlovchi; modelning aniq nomi sessiyada berilmagan.
- Vazifa: S0.1–S0.4. Foydalanuvchi so'ragan 4 ta boshqaruv fayli tayyorlandi.
- O'qilgan manbalar: yuqoridagi uchta matnli loyiha hujjati va 1.4 PDFning barcha 9 sahifasi matni. Investor taqdimoti va uning PDFi mazmunan tekshirilmagan.
- Aniqlangan cheklov: to'liq SQL sxema va eski atlas yo'q; texnik stekning hammasi ham berilmagan. Farazlar foydalanuvchi qarori sifatida qayd etilmadi.
- Muhit: PDF matnini o'qish uchun lokal Python muhitiga `pypdf` o'rnatildi; bu ilova dependencylari tasdiqlangani degani emas.
- Tekshiruv: yaratilgan fayllarning mavjudligi, UTF-8 o'qilishi va o'zaro havolalari tekshirildi. Ilova kodi yozilmadi va ilova sinovlari bajarilmadi.
- Keyingi qadam: S1.1 — amalga oshiruvchi AI mavjud manbalar bo'yicha talablar xaritasini tuzadi, yetishmayotgan spetsifikatsiyalarni alohida qayd etadi.

### LOG-002 — 2026-11-06T23:30:00+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-002` / `2026-11-06T23:30:00+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S1.1` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: S0 yakunlangan (`LOG-001`), Git repozitoriy va masofaviy GitHub (`https://github.com/dilmurodmuxsinjonov/FlexBridge.git`) ulanmagan, `S1.1` (`Mavjud talablar va manbalar xaritasi`) `Rejada — navbatdagi` holatida edi. Maqsad: foydalanuvchi talabi bilan GitHub repozitoriysini ulash (`main` + Issue `#1` + `feature/s1-1-requirements-map` tarmog'i), barcha mavjud manbalarni (jumladan `FlexBridge_Investorlar_uchun.pptx` 27 slayd XML va izohlarini) to'liq o'qib, ish/amaliyot oqimlari, 14 ta rol, invariantlar (`INV-01..15`), qabul mezonlari (`AC-001..042`) va yetishmayotgan artefaktlar xaritasini tuzish.
- Qilingan ish / o'zgargan fayllar:
  - `.gitignore` yaratildi va S0 boshlang'ich fayllari `origin/main` ga yuklandi (`0f71968`).
  - GitHub Issue `#1` (`S1.1: Mavjud talablar va manbalar xaritasi`) ochildi va `feature/s1-1-requirements-map` tarmog'i yaratildi.
  - `05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md` yaratildi: 5 ta manba fayli, 14 ta rol, 8 ta asosiy biznes/texnik oqim (`S2.2..S2.10` kesimida), `INV-01..15`, `AC-017` va `AC-039..042` hamda lokal diskda (`D:\Codex\2026-10-26\sh\outputs\FlexBridge\`) topilgan 1.3 texnik paket auditi manbalar bilan bog'landi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md`, `02_TEXNIK_MODELLAR.md`, `03_BOSQICHLAR_VA_HOLAT.md`, `04_TAKLIFLAR_VA_TANLOVLAR.md` yangilandi (`Q-008`, `Q-009` qarorlari hamda `S1.2`/`S1.3` uchun `T-007`, `T-008` takliflari kiritildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `pypdf` orqali `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (9 sahifa) va `zipfile`+`xml.etree.ElementTree` orqali `FlexBridge_Investorlar_uchun.pptx` (27 slayd va izohlar) to'liq o'qildi.
  - Lokal `D:\Codex\2026-10-26\sh\outputs\FlexBridge\checksums.json` bo'yicha Python skripti orqali SHA-256 tekshiruvi bajarildi: `40/41` fayl ochiq katalogda va `1/41` (`FlexBridge_interaktiv_atlas.html`) `FlexBridge_toliq_texnik_paket_1_3.zip` ichida 100% mos (`reference_errors: 0`).
  - `git status`, `git diff`, `gh issue list` orqali repozitoriy va jurnal fayllari izchilligi tekshirildi. Ilova kodi yozilmadi.
- Muammo va cheklov: `D:\FlexBridge` ichida `FlexBridge_1_4_schema.sql` hali yaratilmagan va `1.3` artefaktlar (`D:\Codex\2026-10-26\sh\outputs\FlexBridge\`) ishchi katalogga ko'chirilmagan; bular `S1.2` doirasida va `T-007` taklifi asosida hal qilinadi.
- Topshirilgan holat / keyingi qadam: `S1.1` `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: Codex `S1.1` natijasini (`05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md` va `01..04` yangilanishlarini) tekshirib `Bajarildi` qiladi; so'ngra foydalanuvchi `T-007` va `T-008` bo'yicha qaror bergach `S1.2` va `S1.3` bajariladi.
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-003 — 2026-11-06T23:58:00+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-003` / `2026-11-06T23:58:00+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S1.2`, `S1.3`, `S1.4` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: Foydalanuvchi (`Q-010`: `"qarorlarni toliq ihtiyoringa qol;diraman qurishni davom etir"`) texnik va arxitektura qarorlarini (`T-007` Variant A va `T-008` Variant A) tasdiqladi hamda qurishni davom ettirishni topshirdi. Maqsad: GitHub Issue `#3` va `feature/s1-2-specs-and-v1-4-schema` tarmog'ida `1.3` spetsifikatsiyalarini `D:\FlexBridge\specs\v1_3\` ga ko'chirish, `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` dagi barcha o'zgarishlarni qo'llab `FlexBridge_1_4_schema.sql` va `FlexBridge_model_1_4.json` (94 jadval / 935 maydon / 214 FK) ni yaratish, real PostgreSQL (PGlite 0.5.15 / PostgreSQL 18.6 WASM + `btree_gist`) dvigatelida barcha invariantlarni (`INV-01..16`, `AC-039..042`) sinovdan o'tkazish hamda `S2.1` kichik ish paketlarini (`S2.1.1..S2.1.3`) tayyorlash.
- Qilingan ish / o'zgargan fayllar:
  - `specs/v1_3/` ichiga `D:\Codex\2026-10-26\sh\outputs\FlexBridge\` dagi 25 ta kanonik 1.3 artefakt (`schema_loyihasi.sql`, `FlexBridge_model_1_3.json`, CSV/MD lug'atlar, `checksums.json`, `audit_hisoboti.json`) nusxalandi va SHA-256 nazorat summasi 100% tasdiqlandi.
  - `specs/v1_4/build_v1_4_specs.py` generator skripti yozildi va ishga tushirildi; natijada `specs/v1_4/FlexBridge_model_1_4.json`, `specs/v1_4/FlexBridge_1_4_schema.sql` va ildiz katalogdagi `FlexBridge_1_4_schema.sql` yaratildi.
  - `specs/v1_4/verify_v1_4_schema.mjs` avtomatlashtirilgan PostgreSQL invariant sinov skripti yozildi va ishga tushirilib, natijasi `specs/v1_4/v1_4_schema_verification.json` fayliga saqlandi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md`, `02_TEXNIK_MODELLAR.md`, `03_BOSQICHLAR_VA_HOLAT.md`, `04_TAKLIFLAR_VA_TANLOVLAR.md` yangilandi (`Q-010`, `T-007`/`T-008` tanlovlari va `S2.1.1..S2.2.2` kichik vazifa paketlari kiritildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python D:\FlexBridge\specs\v1_4\build_v1_4_specs.py` → `tables: 94`, `fields: 935`, `foreign_keys: 214`, `roles: 14`, `capabilities: 40`, `pages: 48`, `sections: 131`, `api_contracts: 124`, `helper_apis: 8`, `acceptance_criteria: 42`, `reference_errors: 0`.
  - `node D:\FlexBridge\specs\v1_4\verify_v1_4_schema.mjs` → PostgreSQL 18.6 (`@electric-sql/pglite` + `btree_gist` kengaytmasi) ichida `FlexBridge_1_4_schema.sql` to'liq bajarildi va **17/17 ta invariant sinovi muvaffaqiyatli o'tdi (`all_checks_passed: true`)**:
    1. `94` base jadval va `935` non-generated ustun (`+4` stored generated `minute_range` = jami `939` ustun);
    2. `btree_gist` va 4 ta `EXCLUDE USING gist (... WITH &&)` qoidasi (`INV-01..02`);
    3. `availability_rules` ustma-ust tushuvchi intervalni `23P01` xatosi bilan rad etdi (`INV-01`);
    4. `opportunity_shifts` ustma-ust tushuvchi bir xil `group_code` smenasini `23P01` bilan rad etdi (`INV-02`);
    5. `opportunity_revisions` noto'g'ri maosh kombinatsiyasini (`hourly` + `stipend_amount > 0`) `23514` bilan rad etdi (`INV-03`, `AC-039`);
    6. `opportunity_revisions` haqiqiy soatbay maoshni qabul qildi (`INV-03`);
    7. Siklik FK (`opportunities ↔ opportunity_revisions`) bitta tranzaksiya ichida `SET CONSTRAINTS ALL IMMEDIATE` bilan muvaffaqiyatli o'tdi (`INV-06`);
    8. `application_attempts` boshqa e'longa tegishli `application_id + opportunity_id` ni `23503` composite FK bilan rad etdi (`INV-08`);
    9. `placements` noto'g'ri e'longa bog'langan taklifni `23503` composite FK bilan rad etdi (`INV-08`);
    10. `workplace_log_reviews` va `academic_log_reviews` boshqa placement kundaligini `23503` bilan rad etdi (`INV-09`, `AC-040`);
    11. `service_entitlements` kvota/ta'rif qoidasiga zid qiymatni `23514` bilan rad etdi (`INV-04`);
    12. `payment_attempts` va `invoices` pul/valyuta nomutanosibligini `23503`/`23514` bilan rad etdi (`INV-05`, `INV-10`);
    13. `organization_members` va `refunds` o'z-o'zini tasdiqlashni (`created_by = approved_by` yoki `requested_by = approved_by`) `23514` bilan rad etdi (`INV-11`);
    14. `audit_events` (`UPDATE`/`DELETE`) o'zgarmaslik triggeri (`P0001: audit_events is append-only`) bilan bloklandi (`INV-13`);
    15. `files` jadvalida `scan_status != 'clean'` bo'lgan faylni `visibility = 'private_ready'` qilish `23514` bilan rad etildi (`INV-14`, `AC-042`);
    16. `retention_policies` jadvalida 8 ta v1 saqlash qoidasi (`30 kun` .. `75 yil`) mavjudligi tasdiqlandi (`DB-083`);
    17. `moderation_actions` jadvalida `policy_code`, `reason_code`, `justification` majburiyligi tasdiqlandi (`AC-041`).
- Muammo va cheklov: Yo'q; barcha 17/17 sxema invariantlari real PostgreSQL dvigatelida tasdiqlandi.
- Topshirilgan holat / keyingi qadam: `S1.2`, `S1.3` va `S1.4` `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.1.1` — `backend/` katalogida FastAPI ilova asosi, konfiguratsiya, `/api/v1/health/live`, `/api/v1/health/ready` (`API-X05`, `API-X06`) va 1.4 DB sxema/invariant `pytest` paketini yaratish.
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-004 — 2026-11-07T00:05:30+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-004` / `2026-11-07T00:05:30+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.1.1` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S1.2..S1.4` yakunlanib PR `#4` (`5155b17`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#5` va `feature/s2-1-1-backend-db-foundation` tarmog'ida `backend/` Python FastAPI ilova asosini, `1.4 PDF` xavfsizlik/sig'im konfiguratsiyasini (`app/core/config.py`), `1.4` sxema va `DB-083` 8 ta retention policy tekshirgichini (`app/db/schema.py`), `API-X05` (`/api/v1/health/live`) va `API-X06` (`/api/v1/health/ready`) endpointlarini (`app/main.py`) hamda avtomatlashtirilgan `pytest` sinov to'plamini (`tests/test_s2_1_1_foundation.py`) yaratish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/pyproject.toml`, `backend/requirements.txt` yaratildi.
  - `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/core/config.py` yaratildi (PgBouncer `80/20/400`, L1/Redis `15s` TTL, `quarantine/` va `60s` signed URL, PDF `50 bet / 5000 obyekt / 20 MB` va 8 ta taqiqlangan PDF tokeni, P1 moliya circuit-breaker).
  - `backend/app/db/__init__.py`, `backend/app/db/schema.py` yaratildi (`FlexBridge_model_1_4.json`, `FlexBridge_1_4_schema.sql`, `DB-083` 8 ta retention policy v1 va `v1_4_schema_verification.json` yuklagichlari).
  - `backend/app/main.py` yaratildi (`GET /api/v1/health/live`, `GET /api/v1/health/ready`, `GET /api/v1/meta/schema-summary`).
  - `backend/tests/test_s2_1_1_foundation.py` yaratildi (6 ta avtomatlashtirilgan `pytest` testi).
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi.
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`6 passed in 0.62s`** (`test_api_x05_health_live`, `test_api_x06_health_ready`, `test_1_4_security_and_pool_configuration`, `test_schema_and_model_1_4_exact_counts`, `test_db_083_retention_policies_v1`, `test_postgres_1_4_invariant_report_completeness`).
- Muammo va cheklov: Dastlabki test ishga tushirilishida `model["counts"]` o'rniga `model["stats"]` va `trg_guard_audit_events` o'rniga `trg_immutable_audit_events` kaliti aniqlandi hamda darhol tuzatilib `6/6` o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.1.1` `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.1.2` — Tranzaksiya boshqaruvchisi (`DEFERRABLE` / `SET CONSTRAINTS ALL IMMEDIATE`), `audit_events`/`consent_events`/`billing_ledger` append-only yordamchisi va P1 moliya circuit-breaker modulini yaratish.
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-005 — 2026-11-07T00:09:00+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-005` / `2026-11-07T00:09:00+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.1.2` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S2.1.1` yakunlanib PR `#6` (`9ff7e8b`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#7` va `feature/s2-1-2-transactions-audit-circuit-breaker` tarmog'ida siklik FKlar uchun `DEFERRABLE` / `SET CONSTRAINTS ALL IMMEDIATE` tranzaksiya boshqaruvchisini (`app/db/session.py`), `audit_events`, `consent_events`, `billing_ledger` append-only va revision o'zgarmaslik himoyachisini (`app/core/audit.py`) hamda P1 moliya circuit-breaker modulini (`app/core/circuit_breaker.py`) yozib `pytest` orqali tekshirish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/app/db/session.py` yaratildi (`DeferredUnitOfWork`, `atomic_deferred`, `create_opportunity_with_initial_revision`, `create_thread_with_first_message`).
  - `backend/app/core/audit.py` yaratildi (`AppendOnlyAuditStore`, `guard_opportunity_revision_update`, `guard_log_revision_update`).
  - `backend/app/core/circuit_breaker.py` yaratildi (`FinanceCircuitBreaker` — P1 hodisasida moliya operatsiyalarini `P1_FINANCE_CIRCUIT_OPEN` bilan muzlatish va ikki shaxs tasdig'i bilan tiklash).
  - `backend/tests/test_s2_1_2_transactions_audit.py` yaratildi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi.
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`11 passed in 0.84s`** (`S2.1.1` 6 ta test + `S2.1.2` 5 ta test: `test_deferred_circular_fk_opportunity_and_thread_success`, `test_deferred_circular_fk_rollback_on_broken_reference`, `test_append_only_audit_consent_and_billing_ledger`, `test_published_opportunity_and_submitted_log_revision_immutability`, `test_p1_finance_circuit_breaker_and_dual_control_reset`).
- Muammo va cheklov: Yo'q; barcha testlar birinchi urinishda 100% o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.1.2` `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.1.3` — `retention_policies` (`DB-083` v1 — 8 toifa) va `feature_flags` (`DB-092`) servisi hamda testlarini yaratib `S2.1` bo'limini yakunlash.
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-006 — 2026-11-07T00:11:30+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-006` / `2026-11-07T00:11:30+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.1.3` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S2.1.2` yakunlanib PR `#8` (`1853545`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#9` va `feature/s2-1-3-retention-and-feature-flags` tarmog'ida `DB-083 retention_policies` v1 (8 ta toifa, `UNPUBLISHED_DRAFT` 23-kun ogohlantirish / 30-kun tozalash, `APPLICATION_AND_SNAPSHOT` 365-kun anonimlashtirish, `BILLING_AND_FISCAL_LEDGER` 1825-kun saqlash va `chk_retention_legal_basis`) servisini (`app/services/retention.py`) hamda `DB-092 feature_flags` servisini (`app/services/feature_flags.py`) yaratish va `pytest`da tekshirish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/app/services/__init__.py`, `backend/app/services/retention.py` yaratildi.
  - `backend/app/services/feature_flags.py` yaratildi.
  - `backend/tests/test_s2_1_3_retention_flags.py` yaratildi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi (`S2.1` to'liq `Tekshiruvda` holatiga o'tkazildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`14 passed in 0.81s`** (`S2.1.1` 6 ta test + `S2.1.2` 5 ta test + `S2.1.3` 3 ta test: `test_retention_policy_v1_lifecycle_decisions`, `test_retention_policy_legal_basis_validation`, `test_feature_flags_r1_vs_r2_defaults_and_org_overrides`).
- Muammo va cheklov: Yo'q; barcha testlar xatosiz o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.1.3` (va butun `S2.1`) `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.2.1` — Autentifikatsiya, sessiya, Argon2id/TOTP va L1+Redis darhol revoke (`INV-15`, `AC-017`) modulini yaratish.
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-007 — 2026-11-07T00:14:30+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-007` / `2026-11-07T00:14:30+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.2.1` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S2.1.3` yakunlanib PR `#10` (`d35bb6d`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#11` va `feature/s2-2-1-auth-session-revoke` tarmog'ida 18+ foydalanuvchi ro'yxatdan o'tishi, Argon2id parol xeshi, RFC 6238 TOTP ikki bosqichli tasdiqlash hamda 15s L1/Redis ruxsat keshi + darhol revoke (`INV-15`, `AC-017`) xizmati va FastAPI `/api/v1/auth/*` endpointlarini yaratib `pytest`da tekshirish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/app/services/auth.py` yaratildi (`AuthSessionService`, `hash_password`, `verify_password`, `generate_totp_code`, `validate_session`, `revoke_session`, `revoke_all_user_sessions`).
  - `backend/app/api/__init__.py`, `backend/app/api/v1/__init__.py`, `backend/app/api/v1/auth.py` yaratildi (`POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/sessions/{session_id}/revoke`, `GET /api/v1/auth/me`) va `backend/app/main.py` ga ulandi.
  - `backend/tests/test_s2_2_1_auth_revoke.py` yaratildi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi.
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`17 passed in 1.19s`** (`S2.1` 14 ta test + `S2.2.1` 3 ta test: `test_register_requires_18_plus_adult_declaration`, `test_login_with_totp_and_ac_017_immediate_session_revocation`, `test_revoke_all_user_sessions_on_membership_or_role_change`).
- Muammo va cheklov: Yo'q; barcha testlar birinchi urinishda 100% o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.2.1` `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.2.2` — Tashkilot a'zoligi, ikki shaxs qoidasi (`INV-11`) va `API-060` / `API-061` scope tekshiruvi (`INV-12`, `AC-041`).
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-008 — 2026-11-07T00:18:00+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-008` / `2026-11-07T00:18:00+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.2.2` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S2.2.1` yakunlanib PR `#12` (`a3305be`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#13` va `feature/s2-2-2-dual-control-and-scope` tarmog'ida tashkilot a'zoligi uchun Ikki shaxs qoidasi (`INV-11`: `created_by != approved_by`), tashkilotlararo va oliygohlararo scope chegarasi (`INV-12`, `AC-041`), `API-060` va `API-061` rol/muassasa tekshiruvlari hamda moderatsiya asoslari (`policy_code`, `reason_code`, `justification >= 15`) xizmatini (`app/services/governance.py`, `app/api/v1/governance.py`) yaratish va `pytest`da tekshirish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/app/services/governance.py` yaratildi (`GovernanceScopeService`: `create_org_member_request`, `approve_org_member`, `create_academic_assignment_api_060`, `update_academic_assignment_api_061`, `record_moderation_action`).
  - `backend/app/api/v1/governance.py` yaratildi va `backend/app/main.py` ga ulandi.
  - `backend/tests/test_s2_2_2_dual_control_scope.py` yaratildi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi (`S2.2` to'liq `Tekshiruvda` holatiga o'tkazildi, `S2.3.1` va `S2.4.1` rejalashtirildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`20 passed in 1.28s`** (`S2.1` 14 ta test + `S2.2.1` 3 ta test + `S2.2.2` 3 ta test: `test_inv_11_dual_control_blocks_self_approval_and_cross_org_scope`, `test_api_060_and_api_061_role_and_institution_scope_ac_041`, `test_moderation_action_requires_policy_reason_and_justification_ac_041`).
- Muammo va cheklov: Yo'q; barcha 20 ta test xatosiz o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.2.2` (va butun `S2.2`) `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.3.1` — Nomzod profili, `int4range(start_minute, end_minute, '[)')` bo'sh vaqt qoidalari va istisnolari (`INV-01`).
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-009 — 2026-11-07T00:21:00+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-009` / `2026-11-07T00:21:00+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.3.1` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S2.2.2` yakunlanib PR `#14` (`19a1996`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#15` va `feature/s2-3-1-candidate-availability` tarmog'ida nomzodning haftalik bo'sh vaqt qoidalari (`DB-013 availability_rules`) va sana istisnolari (`DB-014 availability_exceptions`) uchun yarim-ochiq `[start_minute, end_minute)` (`int4range`) hamda `INV-01` (`23P01` ustma-ust tushmaslik) xizmatini (`app/services/availability.py`, `app/api/v1/availability.py`) yaratish va `pytest`da tekshirish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/app/services/availability.py` yaratildi (`CandidateAvailabilityService`, `ranges_overlap`, `range_contains`, `add_availability_rule`, `add_availability_exception`, `is_candidate_available_for_shift`).
  - `backend/app/api/v1/availability.py` yaratildi va `backend/app/main.py` ga ulandi.
  - `backend/tests/test_s2_3_1_availability.py` yaratildi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi (`S2.3` `Tekshiruvda` holatiga o'tkazildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`22 passed in 1.28s`** (`S2.1` 14 ta + `S2.2` 6 ta + `S2.3.1` 2 ta test: `test_inv_01_half_open_availability_rules_overlap_and_adjacency`, `test_inv_01_availability_exceptions_and_bounds`).
- Muammo va cheklov: Yo'q; barcha 22 ta test xatosiz o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.3.1` (`S2.3`) `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.4.1` — E'lon reviziyasi (`contract_type`, maosh matritsasi), `group_code` smena guruhi va `API-003` (`ALL`/`ANY`) moslik dvigateli (`INV-02`, `INV-03`, `AC-039`).
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-010 — 2026-11-07T00:24:30+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-010` / `2026-11-07T00:24:30+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.4.1` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S2.3.1` yakunlanib PR `#16` (`47a6181`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#17` va `feature/s2-4-1-opportunities-and-matching-ac-039` tarmog'ida `opportunity_revisions` (`DB-026`) `contract_type` va maosh (`HOURLY`/`STIPEND`/`UNPAID_ACADEMIC`) matritsasi (`INV-03`, `AC-039`), `opportunity_shifts` (`DB-027`) `group_code` smena guruhi (`INV-02`) hamda `API-003` (`GET /api/v1/opportunities/feed`) `ALL_SHIFTS_IN_GROUP` vs `ANY_SHIFT_IN_GROUP` moslik dvigatelini (`app/services/opportunities.py`, `app/api/v1/opportunities.py`) yaratish va `pytest`da tekshirish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/app/services/opportunities.py` yaratildi (`OpportunityMatchingService`, `validate_compensation_contract_matrix`, `create_opportunity_revision`, `add_opportunity_shift`, `match_candidate_feed_api_003`).
  - `backend/app/api/v1/opportunities.py` yaratildi va `backend/app/main.py` ga ulandi.
  - `backend/tests/test_s2_4_1_matching_ac_039.py` yaratildi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi (`S2.4` `Tekshiruvda` holatiga o'tkazildi, `S2.5.1..S2.8.1` kichik paketlari jadvalga qo'shildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`24 passed in 1.32s`** (`S2.1..S2.3` 22 ta + `S2.4.1` 2 ta test: `test_ac_039_contract_type_and_compensation_matrix_inv_03`, `test_ac_039_api_003_all_vs_any_shift_matching_and_exceptions`).
- Muammo va cheklov: Yo'q; barcha 24 ta test xatosiz o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.4.1` (`S2.4`) `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.5.1` — Ariza, suhbat, taklif, ikki tomon tasdiqlagan ish boshlanishi (`placements`) va `INV-08` cross-table FK.
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-011 — 2026-11-07T00:27:30+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-011` / `2026-11-07T00:27:30+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.5.1` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S2.4.1` yakunlanib PR `#18` (`41ed9b2`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#19` va `feature/s2-5-1-placements-inv-08` tarmog'ida `applications`, `application_attempts`, `offers` va `placements` uchun `INV-08` cross-table composite FK (`23503`) tekshiruvlarini hamda nomzod va korxona ikki tomonlama ish boshlanishini tasdiqlash (`PENDING_START_CONFIRMATION` -> `ACTIVE`) oqimini (`app/services/placements.py`, `app/api/v1/placements.py`) yaratish va `pytest`da tekshirish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/app/services/placements.py` yaratildi (`ApplicationPlacementService`, `create_application`, `create_application_attempt`, `create_offer`, `create_placement`, `confirm_placement_start`).
  - `backend/app/api/v1/placements.py` yaratildi va `backend/app/main.py` ga ulandi.
  - `backend/tests/test_s2_5_1_placements_inv_08.py` yaratildi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi (`S2.5` `Tekshiruvda` holatiga o'tkazildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`26 passed in 1.41s`** (`S2.1..S2.4` 24 ta + `S2.5.1` 2 ta test: `test_inv_08_application_attempts_and_placements_composite_fk_scope`, `test_placement_requires_two_party_start_confirmation`).
- Muammo va cheklov: Yo'q; barcha 26 ta test xatosiz o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.5.1` (`S2.5`) `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.6.1` — Akademik amaliyot, tayinlov, kundalik (`daily_logs`, `log_revisions`) va mentor vs o'qituvchi bahosi ajratilishi (`INV-09`, `AC-040`).
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-012 — 2026-11-07T00:31:00+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-012` / `2026-11-07T00:31:00+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.6.1` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S2.5.1` yakunlanib PR `#20` (`d2cc277`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#21` va `feature/s2-6-1-internship-diary-ac-040` tarmog'ida amaliyot kundaligi (`daily_logs`, `log_revisions`) uchun korxona mentori (`workplace_log_reviews`) va oliygoh/texnikum o'qituvchisi (`academic_log_reviews`) baholarining alohida saqlanishi (`AC-040`) hamda `INV-09` composite FK (`23503`) tekshiruvini (`app/services/internship_logs.py`, `app/api/v1/internship_logs.py`) yaratish va `pytest`da tekshirish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/app/services/internship_logs.py` yaratildi (`InternshipLogService`, `create_mentor_assignment`, `create_academic_assignment`, `create_daily_log_with_revision`, `submit_workplace_log_review`, `submit_academic_log_review`).
  - `backend/app/api/v1/internship_logs.py` yaratildi va `backend/app/main.py` ga ulandi.
  - `backend/tests/test_s2_6_1_internship_diary_ac_040.py` yaratildi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi (`S2.6` `Tekshiruvda` holatiga o'tkazildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`27 passed in 1.44s`** (`S2.1..S2.5` 26 ta + `S2.6.1` 1 ta kompleks test: `test_ac_040_inv_09_workplace_vs_academic_log_reviews_and_placement_scope`).
- Muammo va cheklov: Yo'q; barcha 27 ta test xatosiz o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.6.1` (`S2.6`) `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.7.1` — Xususiy fayllar, `quarantine/` skaneri (`ClamAV` + `pypdf` 8 ta token / `50 bet / 5000 obyekt / 20 MB`) va 60s signed URL (`INV-14`, `AC-042`).
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`

### LOG-013 — 2026-11-07T00:34:00+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-013` / `2026-11-07T00:34:00+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S2.7.1` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: `S2.6.1` yakunlanib PR `#22` (`a806d5f`) `main` ga birlashtirildi. Maqsad: GitHub Issue `#23` va `feature/s2-7-1-files-quarantine-ac-042` tarmog'ida `DB-018 files` uchun `quarantine/` prefiksi, `ClamAV` + `pypdf` strukturaviy skaneri (`50 bet / 5000 obyekt / 20 MB` va 8 ta taqiqlangan token) hamda `API-X01..X03` 60s signed URL xizmatini (`app/services/files_quarantine.py`, `app/api/v1/files.py`) yaratish va `AC-042` (`PENDING_SCAN`/`QUARANTINED` faylga signed URL bermaslik) qoidasini `pytest`da tekshirish.
- Qilingan ish / o'zgargan fayllar:
  - `backend/app/services/files_quarantine.py` yaratildi (`FileQuarantineService`, `scan_pdf_bytes_and_structure`, `initiate_upload_api_x01`, `complete_and_scan_api_x02`, `issue_signed_download_url_api_x03`).
  - `backend/app/api/v1/files.py` yaratildi va `backend/app/main.py` ga ulandi.
  - `backend/tests/test_s2_7_1_files_quarantine_ac_042.py` yaratildi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md` va `03_BOSQICHLAR_VA_HOLAT.md` yangilandi (`S2.7` `Tekshiruvda` holatiga o'tkazildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `python -m pytest D:\FlexBridge\backend -v` → **`28 passed in 1.48s`** (`S2.1..S2.6` 27 ta + `S2.7.1` 1 ta kompleks test: `test_ac_042_pending_scan_and_quarantined_pdf_never_receive_signed_url`).
- Muammo va cheklov: Yo'q; barcha 28 ta test xatosiz o'tdi.
- Topshirilgan holat / keyingi qadam: `S2.7.1` (`S2.7`) `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: `S2.8.1` — Tarif (`SINGLE_POST_30D`, `ORG_PLAN_30D` 5 parallel slot), to'lov idempotentligi (`DB-072`) va dual-control qaytarish (`INV-04`, `INV-05`, `INV-10`, `AC-042`).
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`
