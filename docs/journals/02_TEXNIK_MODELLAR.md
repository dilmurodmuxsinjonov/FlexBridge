# FlexBridge — texnik modellar va vositalar

## Joriy holat (2026-11-17, LOG-193)

> Shu bo'lim har ishdan keyin **yangilanadi** — eski «Current LOG-…» qatorlarini faylning boshiga ustma-ust qo'shish to'xtatildi. Oldingi holat qatorlari o'zgarmagan holda `archive/` papkasida.

- **Integratsiya**: `integration/r1-agent-collaboration` — `5331259` (PR #270); LOG-192 (tomchi izi, #272) va LOG-193 (suyuq shisha) PR'lari CI kutmoqda. Barcha yangi PR'lar faqat shu branch'ga, exact-head CI yashil bo'lgandan keyin merge qilinadi.
- **main/master**: `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan; foydalanuvchining aniq ruxsatisiz hech qanday o'zgartirish yo'q.
- **Koordinator**: `D:/Codex/FlexBridge-agents/coordinator_state.json` — egasi `CODEX`, holati `HANDED_BACK` (2026-11-14).
- **So'nggi ishlar**: LOG-185 universitet ichki tablari va operator bento (#258); LOG-186 e'lonlar moderatsiyasi navbati (#260); LOG-187 staging E2E'dan topilgan xabar/yorliq tuzatishlari (#262); LOG-188 «qurilma» dizayni barcha oynalarda (#264); LOG-189 tugmalar, harakatlar va animatsiyalar qatlami (#266); LOG-190 hujjatlarni bo'limlarga ajratish (#268); LOG-191 pastki kapsulada suyuqlik oqimi effekti (#270); LOG-192 suyuqlik ortidan tomchisimon iz (#272); LOG-193 tugmalar bo'rtiq va shaffof suyuq shisha (#273).
- **Staging**: 2026-11-17 da `a6c3e01` dan qayta qurilgan (`flexbridge-r1`, frontend 127.0.0.1:3000, backend 127.0.0.1:8000). 4 rolli brauzer E2E 21/23 (2 tasi kutilgan biznes tekshiruvi), harakat o'lchovi 11/11, 24 skrinshot toza. Tartib: `docs/operations/STAGING_VA_E2E.md`.
- **Ochiq masalalar (foydalanuvchi qarori)**: to'lov provayderi ulanmagan — buyurtmalar `PENDING_PAYMENT` bo'lib qoladi, korxona e'lonni UI orqali nashr qila olmaydi; `infra/.env` kalitlarini almashtirish (foydalanuvchi o'zi bajaradi); staging `.env` da `BFF_SESSION_SECRET` va `TELEGRAM_BOT_TOKEN` yo'q.
- **Qayerdan boshlash**: hujjatlar xaritasi — `docs/README.md`; frontend ishi — `frontend/AGENTS.md` + `docs/frontend/README.md`; backend ishi — `backend/AGENTS.md` + `docs/backend/README.md`.


## Joriy texnik stek (qisqa xulosa, 2026-11-17)

- **Frontend** (`frontend/`): Next.js 16.4.6 (App Router), React 19.2, TypeScript 5.6, Tailwind CSS 3.4, framer-motion, lucide-react; Vitest 4 + Testing Library; ESLint `--max-warnings=0`. Brauzer faqat Next.js server-side BFF (`src/app/api/bff/**`) bilan gaplashadi; BFF shifrlangan HttpOnly sessiya bilan backend'ga proksi qiladi. Batafsil: [`docs/frontend/README.md`](../frontend/README.md).
- **Backend** (`backend/`): Python 3.12 (CI), FastAPI 0.140, Pydantic 2, SQLAlchemy 2 (Core), Alembic 1.20 (head `0023_chat_messaging`, `flexbridge` sxemasida 138 jadval), psycopg 3, PostgreSQL 17 + PgBouncer; outbox, identity-delivery, refund va Telegram worker'lari; MinIO (S3) va ClamAV. Batafsil: [`docs/backend/README.md`](../backend/README.md), [`backend/README.md`](../../backend/README.md).
- **Dizayn tizimi**: monoxrom bento + «qurilma» qobig'i (yuqori to'q kapsula, chap rels, vintli ekran-panel, pastki bo'lim kapsulasi) va taktil harakat qatlami. Ranglar faqat `globals.css` tokenlaridan (`--fb-*`, aksent `#e0622d`). Qoidalar: [`docs/frontend/DIZAYN_VA_HARAKAT.md`](../frontend/DIZAYN_VA_HARAKAT.md).
- **Infra**: `infra/compose.yaml` (loyiha nomi `flexbridge-r1`): postgres, pgbouncer, migrate, backend, worker'lar, telegram-bot (simulyatsiya), minio, clamav, frontend.


## Texnik hujjatda ko'rsatilganlar

Manba: `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf`, 2–7-sahifalar.

| Yo'nalish | Model / texnologiya | Tanlov holati |
| --- | --- | --- |
| Ma'lumotlar bazasi | PostgreSQL (`btree_gist`, `int4range`, `GiST`, `EXCLUDE`, composite FK, `DEFERRABLE` constraintlar); lokal sinov uchun PostgreSQL 17.11 (`D:\Codex\.tools\postgresql-17.11`) va PGlite 0.5.15 (`PostgreSQL 18.6 WASM`) | 1.4 hujjatida belgilangan; `FlexBridge_1_4_schema.sql` (`specs/v1_4/` va ildiz katalogda) yaratildi va 17/17 invariant sinovidan o'tdi (`S1.2`, `T-007` Variant A) |
| DB ulanishlari | PgBouncer | 1.4 hujjatida belgilangan |
| Sessiya va ruxsat keshi | L1 In-memory + Redis invalidation keshi (`TTL = 15s`, `INV-15` darhol revoke) | 1.4 hujjatida va `T-008` Variant A (`Q-010`, 2026-11-06) bilan tasdiqlangan |
| Fayl saqlash | MinIO / S3-mos xususiy obyekt ombori (`quarantine/` prefiksi, signed URL `TTL = 60s`) | 1.4 hujjatida va `T-008` Variant A (`Q-010`, 2026-11-06) bilan tasdiqlangan |
| Antivirus | ClamAV / `clamd`, asinxron worker | 1.4 hujjatida belgilangan |
| PDF strukturaviy tekshiruvi | Python `pypdf` (`/JS`, `/JavaScript`, `/AA`, `/OpenAction`, `/Launch`, `/EmbeddedFiles`, `/RichMedia`, `/XFA` rad etiladi) | 1.4 hujjatida belgilangan |
| Kuchaytirilgan autentifikatsiya | Argon2id (parol xeshi) + PyOTP (TOTP) + `py_webauthn` (Passkey / WebAuthn) | 1.4 hujjatida va `T-008` Variant A (`Q-010`, 2026-11-06) bilan tasdiqlangan |
| Favqulodda bildirishnoma | Telegram Bot API / SMS (adapter interfeysi bilan) | Hujjatdagi kanallar; lokal/sinov muhitida mock+audit adapter, productionda Telegram/SMS provayder (`T-008`) |
| Versiya nazorati va repozitoriy | Git + GitHub (`https://github.com/dilmurodmuxsinjonov/FlexBridge.git`), `gh` CLI | Foydalanuvchi qarori (`Q-008`, 2026-11-06) bilan tasdiqlangan va ulandi |
| Ishlab chiquvchi AI / model | `Antigravity` / `Gemini 4 Argon (High)` | Foydalanuvchi qarori (`Q-009`, 2026-11-06) bilan amalga oshiruvchi AI sifatida ish boshladi |
| Tekshiruvchi AI / model | `Codex` / aniq model nomi noma'lum | Foydalanuvchi tekshiruvchi va tuzatuvchi rolini belgilagan (`Q-002`) |

## Tasdiqlangan texnik stek (`Q-010` / `T-008` Variant A, 2026-11-06) va ochiq tanlovlar

| Yo'nalish | Model / texnologiya | Holat |
| --- | --- | --- |
| Backend tili va framework | Python 3.12 + FastAPI + SQLAlchemy 2.0 (`psycopg` / `asyncpg`) + Pydantic v2 | Tasdiqlangan (`Q-010`, `T-008` Variant A, 2026-11-06) |
| Frontend | Next.js (App Router, TypeScript) + Tailwind CSS (`PG-001..048`) | Tasdiqlangan (`Q-010`, `T-008` Variant A, 2026-11-06) |
| Worker va navbat | Python asinxron worker + Redis (`ClamAV`/`pypdf` karantin skaneri, eksport va retention vazifalari) | Tasdiqlangan (`Q-010`, `T-008` Variant A, 2026-11-06) |
| Hosting va lokal infratuzilma | Docker Compose (`PostgreSQL 17`, `PgBouncer`, `Redis`, `MinIO`, `ClamAV`) + lokal `postgresql-17.11` / `PGlite` | Tasdiqlangan (`Q-010`, `T-008` Variant A, 2026-11-06) |
| To'lov integratsiyasi | Unifikatsiyalangan webhook/idempotency adapteri (`Payme` / `Click` / `Apelsin` va `DB-072 payment_attempts` + `API-073`) | Adapter arxitekturasi tasdiqlangan (`T-008`); aniq tijoriy shartnoma pilotda ulanadi |
| Mobil ilova | Belgilanmagan | Keyingi bosqich (`R4 — 13–18-oy`) |
| Mahsulot ichidagi AI model | Belgilanmagan | R1 da deterministik SQL/qoida asosidagi moslik (`API-003`); mahsulot ichida LLM ishlatilmaydi |

Versiyalar manbalarda berilmagan; taxminan yozilmaydi. Keyingi aniq tanlov foydalanuvchi qarori yoki tegishli manba IDsi bilan qayd etiladi.

## FULL-RESUME-PORTAL-DIRECTORIES-FB200 — Candidate Full Resume Builder, Direct PDF Upload, Employer & University Directories (2026-11-15)

- **Contracts**: `API-026-RESUME-DETAILS`, `API-026-DIRECT-UPLOAD`, `API-067-DIRECTORY`, `API-098-DIRECTORY`, `API-101-CREATE` (Issue #200), branch `feature/200-full-resume-and-portal-directories`, base `integration/r1-agent-collaboration`.
- **Endpoints**:
  - `GET/PUT /api/v1/me/candidate/resume-details`: Manage structured candidate resume sections (`achievements`, `work_experiences`, `languages`, `education_details`, `career_preferences`) with `completion_percent` calculation.
  - `POST /api/v1/me/candidate/files/upload`: Direct PDF upload for `CV`, `CERTIFICATE`, and `PORTFOLIO` with `pypdf` validation, EICAR/ClamAV malware rejection (`422 MALWARE_DETECTED_QUARANTINED`), MinIO storage, `flexbridge.files` registration (`CLEAN`), and automatic `cv_file_id` linking on `candidate_profiles`.
  - `GET/PUT /api/v1/organizations/{org}/directory-profile`: Complete Employer Organization Directory Profile (legal details, HR contacts, director, bank name/MFO/account, internship conditions, student perks) with `ORG_SCOPE_FORBIDDEN` (403) cross-org IDOR guard.
  - `GET/PUT /api/v1/institutions/{inst}/directory-profile`: Complete University OTM Directory Profile (official name, HEMIS registry code, rector, career center head, faculties, educational programs, annual intern quota) with `INSTITUTION_SCOPE_FORBIDDEN` (403) cross-institution IDOR guard.
  - `POST /api/v1/institutions/{inst}/academic-agreements`: Create versioned Academic Partnership Agreement (`institution_agreements` + partner organization metadata).


## UNIVERSITY-TIMETABLE-FB202 — University Class Timetable Manual Entry & Template Upload/Import (2026-11-15)

- **Contracts**: `API-098-TIMETABLE`, `API-098-TIMETABLE-TEMPLATE`, `API-098-TIMETABLE-IMPORT` (Issue #202), branch `feature/202-university-timetable-manual-and-template-import`, base `integration/r1-agent-collaboration`.
- **Endpoints**:
  - `GET/PUT /api/v1/institutions/{inst}/timetables`: Retrieve or manually save/append/delete weekly class schedule slots per academic group (`group_code`, `program_name`, `study_year`, `weekday`, `para_number`, `start_time`, `end_time`, `subject_name`, `lesson_type`, `room`, `teacher_name`).
  - `GET /api/v1/institutions/{inst}/timetables/template`: Download official ready-to-fill `.csv` and `.json` schedule templates with standard columns and para presets.
  - `POST /api/v1/institutions/{inst}/timetables/import`: Upload and validate `.csv` or `.json` class schedule templates (`REPLACE` or `APPEND`), reject intra-group time overlaps (`422 TIMETABLE_SLOT_OVERLAP`), compute free student work windows, and automatically synchronize `flexbridge.availability_rules` for enrolled students (`flexbridge.enrollments`).

## INTERNSHIP-DOCUMENTS-EIMZO-FB204 — Standardized Diary, Final Conclusion & 3-Party E-Imzo (2026-11-15)

- **Contracts**: `FB-204-EIMZO`, `FB-204-DIARY-STANDARD`, `FB-204-CONCLUSION-DOC`, `FB-204-DOC-EXPORT`, branch `feature/204-standardized-diary-conclusion-eimzo`, base `integration/r1-agent-collaboration`.
- **Endpoints**:
  - `GET/PUT /api/v1/me/e-imzo`: Per-party electronic signature certificates (`CANDIDATE`, `EMPLOYER`, `UNIVERSITY`) with strict role eligibility checks (`403 SIGNATURE_PARTY_FORBIDDEN`).
  - `GET/PUT /api/v1/placements/{placement_id}/diary/standard` & `POST .../diary/sign`: Document 1 standardized Uzbek OTM/Enterprise internship diary passport, daily entry extensions, and continuous 3-party `HMAC-SHA256` E-Imzo confirmation (`FB-SIG-D-...`).
  - `GET /api/v1/placements/{placement_id}/conclusion-document` & `POST .../conclusion-document/sign`: Document 2 separate end-of-internship conclusion sections (Employer evaluation, University academic decision/ECTS, Student reflection) converging to `TRI_PARTY_SIGNED` (`FB-SIG-C-...`).
  - `POST /api/v1/placements/{placement_id}/documents/download` & `GET .../documents/files/{file_id}/download`: Render & stream formatted multi-page A4 `pypdf` PDFs and JSON exports for both official documents, plus `GET /api/v1/internship-documents/verify/{code}`.





## ROLE-UI-FB206 — Role-Differentiated Portal Shells & Adaptive Navigation (2026-11-15)

- **Scope**: `frontend/src/components/Navbar.tsx`, `frontend/src/app/nomzod/layout.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/kirish/page.tsx`, `frontend/src/app/royxatdan-otish/page.tsx`, `frontend/src/app/employer/page.tsx`, `frontend/src/app/university/page.tsx`, `frontend/src/app/operator/page.tsx`, plus `/nomzod/*` inner page layout alignment.
- **Persona Design System**:
  - `PUBLIC`: Career Discovery Marketplace storefront with asymmetric hero, quick filter chips, 3-role portal entry matrix, and compact `Portallar` switcher.
  - `CANDIDATE` (`/nomzod/*`): Sky Blue (`sky-400`/`sky-500`) persistent left workspace sidebar (`NomzodLayout`).
  - `EMPLOYER` (`/employer`): Emerald (`emerald-400`/`emerald-500`) corporate B2B HR workspace rail.
  - `UNIVERSITY` (`/university`): Indigo (`indigo-400`/`indigo-500`) Academic Deanery workspace rail & live semester counters.
  - `OPERATOR` (`/operator`): Amber/Rose (`amber-400`/`amber-500`) SOC Audit Terminal monospace left module rail.
- **Verification**: `npx tsc --noEmit` (0 errors), Docker Next.js production build & 18-route SSR HTTP 200 check, and `scripts/run_all_staging_tests.py` (**31/31 PASS in 78.94s**).


## UNIV-ISO-FB212 — University / OTM Isolated Login, Role Boundary & Appointment Consent (2026-11-15)

- **Scope**: `backend/app/api/v1/iam.py`, `backend/app/main.py`, `frontend/src/lib/roles.ts`, `frontend/src/app/api/bff/university/appointments/route.ts`, `frontend/src/app/api/bff/university/appointments/[id]/consent/route.ts`, `frontend/src/app/university/layout.tsx`, `frontend/src/app/university/page.tsx`, `frontend/src/app/universitet/kirish/page.tsx`, `frontend/src/app/universitet/royxatdan-otish/page.tsx`, `frontend/src/components/AuthModal.tsx`, `Navbar.tsx`, `Footer.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/kirish/page.tsx`, `scripts/test_university_isolated_login_staging.py`, `scripts/run_all_staging_tests.py`.
- **Technical Architecture**:
  - Added read-only `GET /api/v1/me/contacts` (allowlisted in `self_service`) and Next.js BFF routes for institution appointment inbox (`GET /api/bff/university/appointments`) and revision-checked consent (`POST /api/bff/university/appointments/[id]/consent`) with session cookie role refresh (`TEACHER`/`COORDINATOR`).
  - Enforced `portal="ACADEMIC"` on `/universitet/kirish` and `/university` `<AuthModal>` alongside `isAcademicRoles` boundary checking in `university/layout.tsx` and Indigo-scoped `Navbar.tsx`/`Footer.tsx`.
- **Verification**: `npx tsc --noEmit` (0 errors), `npx eslint` (0 errors), Docker `backend`/`frontend` build, `scripts/test_university_isolated_login_staging.py` (4/4 phases PASS), `scripts/run_all_staging_tests.py` (**34/34 PASSED in 91.4s**). Frozen-main constraint preserved (`integration/r1-agent-collaboration`).


## OP-ISO-FB214 — Platform Operator Isolated Login & SOC Role Boundary (2026-11-15)

- **Scope**: `frontend/src/lib/roles.ts`, `frontend/src/app/operator/layout.tsx`, `frontend/src/app/operator/kirish/page.tsx`, `frontend/src/app/operator/page.tsx`, `frontend/src/components/AuthModal.tsx`, `Navbar.tsx`, `Footer.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/kirish/page.tsx`, `scripts/test_operator_isolated_login_staging.py`, `scripts/run_all_staging_tests.py`.
- **Technical Architecture**:
  - Added `isOperatorOnlyRoles(roles)` in `roles.ts` and Amber/SOC `OperatorLayout` guard rejecting non-platform roles on `/operator/*`.
  - Enforced `portal="OPERATOR"` across password & TOTP MFA steps on `/operator/kirish` and `/operator/page.tsx` `<AuthModal>`, plus SOC-scoped `Navbar.tsx` & `Footer.tsx`.
- **Verification**: `npx tsc --noEmit` (0 errors), `npx eslint` on new/shared files (0 errors), Docker `frontend` rebuild, `scripts/test_operator_isolated_login_staging.py` (4/4 phases PASS), `scripts/run_all_staging_tests.py` (**35/35 PASSED in 97.82s**). Frozen-main constraint retained.


## UNIFIED-AUTH-FB216 — Unified Main Sign-In & Sign-Up Across All 4 Roles (2026-11-15)

- **Scope**: `frontend/src/app/kirish/page.tsx`, `frontend/src/app/royxatdan-otish/page.tsx`, `scripts/test_unified_auth_all_roles_staging.py`, `scripts/run_all_staging_tests.py`.
- **Technical Architecture**:
  - Replaced literal `"EMPLOYER"`/`"ACADEMIC"` array lookups on `/kirish` and `/royxatdan-otish` with shared `resolvePortalDashboard(roles)` and `isRoleAllowedForPortal(roles, redirectPortal)` from `frontend/src/lib/roles.ts`, plus `flexbridge:auth-changed` window event propagation on password, MFA, registration, invite accept, and OTM appointment consent transitions.
  - Corrected `/royxatdan-otish` public `/api/bff/auth/register` payload to baseline `roles: ["CANDIDATE"]` and added Step 4 role activation (`EMPLOYER` invite token preview/accept with `MFA_REQUIRED` -> `/nomzod/xavfsizlik` 2FA guidance, `ACADEMIC` appointment consent, `OPERATOR` dual-control grant re-check).
- **Verification**: `npx tsc --noEmit` (0 errors), `npx eslint` on modified pages (0 errors), `python -m py_compile` (0 errors), Docker `frontend` rebuild, `scripts/test_unified_auth_all_roles_staging.py` (3/3 phases PASS), `scripts/run_all_staging_tests.py` (**36/36 PASSED in 116.69s**). Frozen-main constraint retained (`764fb98496fa40857acb07844fd09fcafa99b7d6`, integration branch `integration/r1-agent-collaboration`).



## SKEUO-UI-FB218 — Two-Mode Skeuomorphic Dashboard Architecture Across All Portals (2026-11-15)

- **Scope**: `frontend/package.json`, `frontend/tailwind.config.ts`, `frontend/src/app/globals.css`, `frontend/src/components/ThemeProvider.tsx`, `frontend/src/components/skeuo/SkeuoPrimitives.tsx`, `frontend/src/components/Navbar.tsx`, `frontend/src/components/Footer.tsx`, `frontend/src/components/AuthModal.tsx`, `frontend/src/app/layout.tsx`, all 4 portal layouts (`nomzod/layout.tsx`, `employer/layout.tsx`, `university/layout.tsx`, `operator/layout.tsx`), public/CMS/auth routes, `/nomzod/*`, `/employer`, `/university`, and `/operator`.
- **Technical Architecture**:
  - **Tokens & Theme Engine**: Defined Light Warm (`#E6E2D8` canvas, `#F4F1EA` stage, raised `.skeuo-card` bevels, recessed `.skeuo-well` wells, obsidian `#161618` chromes) and toggleable Dark Obsidian tokens with `html:not(.dark)` adaptive contrast rules and `ThemeProvider` (`useSyncExternalStore` + `flexbridge:theme`).
  - **Skeuomorphic Components & Dock Bridge**: Added `SkeuoPrimitives.tsx` (`SkeuoCard`, `SkeuoStatCard`, `SkeuoToggle`, `SkeuoVerticalMeter`, `SkeuoSegmented`, `SkeuoLiveFeed`, `SkeuoAreaChart`) powered by `framer-motion` shared-layout transitions, plus custom-event tab synchronization (`flexbridge:dock-tab` <-> `flexbridge:portal-tab-changed`) between `Navbar.tsx` docks and `/employer`, `/university`, `/operator`.
- **Verification**: `npx tsc --noEmit` (0 errors), `npx eslint` on new/core skeuo files (0 errors), Docker `frontend` build, 25/25 live SSR route HTTP 200 checks (`<html lang="uz">` Light Warm default), and `scripts/run_all_staging_tests.py` (**36/36 PASSED in 120.21s**). Frozen-main constraint retained (`764fb98496fa40857acb07844fd09fcafa99b7d6`, integration branch `integration/r1-agent-collaboration`).


## SKEUO-POLISH-PR219 — Browser Audit, Mobile Responsive & Hardware Bento Upgrade (2026-11-15)

- **Scope**: `frontend/src/app/globals.css`, `frontend/src/components/skeuo/SkeuoPrimitives.tsx`, `frontend/src/components/Navbar.tsx`, `frontend/src/components/Footer.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/kirish/page.tsx`, `frontend/src/app/royxatdan-otish/page.tsx`, `frontend/src/app/nomzod/layout.tsx`, `frontend/src/app/nomzod/page.tsx`, `frontend/src/app/employer/page.tsx`, `frontend/src/app/university/page.tsx`, `frontend/src/app/operator/page.tsx`.
- **Technical Fixes**:
  - **Self-Matching Selector & Light Warm Tokens**: Corrected `[data-skeuo-dark="true"]` exclusion in `globals.css` (`:not([data-skeuo-dark="true"]):not([data-skeuo-dark="true"] *)`), refined warm stone surfaces (`#e4dfd4` / `#f6f3ec`) and 700-grade Light Warm text contrast rules for legacy dark utility classes.
  - **Hardware Primitives (`SkeuoPrimitives.tsx`)**: Added Catmull-Rom smooth cubic spline curves (`buildSmoothSpline`) in `SkeuoAreaChart`, 3D glass cylindrical reflections & clamped floating percentage badge + `compact` variant in `SkeuoVerticalMeter`, compact proportional `SkeuoStatCard` with tonal bottom strip, and hover LED accents on `SkeuoToggle`.
  - **Responsive Grid & Bento Pods**: Fixed `390px` horizontal overflow (`min-w-0` + `flex-wrap`) in `page.tsx`, fit mobile capsule dock inside `390px` (`Navbar.tsx`), added live `Katalog balansi` toggle/cylinder Bento pod (`/`) and 5-tube `HR Reyting Indeksi` (`/nomzod`), and decoupled horizontal `SkeuoStatCard` strips from vertical meters/feeds/charts across `/nomzod`, `/employer`, `/university`, and `/operator`.
- **Verification**: `npx tsc --noEmit` (0 errors), `npx eslint` on core/public/auth files (0 errors, 0 warnings), Docker `frontend` rebuild, Playwright Edge visual + contrast verification (`1440x900` Light/Dark + `390x844` Mobile `scrollWidth=390`), `scripts/run_all_staging_tests.py` (**36/36 PASSED in 124.8s**). Frozen-main constraint retained (`integration/r1-agent-collaboration`).


## Arxiv: vazifa bo'yicha texnik qarorlar

Quyidagi bo'limlar [archive/02_texnik_qarorlar_2026-11-07_11.md](archive/02_texnik_qarorlar_2026-11-07_11.md) ga o'zgartirilmasdan ko'chirildi:

- INT-CODEX-001 / current2026-11-10
- AUTH-CODEX-006 - candidate current-session boundary2026-11-10
- STORAGE-CODEX-001 / AUTH-CODEX-005 - current2026-11-10
- EDU-CODEX-001B — reviewed appointment workflow (2026-11-09, in progress)
- EDU-CODEX-001A — current institution authority (2026-11-09)
- AUTH-CODEX-004 — human money authority (2026-11-09)
- AUTH-CODEX-003 — initial moderation authority (2026-11-09)
- AUTH-CODEX-002 — organization transaction authority (2026-11-09)
- IAM-CODEX-001 — amalda qo'llangan komponentlar (2026-11-07)
- CAN-CODEX-001 — amalda qo'llangan yondashuvlar (2026-11-07)
- ORG-CODEX-001 — amalda qo'llangan komponentlar (2026-11-07)
- ORG-CODEX-002 — invitation implementatsiyasi (2026-11-08)
- OPS-CODEX-001 — durable dry-run evaluation (2026-11-08)
- OPS-CODEX-002 — mustaqil apellyatsiya (2026-11-08)
- ORG-CODEX-003A — qo'shimcha OWNER va grant tarixi (2026-11-08)
- ORG-CODEX-003B — existing OWNER successor va departure (2026-11-09)
- ORG-CODEX-003C1 — ikki reviewer bilan fixed-revision continuity (2026-11-09)
- PLACEMENT-CODEX-API049 â€” Placement Completion Requests & Two-Sided Closure (2026-11-10)
- PLACEMENT-API052-EXPORTS — Single Placement Report Export (2026-11-10)
- PLACEMENT-API053-LOGS — Single Placement Diary Logs View (2026-11-10)
- LOG-API055-EVIDENCE — Task Entry Evidence Attachment (2026-11-10)
- RATINGS-API057-VIEW — Candidate & User Personal Ratings View (2026-11-10)
- RATINGS-API058-APPEALS — Rating Appeal Submission & Dispute Resolution (2026-11-10)
- NOTIFICATIONS-API059-PREFERENCES — User Notification Preferences (2026-11-10)
- PRIVACY-API062-REQUESTS — User Privacy Requests (2026-11-10)
- SUPPORT-API063-064-TICKETS — User Support Tickets & Messaging (2026-11-10)
- SAVED-OPPORTUNITIES-API004-037-038 — Candidate Saved Opportunities (2026-11-10)
- OPPORTUNITY-API005-NOTIFICATIONS-API031 — Opportunity Details & Notification Inbox (2026-11-11)
- Eski «Current LOG-…» qatorlari (36 ta): [archive/02_joriy_holat_tarixi.md](archive/02_joriy_holat_tarixi.md)
