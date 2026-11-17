# FlexBridge — AI xotirasi va ish qoidalari

## Joriy holat (2026-11-17, LOG-195)

> Shu bo'lim har ishdan keyin **yangilanadi** — eski «Current LOG-…» qatorlarini faylning boshiga ustma-ust qo'shish to'xtatildi. Oldingi holat qatorlari o'zgarmagan holda `archive/` papkasida.

- **Integratsiya**: `integration/r1-agent-collaboration` — `1964324` (PR #276); LOG-195 (animatsiyalar 3x tez) PR'i CI kutmoqda.
- **main**: foydalanuvchi 2026-11-17 da integration'ni main'ga o'tkazishga aniq ruxsat berdi ("hozirgi holatni main qil, hozirgi main'ni nusxalab qo'y"). Eski main `764fb98` zaxirada: branch `backup/main-2026-11-17-764fb98`, tag `main-backup-2026-11-17`, `D:/Codex/FlexBridge-backups/main-764fb98-2026-11-17.bundle`. O'tkazish `1964324` (exact-head CI yashil bo'lgach, fast-forward). Keyingi har bir main o'zgarishi uchun yana aniq ruxsat kerak.
- **Koordinator**: `D:/Codex/FlexBridge-agents/coordinator_state.json` — egasi `CODEX`, holati `HANDED_BACK` (2026-11-14).
- **So'nggi ishlar**: LOG-185 universitet ichki tablari va operator bento (#258); LOG-186 e'lonlar moderatsiyasi navbati (#260); LOG-187 staging E2E'dan topilgan xabar/yorliq tuzatishlari (#262); LOG-188 «qurilma» dizayni barcha oynalarda (#264); LOG-189 tugmalar, harakatlar va animatsiyalar qatlami (#266); LOG-190 hujjatlarni bo'limlarga ajratish (#268); LOG-191 pastki kapsulada suyuqlik oqimi effekti (#270); LOG-192 suyuqlik ortidan tomchisimon iz (#272); LOG-193 tugmalar bo'rtiq va shaffof suyuq shisha (#274); LOG-194 o'tish animatsiyasi tezlashtirildi (#276); LOG-195 barcha animatsiyalar 3 barobar tez (#277).
- **Staging**: 2026-11-17 da `1964324` dan qayta qurilgan (`flexbridge-r1`, frontend 127.0.0.1:3000, backend 127.0.0.1:8000). 4 rolli brauzer E2E 21/23 (2 tasi kutilgan biznes tekshiruvi), harakat o'lchovi 11/11, 24 skrinshot toza. Tartib: `docs/operations/STAGING_VA_E2E.md`.
- **Ochiq masalalar (foydalanuvchi qarori)**: to'lov provayderi ulanmagan — buyurtmalar `PENDING_PAYMENT` bo'lib qoladi, korxona e'lonni UI orqali nashr qila olmaydi; `infra/.env` kalitlarini almashtirish (foydalanuvchi o'zi bajaradi); staging `.env` da `BFF_SESSION_SECRET` va `TELEGRAM_BOT_TOKEN` yo'q.
- **Qayerdan boshlash**: hujjatlar xaritasi — `docs/README.md`; frontend ishi — `frontend/AGENTS.md` + `docs/frontend/README.md`; backend ishi — `backend/AGENTS.md` + `docs/backend/README.md`.


Boshlanish: 2026-11-06. Ushbu to'rtta boshqaruv fayli barcha AIlar uchun umumiy ish xotirasidir.

## O'qish tartibi va manbalar

1. Shu fayl — rollar, mas'uliyat, ish tartibi va ish tarixi.
2. `02_TEXNIK_MODELLAR.md` — hujjatlarda ko'rsatilgan texnik vositalar va model tanlovlari.
3. `03_BOSQICHLAR_VA_HOLAT.md` — bajarilgan, joriy va keyingi ishlar.
4. `04_TAKLIFLAR_VA_TANLOVLAR.md` — takliflar va foydalanuvchi qarorlari.
5. Ish turiga qarab: frontend — `frontend/AGENTS.md` va `docs/frontend/README.md`; backend — `backend/AGENTS.md` va `docs/backend/README.md`; staging/E2E — `docs/operations/STAGING_VA_E2E.md`. Hujjatlar xaritasi — `docs/README.md`.
6. Eski tarix kerak bo'lsa — `archive/` papkasidagi bo'laklar (o'zgartirilmagan asl matn). Odatiy ish uchun ularni o'qish shart emas.

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
9. Holatni fayl boshiga yangi «Current LOG-…» qatori qilib qo'shmang — «Joriy holat» bo'limini yangilang. Yangi yozuv «Ish tarixi» oxiriga qo'shiladi. Asosiy fayl ~150 KB dan oshsa, eng eski yozuvlarni o'zgartirmasdan yangi `archive/` bo'lagiga ko'chiring va havolasini qo'shing.

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

Eski yozuvlar (o'zgartirilmasdan) arxivda:

- [01_ish_tarixi_LOG-001-035.md](archive/01_ish_tarixi_LOG-001-035.md) — LOG-001…LOG-035
- [01_ish_tarixi_LOG-036-091.md](archive/01_ish_tarixi_LOG-036-091.md) — LOG-036…LOG-091
- [01_ish_tarixi_LOG-092-162.md](archive/01_ish_tarixi_LOG-092-162.md) — LOG-092…LOG-162
- [01_joriy_holat_tarixi.md](archive/01_joriy_holat_tarixi.md) — eski «Current LOG-…» qatorlari (60 ta)

### Yozuvlar LOG-156 … LOG-190 (2026-11-17 da qo'shildi)

> LOG-156…LOG-189 matni o'zgartirilmasdan olingan: LOG-156/157 — shu faylning eski «Current» qatorlaridan, qolganlari — `03_BOSQICHLAR_VA_HOLAT.md` dagi yozuvlardan. Muallif faqat aniq ma'lum bo'lsa yozilgan.

### LOG-156 — 2026-11-15

- AI / sessiya / model: muallif asl yozuvda ko'rsatilmagan
- Manba: eski «Current» holat qatori

Current LOG-156 / Student Isolated Login (/talaba/kirish), Streamlined Registration (/talaba/royxatdan-otish) & Role Boundary Isolation (Issue #208) (2026-11-15): Completely isolated Student/Candidate (`CANDIDATE`) authentication and workspace navigation from Employer, University, and Operator portals while preserving `Verified Skill Badge (1.1)` and `AI Job Match Coach (1.2)` exclusions. Added canonical role-classification module `frontend/src/lib/roles.ts` (`EMPLOYER_ROLE_CODES`, `ACADEMIC_ROLE_CODES`, `OPERATOR_ROLE_CODES`, `NON_STUDENT_ROLE_SET`, `isStudentOnlyRoles`, `isRoleAllowedForPortal`, `resolvePortalDashboard`) aligned with `backend/app/services/auth.py` (`roles_for`) and `flexbridge.role_catalog` so elevated ORG/INSTITUTION/PLATFORM grants never bypass `CANDIDATE` portal checks even though every account holds `CANDIDATE` by default. Enforced server-side `portal` validation (`HTTP 403 ROLE_PORTAL_MISMATCH`, 0 session cookies set on mismatch) inside `frontend/src/lib/server/session.ts` (`completeAuthenticatedSession`), `/api/auth/login`, and `/api/auth/mfa/verify`. Created dedicated Sky-blue Student login (`/talaba/kirish`) and 2-step SMS/Telegram Student-only registration (`/talaba/royxatdan-otish`), wired `requiredPortal="CANDIDATE"` across `/nomzod/*` `AuthModal` call sites, enforced a Role Boundary screen inside `frontend/src/app/nomzod/layout.tsx`, and hid cross-role portal switchers in `Navbar.tsx` and `Footer.tsx` during Student routes or pure `CANDIDATE` sessions while keeping guest SSR compatibility on `/` and `/kirish`. Executed `npx tsc --noEmit` (0 errors), Docker `frontend` rebuild, `scripts/test_student_isolated_login_staging.py` (5/5 phases GREEN), and full 32-suite regression runner `scripts/run_all_staging_tests.py` (32/32 suites PASSED in 80.09s). Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. Zero mutations to pg_live.

### LOG-157 — 2026-11-15

- AI / sessiya / model: muallif asl yozuvda ko'rsatilmagan
- Manba: eski «Current» holat qatori

Current LOG-157 / Employer Isolated Login (/korxona/kirish), Invitation Onboarding (/korxona/royxatdan-otish) & Role Boundary Isolation (Issue #210) (2026-11-15): Completely isolated Employer/Company (`EMPLOYER`) authentication, team invitation onboarding, and `/employer` workspace navigation from Student, University, and Operator roles while preserving `Verified Skill Badge (1.1)` and `AI Job Match Coach (1.2)` exclusions. Extended `frontend/src/lib/roles.ts` with `EMPLOYER_ROLE_SET`, `ACADEMIC_ROLE_SET`, `OPERATOR_ROLE_SET`, `isEmployerRoles`, and `isEmployerOnlyRoles`. Created Next.js 16 BFF invitation preview/accept routes (`GET /api/bff/invitations/[token]` -> `API-024`, `POST /api/bff/invitations/[token]/accept` -> `API-025` with CSRF + session cookie role refresh). Built dedicated Emerald Employer login (`/korxona/kirish` enforcing `portal="EMPLOYER"` across password and TOTP MFA verification) and 3-step Employer representative SMS/Telegram signup + invitation onboarding (`/korxona/royxatdan-otish?token=`). Enforced `/employer` workspace Role Boundary guard in `frontend/src/app/employer/layout.tsx`, wired `requiredPortal="EMPLOYER"` + `"flexbridge:auth-changed"` sync in `/employer/page.tsx` and `AuthModal.tsx`, isolated Employer navigation scope in `Navbar.tsx` and `Footer.tsx`, and added direct `/korxona/kirish` entry links on `/` and `/kirish` without breaking guest SSR. Executed `npx tsc --noEmit` (0 errors), Docker `frontend` rebuild, `scripts/test_employer_isolated_login_staging.py` (4/4 phases GREEN), and full 33-suite regression runner `scripts/run_all_staging_tests.py` (33/33 suites PASSED in 82.97s). Main/master strictly FROZEN at 764fb98496fa40857acb07844fd09fcafa99b7d6. Zero mutations to pg_live.

### LOG-158 — 2026-11-15 — Issue #212 (`feature/212-university-isolated-login`) -> Universitet / OTM (`ACADEMIC`) alohida kirish, rol chegarasi va tayinlov roziligi

- AI / sessiya / model: muallif asl yozuvda ko'rsatilmagan
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **YETKAZILDI VA TEKSHIRILDI (ALL 34/34 STAGING TEST SUITES GREEN)**.
- **Nima Qilindi**:
  * **OTM Alohida Kirish & Ulanish (`/universitet/kirish`, `/universitet/royxatdan-otish`)**: Faqat `ACADEMIC` portaliga ruxsat beruvchi parol + 2FA TOTP kirish hamda SMS/Telegram orqali hisob ochib tayinlov roziligini (`ACCEPT`/`DECLINE`) rasmiylashtiruvchi 3 bosqichli oqim yaratildi (`GET /api/v1/me/contacts` va `/api/bff/university/appointments*`).
  * **Rol Chegarasi & Scoped UI**: `university/layout.tsx`, `university/page.tsx`, `AuthModal.tsx`, `Navbar.tsx`, `Footer.tsx`, `/` va `/kirish` sahifalarida Universitet / OTM menyu va kirish nuqtalari izolyatsiya qilindi (boshqa rollar 403 / Role Boundary bilan bloklandi; `main` muzlatilgan holda saqlandi).
  * **Tekshiruv**: `npx tsc --noEmit` (0 xato), `npx eslint` (0 xato), Docker `backend`/`frontend` build, `test_university_isolated_login_staging.py` (4/4 bosqich YASHIL) va `scripts/run_all_staging_tests.py` (**34/34 to'plam 100% YASHIL, 91.4s**).

### LOG-159 — 2026-11-15 — Issue #214 (`feature/214-operator-isolated-login`) -> Platforma Operatori (`OPERATOR` / SOC) alohida kirish va rol chegarasi

- AI / sessiya / model: muallif asl yozuvda ko'rsatilmagan
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **YETKAZILDI VA TEKSHIRILDI (ALL 35/35 STAGING TEST SUITES GREEN)**.
- **Nima Qilindi**:
  * **SOC Alohida Kirish (`/operator/kirish`)**: Faqat `OPERATOR`, `MODERATOR`, `AUDITOR`, `SUPPORT`, `FINANCE`, `ADMIN`, `SECURITY_LEAD` rollari uchun `portal="OPERATOR"` parol + 2FA TOTP terminal kirishi yaratildi (ochiq o'z-o'zidan ro'yxatdan o'tishsiz, Dual-Control talabi bilan).
  * **Rol Chegarasi & Scoped UI**: `operator/layout.tsx`, `operator/page.tsx` (`requiredPortal="OPERATOR"` + auth sync), `AuthModal.tsx`, `Navbar.tsx`, `Footer.tsx`, `/kirish` va `/` da Operator / SOC chegarasi ajratildi (`main` muzlatilgan holda saqlandi).
  * **Tekshiruv**: `npx tsc --noEmit` (0 xato), `npx eslint` yangi/umumiy fayllarda (0 xato), Docker `frontend` build, `test_operator_isolated_login_staging.py` (4/4 bosqich YASHIL) va `scripts/run_all_staging_tests.py` (**35/35 to'plam 100% YASHIL, 97.82s**).

### LOG-160 — 2026-11-15 — Issue #216 (`feature/216-unified-auth-role-routing`) -> Barcha 4 rol uchun birlashtirilgan bosh `/kirish` va `/royxatdan-otish`

- AI / sessiya / model: muallif asl yozuvda ko'rsatilmagan
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **YETKAZILDI VA TEKSHIRILDI (ALL 36/36 STAGING TEST SUITES GREEN)**.
- **Nima Qilindi**:
  * **Yagona `/kirish` va Rolga Qarab Avto-Yo‘naltirish**: `frontend/src/app/kirish/page.tsx` barcha 4 foydalanuvchi turini (`CANDIDATE` -> `/nomzod`, `OWNER`/`HR`/`HOST_COORDINATOR`/`MENTOR`/`BILLING` -> `/employer`, `COORDINATOR`/`TEACHER` -> `/university`, `OPERATOR`/`MODERATOR`/`AUDITOR`/`FINANCE`/`SUPPORT`/`SECURITY_LEAD`/`ADMIN` -> `/operator`) `resolvePortalDashboard` orqali o‘z kabinetiga yo‘naltiradigan qilib yangilandi (`redirect` parametri esa `isRoleAllowedForPortal` bilan tekshirildi).
  * **Yagona 4-Bosqichli `/royxatdan-otish`**: `frontend/src/app/royxatdan-otish/page.tsx` da baza `roles: ["CANDIDATE"]` ro‘yxatdan o‘tish tuzatildi hamda 4-bosqich rol faollashtirish UI qo‘shildi (`EMPLOYER` taklif tokeni + `MFA_REQUIRED` uchun `/nomzod/xavfsizlik` yo‘riqnomasi, `ACADEMIC` OTM tayinlovi roziligi, `OPERATOR` 2FA/dual-control tekshiruvi). `main`/`master` muzlatilgan holda saqlandi (`integration/r1-agent-collaboration`).
  * **Tekshiruv**: `npx tsc --noEmit` (0 xato), `npx eslint` (0 xato), `py_compile` (0 xato), Docker `frontend` build, `scripts/test_unified_auth_all_roles_staging.py` (3/3 bosqich YASHIL) va `scripts/run_all_staging_tests.py` (**36/36 to‘plam 100% YASHIL, 116.69s**).

### LOG-161 — 2026-11-15 — Issue #218 (`feature/218-skeuomorphic-dashboard-design`) -> Barcha portallar uchun ikki rejimli Skeuomorfik Dizayn Tizimi

- AI / sessiya / model: muallif asl yozuvda ko'rsatilmagan
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **YETKAZILDI VA TEKSHIRILDI (ALL 36/36 STAGING TEST SUITES GREEN)**.
- **Nima Qilindi**:
  * **Ikki Rejimli Rang va Qavariq Dizayn (`ThemeProvider.tsx`, `globals.css`, `SkeuoPrimitives.tsx`)**: `Light Warm` (`#E6E2D8`/`#F4F1EA` iliq tosh foni va qavariq `.skeuo-card`/`.skeuo-well` kartalar) standart qilindi hamda sarlavhadagi Quyosh/Oy tugmasi orqali `Dark Obsidian` rejimiga o‘tkazish imkoniyati (`flexbridge:theme`) yaratildi. `framer-motion` bilan `SkeuoStatCard`, `SkeuoToggle`, `SkeuoVerticalMeter`, `SkeuoSegmented`, `SkeuoLiveFeed` va `SkeuoAreaChart` komponentlari qurildi.
  * **3 ta Suzuvchi Obsidian Chrome (`Navbar.tsx`, `Footer.tsx`, `AuthModal.tsx`, `layout.tsx`)**: Dynamic Island jonli statusli yuqori pill bar, chap vertikal tezkor asboblar doki (`flexbridge:dock-tab`) va `layoutId` animatsiyali pastki suzuvchi kapsula dok (+ yuqoriga sakrash tugmasi) barcha rol izolyatsiyalarini buzmasdan birlashtirildi.
  * **To‘liq Qamrov (25 ta Sahifa)**: Ommaviy katalog (`/`), CMS/Auth (`/ishlar/[id]`, `/kirish`, `/royxatdan-otish`, `/talaba/*`, `/korxona/*`, `/universitet/*`, `/operator/kirish`) hamda barcha 4 kabinet (`/nomzod/*`, `/employer`, `/university`, `/operator`) skeuomorfik elementlar bilan boyitildi (`1.1` va `1.2` qo‘shilmadi; `main` muzlatilgan holda saqlandi).
  * **Tekshiruv**: `npx tsc --noEmit` (0 xato), `npx eslint` yangi komponentlarda (0 xato), Docker `frontend` rebuild, 25/25 sahifa SSR HTTP 200 (`Light Warm`), va `scripts/run_all_staging_tests.py` (**36/36 to‘plam 100% YASHIL, 120.21s**).

### LOG-162 — 2026-11-15 — PR `#219` (`feature/218-skeuomorphic-dashboard-design`) -> Brauzer Auditi va Skeuomorfik UI Mukammallashtirish

- AI / sessiya / model: muallif asl yozuvda ko'rsatilmagan
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **YETKAZILDI VA TEKSHIRILDI (PLAYWRIGHT VIZUAL AUDIT + 36/36 STAGING TESTLAR YASHIL)**.
- **Nima Qilindi**:
  * **Real Brauzer Auditi va Light/Dark Kontrast (`globals.css`, `SkeuoPrimitives.tsx`, `Navbar.tsx`, `Footer.tsx`)**: Playwright Edge skrinshotlari va DOM kontrast tahlili asosida `[data-skeuo-dark="true"]` o‘z-o‘zini moslash nuqsoni, Light Warm matn/fon kontrastlari va mobil (`390x844`) pastki dok sig‘imi tuzatildi; `SkeuoVerticalMeter` (3D glass shisha silindr + `compact` rejim), `SkeuoStatCard` va `SkeuoAreaChart` (silliq Catmull-Rom Bezier egri chizig‘i) namuna darajasidan oshirildi.
  * **Ommaviy Katalog (`/`) & Yagona Kirish/Ro‘yxatdan O‘tish (`/kirish`, `/royxatdan-otish`)**: Yaxlit `.skeuo-well` qidiruv paneli, 2 ustunli Bento vakansiya setkasi, real server ma’lumotlariga ulangan **Katalog balansi** (`SkeuoToggle` + 4 ta shisha kolba), mobil `scrollWidth=390` tuzatishi, hamda `Obsidian / Terracotta` brend belgili va AI-slop gradientlardan xoli auth sahifalari joriy etildi.
  * **4 ta Kabinetda Bento Proporsiyalari (`/nomzod`, `/employer`, `/university`, `/operator`)**: Cho‘zilgan KPI kartalar alohida ixcham qatorga ajratildi, `/nomzod`da 5 kolbali **HR Reyting Indeksi** Bento bloki qo‘shildi va ortiqcha dublikat tugmalar tozalandi (`1.1`/`1.2` qo‘shilmadi; `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` muzlatilgan holda PR `#219` -> `integration/r1-agent-collaboration`).
  * **Tekshiruv**: `npx tsc --noEmit` (0 xato), 9 ta asosiy faylda `npx eslint` (0 xato, 0 ogohlantirish), Docker `frontend` rebuild, Playwright Edge vizual/kontrast auditi (`0` mobil toshish, `0` taqiqlangan matn), `scripts/run_all_staging_tests.py` (**36/36 to‘plam 100% YASHIL, 124.8s**).

### LOG-163 — 2026-11-16 — Issue #220 (`fix/220-integration-ci-green`) -> Integration CI'ni yashil holatga qaytarish

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **LOKAL TEKSHIRILDI; BACKEND GitHub CI KUTILMOQDA** (Claude Code).
- **Sabab**: `integration/r1-agent-collaboration` CI qizil edi: Frontend lint 94 xato (2026-11-14 dan, oxirgi yashil `2de979a`), backend 11 test (2026-11-15 dan, oxirgi yashil `178e31d`). Shu davrda ~20 PR merge qilingan; jurnaldagi "N/N YASHIL" faqat lokal staging skriptlariga tegishli edi.
- **Nima Qilindi**:
  * **Backend**: 7 ta test faylida kutilgan Alembic head `0020_placement_exports` -> `0021_candidate_portal_extension` va jadvallar soni 130 -> 133 (0021: `candidate_portfolios`, `candidate_certificates`, `candidate_resume_exports`).
  * **Frontend**: 64 ta JSX `'` -> `&apos;` (ko'rinish bir xil); 11 ta `any` turlangan; `employer`/`university` sahifalarida useState'lar ularni ishlatuvchi `useCallback`'dan oldinga ko'chirildi; `/haqida`, `/maxfiylik`, `/shartlar` tab yuklanish holati handler'ga ko'chirildi; `/nomzod/kundalik` forma sinxronizatsiyasi effect'dan render-vaqtidagi moslashga o'tkazildi; `window.location.assign`; umumiy loader chaqiruvchi 11 ta fetch-on-mount effektga izohli `eslint-disable-next-line` (keyingi qadam: data hook).
  * **Tekshiruv**: `npx eslint .` (0 xato, 50 ogohlantirish), `npx tsc --noEmit` (0), `npm run build` (OK), `npm audit --audit-level=high` (OK). Backend lokal DB/Docker ishlatilmadi — GitHub CI exact-head natijasi qabul sharti.
  * **Qoida**: integration merge faqat aniq head'dagi yashil GitHub CI bilan; staging skriptlari uning o'rnini bosmaydi. `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-164 — 2026-11-16 — Issue #222 (`feature/222-frontend-quality-tests`) -> Frontend sifati, birinchi test to'plami va BFF sessiya kaliti xavfsizligi

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **LOKAL TEKSHIRILDI; GitHub CI KUTILMOQDA** (Claude Code; PR #221 ustiga qurilgan).
- **Nima Qilindi**:
  * **Lint 0/0**: 50 ta ogohlantirish tuzatildi va `--max-warnings=0` bilan qotirildi; `src` da birorta `eslint-disable` qolmadi. Ogohlantirishlar ortidagi haqiqiy nuqsonlar: ko'rsatilmayotgan yuklash xatolari (`yordam`, `operator`), API'ga yuboriladigan, lekin kiritish maydoni yo'q qiymatlar (`nomzod`: ish joyi joylashuvi, til bali; `university`: fakultet talabalar soni, ta'lim darajasi, shartnoma muddati), effect bog'liqliklari (`useEffectEvent`), Google Fonts `<link>` -> self-hosted `next/font`.
  * **`useAsyncData` hook va `describeRequestError`**: kalitga asoslangan yuklash, render paytida holatni tiklash, eskirgan javoblardan himoya, `reload`/`mutate`. 7 ta sahifa va `InternshipDocumentsHub` o'tkazildi.
  * **Birinchi frontend testlari**: Vitest 4.1.12 + Testing Library + jsdom, 45 test (rollar, sessiya shifrlash/CSRF, hook, xatolar), CI'da `npm test`. npm 10.9 vitest 4 + vite 8 ni hal qila olmagani uchun vite 7.3.7 ga qotirildi; lockfile npm 11 da yaratilib, npm 10 `npm ci` bilan tekshirildi.
  * **Xavfsizlik**: `BFF_SESSION_SECRET` yo'q bo'lsa BFF repoda ochiq turgan zaxira kalitdan foydalanardi (staging: `NODE_ENV=production`, sir yo'q) — istalgan rol bilan cookie qalbakilashtirish mumkin edi. Endi production'da tasodifiy jarayon kaliti (qayta ishga tushganda sessiyalar tugaydi); berilgan sir >= 32 belgi; compose `infra/.env` dagi qiymatni uzatadi. **Operator harakati (bajarilmagan)**: barqaror staging sessiyalari uchun `infra/.env` ga >= 32 belgili `BFF_SESSION_SECRET` qo'shish.
  * **Tekshiruv**: eslint 0/0, `tsc` 0, `next build` OK, vitest 45/45, `npm audit --audit-level=high` OK, lokal `next start` 22/22 sahifa HTTP 200, headless Edge 14 sahifa (pageerror/cheksiz render yo'q). Docker qayta build va staging to'plamlari ishga tushirilmadi; pilot qabul emas. `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-165 — 2026-11-16 — PR #224 -> Skeuomorfik dizayn (#219) va saqlangan WIP integratsiyasi

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGE QILINDI (973077e), CI YASHIL**. D:/FlexBridge dagi 29 ta commit qilinmagan fayl patch sifatida saqlandi (asl papka o'zgartirilmadi). Dizayn shriftlari next/font orqali.

### LOG-166 — 2026-11-16 — PR #225 -> Xodim kabinetlari, sokin UI, bitta navigatsiya

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGE QILINDI (df7a4ae), CI YASHIL**. Brauzer auditi (Edge, 4 rol, desktop+mobil) asosida: `GET /me/workspaces`, API-076 vakansiyalar ro'yxati; korxona/OTM UUID kiritish o'rniga tanlagich; operator moduli rolga qarab; liquid kolba/sheen/bounce olib tashlandi; chap dok va takroriy tab qatorlari olib tashlandi; matnlar soddalashtirildi.

### LOG-167 — 2026-11-16 — PR #226 -> Haqiqiy Telegram bot

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGE QILINDI (fbeb751), CI YASHIL**. Xavfsizlik: webhook OTP ni qaytarardi va sayt botni brauzerda soxtalashtirardi. Endi LIVE/SIMULATION/DISABLED rejimlar, secret header, polling worker, `docs/backend/security_iam/TELEGRAM_BOT.md`. **Operator harakati**: `TELEGRAM_BOT_TOKEN` ni `infra/.env` ga qo'shish.

### LOG-168 — 2026-11-16 — PR #227 -> Talabalikni OTM koordinatori tasdiqlashi (HEMIS ulanguncha)

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **CI KUTILMOQDA**. Migratsiya `0022_enrollment_inst_review` (birinchi nom 34 belgi bo'lib alembic varchar(32) ga sig'madi, tuzatildi). Har qaror bitta vakolat dalili bilan (MODERATOR yoki o'sha OTMning amaldagi COORDINATOR'i); 0013 invariantlari saqlangan. OTM paneli; talaba PDF ma'lumotnoma biriktiradi (avval `file_ids: []` yuborilardi va ariza hech kimga yetmasdi).

### LOG-169 — 2026-11-16 — PR #228 -> Rezyume ishlaydi, qidiruv roziligi, korxona rezyume ko'rinishi

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **CI KUTILMOQDA**. UI/backend maydon nomlari mos emasligi sababli rezyume saqlanmasdi (422) va qiymatlar buzilardi -> `lib/resumeContract.ts`. Profillar doim PRIVATE edi va o'zgartirib bo'lmasdi -> `PUT /me/candidate/visibility` (audit). Korxona endi rezyume bo'limlari va "talabaligi tasdiqlangan" belgisini ko'radi (kontaktlarsiz). Ko'nikma `verified` faqat APPROVED case uchun.
- **Ochiq masala**: nomzod PDF yuklashda antivirus xatosi e'tiborsiz qoldiriladi va bo'sh PDF yaratilishi mumkin - alohida tuzatish kerak.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-170 — 2026-11-16 — PR #229 -> Nomzod PDF yuklash fail-closed

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **CI KUTILMOQDA**. LOG-169 dagi ochiq masala yopildi: servis mavjud bo'lmagan `antivirus.scan_bytes` ni chaqirib xatoni yutardi (hech bir fayl skanerlanmagan); saqlash xatosi yutilardi (obyekt yo'q, lekin CLEAN yozuv); kontentsiz so'rov bo'sh PDF yaratardi ("Elektron PDF tasdiqnoma yaratish" tugmasi).
- **Endi**: `content_base64` majburiy; `antivirus.scan` fail-closed (503 `ANTIVIRUS_UNAVAILABLE`, 422 `MALWARE_DETECTED_QUARANTINED`); saqlash xatosi 503 `FILE_STORAGE_UNAVAILABLE`, yozuv yaratilmaydi; skan DB tranzaksiyasidan tashqarida. Testlar: `backend/tests/security/test_candidate_pdf_upload.py` (6 ta).
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-171 — 2026-11-16 — Issue #231 -> "Liquid Glass" dizayn qatlami

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **CI KUTILMOQDA**. Foydalanuvchi so'rovi: dizayn tushunarliroq, tozaroq va liquid effektli bo'lsin.
- **O'zgarishlar**: `globals.css` qayta yozildi - sovuq neytral fon + sekin suzuvchi 4 rangli dog' (48s, reduced-motion'da o'chadi), xira-shisha kartalar (blur 22px), yaltiroq "suyuq" tugmalar (sakrash/sweep yo'q), popover/modal uchun deyarli shaffof bo'lmagan shisha, yengil modal parda, `prefers-reduced-transparency` va backdrop-filter yo'q brauzerlar uchun zaxira. Primitivlar: oddiy yozuvli statistik sarlavhalar, accent toggle, yumshoq segment. 4 portal sarlavhalari oddiy tilda; korxona moslik filtri UUID o'rniga vakansiya tanlagich.
- **Tekshiruv**: lokal `next start` (3100) + Edge Playwright: 58 sahifa (desktop+mobil), light/dark, modal - gorizontal toshish yo'q, yangi xato yo'q (faqat kutilgan 401 mehmon va eski staging backend 404 `/me/workspaces`). Lint 0, vitest 56/56, build OK.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-172 — 2026-11-16 — Issue #231 (PR #232) -> Kirish sahifalari qayta ishlandi

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **CI KUTILMOQDA**. Foydalanuvchi: "login qilish qisimlarini yahshila".
- **Topilgan muammolar**: 5 ta kirish sahifasi har xil ko'rinishda va bir-birini takrorlagan; korxona kirishida chap panel o'qib bo'lmas darajada qorong'i; rangli tugmalarda qora matn; mehmonga "Salom, FlexBridge"; texnik jargon (CANDIDATE, 403, HttpOnly); xatolar xom kod sifatida ("LOGIN_FAILED") - BFF backend `detail.code` ni yo'qotar edi.
- **Yechim**: yagona `components/auth/LoginPanel.tsx` (+`LoginScreen`): portalga xos rang/matn konfiguratsiyasi, `autocomplete` (username/current-password/one-time-code), Caps Lock ogohlantirishi, parolni ko'rsatish tugmasi (aria), 6 raqamda avtomatik tekshiriladigan 2FA kodi, boshqa rol sessiyasi uchun tushuntirish + chiqish, xavfsiz `?redirect=`/`?next=` (faqat portal ichida, `//` rad), boshqa portallarga havolalar, "Parolni unutdingizmi?" bo'yicha halol yo'riqnoma. `lib/errors.ts describeLoginError`; BFF login/MFA marshrutlari endi backend kodini (va 429 -> RATE_LIMITED) uzatadi. AuthModal ham shu xabarlar va autocomplete bilan. Navbar mehmonga faqat brendni ko'rsatadi.
- **Tekshiruv**: vitest 62/62 (LoginPanel 5 ta yangi test), lint 0, build OK; Edge Playwright: 5 sahifa desktop+mobil, dark, haqiqiy backend xatosi (INVALID_CREDENTIALS -> o'zbekcha xabar), 2FA bosqichi, noto'g'ri rol holati - toshish yo'q, page error yo'q.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-173 — 2026-11-16 — Issue #233 -> Parolni tiklash sahifasi

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **CI KUTILMOQDA**. Foydalanuvchi: parolni tiklash funksiyasini qo'shish ("ha bajar").
- **Topilma**: backendda xavfsiz recovery oqimi (IAM.md) allaqachon bor edi - OTP + mustaqil omil (TOTP/zaxira kod); omilsiz -> PENDING_REVIEW (hisob bor-yo'qligi oshkor qilinmaydi). Frontend/BFF yo'q edi. Xavfsizlik qarori o'zgartirilmadi (faqat OTP bilan parol tiklanmaydi).
- **Qilindi**: `/parolni-tiklash` (`components/auth/PasswordRecovery.tsx`): 4 bosqich + progress, SMS/Telegram (TelegramVerification qayta ishlatildi)/email, 6 xonali kod avtomatik tekshiruvi, qayta yuborish taymeri, TOTP yoki zaxira kod, yangi parol (>=12, harf+raqam, takrorlash), PENDING_REVIEW uchun so'rov raqami va holatni yangilash. BFF `api/bff/auth/recovery*` (tokenlar faqat body/X-Recovery-Token). `lib/recovery.ts`, yangi o'zbekcha xato xabarlari. LoginPanel va AuthModal'dagi "Parolni unutdingizmi?" shu sahifaga.
- **Tekshiruv**: vitest 66/66 (PasswordRecovery 3 + normalizatsiya), lint 0, build OK; Edge Playwright: haqiqiy staging backend kod so'rovini qabul qildi, mock bilan to'liq oqim (kod -> TOTP -> yangi parol -> tayyor) va PENDING_REVIEW (mobil, dark) - toshish/xato yo'q.
- **Ochiq**: PENDING_REVIEW so'rovlarini ko'rib chiqadigan operator navbati yo'q - OPS/siyosat qarori kerak.

### LOG-174 — 2026-11-16 — Issue #235 -> Universitetning maxsus akkaunti va xodimlari

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **CI KUTILMOQDA**. Foydalanuvchi: "universitet uchun maxsus akkaunt bo'ladi, u o'z xodimlarini kiritishi mumkin".
- **Topilma**: backend modeli bor edi (FIRST_COORDINATOR = universitet akkaunti, STAFF_TEACHER = xodim; moderator tekshiruvi + nomlangan xodim roziligi, MFA). Frontendda ulash arizasi ham, xodim qo'shish ham yo'q edi; staff uchun PDF yuklash yo'li ham yo'q edi.
- **Backend**: `services/pdf_intake.py` (fail-closed PDF qabul - talaba yuklashi ham shunga o'tkazildi), `POST /api/v1/files/pdf` (har qanday hisob, faqat INSTITUTION_APPOINTMENT/INSTITUTION_AGREEMENT/ORGANIZATION_EVIDENCE, rate-limit), `GET /api/v1/institutions/{inst}/staff-appointments` (faqat COORDINATOR: barcha tayinlovlar holati + amaldagi shartnoma + registry_code). Test: `tests/security/test_university_staff.py` (4).
- **Frontend**: `/university` -> "Xodimlar" (koordinator): ro'yxat, xodim qo'shish (telefon/pochta + buyruq PDF + sanalar + huquqiy asos), bekor qilish (sabab bilan). `/universitet/royxatdan-otish` 3-bosqich: "Universitetni ulash" arizasi (nom, hudud, STIR, buyruq PDF, shartnoma PDF; 2FA/kontakt oldindan tekshiriladi). BFF: `files/pdf`, `university/institutions/[inst]/staff`, `university/appointments` POST, `appointments/[id]/revoke` (`lib/server/proxy.ts`). O'zbekcha xato xabarlari (`lib/universityStaff.ts`).
- **Tekshiruv**: vitest 67/67 (+5), lint 0, build OK; Edge Playwright (mock): xodimlar paneli desktop/mobil-dark, ulash formasi; 56 sahifa regressiya - toshish yo'q.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-175 — 2026-11-16 — Issue #237 -> Talaba parolini universitet koordinatori tasdiqlashi

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **CI KUTILMOQDA**. Foydalanuvchi qarori: ikkinchi omili yo'q talabalar uchun universitet koordinatori tasdig'i ("navbatma navbat bajar").
- **Backend**: `identity.request_recovery` - shu kontaktdan 72 soat ichidagi APPROVED so'rov mustaqil omil (bir martalik, CONSUMED, audit). `services/institution_recovery.py`: navbat (joriy VERIFIED talabalar, niqoblangan kontaktlar) va qaror (MFA koordinator, o'zi emas, sabab). Marshrutlar `/api/v1/institutions/{inst}/recovery-requests[/{id}/decide]`. Test: `test_institution_recovery.py` (4: to'liq oqim, boshqa OTM/o'qituvchi/talaba rad, kontaktga bog'liqlik + 72 soat, sabab).
- **Frontend**: `/university` -> "Talabalikni tasdiqlash" ichida "Parolni tiklash so'rovlari" paneli; `/parolni-tiklash` matnlari (koordinatorga murojaat, "Tasdiqlandi" holati). BFF `university/institutions/[inst]/recovery-requests*`.
- **Tekshiruv**: vitest 75/75, lint 0, build OK; Edge Playwright (mock) desktop/mobil - toshish yo'q. IAM.md yangilandi.
- PR #234 (df5b942) va #236 (1363c75) integration'ga merge qilindi.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-176 — 2026-11-16 — Issue #239 -> Korxonaning markaziy (OWNER) akkaunti va jamoasi

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **CI KUTILMOQDA**. Foydalanuvchi: "korxona markaziy akkaunti ham qilinsin".
- **Topilma**: backend modeli bor (POST /organizations: asoschi moderator tekshiruvidan keyin OWNER, mavjud korxonaga qo'shilish = PENDING_APPROVAL; takliflar; a'zolikni bekor qilish). Kamchiliklar: korxonani ro'yxatdan o'tkazish UI yo'q edi; taklif tokeni hech kimga yetkazilmasdi (UI "yuborildi" derdi); a'zolar "Foydalanuvchi #id" bo'lib rolsiz ko'rinardi; qo'shilish so'rovlarini tasdiqlash UI yo'q edi.
- **Backend**: `GET /api/v1/organizations/{org}/team` (faqat MFA OWNER): a'zolar ism + faol rollar, qo'shilish so'rovlari (so'ralgan rol), ochiq takliflar. Test `test_org_team.py` (3).
- **Frontend**: `/employer` -> "Tashkilot & Jamoa": yangi `OrganizationTeamPanel` (ismlar, o'zbekcha rollar, taklif -> 24 soatlik ulashiladigan havola + nusxalash, so'rovni tasdiqlash/rad etish, xodimni sabab bilan chiqarish, taklifni bekor qilish); eski ro'yxat/forma/modal olib tashlandi. `/korxona/royxatdan-otish` 3-bosqich: "Korxonani ro'yxatdan o'tkazish" (`OrganizationConnectForm`: STIR, nomlar, hudud, sayt, PDF vakolat hujjati - `files/pdf` ORGANIZATION_EVIDENCE, 2FA oldindan tekshiriladi); `?ulash=1` va `?token=` havolalari. BFF: `employer/organization/[org]/team`, `members/[id]/approve`, `invitations/[id]/revoke`, `employer/organizations`.
- **Tekshiruv**: vitest 79/79, lint 0, build OK; Edge Playwright (mock) jamoa desktop/mobil-dark va ulash formasi - toshish yo'q.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-177 — 2026-11-16 — Issue #241 -> Rezyume to'ldirish qadam-baqadam (yirik saytlar namunasida)

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#242, 0e9a179). Foydalanuvchi: "katta saytlardan rezyume formasini ko'rib chiq, bizniki tushunarsiz".
- **Muammo**: rezyume 7 tabga tarqalgan; "To'liq rezyume"da 25 maydon birdan ochiq, ko'pi yorliqsiz (faqat kesilgan placeholder), sanalar nomsiz, ro'yxatga qo'shgach alohida "Barcha bo'limlarni saqlash" kerak edi (aks holda yo'qolardi), "HR reyting indeksi (1/7 band)" kabi jargon; BFF xato kodini "[object Object]" qilib yuborardi.
- **Namuna**: Handshake (About/Experience/Education/Skills, ta'lim talabalar uchun birinchi), hh/Jooble kabi qadamli builder'lar, multi-step forma amaliyotlari (jarayon ko'rsatkichi, har qadam saqlash, qadam bo'yicha validatsiya).
- **Yechim**: `components/resume/ResumeBuilder.tsx` + `resumeDraft.ts`: 6 qadam (Asosiy, Ta'lim, Tajriba, Tillar, Yutuqlar, Ko'rib chiqish), har maydonda yorliq + namuna + xato, tajriba/yutuqlar kartochka orqali (oy tanlagich, "Hozir ham shu yerda"), lavozim/texnologiya chiplari, har qadamda avtomatik saqlash ("Saqlandi 12:47"), tayyorlik 0/5, tajriba oylari avtomatik hisoblanadi, ko'rib chiqishda ish beruvchi ko'rinishi + PDF CV + qidiruvga ochish. Nomzod sahifasida "Kasbiy profil" va "To'liq rezyume" bitta "Rezyume" tabiga birlashtirildi, "HR reyting indeksi" bloki va ~70 eski state/handler olib tashlandi. BFF resume-details backend kodini to'g'ri uzatadi.
- **Tekshiruv**: vitest 85/85 (+6), lint 0, build OK; Edge Playwright haqiqiy staging backend bilan to'liq oqim (PUT 200, profil sarlavhasi va experience_months=15 saqlandi), desktop + mobil-dark, 56 sahifa regressiya - toshish yo'q. Eslatma: lokal staging backend eski kodda, desired_roles/ta'lim maydonlarini saqlamaydi (integration backend #228 dan beri saqlaydi).
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-178 — 2026-11-16 — Issue #243 -> Sahifalar ko'rigi: topilgan xatolarni tuzatish

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#244, c969d76). Foydalanuvchi: "o'zing ko'rib chiq va xatolarni topib to'g'irla" (49 sahifa x 2 ko'rinish galereyasi asosida).
- **Topildi va tuzatildi**:
  - Xato matnlari: 50 BFF marshruti backend `detail` obyektini `error` sifatida uzatadi, sahifalar "[object Object]" yoki "INSTITUTIONS_NOT_FOUND" kabi kodni ko'rsatardi. Yangi `lib/errorText.ts` (ma'lum kodlar o'zbekcha, noma'lum kodlar umumiy jumla), `api.ts` dagi 136 joy va 3 ro'yxatdan o'tish sahifasi unga o'tkazildi.
  - Enum yorliqlari: yangi `lib/labels.ts` (`enumLabel`): INTERNSHIP_AGREEMENT/HYBRID (e'lon kartasidan toshib chiqardi), OWNER, INTERMEDIATE, UNAVAILABLE, BEPUL_KIRISH, murojaat ustuvorligi/turi/holati; "Self-declared/Verified", "MANUAL ENTRY", "Matching Engine", "Assurance", "/nomzod" kabi yo'l belgilar o'zbekchaga.
  - Yorug' rejim: to'yingan fonli tugmalarda (bg-primary, bg-emerald-500 ...) matn qora bo'lib qolardi -> oq; pastel matnlar (shu jumladan /90 shaffoflik variantlari, masalan xavfsizlikdagi sariq ogohlantirish) 700-tonga; placeholder oldindan to'ldirilgan qiymatga o'xshamaydi; fayl tanlash tugmasi bezatildi; `font-mono` ortiqcha ishlatilishi oddiy shriftga.
  - Shartlar/Maxfiylik/Haqida: markdown "# ..." xom ko'rinardi -> xavfsiz `SimpleMarkdown` (faqat React tugunlari).
  - Kundalik: faol amaliyot bo'lmasa kiritish formasi ko'rsatilmaydi; arizalar/shartnomalar/kundalikdagi takroriy "Faol hisob / ID / Chiqish" bloki olib tashlandi (Navbar'da bor).
  - Baholar: backend izohidan "AC-023" olib tashlandi, og'ir kulrang blok yengil quduqqa.
- **Tekshiruv**: eslint 0, tsc 0, vitest 90/90 (+5), next build OK; Edge bilan 15 ommaviy sahifa qayta suratga olindi (markdown, enum, tugma matni, placeholder tasdiqlandi). Kabinet sahifalarini qayta suratga olish uchun yangi staging sessiya kerak edi; seed skripti IAM shifrlash kalitini talab qiladi (.env) - unga tegilmadi, kabinet sahifalari CI va kod ko'rigi bilan tekshirildi.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-179 — 2026-11-16 — Issue #245 -> Dizayn prototipi: foydalanuvchi profili va elementlar

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#246, 419639d). Foydalanuvchi namuna rasm yubordi (monoxrom bento dashboard: katta sarlavha, avatarli pill-taymlayn, qora kartalar, chap pastda profil kartasi) va "profil ko'rinishi hamda element qismlariga chuqurroq yondash" dedi.
- **Yechim**:
  - `globals.css` "Mono bento" qatlami: `fb-display` (katta sarlavha), `fb-ink-card` (qora karta, dark rejimda ham), `fb-nav-item` (faol bo'lim - qora pill, dark rejimda oq pill), `fb-capsule`, `fb-bar` (taymlayn), `fb-seg`, `fb-avatar` (bosh harflar), `fb-progress`, `fb-file-row`, `fb-icon-btn`, dekorativ `fb-ring` (reduced-motion'da to'xtaydi).
  - `components/profile/ProfileOverview.tsx`: "Salom, {ism}" + "Mening profilim"; haftalik bo'sh vaqt taymlayni (hafta kunlari x soatlar, bugungi kun ajratilgan, haftalik soat jami); profil tayyorligi % (5 bo'lim, har biri tegishli tabni ochadi); qora "Rezyume" kartasi (PDF yuklab olish, tahrirlash); "Hujjatlarim" (sertifikat + portfolio, "+"); arizalar statistikasi (jami / ko'rib chiqilmoqda / suhbat / taklif, yuklanmasa xabar - nol emas); qora panel: ko'nikmalar (tasdiqlangan ulushi), tajriba (oylar), talabalik (ariza -> tekshiruv -> tasdiq). Faqat haqiqiy ma'lumot, soxta grafik yo'q.
  - `components/profile/ProfileCard.tsx`: sidebar pastida avatar, ism, rol, ochiladigan hisob menyusi (Xavfsizlik, Chiqish; aria-expanded).
  - Nomzod sidebar'i oq panel + qora faol pill; korxona va universitet yon menyulari ham shu elementga o'tkazildi. Navbar salomlashuvi ism bilan.
  - Backend `/auth/me` endi foydalanuvchining o'z `display_name`ini qaytaradi (+ test `test_auth_me_profile.py`), BFF uzatadi.
- **Tekshiruv**: eslint 0, tsc 0, vitest 100/100 (+10), next build OK; Edge'da nomzod API'lari mock qilingan holda desktop yorug'/qorong'i va mobil suratlar (konsol xatosi yo'q, gorizontal toshish yo'q). Korxona/universitet menyulari suratga olinmadi (sessiya kerak), lint/build bilan tekshirildi. Backend testi faqat CI'da.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-180 — 2026-11-16 — Issue #247 -> Kundalik va o'quv jadvali

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#248, 09571ff). Foydalanuvchi: "Kundalik hamda o'quv jadvali bo'yicha ishla".
- **Topilgan xatolar**:
  - Kundalik: backend API-053 yozuvni `current_revision` ichida qaytaradi, frontend esa tekis maydonlarni o'qirdi -> tarixda hamma kun "Qoralama, 0 daqiqa", mentor/OTM qarorlari ko'rinmasdi ("REVIEWED"/"NEEDS_REVISION" backendda yo'q). Standart maydonlar qayta yuklanmasdi, saqlash xatosi `.catch(() => null)` bilan yutilardi; sana UTC bo'yicha; "200 soat" qattiq yozilgan.
  - O'quv jadvali: talaba o'z jadvalini ko'ra olmasdi (faqat xodim endpointlari). Jadvalni har qanday faol xodim (o'qituvchi ham) qayta yoza olardi va bu barcha talabalarning bo'sh vaqt qoidalarini o'chirib qayta yozadi. Sinxronlash tasdiqlanmagan (DECLARED/PENDING) talabalarga ham tegardi, tugash sanasi bor talabalarni esa umuman o'tkazib yuborardi (`end_date IS NULL`).
- **Yechim**:
  - Backend: `GET /api/v1/me/timetable` (faqat joriy VERIFIED talabalik + VERIFIED OTM; guruh dastur nomidan, aks holda DEFAULT; slotlarda guruh kodi/ID yo'q), `_match_group` umumiy funksiya; jadval yozish/import uchun MFA COORDINATOR; sinxronlash faqat joriy VERIFIED talabalik (start<=bugun, end null yoki >=bugun). Testlar `test_my_timetable.py` (4).
  - Frontend: `/nomzod/jadval` "O'quv jadvali" (keyingi dars qora kartada, bugungi darslar, haftalik yuklama, para x kun setkasi, mobil kun tanlagich, ish uchun bo'sh oynalar; holat bo'yicha bo'sh holatlar). `lib/diary.ts` normalizatori (API-053 -> UI, sharh qarorlaridan holat). Kundalik sahifasi qayta qurildi: oy kalendari (tasdiqlangan/tekshiruvda/izoh bor/qoralama, dars kunlari belgisi, amaliyot davridan tashqari kunlar yopiq), tanlangan kun darslari + ish vaqti dars bilan to'qnashsa ogohlantirish, kelish/ketish standart qiymati jadvaldagi bo'sh oynadan, 8 soat chegarasi progress bilan, standart maydonlar qayta yuklanadi, qo'shimcha maydonlar saqlanmasa ogohlantirish, me'yor soati diary stats'dan, mentor/OTM izohlari qora kartada. Profil taymlayniga darslar kulrang chiziq bilan qo'shildi. InternshipDocumentsHub bo'sh imzo xaritasida yiqilmaydi.
- **Tekshiruv**: eslint 0, tsc 0, vitest 110/110 (+10), next build OK; Edge'da mock API bilan kundalik va jadval desktop yorug'/qorong'i + mobil (konsol xatosi yo'q, gorizontal toshish yo'q). Backend testlari faqat CI'da.
- **Qolgan bo'shliq (backend workflow)**: mentor "tuzatish so'radi" desa ham yozuv SUBMITTED holatda qoladi va talaba uni o'zgartira olmaydi (SUBMITTED_LOG_IMMUTABLE) - UI buni ochiq aytadi; qayta topshirish oqimi alohida qaror talab qiladi.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-181 — 2026-11-16 — Issue #249 -> Universitet kabineti: monoxrom bento dizayn

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#250, 391e217). Foydalanuvchi: "talabalarda hozircha yaxshi, endi universitet uchun shu dizayndan foydalan".
- **Yechim**: `components/university/UniversityOverview.tsx` - "Salom, {ism}" + "Akademik panel", OTM nomi/hududi, sana va rol kapsulasi; "Kundaliklar oqimi" (navbatdagi kundaliklar so'nggi 7 kun yuborilgan kuni bo'yicha, eng eskisi necha kun kutmoqda); "Biriktiruv qamrovi" (koordinator: rahbar biriktirilgan / kutmoqda; o'qituvchi: qabul qilingan / kutmoqda); qora "Navbatdagi ko'rik" (eng eski kundalik, avatar, ko'rib chiqish); "Rahbar tayinlash" yoki "Talabalarim" ro'yxati; "Bugungi holat" sonlari; qora panel (amaliyot nazorati progress, kafedra, o'quv jadvali guruh/dars/talaba). Avvalgi `SkeuoAreaChart` turli modullar sonini vaqt qatori kabi chizgan edi - olib tashlandi. Sidebar ostida ProfileCard (ism, rol, OTM, chiqish). Navbat va biriktirilganlar ro'yxati yangi elementlarda: "Maqsad: ACADEMIC_REVIEW" va amaliyot/muassasa ID'lari o'rniga talaba ismi, kundalik sanasi, korxona, holat kapsulasi. Kirgan xodimga layout'dagi ortiqcha yuqori chiziq ko'rsatilmaydi. Workspace (OTM nomi, rollar) endi saqlanadi.
- **Tekshiruv**: eslint 0, tsc 0, vitest 116/116 (+6), next build OK; Edge'da mock API bilan desktop yorug'/qorong'i + mobil (konsol xatosi yo'q, gorizontal toshish yo'q). Qolgan tablar (hisobotlar, analitika, jadval tahriri) mavjud uslubda, yorug' rejim moslamasi orqali.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-182 — 2026-11-16 — Issue #251 -> Korxona kabineti: monoxrom bento dizayn

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#252, 3fb4b8f). Foydalanuvchi: "ish yakunlangach korxona profili bilan ham ishla".
- **Yechim**: `components/employer/EmployerOverview.tsx` - "Salom, {ism}" + "Korxona paneli", korxona nomi/hududi, sana, rol ("Asosiy egasi"), "Yangi e'lon"; "Nabor voronkasi" (arizalar -> saralangan -> suhbatdan o'tgan -> taklif -> qabul, API-068 dan; konversiya va javob kutayotganlar); "Vakansiyalar" (e'lon qilingan/jami, holatlar bo'yicha segment chiziq); qora "Eng faol vakansiya" (eng ko'p arizali e'lon, band o'rinlar progress, "Arizalarni ko'rish" kanbanni shu e'lon bilan ochadi); "E'lonlarim" ro'yxati; "Bugungi holat"; qora panel (suhbatlar, amaliyot va dual ta'lim, mentorlik: kundaliklar navbati va muddati o'tganlar). Avvalgi SkeuoStatCard/VerticalMeter/LiveFeed (feed'da xom ariza holati) olib tashlandi. Sidebar ostida ProfileCard; tashkilot tanlash bloki faqat bir nechta tashkilot bo'lsa; layout yuqori chizig'i faqat mehmonlarga. PAUSED yorlig'i qo'shildi.
- **Topilgan xato**: `bg-[var(--x)]/NN` (CSS o'zgaruvchili rang + shaffoflik) Tailwind'da shaffof chiqardi - profil taymlayni, jadval va voronka fonlari ko'rinmasdi; `color-mix` bilan almashtirildi va build CSS'da tekshirildi.
- **Tekshiruv**: eslint 0, tsc 0, vitest 122/122 (+6), next build OK; Edge'da mock API bilan desktop yorug'/qorong'i + mobil (konsol xatosi yo'q, gorizontal toshish yo'q).
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-183 — 2026-11-16 — Issue #253 -> Foydalanuvchilar o'rtasida chat va guruhlar

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#254, 9442215). Foydalanuvchi: "endi har bir foydalanuvchi uchun o'zaro chat tizimini guruh ochish imkoni bilan qil".
- **Xavfsizlik modeli** (qaror): begona odamga to'g'ridan-to'g'ri yozib bo'lmaydi. Kontaktlar real aloqadan hisoblanadi: bir korxona yoki bir OTM faol xodimlari (hamkasb), korxona xodimi <-> uning vakansiyasiga ariza bergan nomzod, OTM xodimi <-> shu OTMda VERIFIED talaba, mavjud shaxsiy suhbatdosh. Boshqa har kim faqat egasi ulashgan 8 belgili shaxsiy kontakt kod orqali (yangilasa eskisi ishlamaydi). Bloklash ikki tomonlama shaxsiy xabarni to'xtatadi va kontaktdan olib tashlaydi. Suhbat faqat a'zolarga mavjud (boshqalarga 404). O'chirilgan xabar matni bazada ham o'chiriladi. Xabar 1-4000 belgi, 30 xabar/daqiqa cheklovi. Guruh: egasi nom, a'zolar, taklif havolasini boshqaradi (bazada faqat SHA-256 xeshi), a'zo o'zi chiqadi, egasi chiqsa eng eski a'zo ega bo'ladi; 200 kishigacha.
- **Backend**: migratsiya `0023_chat_messaging` (chat_conversations, chat_members, chat_messages, chat_contact_codes, chat_blocks; jadvallar 133 -> 138, testlardagi head/son yangilandi), `app/services/chat.py`, `app/api/v1/chat.py` (19 marshrut), `test_chat.py` (6 test: aloqa/kod, xabar/o'qilmagan/ko'rinish, guruh qoidalari/havola/vorislik, bloklash, o'chirish, sessiya).
- **Frontend**: BFF `api/bff/chat/[...path]` (faqat ruxsat etilgan yo'llar, mutatsiyalarda CSRF), `lib/chat.ts`, `/xabarlar` (ro'yxat + suhbat, mobil bitta panel, 15s/4s so'rov, Enter yuborish, eski xabarlar, o'chirish, guruh sozlamalari, yangi suhbat: kontaktlar yoki kod, guruh yaratish, `?qoshilish=` taklif havolasi orqali qo'shilish), Navbar'da o'qilmaganlar soni. Modal portal orqali (glass kartadagi backdrop-filter fixed qatlamni qamab qo'ymasligi uchun).
- **Tekshiruv**: eslint 0, tsc 0, vitest 128/128 (+6), next build OK; Edge'da mock API bilan desktop yorug'/qorong'i + mobil, sozlamalar va yangi suhbat oynalari (konsol xatosi yo'q, gorizontal toshish yo'q). Backend testlari faqat CI'da. Real vaqt (WebSocket) yo'q - so'rov (polling) bilan.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-184 — 2026-11-16 — Issue #255 -> Qolib ketgan va tushunarsiz qismlar

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#256, 96dab70). Foydalanuvchi: "qolib ketgan qismlarni aniqla, tushunarsiz bo'lib qolganlarini ham, qo'shimcha kerak bo'lsa kirit".
- **Aniqlash usuli**: har bir sahifada eski klasslar, xom ID (`.slice(0, 8)`), jargon soni bo'yicha reyting + nomzod sahifalarini mock bilan suratga olish.
- **Topilgan xatolar**: (1) universitet "Yig'ma hisobotlar"dagi kelishuv kartasi `agr.organization_id.slice` ni chaqirardi, backend esa bu maydonni qaytarmaydi -> kelishuv bo'lsa tab yiqilardi; tur va karta haqiqiy maydonlarga (versiya, maqsadlar, muddat) moslandi, rahbarlik kartasi talaba ismi va tasdiq sanasi bilan. (2) Baholar sahifasi javobda ro'yxat bo'lmasa yiqilardi; arizalar statistikasi maydon bo'lmasa "NaN" ko'rsatardi -> API'da normallashtirildi. (3) Xodim tayinloviga rozilik beruvchi qaysi universitet so'rayotganini ko'rmasdi (faqat ID) -> backend inbox'ga `institution_name` qo'shildi (+ test).
- **Xom ID'lar o'rniga ma'no**: korxona kanbanida nomzod sarlavhasi (ariza snapshot'i DB-042 bo'yicha ataylab ismsiz - ism qo'shilmadi), mentorlik/amaliyot kartalari sana va holat bilan; nomzod shartnomalari - vakansiya, korxona, "shartlar kelishilgan"; saqlanganlar - korxona nomi (backend'ga `organization_name` qo'shildi); baholar va talabalikdagi ID'lar olib tashlandi; sertifikatdagi "File UUID" maydoni olib tashlandi; e'londa kirgan hisob ismi; universitet navbati, talabalar jadvali, hujjatlar tanlovi. Buyurtma/murojaat/kvitansiya raqamlari va operator paneli ID'lari ataylab qoldirildi.
- **Tushunarlilik**: nomzod sahifalari sarlavhalari qisqa va katta (Arizalarim, Shartnomalar, Saqlanganlar, Baholar, Bildirishnomalar, Xavfsizlik, Yordam); xavfsizlikda "A1/A2", "RFC 6238 TOTP (SHA-1)", "API amallari", "(Recovery Codes)" oddiy tilga; korxona/universitet tab sarlavhalari qisqartirildi.
- **Vizual**: eski ko'k/indigo/sky tugmalar (131+ joy) CSS orqali qora pill'ga, eski kartalar 20px burchakka.
- **Qo'shimcha**: nomzod sidebar'iga "Xabarlar".
- **Tekshiruv**: eslint 0, tsc 0, vitest 128/128, next build OK; Edge'da 7 nomzod sahifasi va korxona paneli mock bilan (konsol xatosi yo'q, toshish yo'q).
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-185 — 2026-11-17 — Issue #257 -> Universitet ichki tablari va operator paneli

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#258, 2050a49). Foydalanuvchi LOG-184 hisobotidagi "ichki tablarni qayta ishlash" taklifiga: "ha bajar".
- **Universitet**: "Kafedra taqsimoti" -> "Ilmiy rahbar tayinlash" mono ro'yxat (avatar, holat, qora tugma, tushuntirish); dars jadvali: hafta kuni nomi backend bermasa raqamdan, CSV yuklash yordami ingliz ustun nomlari o'rniga oddiy tilda, "REPLACE/APPEND" o'rniga o'zbekcha; sarlavhalar: Hisobotlar, Platforma kelishuvlari, Universitet ma'lumotlari, Davomat, Haftalik soatlar, Natijalar va baholar, Dars jadvali; haftalik trend ustunlari pill (oxirgi hafta ajratilgan); kelishuv/rahbarlik maqsadlari o'zbekcha (ACADEMIC_VIEW va boshq.).
- **Operator paneli**: `components/operator/OperatorOverview.tsx` - "Salom, {ism}" + "Operator paneli", rollar o'zbekcha; faqat rol ochishi mumkin bo'lgan modullar: tekshiruv navbati (ochiq soni, progress, birinchi 3 ta), murojaatlar muhimligi bo'yicha (pill), qora "Diqqat talab qiladi" (muhim murojaatlar, muddati o'tgan tekshiruvlar, to'lov nomuvofiqligi), so'nggi hodisalar, qora panel (audit, moliya, favqulodda ruxsat). Eski SkeuoStatCard/VerticalMeter/LiveFeed (feed'da xom harakat kodi va xodim ID) olib tashlandi; sidebar pill + ProfileCard; mehmon uchun sarlavha. Audit jadvalida harakat va obyekt turi o'qiladigan (asl kod tooltip'da); ID/kalit/xesh ustunlari forensika uchun qoldirildi.
- **Tekshiruv**: eslint 0, tsc 0, vitest 133/133 (+5), next build OK; Edge'da mock bilan universitet 6 ta tab va operator paneli (desktop yorug'/qorong'i, mobil) - konsol xatosi yo'q, toshish yo'q.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-186 — 2026-11-17 — Issue #259 -> Staging'da 4 ta haqiqiy akkaunt bilan brauzer testi + e'lonlar moderatsiyasi

- AI / sessiya / model: Claude Code / model shu yozuvda qayd etilmagan / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#260, 4dd352c). Foydalanuvchi: "har bir funksiyani brauzer rejimida 4 xil akkaunt ochib sinab ko'r ... o'zingga akkauntlar yaratishing mumkin"; muhit tanlovi: "Eski staging'da sinash" (Docker qayta build qilinmadi).
- **Akkauntlar**: staging helper (`scripts/test_unified_auth_all_roles_staging.py`, infra/.env foydalanuvchi ruxsati bilan, qiymatlar chiqarilmadi) orqali talaba, korxona OWNER (2FA), universitet COORDINATOR (2FA), operator MODERATOR (2FA). Login ma'lumotlari faqat lokal scratchpad faylida.
- **Natija (Edge, :3000 eski staging)**: 4 rol UI orqali parol + TOTP bilan kirdi; barcha kabinet sahifalari/tablari ochildi (sahifa xatosi 0). Talaba: profil saqlash 200, ko'nikma 200, haftalik jadval PUT 200, rezyume PDF 201, vakansiyani saqlash 201/200, ariza topshirish 201 va "Arizalarim"da ko'rindi, murojaat 201 -> operator navbatida ko'rindi. Korxona: vakansiya yaratish 201, kanban yuklandi. Universitet: analitika yuklandi.
- **Topilgan xatolar**: (1) **Vakansiya moderatsiyasi uchun UI va ro'yxat API yo'q** - UI'da yaratilgan e'lon DRAFT'da qoladi, nashr 409 (avval moderatsiya, keyin faol tarif kerak); butun yollash zanjiri UI orqali uzilgan. (2) Vakansiya sahifasi `organization.name` o'qiydi, API-005 esa `public_name/legal_name` qaytaradi -> korxona nomi sahifada va ariza oynasida bo'sh. (3) Nashr xatolari umumiy matn bilan. Eski staging'ning o'zida bo'lgan, integration'da allaqachon tuzatilganlar: universitet navbati INSTITUTION_REQUIRED (400), operator ruxsatsiz modullarga 403, tashkilot/vakansiya UUID qo'lda kiritish, dock desktopda kontent ustida, xom enum/katalog kodlari.
- **Tuzatish**: backend `GET /api/v1/moderation/opportunities` (faqat MODERATOR; eski birinchi; korxona nomi, shartlar, to'lov; o'z e'loni `own`, muallif ID'si chiqmaydi) + `test_moderation_queue.py` (2 test). Frontend: OperatorModule `MODERATION`, BFF `operator/moderation/{opportunities,actions}` (faqat ruxsat etilgan maydonlar, izoh >=15), `ModerationPanel` (sabab tanlash + izoh, o'z e'loniga qaror berilmaydi), operator overview "e'lon moderatsiyani kutmoqda"; korxona e'lonlari "Moderatsiyada / Tasdiqlandi - e'lon qilish mumkin / Moderator rad etdi"; MODERATION_APPROVAL_REQUIRED va ACTIVE_ENTITLEMENT_REQUIRED tushunarli xabarlar; API-005 korxona nomi normallashtirildi.
- **Sinab bo'lmagan / to'xtatilgan**: korxona kanbanida arizani saralash va universitet jadval/hisobot yozish - eski staging cheklovi va nashr zanjiri tufayli. Staging bazasiga soxta "to'langan" buyurtma + qo'lda APPROVED yozish (test fixture) avtomatik ruxsat tizimi tomonidan rad etildi va chetlab o'tilmadi.
- **Tekshiruv**: eslint 0, tsc 0, vitest 136/136 (+3), next build OK; backend testlari CI'da.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-187 — 2026-11-17 — Issue #261 -> Yangilangan staging'da to'liq E2E va topilgan kamchiliklar

- AI / sessiya / model: Claude Code / Claude Opus 5.5 (`claude-opus-5-5`) / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#262, 66cac57). Foydalanuvchi staging'ni yangi kod bilan qayta build qilishga ruxsat berdi ("1").
- **Staging**: `docker compose -p flexbridge-r1 -f <worktree>/infra/compose.yaml --env-file D:/FlexBridge/infra/.env up -d --build` integration 4dd352c dan; migrate exit 0 (0023 chat qo'llandi), backend/frontend healthy, telegram-bot servisi (simulation) qo'shildi; Postgres/MinIO/ClamAV ma'lumotlari saqlandi. BFF_SESSION_SECRET yo'q -> sessiyalar qayta ishga tushganda tugaydi.
- **E2E (Edge, 4 ta haqiqiy akkaunt, UI orqali parol + TOTP)**: 21/23 qadam o'tdi, sahifa xatosi 0. Zanjir: korxona e'lon yaratdi (201) -> "Moderatsiyada" -> operator yangi bo'limda tasdiqladi (201) -> nashr 409 ACTIVE_ENTITLEMENT_REQUIRED (tushunarli xabar) -> tarif buyurtmasi (201, PENDING_PAYMENT). Chat: talaba korxona kontakt kodi orqali yozdi, korxona javob berdi, talaba javobni oldi, guruh yaratildi. Universitet: dars qo'shish 200 (keyingi takrorda kutilgan 422 to'qnashuv), yig'ma hisobot 201, xodimlar/talabalik/analitika ochildi. Kanban yuklandi. Talabaning takroriy arizasi kutilgan 409.
- **Topilgan va tuzatilgan**: takroriy ariza va jadval to'qnashuvi "birozdan so'ng qayta urinib ko'ring" deb chiqardi (noto'g'ri yo'naltiruvchi) -> aniq xabarlar + `_OVERLAP`/`_EXISTS` naqshlari (+test); "Vakansiyalar" kartasida moderatsiyadan o'tgan, hali e'lon qilinmagan e'lonlar hisobga kirmasdi -> "Nashrga tayyor" segmenti; to'lov bo'limida BEPUL_KIRISH, PENDING_PAYMENT, ORG_PLAN_30D xom kodlari -> o'zbekcha; kutilayotgan buyurtma uchun izoh.
- **Hal qilinmagan (foydalanuvchi qarori)**: buyurtma to'lanmaydi - `POST /payments/attempts` faqat umumiy HMAC adapterini qabul qiladi, pul faqat provayderning imzolangan webhook'i bilan tasdiqlanadi; real provayder (Click/Payme/Uzum) ulanmagan. Shu sababli korxona interfeys orqali e'lonni oxirigacha nashr qila olmaydi.
- **Tekshiruv**: eslint 0, tsc 0, vitest 137/137 (+1), next build OK.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-188 — 2026-11-17 — Issue #263 -> Barcha oynalarda video-namunadagi "qurilma" dizayni (ranglar o'zgarmadi)

- AI / sessiya / model: Claude Code / Claude Opus 5.5 (`claude-opus-5-5`) / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#264, f21ec5e). Foydalanuvchi skeuomorf dashboard videosini yubordi: "dizayinni hamma oynalarda shu kabi qilib chiq lekin ranglar hozirgiday qolsin". Video kadrlari ffmpeg bilan ajratildi va tahlil qilindi.
- **Qilingan**: (1) Navbar -> bitta to'q yuqori kapsula: chapda avatar (bosh harflar) + salomlashuv, o'rtada botiq holat maydoni (aylanuvchi orb, portal nomi, sana, kursor), o'ngda metall dumaloq tugmalar (chat, mavzu/chiqish faqat mobil); (2) kompyuterda chap suzuvchi rels: tezkor manzillar + mavzu, yuqoriga, chiqish; faol tugma metall "knob", hover'da yorliq; (3) `AppStage`: barcha sahifalar vintli bitta "ekran" panelida (transform/filter yo'q - fixed elementlar buzilmaydi); bo'lim/tab almashganda ko'rinayotgan kartalar bosqichma-bosqich paydo bo'ladi (reduced-motion hurmat qilinadi, holat qayta mount qilinmaydi); (4) `SectionDock`: talaba/korxona/universitet/operator ichki menyulari createPortal orqali pastki to'q kapsulaga ko'chirildi - tugmalar, rol cheklovlari, hisoblagichlar va yuklash mantig'i o'zgarmadi; mobil'dagi ikki marta takrorlangan menyu yo'qoldi; ProfileCard ustunlari olib tashlandi (shaxs/chiqish yuqori kapsula va relsda); (5) silindrsimon ustunlar, botiq segmentlar. Ranglar mavjud tokenlardan (aksent #e0622d, obsidian, oq shisha).
- **Topilgan eski xato**: Navbar `getDashboardForRoles` eski rol kodlarini (EMPLOYER_OWNER...) qidirardi, shuning uchun har qanday xodim "Talaba Kabineti"ga yo'naltirilardi -> `lib/roles.resolvePortalDashboard` ishlatiladi. Tailwind v4 utilitlari qatlamda bo'lgani uchun komponent sinfida `display` berish `hidden`ni bosib ketadi - chiplarda display utilitlarda qoldirildi.
- **Tekshiruv**: eslint 0, tsc 0, vitest 140/140 (+3 qobiq testi), next build OK. Lokal build (127.0.0.1:3100, staging backend) bilan 4 akkaunt UI orqali kirdi; 8 oyna x (kompyuter yorug'/qorong'i + telefon) = 24 skrinshot: sahifa xatosi 0, gorizontal siljish 0, bo'lim kapsulasi portal sahifalarida (11/5/9/6 band), umumiy dock faqat boshqa sahifalarda. Rollararo E2E yangi dizaynda: 21/23 (2 tasi kutilgan: takroriy ariza, jadval to'qnashuvi) - moderatsiya, chat, tarif buyurtmasi, jadval/hisobot ishlaydi.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-189 — 2026-11-17 — Issue #265 -> Tugmalar, harakatlar va animatsiyalar (taktil harakat qatlami)

- AI / sessiya / model: Claude Code / Claude Opus 5.5 (`claude-opus-5-5`) / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Manba: `03_BOSQICHLAR_VA_HOLAT.md` yozuvi
- **Holat**: **MERGED** (#266, a6c3e01). Foydalanuvchi: "Tugmalar harakatlar va animatsiyalar uchun chuqur ish olib bor". Staging 2026-11-17 da a6c3e01 dan qayta qurildi (foydalanuvchi: "ha ruhsad"): E2E 21/23, harakat 11/11, 24 skrinshot toza.
- **Qilingan**: (1) `InteractionLayer` (global, sahifalarni o'zgartirmaydi): har bir tugma hover'da biroz ko'tariladi, bosilganda botadi (klaviatura Enter/Space ham), bosilgan nuqtadan tugma rangida ripple; bosilgan tugma disabled bo'lsa (so'rov ketyapti) `aria-busy` + yorug'lik o'tishi, qaytib yoqilganda "settle" porlashi; ::before bo'sh va kesilgan tugmalardagina chiziladi. (2) `useGlider`: pastki bo'lim kapsulasi, chap rels (metall knob) va mobil dock'da bitta faol pill/knob prujinali harakat bilan siljiydi, aylanuvchi menyuda faol band markazga suriladi. (3) Mavzu almashinuvi View Transitions API bilan bosilgan tugmadan doira bo'lib yoyiladi (klaviaturada tugma markazidan; API yo'q bo'lsa oddiy almashinuv). (4) `CountUp`: dashboard raqamlari (korxona/operator/universitet/talaba) mexanik hisoblagichdek sanaladi; server HTML'da yakuniy qiymat. (5) Modal/scrim paydo bo'lishi, alertlar sirpanib kirishi, progress to'lishi, bo'lim almashganda ekran bo'ylab yangilanish chizig'i. (6) Bitta fokus halqasi (aksent), disabled kursori. prefers-reduced-motion: ripple/settle/CountUp/doira o'chadi.
- **Topilgan xato (#264 dan)**: faol bo'lim ustida hover'da matn oq bo'lib, oq pill ustida ko'rinmay qolardi -> hover faol bandni chetlab o'tadi.
- **Tekshiruv**: eslint 0, tsc 0, vitest 147/147 (+7 harakat testi), next build OK. Edge'da o'lchov (11/11 PASS): glider faol bandga siljidi (oraliq holat bor), ripple + botish (scale 0.977), modal animatsiyasi, rels knob-glider, View Transition doira, so'rov paytida "band" va keyin tiklanish, sahifa xatosi 0, reduced-motion'da ripple yo'q. Rollararo E2E 21/23 (2 tasi kutilgan). Demo video kadrlardan yig'ildi.
- `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan.

### LOG-190 — 2026-11-17 — Hujjatlarni bo'limlarga ajratish, AI xotirasini to'ldirish (Issue #267)

- AI / sessiya / model: Claude Code / Claude Opus 5.5 (`claude-opus-5-5`) / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Vazifa / rol: foydalanuvchi so'rovi — «o'zing qilgan ishlarni AI xotirasi md ga qo'shmagan bo'lsang qo'shib qo'y hamda loyihani aniq bo'limlarga ajratib frontend va backend alohida ishlashi uchun kerakli fayllar hamda AI xotiralari md lar va hujjatlar qismlarini bo'laklab fayllarni tartibga keltir». Amalga oshiruvchi.
- Boshlang'ich holat: 01-faylda batafsil yozuvlar LOG-155 da tugagan; LOG-156…189 faqat fayl boshidagi «Current …» qatorlarida edi (eng uzuni 6.8 KB). 01 — 388 KB, 03 — 344 KB, ANTIGRAVITY_HANDOFF — 190 KB, 02 — 103 KB: AI agentlar ularni to'liq o'qiy olmasdi.
- Qilingan ish:
  - 01-faylga LOG-156…LOG-190 yozuvlari qo'shildi (manbadan o'zgartirilmasdan, muallif faqat aniq bo'lsa).
  - 01, 02, 03 va ANTIGRAVITY_HANDOFF asosiy fayllari o'z yo'lida qoldi (AGENTS.md, Antigravity runner va boshqa agentlar ularni yo'l bo'yicha o'qiydi); ularda endi qoidalar, yagona «Joriy holat» bo'limi va so'nggi yozuvlar. Eski tarix `docs/journals/archive/` va `docs/protocols/archive/` ga o'zgartirilmasdan ko'chirildi; skript har bir asl qator yangi fayllarda borligini tekshirdi (yo'qolgan qator 0).
  - Frontend va backend alohida ishlashi uchun: `frontend/AGENTS.md`, `backend/AGENTS.md` (tegishli fayllar, buyruqlar, qoidalar, chegara shartnomasi), `docs/frontend/README.md`, `docs/frontend/DIZAYN_VA_HARAKAT.md`, `docs/backend/README.md` (26 ta domen spetsifikatsiyasi indeksi), `docs/operations/STAGING_VA_E2E.md`; brauzer E2E skriptlari `scripts/e2e/` ga qo'shildi (sir yo'q, hisob ma'lumotlari faqat argument sifatida).
  - `docs/README.md` hujjatlar xaritasi va yozish qoidasi bilan qayta yozildi.
- Tuzatish yozuvi (LOG-188 ga): u yerda «Tailwind v4 utilitlari qatlamda» deb yozilgan — noto'g'ri. Loyihada Tailwind 3.4.15; `globals.css` da `@tailwind utilities` boshida, komponent sinflari keyin keladi, shuning uchun bir xil specifiklikda komponent sinfidagi `display` utilitadagi `hidden` ni bosib ketadi. Xulosa (display'ni utilitlarda qoldirish) o'zgarmaydi.
- Tekshiruv: bo'laklash skripti qatorlar to'liqligini tekshirdi; havolalar mavjud fayllarga ishora qilishi tekshirildi; `python scripts/check_publish.py` (sir/`.env` yo'qligi); frontend/backend kodi o'zgarmadi.
- Topshirilgan holat / keyingi qadam: yangi yozuvlar asosiy faylning oxiriga qo'shiladi va «Joriy holat» bo'limi yangilanadi; asosiy fayl ~150 KB dan oshsa, eski yozuvlar yangi `archive/` bo'lagiga ko'chiriladi.

### LOG-191 — 2026-11-17 — Pastki kapsulada suyuqlik oqimi effekti (Issue #269)

- AI / sessiya / model: Claude Code / Claude Opus 5.5 (`claude-opus-5-5`) / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Vazifa / rol: foydalanuvchi skrinshot bilan so'radi — "pastki qismga ko'rsatilganday lekin silliqroq animatsion suyuqlik oqish effektini qo'sh". Amalga oshiruvchi.
- Boshlang'ich holat: glider CSS `transition` (overshoot easing) bilan kenglik va joylashuvni birga animatsiya qilardi; skrinshotda o'tish paytida uzilgan oq bo'lak va oq ustida oq matn ko'ringan.
- Qilingan ish: `frontend/src/lib/motion.ts` — to'rt chetli prujina fizikasi (`createLiquid`, `retarget`, `stepLiquid`, `liquidShape`), tezlik chegarasi, tinch kadrdan boshlash, har kadrda qoplangan bandni belgilash (`data-under-glider`); `globals.css` — glider easing'i olib tashlandi, matn rangi qoplamaga bog'landi; `frontend/src/lib/motion.test.ts` (6 test); `Motion.test.tsx` glider testi `waitFor` bilan.
- Tekshiruv: eslint 0, tsc 0, vitest 153/153, next build OK; Edge'da 7 o'tish kadrma-kadr: aniq tushish, qadam 15–54 px (oldin 132), sahifa xatosi 0; kadrlar lentasi va video foydalanuvchiga yuborildi.
- Muammo va cheklov: qisman (<50%) qoplangan chetdagi band o'tish paytida bir lahza yorug' matnda qoladi — ataylab (oqim effekti).
- Topshirilgan holat / keyingi qadam: PR #270 merge qilindi (5331259). Foydalanuvchi: kutgan natija emas — tomchisimon iz kerak (LOG-192).

### LOG-192 — 2026-11-17 — Suyuqlik ortidan tomchisimon iz (Issue #271)

- AI / sessiya / model: Claude Code / Claude Opus 5.5 (`claude-opus-5-5`) / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Vazifa / rol: foydalanuvchi LOG-191 natijasini ko'rib: "kutgan natija emas — yuborgan rasmdagidek tomchisimon iz qolishi kerak". Amalga oshiruvchi.
- Boshlang'ich holat: pill suyuqlikdek cho'zilib-yig'ilardi, lekin ortida iz qoldirmasdi.
- Qilingan ish: `frontend/src/components/motion/GooFilter.tsx` (SVG metaball filtri, root layout'da); `.fb-goo` qatlami Navbar (rels, mobil dock) va `SectionDock` da; `frontend/src/lib/motion.ts` — tomchilar (uzilish, to'kilish, so'nish, tortilish) va sof funksiyalar; `globals.css` — `.fb-goo`, `.fb-drop`; testlar `lib/motion.test.ts`, `components/motion/Motion.test.tsx`.
- Tekshiruv: eslint 0, tsc 0, vitest 157/157, next build OK; Edge'da tomchilar soni (5–9, oxirida 0), aniq tushish, sahifa xatosi 0, harakat o'lchovi 11/11; real vaqt screencast videosi yuborildi.
- Muammo va cheklov: oq tomchi yorliq ustidan o'tganda yorliq bir lahza past kontrastda qoladi (tomchi matn ortida).
- Topshirilgan holat / keyingi qadam: PR CI'dan keyin integration'ga; foydalanuvchi fikri bo'yicha tomchi soni/kattaligini sozlash mumkin.

### LOG-193 — 2026-11-17 — Tugmalar bo'rtiq, shaffof suyuq shisha (Issue #273)

- AI / sessiya / model: Claude Code / Claude Opus 5.5 (`claude-opus-5-5`) / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Vazifa / rol: foydalanuvchi — "tugmalar bo'rtib chiqqanroq, shaffofroq, liquidga o'xshasin". Amalga oshiruvchi.
- Boshlang'ich holat: suyuq pill va tomchilar oq, xira (opaque) edi.
- Qilingan ish: `frontend/src/components/motion/GooFilter.tsx` — suyuq shisha filtri (shaffof tana, specular yorug'lik, ichki soya, shisha chekka, soya); `globals.css` va `Navbar.tsx` — suyuqlik ostidagi yorliqlar oq. Ranglar palitrasi o'zgarmadi.
- Tekshiruv: eslint 0, tsc 0, next build OK; Edge screencast va kattalashtirilgan kadrlar (talaba/korxona kapsulasi, chap rels), sahifa xatosi 0.
- Yumshatish: foydalanuvchi "OSHIRIB YUBORILGAN" dedi -> 1 ta kichik tomchi, kamroq va qisqa iz, kuchsizroq yaltirash/chekka/soya, tana biroz to'liqroq.
- Topshirilgan holat / keyingi qadam: #272 merge qilingach rebase va PR; foydalanuvchi fikri bo'yicha shaffoflik/yaltiroqlikni sozlash mumkin.

### LOG-194 — 2026-11-17 — O'tish animatsiyasi tezlashtirildi (Issue #275)

- AI / sessiya / model: Claude Code / Claude Opus 5.5 (`claude-opus-5-5`) / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Vazifa / rol: foydalanuvchi — "o'tish animatsiyalari tugmalardagi juda sekin bo'lib qolgan". Amalga oshiruvchi.
- Boshlang'ich holat: pill harakati o'rtacha ~0.57–0.59 s (staging'da o'lchandi), oldidan 320 ms gacha kutish.
- Qilingan ish: `frontend/src/lib/motion.ts` (qattiqroq prujinalar, 7000 px/s, 90 ms kutish, tomchilar umri qisqa), `frontend/src/lib/motion.test.ts` (550 ms chegara).
- Tekshiruv: korxona 592 -> 379 ms, talaba 571 -> 330 ms; cho'zilish va aniq tushish saqlandi; eslint/tsc 0, testlar 17/17, build OK.
- Qo'shimcha: `D:/FlexBridge/frontend/tsconfig.json` dagi ortiqcha `1` qatori olib tashlandi (frontend VS Code'da qizil bo'lishining sababi); eski branch va 29 WIP faylga tegilmadi.
- Topshirilgan holat / keyingi qadam: PR CI'dan keyin integration'ga; staging keyingi qayta qurishda yangilanadi.

### LOG-195 — 2026-11-17 — Barcha animatsiyalar 3 barobar tez; main'ni o'tkazish (Issue #277)

- AI / sessiya / model: Claude Code / Claude Opus 5.5 (`claude-opus-5-5`) / sessiya https://claude.ai/code/session_012EiWngRW7f6dkHVrxC2ZwR
- Vazifa / rol: foydalanuvchi — (1) "ha ruxsat, qo'shimcha main'ga o'tishga ruxsat beraman, hozirgi holatni main qil, hozirgi main'ni nusxalab qo'y"; (2) "animatsiyalarni hozirgidan 3 barobar tezlashtirish kerak". Amalga oshiruvchi.
- Qilingan ish: eski main 764fb98 zaxiralandi (GitHub branch `backup/main-2026-11-17-764fb98`, tag `main-backup-2026-11-17`, oflayn bundle `D:/Codex/FlexBridge-backups/main-764fb98-2026-11-17.bundle`, `git bundle verify` OK); main himoyalanmagan, master yo'q, integration main'ni o'z ichiga oladi (191 commit oldinda) -> fast-forward. Staging 1964324 dan qayta qurildi. Animatsiyalar: `lib/motion.ts`, `AppStage.tsx`, `CountUp.tsx`, `ThemeProvider.tsx`, `InteractionLayer.tsx`, `globals.css`, `lib/motion.test.ts`.
- Tekshiruv: 157/157, eslint/tsc 0, build OK; korxona 379 -> 157 ms, talaba 333 -> 148 ms.
- Topshirilgan holat / keyingi qadam: main 1964324 ga fast-forward (exact-head CI yashil bo'lgach); 3x PR integration'ga; main'ga keyingi o'tkazish uchun yangi ruxsat kerak.
