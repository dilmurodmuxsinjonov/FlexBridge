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
- Amalga oshiruvchi AI — asosiy dasturlashni bajaradi; o'z o'zgarishi, xatosi, tekshiruvi va topshirilgan qism uchun mas'ul. Hozircha nomi tayinlanmagan.
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
