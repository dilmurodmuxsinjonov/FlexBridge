# ORG-CODEX-002 — 24 soatlik kontaktga bog'langan invitationlar

2026-11-08, Asia/Tashkent; Codex. Foydalanuvchi “DAVOM ETTIR” dedi.
ORG-CODEX-001ning saqlangan yakuniy dalili avval qayta tekshirildi: 179 passed,
source hashlar mos. So'ng invitation paketi alohida bajarildi. Boshqa agent,
commit/push yoki deploy yo'q; oldingi o'zgarishlar saqlandi.

**Yakun: 198 passed, 1 framework deprecation warning, 217.28s, exit 0.**
Failure/error/skip 0. Runner 218.75s; `summary.json`, `junit.xml`, stdout/stderr.
19 ta yangi invitation holati umumiy suitega qo'shildi. Dastlabki maqsadli yurish
17 passed / 1 warning / 26.56s edi; qolgan ikki holat va qo'shimcha assertionlar
yakuniy 198-test yurishida tekshirildi. Sonlar ustma-ust, qo'shib hisoblanmaydi.

## Bajarildi

- API-074: current scoped OWNER/MFA va VERIFIED organization; explicit
  HR/HOST_COORDINATOR/MENTOR/BILLING invitation. OWNER/platform role va self-invite rad.
- Kriptografik random 32-byte token, 24h expiry, purpose-bound HMAC token/contact
  digestlari; raw token/destination DBga yozilmaydi. Token faqat creation javobida.
- API-024: minimal anonymous preview, hech qanday target shaxs/kontakt/evidence yo'q.
  API-025: authenticated MFA, current verified IAM contact va mavjud account/contact
  pin mosligi; contact boshqa hisobga ko'chsa eski taklifni qabul qila olmaydi.
- Organization/invitation row lock bilan parallel accept bitta membership/grant.
  Idempotent repeat yangi vakolat bermaydi; expired qabul qilingan token uchun
  faqat o'zining hali ACTIVE membership/granti qaytarilishi mumkin.
- Supersede, explicit revoke, expired/revoked/accepted public preview 404;
  inviterning current OWNER/user/org statusi qayta tekshiriladi.
- Membership revoke pending issuer/target/contact invitationlarini ham yopadi.
  Old accepted/pending link revoked rolni qayta ochmaydi. Faqat revocationdan keyin
  berilgan fresh explicit invite o'z rolini qayta faollashtirishi mumkin;
  inactive legacy boshqa grantlar yashirin qaytmaydi.
- Canonical URL token segmenti outer ASGI middleware orqali Uvicorn access logidan
  niqoblanadi; no-store/no-referrer va body limiti saqlandi. Oversized va unhandled
  error yo'llari ham testlangan. Tashqi proxy loglarini bu ASGI middleware boshqarmaydi.

## Migratsiya va kontraktlar

Head `0005_org_invitations`, runtime 99 jadval. Yangi dependency yo'q.
Role/channel/target pin ustunlari, pending contract CHECK, inviter/org composite FK,
token unique/contact indexlar. Legacy pending role-less tokenlar revoke qilinadi,
accepted tarix o'zgarmaydi. Mavjud user/membership/grantlar ko'chirilmaydi yoki yaratilmaydi.
Deploymentdan oldin upgrade va legacy linklarni qayta berish zarurligi qo'llanmada yozilgan.

`contracts.json`: **132 canonical / 45 explicit / 87 ta501 / missing0**.
API-024/025 hozir organization takliflarini bajaradi; institution invitation hali yo'q.
Bu handler soni butun acceptance yoki mahsulot tayyorligi foizi emas.

## Qo'shimcha dalil

- Native uvicorn + HTTP + disposable PostgreSQL **6/6** (`native_smoke.json`):
  creation, private preview headers, accept, idempotent retry, accepted preview 404,
  current role read. Captured native access logda raw token yo'qligi tasdiqlandi;
  `access_log_redacted.txt` faqat niqoblangan pathlarni saqlaydi.
- Synthetic populated0004 -> 0005 (`check_upgrade.py`, `upgrade.json`): pending
  role-less invitation revoke, accepted history va ikkala row saqlandi; grant yaratilgani0.
  Alohida migration bazasi yakunda o'chirildi. Production backup/restore dalili emas.
- TestClient/native verified-contact yozuvlari fixture sifatida berildi. Jonli SMS/email
  yuborish sinalmadi; IAMdagi OTP/contact verification alohida oldingi regressiyalarda mavjud.
- `source_hashes.json`, Python AST parse, OpenAPI inventari va `git diff --check`
  tekshirildi. Git LF/CRLF bildirishnomalari xato emas. Yakuniy admin katalogida
  disposable test DBlar qolmagani tasdiqlandi; ishga tushirilgan server to'xtatildi.

Qo'llanma: `backend/INVITATIONS.md`; READMEning current migration va ORG qo'llanmasi yangilandi.

## Chegara va keyingi qadam

Creation javobi ulashiladigan API havolasi; SMS/email yuborilgan degani emas.
Contact matching authoritative IAM yozuviga tayanadi; carrier registry yoki insonning
huquqiy shaxsini sertifikatlamaydi. Proxy/gateway loglari uchun alohida redaction kerak.
Browser/UI, real delivery/scanner/S3 staging, Docker/DR va to'liq pilot qabuli yo'q.

Keyingi `ORG-CODEX-003`: mustaqil tekshiruv bilan qo'shimcha OWNER/ownership
transfer/recovery. Oddiy staff invitation OWNER bermaydi. Keyin EDU va qolgan canonical
modullar. Pilot tayyor emas.
