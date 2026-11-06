# FlexBridge — bosqichlar va bajarilish holati

Yangilangan: 2026-11-06 — Antigravity (`Gemini 4 Argon (High)`). Hozirgi holat: boshqaruv fayllari tayyor, GitHub repozitoriy ulandi (`Q-008`), `S1.1` bajarilib `Tekshiruvda` holatiga topshirildi, dasturlash hali boshlanmagan.

Holatlar: `Rejada`, `Jarayonda`, `Tekshiruvda`, `Tuzatish kerak`, `Bajarildi`, `Bloklangan`. Bloklangan bandda sabab va ochish sharti yoziladi. Mas'uli tayinlanmagan ish boshlanmagan hisoblanadi.

## S0 — Umumiy ish xotirasini tayyorlash

| ID | Kichik bo'lim | Holat | Mas'ul | Qabul dalili |
| --- | --- | --- | --- | --- |
| S0.1 | Mavjud matnlar va 1.4 texnik PDFni o'qish | Bajarildi | Codex | 3 matn manbasi va 9 sahifalik PDF matni o'qildi |
| S0.2 | AI rollari, mas'uliyat va topshirish qoidalari | Bajarildi | Codex | 01-fayl |
| S0.3 | Texnik tanlovlarni manbadan ajratish | Bajarildi | Codex | 02-faylda ma'lum va noma'lum tanlovlar ajratildi |
| S0.4 | Bosqichlar va qarorlar jurnali | Bajarildi | Codex | 03 va 04-fayllar; fayllar mavjudligi va havolalar tekshiruvi |

## S1 — Talablar va kichik ish paketlari

| ID | Kichik bo'lim | Holat | Mas'ul | Qabul mezoni |
| --- | --- | --- | --- | --- |
| S1.1 | Mavjud talablar va manbalar xaritasi | Tekshiruvda | Antigravity (`Gemini 4 Argon (High)`) | Ish/amaliyot oqimlari, rollar, mavjud AC va bo'shliqlar manba bilan bog'lanadi (`05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md`, Issue `#1`) |
| S1.2 | Yetishmayotgan SQL, 1.3 TZ va atlasni olish yoki tiklash doirasini kelishish | Rejada — navbatdagi | Antigravity (`T-007` qarori kutilmoqda) | Yo'q artefaktlar topiladi yoki ularga bog'liq ish uchun aniq yechim qayd etiladi (`D:\Codex\2026-10-26\sh\outputs\FlexBridge\` topildi, `T-007`) |
| S1.3 | Ochiq texnik tanlovlarni alohida taklif qilish | Rejada | Antigravity (`T-008` qarori kutilmoqda) | Har tanlov 04-faylda; tanlangan vosita 02-faylda aks etadi (`T-008`) |
| S1.4 | Birinchi kichik amalga oshirish paketini tayyorlash | Rejada | Antigravity (`Gemini 4 Argon (High)`) | Chegaralangan maqsad, fayllar, bog'liqlik va sinov mezoni bor; Codex tekshiradi |

## S2 — R1 dasturlash uchun dastlabki ish bo'limlari

Quyidagi bo'limlar reja, bajarilgan funksiyalar emas. Har biri boshlanishidan oldin S2.1.1 kabi kichik vazifalarga bo'linadi. Butun bo'lim bitta katta topshiriqda yozilmaydi. Mas'ullar hozircha tayinlanmagan.

| ID | Bo'lim | Holat | Tekshiruv yo'nalishi |
| --- | --- | --- | --- |
| S2.1 | Loyiha asosi va DB migratsiyalari | Rejada | Manbadagi sxema, constraint va tranzaksiyalar |
| S2.2 | Hisob, sessiya, tashkilot va vakolatlar | Rejada | Rol/scope, o'zini tasdiqlamaslik, revoke |
| S2.3 | Nomzod profili va bo'sh vaqt | Rejada | Vaqt intervallari va istisnolar |
| S2.4 | E'lon, smena va moslik | Rejada | Shartnoma, maosh shartlari, ALL/ANY; AC-039 |
| S2.5 | Ariza, suhbat, taklif, ish boshlanishi | Rejada | Holat o'tishlari va ikki tomon tasdig'i |
| S2.6 | Akademik amaliyot, tayinlov, kundalik | Rejada | Mentor/o'qituvchi ajratilishi, AC-040 |
| S2.7 | Xususiy fayllar, karantin, eksport | Rejada | Scan holati, ruxsat va signed URL; AC-042 |
| S2.8 | Tarif, kvota, to'lov va qaytarish | Rejada | Parallel limit, pul yaxlitligi, dual-control |
| S2.9 | Moderatsiya, audit va saqlash siyosati | Rejada | Scope, o'zgarmas tarix, asoslangan retention; AC-041 |
| S2.10 | Pilotga tayyorgarlik va operatsiyalar | Rejada | Mavjud AC talablari, tiklash, alert va qo'llab-quvvatlash dalillari |

## Mahsulotning uzoq muddatli bosqichlari

Manba: `FlexBridge_kelgusi_bosqichlar.md`. Davrlar loyiha boshlanishiga nisbatan ishchi taklif; kalendar muddat yoki tayyorlik kafolati emas. Barcha R bosqichlar hozir `Rejada`.

| Bosqich | Taklif davri | Ichki bo'limlar | Keyingi bosqichga o'tish sharti |
| --- | --- | --- | --- |
| R1 — Ish va amaliyot | 1–6-oy | Talablarni aniqlash; asosiy oqimlar; bepul pilot; tayyor bo'lsa pullik tarif; fikrlar asosida tuzatish | Asosiy oqimlar, korxona javobi, ikki tomon tasdiqlagan ish boshlanishi va haqiqiy to'lov dalili |
| R2 — Frilans sinovi | 7–9-oy | Tanlangan xizmatlar; paket/buyurtma; bosqichli topshirish; qabul; nizo/qaytarish | Talab va ijrochilar, qabul mezoni, hisob-kitob va huquqiy yo'l tayyor |
| R3 — Hududlar va korporativ dasturlar | 10–12-oy | Hudud tanlash; portfolio; malaka topshiriqlari; korporativ tanlovlar | Pilot sifati, takror buyurtma/to'lov, nizo jarayoni va haqiqiy e'lonlar |
| R4 — Respublika va mobil xizmat | 13–18-oy | Qamrov; mobil ilova; ko'p muassasa; ruxsatli integratsiyalar | O'lchangan talab, alohida jamoa/budjet va xizmat sifati |
| R5 — Xalqaro masofaviy xizmat | 19–24-oy | Bozor va til; mijoz yordami; masofaviy ish/buyurtma; to'lov | Bozor talabi va tegishli shartnoma, soliq, valyuta hamda ma'lumot talablari tekshirilgan |

## Har bir kichik vazifa kartasi

```text
ID / nom:
Bosqich / manba:
Mas'ul AI / model / boshlanish:
Holat:
Maqsad / doira / bog'liq vazifalar:
Tegiladigan fayllar:
Qabul mezonlari:
Bajarilgan qism / qolgan qism:
Tekshiruv dalili:
Codex xulosasi / tuzatishlar:
Keyingi kichik qadam:
```

### S1.1 — Mavjud talablar va manbalar xaritasi (GitHub Issue #1)

- ID / nom: `S1.1` / Mavjud talablar va manbalar xaritasi
- Bosqich / manba: `S1` / `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf`, `FlexBridge_Ustoz_uchun_loyiha_izohi.md`, `FlexBridge_kelgusi_bosqichlar.md`, `FlexBridge_Investorlar_uchun.pptx`, `Oqish_tartibi.txt`
- Mas'ul AI / model / boshlanish: `Antigravity` (`ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76`) / `Gemini 4 Argon (High)` / `2026-11-06T23:21:15+05:00`
- Holat: `Tekshiruvda`
- Maqsad / doira / bog'liq vazifalar: `D:\FlexBridge` katalogidagi barcha manbalarni o'qib, 14 ta rol, ish va akademik amaliyot oqimlari (`S2.2..S2.10`), DB jadvallari/invariantlar (`INV-01..15`), API ruxsatlari, qabul mezonlari (`AC-017`, `AC-039..042`) va yetishmayotgan artefaktlar (`1.3` va `1.4` SQL/Atlas) holatini manbalarga bog'lab xaritaga tushirish (`S0.1..S0.4` ga tayanadi; `S1.2..S1.4` uchun asos bo'ladi).
- Tegiladigan fayllar: `05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md`, `01_AI_XOTIRASI_VA_QOIDALAR.md`, `02_TEXNIK_MODELLAR.md`, `03_BOSQICHLAR_VA_HOLAT.md`, `04_TAKLIFLAR_VA_TANLOVLAR.md`, `.gitignore`
- Qabul mezonlari: Ish/amaliyot oqimlari, 14 rol, mavjud AC/INV talablari va bo'shliqlar aniq manba sahifasi/qatori bilan bog'langan; topilgan `1.3` artefaktlar SHA-256 orqali tekshirilgan; ochiq tanlovlar uchun takliflar `04-fayl`ga yozilgan.
- Bajarilgan qism / qolgan qism: Barcha 5 ta manba (jumladan 27 slaydlik `.pptx` XML/notes) o'qildi; `05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md` tuzildi; lokal `D:\Codex\2026-10-26\sh\outputs\FlexBridge\` katalogidagi 41/41 ta `1.3` artefakt topildi va SHA-256 tekshiruvidan o'tkazildi. Qolgan qism: Codex tekshiruvi va foydalanuvchining `T-007`/`T-008` bo'yicha qarori.
- Tekshiruv dalili: `pypdf` (9 sahifa 1.4 PDF), `zipfile`+`xml.etree.ElementTree` (27 slayd `.pptx`), `checksums.json` SHA-256 tekshiruvi (`40/41` katalogda + `1/41` zip ichida, `reference_errors: 0`), GitHub Issue `#1` va PR.
- Codex xulosasi / tuzatishlar: `Kutilmoqda (Tekshiruvda)`
- Keyingi kichik qadam: Codex `S1.1` ni tekshiradi; foydalanuvchi `T-007` va `T-008` takliflarini tasdiqlagach `S1.2` (`1.3` artefaktlarni `D:\FlexBridge`ga ko'chirish va `FlexBridge_1_4_schema.sql` ni yaratib PostgreSQL/PGlite da sinash) bajariladi.
