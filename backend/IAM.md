# IAM — hisob, kirish va xavfsizlik

Bu paket backendni to'ldiradi. Jonli SMS/email provayderi, haqiqiy brauzer/hardware passkey
va foydalanuvchi interfeysi alohida integratsiya/qabul ishidir. Testlar real odamlarga xabar yubormaydi.

## Sozlash

`alembic upgrade head` yangi `0003_iam_flows` migratsiyasini qo'llaydi. Oldingi kanonik
`0002_security_runtime` ustiga ustunlar/jadvallar qo'shiladi; user/profile yoki ledger o'chirilmaydi.
Oldin MFA yoqilgunga qadar ochilgan PASSWORD sessiyalari active MFAga ega hisoblarda revoke
qilinadi; mavjud MFA sessiyalari va oddiy password-only hisob sessiyalari saqlanadi.
Eski prototype SQLite uchun oldingi qo'lda data migration talabi saqlanadi.

Kerakli environment kalitlari (`infra/.env.example`):

- `AUTH_HMAC_KEY`: kamida 32 belgili tasodifiy sir; OTP, continuation va rate-limit digestlari uchun.
- `MFA_ENCRYPTION_KEY`: 32 baytli Fernet key; TOTP, vaqtinchalik OTP va continuation payloadlari shifrlanadi.
- `AUTH_DELIVERY_URL`: tekshiriladigan sertifikatli HTTPS gateway; `AUTH_DELIVERY_TOKEN`: uning server siri.
- `TERMS_POLICY_VERSION`, `PRIVACY_POLICY_VERSION`: amalda chop etilgan shart/maxfiylik versiyalari.
- `WEBAUTHN_RP_ID`: tegishli domen; `WEBAUTHN_ORIGIN`: aniq HTTPS origin. Faqat developmentda
  `localhost` va `http://localhost:8000` ishlatish mumkin. Productionda HTTPS talab qilinadi.

Ushbu kalitlar yo'q bo'lsa production uchun soxta kod, console SMS yoki avtomatik tasdiqlash yo'q.
API secret va verification tokenlarni URLga kiritmang. IAM javoblari `Cache-Control: no-store`
va `Referrer-Policy: no-referrer` bilan keladi; auth request body 128 KiB bilan cheklangan.

OTP uchun alohida worker ishga tushiriladi:

```powershell
Set-Location D:\FlexBridge\backend
$env:OUTBOX_EVENT_TYPES='AUTH_OTP_DELIVERY'
$env:OUTBOX_WORKER_KEY='identity'
python -m app.workers.outbox
```

Compose ichida bu `identity-worker` servisidir. Oddiy outbox worker FILE_SCAN/REFUNDni ishlaydi.
Ajratilgan worker uzoq PDF tekshiruvi ortida OTP kutib qolishini kamaytiradi. Ikkala worker
heartbeati readinessda tekshiriladi. Bo'sh navbatda polling 0.5s; muvaffaqiyatli ish ortidan
navbatdagi vazifa darhol olinadi. Ko'p worker SKIP LOCKED/lease/fencing orqali birga ishlaydi.

## SMS/email gateway shartnomasi

Worker `POST {AUTH_DELIVERY_URL}/otp` yuboradi:

```json
{"request_id":"challenge UUID","channel":"PHONE","destination":"+998...","code":"6 digits","ttl_seconds":300}
```

Headerlar: `Authorization: Bearer <gateway token>`, `Idempotency-Key: <challenge UUID>`.
Javob: `{"request_id":"shu UUID","status":"ACCEPTED"}`. Bu provayder yuborish uchun qabul
qilganini bildiradi; telefon ekraniga yetib borganini sertifikatlamaydi. EMAIL kanali shu
shartnomadan foydalanadi. Gateway bir xil request_id qayta kelganda xabarni takror yubormasligi,
birinchi natijani qaytarishi kerak; retryda qolgan ttl_seconds kamayishi mumkin.
Redirect va TLS tekshiruvini o'chirish ishlatilmaydi. Provider xatosida outbox pending/retry qoladi.

## Ro'yxatdan o'tish va qayta berilgan raqam

1. `GET /api/v1/auth/options`: joriy shart versiyalari va OTP chegaralari.
2. `POST /api/v1/auth/challenges`: `channel`, `destination`, `purpose="REGISTER"`.
   Javob 202: `challenge_id`, `QUEUED`, `expires_in=300`, `resend_after=60`. Kod qaytmaydi.
3. Worker provayderga yuboradi. `POST /auth/challenges/{id}/consume`: `purpose`, `code`.
   Javobdagi `verification_token` 5 daqiqalik, bir martalik va maqsadga bog'langan.
4. `POST /auth/register`: display_name, password (12..1024 belgi), adult_confirmed,
   verification_token, terms_version, privacy_version. Faqat CANDIDATE yaratiladi.

Telefon xalqaro `+` formatiga, email kichik harflarga normalizatsiya qilinadi. OTP 5 daqiqa,
ko'pi bilan 5 noto'g'ri urinish. Resend 60s; oldingi kod bekor bo'ladi. Bir destinationga
turli maqsad/IPdan ham jami 5 so'rov/10 min, IPga 20/10 min chegarasi bor. Bu boshlang'ich
backend limitlari; deploymentda ishonchli proxy va qo'shimcha abuse nazorati ham sozlanadi.

Yangi raqam egasi REGISTERni tanlasa, **yangi user/profile** yaratiladi. Eski contact qatori
boshqa odamga ko'chirilmaydi: eski qiymat tombstone qilinadi, contact revoke bo'ladi, eski
sessiyalar/auth continuation versiyasi bekor qilinadi. Eski CV/kundalik/grantlar eski userda
qoladi. Yangi egaga eski user IDsi yoki ma'lumoti qaytarilmaydi. Eski shaxs o'z mustaqil
paroli/passkeyi bilan hisobiga kira oladi. Qayta signup orqali yaratilgan yangi hisob bilan
eski ma'lumotni avtomatik birlashtirish bajarilmaydi.

## Kirish va MFA

`POST /auth/login` user_id yoki channel/destination va password oladi. Ixtiyoriy LOGIN OTP
proof ham berilishi mumkin, lekin OTPning o'zi eski hisobga sessiya bermaydi. Noto'g'ri
login umumiy xato qaytaradi; IP 30/10 min va normalizatsiya qilingan identifier 10/10 min
bo'yicha PostgreSQL counterlari mavjud. Noma'lum hisob uchun ham Argon2 tekshirish xarajati bor.

MFA yoqilganida parol tasdig'idan keyin 202 va `mfa_ticket` keladi; access_token berilmaydi.
`POST /auth/mfa/verify` ticket va TOTP kodini oladi. Ticket 5 daqiqa, 5 noto'g'ri urinish va
bir martalik; u oddiy Bearer sifatida ishlamaydi. Login requestda to'g'ridan-to'g'ri to'g'ri
TOTP berish ham qo'llab-quvvatlanadi.

OWNER, BILLING, COORDINATOR, MODERATOR, SUPPORT, FINANCE, ADMIN uchun MFA talab qilinadi.
Hali MFA o'rnatmagan ushbu actorning PASSWORD sessiyasi faqat account/security/session
boshqaruviga cheklanadi; biznes amali 403 beradi. Grant berilgan eski PASSWORD sessiyasi
ham shu cheklovga tushadi. TOTP yoki passkey tasdiqlangach qayta kirish kerak.

TOTP 30 soniyalik qadamda ishlaydi; kod kiritishdagi chegara/soat farqi uchun bir oldingi va
bir keyingi qadam ham tekshiriladi. Chegaradan ikki qadam uzoq kod rad etiladi. Implementatsiya
RFC 6238 SHA-1 test vektorlarining 6 xonali natijalari bilan tekshiriladi.

`PATCH /me/security` + `POST /me/security/totp/confirm`: parol tekshiriladi, avval pending
TOTP siri bir marta beriladi, keyin haqiqiy kod bilan tasdiqlanadi. Pending tasdiq 5 daqiqa
amal qiladi. Mavjud MFAni o'zgartirish uchun joriy kod yoki oxirgi 5 daqiqadagi MFA sessiyasi
kerak. Faktor o'zgarsa auth_version oshadi, eski sessiyalar va eskirgan MFA ticketlar yaroqsiz
bo'ladi. TOTP/passkey o'zgarishlari auditga yoziladi; secret auditda bo'lmaydi.

## Passkey / WebAuthn

- `POST /me/security/passkeys/options`: joriy password va zarur step-up. Javobda
  `ceremony_token` hamda `public_key` browser options bor.
- Brauzer `navigator.credentials.create()` natijasini
  `POST /me/security/passkeys/verify`ga yuboradi. Akkount, challenge, RP, origin,
  user presence/verification va public key py_webauthn orqali tekshiriladi.
- `POST /auth/passkeys/options`: ixtiyoriy mfa_ticket. Anonim login discoverable credential
  bilan ishlaydi, boshqa foydalanuvchilarning credential IDlari ro'yxat qilinmaydi.
- Brauzer `navigator.credentials.get()` natijasi `POST /auth/passkeys/verify`ga yuboriladi.
  User handle, haqiqiy imzo, UV, challenge va counter tekshiriladi. Cross-origin iframe
  ceremonylari qabul qilinmaydi. Muvaffaqiyatli nonce takror ishlatilmaydi.
- `DELETE /me/security/passkeys/{credential_id}`: egasi va step-up tekshiruvi bilan revoke.

Ceremony 5 daqiqa va 5 noto'g'ri urinish bilan cheklangan. Authenticatorning private keyi
serverga kelmaydi; DBda public key, credential ID va sign counter saqlanadi. DB digestini
Bearer sifatida yuborish yoki public keyni bilish sessiya bermaydi. Synced passkeylarning
zero-counter xulqi library/spec bo'yicha qo'llab-quvvatlanadi; musbat counter ortga qaytsa
verifier rad etadi. Haqiqiy browser/hardware UX alohida stagingda tekshirilishi kerak.

## Contact va recovery

Mavjud hisobga boshqa kontakt qo'shish uchun CONTACT challenge o'z sessiyasidan so'raladi,
keyin proof + current_password/step-up `POST /me/contacts`ga beriladi. Proof boshqa actor
yoki REGISTER maqsadi uchun ishlamaydi.

MFA yoqilgach `POST /me/security/recovery-codes` 8 ta yuqori entropiyali backup kodni
bir marta ko'rsatadi. Ularni foydalanuvchi xavfsiz joyga saqlaydi; server faqat HMAC digest
saqlaydi. Yangi to'plam eski to'plamni bekor qiladi. Ularni xodimga/chatga bermang.

1. RECOVERY OTPni tasdiqlang.
2. `POST /auth/recovery`: verification_token + mavjud recovery_code yoki TOTP.
3. Mustaqil omil bo'lsa READY_TO_RESET va 5 daqiqalik reset_token keladi. Omil bo'lmasa,
   mavjud/mavjud bo'lmagan hisob uchun bir xil PENDING_REVIEW oqimi; ma'lumot yoki reset ruxsati yo'q.
4. `GET /auth/recovery/{id}` uchun `X-Recovery-Token` kerak; boshqa case ko'rinmaydi.
5. `POST /auth/recovery/{id}/complete`: reset_token + new_password. Parol yangilanadi,
   barcha eski sessiyalar, MFA omillari va backup kodlar bekor bo'ladi. Sezgir rol qayta MFA
   o'rnatmaguncha biznes amallariga kira olmaydi. Reset token yana ishlamaydi.

Qo'lda identity review — OPSning keyingi ishi. PENDING_REVIEW o'z-o'zidan APPROVED bo'lmaydi.
Telefon qayta boshqa hisobga bog'lansa, avvalgi kontaktga chiqarilgan proof/reset token
eski shaxsning hisobini ochish uchun ishlamaydi.

Identity worker har 30 soniyada cheklangan batch bilan eskirgan raw OTP ciphertextini
tozalaydi; 24 soatdan eski auth challenge/continuation va rate counterlarni asosiy DBdan
o'chiradi. Bu backup/WAL nusxalarining fizik o'chirilishini tasdiqlamaydi; ularning saqlash
muddati infrastruktura/OPS ishidir. Har batch ko'pi bilan 1000 yozuv; lookup/rate amallari
indeks orqali odatda O(log N), batch tozalash xarajati tanlangan K yozuvga bog'liq.

## Dalillar

`tests/security/test_iam.py` va `test_iam_http.py`: OTP expiry/replay/resend/concurrency,
recycled phone, recovery, MFA scope, kriptografik WebAuthn positive/negative va native
API + alohida worker + lokal TLS gateway. Lokal gateway real SMS/email yubormaydi.
Test natijalari `reviews/2026-11-07/iam/`da saqlanadi. Bu testlar butun R1 yoki jonli
SMS/hardware passkey qabulini anglatmaydi.

Rasmiy texnik manbalar: [py_webauthn registration](https://duo-labs.github.io/py_webauthn/registration.html),
[authentication](https://duo-labs.github.io/py_webauthn/authentication.html),
[RFC 6238](https://www.rfc-editor.org/rfc/rfc6238.html),
[NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html),
[OWASP password recovery](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
