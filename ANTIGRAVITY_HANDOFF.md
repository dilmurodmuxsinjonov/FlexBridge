# Antigravity uchun joriy ish va davom ettirish tartibi

Yangilangan2026-11-10, Asia/Tashkent; mas'ul Codex, D:\FlexBridge.
Codex fix/59-file-session-authority branchida ishlamoqda. Bir xil fayllarni parallel
tahrir qilma. Ishni boshlashda git status, GitHub va actual jarayonlarni tekshir.
Bu fayl Antigravity agenti loyiha review'ini bajarib bo'lgan degani emas.

## Qabul qilingan paketlar

- PR56/Issue55 institution onboarding merge12cd30746a2412afba326adc3025782638029900.
  Sourceeadac11, evidence4ffbe96, final732 CI42679916814/42679929206
  383.64s/463.87s passed. API017/096/097, firstCOORD/currentCOORD requestedTEACHER,
  independent assigned review+exact named revision consent, revisions/revoke/private
  evidence, legacy/history va actual actor/lock guards. Additional coordinator,
  recovery/student admission/export/official grade/frontend alohida qolgan.
- PR58/Issue57 private storage versions merge04ffd42e40ac3a475728c203f5da1583023629e4.
  Sourceb251644, final evidence408b3cd4bd5fa14e52221b42a2f49fae5610441e.
  Final757 CI42695810684/42695820221 passed375.77s/507.07s. Actual Linux MinIO+PG
  integration included; AV in those S3 cases explicitly doubled. Runtime0012/111.
  Explicit bucket/VersionId/ETag, no ETag inference, source-pinned scan/GET, outbox
  source/token fences, legacy fail-closed/new revision and Enabled readiness accepted
  within this bounded backend scope. Existing accepted history/grants preserved.

Source/native/CI/red/harness/review dalillari reviews/2026-11-09/institution_onboarding
va reviews/2026-11-10/storage_versioning ichida. PR58 final metadata files_authority/
pr58_final_ci.json da. Native overlapping test sonlarini qo'shib jami deb yozma.
Canonical94 va49 explicit/83 placeholder registrations acceptance foizi emas.
Pilot hali tayyor emas; live IAM/retention/credential rotation/legal identity/DR,
frontend va umumiy R1 AC ochiq. Owner file session authority PR58 doirasiga kirmagan.

## Joriy paket: Issue59 - owner file current-session authority

https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/59
Branch fix/59-file-session-authority merged04ffd42 bazasida. Codex kodni yozdi:
3 owner file method/caller actual ActorContext oladi, business file locks -> current
user/session/auth_version/expiry -> existing sensitive-role MFA -> HEAD/sign/write ->
commit. Initiation guard presign/insert oldidan. Download endi owned file row lock.
Onboarding account_authority helperi o'zgarmagan policy bilan authority.py ga olindi.
Ordinary PASSWORD va current sensitive MFA saqlanadi; user-id-only fallback yo'q.
Worker recorded uploadni keyingi logoutdan mustaqil scan qiladi; fake user session yo'q.

Dalil:

- Oldafd actual row wait+HTTP logout200dan keyin complete202/SCANNING/event1;
  initial1 failed33.57s. Expanded b25115 corrected denial probes all failed19.27s:
 3 method x logout/expiry/auth_version/suspended/late-sensitive-role. First15 run
 12 actual assertion+3 invalid self-grant fixture failure edi; check constraint
 retained, distinct trusted grantor bilan fixture corrected. Public/foreign exploit emas.
- Complete real file-row wait, old download actual table-lock wait; initiation
 service-entry barrier after real HTTP auth, SQL wait da'vosi emas. Storage doubled.
- New27 native passed36.60s: stale denial, reverse actual logout waits, ordinary
 PASSWORD/current MFA, forged session va provider rollback. Bu full785 yoki final
 source/CI qabuli emas. Affected old EDU/storage72 native passed102.01s;
 actual S3 logout->worker-CLEAN/old-token401 testi ham o'tdi.
 Source-pinned review va complete latest-head CI hali keyingi gate.

Keyingi aniq qadamlar:

1. reviews/2026-11-10/files_authority/DECISIONS.md, backend/FILE_AUTHORITY.md va
   joriy test process/JUnitni tekshir. Kodning qolgan regressiyalarini tugat.
2. Source commit/draft PR ochib current full CI chiqar. Izolyatsiyalangan pinned
   source'ni read-only Copilot review'iga ber; hech bir agentga ignored secrets/state
   yoki boshqa agent fayllarini edit qilish vakolati berilmasin.
3. Topilgan concrete nuqson bo'lsa mustaqil red probe/fix; latest actual full native/
   CI, manifest/hisobot/01/02/03 va shu handoffni yangila. Evidence-only latest head
   checks passed bo'lgandan keyin --match-head-commit merge.
4. Candidate/CV va boshqa self-service actor-id-only siblinglar alohida ochiq audit
   scope.59 ularni yopdi deb yozma; keyingi bounded security audit, keyin original
   1.3/1.4 manba talablaridan EDU admission/enrollmentni qur. R2 freelance qo'shma.

## Ish muhiti va tugamagan system install

- D:\FlexBridge\.venv: backend/requirements.txt installed, pip check0. IDE interpreter
  .vscode/settings.json da. Global boshqa loyihalar dependencylarini almashtirma.
- PostgreSQL17.11 binaries D:\Codex\.tools\postgresql-17.11\pgsql\bin,
  test server127.0.0.1:55440. Faqat random flexbridge_test_* disposable bazalar.
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
