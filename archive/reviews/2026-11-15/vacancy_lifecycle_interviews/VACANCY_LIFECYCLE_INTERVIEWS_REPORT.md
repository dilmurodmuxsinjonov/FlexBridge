# FlexBridge 1.4 Vacancy Lifecycle & Interview Responses Hub (FB-180) Forensic Report

**Sana**: 2026-11-15  
**Ishlab chiquvchi**: Antigravity Autonomous Agent  
**Tegishli Issue**: [#180](https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/180)  
**Tarmoq**: `feature/180-vacancy-lifecycle-interview-responses-hub`  
**Baza tarmoq**: `integration/r1-agent-collaboration`  
**Muvofiqlik statusi**: 100% GREEN (19/19 Staging Suites Passed)  

---

## 1. Vazifa va arxitektura qamrovi

Ushbu bosqichda FlexBridge platformasida ish beruvchining vakansiya e'lonlarini nashr qilish, ularning hayot siklini boshqarish (to'xtatish va yopish) hamda nomzodning belgilangan suhbatlarga javob berish (qabul qilish, rad etish, vaqtini ko'chirish) jarayonlari to'liq Next.js 16 (App Router) BFF va Enterprise Backend qatlamlari orqali amalga oshirildi.

### Qamrab olingan Kanonik Shartnomalar:
1. **`API-081`**: `POST /api/v1/opportunities/{id}/publish` (CAP-027 / EMPLOYER / DB-070 / DB-075).
   - Tashkilotning faol obunasi va post limitlarini tekshirish (`service_entitlements.concurrent_active_limit`, `quota`).
   - Moderatsiyadan o'tgan (`APPROVED` yoki `PAUSED`) qoralama e'lonni `PUBLISHED` holatiga o'tkazish.
   - `published_at` va `expires_at` vaqt tamg'alarini qayd qilish.
   - Tashkilot ruxsati (`require_capability` - `JOB_EMPLOYER` yoki `INTERNSHIP_HOST`) va xodim roli (`OWNER`, `HR`, `HOST_COORDINATOR`) kafolatlangan tekshiruvi.
2. **`API-082`**: `POST /api/v1/opportunities/{id}/transition` (CAP-027 / EMPLOYER / DB-070).
   - Faol yoki to'xtatilgan vakansiya holatini o'zgartirish: `PAUSED` yoki `CLOSED`.
   - Strict validation: payload faqat `status` qabul qiladi, qo'shimcha parametrlar `extra='forbid'` orqali taqiqlanadi (HTTP 422).
   - Invariant: faqat `PUBLISHED` yoki `PAUSED` holatidagi e'lonlar holati o'zgartirilishi mumkin.
   - Audit jurnali: `OPPORTUNITY_PAUSED` yoki `OPPORTUNITY_CLOSED` audit yozuvi avtomatik shakllantiriladi.
3. **`API-042`**: `POST /api/v1/interviews/{id}/responses` (CAP-009 / AC-012 / DB-040 / DB-041).
   - Nomzod belgilangan suhbatga javob beradi: `ACCEPTED`, `DECLINED`, `RESCHEDULE_REQUESTED`.
   - Suhbat holati avtomatik o'zgaradi:
     - `ACCEPTED` -> `CONFIRMED`
     - `DECLINED` -> `CANCELLED`
     - `RESCHEDULE_REQUESTED` -> `RESCHEDULE_REQUESTED`
   - Strict candidate authorization & IDOR himoyasi: nomzod faqat o'z arizasiga tegishli suhbatga javob berishi mumkin, begona foydalanuvchilar probingini bartaraf etish uchun qat'iy HTTP 404 qaytariladi.
   - Tashkilot xodimlari cheklovi: `COMPLETED` va `NO_SHOW` faqat HR tomonidan belgilanadi.
   - Audit logging: `INTERVIEW_RESPONSE_RECORDED` audit voqeasi qayd etiladi.

---

## 2. Amalga oshirilgan fayllar va o'zgarishlar

### A. Next.js BFF Endpoints:
- `frontend/src/app/api/bff/employer/opportunities/[id]/publish/route.ts`:
  - `POST` metodi orqali API-081 backend shartnomasiga xavfsiz proksi.
  - Cookie asosidagi sessiya va CSRF himoyasi.
- `frontend/src/app/api/bff/employer/opportunities/[id]/transition/route.ts`:
  - `POST` metodi orqali API-082 backend shartnomasiga xavfsiz proksi.
  - Payload sanitizatsiyasi (`status: 'PAUSED' | 'CLOSED'`).
- `frontend/src/app/api/bff/candidate/interviews/[id]/responses/route.ts`:
  - `POST` metodi orqali API-042 backend shartnomasiga xavfsiz proksi.
  - Payload sanitizatsiyasi (`response: 'ACCEPTED' | 'DECLINED' | 'RESCHEDULE_REQUESTED'`, ixtiyoriy `note`).

### B. TypeScript SDK & Models:
- `frontend/src/lib/api.ts`:
  - Modellar: `OpportunityPublishResponse`, `OpportunityTransitionPayload`, `OpportunityTransitionResponse`, `InterviewResponsePayload`, `InterviewResponseResult`.
  - SDK Funksiyalari:
    - `publishEmployerOpportunity(opportunityId: string)`
    - `transitionOpportunityStatus(opportunityId: string, status: 'PAUSED' | 'CLOSED')`
    - `respondToInterview(interviewId: string, response: string, note?: string)`

### C. Frontend UI Yangilanishlari:
- `frontend/src/app/employer/page.tsx`:
  - Ish beruvchi boshqaruv panelida har bir e'lon kartasida interaktiv holat amallari:
    - **Nashr qilish** (DRAFT yoki PAUSED holatida).
    - **To'xtatish** (PUBLISHED holatida).
    - **Yopish** (PUBLISHED yoki PAUSED holatida).
  - Real-vaqtli banner bildirishnomalari va statistika metrikalarining avtomatik qayta yangilanishi.
- `frontend/src/app/nomzod/arizalar/page.tsx`:
  - Nomzod arizalari bo'limida belgilangan suhbatlar uchun interaktiv javob berish bloki:
    - **Qabul qilish** (Taklifni tasdiqlash).
    - **Vaqtini ko'chirish** (Sababini ko'rsatuvchi interaktiv matn maydoni bilan).
    - **Rad etish** (Taklifni bekor qilish).
  - Muvaffaqiyatli javobdan so'ng kartaning yangi holati real vaqtda aks ettiriladi.

### D. Staging Verifikatsiya Testlari:
- `scripts/test_vacancy_lifecycle_interviews_staging.py`:
  - 10 bosqichli to'liq regressiya:
    - Phase 1: 401 Unauthenticated rejection on all 3 endpoints.
    - Phase 2: 403 CSRF_ORIGIN_MISMATCH rejection on mutating endpoints.
    - Phase 3: DB Fixtures setup via PgBouncer (Users, Candidates, Organization, Capabilities, Entitlements, Opportunities, Applications, Interviews).
    - Phase 4: HR, Candidate, Foreign Candidate authentication via BFF and MFA elevation.
    - Phase 5: API-081 Opportunity publish verification (DB verified status `PUBLISHED`).
    - Phase 6: API-082 Opportunity transition (PAUSED, CLOSED) verification (DB verified status `CLOSED`).
    - Phase 7: API-042 Candidate interview ACCEPTED verification (DB verified status `CONFIRMED`).
    - Phase 8: API-042 Candidate interview RESCHEDULE_REQUESTED verification (DB verified status `RESCHEDULE_REQUESTED`).
    - Phase 9: API-042 Candidate interview DECLINED verification (DB verified status `CANCELLED`).
    - Phase 10: Negative Authorization Checks (Foreign candidate IDOR rejected with HTTP 404; Unauthorized candidate publish attempt rejected with HTTP 403).

---

## 3. Verifikatsiya Natijalari

1. **Next.js Production Build**:
   - `npm run build` muvaffaqiyatli o'tdi (45 ta marshrut xatoliksiz kompilyatsiya qilindi).
2. **Dedicated Staging Test Suite**:
   - `scripts/test_vacancy_lifecycle_interviews_staging.py` 100% GREEN (barcha 10 ta faza muvaffaqiyatli).
3. **Comprehensive Regression**:
   - `scripts/run_all_staging_tests.py` orqali barcha 19 ta staging test to'plamlari 100% GREEN yakunlandi.
4. **Frozen Main & Isolation**:
   - `origin/main` o'zgarishsiz muzlatilgan holatda (`764fb98496fa40857acb07844fd09fcafa99b7d6`).
   - Barcha o'zgarishlar `integration/r1-agent-collaboration` bazasidan yaratilgan va unga yo'naltirilgan.
   - `pg_live` katalogiga bironta so'rov yuborilmadi; barcha DB operatsiyalari faqat PgBouncer (`127.0.0.1:5432/flexbridge`) orqali bajarildi.
