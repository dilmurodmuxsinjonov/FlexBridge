# FlexBridge — hujjatlar xaritasi (`docs/`)

Kod `frontend/` va `backend/` da, hujjatlar shu yerda. Ish turiga qarab faqat kerakli qismni o'qing.

## 1. Qayerdan boshlash

| Kim / qanday ish | Avval o'qing | Keyin |
| --- | --- | --- |
| Har qanday AI agent | Ildizdagi [`AGENTS.md`](../AGENTS.md) (`Q-017`: faol branch `main`, PR + CI) | [`journals/01_AI_XOTIRASI_VA_QOIDALAR.md`](journals/01_AI_XOTIRASI_VA_QOIDALAR.md) — qoidalar va «Joriy holat» |
| Frontend ishi | [`frontend/AGENTS.md`](../frontend/AGENTS.md) | [`frontend/README.md`](frontend/README.md), [`frontend/DIZAYN_VA_HARAKAT.md`](frontend/DIZAYN_VA_HARAKAT.md) |
| Backend ishi | [`backend/AGENTS.md`](../backend/AGENTS.md) | [`backend/README.md`](backend/README.md) (domen spetsifikatsiyalari), [`../backend/README.md`](../backend/README.md) (ishga tushirish, testlar) |
| Staging va server deploy | [`operations/STAGING_VA_E2E.md`](operations/STAGING_VA_E2E.md), [`operations/SERVER_DEPLOY.md`](operations/SERVER_DEPLOY.md) | [`../scripts/build_server_package.py`](../scripts/build_server_package.py), [`../scripts/e2e/README.md`](../scripts/e2e/README.md) |
| Antigravity (Codex limiti tugaganda) | [`protocols/ANTIGRAVITY_MASTER_PROTOCOL.md`](protocols/ANTIGRAVITY_MASTER_PROTOCOL.md) | [`protocols/ANTIGRAVITY_HANDOFF.md`](protocols/ANTIGRAVITY_HANDOFF.md) |

## 2. Papkalar

```
docs/
├── README.md                     # shu xarita
├── journals/                     # AI xotirasi va loyiha jurnallari (asosiy fayllar — joriy holat + so'nggi yozuvlar)
│   ├── 01_AI_XOTIRASI_VA_QOIDALAR.md   # qoidalar, «Joriy holat», ish tarixi (LOG-156 dan)
│   ├── 02_TEXNIK_MODELLAR.md           # texnik stek va joriy texnik qarorlar
│   ├── 03_BOSQICHLAR_VA_HOLAT.md       # bosqichlar va so'nggi yozuvlar (LOG-170 dan)
│   ├── 04_TAKLIFLAR_VA_TANLOVLAR.md    # takliflar va foydalanuvchi qarorlari
│   ├── 05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md
│   └── FlexBridge_kelgusi_bosqichlar.md
├── protocols/                    # agentlar o'rtasida topshirish
│   ├── ANTIGRAVITY_MASTER_PROTOCOL.md
│   └── ANTIGRAVITY_HANDOFF.md
├── frontend/                     # frontend arxitekturasi, dizayn va harakat qoidalari
├── backend/                      # 27 ta domen spetsifikatsiyasi + indeks
└── operations/                   # staging, E2E va serverga yuklash qo‘llanmasi (SERVER_DEPLOY.md)

archive/                          # serverga kirmaydigan tarix, review, taqdimot va v1.3 spetsifikatsiyalar
├── ai-history/journals/          # LOG-001..169 va eski joriy-holat arxivi
├── ai-history/protocols/         # Handoff tarixiy bo'limlari
├── reviews/                      # 2026-11-07..15 audit va review yozuvlari (+ legacy_tests SHA-256)
├── presentations/                # texnik topshiriq PDF, investor va ustoz uchun materiallar
└── specs/v1_3/                   # 1.3 spetsifikatsiyalar arxivi
```

## 3. Arxiv (`../archive/`)

| Fayl | Ichida |
| --- | --- |
| `../archive/ai-history/journals/01_ish_tarixi_LOG-001-035.md`, `…036-091.md`, `…092-162.md` | 01-faylning LOG-155 gacha bo'lgan yozuvlari |
| `../archive/ai-history/journals/01_joriy_holat_tarixi.md` | 01-faylning eski «Current LOG-…» qatorlari |
| `../archive/ai-history/journals/02_texnik_qarorlar_2026-11-07_11.md`, `02_joriy_holat_tarixi.md` | 02-faylning vazifa bo'yicha texnik qarorlari va eski holat qatorlari |
| `../archive/ai-history/journals/03_bosqichlar_arxiv_1.md`, `…_2.md`, `03_joriy_holat_tarixi.md` | 03-faylning LOG-169 gacha bo'limlari va eski holat qatorlari |
| `../archive/ai-history/protocols/HANDOFF_tarixiy_bolimlar.md`, `HANDOFF_joriy_holat_tarixi.md` | Handoff'ning LOG-065…076 bo'limlari va eski holat qatorlari |
| `../archive/reviews/`, `../archive/presentations/`, `../archive/specs/v1_3/` | Review yozuvlari, taqdimotlar va eski v1.3 spetsifikatsiyalar |

Arxiv fayllari asl matndan o'zgartirilmasdan ko'chirilgan (bo'laklash skripti har bir asl qator saqlanganini tekshirgan). Ularni tahrirlamang.

## 4. Yozish qoidasi

1. Holatni fayl boshiga yangi «Current LOG-…» qatori qilib qo'shmang — har bir asosiy faylning **«Joriy holat»** bo'limini yangilang.
2. Yangi ish yozuvi: 01-faylda «Ish tarixi» oxiriga (yozuv shakli shu faylda), 03-faylda oxiriga `### sana | LOG-N | …`.
3. Asosiy fayl ~150 KB dan oshsa, eng eski yozuvlarni o'zgartirmasdan yangi `archive/` bo'lagiga ko'chiring va havolasini qo'shing.
4. Frontend hujjati — `docs/frontend/`, backend domen hujjati — `docs/backend/<domen>/`, operatsion yo'riqnoma — `docs/operations/`.
5. Sir, token, parol, `.env` mazmuni yoki shaxsiy dalil hech qaysi hujjatga yozilmaydi.
