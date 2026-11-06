# FlexBridge — S1.1: Mavjud talablar va manbalar xaritasi

**Vazifa ID**: `S1.1`  
**Sana**: `2026-11-06` (`Asia/Tashkent`)  
**Mas'ul AI**: `Antigravity` (Sessiya: `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`, Model: `Gemini 4 Argon (High)`)  
**Holat**: `Tekshiruvda` (Codex tekshiruvi kutilmoqda)

---

## 1. O'rganilgan manbalar reestri (`D:\FlexBridge`)

Quyidagi jadvalda `D:\FlexBridge` katalogidagi barcha mavjud manbalar, ularning hajmi, o'qilish usuli va qamrovi keltirilgan:

| Manba fayli | Sana / Versiya | Hajmi / Ko'lami | Tekshiruv usuli va holati | Asosiy mazmuni |
| --- | --- | --- | --- | --- |
| `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` | 2026-11-05 (v1.4) | 9 sahifa, 361 574 bayt | `pypdf` orqali 9 sahifa to'liq o'qildi | 1.3→1.4 farqlar (94 jadval, 935 maydon, 214 FK), 12 ta DB/API/arxitektura tuzatishi, DB-083 retention jadvali va AC-039..042 |
| `FlexBridge_Ustoz_uchun_loyiha_izohi.md` (va `.pdf`) | 2026-10-30 (v1.3) | 183 qator / 7 sahifa | To'liq matn o'qildi | Mahsulot maqsadi, 8 foydalanuvchi guruhi, maoshli ish va akademik amaliyot oqimlari, kundalik qoidalari, tariflar, 63 mln so'm 6 oylik pilot budjeti, R2–R5 rejasi |
| `FlexBridge_kelgusi_bosqichlar.md` | 2026-10-30 (v1.3) | 59 qator | To'liq matn o'qildi | R1–R5 (1–24-oylar) bosqichlari, daromad modeli (frilans 10% xizmat haqi) va keyingi bosqichga o'tish shartlari |
| `FlexBridge_Investorlar_uchun.pptx` (va `.pdf`) | 2026-10-30 (v1.3) | 27 slayd va slayd izohlari | `.pptx` ichidagi `ppt/slides/slide1..27.xml` va `ppt/notesSlides/notesSlide1..27.xml` XML darajasida to'liq o'qildi (`.pdf` nusxasi rasm-slaydlardan iborat) | Bozor hajmi (1,535 mln OTM talabasi, Milliy statistika qo'mitasi 26.05.2026), `hh.uz` bilan taqqoslash, unit-ekonomika, 6 oylik 3 ssenariy (Ehtiyotkor: 10, Asosiy: 39, Tez o'sish: 71 pullik plan), operatsion qoplanish nuqtasi (17 ta korxona tarifi = 9,2 mln UZS/oy; asoschi maoshi bilan 32 ta tarif), xatarlar matritsasi |
| `Oqish_tartibi.txt` | 2026-10-30 | 16 qator | To'liq matn o'qildi | Hujjatlar to'plamining vazifasi va moliyaviy/tijoriy farazlar chegarasi |

---

## 2. Foydalanuvchi rollari xaritasi (14 ta rol)

`FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (2- va 6-sahifalar: `14 rol / 40 CAP / 48 sahifa (131 bo'lim)`) hamda `FlexBridge_Ustoz_uchun_loyiha_izohi.md` (29–48-qatorlar) bo'yicha rollarning biznes va texnik bog'lanishi:

| # | Texnik rol kodi (1.4 PDF, 6-bet) | Biznes nomi (`Ustoz_uchun_loyiha_izohi.md`) | Asosiy vazifasi va huquq doirasi (Scope) | 1.4 PDFda aniq ko'rsatilgan ruxsat/cheklov qoidalari |
| --- | --- | --- | --- | --- |
| 1 | `GUEST` | Ro'yxatdan o'tmagan mehmon | Ochiq ma'lumotlarni ko'rish va ro'yxatdan o'tish | `API-060` va `API-061` dan `GUEST` chiqarib tashlangan (`401 Unauthorized` — `AC-041`) |
| 2 | `CANDIDATE` | Nomzod (18+ talaba yoki mutaxassis) | Profil, malaka va bo'sh vaqtini kiritish; maoshli ish va umumiy amaliyotga bepul ariza berish; ish boshlanishi / amaliyot qarorlari (`API-049`) va shaxsiy eksport (`API-052`) | Ish qidirish va ariza berish bepul; maoshdan ulush olinmaydi. `API-088` (`/host-decisions`) va `API-100` (`/institutions/{inst}/exports`) chaqirilsa `403 Forbidden` (`AC-041`) |
| 3 | `STUDENT` | Talaba | `CANDIDATE` imkoniyatlari + o'quv muassasasiga tegishliligini tasdiqlab uch tomonlama akademik amaliyotda qatnashish va kundalik yuritish | `API-088` va `API-100` uchun ruxsat yo'q (`403 Forbidden`) |
| 4 | `OWNER` | Korxona / Host tashkilot egasi | Tashkilotni boshqarish, vakolat berish, e'lon va amaliyot host qarorlarini (`API-088`) qabul qilish | `CAP-025` (qat'iy `ORG` doirasi) bo'yicha `API-088` ruxsatiga ega |
| 5 | `HR` | Oddiy ish beruvchi HR mas'uli | Maoshli ish e'lonini berish, arizalarni saralash, suhbat va taklifni tashkil qilish | `INV-02` (`fk_opp_hr_membership_same_org`): HR faqat o'z tashkiloti (`organization_id`) e'loniga biriktiriladi |
| 6 | `HOST_COORDINATOR` | Amaliyot hosti mas'uli | Amaliyot joyi, sharoiti va rejasini kelishish, korxonadan mentor tayinlash, host qarorlarini (`ACTIVATE`, `APPROVE_COMPLETION`, `DISPUTE`, `CANCEL`) berish | `CAP-025` (`API-088`, qat'iy `ORG` doirasi) |
| 7 | `MENTOR` | Korxona ustozi (mentor) | Amaliy ishga yo'l-yo'riq berish, kundalikdagi ish natijasini tekshirish (tasdiqlash yoki tuzatishga qaytarish) | `INV-02` (`fk_mentor_placement_same_org`); `API-088` va `API-100` dan chiqarilgan; bitta amaliyot hisobotini `API-052` orqali oladi |
| 8 | `BILLING` | Korxona to'lov mas'uli | Tarif va e'lon kvotalarini sotib olish, hisob-faktura va to'lovlarni yuritish | Autentifikatsiyadan o'tgan hisob xavfsizligi (`API-060`, `API-061`) |
| 9 | `COORDINATOR` | Muassasaning rasmiy mas'uli | OTM/muassasa nomidan ulanish, talabalar va o'qituvchilarni biriktirish, muassasa kesimida yig'ma hisobot eksporti | `INV-03` (`fk_supervision_coordinator_same_inst`); `CAP-026` (`API-100 POST /api/v1/institutions/{inst}/exports`, qat'iy `INSTITUTION` doirasi, step-up re-auth va audit bilan); `API-088` dan chiqarilgan |
| 10 | `TEACHER` | O'qituvchi (o'quv rahbari) | Talabaga biriktirilgan o'quv rahbari; o'quv maqsadi va yakuniy hisobotga alohida akademik xulosa berish (`API-108`) | `INV-03` (`fk_academic_teacher_same_inst`); `API-088` chaqirilsa `403 Forbidden` (`AC-041`); bitta amaliyot hisobotini `API-052` orqali oladi |
| 11 | `MODERATOR` | Platforma moderatori | Tashkilot, STIR, vakolat va e'lonlarni tekshirish, shikoyat va nizolarni ko'rib chiqish | Dual-Control: o'zi ochgan `verification_cases` so'rovini o'zi tasdiqlay olmaydi (`chk_verification_not_self_review` — `AC-041`) |
| 12 | `SUPPORT` | Qo'llab-quvvatlash mas'uli | Foydalanuvchi murojaatlari va hisobni tiklash (`recovery_requests`) jarayonlari | Dual-Control: `recovery_requests` da o'z-o'zini tasdiqlash bloklangan |
| 13 | `FINANCE` | Platforma moliya mas'uli | To'lovlar, billing ledger va qaytarishlarni (`refunds`) tekshirish hamda tasdiqlash | Dual-Control (`DB-076 refunds`): `requester_id`, `approver_id` va `second_approver_id` uch xil shaxs bo'lishi shart (`chk_refunds_independent_approvers`) |
| 14 | `ADMIN` | Platforma administratori | Tizim sozlamalari, platforma rollarini berish (`platform_role_grants`), favqulodda operatsiyalar | Dual-Control: `chk_platform_grant_not_self`; Productionda kamida 2 ta mustaqil operator passkey/TOTP bilan ishlashi shart (`1.4 PDF`, 7-bet) |

---

## 3. Biznes va texnik oqimlar xaritasi (R1 — Ish va Amaliyot)

### 3.1. Hisob, Sessiya, Tashkilot va Vakolatlar (`S2.2` doirasi)
* **Biznes talablar** (`Ustoz_uchun_loyiha_izohi.md`, 44–48-qatorlar):
  * Nomzod email yoki telefonini tasdiqlab profil ochadi; talaba bo'lmagan nomzod ham umumiy ishga ariza bera oladi.
  * Kontaktni tasdiqlashning o'zi tashkilot vakili bo'lish huquqini bermaydi; korxona va muassasa vakillari o'z tashkiloti va vakolatini alohida tasdiqlaydi.
  * Xodim, mentor va o'qituvchi tayinlov taklifini shaxsan qabul qiladi.
* **Texnik talablar** (`1.4 PDF`, 5–8-betlar):
  * **Jadvallar**: `users`, `sessions`, `organizations`, `org_memberships`, `org_role_grants`, `org_invitations`, `platform_role_grants`, `verification_cases`, `recovery_requests`.
  * **APIlar**:
    * `API-060 PATCH /api/v1/me/security` — `CAP-002`, faqat autentifikatsiyadan o'tgan 13 rol (`GUEST`siz) va step-up (parol/MFA) tasdig'i bilan.
    * `API-061 DELETE /api/v1/me/sessions/{id}` — `CAP-002`, faqat foydalanuvchining o'z sessiyalarini (`user_id = current_user.id`) bekor qiladi.
    * `API-075`, `API-103`, `API-120` — xodim, o'qituvchi yoki vakolatni bekor qilish endpointlari.
  * **Arxitektura va Invariantlar**:
    * `INV-02`: `fk_org_invitations_inviter_same_org` — taklif yuboruvchi aynan shu `organization_id` a'zosi bo'lishi shart.
    * `INV-03`: `fk_supervision_coordinator_same_inst`, `fk_academic_teacher_same_inst` — koordinator va o'qituvchi kelishuvdagi `institution_id` ga tegishli bo'lishi shart.
    * `INV-15` (Darhol Revoke): PgBouncer + qisqa muddatli (TTL = 15s) in-memory/Redis ruxsat keshi; sessiya yoki rol bekor qilinganda (`API-061`, `API-075`, `API-103`, `API-120`) kesh tranzaksiya commitidan so'ng darhol tozalanadi (Read p95 < 800ms).
    * **Dual-Control**: `chk_verification_not_self_review`, `chk_platform_grant_not_self`.

### 3.2. Nomzod profili va Bo'sh vaqt jadvali (`S2.3` doirasi)
* **Biznes talablar** (`Ustoz_uchun_loyiha_izohi.md`, 12–17, 54-qatorlar):
  * Nomzod haftalik bo'sh vaqt oynalarini va aniq sanalardagi istisnolarni (bandlik yoki qo'shimcha bo'sh vaqt) kiritadi.
* **Texnik talablar** (`1.4 PDF`, 1–3-betlar):
  * **Jadvallar**:
    * `candidate_profiles` (`user_id`, `headline`, `region`, `experience_months`, `visibility`).
    * `DB-016 availability_rules` — `minute_range int4range GENERATED ALWAYS AS (int4range(start_minute, end_minute, '[)')) STORED` hamda `USING gist (candidate_id, weekday, minute_range)` indeksi (28 kunlik oynada tezkor range union va overlap qidiruvi uchun).
    * `DB-017 availability_exceptions` — `minute_range int4range GENERATED ALWAYS AS (int4range(start_minute, end_minute, '[)')) STORED` (aniq sanadagi `AVAILABLE`/`REPLACE` va `UNAVAILABLE`/`BLOCK` intervallarini `int4range` ayirish amali bilan moslashtirish).

### 3.3. E'lonlar, Shartnoma turlari, Smena guruhlari va Moslik (`S2.4` doirasi)
* **Biznes talablar** (`Ustoz_uchun_loyiha_izohi.md`, 19–25, 31, 53–55-qatorlar):
  * Korxona ish vaqti (smenalar), maosh, joylashuv/ish rejimi, shartnoma turi va vazifalarni aniq ko'rsatadi.
  * Amaliyotda haq to'lanishi yoki to'lanmasligi oldindan ochiq yoziladi.
* **Texnik talablar** (`1.4 PDF`, 1–5 va 9-betlar):
  * **Jadvallar va Invariantlar**:
    * `opportunities` — `current_revision_id` halqali composite FK (`DEFERRABLE INITIALLY DEFERRED` — `INV-14`).
    * `DB-036 opportunity_revisions`:
      * `contract_type text NOT NULL CHECK (contract_type IN ('LABOR_PART_TIME', 'CIVIL_GPC', 'INTERNSHIP_AGREEMENT', 'ACADEMIC_TRIPARTITE'))`.
      * `INV-07` (`chk_opp_rev_salary`): `is_paid = false` bo'lganda `salary_min`, `salary_max`, `salary_period`, `salary_basis` qat'iy `NULL`; `is_paid = true` bo'lganda `salary_min > 0`, `salary_period IS NOT NULL`, `salary_basis IS NOT NULL`.
      * `chk_opp_rev_program`: `eligibility = 'ENROLLMENT_PROGRAM'` bo'lganda `program_required IS NOT NULL`.
    * `DB-038 opportunity_shifts`:
      * `group_code text NOT NULL DEFAULT 'GROUP_A'` va `minute_range int4range STORED`.
      * `shift_match_mode = 'ALL'` bo'lsa barcha `group_code` smenalari, `'ANY'` bo'lsa kamida bitta `group_code` ichidagi barcha smenalar nomzod bo'sh vaqtiga (**30 daqiqa oflayn bufer** bilan) sig'ishi tekshiriladi.
    * `opportunity_hr_assignments` (`fk_opp_hr_membership_same_org` — `INV-02`).
  * **API va AC**:
    * `API-003 /matching/preview` (`CAP-005`, `CAP-016`).
    * `AC-039`: `contract_type` ko'rsatilmagan e'lon nashri `422` bilan rad etiladi; `ANY` rejimida `GROUP_A` va `GROUP_B` berilganda nomzod vaqti faqat `GROUP_B` ga mos kelsa `API-003` `MATCH` qaytaradi.

### 3.4. Ariza, Suhbat, Taklif va Ish boshlanishi (`S2.5` doirasi)
* **Biznes talablar** (`Ustoz_uchun_loyiha_izohi.md`, 53–60-qatorlar):
  * Nomzod mos e'longa ariza beradi → Korxona suhbatga chaqiradi → Taklif va shartlar kelishiladi → Nomzod va korxona ish boshlanishini ikki tomonlama tasdiqlaydi.
  * Oddiy yarim stavkali ish uchun amaliyot kundaligi majburiy emas; maoshni ish beruvchi bevosita nomzodga to'laydi.
* **Texnik talablar** (`1.4 PDF`, 4, 5, 8-betlar):
  * **Jadvallar va Invariantlar**:
    * `applications` — `current_attempt_id` halqali composite FK (`DEFERRABLE INITIALLY DEFERRED` — `INV-14`).
    * `application_attempts` — `INV-01` (`fk_app_attempts_app_same_opp`, `fk_app_attempts_rev_same_opp`): ariza urinishi va e'lon versiyasi aynan bitta `opportunity_id` ga tegishli bo'lishini DB darajasida tekshiradi; `profile_snapshot`, `schedule_result`, `idempotency_key`.

### 3.5. Akademik va Umumiy Amaliyot, Kundalik va Baholash (`S2.6` doirasi)
* **Biznes talablar** (`Ustoz_uchun_loyiha_izohi.md`, 62–78-qatorlar):
  * Host korxona amaliyot joyi va rejasini taklif qiladi; akademik yo'lda talaba OTM orqali biriktiriladi; mentor va o'qituvchi tayinlovni qabul qiladi.
  * Kundalikda sana, bajarilgan vazifa, sarflangan vaqt va natija yoziladi.
  * Mentor ish bajarilganini tasdiqlaydi yoki tuzatishga qaytaradi; o'qituvchi o'rganilgan bilim va hisobotga alohida akademik xulosa beradi.
  * Shaxs o'z kundaligini boshqa rol orqali tasdiqlamaydi; platforma xulosasi o'z-o'zidan muassasaning rasmiy bahosiga aylanmaydi (alohida kelishuv talab etiladi).
* **Texnik talablar** (`1.4 PDF`, 1, 3, 5, 6, 9-betlar):
  * **Jadvallar va Invariantlar**:
    * `placements`, `supervision_agreements` (`INV-02`, `INV-03`).
    * `DB-056 log_revisions` — `trg_validate_log_submission` triggeri (`INV-09`): `SUBMITTED` holatiga o'tishda `total_minutes = SUM(log_task_entries.minutes)` avtomatik hisoblanadi; sana `[start_date, end_date]` ichida va `<= CURRENT_DATE`; `day_type = 'WORKED'` bo'lganda `total_minutes > 0` va `total_minutes <= daily_limit_minutes` bo'lishi shart.
    * `DB-057 log_task_entries` — `CHECK (minutes >= 0)` (`DRAFT`da 0 daqiqali reja bandi mumkin); `minute_range int4range STORED` va `EXCLUDE USING gist (revision_id WITH =, minute_range WITH &&) WHERE (minute_range IS NOT NULL)` (`AC-017`, `AC-040`).
    * `rating_scores` — `INV-11` (`fk_rating_scores_rev_same_rubric`, `fk_rating_scores_crit_same_rubric`): baholash mezoni aynan bitta rubrika versiyasiga tegishli bo'lishi shart.
  * **APIlar va AC**:
    * `PUT /api/v1/placements/{id}/logs/{date}` va `POST .../submit` (`CAP-022`, `AC-040`).
    * `API-049` (nomzod qarori), `API-088 POST /api/v1/placements/{id}/host-decisions` (`CAP-025`, faqat `OWNER` va `HOST_COORDINATOR`), `API-108` (o'qituvchi qarori).
    * `API-052 POST /api/v1/placements/{id}/exports` (bitta amaliyot hisoboti — nomzod, mentor, o'qituvchi uchun).
    * `API-100 POST /api/v1/institutions/{inst}/exports` (`CAP-026`, faqat shu muassasaning faol `COORDINATOR`i uchun).

### 3.6. Xususiy fayllar, Karantin, Antivirus va Eksport (`S2.7` doirasi)
* **Texnik talablar** (`1.4 PDF`, 1, 7, 8, 9-betlar):
  * **Jadval**: `DB-018 files` (`scan_status`: boshlang'ich `PENDING_SCAN`, zararli bo'lsa `QUARANTINED`).
  * **APIlar**: `API-X01`, `API-X02` (S3-mos xususiy omborga `quarantine/` prefiksi bilan yuklash), `API-X03 /download` (`CAP-029`, signed URL TTL = 60s; server-side access guard qayta tekshiriladi).
  * **Asinxron skaner worker**:
    * Magic-bytes (MIME) tekshiruvi.
    * Hajm limiti: CV va hujjatlar uchun `10 MB`, kundalik dalili uchun `15 MB`.
    * Antivirus: `ClamAV` (`clamd` daemon, ~1.2 GB RAM imzolar bazasi; server kamida 4 vCPU / 8 GB RAM yoki alohida skaner konteyneri).
    * PDF strukturaviy filtri: Python `pypdf` orqali PDF ichida JavaScript / Launch action yo'qligini tekshirish.
  * **AC**: `AC-042` (`PENDING_SCAN` yoki `QUARANTINED` fayl uchun `API-X03` chaqirilsa `409/403` qaytadi va signed URL berilmaydi).

### 3.7. Tarif, Kvota, To'lov va Qaytarish (`S2.8` doirasi)
* **Biznes talablar** (`Ustoz_uchun_loyiha_izohi.md`, 80–97-qatorlar; `Investorlar_uchun.pptx`, 7, 21, 22-slaydlar):
  * Bitta e'lon (`SINGLE_POST`): 149 000 so'm / 30 kun (kvota = 1).
  * Korxona tarifi (`ORG_PLAN_30D`): 599 000 so'm / 30 kun (bir vaqtda 5 tagacha faol `PUBLISHED` e'lon).
* **Texnik talablar** (`1.4 PDF`, 1, 4, 7, 8, 9-betlar):
  * `DB-075 service_entitlements`: `quota` (jami nashrlar limiti) va `concurrent_active_limit integer NOT NULL DEFAULT 5 CHECK (concurrent_active_limit > 0)` (bir vaqtda `PUBLISHED` turishi mumkin bo'lgan aktiv e'lonlar soni).
  * `DB-076 refunds`: `second_approver_id uuid NULL REFERENCES users(id)` va `chk_refunds_independent_approvers` (`requester_id`, `approver_id`, `second_approver_id` bir-biridan farqli bo'lishi shart); `trg_validate_refund_limit` triggeri (`INV-12`: jami qaytarilgan summa `CAPTURED` summadan oshmasligini row lock bilan kafolatlaydi).
  * `orders`, `invoices`, `billing_ledger`.
  * **AC**: `AC-042` (`ORG_PLAN_30D` da 5 ta aktiv `PUBLISHED` e'lon turganda 6-e'lonni publish qilish `409 concurrent_quota_reached` qaytaradi; 1 ta e'lon `CLOSED`/`PAUSED` bo'lgach yangisi publish bo'ladi).

### 3.8. Moderatsiya, Audit, Saqlash Siyosati va Operatsion SLA (`S2.9` va `S2.10` doirasi)
* **Saqlash muddatlari** (`DB-083 retention_policies` — `1.4 PDF`, 8-bet, Policy v1):
  1. `OTP_CHALLENGE_DIGEST`: 1 kun aktiv / 7 kun backup (OTP kod 5 daqiqa amal qiladi, xeshi 24 soatda o'chiriladi).
  2. `SECURITY_LOGIN_METADATA`: 90 kun aktiv / 30 kun backup (90 kundan keyin IP va device digest tozalanadi).
  3. `PRIVATE_EXPORT_FILE`: 1 kun aktiv / 7 kun backup (PDF/ZIP eksport 24 soatda S3 va `DB-018` dan o'chiriladi).
  4. `UNPUBLISHED_DRAFT`: 30 kun aktiv / 14 kun backup (23-kuni ogohlantiriladi, 30-kuni tozalanadi).
  5. `VERIFICATION_EVIDENCE`: qarordan so'ng 90 kun aktiv / 30 kun backup (xom dalil fayli o'chiriladi, qaror va audit qoladi).
  6. `APPLICATION_AND_SNAPSHOT`: 365 kun (1 yil) aktiv / 30 kun backup (so'ngra PII anonimlashtiriladi).
  7. `INTERNSHIP_DIARY_ACADEMIC`: 1095 kun (3 yil) aktiv / 30 kun backup.
  8. `BILLING_AND_FISCAL_LEDGER`: 1825 kun (5 yil) aktiv / 90 kun backup (`orders`, `invoices`, `refunds`, `billing_ledger`).
* **Operatsion SLA va P1 Circuit-Breaker** (`1.4 PDF`, 7-bet):
  * Ish vaqti: Dushanba–Juma 09:00–18:00 (`Asia/Tashkent`).
  * Ish vaqtidan tashqari P1 hodisalarda (to'lov callback xatosi, ketma-ket 5xx yoki ommaviy auth lock) Circuit-Breaker avtomatik ravishda `paid_checkout` flagini vaqtincha o'chiradi va navbatchi operatorga Telegram/SMS alert yuboradi.

---

## 4. Qabul mezonlari (AC-001..AC-042) va Invariantlar (INV-01..INV-15) holati

### 4.1. `D:\FlexBridge` ichidagi `1.4 PDF`da to'liq bayon qilingan AClar
* **AC-017** (3-betda havola): Bitta kundalik versiyasi ichida vaqt oralig'i berilgan ikki vazifa GiST `EXCLUDE` orqali hech qachon kesishmaydi.
* **AC-039 (`DB-06`)**: `contract_type` majburiyligi (`422`) va `ANY` rejimida smena guruhlari (`GROUP_A`, `GROUP_B`) bo'yicha `API-003 (/matching/preview)` `MATCH` javobi.
* **AC-040 (`DB-07`)**: Kundalikda `minutes = 0` qoralama (`200 OK`), `WORKED` kunda `total_minutes = 0` bilan submit (`422`), vaqt kesishmasligi (`GiST EXCLUDE`).
* **AC-041 (`SEC-03`)**: `GUEST` uchun `API-060`/`API-061` (`401`), `CANDIDATE`/`TEACHER` uchun `API-088` (`403`), `CANDIDATE` uchun `API-100` (`403`) va DB darajasida self-approval bloklanishi.
* **AC-042 (`OPS-10`)**: `PENDING_SCAN`/`QUARANTINED` fayl uchun `API-X03` (`409`/`403`) va `ORG_PLAN_30D` da 6-parallel e'lon uchun `409 concurrent_quota_reached`.

### 4.2. `1.4 PDF`da nomlari va qoidasi berilgan DB Invariantlari
* **INV-01**: `fk_app_attempts_app_same_opp`, `fk_app_attempts_rev_same_opp` (ariza urinishi va e'lon versiyasi bitta `opportunity_id` ga tegishli).
* **INV-02**: `fk_org_invitations_inviter_same_org`, `fk_opp_hr_membership_same_org`, `fk_mentor_placement_same_org` (bitta `organization_id` doirasi).
* **INV-03**: `fk_supervision_coordinator_same_inst`, `fk_academic_teacher_same_inst` (bitta `institution_id` doirasi).
* **INV-07**: `chk_opp_rev_salary` (`is_paid` va maosh ustunlari mosligi).
* **INV-09**: `trg_validate_log_submission` (kundalik topshirishda vaqt va sana qoidalari).
* **INV-10**: Cross-table scope composite FK (5-betda eslatilgan).
* **INV-11**: `fk_rating_scores_rev_same_rubric`, `fk_rating_scores_crit_same_rubric` (bitta rubrika versiyasi doirasi).
* **INV-12**: `trg_validate_refund_limit` (qaytarilgan summa `CAPTURED` summadan oshmasligi).
* **INV-14**: Barcha 6 ta halqali composite FKga `DEFERRABLE INITIALLY DEFERRED` xossasi berilishi.
* **INV-15**: Sessiya va rol bekor qilinganda L1/Redis keshni darhol tozalash va server-side access guard.

---

## 5. Aniqlangan bo'shliqlar va topilgan lokal artefaktlar auditi (`S1.2` uchun asos)

`S1.1` tekshiruvi davomida `D:\FlexBridge` ichida yetishmayotgan, ammo `1.4 PDF`da havola qilingan artefaktlar bo'yicha lokal disk (`D:\`) tekshirildi va quyidagi aniq holat aniqlandi:

| Artefakt | `D:\FlexBridge` ichidagi holati | Lokal diskdagi haqiqiy manzili va holati | Tekshiruv dalili |
| --- | --- | --- | --- |
| **1.3 to'liq texnik paket** (`schema_loyihasi.sql`, `FlexBridge_model_1_3.json`, `FlexBridge_ishga_tayyorgarlik_va_texnik_topshiriq.pdf`, `FlexBridge_baza_va_API_atlas.pdf`, `api_kontraktlari.csv`, `baza_maydonlari.csv`, `kamchiliklar_va_qabul_mezonlari.csv` — `AC-001..038`, `rol_imkoniyat_matritsasi.csv`, `sahifalar_va_bolimlar.csv` va b.) | Hozircha `D:\FlexBridge` ichiga ko'chirilmagan | `D:\Codex\2026-10-26\sh\outputs\FlexBridge\` katalogida va `FlexBridge_toliq_texnik_paket_1_3.zip` arxivida **to'liq mavjud** | `checksums.json` bo'yicha 41/41 fayl SHA-256 nazorat summasi 100% mos (`40/41` ochiq katalogda + `1/41` `FlexBridge_interaktiv_atlas.html` zip ichida). `FlexBridge_model_1_3.json` stats: `94 jadval, 923 maydon, 205 FK, 14 rol, 40 CAP, 48 sahifa, 131 bo'lim, 124 API, 38 AC` |
| **1.4 yangilangan SQL sxema** (`FlexBridge_1_4_schema.sql` — 94 jadval, 935 maydon, 214 FK) | `D:\FlexBridge` ichida yo'q | Lokal diskda alohida `.sql` fayl sifatida yo'q; ammo `1.3 schema_loyihasi.sql` + `D:\Codex\2026-10-26\sh\work\review_2026_11_05\check_schema.mjs` + `1.4 PDF` (1–5 va 8-betlar) barcha 12 ta ustun va 9 ta FK o'zgarishini aniq belgilaydi | `S1.2` bosqichida `1.3` artefaktlarini `D:\FlexBridge`ga ko'chirish va `1.4 PDF` asosida `FlexBridge_1_4_schema.sql`ni yaratib, lokal PostgreSQL 17.11 / PGlite da sinash taklif etildi (`04_TAKLIFLAR_VA_TANLOVLAR.md` — `T-007`) |
| **Ochiq texnik stek tanlovlari** (Frontend, Backend, Worker/navbat, S3 provayder, Auth/TOTP, To'lov, Deploy) | `02_TEXNIK_MODELLAR.md`da "Belgilanmagan" | Manbalarda qat'iy tanlanmagan | `S1.3` bosqichi uchun `04_TAKLIFLAR_VA_TANLOVLAR.md`da `T-008` taklifi shakllantirildi |
