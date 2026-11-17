# Antigravity uchun joriy ish va davom ettirish tartibi

## Joriy holat (2026-11-17, LOG-190)

> Shu bo'lim har ishdan keyin **yangilanadi** — eski «Current LOG-…» qatorlarini faylning boshiga ustma-ust qo'shish to'xtatildi. Oldingi holat qatorlari o'zgarmagan holda `archive/` papkasida.

- **Integratsiya**: `integration/r1-agent-collaboration` — `a6c3e01` (PR #266). Barcha yangi PR'lar faqat shu branch'ga, exact-head CI yashil bo'lgandan keyin merge qilinadi.
- **main/master**: `764fb98496fa40857acb07844fd09fcafa99b7d6` da muzlatilgan; foydalanuvchining aniq ruxsatisiz hech qanday o'zgartirish yo'q.
- **Koordinator**: `D:/Codex/FlexBridge-agents/coordinator_state.json` — egasi `CODEX`, holati `HANDED_BACK` (2026-11-14).
- **So'nggi ishlar**: LOG-185 universitet ichki tablari va operator bento (#258); LOG-186 e'lonlar moderatsiyasi navbati (#260); LOG-187 staging E2E'dan topilgan xabar/yorliq tuzatishlari (#262); LOG-188 «qurilma» dizayni barcha oynalarda (#264); LOG-189 tugmalar, harakatlar va animatsiyalar qatlami (#266); LOG-190 hujjatlarni bo'limlarga ajratish.
- **Staging**: 2026-11-17 da `a6c3e01` dan qayta qurilgan (`flexbridge-r1`, frontend 127.0.0.1:3000, backend 127.0.0.1:8000). 4 rolli brauzer E2E 21/23 (2 tasi kutilgan biznes tekshiruvi), harakat o'lchovi 11/11, 24 skrinshot toza. Tartib: `docs/operations/STAGING_VA_E2E.md`.
- **Ochiq masalalar (foydalanuvchi qarori)**: to'lov provayderi ulanmagan — buyurtmalar `PENDING_PAYMENT` bo'lib qoladi, korxona e'lonni UI orqali nashr qila olmaydi; `infra/.env` kalitlarini almashtirish (foydalanuvchi o'zi bajaradi); staging `.env` da `BFF_SESSION_SECRET` va `TELEGRAM_BOT_TOKEN` yo'q.
- **Qayerdan boshlash**: hujjatlar xaritasi — `docs/README.md`; frontend ishi — `frontend/AGENTS.md` + `docs/frontend/README.md`; backend ishi — `backend/AGENTS.md` + `docs/backend/README.md`.


## Arxiv

- [HANDOFF_tarixiy_bolimlar.md](archive/HANDOFF_tarixiy_bolimlar.md) — LIVE LOG-076, Q015, LOG-065…LOG-073 tarixiy bo'limlari
- [HANDOFF_joriy_holat_tarixi.md](archive/HANDOFF_joriy_holat_tarixi.md) — eski «Current LOG-…» qatorlari (69 ta)

## Ish muhiti va tugamagan system install

- D:\FlexBridge\.venv: backend/requirements.txt installed, pip check0. IDE interpreter
  .vscode/settings.json da. Global boshqa loyihalar dependencylarini almashtirma.
- PostgreSQL17.11 binaries D:\Codex\.tools\postgresql-17.11\pgsql\bin,
  test server127.0.0.1:55440 (actual accepting02:38). Faqat random flexbridge_test_*
  disposable bazalar. IDE'dagi backend/.data/pg_live uchun pg_ctl status02:38
  no server running; bu katalogga live migration/deploy bajarildi deb yozma.
- MinIO_TEST_BINARY D:\Codex\.tools\minio-2025-02-18\minio.exe. Publisher SHA256
  scripts/prepare_test_minio.py da. Current compose reliziga mos, production release
  support/security sertifikati emas. CI Linux binary ham haqiqiy sinovda ishladi.
- ClamAV1.4.6 oldindan bor edi; freshclam official updater exit0 main/daily/bytecode
  bazalarni D:\Codex\ClamAV\database ga yukladi. Temporary localhost clamd bilan
  actual app INSTREAM adapter benign431-byte PDFni accepted qildi, daemon to'xtadi.
  Bu malware detection coverage/full pipeline yoki ongoing AV service emas.
  Dalil files_authority/CLAMAV_SETUP.md va clamav_local_result.json. System service
  o'rnatilmadi; PR58 mocked-AV tests scope'i tarixda o'zgartirilmaydi.
- agy actual CLI --version1.5.3. Bu Gemini/model/loyiha review'i dalili emas.
- Docker4.99.0 va WSL2.7.14 installerlar D:\Codex\Installers\FlexBridge da, rasmiy
  hashlar va Docker EXE/WSL MSI Authenticode valid. Docker installed emas: actual
  exit1, VirtualMachinePlatform disabled. WSL MSIX0x80073D28 admin required. Native
  UAC launch canceled: feature script ishga tushmadi. Windows featurelar Disabled,
  Docker engine/compose/hello-world hali bajarilmadi, automatic reboot berilmadi.

Administrator bosqichini foydalanuvchi yakunlashi kerak. Bir xil UAC oynasini qayta
qayta ishga tushirma; result/loglarni D:\Codex\Setup dan tekshir. Zarur bo'lsa
administrator PowerShell'da tayyor reviewable skript:

```powershell
powershell -NoProfile -File D:\FlexBridge\scripts\setup_windows_dependencies.ps1 -SystemPrerequisites
```

NoRestart ishlatiladi; exit3010/restartNeeded bo'lsa foydalanuvchi qo'lda reboot qiladi.
Keyin intended oddiy foydalanuvchi PowerShell'ida:

```powershell
powershell -NoProfile -File D:\FlexBridge\scripts\setup_windows_dependencies.ps1 -InstallDocker
```

So'ralgan Docker path D:\Codex\Apps\DockerDesktop, data D:\Codex\Docker\wsl.
Actual CLI joyi/setup exit tekshiriladi, so'ng Docker Desktop, docker info,
docker compose version va docker run --rm hello-world. Engine ishlamasa tayyor dema.
CIM HypervisorPresent=true bo'lsa CPU virtualizationfalse'dan BIOS xulosasi chiqarma.
Rasmiy: https://docs.docker.com/desktop/setup/install/windows-install/
https://learn.microsoft.com/windows/wsl/install

## Ishni yuritish

01/02/03/04 jurnallar va manba talablar xaritasini o'qi. Q-013 bo'yicha foydalanuvchi
stop demaguncha GitHub bilan kichik tekshiriladigan paketlar; Q-014 vositalar va aniq
Antigravity handoff talab qiladi. Actual chaqirilgan agentlarni ko'rsat, modelni taxmin
qilma. Test/probe magic literals, cached role flag, soxta session yoki yashirilgan
failure bilan yashil natija yasama. Production/live money/credential rotation bo'ldi
va pilot_ready=true deb yozma. Yangi current-state dalili bilan handoffni yangila.

## Holat 2026-11-10 (tarixiy — joriy holat yuqorida)

- Master holati: Antigravity Q-016 master succession ostida; Copilot CLI (`1.0.109`) va OpenCode CLI (`1.18.29`) bilan hamkorlikda to'liq avtonom rejimda.
- Oldingi topshiriqlar (API-057, API-058, API-059, API-062, API-063..064):
  * API-057 (Issue #88 / PR #89): Shaxsiy reytinglar ko'rinishi (`GET /api/v1/me/ratings`) $n < 5$ maxfiylik va 14-kunlik double-blind himoyasi bilan to'liq squash-merge bo'ldi (`c22e0222f986ba612dae729a997a3cf120c15383`).
  * API-058 (Issue #90 / PR #91): Bahoga rasmiy e'tiroz bildirish (`POST /api/v1/ratings/{id}/appeals`) va moderatsiya navbatiga qo'yish to'liq squash-merge bo'ldi (`b5ffdc47fa2c46f8ee408d6c8b9d62886f44d188`).
  * API-059 (Issue #92 / PR #93): Bildirishnoma sozlamalari (`PUT /api/v1/me/notification-preferences`) va consent logging to'liq squash-merge bo'ldi (`182608b6bf3f3d19d7fbabf3640ba9a0b037aa99`).
  * API-062 (Issue #94 / PR #95): Maxfiylik va ma'lumotlar sub'ekti huquqlari (`POST /api/v1/me/privacy-requests`) legal hold himoyasi bilan to'liq squash-merge bo'ldi (`b1e53673b9e45ecf91bf7e8d5a9ca4b0b1e9f1de`).
  * API-063 & API-064 (Issue #96 / PR #97): Foydalanuvchi support ticketlari va xabarlashuv tizimi ichki qaydlar segregatsiyasi bilan to'liq squash-merge bo'ldi (`1fc06f0f767863c5a3debca37d2dfc61b6e53608`), Issue #96 yopildi.
- Joriy topshiriq (API-004, API-037, API-038 / Issue #98): Nomzod saqlagan e'lonlar tizimi (`POST /api/v1/saved-opportunities`, `GET /api/v1/me/saved-opportunities`, `DELETE /api/v1/me/saved-opportunities/{id}` / `CAP-006` / `DB-040`) `feature/98-saved-opportunities` tarmog'ida muvaffaqiyatli yakunlandi.
  * Nomzod izolyatsiyasi: Faqat nomzod profili mavjud foydalanuvchilar (`candidate_id_for`) e'lon saqlay oladi; boshqa nomzod nomidan saqlash (`CANDIDATE_ACCESS_DENIED`) yoki boshqaning saqlangan e'lonini o'chirish (`SAVED_OPPORTUNITY_ACCESS_DENIED`) 403 bilan qat'iy to'siladi.
  * Idempotentlik va Toggle (`API-004`): Bir xil e'lonni qayta saqlash xatosiz mavjud yozuvni qaytaradi (200 OK). `toggle=True` yuborilganda esa mavjud bo'lsa o'chiradi (200 OK), bo'lmasa saqlaydi (201 Created).
  * Yopilgan e'lon statusi saqlanishi (`API-037` / CAP-006): Saqlangan e'lonlar ro'yxatida e'lonning original holati (`CLOSED`, `ARCHIVED`) va `is_closed` boolean belgisi ko'rsatiladi.
  * Idempotent o'chirish (`API-038`): `saved_opportunities.id` yoki `opportunity_id` orqali o'chirishni qo'llab-quvvatlaydi; takroriy o'chirish 204 No Content qaytaradi (`repeat204`).
  * Baza va Audit: `flexbridge.saved_opportunities` (DB-040) jadvaliga yoziladi, har bir amal `AppendOnlyAuditStore` orqali `audit_events` jadvaliga qayd etiladi.
  * Test dalillari: 16/16 shartnoma & adversarial testlar (`test_saved_opportunities_api004_037_038.py`, `test_saved_opportunities_adversarial.py`) va 40/40 kanonik regressiya testlari bilan jami 56/56 test 100% yashil o'tdi.
  * Multi-agent reviews: GitHub Copilot CLI 1.0.109 (`reviews/2026-11-10/saved_opportunities/COPILOT_REVIEW.md` - APPROVED) va OpenCode Peer Review (`reviews/2026-11-10/saved_opportunities/OPENCODE_REVIEW.md` - APPROVED).
- `main` branch: Strictly muzlatilgan (`764fb98496fa40857acb07844fd09fcafa99b7d6`). Barcha o'zgarishlar va PRlar faqat `integration/r1-agent-collaboration` bazasiga yo'naltiriladi.
- Alembic head: `0020_placement_exports` (130 runtime tables).
- So'nggi topshiriq (FB-152 / Issue #152): Universitet portali talabalar amaliyot kundaliklarini ko'rib chiqish va baholash tizimi (`feature/152-university-academic-reviews`). API-105, API-106, API-107 Next.js BFF endpoints, AcademicReviewModal.tsx, va 8-bosqichli staging test paketi (`scripts/test_university_academic_reviews_staging.py`) muvaffaqiyatli topshirildi va 100% yashil o'tdi.
- So'nggi topshiriq (FB-176 / Issue #176): Operator portali moliya, solishtiruv va to'lovlarni qaytarish 4-ko'z tasdiqlash xabi (`feature/176-operator-finance-reconciliation-hub`). API-117, API-115, API-078 Next.js BFF endpoints, `/operator` Tab 5 `FINANCE`, 10-bosqichli staging test paketi (`scripts/test_operator_finance_staging.py`) va 17 ta staging to'plam 100% yashil o'tdi. PR #177 birlashtirildi (`3358723`).
- So'nggi topshiriq (FB-178 / Issue #178): Foydalanuvchi markazi qo'llab-quvvatlash tiketlari, GDPR maxfiylik huquqlari va bildirishnomalar xabi (`feature/178-user-support-privacy-notifications-hub`). API-063, API-064, API-062, API-114, API-059 Next.js BFF endpoints, `/nomzod/yordam`, 10-bosqichli staging test paketi (`scripts/test_user_support_privacy_staging.py`) va 18 ta staging to'plam 100% yashil o'tdi (32.36s).
- So'nggi topshiriq (FB-200 / Issue #200 / PR #201): Nomzod to'liq rezyumesi va bevosita PDF yuklash (`API-026-RESUME-DETAILS`, `API-026-DIRECT-UPLOAD`), Korxona rasmiy ma'lumotnomasi (`API-067-DIRECTORY`), va Universitet OTM pasporti hamda hamkorlik shartnomalari (`API-098-DIRECTORY`, `API-101-CREATE`) to'liq yakunlandi va 29/29 staging test to'plamlari 100% yashil o'tdi (`2b8667b`).
- Joriy topshiriq (FB-202 / Issue #202): Universitet xodimi tomonidan dars jadvalini qo'lda kiritish yoki rasmiy shablon (`.CSV` / `.JSON`) asosida yuklash tizimi (`API-098-TIMETABLE`, `/university` 6-tabi `timetable`, va `flexbridge.availability_rules` avtomatik sinxronizatsiyasi) yakunlandi; 30/30 staging test to'plamlari 100% yashil o'tdi.
- Joriy topshiriq (FB-204 / Issue #204): Talaba, Korxona va Universitet uchun alohida E-Imzo tizimi, standartlashtirilgan 1-Hujjat (`Amaliyot Kundaligi` — doimiy tasdiqlanadigan) hamda 2-Hujjat (`Yakuniy Amaliyot Xulosasi` — yakunda alohida tasdiqlanadigan), ikkala hujjatni real `pypdf` A4 PDF va JSON formatida yuklab olish hamda `/nomzod/kundalik`, `/employer`, `/university` portallarida `InternshipDocumentsHub` bilan integratsiya yakunlandi (`1.1`/`1.2` qo'shilmadi). Barcha **31/31 staging test to'plamlari 100% yashil (`77.09s`)**.








- Joriy topshiriq (FB-206 / Issue #206): Barcha sahifalarni alohida ko'rib chiqib, har bir foydalanuvchi turi (`PUBLIC`, `CANDIDATE` `/nomzod/*`, `EMPLOYER` `/employer`, `UNIVERSITY` `/university`, `OPERATOR` `/operator`, `/kirish`, `/royxatdan-otish`) uchun rolga xos dizayn, rang identifikatsiyasi, `Navbar.tsx` moslashuvi va chap yon boshqaruv panellari bilan qayta qurish yakunlandi (`1.1`/`1.2` qo'shilmadi). Barcha 18 sahifa SSR HTTP 200 va **31/31 staging test to'plamlari 100% yashil (`78.94s`)**.


- Joriy topshiriq (FB-212 / Issue #212 / `LOG-158`): Universitet / OTM (`ACADEMIC`) foydalanuvchi turi uchun alohida `/universitet/kirish` (`portal="ACADEMIC"`), `/universitet/royxatdan-otish` (SMS/Telegram + `GET /api/v1/me/contacts` + `/api/bff/university/appointments/[id]/consent` roziligi), `/university/layout.tsx` rol chegarasi va Indigo `Navbar`/`Footer` izolyatsiyasi yakunlandi (`main` muzlatilgan, PR `integration/r1-agent-collaboration` ga). **34/34 staging test to'plamlari 100% yashil (`91.4s`)**. Keyingi qadam: Platforma Operatori (`OPERATOR`) izolyatsiyasi va yakunda 4 ta rol uchun birlashtirilgan bosh `/kirish` hamda `/royxatdan-otish`.


- Joriy topshiriq (FB-214 / Issue #214 / `LOG-159`): Platforma Operatori (`OPERATOR`, `MODERATOR`, `AUDITOR`, `SUPPORT`, `FINANCE`) uchun alohida `/operator/kirish` (`portal="OPERATOR"`), `/operator/layout.tsx` SOC Rol Chegarasi, `operator/page.tsx` va `Navbar`/`Footer` izolyatsiyasi yakunlandi (`main` muzlatilgan, PR `integration/r1-agent-collaboration` ga). **35/35 staging test to'plamlari 100% yashil (`97.82s`)**. Keyingi yakuniy qadam: barcha 4 foydalanuvchi turi uchun yagona birlashtirilgan bosh `/kirish` va `/royxatdan-otish` sahifalarini qurish hamda kirgan foydalanuvchini roliga qarab avtomatik o'z kabinetiga yo'naltirish.


- Joriy topshiriq (FB-216 / Issue #216 / `LOG-160`): Barcha 4 foydalanuvchi turi (`CANDIDATE`, `EMPLOYER`, `ACADEMIC`, `OPERATOR`) uchun alohida izolyatsiyalangan kirish nuqtalarini saqlagan holda yagona bosh `/kirish` (kirgan foydalanuvchi roliga qarab `/nomzod`, `/employer`, `/university` yoki `/operator` kabinetiga avtomatik yo‘naltirish) va 4-bosqichli `/royxatdan-otish` (korxona taklifi, OTM tayinlov roziligi va operator dual-control/2FA tekshiruvi bilan) yakunlandi (`main` `764fb98496fa40857acb07844fd09fcafa99b7d6` muzlatilgan, PR `integration/r1-agent-collaboration` ga). **36/36 staging test to‘plamlari 100% yashil (`116.69s`)**.


- Joriy topshiriq (FB-218 / Issue #218 / `LOG-161`): Videodagi ikki rejimli Skeuomorfik Dashboard dizayn tizimi (`Light Warm` standart + toggle qilinadigan `Dark Obsidian`, 3 ta suzuvchi Obsidian chrome, `framer-motion` `SkeuoPrimitives`, `flexbridge:dock-tab` integratsiyasi) barcha 25 ta public/auth sahifa va 4 ta rol kabinetiga (`/nomzod/*`, `/employer`, `/university`, `/operator`) tatbiq etildi (`1.1`/`1.2` qo‘shilmadi; `main` `764fb98496fa40857acb07844fd09fcafa99b7d6` muzlatilgan, PR `integration/r1-agent-collaboration` ga). `npx tsc --noEmit` (0 xato), Docker `frontend` build, 25/25 SSR HTTP 200 va **36/36 staging test to‘plamlari 100% yashil (`120.21s`)**.
- Joriy topshiriq (FB-218 / PR #219 / `LOG-162`): Real Edge Playwright brauzer va DOM kontrast auditi asosida skeuomorfik dizayn mukammallashtirildi: `globals.css` Light Warm kontrast va `[data-skeuo-dark="true"]` selektori, `SkeuoPrimitives.tsx` (silliq Catmull-Rom Bezier grafigi, 3D glass silindrlar, ixcham stat kartalar), `page.tsx` (yaxlit qidiruv paneli, `Katalog balansi` toggle+kolba Bento bloki, 2 ustunli vakansiyalar va `390x844` mobil overflow=0 tuzatishi), `/kirish` va `/royxatdan-otish` (`Obsidian / Terracotta` brending va yuqori kontrastli rol kartalari) hamda `/nomzod`, `/employer`, `/university`, `/operator` Bento nisbatlari yaxshilandi (`main` `764fb98496fa40857acb07844fd09fcafa99b7d6` muzlatilgan, PR `#219` `integration/r1-agent-collaboration` ga). Playwright Edge audit (`0` mobil overflow, `0` ko‘rinadigan kontrast xatosi), `npx tsc --noEmit` (0 xato) va **36/36 staging test to‘plamlari 100% yashil (`124.8s`)**.
