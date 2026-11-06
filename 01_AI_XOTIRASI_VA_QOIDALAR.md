# FlexBridge — AI xotirasi va ish qoidalari

Boshlanish: 2026-11-06. Ushbu to'rtta boshqaruv fayli barcha AIlar uchun umumiy ish xotirasidir.

## O'qish tartibi va manbalar

1. Shu fayl — rollar, mas'uliyat, ish tartibi va ish tarixi.
2. `02_TEXNIK_MODELLAR.md` — hujjatlarda ko'rsatilgan texnik vositalar va model tanlovlari.
3. `03_BOSQICHLAR_VA_HOLAT.md` — bajarilgan, joriy va keyingi ishlar.
4. `04_TAKLIFLAR_VA_TANLOVLAR.md` — takliflar va foydalanuvchi qarorlari.

Asosiy loyiha manbalari:
- `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` — 2026-11-05, texnik aniqlashtirishlar, DB/API tuzatishlari va AC-039..042.
- `FlexBridge_Ustoz_uchun_loyiha_izohi.md` — 2026-10-30, mahsulot maqsadi, foydalanuvchilar va biznes oqimlari.
- `FlexBridge_kelgusi_bosqichlar.md` — 2026-10-30, R1–R5 ishchi rivojlanish rejasi.
- `Oqish_tartibi.txt` — materiallar vazifasi va moliyaviy farazlar chegarasi.

Texnik tafovutlarda 1.4 hujjatidagi aniq tuzatish asos bo'ladi. U barcha avvalgi spetsifikatsiyalar o'rnini to'liq bosadi deb taxmin qilinmaydi. Foydalanuvchining keyingi aniq qarori tegishli eski qarorni almashtiradi; o'zgarish tarixi saqlanadi. Ziddiyat yoki yetishmayotgan talab taxmin bilan yopilmaydi, ochiq masala sifatida yoziladi.

## Rollar va mas'uliyat

- Foydalanuvchi — mahsulot egasi; takliflarni tanlaydi va doirani belgilaydi.
- Amalga oshiruvchi AI — asosiy dasturlashni bajaradi; o'z o'zgarishi, xatosi, tekshiruvi va topshirilgan qism uchun mas'ul. Hozircha nomi tayinlanmagan. (2026-11-06 yangilanishi, Q-009: amalga oshiruvchi AI sifatida `Antigravity`, model `Gemini 4 Argon (High)`, sessiya `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` ish boshladi.)
- Codex — tekshiruvchi va tuzatish kirituvchi. Talabga moslikni tekshiradi, xatolarni dalil bilan qayd etadi, zarur tuzatishni kiritadi va qayta tekshiradi. Hozirgi topshiriq doirasida asosiy ilova yozilmaydi.
- Har bir AI o'z haqiqiy nomi/CLI nomi, sessiya identifikatori va mavjud bo'lsa aniq model nomini yozadi. Noma'lum model taxmin qilinmaydi.
- Boshqa AI qatnashgani faqat u amalda ishlagan bo'lsa qayd etiladi. Ushbu tayyorlashda faqat Codex ishladi.

## Majburiy ish tartibi

1. Ish boshlashdan oldin to'rtta fayl va vazifaga tegishli asl manbalarni o'qing.
2. Bitta kichik vazifani ID bilan oling; maqsad, qabul mezoni, mas'ul va tegiladigan fayllarni 03-faylda yozing. Boshqa AI band qilgan faylni kelishmasdan tahrirlamang.
3. Butun tizimni yoki barcha modullarni birdan yozmang. Har topshiriq bitta tekshiriladigan kichik natija bersin: talab → o'zgarish → tegishli tekshiruv → topshirish.
4. O'z ishingiz tugaganda shu faylga o'z nomingiz bilan yozuv qo'shing, 03-fayldagi holatni yangilang. Texnik tanlov o'zgarsa 02-fayl, yangi taklif yoki qaror bo'lsa 04-fayl ham yangilanadi.
5. Amalga oshiruvchi topshirgan ish avval `Tekshiruvda` bo'ladi. Codex qabul mezonini va tegishli tekshiruv natijasini ko'rganidan keyin `Bajarildi` qiladi. Muammo bo'lsa `Tuzatish kerak` holati va aniq kamchilik yoziladi.
6. Tekshirilmagan ishni tayyor, ishlatilmagan modelni ishlatilgan, taklifni foydalanuvchi tanlovi deb yozmang. Buyruq ishga tushmagan bo'lsa sababi yozilsin.
7. Oldingi yozuvlarni o'chirmang; xato yozuvga tuzatish yozuvi qo'shing. Topshirishda qolgan ish va keyingi AI uchun davom nuqtasini ko'rsating.
8. Ish fayllari va natijalar `D:\FlexBridge` ichida saqlanadi. Maxfiy kalit, token, parol yoki shaxsiy dalil faylining mazmunini bu jurnallarga yozmang.

## Loyiha bo'yicha eslab qolish kerak bo'lgan asoslar

- FlexBridge: 18+ nomzodlar uchun vaqt va malakaga mos yarim stavkali ish, umumiy va akademik amaliyot. Frilans keyingi bosqich.
- Ish va akademik amaliyot alohida oqimlar; mentorning ish xulosasi bilan o'qituvchining akademik xulosasi ajratiladi.
- Nomzodning ish qidirishi va arizasi bepul; oddiy ish maoshidan ulush olinmaydi.
- Hozir papkada ilova kodi, ishga tushirish konfiguratsiyasi yoki amaldagi mahsulot dalili yo'q.
- 1.4 PDF 94 jadval, 935 maydon, 214 FK, 14 rol, 40 CAP, 48 sahifa va 42 AC haqida ma'lumot beradi. Bu sonlar hujjat bayonoti, mavjud kod tekshiruvi natijasi emas.
- PDFda tilga olingan `FlexBridge_1_4_schema.sql`, 1.3 to'liq texnik topshirig'i va Baza/API atlasi papkada mavjud emas. To'liq sxema va APIlar taxminan tiklanmaydi.
- 1.4 hujjatidagi retention va huquqiy muvofiqlik bayonotlari mustaqil tekshirilmagan; bu fayllar ularni huquqiy tasdiq deb belgilamaydi.

## Har bir AI uchun yozuv shakli

```text
Yozuv ID / sana-vaqt va vaqt zonasi:
AI / sessiya / model (noma'lum bo'lsa shunday yozing):
Vazifa ID / rol:
Boshlang'ich holat va maqsad:
Qilingan ish / o'zgargan fayllar:
Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
Muammo va cheklov:
Topshirilgan holat / keyingi qadam:
Tekshiruvchi AI / tekshiruv natijasi:
```

## Ish tarixi

### LOG-001 — 2026-11-06, Asia/Tashkent — Codex

- Rol: tekshiruvchi va hujjatlarni tayyorlovchi; modelning aniq nomi sessiyada berilmagan.
- Vazifa: S0.1–S0.4. Foydalanuvchi so'ragan 4 ta boshqaruv fayli tayyorlandi.
- O'qilgan manbalar: yuqoridagi uchta matnli loyiha hujjati va 1.4 PDFning barcha 9 sahifasi matni. Investor taqdimoti va uning PDFi mazmunan tekshirilmagan.
- Aniqlangan cheklov: to'liq SQL sxema va eski atlas yo'q; texnik stekning hammasi ham berilmagan. Farazlar foydalanuvchi qarori sifatida qayd etilmadi.
- Muhit: PDF matnini o'qish uchun lokal Python muhitiga `pypdf` o'rnatildi; bu ilova dependencylari tasdiqlangani degani emas.
- Tekshiruv: yaratilgan fayllarning mavjudligi, UTF-8 o'qilishi va o'zaro havolalari tekshirildi. Ilova kodi yozilmadi va ilova sinovlari bajarilmadi.
- Keyingi qadam: S1.1 — amalga oshiruvchi AI mavjud manbalar bo'yicha talablar xaritasini tuzadi, yetishmayotgan spetsifikatsiyalarni alohida qayd etadi.

### LOG-002 — 2026-11-06T23:30:00+05:00 (Asia/Tashkent) — Antigravity

- Yozuv ID / sana-vaqt va vaqt zonasi: `LOG-002` / `2026-11-06T23:30:00+05:00` (`Asia/Tashkent`)
- AI / sessiya / model: `Antigravity` / `ad6fc32d-f9d1-4120-bfe5-3f332b8fcc76` / `Gemini 4 Argon (High)`
- Vazifa ID / rol: `S1.1` / Amalga oshiruvchi AI
- Boshlang'ich holat va maqsad: S0 yakunlangan (`LOG-001`), Git repozitoriy va masofaviy GitHub (`https://github.com/dilmurodmuxsinjonov/FlexBridge.git`) ulanmagan, `S1.1` (`Mavjud talablar va manbalar xaritasi`) `Rejada — navbatdagi` holatida edi. Maqsad: foydalanuvchi talabi bilan GitHub repozitoriysini ulash (`main` + Issue `#1` + `feature/s1-1-requirements-map` tarmog'i), barcha mavjud manbalarni (jumladan `FlexBridge_Investorlar_uchun.pptx` 27 slayd XML va izohlarini) to'liq o'qib, ish/amaliyot oqimlari, 14 ta rol, invariantlar (`INV-01..15`), qabul mezonlari (`AC-001..042`) va yetishmayotgan artefaktlar xaritasini tuzish.
- Qilingan ish / o'zgargan fayllar:
  - `.gitignore` yaratildi va S0 boshlang'ich fayllari `origin/main` ga yuklandi (`0f71968`).
  - GitHub Issue `#1` (`S1.1: Mavjud talablar va manbalar xaritasi`) ochildi va `feature/s1-1-requirements-map` tarmog'i yaratildi.
  - `05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md` yaratildi: 5 ta manba fayli, 14 ta rol, 8 ta asosiy biznes/texnik oqim (`S2.2..S2.10` kesimida), `INV-01..15`, `AC-017` va `AC-039..042` hamda lokal diskda (`D:\Codex\2026-10-26\sh\outputs\FlexBridge\`) topilgan 1.3 texnik paket auditi manbalar bilan bog'landi.
  - `01_AI_XOTIRASI_VA_QOIDALAR.md`, `02_TEXNIK_MODELLAR.md`, `03_BOSQICHLAR_VA_HOLAT.md`, `04_TAKLIFLAR_VA_TANLOVLAR.md` yangilandi (`Q-008`, `Q-009` qarorlari hamda `S1.2`/`S1.3` uchun `T-007`, `T-008` takliflari kiritildi).
- Tekshiruv buyrug'i yoki usuli / haqiqiy natija:
  - `pypdf` orqali `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (9 sahifa) va `zipfile`+`xml.etree.ElementTree` orqali `FlexBridge_Investorlar_uchun.pptx` (27 slayd va izohlar) to'liq o'qildi.
  - Lokal `D:\Codex\2026-10-26\sh\outputs\FlexBridge\checksums.json` bo'yicha Python skripti orqali SHA-256 tekshiruvi bajarildi: `40/41` fayl ochiq katalogda va `1/41` (`FlexBridge_interaktiv_atlas.html`) `FlexBridge_toliq_texnik_paket_1_3.zip` ichida 100% mos (`reference_errors: 0`).
  - `git status`, `git diff`, `gh issue list` orqali repozitoriy va jurnal fayllari izchilligi tekshirildi. Ilova kodi yozilmadi.
- Muammo va cheklov: `D:\FlexBridge` ichida `FlexBridge_1_4_schema.sql` hali yaratilmagan va `1.3` artefaktlar (`D:\Codex\2026-10-26\sh\outputs\FlexBridge\`) ishchi katalogga ko'chirilmagan; bular `S1.2` doirasida va `T-007` taklifi asosida hal qilinadi.
- Topshirilgan holat / keyingi qadam: `S1.1` `Tekshiruvda` holatiga o'tkazildi. Keyingi qadam: Codex `S1.1` natijasini (`05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md` va `01..04` yangilanishlarini) tekshirib `Bajarildi` qiladi; so'ngra foydalanuvchi `T-007` va `T-008` bo'yicha qaror bergach `S1.2` va `S1.3` bajariladi.
- Tekshiruvchi AI / tekshiruv natijasi: `Codex` / `Kutilmoqda (Tekshiruvda)`
