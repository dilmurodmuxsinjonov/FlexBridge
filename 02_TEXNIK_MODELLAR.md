# FlexBridge — texnik modellar va vositalar

Faqat model va texnologiya tanlovlari reestri. Ishni qismlarga bo'lish qoidasi 01-faylda, bajarilish holati 03-faylda yuritiladi. Hujjatda yozilgan texnologiya hali loyihada o'rnatilgan yoki ishlatilgan degani emas.

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

## IAM-CODEX-001 — amalda qo'llangan komponentlar (2026-11-07)

- `webauthn==2.8.0`: passkey registration/authentication verifieri, RP/origin/UV/counter va haqiqiy imzo tekshiruvi. Haqiqiy browser/hardware staging hali bajarilmagan.
- `cryptography==50.0.2`: Fernet shifrlash va verifier dependencylari; versiyalar `backend/requirements.txt`da yagona manba sifatida pinlangan.
- Mavjud TOTP primitive stdlib HMAC-SHA1 asosida saqlandi; RFC 6238 test vektorlari, ASCII kod va 30s chegara/drift sinovlari qo'shildi. PyOTP oldingi reja satrida turadi, amalda ushbu paketda o'rnatilgan deb ko'rsatilmaydi.
- OTP provayderining tijoriy brendi tanlanmadi: strict HTTPS SMS/email gateway shartnomasi, encrypted outbox va alohida identity worker implementatsiya qilindi. Tashqi real credentiallar testda ishlatilmaydi.
- Rate-limit, OTP/proof, session auth_version va scoped grantlar PostgreSQLda authoritative. Login/verification yo'llari process xotirasidagi ruxsat keshiga tayanmaydi.

## CAN-CODEX-001 — amalda qo'llangan yondashuvlar (2026-11-07)

- Yangi dependency yoki migratsiya talab qilinmaydi; profil/skill/CV va availability mavjud PostgreSQL sxemasiga yoziladi.
- Matching `1.4.1-can`: 28 kunlik real occurrences, inclusive qoida validitysi, date exceptionlar, ALL/ANY guruhlar va ko'rsatilgan 30min onsite/0min remote buferi. Yarim tun haqiqiy qo'shni sana bilan tekshiriladi.
- R1 request zonasi `Asia/Tashkent` (UTC+05); boshqa zona jim talqin qilinmaydi. Bu mavjud topshiriqdagi mahalliy jadvalning implementatsiya chegarasi; yangi kutubxona qo'shilmadi.
- SQLAlchemy `REPEATABLE READ` bilan request-local snapshot; profil row lock bilan atomik schedule replacement; e'lonlar UUID cursor orqali ko'pi bilan 100 tadan olinadi. Authoritative jadval keshi yo'q.
- `availability_revision` tegishli SQL yozuv ID/updated_atlarining SHA-256 fingerprinti; client bu qiymat bilan tasdiq yoki vakolat olmaydi.
- Private CV link mavjud scan/S3 pipeline ustida; HR sharing, CV-specific retention va haqiqiy purge bu paketdan tashqarida. Qo'llanma: `backend/CANDIDATE.md`.

## ORG-CODEX-001 — amalda qo'llangan komponentlar (2026-11-07)

- `0004_org_onboarding`: normalized tax-ID unique index, immutable `org_verification_submissions` va composite org/case/membership FKlar. Runtime 99 jadval; canonical model statistikasi qayta yozilmadi.
- Faqat ORG rol katalogi migrationda seed qilinadi; foydalanuvchi/grant/operatorni avtomatik seed qilish yo'q. Mavjud role scope yoki normalized tax-ID to'qnashsa upgrade fail bo'ladi, yozuvlar jim birlashtirilmaydi.
- STIR uchun 3–32 ASCII raqam, whitespace/hyphen normalization — cheklangan input implementatsiyasi; rasmiy registry validation yoki huquqiy format tasdig'i emas.
- Organization row lock va revisionli immutable submissions: bootstrap, capability approval, profile change, membership revoke va publish bir org doirasida ketma-ket. Authoritative scoped grant va case-backed capability SQLdan tekshiriladi.
- Moderator/current-MFA/assigned-case chegarasi, linked CLEAN evidencega 60s presign va no-store; ikki weekday due targetida holiday calendar qo'llanmagan. Yangi kutubxona talab qilinmaydi.

## ORG-CODEX-002 — invitation implementatsiyasi (2026-11-08)

- 0005 migration: explicit role/channel va target account/contact pinlar, inviter/org composite FK, pending contract CHECK va token/contact indexlar. Runtime99; yangi dependency yo'q.
- Token `secrets.token_urlsafe(32)`; token va kontakt faqat purpose-bound HMAC bilan saqlanadi. 24h, current verified IAM kontakt va current scoped inviter authority; OWNER oddiy invitationga kirmaydi.
- Canonical token URLi Uvicorn access logidan outer ASGI response/error chegarasida niqoblanadi. Native log tekshiruvi o'tdi; tashqi proxy loglari deployment konfiguratsiyasi bo'lib qoladi.
- Legacy pending invitationlarda role/contact contract yo'q: migratsiya ularni revoke qilib tarixni saqlaydi. Accepted tarix va grantlar qayta talqin qilinmaydi. Qo'llanma backend/INVITATIONS.md.

## OPS-CODEX-001 ? durable dry-run evaluation (2026-11-08)

- 0006_retention_evaluations qo'shimcha helper jadvali: runtime100, canonical94 o'zgarmadi. Composite actor/idempotency unique, immutable UPDATE/DELETE trigger, audit bilan bitta UOW. Yangi dependency talab qilinmadi.
- COMPLIANCE/current-MFA write; COMPLIANCE yoki ADMIN/current-MFA read. Strict integer input; client count requested metadata, haqiqiy scanned/actioned0. Snapshot NOT_CERTIFIED, status EVALUATED_ONLY/NOT_EXECUTED.
- Legal-reviewed custom policy installation va haqiqiy purge yo'q. Legacy fabricated combined appeal410; alohida appellant/reviewer workflow keyingi paket. 0005->0006 upgrade representative populated userni saqladi.
- GitHub bilan ish gh CLI/REST va amalda ishlagan read-only Copilot CLI orqali. read:org kengaytirilmagan; repo-scope fallback ishladi. Qo'llanma: backend/OPERATIONS.md.
