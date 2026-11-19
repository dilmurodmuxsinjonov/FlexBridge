# FB-196: Telegram Bot Phone Verification & OTP Choice Report

- **Date**: 2026-11-15
- **Issue**: #196
- **Branch**: `feature/196-telegram-phone-verification`
- **Target Integration Branch**: `integration/r1-agent-collaboration`
- **Main Frozen Invariant**: `764fb98496fa40857acb07844fd09fcafa99b7d6` (`main` untouched)
- **Database Boundary**: Strictly `PgBouncer` (`127.0.0.1:5432/flexbridge`, `prepare_threshold=None`); `0` queries/mutations to `pg_live`.

---

## 1. Executive Summary

Implemented end-to-end **Telegram Bot Phone Verification & OTP Delivery Choice** for user registration (`/royxatdan-otish`):
1. **Delivery Method Choice (`SMS` vs `TELEGRAM`)**:
   - Users registering on `/royxatdan-otish` (Step 2) can select between receiving their 6-digit verification code via **SMS xabar (`SMS`)** or **Telegram Bot (`TELEGRAM`)**.
2. **Telegram Bot Startup Contact Prompt (`/start`)**:
   - When the user starts the bot (`/start` or `/start <challenge_id>`), `TelegramBotVerificationService` binds the session and responds with a native Telegram `ReplyKeyboardMarkup` button (`request_contact: True` — `📱 Telefon raqamni yuborish`).
3. **Bot-Level Phone Verification & Anti-Spoofing Guards**:
   - **Native Contact Enforcement**: Rejects plain-text phone numbers typed manually in the chat (`422 TELEGRAM_NATIVE_CONTACT_REQUIRED`).
   - **Contact Ownership Verification**: Verifies `message.contact.user_id == message.from.id` so a user cannot forward someone else's contact card (`403 TELEGRAM_CONTACT_OWNERSHIP_MISMATCH`).
   - **Website vs Telegram Phone Strict Equality**: Normalizes `message.contact.phone_number` and checks strict equality against the phone number entered on the FlexBridge website for the active challenge (`409 TELEGRAM_PHONE_MISMATCH`).
   - **Pre-Verification Consume Guard**: Blocks consuming a `TELEGRAM` challenge before the Telegram Bot verifies the matching phone contact (`403 TELEGRAM_CONTACT_REQUIRED`).

---

## 2. Delivered Components

### A. Backend (`FastAPI` + `SQLAlchemy Core`)
- [`backend/app/services/telegram_bot.py`](file:///D:/FlexBridge/backend/app/services/telegram_bot.py):
  - `TelegramBotVerificationService.handle_update(update, ip, explicit_challenge_id)`
- [`backend/app/services/identity.py`](file:///D:/FlexBridge/backend/app/services/identity.py):
  - `delivery_method` (`SMS` | `TELEGRAM`) in `issue_challenge`, `_issue`, `resend`, `challenge_status`, and `consume`.
- [`backend/app/api/v1/iam.py`](file:///D:/FlexBridge/backend/app/api/v1/iam.py):
  - `GET /api/v1/auth/options` (`delivery_methods: ["SMS", "TELEGRAM"]`, `telegram_bot_username`)
  - `POST /api/v1/auth/challenges` (`delivery_method` support)
  - `GET /api/v1/auth/challenges/{id}/status`
  - `POST /api/v1/auth/telegram/webhook`

### B. Next.js 16 BFF & Registration Wizard UI
- [`frontend/src/app/api/bff/auth/challenges/route.ts`](file:///D:/FlexBridge/frontend/src/app/api/bff/auth/challenges/route.ts)
- [`frontend/src/app/api/bff/auth/challenges/[id]/status/route.ts`](file:///D:/FlexBridge/frontend/src/app/api/bff/auth/challenges/[id]/status/route.ts)
- [`frontend/src/app/api/bff/auth/telegram/webhook/route.ts`](file:///D:/FlexBridge/frontend/src/app/api/bff/auth/telegram/webhook/route.ts)
- [`frontend/src/lib/api.ts`](file:///D:/FlexBridge/frontend/src/lib/api.ts)
- [`frontend/src/app/royxatdan-otish/page.tsx`](file:///D:/FlexBridge/frontend/src/app/royxatdan-otish/page.tsx)

---

## 3. Staging Verification (10 Phases + 28-Suite Full Regression)

- **Dedicated Suite (`scripts/test_telegram_phone_verification_staging.py`)**: **10/10 PHASES PASSED 100% GREEN**
- **Master Regression Runner (`scripts/run_all_staging_tests.py`)**: **28/28 SUITES PASSED 100% GREEN**
