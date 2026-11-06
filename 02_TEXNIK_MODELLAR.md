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
