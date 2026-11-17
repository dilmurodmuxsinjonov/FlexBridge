# Implementation Plan: Canonical Opportunity Details (API-005) & Notification Inbox (API-031)

- **Issue**: [#100](https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/100)
- **Branch**: `feature/100-opportunity-details-and-notifications`
- **Target Branch**: `integration/r1-agent-collaboration`
- **Main Status**: strictly FROZEN at `764fb98496fa40857acb07844fd09fcafa99b7d6`

---

## 1. Specifications & Contracts
- **API-005**: `GET /api/v1/opportunities/{id}` (`CAP-001`, `DB-035`, `DB-036`, `DB-037`, `DB-038`, `DB-021`, `DB-013`)
  - Public guest and authenticated user access to published and closed opportunities.
  - Returns opportunity status, capacity, occupied count, vacancies available.
  - Returns revision details (compensation, contract type, work mode, eligibility, dates).
  - Returns owning organization public details.
  - Returns linked skills and required levels.
  - Returns structured shift schedules.
  - Visibility enforcement: `PUBLISHED` and `CLOSED` visible to public; `DRAFT` and `PENDING_MODERATION` restricted to owning org (`OWNER`, `HR`, `HOST_COORDINATOR`) or platform `ADMIN`/`MODERATOR` (404 otherwise).

- **API-031**: `GET /api/v1/me/notifications` (`CAP-031`, `DB-085`, `DB-087`, `DB-088`)
  - Authenticated user transactional notification inbox.
  - Filtering by read/unread statuses (`unread_only` flag).
  - Keyset cursor pagination (`limit`, `after`, `next_after`).
  - Returns associated scopes (`placement_id`, `opportunity_id`, `application_id`, `ticket_id`).
  - Strict isolation: User A cannot inspect or mark User B's notifications.
  - Privacy protection: Unverified outbox payloads are never leaked.

---

## 2. Architecture & Implementation Decisions
1. **Authentication Boundary (`backend/app/main.py`)**:
   - Extended `authentication_boundary` middleware to allow public `GET /api/v1/opportunities/{id}` while keeping `/feed` and other routes behind strict `require_actor_context`.
2. **Optional Actor Context (`backend/app/api/dependencies.py`)**:
   - `optional_actor_context` extracts and validates `ActorContext` if `Authorization: Bearer <token>` is present, or returns `None` for unauthenticated guests.
   - Forged or expired tokens are rejected with 401 `AUTH_REQUIRED`.
3. **Service Layer (`opportunities.py` & `mentor_notices.py`)**:
   - `opportunity_service.get_opportunity_detail`: Efficient single-connection transaction querying opportunity, current revision, organization, opportunity_skills, and shifts.
   - `notification_service.own`: Returns keyset pagination with cursor validation and linked scopes.
