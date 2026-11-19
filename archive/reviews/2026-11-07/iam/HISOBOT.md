# IAM-CODEX-001 — backend paketi

2026-11-07, Codex. Foydalanuvchi bo'limlarni ketma-ket tayyorlashni davom ettirishni topshirdi.
Birinchi paket IAMga olindi. Oldingi FIX-CODEX-001 o'zgarishlari va dalillari saqlangan.

**Natija: IAM backend paketi tayyor va regressiyadan o'tdi. Jonli provayder/browser/UI qabuli hali yo'q.**

## Bajarildi

- Telefon/email OTP: 6 raqam, 5 daqiqa, 5 noto'g'ri urinish, 60s resend, eski kodni supersede qilish.
- Target va IP limitlari PostgreSQLda; noto'g'ri urinish biznes xatosi bilan rollback bo'lib ketmaydi.
- OTP faqat shifrlangan holda saqlanadi, API/logda qaytmaydi. HTTPS gateway adapteri va alohida identity worker bor.
- REGISTER/LOGIN/RECOVERY/CONTACT prooflari maqsadga bog'langan, qisqa muddatli va bir martalik.
- Signup uchun kontakt tasdig'i, 18+ deklaratsiya va joriy shart/privacy versiyalarini qabul qilish kerak.
- Qayta berilgan raqam boshqa shaxsga eski contact/user/profile/rolelarni ko'chirmaydi: yangi user yaratiladi,
  eski contact retire qilinadi, eski sessiya va auth versiyasi bekor qilinadi. Eski ma'lumot eski userda qoladi.
- Eski hisobga telefon OTPning o'zi bilan kirish/parol tiklash mumkin emas. Mustaqil eski omil kerak.
- Login MFA ticketlari, TOTP tekshiruvi, sezgir rolning MFA enrollment cheklovi va serverdagi auth_version ishlaydi.
- Passkey options/registration/authentication/revoke: py_webauthn orqali haqiqiy imzo, RP/origin, UV,
  user handle, challenge, first-party va sign-counter tekshiruvlari. Secret private key serverda saqlanmaydi.
- Recovery: 8 ta bir martalik backup kod, HMAC saqlash; OTP + oldingi backup/TOTP orqali reset.
  Omil yo'q holat PENDING_REVIEW qoladi, shaxsiy ma'lumot/reset ruxsati berilmaydi. Case statusi maxfiy header tokeni bilan.
- Reset barcha eski sessiya, MFA va backup kodlarini revoke qiladi; sezgir rol qayta MFA o'rnatishi kerak.
- Mavjud yangi passkey sessiyasi bilan yo'qolgan TOTPni almashtirish mumkin; o'zga actor passkeyini revoke qilib bo'lmaydi.
- Auth javoblari no-store/no-referrer, request body limiti, TOTP/passkey o'zgarishlariga audit qo'shildi.
- Identity worker 30s oralig'ida chegaralangan batch bilan expired OTP ciphertextini tozalaydi,
  24 soatdan eski auth challenge/continuation/rate holatini primary DBdan o'chiradi. Backup/WAL purge alohida OPS ishidir.

## API va migration

Canonical IAM: API-015, 016, 018, 019, 020, 021, 022, 023 hamda xavfsizlik API-060/061.
API-017 institution onboarding bo'lib EDU doirasida qoladi. Passkey/contact/recovery-complete
qo'shimcha endpointlari `backend/IAM.md`da yozilgan.

`0003_iam_flows`: 2 yordamchi jadval va IAM ustunlari qo'shiladi; runtime 98 jadval.
Eski canonical 0002dan upgrade alohida sintetik DBda tekshirildi (`upgrade.json`):
2 mavjud user, parol xeshlari va shifrlangan TOTP saqlandi; mavjud MFA sessiyasi saqlandi;
MFA yoqilishidan oldingi PASSWORD sessiyasi revoke bo'ldi; oddiy password-only sessiya saqlandi.
Mavjud foydalanuvchi DBsi va oldingi SQLite fayllariga tegilmadi.

API inventari: **132 canonical shartnomadan 27 explicit handler, 105 ta 501** (`contracts.json`).
Bu butun mahsulot tayyorligi foizi yoki barcha acceptance mezonlari bajarildi degani emas.

## Sinov dalillari

**107 passed, 1 framework deprecation warning, 345.29s**. Exit 0; failure/error/skip — 0.
Runner vaqti 348.81s. `summary.json`, `junit.xml`, `pytest_stdout.txt` saqlangan.

46 ta yangi IAM/HTTP test holati qo'shildi. Real PostgreSQL 17.11da:

- expired/wrong/replayed OTP, resend, parallel consume, rate-limit va 24h cleanup;
- recycled-phone isolation, OTP-only takeover/recoveryni rad etish;
- MFA ticket/bearer farqi, 5 noto'g'ri urinish, auth_version bilan stale ticketni rad etish;
- haqiqiy P-256/COSE/CBOR kriptografik WebAuthn positive va noto'g'ri origin/RP/UV/signature/handle/counter;
- passkey revoke, expiry, cross-origin/malformed javob va mavjud passkey bilan TOTPni almashtirish;
- ikkinchi Python process yaratgan verification proofni asosiy API qabul qilishi;
- **native uvicorn + alohida worker + lokal HTTPS gateway** orqali OTP → signup → login → auth/me.

Lokal TLS gateway test transporti bo'lgan, real SMS/email yuborilmagan. WebAuthn testlari
software authenticator orqali haqiqiy imzo bilan bajarilgan, browser/hardware authenticator bilan emas.

Oraliq sinovlar yashirilmagan: ilk 101 testda yangi MFA qoidasiga moslanmagan eski membership
kutilmasi 403/200 tafovutini ko'rsatdi; test endi MFA o'rnatilmaguncha 403, keyin 200ni tekshiradi.
Keyingi 105-test yurishida TOTP 30s chegarasi aniqlandi; verifier bir qadam driftni qo'llaydigan
qilindi va RFC 6238 vektorlari bilan tekshirildi. Yakuniy 107-test yurishi xatosiz.
Oldingi dalillarda sintetik bearerlar redaktlangan; production secretlar ishlatilmagan.

## Chegara va davom nuqtasi

- Real SMS/email gatewayning tijoriy provayderi hali tanlanmagan/ulanmagan. Adapter shartnomasi mavjud;
  provider credentiallarini repository yoki chatga qo'ymasdan deployment environmentga kiritish kerak.
- Haqiqiy brauzer passkey UX, frontend va Docker runtime staging bu paketda sinalmagan.
- Omilsiz qo'lda recovery tasdig'i OPS/moderatorning keyingi identity review oqimidir; avtomatik ruxsat yo'q.
- Qolgan CAN/ORG/EDU/JOB/APP/INT/LOG/RAT/BIL/OPS funksiyalari ushbu IAM paketi bilan yakunlandi deb belgilanmaydi.
- Navbatdagi paket: CAN — profil/malaka, CVni profilga ulash, yo'l buferi va canonical availability APIlari.

Sozlash va yangi request/response oqimlari: [IAM qo'llanmasi](../../../backend/IAM.md).
