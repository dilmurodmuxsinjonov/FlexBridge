# Antigravity uchun aniq davom ettirish eslatmasi

Yangilangan: 2026-11-10, Asia/Tashkent. Mas'ul: Codex. Ish papkasi D:\FlexBridge.
Bu joriy holat surati; ish boshlashda git status, GitHub va jarayonlarni qayta tekshir.
Codex fix/57-storage-versioning branchida ishlamoqda; bir xil fayllarni parallel
tahrir qilma. Bu fayl Antigravity agenti allaqachon ishlagan degani emas.

## Bajarilgan paket va dalil

PR56 / Issue55: institution onboarding backend paketi birlashtirildi.
Merge: 12cd30746a2412afba326adc3025782638029900. Issue55 yopiq.
Tekshirilgan source: eadac1149ba66d8e34f77190c21f1c6211183a65;
evidence-only final head: 4ffbe96ff4d1463735303844920a253fbcb5500d.
Final head push42679916814: 732 passed /383.64s;
PR42679929206: 732 passed /463.87s. Har birida bitta framework warning.
Old source CI va native subsetlar bilan test sonlarini qo'shib jami deb yozma.

API017/096/097 endi signed-in options, firstCOORD va currentCOORD so'ragan named
TEACHER oqimlarini beradi. Mustaqil assigned moderator qarori va aynan shu revision
uchun shaxsiy rozilik ikkalasi bo'lmasdan grant berilmaydi. Revisions/revoke/private
document view, stale identity/contact/security/original grant, consent expiry,
real session/lock-race va legacy migration tekshirilgan. Teacher-only PASSWORD
assurance saqlanadi; sensitive actorlar current MFA talab qiladi.

Merged PR56 runtime0011/111 edi. Joriy draft branch kodi0012_file_storage_versions/111;
uning qabul tekshiruvlari hali tugamagan. Canonical tarixiy
baseline94 o'zgarmagan.132 canonical route:49 explicit handler/83 placeholder501.
Bu funksional yoki xavfsizlik qabuli foizi emas. Pilot hali tayyor emas.

Dalillar: reviews/2026-11-09/institution_onboarding/HISOBOT.md, source_manifest.json,
native_results.json, red/fix XML va actual read-only Copilot reviewlar.
PR56 yakuniy head CI metadata: reviews/2026-11-10/storage_versioning/pr56_final_ci.json.
Copilot source review qildi; SHA/test/pilot yoki modelni mustaqil sertifikatlamadi.

## Muhit va hali tugamagan o'rnatish

- Antigravity agy CLI avvaldan bor; actual executable --version:1.5.3. Bu CLI
  mavjudlik dalili, Gemini/model yoki loyiha review'i dalili emas.
- Python3.12, Git, gh, Node/npm mavjud. PostgreSQL17.11 test serveri
  localhost55440 da tekshirildi; faqat disposable flexbridge_test_* bazalarini ishlat.
- D:\FlexBridge\.venv yaratildi, backend/requirements.txt o'rnatildi, pip check:
  No broken requirements found. Global boshqa loyiha paketlarini almashtirma.
  Shu interpreter bilan existing migration/password/S3 adapter smoke3 passed8.51s;
  bu yangi lokal full732 rerun deb ko'rsatilmaydi.
- MinIO compose'dagi pinned2025-02-18 relizi D:\Codex\.tools\minio-2025-02-18\minio.exe
  orqali haqiqiy disposable localhost sinovda ishlatildi. Publisher hash tekshirildi.
  ClamAV/PDF/PostgreSQL vositalari D:\Codex\.tools ichida bor; mavjudlik full-stack
  ishga tushdi yoki actual AV signatures yangilandi degani emas.
- Docker4.99.0 va WSL2.7.14 installerlar D:\Codex\Installers\FlexBridge ga yuklandi.
  Docker EXE va WSL MSI SHA256 hamda Authenticode publisher signatures valid.
  MSI yonidagi JSONlarda rasmiy URL/hash manbalari bor. Binarlarni Gitga qo'shma.
- Docker hali o'rnatilmadi: actual installer exit1, prerequisite
  VirtualMachinePlatform disabled. WSL MSIX ham0x80073D28 bilan administrator
  huquqi talab qildi. Bu muvaffaqiyatli install deb belgilanmasin.
- Windows WSL/VirtualMachinePlatform/HypervisorPlatform dastlab Disabled edi.
  D:\Codex\Setup\Enable-FlexBridge-WSL.ps1 uchun native UAC tasdiqlash oynasi
  ochildi, ammo native launch error: The operation was canceled by the user.
  Feature script ishga tushmadi; keyingi CIM tekshiruvida ikkalasi ham Disabled.
  Bu chatdagi davom ettirish topshirig'ini bekor qilish emas; native administrator
  bosqichi tugamagan. Bir xil UAC oynalarini takroran ochma. Launch error:
  D:\Codex\Setup\flexbridge-wsl-launch-error.txt. Reboot berilmagan.

O'rnatishni yakunlash uchun reviewable scripts/setup_windows_dependencies.ps1 bor.
PowerShell parser syntax tekshirildi; elevated system branch hali bajarilmadi.
Avval native administrator oynasini foydalanuvchi tasdiqlashi kerak. So'ng actual
feature natijasiga qarab quyidagini administrator PowerShell'da bajar:

```powershell
powershell -NoProfile -File D:\FlexBridge\scripts\setup_windows_dependencies.ps1 -SystemPrerequisites
```

Bu VMP/WSL featurelarini NoRestart bilan yoqadi va verified WSL MSI o'rnatadi.
Result exit3010 yoki restartNeeded bo'lsa, foydalanuvchi ishlarini saqlab, Windowsni
qo'lda qayta yuklashi kerak. Rebootni o'zboshimchalik bilan boshlama.
Keyin intended oddiy foydalanuvchi PowerShell'ida:

```powershell
powershell -NoProfile -File D:\FlexBridge\scripts\setup_windows_dependencies.ps1 -InstallDocker
```

Bu per-user Docker Desktop'ni D:\Codex\Apps\DockerDesktop ga, WSL data'ni
D:\Codex\Docker\wsl ga so'raydi. Actual joylashuv/CLI tekshiriladi. Windows tizim
WSL qismlarining joyini MSI boshqaradi. Docker Desktop'ni ishga tushirgach haqiqiy
docker info, docker compose version va docker run --rm hello-world ni tekshir.
Engine ishlamasa uni installed/ready deb ko'rsatma. Nested virtualization ehtimolini
actual error asosida tekshir; HypervisorPresent=true bo'lganda CPU CIM false
qiymatidan BIOS virtualization o'chiq degan xulosa chiqarma.

Rasmiy install yo'riqnomalar:
https://docs.docker.com/desktop/setup/install/windows-install/
https://learn.microsoft.com/windows/wsl/install

## Eng yaqin kod vazifasi: Issue57

https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/57
Branch: fix/57-storage-versioning, draft PR58.0012/app tuzatishlari yozildi, ammo
qabul hali yo'q. Explicit bucket/version/ETag, source-pinned scan/GET, source event
fence, snapshots/CV/evidence gates va Enabled readiness implementatsiya qilindi.
Yangi25 storage holati va existing2 private-view testi27 passed44.51s. Sourceafd343a
read-only Copilot review exit0 no concrete version-binding defect; actual CLI context
REVIEW_CONTEXT.md ichida. Old affected240 run239 passed/1 invalid SCANNING fixture
350.06s; fixture actual quarantine reference bilan tuzatildi, candidate44 passed43.39s.
Runtime guard yumshatilmagan. Exact b251644 source complete757 CI push42687285321/PR42687299361
530.01s/513.04s passed. Evidence-only head checks/merge hali keyingi gate.
Yakuniy manba hisobot: reviews/2026-11-10/storage_versioning/HISOBOT.md.
backend/STORAGE_VERSIONS.md va LOG-055 ni o'qi. Eski red/fixture failures saqlangan.

1. reviews/2026-11-10/storage_versioning/PLAN.md va DECISIONS.md ni o'qi. Baseline
   actual localhost MinIO'da trusted provider-admin same-key overwrite qilib,
   old application URL replacement baytlarni, explicit VersionId URL originalni
   qaytarishini ko'rsatdi. Bu public overwrite/auth exploit yoki AV/live proof emas.
2. Yozilgan forward0012 storage_bucket/storage_version_id/storage_etag chegaralarini tekshir.
   Legacy object_version ETag yoki version bo'lishi mumkin: taxminiy backfill yo'q.
   Old proof/history/grants saqlansin. Noma'lum provenance download/yangi approval
   uchun fail closed; yangi upload va explicit revision talab qilinsin.
3. Bog'langan quarantine HEAD->exact-version+ETag read->scanned private PUT->exact-version GET
   zanjirini tekshir. Missing/empty/literal null version, bucket mismatch, provider
   failure hech qachon CLEAN yoki key-only fallback bermasin. Barcha6 signer caller
   va yangi EDU snapshots/reference checks yangilansin. Existing authorization/
   audit/teacher assurance yumshamasin.
4. Outbox claim_token fence avvaldan bor. Reviewdagi taxminni ko'r-ko'rona yangi
   counter bilan almashtirma. Real stale FILE_SCAN token/result va source reference
   o'zgargan holatlarni sinab, eski worker CLEAN nashr qila olmasligini isbotla.
   External PUT retry orphan versions qoldirishi mumkin; exactly-once PUT/purge da'vosi yo'q.
5. Implementatsiyadagi readiness actual bucket versioning Enabled ni o'qishini tekshir. Suspended/absent/outage
   false. Actual MinIO integrationda old/new bytes, version tampering/deletion,
   unversioned/suspended outputs, scan/retry/rollback va scope denialni tekshir.
   Credentials/presigned URLs log/evidencega chiqmasin. CI'da actual testni skip qilma.
6. Native PG va provider integration, populated upgrade, affected old suites,
   pinned read-only peer review, full matching-head CI, dalil/jurnallar, PR va
   matching-head merge bilan paketni yakunla. Keyin Issue59 file-session authority
   paketini bajar; shundan keyin manba talablaridan EDU admission/enrollmentni rejalashtir. Hali student/grades/frontend qurildi dema.

scripts/prepare_test_minio.py repo ichida va CI stepga ulangan. Windows verified
binary bilan actual7 integration holat expanded paketda o'tdi. Linux hash publisher
checksumdan olingan; joriy app o'zgarishlari uchun Linux CI hali bajarilmagan.
Yangi lokal testlarda MINIO_TEST_BINARY muhit qiymati majburiy; yo'qligi skip emas failure.

## Keyingi tasdiqlangan xavfsizlik residuali: Issue59

https://github.com/dilmurodmuxsinjonov/FlexBridge/issues/59
Sourceafd343a pinned review worktree, actual HTTP/native PG probe1 failed33.57s:
completion actual file-row lockni kutdi, logout200 tugadi, lock ochilgach so'rov202,
SCANNING va scan-event1 yozdi. S3 HEAD/presign test double; anonymous/foreign/live/AV
claim emas. Methodga user_id beriladi, actual ActorContext/session final guard yo'q.
Dalil reviews/2026-11-10/files_authority. PR58 bu masalani yopmaydi; uning storage
versiya review/CI natijasi session-authority to'liq ishlaydi degani emas.
PR58 mergedan keyin yangi branch/review bilan3 owner file method/callerni tuzat.
Candidate/CV boshqa self-service actor-id-only yo'llari alohida ochiq audit scope.

## Ishlash qoidalari

01/02/03/04 boshqaruv fayllari va original1.3/1.4 talablar xaritasini o'qi.
Foydalanuvchi Q-013 bo'yicha to'xtatmaguncha kichik paketlarda GitHub bilan davom
ettirishni, Q-014 bo'yicha kerakli vositalarni o'rnatish va eslatma qoldirishni so'ragan.
R2 freelance hozir qo'shilmaydi. Production deployment, haqiqiy to'lov yoki jonli
credential rotation bo'ldi dema. Test uchun magic strings/role flags ishlatma.
Green CI'dan kengroq pilot xulosasini chiqarma;83 placeholder va umumiy AC/live/
frontend/DR ochiq. Yangi paket boshlashdan oldin o'zgargan actual holatni shu eslatma
va jurnallarga yangila; parallel ishlayotgan agent fayllarini qaytarib yuborma.
