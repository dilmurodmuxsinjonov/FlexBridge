# FlexBridge 1.4 Forensic Report: University Academic Log Reviews & Evaluation Workflow Verification (FB-152 / API-105-107)

**Sana**: 2026-11-15  
**Topshiriq / Muammo**: Issue #152 — Universitet Portali (`/university`) — Talabalar Amaliyot Kundaliklarini Ko‘rib Chiqish va Tasdiqlash Tizimi  
**Tegishli shartnomalar (Contracts)**: API-105, API-106, API-107, CAP-018  
**Ijrochi**: Antigravity Autonomous Master Execution & Principal Systems Technologist  
**Tizim holati**: Barcha 8 bosqichli testlar muvaffaqiyatli o'tdi (100% Green).

---

## 1. Muammo va Talablar Tahlili

FlexBridge 1.4 platformasida oliy ta'lim muassasalari (OTM) kafedra o'qituvchilari va amaliyot rahbarlari (`/university`) talabalarning ishlab chiqarish yoki muhandislik amaliyoti davomida kiritgan kunlik hisobotlarini (kundaliklarini) ko'rib chiqishi, vazifalar taqsimotini baholashi, ish beruvchi (mentor) bergan xulosalarni tekshirishi va rasmiy akademik baholash qarorini (`REVIEWED` yoki `NEEDS_REVISION`) qabul qilishi uchun Next.js BFF va frontend interfeysi talab etildi:

1. **API-105**: `GET /api/v1/me/academic-review-queue` (va `/me/teacher-review-queue` kanonik laqabi) — O'qituvchiga biriktirilgan va ko'rib chiqilishi kutilayotgan talabalar amaliyot kundaliklari navbati (talaba F.I.Sh., sana, amaliyot maqsadi, kundalik ID).
2. **API-106**: `GET /api/v1/log-revisions/{revision}/academic` — Talaba kiritgan kundalik reviziyasining to'liq tafsiloti (vazifalar ro'yxati, daqiqalar taqsimoti, umumiy xulosa, ish beruvchi/mentor taqrizi va avvalgi akademik taqrizlar tarixi).
3. **API-107**: `POST /api/v1/log-revisions/{revision}/academic-reviews` — Akademik taqriz xulosasini topshirish (`academic_assignment_id`, `decision: "REVIEWED" | "NEEDS_REVISION"`, `comment`, `idempotency_key`).

---

## 2. Amalga Oshirilgan O'zgarishlar

### A. Next.js 16 BFF API Marshrutlari
1. `frontend/src/app/api/bff/university/log-revisions/[revision]/academic/route.ts`:
   - Sessiya mavjudligi va avtorizatsiya tekshiruvi (HTTP 401 `AUTH_REQUIRED`).
   - Backend API-106 (`/api/v1/log-revisions/{revision}/academic`) shartnomasiga xavfsiz proksi.
2. `frontend/src/app/api/bff/university/log-revisions/[revision]/academic-reviews/route.ts`:
   - CSRF tekshiruvi (`verifyCsrfOrigin` orqali cross-site hujumlarni 403 bilan rad etish).
   - Sessiya va foydalanuvchi tekshiruvi.
   - `academic_assignment_id` avtomatik aniqlash (agar frontenddan uzatilmagan bo'lsa, o'qituvchining biriktirilgan akademik topshirig'ini backenddan topib ulaydi).
   - Backend API-107 (`/api/v1/log-revisions/{revision}/academic-reviews`) ga `Idempotency-Key` bilan yuborish.

### B. TypeScript Tiplari va Mijoz Yordamchilari (`frontend/src/lib/api.ts`)
- Qat'iy interfeyslar:
  - `AcademicLogTaskEntry`: Vazifa tavsifi, sarflangan vaqt (daqiqa), reja vazifasi kodi va nomi.
  - `AcademicLogRevisionDetail`: Kundalik reviziyasi tafsiloti, ish beruvchi sharhlari (`workplace_reviews`) va o'qituvchi sharhlari (`academic_reviews`).
  - `SubmitAcademicReviewPayload`: Qaror (`REVIEWED` | `NEEDS_REVISION`), sharh, idempotency key.
  - `AcademicReviewResult`: Qaytgan kvitansiya (receipt) ma'lumotlari.
- Asinxron funksiyalar:
  - `fetchAcademicLogRevision(revisionId: string)`
  - `submitAcademicLogReview(revisionId: string, payload: SubmitAcademicReviewPayload)`

### C. Universitet Portali UI va Yangi Baholash Modali
1. `frontend/src/components/AcademicReviewModal.tsx`:
   - Anti-slop qoidalariga to'liq mos keluvchi `#09090b` / `#121214` to'q rangli interfeys.
   - Amaliyot statistikasi (sana, umumiy vaqt, kun turi, maqsad).
   - Talabaning kunlik xulosasi va bajargan vazifalari (`log_task_entries`) bloklari.
   - Ish beruvchi / mentor taqrizlari tarixi (mentor bahosi va izohi).
   - O'qituvchi qarori selektori (`REVIEWED` - Yashil zumrad / `NEEDS_REVISION` - Sariq ogohlantirish).
   - O'qituvchi sharhi (`textarea`), yuklanish va xatolik holatlari.
2. `frontend/src/app/university/page.tsx`:
   - Amaliyot kundaliklari jadvalida har bir element uchun "Ko‘rib chiqish" tugmasi qo'shildi.
   - `AcademicReviewModal` bilan integratsiya qilindi va muvaffaqiyatli tasdiqlashdan so'ng ro'yxatni avtomatik yangilash mexanizmi ulandi.

---

## 3. Staging Muhitida Tekshiruv Natijalari

Yaratilgan `scripts/test_university_academic_reviews_staging.py` avtomatlashtirilgan test to'plami PgBouncer orqali (`127.0.0.1:5432/flexbridge`) jonli Docker konteynerlarida sinovdan o'tkazildi:

| Bosqich | Nomi | Kutilgan natija | Haqiqiy natija | Holat |
|---|---|---|---|---|
| **Phase 1** | Barcha Universitet BFF yo'llarida avtorizatsiya talabi | HTTP 401 AUTH_REQUIRED | HTTP 401 AUTH_REQUIRED | **PASS** |
| **Phase 2** | PgBouncer orqali test ma'lumotlarini kiritish | O'qituvchi, Talaba, Amaliyot, Kundalik reviziyasi | Muvaffaqiyatli kiritildi | **PASS** |
| **Phase 3** | O'qituvchi login va HttpOnly sessiya o'rnatish | HTTP 200, TEACHER roli | HTTP 200, ['CANDIDATE', 'TEACHER'] | **PASS** |
| **Phase 4** | Amaliyot kundaliklari navbatini olish (API-105) | HTTP 200, 1 ta reviziya | HTTP 200, 1 ta SUBMITTED reviziya | **PASS** |
| **Phase 5** | Kundalik reviziyasi tafsilotini tekshirish (API-106) | HTTP 200, 420 daqiqa, 2 ta vazifa | HTTP 200, 420 daqiqa to'liq mos | **PASS** |
| **Phase 6** | Akademik baholash qarorini topshirish (API-107) | HTTP 200/201, REVIEWED kvitansiyasi | HTTP 201, receipt qaytdi | **PASS** |
| **Phase 7** | Cross-site CSRF hujumini bloklash | HTTP 403 CSRF_ORIGIN_MISMATCH | HTTP 403 CSRF_ORIGIN_MISMATCH | **PASS** |
| **Phase 8** | Idempotency va takroriy baholashdan himoya | Bir xil kvitansiya va 409 xatolik | Idempotent receipt va 409 himoyasi | **PASS** |

### Regressiya Testlari (0 Regressiya):
- `python scripts/test_employer_kanban_staging.py`: 12/12 Bosqich [PASS]
- `python scripts/test_candidate_applications_staging.py`: 12/12 Bosqich [PASS]
- `python scripts/test_opportunity_application_staging.py`: 6/6 Bosqich [PASS]
- `python scripts/test_bff_staging.py`: 8/8 Bosqich [PASS]
- `python scripts/test_staging_e2e.py`: 5/5 Bosqich [PASS]

---

## 4. Xavfsizlik va Invariantlar Audit
1. **Frozen Main Invariant**: `origin/main` commit `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan. Main filialiga to'g'ridan-to'g'ri hech qanday yozish yoki merge qilinmadi. Barcha ishlar `integration/r1-agent-collaboration` ga yo'naltirilgan PR orqali amalga oshiriladi.
2. **pg_live Invariant**: `backend/.data/pg_live` katalogiga mutlaqo tegilmadi. Barcha amallar PgBouncer orqali jonli Docker staging bazasida bajarildi.
3. **Zero Type Errors**: `npx tsc --noEmit` 0 xato bilan yakunlandi.
4. **Clean Turbopack Build**: `npm run build` barcha 31 ta marshrutni muvaffaqiyatli statik va dinamik kompilyatsiya qildi.
