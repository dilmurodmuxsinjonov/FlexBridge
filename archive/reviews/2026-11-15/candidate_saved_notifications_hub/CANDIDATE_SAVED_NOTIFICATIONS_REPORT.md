# FlexBridge 1.4 Candidate Saved Opportunities & Notifications Hub (FB-182) Forensic Report

**Sana**: 2026-11-15  
**Ishlab chiquvchi**: Antigravity Autonomous Agent  
**Tegishli Issue**: [#182](https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/182)  
**Tarmoq**: `feature/182-candidate-saved-opportunities-notifications-hub`  
**Baza tarmoq**: `integration/r1-agent-collaboration`  
**Muvofiqlik statusi**: 100% GREEN (20/20 Staging Suites Passed)  

---

## 1. Vazifa va arxitektura qamrovi

Ushbu bosqichda FlexBridge platformasida nomzodlar uchun eng zarur qulayliklar bo'lgan **Saqlangan Vakansiyalar (Xatcho'plar / Bookmarks)** va **Shaxsiy Bildirishnomalar Inbox oqimi hamda O'qilganlik kvitansiyalari (Read Receipts)** to'liq Next.js 16 (App Router) BFF va Enterprise Backend qatlamlari orqali amalga oshirildi.

### Qamrab olingan Kanonik Shartnomalar:
1. **`API-004`**: `POST /api/v1/saved-opportunities` (CAP-006 / CANDIDATE / DB-008 / DB-040).
   - Nomzod vakansiyani saqlab qo'yishi (`saved=True`, HTTP 201 Created).
   - Qayta takroriy saqlash so'rovlari bo'yicha to'liq idempotentlik (`saved=True`, HTTP 200 OK).
   - Toggle rejimi: agar `toggle=True` bo'lsa va e'lon avval saqlangan bo'lsa, xatcho'plardan avtomatik o'chiriladi (`saved=False`, HTTP 200 OK).
   - Nomzod izolyatsiyasi: faqat o'z nomzod profili nomidan e'lon saqlash kafolatlanadi.
   - Audit logging: `OPPORTUNITY_SAVED` va `OPPORTUNITY_UNSAVED` audit voqealari qayd etiladi.
2. **`API-037`**: `GET /api/v1/me/saved-opportunities` (CAP-006 / CANDIDATE / DB-008).
   - Nomzodning barcha saqlangan e'lonlari ro'yxati (paginatsiya bilan).
   - Vakansiyaning joriy holati saqlanadi: agar ish beruvchi e'lonni yopgan (`CLOSED` / `ARCHIVED`) bo'lsa ham, nomzod ro'yxatida `is_closed: true` ko'rsatkichi bilan saqlanib turadi.
   - Saralash: eng so'nggi saqlangan e'lonlar birinchi bo'lib chiqadi (`created_at DESC`).
3. **`API-038`**: `DELETE /api/v1/me/saved-opportunities/{id}` (CAP-006 / CANDIDATE / DB-008).
   - Saqlangan e'lonni xatcho'plardan o'chirish (identifikator sifatida `saved_opportunity.id` yoki bevosita `opportunity_id` qabul qilinadi).
   - Idempotent repeat: allaqachon o'chirilgan yoki mavjud bo'lmagan e'lonni qayta o'chirish HTTP 204 No Content qaytaradi.
   - Cross-candidate IDOR himoyasi: begona nomzodning saqlangan e'lonini o'chirish qat'iy HTTP 403 `SAVED_OPPORTUNITY_ACCESS_DENIED` bilan to'xtatiladi.
4. **`API-031`**: `GET /api/v1/me/notifications` & `POST /api/v1/me/notifications/{id}/read` (CAP-030 / AC-029 / DB-085 / DB-086).
   - Foydalanuvchining shaxsiy bildirishnomalar oqimi (`unread_only` filtri, kursorli paginatsiya).
   - Tranzaksiyaviy outbox voqealari bilan uzviy bog'langanlik (`outbox_events`).
   - Xabarni o'qilgan deb tasdiqlash (`POST /api/v1/me/notifications/{id}/read`): `read_at` vaqt tamg'asi qayd qilinadi va `NOTIFICATION_READ` audit voqeasi yoziladi.
   - Boshqa foydalanuvchining xabarini o'qish/o'zgartirish urinishlarida uniform HTTP 404 anti-enumeration himoyasi.

---

## 2. Amalga oshirilgan fayllar va o'zgarishlar

### A. Next.js BFF Endpoints:
- `frontend/src/app/api/bff/me/saved-opportunities/route.ts` (`GET` ro'yxat, `POST` saqlash/toggle).
- `frontend/src/app/api/bff/me/saved-opportunities/[id]/route.ts` (`DELETE` o'chirish).
- `frontend/src/app/api/bff/candidate/saved-opportunities/[id]/route.ts` (moslik yo'lagi).
- `frontend/src/app/api/bff/me/notifications/route.ts` (`GET` xabarnomalar).
- `frontend/src/app/api/bff/me/notifications/[id]/read/route.ts` (`POST` o'qilgan deb belgilash).

### B. TypeScript SDK & Models:
- `frontend/src/lib/api.ts`:
  - `SavedOpportunityItem`, `SavedOpportunitiesResponse`, `SaveOpportunityResult`.
  - `NotificationItem`, `NotificationsResponse`.
  - SDK Funksiyalari:
    - `fetchMySavedOpportunities(page, pageSize)`
    - `saveOpportunity(opportunityId, toggle)`
    - `deleteSavedOpportunity(identifier)`
    - `fetchMyNotifications(unreadOnly, limit, after)`
    - `markNotificationRead(notificationId)`

### C. Frontend UI Sahifalari va Komponentlar:
- `frontend/src/app/nomzod/saqlanganlar/page.tsx`:
  - Saqlangan vakansiyalar xabi: telemetriya kartalari (Jami, Faol, Yopilgan/Arxiv), har bir e'lon kartasida ish rejimi, shartnoma formati, tashkilot ID va holat indikatorlari, "Batafsil ko'rish" va "O'chirish" amallari.
- `frontend/src/app/nomzod/bildirishnomalar/page.tsx`:
  - Shaxsiy xabarnomalar xabi: "Barchasi" va "Faqat o'qilmagan" filtrlari, telemetriya metrikalari, xabar shabloni, vaqt tamg'asi, arizalar/amaliyot/yordam bo'limlariga to'g'ridan-to'g'ri havolalar va "O'qilgan deb belgilash" interaktiv tugmasi.
- `frontend/src/app/ishlar/[id]/page.tsx`:
  - Vakansiya batafsil sahifasida bevosita "Saqlab qo'yish" (Bookmark/Save) interaktiv toggle tugmasi integratsiya qilindi.
- `frontend/src/components/Navbar.tsx`:
  - Navbarda "Saqlanganlar" (`/nomzod/saqlanganlar`) va "Xabarlar" (`/nomzod/bildirishnomalar`) tezkor havolalari qo'shildi.

### D. Staging Verifikatsiya Testlari:
- `scripts/test_candidate_saved_notifications_staging.py`:
  - 10 bosqichli to'liq regressiya:
    - Phase 1: 401 Unauthenticated rejection on all 5 endpoints.
    - Phase 2: 403 CSRF_ORIGIN_MISMATCH rejection on mutating endpoints.
    - Phase 3: DB Fixtures setup via PgBouncer (Users, Candidates, Opportunities, Outbox Events, Notifications).
    - Phase 4: Candidate authentication via BFF and session assurance elevation to MFA.
    - Phase 5: API-004 Save Opportunity (201 Created, DB row verified).
    - Phase 6: API-004 Idempotent repeat (200 OK) and Toggle unsave (200 OK, DB row deleted).
    - Phase 7: API-037 List Candidate's Saved Opportunities (200 OK, status verified).
    - Phase 8: API-038 Delete Saved Opportunity (200/204) with idempotent repeat.
    - Phase 9: API-031 Notifications stream and Mark-as-Read receipt (`read_at` updated).
    - Phase 10: Negative Authorization & Cross-Candidate IDOR Isolation (403 on cross-candidate unsave, 404 on cross-candidate notification read).

---

## 3. Verifikatsiya Natijalari

1. **Next.js Production Build**:
   - `npm run build` muvaffaqiyatli yakunlandi (48 ta marshrut xatoliksiz kompilyatsiya qilindi).
2. **Dedicated Staging Test Suite**:
   - `scripts/test_candidate_saved_notifications_staging.py` 100% GREEN (barcha 10 ta faza muvaffaqiyatli).
3. **Comprehensive Regression**:
   - `scripts/run_all_staging_tests.py` orqali barcha 20 ta staging test to'plamlari 100% GREEN yakunlandi.
4. **Frozen Main & Isolation**:
   - `origin/main` o'zgarishsiz muzlatilgan holatda (`764fb98496fa40857acb07844fd09fcafa99b7d6`).
   - Barcha o'zgarishlar `integration/r1-agent-collaboration` bazasidan yaratilgan va unga yo'naltirilgan.
   - `pg_live` katalogiga bironta so'rov yuborilmadi; barcha DB operatsiyalari faqat PgBouncer (`127.0.0.1:5432/flexbridge`) orqali amalga oshirildi.
