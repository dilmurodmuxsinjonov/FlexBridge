# API amallari kontrakt jadvali

Method + path + operation role + CAP scope birga ishlaydi. GUEST qatnashgan AUTH/INVITE oilasida POSTning o‘z auth/purpose tekshiruvi bor; taklif GET minimal, accept verified login bilan. /operator amallari faqat ko‘rsatilgan operator rolida. Bu OpenAPI JSON schema tayyorligi yoki ishlayotgan endpoint da’vosi emas.

| API va method | Path | CAP / amal rollari |
| --- | --- | --- |
| API-001 GET | /api/v1/opportunities | CAP-001 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-002 GET | /api/v1/onboarding/options | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-003 POST | /api/v1/matching/preview | CAP-005 / CANDIDATE, STUDENT |
| API-004 POST | /api/v1/saved-opportunities | CAP-006 / CANDIDATE, STUDENT |
| API-005 GET | /api/v1/opportunities/{id} | CAP-001 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-006 POST | /api/v1/opportunities/{id}/applications | CAP-007 / CANDIDATE, STUDENT |
| API-007 POST | /api/v1/moderation-cases | CAP-032 / CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, TEACHER, COORDINATOR |
| API-008 GET | /api/v1/organizations/{id}/public | CAP-001 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-009 GET | /api/v1/organizations/{id}/opportunities | CAP-001 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-010 GET | /api/v1/organizations/{id}/rating-summary | CAP-040 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR |
| API-011 GET | /api/v1/services/public | CAP-039 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-012 GET | /api/v1/prices/public | CAP-039 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-013 GET | /api/v1/help/{document} | CAP-039 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-014 GET | /api/v1/policies/{document} | CAP-039 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-015 POST | /api/v1/auth/register | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-016 POST | /api/v1/auth/challenges | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-017 GET | /api/v1/institution-onboarding/options | CAP-019 / COORDINATOR |
| API-018 POST | /api/v1/auth/login | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-019 POST | /api/v1/auth/mfa/verify | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-020 POST | /api/v1/auth/challenges/{id}/consume | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-021 POST | /api/v1/auth/challenges/{id}/resend | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-022 POST | /api/v1/auth/recovery | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-023 GET | /api/v1/auth/recovery/{id} | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-024 GET | /api/v1/invitations/{token} | CAP-015 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-025 POST | /api/v1/invitations/{token}/accept | CAP-015 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-026 PATCH | /api/v1/me/candidate | CAP-003 / CANDIDATE, STUDENT |
| API-027 POST | /api/v1/me/enrollments | CAP-004 / CANDIDATE, STUDENT |
| API-028 PUT | /api/v1/me/availability | CAP-005 / CANDIDATE, STUDENT |
| API-029 GET | /api/v1/me/applications/summary | CAP-007 / CANDIDATE, STUDENT |
| API-030 GET | /api/v1/me/placements | CAP-018 / CANDIDATE, STUDENT, MENTOR, TEACHER |
| API-031 GET | /api/v1/me/notifications | CAP-031 / CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-032 PATCH | /api/v1/me/candidate/skills | CAP-003 / CANDIDATE, STUDENT |
| API-033 POST | /api/v1/me/candidate/cv | CAP-003 / CANDIDATE, STUDENT |
| API-034 GET | /api/v1/me/enrollments | CAP-004 / CANDIDATE, STUDENT |
| API-035 GET | /api/v1/me/availability | CAP-005 / CANDIDATE, STUDENT |
| API-036 PUT | /api/v1/me/availability/exceptions | CAP-005 / CANDIDATE, STUDENT |
| API-037 GET | /api/v1/me/saved-opportunities | CAP-006 / CANDIDATE, STUDENT |
| API-038 DELETE | /api/v1/me/saved-opportunities/{id} | CAP-006 / CANDIDATE, STUDENT |
| API-039 GET | /api/v1/me/applications | CAP-007 / CANDIDATE, STUDENT |
| API-040 POST | /api/v1/me/applications/{id}/reapply | CAP-007 / CANDIDATE, STUDENT |
| API-041 GET | /api/v1/me/applications/{id} | CAP-007 / CANDIDATE, STUDENT |
| API-042 POST | /api/v1/interviews/{id}/responses | CAP-009 / CANDIDATE, STUDENT, OWNER, HR |
| API-043 POST | /api/v1/offers/{id}/respond | CAP-011 / CANDIDATE, STUDENT |
| API-044 POST | /api/v1/me/applications/{id}/withdraw | CAP-007 / CANDIDATE, STUDENT |
| API-045 GET | /api/v1/me/engagements/{id} | CAP-012 / CANDIDATE, STUDENT, OWNER, HR |
| API-046 POST | /api/v1/engagements/{id}/confirmations | CAP-012 / CANDIDATE, STUDENT, OWNER, HR |
| API-047 POST | /api/v1/engagements/{id}/ratings | CAP-027 / CANDIDATE, STUDENT, HR, HOST_COORDINATOR, MENTOR, TEACHER |
| API-048 POST | /api/v1/placements/{id}/accept | CAP-018 / CANDIDATE, STUDENT, MENTOR, TEACHER |
| API-049 POST | /api/v1/placements/{id}/completion-requests | CAP-025 / CANDIDATE, STUDENT, HOST_COORDINATOR, MENTOR, TEACHER, COORDINATOR |
| API-050 GET | /api/v1/placements/{id}/plan | CAP-018 / CANDIDATE, STUDENT, MENTOR, TEACHER |
| API-051 POST | /api/v1/placements/{id}/assignments/{assignment}/accept | CAP-018 / CANDIDATE, STUDENT, MENTOR, TEACHER |
| API-052 POST | /api/v1/placements/{id}/exports | CAP-026 / CANDIDATE, STUDENT, MENTOR, TEACHER, COORDINATOR |
| API-053 GET | /api/v1/placements/{id}/logs | CAP-022 / CANDIDATE, STUDENT |
| API-054 PUT | /api/v1/placements/{id}/logs/{date} | CAP-022 / CANDIDATE, STUDENT |
| API-055 POST | /api/v1/log-entries/{id}/evidence | CAP-022 / CANDIDATE, STUDENT |
| API-056 POST | /api/v1/logs/{id}/submit | CAP-022 / CANDIDATE, STUDENT |
| API-057 GET | /api/v1/me/ratings | CAP-027 / CANDIDATE, STUDENT, HR, HOST_COORDINATOR, MENTOR, TEACHER |
| API-058 POST | /api/v1/ratings/{id}/appeals | CAP-028 / CANDIDATE, STUDENT, OWNER, HR, MENTOR, TEACHER, MODERATOR |
| API-059 PUT | /api/v1/me/notification-preferences | CAP-031 / CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-060 PATCH | /api/v1/me/security | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-061 DELETE | /api/v1/me/sessions/{id} | CAP-002 / GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-062 POST | /api/v1/me/privacy-requests | CAP-035 / CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-063 GET | /api/v1/me/support-tickets | CAP-034 / CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-064 POST | /api/v1/support-tickets/{id}/messages | CAP-034 / CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| API-065 POST | /api/v1/organizations | CAP-013 / OWNER, HOST_COORDINATOR |
| API-066 POST | /api/v1/organizations/{id}/verification | CAP-013 / OWNER, HOST_COORDINATOR |
| API-067 GET | /api/v1/organizations/{id}/verification | CAP-013 / OWNER, HOST_COORDINATOR |
| API-068 GET | /api/v1/organizations/{org}/dashboard | CAP-008 / OWNER, HR, HOST_COORDINATOR |
| API-069 GET | /api/v1/organizations/{org}/placements | CAP-017 / OWNER, HOST_COORDINATOR |
| API-070 GET | /api/v1/organizations/{org}/entitlements | CAP-029 / OWNER, BILLING |
| API-071 PATCH | /api/v1/organizations/{org} | CAP-013 / OWNER, HOST_COORDINATOR |
| API-072 GET | /api/v1/organizations/{org}/capabilities | CAP-013 / OWNER, HOST_COORDINATOR |
| API-073 GET | /api/v1/organizations/{org}/memberships | CAP-014 / OWNER |
| API-074 POST | /api/v1/organizations/{org}/invitations | CAP-014 / OWNER |
| API-075 POST | /api/v1/organizations/{org}/memberships/{id}/revoke | CAP-014 / OWNER |
| API-076 GET | /api/v1/organizations/{org}/opportunities | CAP-016 / OWNER, HR, HOST_COORDINATOR |
| API-077 POST | /api/v1/opportunities/{id}/transition | CAP-016 / OWNER, HR, HOST_COORDINATOR |
| API-078 PUT | /api/v1/opportunities/{id}/draft | CAP-016 / OWNER, HR, HOST_COORDINATOR |
| API-079 PUT | /api/v1/opportunities/{id}/draft/terms | CAP-016 / OWNER, HR, HOST_COORDINATOR |
| API-080 PUT | /api/v1/opportunities/{id}/draft/schedule | CAP-016 / OWNER, HR, HOST_COORDINATOR |
| API-081 POST | /api/v1/opportunities/{id}/publish | CAP-016 / OWNER, HR, HOST_COORDINATOR |
| API-082 GET | /api/v1/opportunities/{id}/applications | CAP-008 / OWNER, HR, HOST_COORDINATOR |
| API-083 POST | /api/v1/applications/{id}/transition | CAP-008 / OWNER, HR, HOST_COORDINATOR |
| API-084 GET | /api/v1/applications/{id}/hr | CAP-008 / OWNER, HR, HOST_COORDINATOR |
| API-085 POST | /api/v1/applications/{id}/interviews | CAP-009 / CANDIDATE, STUDENT, OWNER, HR |
| API-086 POST | /api/v1/applications/{id}/offers | CAP-010 / OWNER, HR, HOST_COORDINATOR |
| API-087 POST | /api/v1/placements/{id}/mentor-assignments | CAP-017 / OWNER, HOST_COORDINATOR |
| API-088 POST | /api/v1/placements/{id}/host-decisions | CAP-025 / CANDIDATE, STUDENT, HOST_COORDINATOR, MENTOR, TEACHER, COORDINATOR |
| API-089 GET | /api/v1/me/mentor-assignments | CAP-018 / CANDIDATE, STUDENT, MENTOR, TEACHER |
| API-090 GET | /api/v1/me/mentor-review-queue | CAP-023 / MENTOR |
| API-091 GET | /api/v1/log-revisions/{revision}/workplace | CAP-023 / MENTOR |
| API-092 POST | /api/v1/log-revisions/{revision}/workplace-reviews | CAP-023 / MENTOR |
| API-093 GET | /api/v1/organizations/{org}/billing | CAP-029 / OWNER, BILLING |
| API-094 POST | /api/v1/organizations/{org}/orders | CAP-029 / OWNER, BILLING |
| API-095 POST | /api/v1/orders/{id}/refund-requests | CAP-030 / OWNER, BILLING, FINANCE |
| API-096 POST | /api/v1/institution-appointments | CAP-019 / COORDINATOR |
| API-097 GET | /api/v1/institution-appointments/{id} | CAP-019 / COORDINATOR |
| API-098 GET | /api/v1/institutions/{inst}/supervisions | CAP-021 / COORDINATOR, TEACHER |
| API-099 GET | /api/v1/institutions/{inst}/assignment-queue | CAP-020 / COORDINATOR |
| API-100 POST | /api/v1/institutions/{inst}/exports | CAP-026 / CANDIDATE, STUDENT, MENTOR, TEACHER, COORDINATOR |
| API-101 POST | /api/v1/student-supervisions | CAP-020 / COORDINATOR |
| API-102 POST | /api/v1/placements/{id}/academic-assignments | CAP-020 / COORDINATOR |
| API-103 POST | /api/v1/academic-assignments/{id}/revoke | CAP-020 / COORDINATOR |
| API-104 GET | /api/v1/me/academic-assignments | CAP-018 / CANDIDATE, STUDENT, MENTOR, TEACHER |
| API-105 GET | /api/v1/me/academic-review-queue | CAP-021 / COORDINATOR, TEACHER |
| API-106 GET | /api/v1/log-revisions/{revision}/academic | CAP-021 / COORDINATOR, TEACHER |
| API-107 POST | /api/v1/log-revisions/{revision}/academic-reviews | CAP-024 / TEACHER |
| API-108 POST | /api/v1/placements/{id}/academic-decisions | CAP-024 / TEACHER |
| API-109 GET | /api/v1/operator/verification-cases | CAP-033 / MODERATOR |
| API-110 POST | /api/v1/operator/verification-cases/{id}/decide | CAP-033 / MODERATOR |
| API-111 POST | /api/v1/operator/moderation-cases/{id}/actions | CAP-033 / MODERATOR |
| API-112 GET | /api/v1/operator/support-tickets | CAP-034 / SUPPORT |
| API-113 POST | /api/v1/operator/support-tickets/{id}/messages | CAP-034 / SUPPORT |
| API-114 POST | /api/v1/operator/privacy-requests/{id}/resolve | CAP-035 / SUPPORT |
| API-115 GET | /api/v1/operator/reconciliation | CAP-030 / FINANCE |
| API-116 POST | /api/v1/operator/refunds/{id}/approve | CAP-030 / FINANCE |
| API-117 GET | /api/v1/operator/finance-summary | CAP-038 / FINANCE |
| API-118 GET | /api/v1/operator/audit-events | CAP-036 / ADMIN |
| API-119 POST | /api/v1/operator/access-requests | CAP-036 / ADMIN |
| API-120 POST | /api/v1/operator/users/{id}/revoke-sessions | CAP-036 / ADMIN |
| API-121 PATCH | /api/v1/operator/feature-flags/{code} | CAP-037 / ADMIN |
| API-122 POST | /api/v1/operator/incidents | CAP-037 / ADMIN |
| API-123 GET | /api/v1/operator/restore-runs | CAP-037 / ADMIN |
| API-124 GET | /api/v1/operator/analytics | CAP-037 / ADMIN |

## Umumiy yordamchi APIlar

Quyidagi APIlar sahifa bo‘limlarida fayl/OTP/worker yordamchi amallari sifatida qo‘llanadi; alohida mahsulot sahifasi emas.

| Kod | Method/path | Shart |
| --- | --- | --- |
| API-X01 | POST /api/v1/files/upload-intents | Owner, maqsad va scope; size/MIME allowlist |
| API-X02 | POST /api/v1/files/{id}/finalize | Hash, byte size va karantin scan; boshqa user file rad |
| API-X03 | GET /api/v1/files/{id}/download | Joriy scope, clean scan, short URL/proxy va audit |
| API-X04 | POST /api/v1/auth/logout | Joriy sessiya revoke; local private draft clear |
| API-X05 | POST /api/v1/webhooks/payments/{provider} | Provayderning aniq auth/protokoli; event dedupe/order/amount |
| API-X06 | POST /api/v1/webhooks/delivery/{provider} | Verified provider callback; delivery login proof emas |
| API-X07 | GET /api/v1/health/ready | Public minimal healthy/unhealthy; ichki secrets/DB tafsiloti yo‘q |
| API-X08 | POST /api/v1/me/notifications/{id}/read | O‘z notificationi; retry idempotent |
