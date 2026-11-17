# Backend bo'limi — agentlar uchun qoidalar

Ildizdagi `AGENTS.md` (muzlatilgan `main`, faqat integration branch, `.env`/`.data`/sirlarni o'qimaslik va yubormaslik) bu yerda ham to'liq amal qiladi. Bu fayl faqat **backend ishiga** xos qo'shimchalar.

## Egalik chegarasi

- Backend vazifasi faqat `backend/**`, `docs/backend/**` va kerak bo'lsa `contracts/**` ga tegadi.
- `frontend/**` ga tegmang. Javob shakli o'zgarsa — PR tavsifida yozing va frontend uchun alohida vazifa qoldiring (`frontend/AGENTS.md`).
- Yangi yoki o'zgargan endpoint `contracts/r1_api_matrix.csv` va tegishli `docs/backend/<domen>/*.md` da aks etsin.

## Tuzilma

| Yo'l | Nima |
| --- | --- |
| `app/main.py` | FastAPI ilova, router'larni ulash (`app.include_router`) |
| `app/api/v1/*.py` | HTTP qatlami (auth, candidates, organizations, opportunities, governance, billing, chat, …); `app/api/dependencies.py` — aktor konteksti |
| `app/services/*.py` | Biznes qoidalari va vakolat tekshiruvlari (74 modul) |
| `app/db/*.py` | Jadval ta'riflari: har bir modulda `register_tables(metadata, types)`, `app/db/storage.py` dan chaqiriladi |
| `app/core/` | Konfiguratsiya, IAM xavfsizligi, audit, readiness, HTTP kesh |
| `app/adapters/` | Antivirus (ClamAV), S3 saqlash, identity yetkazish |
| `app/workers/` | `outbox`, `identity_delivery`, `pdf_check`, `refunds`, `telegram_bot_poller` |
| `alembic/versions/` | Migratsiyalar; joriy head `0023_chat_messaging` |
| `tests/security/` | Regressiya testlari (haqiqiy PostgreSQL) |

Domen spetsifikatsiyalari indeksi: [`docs/backend/README.md`](../docs/backend/README.md). Ishga tushirish va testlar: [`backend/README.md`](README.md).

## Buyruqlar

```powershell
# repo ildizidan, loyiha .venv interpretatori bilan
python -m pip install -r backend/requirements.txt
python scripts/check_publish.py
$env:FLEXBRIDGE_TEST_ADMIN_URL='postgresql+psycopg://TEST_USER:TEST_PASSWORD@127.0.0.1:5432/postgres'
python -m pytest backend -q
```

CI: `.github/workflows/backend-tests.yml` (Python 3.12, PostgreSQL, MinIO test serveri). Bitta faylni tez tekshirish: `python -m pytest backend/tests/security/test_<nom>.py -q`.

## Majburiy qoidalar

1. **Yangi jadval** qo'shilsa:
   - yangi Alembic migratsiya (revision id **≤ 32 belgi** — `alembic_version.version_num` varchar(32));
   - `app/db/<modul>.py` da `register_tables`, `app/db/storage.py` dagi ro'yxatga ulash;
   - head va jadval sonini tekshiruvchi testlarni yangilash (hozir `0023_chat_messaging`, `flexbridge` sxemasida **138** jadval; ~7 ta testda assert).
2. **Vakolat**: har bir o'zgartiruvchi amal servis qatlamida aktor, rol va tashkilot/muassasa doirasini tekshiradi; yo'q bo'lsa — aniq kodli xato (`*_REQUIRED`, `*_FORBIDDEN`). UI tekshiruvi vakolat emas.
3. **Xato kodlari** barqaror va katta harfli (`ACTIVE_ENTITLEMENT_REQUIRED`, `TIMETABLE_SLOT_OVERLAP`); frontend ularni `lib/errorText.ts` da matnga aylantiradi — yangi kod qo'shsangiz PR'da yozing.
4. **Pul va fayllar**: provayder/AV/saqlash mavjud bo'lmasa vakolat berilmaydi, to'lov tasdiqlanmaydi, fayl CLEAN bo'lmaydi (fail-closed). To'lov faqat imzolangan provayder webhook'i bilan tasdiqlanadi.
5. **Test**: har bir xatti-harakat o'zgarishi `tests/security/` da test bilan; ruxsat yo'qligi (403/404) va chegara holatlari ham.
6. **Sirlar**: `.env`, `.data`, tokenlar, parollar loglarga, testlarga yoki jurnallarga yozilmaydi.

## Ish oxirida

- `docs/journals/01_AI_XOTIRASI_VA_QOIDALAR.md` («Joriy holat» + «Ish tarixi» oxiriga yozuv) va `03_BOSQICHLAR_VA_HOLAT.md`; texnik tanlov o'zgarsa `02_TEXNIK_MODELLAR.md`.
- PR bazasi: `integration/r1-agent-collaboration`. Merge faqat exact-head CI yashil bo'lganda.
