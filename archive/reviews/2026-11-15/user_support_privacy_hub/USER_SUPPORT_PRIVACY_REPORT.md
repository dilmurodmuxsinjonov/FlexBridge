# FlexBridge 1.4 User Support, Privacy Rights & Notification Preferences Hub (FB-178) Forensic Report

**Sana**: 2026-11-15  
**Ishlab chiquvchi**: Antigravity Autonomous Agent  
**Tegishli Issue**: [#178](https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/178)  
**Tarmoq**: `feature/178-user-support-privacy-notifications-hub`  
**Baza tarmoq**: `integration/r1-agent-collaboration`  
**Muvofiqlik statusi**: 100% GREEN (18/18 Staging Suites Passed)  

---

## 1. Vazifa va arxitektura qamrovi

Ushbu bosqichda FlexBridge platformasining nomzod va barcha autentifikatsiyalangan foydalanuvchilar markazi bo'lgan **Qo'llab-quvvatlash, Maxfiylik huquqlari (GDPR/APPI) va Bildirishnoma sozlamalari xabi (`/nomzod/yordam`)** to'liq Next.js 16 (App Router + Turbopack) BFF va Enterprise Backend qatlamlari orqali amalga oshirildi.

### Qamrab olingan Kanonik Shartnomalar:
1. **`API-063`**: `GET /api/v1/me/support-tickets` & `POST /api/v1/me/support-tickets` (CAP-033 / AC-032 / DB-080).
   - Foydalanuvchining shaxsiy tiketlari ro'yxati va yangi tiket ochish.
   - Kategoriyalar: `GENERAL`, `TECHNICAL`, `BILLING`, `ACCOUNT`, `PLACEMENT`.
   - Ustuvorliklar va SLA kuzatuvi: `LOW`, `NORMAL`, `HIGH`, `URGENT` (`first_response_due_at`).
2. **`API-064`**: `GET /api/v1/support-tickets/{id}/messages` & `POST /api/v1/support-tickets/{id}/messages` (CAP-033 / AC-032 / DB-081).
   - Tiket bo'yicha to'liq suhbat tarixi va foydalanuvchining javob xabarlari.
   - Ichki operator qaydlari (`internal=True`) nomzodlarga ko'rinmaslik kafolati.
3. **`API-062`**: `GET /api/v1/me/privacy-requests` & `POST /api/v1/me/privacy-requests` (CAP-032 / AC-031 / DB-082 / DB-084).
   - GDPR/O'zbekiston qonunchiligi bo'yicha shaxsiy ma'lumotlar huquqlari (`EXPORT`, `DELETE`, `RECTIFY`).
   - 30 kunlik qonuniy ijro SLA muddati (`due_at`).
   - Anti-duplication / in-flight concurrency himoyasi (`PRIVACY_REQUEST_ALREADY_PENDING` 409).
4. **`API-114`**: `POST /api/v1/operator/privacy-requests/{id}/resolve` (CAP-035 / PRIVACY / DB-082 / DB-084).
   - Operator tomonidan ma'lumotlar eksporti/o'chirilishi bo'yicha qaror qabul qilish (`RESOLVED`, `COMPLETED`, `REJECTED`).
   - O'z-o'zini tasdiqlash taqiqlangan (`SELF_RESOLUTION_FORBIDDEN` 403).
5. **`API-059`**: `GET /api/v1/me/notification-preferences` & `PUT /api/v1/me/notification-preferences` (CAP-031 / AC-030 / DB-085 / DB-011).
   - Kanallar: `EMAIL`, `SMS`, `PUSH`, `WHATSAPP`.
   - Maqsadlar: `TRANSACTIONAL`, `SECURITY`, `MARKETING`.
   - Invariant: `TRANSACTIONAL` va `SECURITY` xabarnomalari barcha kanallar bo'yicha to'liq o'chirib qo'yilishi qat'iyan taqiqlanadi (xavfsizlik kafolati).
   - Marketing xabarnomalari o'zgarishi `DB-011 consent_events` ro'yxatida huquqiy qayd etiladi.

---

## 2. Amalga oshirilgan fayllar va o'zgarishlar

### A. Next.js BFF Endpoints:
- `frontend/src/app/api/bff/me/support-tickets/route.ts` (GET va POST).
- `frontend/src/app/api/bff/support-tickets/[id]/messages/route.ts` (GET va POST).
- `frontend/src/app/api/bff/me/privacy-requests/route.ts` (GET va POST).
- `frontend/src/app/api/bff/operator/privacy-requests/[id]/resolve/route.ts` (POST).
- `frontend/src/app/api/bff/me/notification-preferences/route.ts` (GET va PUT).

### B. TypeScript SDK & Models:
- `frontend/src/lib/api.ts`:
  - `CustomerSupportTicketItem`, `CustomerSupportMessageItem`, `CreateSupportTicketPayload`, `CustomerSupportTicketsResponse`, `CustomerSupportMessagesResponse`.
  - `CustomerPrivacyRequestItem`, `CreatePrivacyRequestPayload`, `CustomerPrivacyRequestsResponse`, `ResolveOperatorPrivacyPayload`.
  - `NotificationPreferenceItem`, `NotificationPreferencesResponse`, `UpdateNotificationPreferencesPayload`.
  - `fetchMySupportTickets()`, `createSupportTicket()`, `fetchSupportTicketMessages()`, `postCustomerSupportMessage()`.
  - `fetchMyPrivacyRequests()`, `createPrivacyRequest()`, `resolveOperatorPrivacyRequest()`.
  - `fetchMyNotificationPreferences()`, `updateMyNotificationPreferences()`.

### C. Frontend Hub Sahifasi:
- `frontend/src/app/nomzod/yordam/page.tsx`:
  - 3 ta interaktiv tab:
    1. **Texnik va umumiy yordam (Mening tiketlarim)**: Tiketlar ro'yxati, yangi tiket yaratish modal formasi, dialog oynasi orqali chat ko'rinishida xabar almashish.
    2. **Maxfiylik va Shaxsiy ma'lumotlar (GDPR/APPI)**: Ma'lumotlarni eksport qilish (`EXPORT`), profilingni tozalash/o'chirish (`DELETE`), tuzatish kiritish (`RECTIFY`) so'rovlarini topshirish va ularning holatini kuzatish.
    3. **Bildirishnoma sozlamalari (Matrix)**: Email, SMS, Push kanallari bo'yicha Xavfsizlik, Tranzaksiyaviy va Marketing xabarlarini boshqarish.

### D. Staging Verifikatsiya Testlari:
- `scripts/test_user_support_privacy_staging.py`:
  - 10 bosqichli test suite 100% GREEN natija ko'rsatdi:
    - Phase 1: 401 Unauthenticated rejection on all endpoints.
    - Phase 2: 403 CSRF_ORIGIN_MISMATCH rejection on mutating endpoints.
    - Phase 3: DB Fixtures setup via PgBouncer with `chk_platform_grant_not_self` compliance.
    - Phase 4: Authentication via BFF and session assurance elevation to MFA.
    - Phase 5: API-063 Ticket creation and list verification.
    - Phase 6: API-064 Message thread conversation verification.
    - Phase 7: API-062 Privacy request lifecycle.
    - Phase 8: API-114 Operator privacy request resolution.
    - Phase 9: API-059 Notification preferences retrieval & mutation.
    - Phase 10: Negative authorization checks (Candidate 403 on operator resolution, Operator 403 on self-resolution).
- `scripts/run_all_staging_tests.py`:
  - 18/18 barcha staging testlari 32.36 soniyada 100% GREEN o'tdi.

---

## 3. Qat'iy Invariantlar Tekshiruvi

| Qoida / Invariant | Holat | Izoh |
| :--- | :--- | :--- |
| **FROZEN MAIN** | ✅ SAQLANDI | `main` filiali `764fb98496fa40857acb07844fd09fcafa99b7d6` hashida daxlsiz saqlandi. |
| **INTEGRATION PR TARGET** | ✅ SAQLANDI | Barcha o'zgarishlar `integration/r1-agent-collaboration` filialiga yo'naltirildi. |
| **ZERO PG_LIVE QUERIES** | ✅ SAQLANDI | To'liq PgBouncer (`127.0.0.1:5432/flexbridge`, `prepare_threshold=None`) orqali ishlandi. |
| **ANTI-CSRF ORIGIN GUARD** | ✅ TEKSHIRILDI | Soxta `Origin` sarlavhalari darhol HTTP 403 bilan rad etildi. |
| **DUAL-CONTROL / SELF-ACTION BAN**| ✅ TEKSHIRILDI | Operator o'zining maxfiylik so'rovini o'zi hal qilolmaydi (HTTP 403 `SELF_RESOLUTION_FORBIDDEN`). |
| **TRANSACTIONAL SEGREGATION** | ✅ TEKSHIRILDI | Tranzaksiyaviy va xavfsizlik bildirishnomalarini to'liq o'chirib qo'yish taqiqlangan. |
