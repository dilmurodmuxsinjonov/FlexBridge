# FlexBridge — texnik modellar va vositalar

Faqat model va texnologiya tanlovlari reestri. Ishni qismlarga bo'lish qoidasi 01-faylda, bajarilish holati 03-faylda yuritiladi. Hujjatda yozilgan texnologiya hali loyihada o'rnatilgan yoki ishlatilgan degani emas.

## Texnik hujjatda ko'rsatilganlar

Manba: `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf`, 2–7-sahifalar.

| Yo'nalish | Model / texnologiya | Tanlov holati |
| --- | --- | --- |
| Ma'lumotlar bazasi | PostgreSQL; int4range, GiST, EXCLUDE, composite FK, deferred constraintlar | 1.4 hujjatida belgilangan; sxema fayli mavjud emas |
| DB ulanishlari | PgBouncer | 1.4 hujjatida belgilangan |
| Sessiya va ruxsat keshi | In-memory / Redis invalidation keshi | Hujjatda variantlar bor; yakuniy variant aniqlanmagan |
| Fayl saqlash | S3-mos xususiy obyekt ombori | Hujjatda belgilangan; provayder tanlanmagan |
| Antivirus | ClamAV / clamd, asinxron worker | Hujjatda belgilangan |
| PDF strukturaviy tekshiruvi | Python pypdf | Hujjatda belgilangan |
| Kuchaytirilgan autentifikatsiya | Passkey / TOTP | Hujjatda ko'rsatilgan; kutubxona tanlanmagan |
| Favqulodda bildirishnoma | Telegram / SMS | Hujjatdagi kanallar; provayder tanlanmagan |

## Hali aniqlanmagan tanlovlar

| Yo'nalish | Model / texnologiya | Holat |
| --- | --- | --- |
| Frontend | Belgilanmagan | Yangi stek o'zboshimchalik bilan tanlanmaydi |
| Backend tili va framework | Belgilanmagan | pypdf tilidan butun backend tili chiqarib olinmaydi |
| Worker va navbat | Belgilanmagan | Asinxron worker talabi bor, vositasi yo'q |
| Hosting va deploy | Belgilanmagan | Provayder va platforma aniqlanmagan |
| To'lov | Belgilanmagan | Provayder tanlanmagan |
| Mobil ilova | Belgilanmagan | Keyingi bosqich |
| Mahsulot ichidagi AI model | Belgilanmagan | Mavjud o'qilgan hujjatlarda aniq model berilmagan |
| Ishlab chiquvchi AI / model | Belgilanmagan | Boshqa AI asosiy ishni bajaradi; nomi hali berilmagan |
| Tekshiruvchi AI / model | Codex / aniq model nomi noma'lum | Foydalanuvchi tekshiruvchi va tuzatuvchi rolini belgilagan |

Versiyalar manbalarda berilmagan; taxminan yozilmaydi. Keyingi aniq tanlov foydalanuvchi qarori yoki tegishli manba IDsi bilan qayd etiladi.
