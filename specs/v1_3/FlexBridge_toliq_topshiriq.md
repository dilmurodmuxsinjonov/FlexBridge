# FlexBridge: ishga tayyorgarlik va texnik topshiriq

Versiya 1.3 | 30 oktabr 2026

Talaba va talaba bo‘lmagan nomzodlar uchun maoshli yarim stavkali ish; umumiy va akademik amaliyot. Avvalgi muhokamalardagi foydalanuvchi turlari, rasmiy muassasa mas’uli, kundalik, reyting, ro‘yxatdan o‘tish, email/WhatsApp va barcha audit masalalari birlashtirildi.

Bu hujjatning natijasi - to‘ldirilgan talablar va tekshiriladigan loyiha. Dastur, haqiqiy ma’lumotlar bazasi, integratsiya, shartnoma va tashqi tasdiqlar hali bajarilgan deb hisoblanmaydi. Oldingi 1.2 hujjati tarixiy arxiv, yangi ish uchun shu1.3 va ayni modeldan chiqarilgan atlas ishlatiladi.

Texnik to‘plam: 94 jadval, 923 maydon, 205 FK, 14 rol, 40 imkoniyat, 48 sahifa, 131 bo‘lim, 124 asosiy UI API va 8 yordamchi kontrakt. PDF atlasda barcha jadvallar maydonlari va aloqalari; HTMLda kattalashtirish va ID bo‘yicha havolalar bor.

Texnik indekslar foydalanuvchiga ko‘rsatiladigan interfeys matni emas. DB/CAP/PG/API/AC hujjatda kuzatuv va dasturchi topshirig‘i uchun.


# Mahsulot va xizmat chegaralari

## Versiya va ish holati

Loyiha nomi: FlexBridge, foydalanuvchining 30 oktabr 2026dagi nomlash qarori. Asl taqdimot va masterplan manbalarida avvalgi TalabaIsh nomi ishlatilgan; ushbu yangi to‘plam FlexBridge nomida birlashtirilgan.


FlexBridge 1.3, 30 oktabr 2026. Ushbu hujjat dasturchi, mahsulot egasi, muassasa va korxona vakillari uchun yagona talablar bazasidir. U avvalgi 1.2-versiyadagi talabalarni barcha arizalar uchun majburiy tekshirish qoidasi, alohida audit va email/WhatsApp qo'shimchasini birlashtiradi. Qarorlar hujjatda belgilandi; dastur, shartnomalar, hamkorliklar va tashqi tasdiqlar amalda bajarildi deb hisoblanmaydi.

Asosiy natija: nomzod o'z vaqti va malakasiga mos haqiqiy ishni topadi; tashkilot nomzodni tanlaydi; akademik amaliyot kerak bo'lsa korxona ustozi va muassasa rahbari alohida vakolat bilan qatnashadi. Dastlab Toshkentda talabalar asosiy segment bo'lib qoladi, talaba bo'lmagan 18+ ish izlovchilar umumiy ishlar uchun chetlatilmaydi. Har ikki guruhning faollashuvi va natijasi alohida o'lchanadi.

## Xizmatlar katalogi

| Xizmat | Kim uchun va kirish sharti | Natija va to'lov |
| --- | --- | --- |
| Ish qidirish | 18+ nomzod; tasdiqlangan login, to'ldirilgan asosiy profil | Qidiruv, ariza, suhbat va taklif; nomzodga bepul |
| Maoshli yarim stavkali ish | Tekshirilgan tashkilot, JOB_PUBLISH vakolati | Maosh va smenasi aniq e'lon; korxonaga tarif yoki pilot krediti |
| Umumiy stajirovka | Host talabiga mos nomzod; talabalik faqat e'lon talab qilsa | Mentor bilan muddatli amaliyot; haq holati oldindan ochiq |
| Akademik amaliyot | Amaldagi ta'lim yozuvi, muassasa kelishuvi, vakolatli rahbar | Amaliyot kundaligi va akademik fikr; rasmiy qabul/imzo alohida kelishiladi |
| Nomzod kuzatuvi | Korxonaning aynan shu e'loniga vakolatli HR | Ariza va takliflar; global rezyume eksporti yo'q |
| Muassasa kuzatuvi | Rasmiy tayinlov, faol a'zolik, talaba/ta'lim yozuvi biriktiruvi | Faqat berilgan maqsad doirasidagi holat va kundalik |
| Bildirishnomalar | Saytda; email/Telegram/WhatsApp bo'yicha alohida sozlama | Zarur statuslar va ixtiyoriy tavsiyalar; reklama roziligi alohida |
| Reyting | Faqat tekshirilgan haqiqiy munosabat va belgilangan mezonlar | Dalilli fikr; alohida pilotdan keyin yoqiladi; ishga qabul kafolati emas |

Platforma ish haqini to'lamaydi, nomzodning ishga kirishini kafolatlamaydi va talabaning rasmiy bahosini o'zicha belgilamaydi. Mavjud bo'lmagan HEMIS/OneID imkoniyati tayyor funksiya sifatida sotilmaydi. Frilans buyurtma, 10 foiz ulush, hamyon, escrow, xorijga yollash, to'liq stavka va 18 yoshgacha foydalanuvchi oqimi keyingi ko'lamdir. Bu xizmatlarga talab bo'lsa alohida baho, huquqiy tasnif va qabul mezoni tuziladi.

## Rollar va vakolat

| Rol yoki ishtirokchi | Asosiy vazifa | Kimga ulanadi |
| --- | --- | --- |
| Ish izlovchi | Profil, ko'nikma, bo'sh vaqt, ariza va taklifni qabul qilish | O'z hisobi; ixtiyoriy ta'lim tarixi; ariza bergan korxona |
| Talaba | Ish izlovchi imkoniyatlari va ta'limga bog'liq akademik jarayon | Amaldagi tasdiqlangan enrollment va biriktirilgan rahbar |
| Korxona egasi/vakili | Tashkilot va delegatsiya, tariflar | Vakolati tekshirilgan organization membership |
| HR | Berilgan ish e'lonlari va nomzodlar | Faqat ajratilgan e'lonlar; mentor/billing huquqi avtomatik emas |
| Amaliyot hosti mas'uli | O'rin, sharoit, qabul va mentor tayinlash | INTERNSHIP_HOST va tegishli tashkilot |
| Korxona ustozi | Amaliy ish, kundalik va workplace tasdig'i | Qabul qilingan aniq placement tayinlovi |
| O'qituvchi | O'quv maqsadi va akademik fikr | Muassasa tayinlovi va qabul qilingan academic assignment |
| Muassasa mas'uli | Rasmiy biriktirish so'rovlari va nazorat | Muassasa topshirig'i va belgilangan talabalar |
| Moderator | E'lon, tekshiruv, shikoyat va apellyatsiya | Navbatdagi kerakli dalillar; pul va tizim sirlari ochilmaydi |
| Operator admin | Reliz, ruxsatni dalil asosida ijro qilish, incident | Vaqtli auditlangan kirish; biznes vakolatini o'zicha tarqatmaydi |

Ish beruvchi va host bir tashkilotning ikki imkoniyati bo'lishi mumkin. Ularning e'lon shakli, saralash va placement oqimi ajratiladi. Bitta shaxs bir nechta rolga ega bo'lsa har amal uchun faol doira tanlanadi; rollar global birlashtirilmaydi. O'z kundaligi yoki o'z nomzod natijasini boshqa rol bilan tasdiqlash qat'iy rad etiladi.

## Hisob ochish va ulanish

Kirishda Ish izlovchiman, Ish beruvchiman, Amaliyotga qabul qilaman, O'qituvchiman va Korxona xodimiman yo'llari ko'rsatiladi. Muassasaning rasmiy koordinatori uchun alohida xizmat havolasi bor. Ish izlovchi ichida Talabaman/Talaba emasman tanlovi mavjud. Tanlov hisobot yoki vakolat so'rovini boshlaydi; mustaqil tasdiqlangan rolni bermaydi.

Ish izlovchi email yoki telefonini tasdiqlaydi, 18+ deklaratsiyasini beradi, ism, mutaxassislik/ko'nikma, hudud va mavjudligini to'ldiradi. Talabalik, PINFL va diplom oddiy maoshli ish uchun umumiy majburiyat emas. E'lonning zarur sertifikat yoki ta'lim talabi alohida tekshiriladi. O'zi kiritgan ko'nikma verified deb ko'rsatilmaydi. Talabalik qo'shilsa enrollment tekshiriladi; bitirish profil va umumiy arizalarni yo'qotmaydi.

Korxona STIR, nom, faoliyat va vakil dalilini topshiradi. Mavjud STIR uchun ikkinchi organization yaratilmaydi, mansublik so'rovi ochiladi. Birinchi boshqaruvchini platformaning boshqa vakolatli tekshiruvchisi dalil asosida faollashtiradi. Egani almashtirishda tasdiqlangan tashkilot topshirig'i va yangi vakil tekshiruvi kerak. Oxirgi faol boshqaruvchini o'chirish yoki tushirishdan oldin o'rinbosar yoxud himoyalangan recovery tasdiqlanadi.

Korxona xodimi aniq HR, HOST_COORDINATOR yoki MENTOR taklifini o'z hisobi bilan qabul qiladi. Kontakt mosligi, 24 soat TTL, inviter vakolati, tashkilot statusi va permission scope serverda tekshiriladi. Takror qabul bir membershipni qaytaradi. Owner va billing huquqlari yashirin berilmaydi. Bekor qilingan taklif, membership yoki doira eski sessiya, kesh va eksportda ham ishlamaydi.

Muassasa koordinatori va o'qituvchi rasmiy tayinlov bilan ulanadi. Email domenining o'zi yetarli emas. MVPda vakolatli muassasa topshirig'ini platforma tekshiruvchisi tasdiqlaydi. O'qituvchi tegishli student enrollment va placement assignmentini shaxsan qabul qiladi. Muassasa mas'uli biriktirishni muvofiqlashtiradi; o'qituvchi o'zini talabaga tayinlamaydi. Talabaning universitet almashtirishi eski kirishni yangi enrollmentga ko'chirmaydi.

Tekshiruv navbatlari uchun taklif etilgan birinchi javob: nomzod hujjati 1 ish kuni, korxona 2 ish kuni, muassasa tayinlovi 3 ish kuni. Mas'ul va kutilayotgan amal foydalanuvchiga ko'rsatiladi; muddat oshsa operatorga eskalatsiya bo'ladi. Qo'shimcha hujjat o'sha so'rovning yangi revisionida olinadi, rad tarixi o'chirilmaydi. Bir odamning ikki hisobini bog'lash avtomatik emas; egasi tekshirilgan yordam jarayoni va audit kerak.

## Email WhatsApp va tiklash

Email va parol orqali kirish, email manzilini kod bilan tasdiqlash qo'shiladi. WhatsApp yoki SMSda foydalanuvchi so'ragan bir martalik kod ishlaydi. Uch kanalni birinchi kirishda birgalikda majburlash yo'q. Barcha login kontaktlari user_idga bog'lanadi; keyinchalik boshqa kanal faqat kirilgan va qayta tasdiqlangan hisobdan ulanadi. Kontakt to'qnashuvi ikki hisobni avtomatik birlashtirmaydi.

Kod uchun loyiha standarti: 5 daqiqa, 5 urinish, resend kamida 60 soniya. Limit hisob/kontakt/IP va sutkalik xarajatga bog'liq. Maqsad LOGIN, VERIFY_CONTACT, LINK_CONTACT yoki RECOVERY; kod boshqa maqsadda o'tmaydi. Kanal almashtirish yoki resend avvalgi kodni yaroqsiz qiladi. Delivery callback tasdiq emas. Kod matni loglanmaydi; HMAC va secret pepper bazadan alohida saqlanadi. Parol xavfsiz framework hasheri bilan saqlanadi, buzilgan/keng tarqalgan parollar rad etiladi; yagona omil parol uchun minimum 15 belgi, maksimum kamida 64 belgi qabul qilish loyiha siyosati sifatida olinadi [N01].

Korxona/muassasa boshqaruvi, fayl eksporti, kontakt o'zgarishi, recovery va pul amallari qo'shimcha TOTP yoki passkey bilan himoyalanadi. Emailni tiklash qo'shimcha omilni avtomatik o'chirmaydi. Raqam boshqa shaxsga o'tishi ssenariysida yangi qurilmadan eski hisobning yopiq ma'lumotlariga telefon kodining o'zi yetmaydi: avval bog'langan ishonchli qurilma kaliti yoki boshqa omil, yoxud vakolatli recovery talab qilinadi. Shubhali hisob cheklangan recovery holatiga o'tadi; yangi kontaktni yozib eski hisobni egallash mumkin emas.

SMS va WhatsApp bir raqamda bo'lsa ular mustaqil ikki omil deb atalmasin. WhatsApp rasmiy platformasi, ruxsatli authentication xabari va amaldagi narxlash tayyor bo'lgach yoqiladi [N02]. Hozir tayyor Meta akkaunti yoki kafolatli yetkazish da'vo qilinmaydi. Provayder xatosida cheklangan retry va foydalanuvchi tanlagan boshqa usul bor; hisob sirini yordamchi xodim so'ramaydi.


# E'lon ariza kundalik va reyting qoidalari

## E'lon va muvofiqlik

E'lon turiga PART_TIME yoki INTERNSHIP, nom, vazifa, tashkilot, joy/remote, kontakt vakili, boshlanish, ariza muddati va shartnoma turi kiradi. PART_TIME musbat maosh min/max, UZS, davr va brutto/netto talab qiladi. Uning ish muddati tugashi null bo'lishi mumkin. INTERNSHIP uchun start/end majburiy, is_paid aniq: false bo'lsa salary null va haq to'lanmaydi belgisi, true bo'lsa musbat summa va to'lov shartlari kerak.

Eligibility nomzod maqomidan alohida: ALL_CANDIDATES, VERIFIED_STUDENTS yoki muayyan ENROLLMENT_PROGRAM. Tajriba, zarur ko'nikma va sertifikat talablari ko'rsatiladi. Talabalik dalili faqat student/program talabi bo'lsa arizani cheklaydi. Umumiy stajirovkaga talaba bo'lmagan nomzod ham mos kelishi mumkin. Akademik yo'l faqat tegishli enrollment va muassasa kelishuvi bilan ochiladi.

E'lon DRAFT, PENDING_REVIEW, PUBLISHED, PAUSED, CLOSED, EXPIRED yoki REJECTED bo'ladi. Nashr faqat tekshirilgan tashkilot, faol capability va to'ldirilgan shartlarda. Jiddiy tahrir yangi immutable revision yaratadi; yangi arizalar faqat nashr qilingan versiyaga keladi. Oldingi ariza o'sha paytdagi maosh/jadval nusxasini saqlaydi. Publish, expiry va shikoyatdan keyingi yashirish qidiruv, kesh, xabarnoma va tashqi metadata holatiga birga ta'sir qiladi.

## Bo'sh o'rin va taklif

O'rinlar capacity soni bilan saqlanadi. Arizalar cheklanmagan qabul qilinishi mumkin, ammo qabul qilinadigan takliflar qolgan o'rin bilan atomar tekshiriladi. Standart: OFFERED bosqichi joyni kafolatlamaydi; bu taklif oynasida ochiq yoziladi. Nomzod ACCEPT bosganda row lock bilan o'rin ajratiladi; oxirgi bitta o'rin uchun ikki parallel qabuldan biri o'tadi, ikkinchisi 409 capacity_full oladi. Kafolatli reservation kerak bo'lsa alohida feature va muddati bilan joriy qilinadi; bu MVPda sotilmaydi.

O'rin OFFER_ACCEPTED holatidan tasdiqlangan chiqish yoki bekor qilishda qaytariladi. Nomzod ishni boshlamagani haqidagi bir tomonlama da'vo o'rinni majburan yashirin bo'shatmaydi; nizo pending qoladi. Capacityni band o'rinlardan pastga tushirish rad etiladi. Place soni 0 bo'lsa yangi taklif qabuli yopiladi, HR e'lonni yana ochish uchun capacityni oshiradi.

## Ariza va ish hayoti

Bir candidate/opportunity juftligi uchun bitta application saqlanadi. Har qayta topshirish application_attempt yaratadi. WITHDRAWN nomzod ochiq e'longa qayta yubora oladi; standart kamida 24 soat tanaffus va 30 kunda 3 attempt. HR rad qilgan yoki offer EXPIRED bo'lgan arizani qayta ochish faqat HRning auditlangan taklifidan so'ng. Faol ariza retry bilan ko'paymaydi. Snapshot va eligibility har attemptda yangilanadi, eski nusxa o'chirilmaydi.

Holatlar SUBMITTED, VIEWED, SHORTLISTED, INTERVIEW, OFFERED, ACCEPTED, REJECTED, WITHDRAWN, EXPIRED. Nomzod o'z offerini qabul qiladi; HR uning nomidan ACCEPTED qilmaydi. E'lon deadlinei yangi arizaga tegishli; mavjud offer o'z expiry sanasi bilan boshqariladi. Taklif shartlari o'zgarsa eski qabul yangi shartga ko'chmaydi.

ACCEPTEDdan keyin job_engagement START_PENDING yaratiladi. Ish boshlash hodisasi ikki tomonning mustaqil tasdig'i bilan ACTIVEga o'tadi. Bir tomon tasdiqlamasa UNCONFIRMED, qarama-qarshi javob bo'lsa DISPUTED; bu yozuv tasdiqlangan bandlik hisobiga kirmaydi. Ish ENDED yoki CANCELLED holatida sabab, tashabbuskor va sana bilan yopiladi. Kelmaslikning bir tomonlama xabari avtomatik past reyting yoki qora ro'yxat emas.

Suhbat uchun invitation va vaqt, kanal/manzil, taklif etilgan timezone, qabul/rad/ko'chirish hamda eslatma saqlanadi. Taqvimga tashqi ulanish bo'lmasa ilova ichidagi uchrashuv yozuvi ishlaydi; mavjud bo'lmagan Google Calendar integratsiyasi va'da qilinmaydi. Kontaktlar faqat ushbu jarayonga berilgan ruxsat doirasida ochiladi.

## Jadval mosligi

Vaqtning bazasi UTC tamg'a va foydalanuvchiga Asia/Tashkent ko'rinishi. Haftalik bo'sh vaqt int4range daqiqalarda [start,end); amal sanalari va sanali REPLACE/BLOCK istisnolar bilan. Tun va yakshanba chegarasi haqiqiy qo'shni sanalarga bo'linadi. Intervallar union qilinadi, BLOCK ayiriladi. Remote uchun nol, oflayn uchun foydalanuvchiga ko'rsatilgan qatnov buferi standart 30 daqiqa; bu o'lchangan transport vaqti emas.

Tekshiruv oynasi bugun yoki kelajak startidan 28 kun, end mavjud bo'lsa shunga kesiladi. ALL guruhidagi hamma smena yoki ANYdagi bitta to'liq guruh sig'ishi kerak. Nol real smena hosil bo'lsa UNKNOWN/no_required_occurrences, hech qachon bo'sh tekshiruvdan MATCH qaytmaydi. Javob checked_from/to, algorithm_version, availability_revision va reasonni beradi; checked_to exclusive. Bu butun kelajak ish muddatiga kafolat emas.

schedule_policy STRICT bo'lsa faqat MATCH bilan ariza; konflikt/UNKNOWN aniq sabab bilan rad. NEGOTIABLE bo'lsa nomzod o'z taklif qilgan vaqtini yozib ariza berishi mumkin, HRga CONFLICT yoki UNKNOWN holati yashirilmaydi. Ma'lumot yo'q bo'lsa nol konflikt deb talqin qilinmaydi. Ariza va offer qabulida match qayta hisoblanadi; oldingi ariza jadval o'zgarishi bilan yashirin yo'qolmaydi.

Saralashning MVP formulasi qattiq muvofiqlikdan keyin: ko'nikma mosligi kamayish bo'yicha, so'ng published_at va ID. So'rov bo'yicha eng yangi yoki maosh saralovi foydalanuvchi tanlaydi. Baholanmagan odamni reyting tufayli chetlatish yo'q. Reklama belgilangan, qattiq filtrlarni chetlab o'tmaydi. Formula versiyasi qayd etiladi, yashirin xulq reytingi yo'q.

## Amaliyotni faollashtirish

Placement faqat qabul qilingan INTERNSHIP arizasidan PLANNED bo'ladi. ACTIVE uchun nomzodning shartlar versiyasini qabul qilishi, host tasdig'i va aynan shu tashkilotga tegishli faol MENTOR membership/assignmentning shaxsiy qabuli shart. Academic trackda qo'shimcha tasdiqlangan enrollment, muassasa koordinatori bog'lanishi va o'qituvchi qabul qilgan academic assignment kerak. Ular bo'lmasa umumiy host stajirovkasi akademik hujjat deb ko'rsatilmaydi.

Oddiy PART_TIME uchun amaliyot placementi va kundalik majburiy emas. Ish vaqtini hisoblash alohida ixtiyoriy xizmat sifatida keyingi ko'lamda turadi. Mentor yoki o'qituvchi almashishi eski mualliflikni yangisiga ko'chirmaydi; yangi assignment qabul qilinadi, nomzodga yangi ko'ruvchi va doirasi bildiriladi.

## Kundalik va yakunlash

Har placement/local_date uchun bitta daily_log va uning ko'p task_entries yozuvi bor. Har topshiriq reja vazifasi, natija matni va daqiqani saqlaydi; ixtiyoriy vaqt oralig'i ham bo'lishi mumkin. Kunlik jami entry summasidan hisoblanadi, foydalanuvchi uni alohida oshirib yozmaydi. DRAFTda nol vaqt mumkin; topshirishda ish yozuvi uchun musbat vaqt yoki NOT_WORKED/EXCUSED day turi kerak. Rejalashtirilgan haftalik/kunlik limit placement plan versiyasida beriladi.

Sanalar placement davrida bo'ladi. Kelajakdagi bajarildi yozuvi topshirilmaydi. Oraliq berilsa o'zaro kesishma tekshiriladi; faqat jami daqiqa bo'lsa aniq vaqt mosligini tekshirdim deyilmaydi. Rejadan ortiq jami yoki kech kiritish talabi sabab va vakolatli istisno bilan. Standart retrospektiv topshirish 7 kun; ilgari yopilgan davr uchun amendment so'rovi kerak. Texnik uzilish tasdiqlangan bo'lsa kechikish nomzodga avtomatik jazo emas.

Qoralama avval foydalanuvchiga saqlandi/sinxronlanmagan holatini ko'rsatadi. Maxfiy matnni umumiy service worker keshiga solmaydi; lokal qoralama foydalanuvchi ruxsati bilan, logoutda tozalanadi. Retry idempotent, boshqa qurilmadagi version eski bo'lsa 412 va konflikt ko'rinishi. Tasdiqlangan matn tahriri yangi immutable revision; workplace va academic qarorlar aynan eski revisionda qoladi, yangisi qayta tekshiruv kutadi.

Mentor uchun birinchi ko'rib chiqish nishoni 3 ish kuni; eslatma va muassasa/host mas'uliga eskalatsiya. Sukut avtomatik tasdiq emas. Workplace holati DRAFT/SUBMITTED/APPROVED/RETURNED; academic holati NOT_REVIEWED/REVIEWED/NEEDS_REVISION. O'qituvchi ish joyi tasdig'ini almashtirmaydi; mentor akademik baho yaratmaydi. Korxona sirli fayli yoki mijoz ma'lumoti dalil sifatida majburiy emas; zarur bo'lsa maxfiy, rol bilan cheklangan ilova qabul qilinadi.

Yakun COMPLETED uchun reja bo'yicha kerakli vazifa/soat, qolgan muhim returned yozuvlarning yopilishi, host yakuni va academic trackdagi tegishli o'qituvchi xulosasi kerak. START/END sananing o'tishi o'zi muvaffaqiyatli yakun emas. Nizo bo'lsa COMPLETION_PENDING; bekor qilish CANCELLED sababi bilan. Generatsiya qilingan hisobot PDF axborot ko'chirmasi; rasmiy imzo va baho muassasa bilan kelishilmaguncha ularni taqlid qilmaydi.

## Reyting siyosati

Birinchi pilotda bajarilgan vazifalar, tasdiqlangan soatlar, ko'rib chiqish kechikishi va individual fikr alohida ko'rsatiladi; ommaviy global 100 ball yo'q. Reyting flagi yoqilishidan oldin rubric_version va uning mezonlari mahsulot egasi, host va akademik vakil bilan tasdiqlanadi. Quyidagi boshlang'ich model loyiha taklifi, ishlayotgan tizimning natijasi emas.

Workplace rubrikasi 1–5 shkalada: ish sifati 50%, kelishilgan muddatlarga rioya 25%, muloqot 25%. Akademik rubrika alohida: o'quv natijasi 60%, hisobotning asoslanganligi 40%. Qaror mos assessment davri va log revision/dalilga bog'liq. Excused holatlar muddat mezonida jazo bo'lmaydi. To'liq majburiy mezon bo'lmasa kompozit ball chiqarilmaydi; nazariy og'irliklar yig'indisi 100% bo'lishi shart. Daily log tasdiqi reyting ovozi emas.

Har completed munosabat uchun har tomon/rubrika versiyasiga bitta yakuniy submission va uning revisionlari. Faqat haqiqiy ishtirokchi baholaydi; self-rating va aynan nomzodning o'zini boshqa rol bilan baholashi rad. Ball o'zgarsa oldingi tarix qoladi. Workplace va academic natija bitta songa aralashtirilmaydi; boshqa mutaxassislik yoki formula versiyasi bilan yashirin taqqoslanmaydi.

Ommaviy agregat faqat bir xil rubrika oilasidagi kamida 5 ta yakuniy haqiqiy munosabatdan keyin; ungacha hali yetarli baho yo'q. Ko'rsatilgan o'rtacha bilan n, davr va rubric version beriladi. Bir munosabatni kundaliklar soni bilan ko'paytirish mumkin emas. Yangi foydalanuvchiga 0 ball yozilmaydi. Reyting qidiruv va qabulda avtomatik qora ro'yxat yaratmaydi; MVP saralashiga kirmaydi.

Korxona/mentor haqida nomzod fikri alohida rubrika: e'lon shartlariga moslik, yordam va muloqot. Yakuniy fikrlar ikkala tomon yuborgach yoki taklif etilgan 14 kunlik oynadan keyin birga e'lon qilinadi; haqorat, shaxsiy ma'lumot va aniq nizo moderatsiyaga tushadi. E'lon qilingan ballga 14 kun ichida e'tiroz beriladi, mustaqil moderator nishoni 5 ish kuni. Nizoli submission ochiq agregatdan vaqtincha chiqariladi, n ham qayta hisoblanadi; dalil saqlanadi va natija auditlanadi. Pullik tarif bahoni sotib olish, yashirish yoki salbiy fikrni pulga o'chirish huquqini bermaydi.


# Xizmatlar, sifat va kundalik boshqaruv

## Qidiruv va natija sifati

Qidiruv e'lonning published revisioni, public tashkilot ma'lumoti va skill katalogiga ishlaydi. Nomzodlar bazasi, CV, shaxsiy kontakt yoki kundalik public indeksga kirmaydi. Lotin/kirill yozuvlari, o'/g' apostroflari va UZ/RU nomlar alohida normalizatsiya qilinadi; synonym ro'yxati versiyalanadi. Bir xil normallashgan matn ham qidiruv reytingini sotib olish imkonini bermaydi. Dastlab PostgreSQL to'liq matn/trigram qidiruvi yetarliligi o'lchanadi; tashqi qidiruv xizmati faqat o'lchovdan keyin.

Filtrlar: hudud, masofaviy/ofis/aralash, PART_TIME/INTERNSHIP, maosh oralig'i va davri, kerakli ko'nikma, student-only, smena, nashr sanasi. Turli davrdagi maoshlar xom son bilan taqqoslanmaydi; soat/oy filtri alohida yoki oshkora normallashgan formula bilan. Unpaid internship pullik ish filtriga chiqmaydi. Cursor sort_key + id orqali barqaror; yashirilgan, yopilgan va muddati o'tgan e'lon API, kesh va qidiruvdan chiqariladi. O'xshash e'lonlar org/title/joy/jadval orqali signal beradi; inson ko'rmasdan barcha nusxa o'chirilmaydi.

## Public sahifalar va mobil qulaylik

Har e'lonning bitta canonical tafsilot sahifasi bor. JobPosting metadata faqat tegishli bitta public ish sahifasida, sahifadagi haqiqiy shartlar bilan mos beriladi. Unpaid amaliyot va yopiq ma'lumotga noto'g'ri metadata qo'yilmaydi. validThrough/expiry va o'chirish bir reliz kontraktida. Google ko'rinish kafolati berilmaydi [N03]. Private kabinet login va server vakolati bilan yopiladi; noindex va robots xavfsizlik o'rnini bosa olmaydi [N04].

Har indekslangan bo'lim uchun LOADING, EMPTY, VALIDATION_ERROR, NO_ACCESS, NOT_FOUND, CONFLICT, RATE_LIMITED, PROVIDER_UNAVAILABLE va OFFLINE holatlari dizayn kontraktida bo'ladi. 320px/360px mobil, klaviatura, fokus, matnli xato va label, screen reader, rang kontrasti WCAG 2.2 AA mezonlari asosida tekshiriladi [N05]. Oddiy foydalanuvchi oqimida DB/API kodi ko'rsatilmaydi; texnik indekslar hujjat va operator ma'lumotida. Vaqt default Asia/Tashkent, server UTC; foydalanuvchi sana/vaqt zonasini ko'radi. UZ birinchi til, RU matnlar va formatlar alohida tekshiriladi.

## Xabarlar va yetkazish

Ariza, offer, assignment, review, to'lov holati o'zgargan tranzaksiyada outbox_events yoziladi. Worker uni kamida bir marta yetkazishga mo'ljallanadi; har consumer dedupe key bilan bir natija chiqaradi. Worker yiqilsa pending event qoladi, cheklangan exponential backoff+jitter, maksimal urinishdan keyin operator navbati bor. Foydalanuvchi inboxi asosiy, email/WhatsApp/SMS esa tanlangan va ishga tushgan kanallar. Telegram integratsiyasi alohida bot ulash isboti va sozlamasi bilan keyingi flag; telefon raqamidan Telegram akkauntini taxmin qilish yo'q.

Tashqi xabarda ism, CV matni, kundalik siri, maoshli shaxsiy qaror yoki dalil fayli yuborilmaydi; minimal status va login talab qiladigan havola bor. OTP mazmuni vaqtli shifrlangan yuborish payloadida; uzoq saqlanadigan outbox/audit/logda kod yo'q. Provider message_id, delivered va user verified alohida. Har kanalning kunlik so'rov/xarajat chegarasi va ogohlantirish darajasi bo'ladi; limitga yetish sayt ichidagi xabarni o'chirmaydi. Reklama faqat alohida opt-in va oson unsubscribe bilan.

## Firibgarlik va moderatsiya

Oldindan pul so'rash, yolg'on maosh, ma'lumot yig'ish, bepul katta sinov ishi, boshqa tashkilot nomidan e'lon, yolg'on tasdiq, uyatli yoki majburiy kontent alohida shikoyat kategoriyasi. STIR/vakil tekshiruvi, tezlik limiti, dublikat va shikoyat signali inson ko'rish navbatini yaratadi. Jiddiy xavfda vaqtli hide/suspend sabab va muddat bilan; avtomatik signal yakuniy qora ro'yxat emas. Tashkilot faoliyati to'xtasa yangi publish/offer yopiladi; mavjud taraflarning o'z dalili, nizo va aloqa yo'li saqlanadi.

Har qaror case, reviewer, asos, dalil revisioni va appeal yo'liga bog'liq. Qaror egasi apellyatsiyani yakka o'zi hal qilmaydi. Tahrir sabab moderatsiya davom etsa pullik nashrning 30 kunlik soati hali boshlanmaydi. Soxta e'lon yoki korxona aybi bilan bloklangan davr uchun avtomatik kompensatsiya yo'q; haqiqatda ishlatilmagan xizmatga shartnomadagi qoida qo'llanadi. Reyting yoki shikoyatni pulga o'chirish xizmat emas.

## Tariflar, aktivatsiya va qaytarish

Nomzod, talaba va talaba bo'lmagan shaxs uchun ish qidirish/ariza bepul. Pilot narx taklifi: korxona 599 000 UZS/30kun plan yoki 149 000 UZS/30kun bitta e'lon. Bu tasdiqlangan bozor talabi yoki provayder kotirovkasi emas. Plan kvotasi pilot mahsulot qarorida aniq qotiriladi; cheksiz xizmat deb sotilmaydi. Boshlang'ich taklif: plan davomida 5 ta bir vaqtdagi public e'lon; keyingi nashr faqat slot bo'shagach, alohida post huquqi alohida. Refund va aktiv huquqlar double-spend bo'lmasligi tranzaksiyada tekshiriladi.

| Hodisa | Platforma qoidasi | Baza va nazorat |
| --- | --- | --- |
| Checkout | Narx/currency/mahsulot immutable snapshot; auto-renew OFF | orders, price_versions, payment_attempts |
| Pul tasdig'i | Faqat providerning tekshirilgan server protokoli; brauzer success yetarli emas | payment_events UNIQUE, bir marta ledger |
| POST_30D | 30kun birinchi PUBLISHED vaqtdan; moderation kutish hisoblanmaydi | service_entitlements starts_at/ends_at |
| ORG_PLAN_30D | Birinchi publish yoki egasi ochiq bosgan aktivatsiya; boshlanmagan huquq to'lovdan 90kun ichida aktivatsiya/refund ko'rib chiqiladi | status PENDING_ACTIVATION, reminder va operator case |
| Nashrdan oldin rad | Tuzatish yoki ishlatilmagan order uchun refund so'rovi; boshqa xizmatga majburiy kredit emas | refund va entitlement cancel bir tranzaksiyada |
| Operator uzilishi | Tasdiqlangan yo'qotilgan nashr vaqtini uzaytirish yoki shartga mos proporsional qaytarish | incident + audit + ledger credit; ikki marta kompensatsiya yo'q |
| Takror to'lov | Ikkinchi capture alohida aniqlanadi; yangi huquq yashirin yaratilmaydi; refund navbati | provider reconciliation va dedupe |
| Refund | Captured - successful refunds chegarasi, mustaqil approval, callback bo'yicha yakun | refunds lock, billing_ledger append-only |

Qaytarishning huquqiy majburiy muddatlari, fiskal hujjat va soliqlar operatorning huquqiy shakli va xizmat shartnomasiga mos mutaxassis bilan tasdiqlanadi. 8% moliyaviy rezervni soliq stavkasi deb yozish mumkin emas. Rasmiy merchant kelishuvi, provider test muhiti, callback auth/protokoli va fiskal yo'l yakunlanmaguncha paid_checkout flag OFF [N06, N07].

## Yordam va xizmat darajasi

Taklif etilgan yordam vaqti: dushanba-juma 09:00-18:00, Asia/Tashkent, rasmiy dam olish kunlarisiz. Maqsadlar kafolatli shartnoma SLA emas; pilot natijasida qayta ko'riladi. P1 uchun haqiqiy navbatchi tayinlash reliz sharti; u bo'lmasa saytda 24/7 deb yozilmaydi.

| Navbat | Dastlabki javob nishoni | Eskalatsiya |
| --- | --- | --- |
| P1 hisob egallanishi/pul nomuvofiqligi/katta uzilish | Navbatchi ishga tushgach 30min ack, containment reja | Incident commander; checkoutni flag bilan to'xtatish |
| P2 ariza yoki kundalik asosiy oqimi | 4 ish soati | Operator va mahsulot egasi |
| P3 umumiy savol/tuzatish | 1 ish kuni | Yordam mas'uli |
| Nomzod dalili / korxona / muassasa | 1 / 2 / 3 ish kuni | Due o'tsa boshqa reviewer; sukut tasdiq emas |
| Mentor review / rating appeal | 3 / 5 ish kuni | Host yoki mustaqil moderator |

## Maxfiylik va ma'lumot hayoti

Maqsadlar alohida: account, ish arizasi, akademik kuzatuv, billing, support, xavfsizlik va marketing. Kim ma'lumot egasi/operatori, tashkilot va muassasa nimaga kirishi, asos va o'chirish javobgarligi pilot kelishuvlarida yoziladi. PINFL, pasport, to'liq baholar, dars jadvali yoki mijoz siri barcha foydalanuvchidan olinmaydi. Student proof minimal, operator qarori va muddati ajratiladi. Tashqi email/WhatsAppga chiqadigan data, joylashuv va subprocessor ro'yxati huquqiy ko'rib chiqiladi; lokal hosting loyiha tanlovi, amaldagi qonun bo'yicha universal xulosa emas.

Taklif retention: OTP 5min amal va 24h texnik digest; muvaffaqiyatsiz login xavfsizlik metama'lumoti 90kun; xususiy eksport fayli 24h; ishlatilmagan verification dalili qarordan keyin 90kun; private draft 30kun nofaollikdan keyin ogohlantirib tozalash. Ariza/kundalik, audit, moliya va rasmiy akademik dalillarning yakuniy muddati huquqiy tasdiq talab qiladi. Tasdiqlanmagan muddatni cheksiz yig'ishga aylantirmaslik uchun pilotda faqat kelishilgan toifalar olinadi. Policy version, legal hold, deletion manifest, backup expiry va restore paytida o'chirilganlarni qayta chiqarib yubormaslik testi shart.

## Moliyaviy reja va ishga tayyorgarlik

Avvalgi 6 oylik model: 33,9 mln UZS joriy xarajat + 6 mln bir martalik = 39,9 mln; asoschi mehnati naqd xarajatda 0, shartli iqtisodiy qiymati 8 mln/oy deb alohida ko'rsatilgan. Bu model yangi WhatsApp/email/MFA/recovery/moderatsiya hajmi uchun yangilangan tijoriy taklif emas. Uni yangi ko'lamning kafolatli umumiy byudjeti sifatida ishlatmaslik kerak.

Kengaytirilgan ko'lam uchun sezgirlik misoli: takror hisoblanmagan qo'shimcha aloqa/xavfsizlik/operatsiya rezervi 1-6oyda 0,4; 0,5; 0,6; 0,8; 1,1; 1,3 mln bo'lsa +4,7 mln. Yangilangan fixed [3,4; 4,0; 6,9; 7,3; 7,8; 9,2] mln, jami 38,6 mln; bir martalik bilan 44,6 mln. Nol tushum ssenariysi: 44,6 x 1,2 + 9,2 = 62,72 mln UZS naqd rezerv. Bu ehtiyotkor taxmin, real takliflar va hajm bilan almashtiriladi. Mavjud SMS/hosting xarajatiga aynan bir xizmatni ikki marta qo'shmaslik uchun provider kesimida reconciliation qilinadi. 20% rezerv va 1oy emergency bir-biridan alohida maqsadga ega.

Nomzod soni, haqiqiy active e'lon, 7kun ichida malakali javob, suhbat, 2tomon tasdiqlagan ish boshlanishi, amaliyot davomiyligi, reja yakuni, qaytarish va yordam yuki alohida cohortlarda o'lchanadi. MRRga faqat takroriy plan tushumi; bir martalik post MRR emas. Tushgan pul, hali ko'rsatilmagan xizmat majburiyati va tan olingan tushum alohida. Pullik sotuv boshlanishidan oldin kamida 10 faol korxona bilan suhbat, shartlari aniq 30 haqiqiy e'lon, 2 muassasa bilan akademik pilot ehtiyoji tekshiruvi taklif etiladi; bu raqamlar allaqachon mavjud hamkorlar emas. Nomzod oqimini foydali e'lon/tezkor javobdan oldin katta reklama bilan oshirmaslik; likvidlik yomonlashsa o'sish emas, supply va HR javobi tuzatiladi.


# Arxitektura, baza cheklovlari va reliz

## Tuzilish va texnik tanlov

Modulli monolit: TypeScript web interfeysi, Django/DRF biznes API, PostgreSQL relational tranzaksiyalar, xususiy fayl ombori va outbox worker. Aniq kutubxona versiyasi qurish boshida qo'llab-quvvatlanadigan xavfsizlik patchi bilan lock qilinadi. Oldingi hujjatdagi framework versiyasini tekshirmasdan qayta qotirish yo'q. SQL tanlovi sababi: ariza, o'rin, offer, xizmat huquqi va pulni bitta atomar tranzaksiyada moslashtirish, foreign key va unique orqali dublikatni to'sish. Mikroservis, Kubernetes, alohida search cluster va Redis faqat o'lchangan zarurat bo'lsa qo'shiladi.

Modullar: identity; candidates; organizations; institutions; opportunities; matching; applications; internships; diary; ratings; billing; notifications; moderation; support; privacy; audit. Web har bir role-specific route uchun server kontraktini ishlatadi. Backend serializer faqat whitelist maydonlarni chiqaradi; brauzerda tugmani yashirish ruxsat tekshiruvi emas. Bir shaxsda bir necha membership bo'lsa har so'rovning faol organization/institution/assignment doirasi ochiq beriladi va qayta tekshiriladi.

## ER chizmasini o'qish va baza lug'ati

DB-xxx jadvalning barqaror indeksi; CAP-xxx imkoniyat; PG-xxx sahifa; PG-xxx.Sxx sahifa bo'limi; API-xxx server kontrakti; AC-xxx qabul sinovi. Bular bitta modeldan chiqariladi. Har jadvalda UUID id PK, created_at va updated_at UTC majburiy; created_at immutable. FKlar haqiqiy jadvalga; operatsion jadvallarda soxta target_type + target_id yo'q. Audit/outboxdagi tarixiy object/aggregate key domain FK o'rnini bosa olmaydi. Ular faqat iz va routing uchun.

PK qayta ishlatilmaydi. Default FK deletion RESTRICT; huquqiy retentiondan keyingi delete/anonymize tartibi alohida job bilan bog'liqlikni buzmasdan. Xizmat amallari DB role orqali; audit/ledger, published snapshots va topshirilgan revisionlar update/deletega yopiladi. Trigger yoki alohida append-only DB privilege migratsiyada kiritiladi. Snapshot JSON schema_version va server validatsiyasiga ega; tez-tez qidiriladigan munosabatlar JSONga yashirilmaydi. Hujjatdagi DDL boshlang'ich tuzilma loyihasi; business invariantlarni o'zi to'liq bajaradigan tayyor production migratsiya emas.

## Majburiy tranzaksion invariantlar

| Kod | Cheklov va bajarish joyi | Tekshiruv dalili |
| --- | --- | --- |
| INV-01 | application candidate/opportunity UNIQUE; attempt va revision ayni application e'loniga | FK + service; boshqa e'lon revisioni 422 |
| INV-02 | org invitation/membership/opportunity/HR/mentorning organizationi teng | Write va read scope; cross-org ID bilan403/404 |
| INV-03 | enrollment/appointment/agreement/teacher/supervisionning institutioni teng | Tranzaksion scope validatsiyasi; cross-institution test |
| INV-04 | OFFER ACCEPT: unexpired + allowed state + eligibility + lock capacity | Ikki parallel request, bittasi200 ikkinchisi409; counter va relation birga |
| INV-05 | Offer/capacity release idempotent; occupied_count band relationsga teng | Takror cancel, reconciliation va rollback test |
| INV-06 | Bir orgda oxirgi faol owner yo'qolmaydi; birinchi egani mustaqil reviewer | Membership row locks; parallel ikki revoke testi |
| INV-07 | PART_TIME salary va INTERNSHIP end/is_paid; eligibility faqat zarur ta'limga | Publishdagi cross-table kind check; invalid422 |
| INV-08 | Placement faqat accepted internship; academic ACTIVEda kelishuv/enrollment/teacher/mentor accept | Xom ID yuborib faollashtirish rad; oddiy ishga log404 |
| INV-09 | Log date reja doirasida; minutes=SUM; vaqtlar kesishmaydi, limit va day type mos | Submit tranzaksiyasi; mixed duration/oraliq testi |
| INV-10 | Review ayni placement/revision/assignmentga; self-review yo'q | Wrong assignment403; old revision approval yangisini tasdiqlamaydi |
| INV-11 | Rating criterion ayni rubricga, vazn100, ball diapazonida; rater completed relationda | Rubric activate va submit atomar; versiya bo'yicha qayta hisob |
| INV-12 | Capture/refund currency/amount/orderga mos; refund jami capturedan oshmaydi | Row lock, provider event UNIQUE, duplicate/out-of-order callback test |
| INV-13 | Bir entitlement aktivatsiyasi/ledger/outbox bitta DB commitda | Crash oldin/keyin replay; bir marta biznes natija |
| INV-14 | Joriy revision FK ayni parentdan, current_attempt ayni applicationdan | Migratsiyada composite FK yoki constraint trigger; noto'g'ri parent rad |
| INV-15 | Revoked/expired membership, appointment yoki assignment har read/list/exportda yopiq | Eski sessiya/cache/signed URL va background job test |
| INV-16 | Snapshot/review/ledger/audit tarixini o'zgartirish taqiqlanadi | DB privilege va immutable trigger; admin API bilan update rad |

DDLda to'g'ridan-to'g'ri PK/FK/UNIQUE/CHECK va asosiy indekslar beriladi. INV-01..16dagi ko'p qatorli/boshqa jadvalga bog'liq shartlar service tranzaksiyasi va kerakli composite FK/constraint trigger migratsiyasi bilan yakunlanadi. Ular bajarilmaguncha schema.sqlni productionga qo'llash qabul mezonidan o'tmaydi. PostgreSQL CHECK boshqa jadvaldagi qiymatni doimiy tekshiruvchi vosita sifatida ishlatilmaydi.

## API standartlari va ruxsat

API-xxx jadvali method, path, CAP va data manbasini beradi. Bu UI endpoint kontraktlari; ularning request/response JSON Schema va OpenAPI qurilish bosqichida yoziladi. Sezgir POSTlarda Idempotency-Key, mutable resursda If-Match/version; bir xil key boshqa body bilan409. Saqlash TTL misoli 24h, pul va unique domain yozuvlari uzoqroq dublikatni ham to'sadi. GET mutatsiya qilmaydi. Pagination default20 max100; yirik eksport async job va qayta auth bilan. Upload boshlash/finalize/signed-download ruxsatlari barcha fayl bo'limlari uchun umumiy yordamchi kontraktlar.

HTTP: 400 format; 401 kirilmagan; 403 vakolat yo'q; 404 scope tashqarisidagi yashiriladigan obyekt; 409 holat/capacity/idempotency to'qnashuvi; 412 eski version; 422 biznes validatsiya; 429 limit; 503 tashqi xizmat vaqtincha yo'q. Xato javobi code, foydalanuvchi uchun izoh, maydon xatosi va request_idni beradi; sir/stack trace yo'q. Bir route ichida GET public, POST private bo'lishi mumkin; method darajasida ruxsat bor. Umumiy rol jadvali doimo scope, faol status va real munosabat bilan kesishadi. ADMIN ham o'zi biznes vakolatini sotib ololmaydi.

## Xavfsizlik va tahdid modeli

Asosiy tahdidlar: raqam qayta sotilishi, OTP bombardimon, dublikat hisob, soxta korxona/appointment, IDOR orqali boshqa talaba CV/kundaligi, o'zini boshqa rol bilan tasdiqlash, fayl orqali zarar, callback replay, parallel capacity/refund, auditni o'chirish, bekor scope bilan eksport. Har biriga policy + server guard + DB yoki tranzaksiya + AC testi ajratiladi. OWASP ASVS mezonlari tekshiruv ro'yxati sifatida olinadi, sertifikat deb da'vo qilinmaydi [N08].

TLS, Secure/HttpOnly/SameSite cookie, CSRF, CSP, server-side output escaping, parametrli SQL/ORM, minimal DB rollari, secrets manager, avtomatik secret scan va dependency yangilash shart. IPning o'zi rate limit uchun yetarli emas; hisob/kontakt/qurilma bo'yicha qatlam, progressiv delay, umumiy OTP budjeti. Qattiq hisob lockini boshqaga DoS vositasiga aylantirmaslik [N09]. Private sahifa va API Cache-Control: no-store, shared CDN/service-workerga CV/OTP/log kirmaydi. Signed URL faqat joriy ruxsatdan so'ng, default60s; revoked scope uchun obyekt access proxy yoki juda qisqa TTLning huquqiy qabul qilinishi aniq tanlanadi. Bu 'darhol revoke' da'vosi bilan uzoq URLni birga qo'llamaslik uchun gate.

## Kuzatuv, yuklama va tiklash

Boshlang'ich nishon: 100 bir vaqtdagi sessiya, 10 API request/s, 20 daqiqa aralash realistik workload; auth/checkout tashqi tarmoqdan alohida o'lchanadi. Read API p95<800ms, write p95<1200ms, server5xx<1%, queue p95<60s. Bu 150ming foydalanuvchiga o'lchangan sig'im degani emas. DB connection, query time, CPU, RAM, disk, worker backlog, provider error/cost, stale verification va unreviewed log kuzatiladi. EXPLAIN ANALYZE, real hajmdagi anonim fixture va query-count/N+1 tekshiruvi talab qilinadi.

| Rejim | Nishon | Qabul dalili |
| --- | --- | --- |
| Bepul pilot | Kunlik encrypted backup, RPO<=24h, RTO<=4h | Izolyatsiyalangan restore, FK/row totals/file manifest va 3 asosiy oqim testi |
| Pullik xizmat | PITR/WAL bilan RPO<=15min, RTO<=2h; bank/providerdan yo'qolgan paymentlarni qayta moslashtirish | Haqiqiy restore-run o'lchovi + capture/refund reconciliation; tashqi moliyaviy hodisa yo'qolmaganiga dalil |
| Fayllar | DB backupga mos version/manifest, encrypted offsite copy | Tanlangan private fayl va huquqni tiklab tekshirish |
| Incident | Flag orqali zararli oqimni to'xtatish, commander, aloqa va postmortem | Simulyatsiya va navbatchi javobi |

RPO15min bo'lsa ham oxirgi 15min DB yozuvini yo'qotish mumkin; 'hech qanday tranzaksiya yo'qolmaydi' va'dasi berilmaydi. Moliyaviy hodisalar provider/bankdan reconciliation bilan tiklanadi. Backupni saqlash va restore testini xuddi production huquqlaridan alohida operator bajaradi [N10].

## Migratsiya, CI va reliz ketma-ketligi

Avvalgi students yozuvini candidate_profilesga user UUIDni saqlab ko'chirish; ta'lim ma'lumotini enrollments tarixiga ajratish. Talaba bo'lmagan nomzodga soxta student row yaratmaslik. Dublikat STIR/kontakt/applicationni oldin aniqlash, avtomatik yo'qotmasdan review navbati. Dry-run row count, orphan FK, uniqueness, money sum va scope tekshiruvi; xato bo'lsa reliz to'xtaydi.

Schema expand -> ma'lumot backfill -> dual-read tekshiruvi -> yangi write -> eski ustunni keyingi relizda contract. Production reset yoki tarixni o'chirish migratsiya yo'li emas. CI: lint/type, unit business rules, haqiqiy PostgreSQL integration, permission matrix, concurrent accept/refund, API contract, selected security, accessible UI, build va dependency/secret scan. Deploy oldin backup/restore dalili; keyin smoke tests va rollback qarori. Schema rollback har doim drop bilan emas; forward-fix yoki mos eski app ishlay olishi kerak [N11].

## Amalga oshirish bosqichlari va egalik

| Bosqich | Natija va egasi | Tugash sharti |
| --- | --- | --- |
| G0 ko'lam va huquq | Mahsulot egasi + yuridik/buxgalter: xizmatlar, kontrakt, retention, narx/kvota | Mustaqil xizmat va data-role qarorlari yozilgan; pullik/akademik majburiyat tasdiqlangan |
| G1 hisob va baza | Dasturchi: identity, candidate, org/institution, minimal DDLni haqiqiy migratsiyaga aylantirish | Cross-scope va raqam recovery testlari; original UUID/history ko'chishi |
| G2 ish oqimi | Dasturchi + HR UAT: publish, schedule, application, interview, offer, jobconfirm | Capacity parallel test va nonstudent/student UAT; free pilot boshlanishi |
| G3 amaliyot | Dasturchi + host + muassasa: assignment, reja, diary, ikki review | Nomzod/mentor/teacher alohida UAT; self-review va revoked testlari |
| G4 operatsiya | Operator + dasturchi: moderation, support, privacy, notification, restore | Navbat, incident drill, backup restore, WCAG va load dalili |
| G5 billing | Moliya + merchant + dasturchi | Callback/refund/reconciliation/fiskal, PITR va real test order; paid flag keyin yoqiladi |
| G6 reyting | Mahsulot egasi + host/akademik vakil + moderator | Rubrika tasdiqi, namunalar yetarliligi, appeal UAT; rating flag keyin yoqiladi |

G2 bepul pilot uchun G5 yoki G6ni kutish shart emas. Academic official export G3 umumiy host oqimidan alohida muassasa kelishuviga bog'liq. Bir kishi dasturchi va operator bo'lishi mumkin, ammo o'z pul qaytarishi/rol grantini yagona tasdiqlovchi bo'lishi mumkin emas. Hamkor yoki mustaqil approver tayinlanmaguncha shu yuqori vakolatli xizmat yopiq qoladi.

## Rasmiy dalillar va hali ochiq qarorlar

Huquqiy xizmat tasnifi, operatorning tashkiliy shakli, soliqlar, shaxsiy ma'lumot asosi/retention, muassasa tayinlovi, rasmiy baho/imzo, OneID/HEMIS ruxsati, WhatsApp Business va to'lov merchant shartnomalari tashqi tasdiq talab qiladi. Avvalgi huquqiy tahlil 26oktabr sanali ma'lumotnoma bo'lib qoladi; hozirgi hujjat uni yangi yuridik xulosa sifatida takrorlamaydi. Nomzodning shartnomadagi ish haqi ish beruvchi mas'uliyati; platforma xizmat orderi nomzod ish haqi hisob-kitobi emas.

## Manbalar

Texnik manbalar 30oktabr2026dagi talablarni tayyorlashda tekshirildi. Siyosatdagi limit va nishonlar manbadan olingan majburiy qonun emas, loyiha qarori.

- [N01] NIST SP800-63B: https://pages.nist.gov/800-63-4/sp800-63b.html
- [N02] WhatsApp authentication va amaldagi platforma narxlashi: https://whatsappbusiness.com/products/conversation-categories/authentication/ va https://whatsappbusiness.com/products/platform-pricing/
- [N03] Google JobPosting: https://developers.google.com/search/docs/appearance/structured-data/job-posting
- [N04] Google noindex: https://developers.google.com/search/docs/crawling-indexing/block-indexing
- [N05] W3C WCAG2.2: https://www.w3.org/TR/WCAG22/
- [N06] Payme Merchant API: https://developer.help.paycom.uz/metody-merchant-api/performtransaction/
- [N07] Click API: https://docs.click.uz/
- [N08] OWASP ASVS: https://asvs.owasp.org/
- [N09] OWASP brute force: https://owasp.org/www-community/controls/Blocking_Brute_Force_Attacks
- [N10] PostgreSQL backup: https://www.postgresql.org/docs/17/backup.html
- [N11] Django deployment checklist: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/


# Foydalanuvchi va xizmat imkoniyatlari texnik jadvali

DOIRASIDA belgisi mustaqil global ruxsat emas: tegishli account, faol a’zolik, assignment, amal turi va data scope birga tekshiriladi. GUEST ochiq ko‘rish; CANDIDATE o‘z profiliga ega hisob; STUDENT amaldagi tasdiqlangan enrollmentdan keladigan shart. Bir shaxs ko‘p rol bilan o‘z yozuvini tasdiqlamaydi. API jadvali operator/own amal farqini toraytiradi.

| Rol | Vakolat kelib chiqishi |
| --- | --- |
| GUEST - Mehmon | SELF doirasi; tegishli CAP va operation guard |
| CANDIDATE - Ish izlovchi | SELF doirasi; tegishli CAP va operation guard |
| STUDENT - Tasdiqlangan talaba | SELF doirasi; tasdiqlangan enrollment sharti |
| OWNER - Korxona egasi | ORG doirasi; tegishli CAP va operation guard |
| HR - HR | ORG doirasi; tegishli CAP va operation guard |
| HOST_COORDINATOR - Amaliyot mas’uli | ORG doirasi; tegishli CAP va operation guard |
| MENTOR - Korxona ustozi | ORG doirasi; tegishli CAP va operation guard |
| BILLING - Hisob-kitob xodimi | ORG doirasi; tegishli CAP va operation guard |
| COORDINATOR - Muassasa mas’uli | INSTITUTION doirasi; tegishli CAP va operation guard |
| TEACHER - O‘qituvchi | INSTITUTION doirasi; tegishli CAP va operation guard |
| MODERATOR - Moderator | PLATFORM doirasi; tegishli CAP va operation guard |
| SUPPORT - Yordam xodimi | PLATFORM doirasi; tegishli CAP va operation guard |
| FINANCE - Moliya nazoratchisi | PLATFORM doirasi; tegishli CAP va operation guard |
| ADMIN - Tizim operatori | PLATFORM doirasi; tegishli CAP va operation guard |

## CAP-001 E’lon qidirish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | PUBLIC_SEARCH / MVP |
| Kim | GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| Scope va cheklov | Faqat PUBLISHED, public fields. Qidiruvda shaxsiy profil/kundalik yo‘q; muddati o‘tganlar darhol chiqariladi. |
| Baza | DB-035 opportunities, DB-036 opportunity_revisions, DB-037 opportunity_skills, DB-038 opportunity_shifts, DB-021 organizations, DB-013 skills |
| Sahifalar | PG-001, PG-002, PG-003, PG-004 |

## CAP-002 Hisob va kirish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | AUTH_SELF / MVP |
| Kim | GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| Scope va cheklov | O‘z kontakt/sessiyasi. Kontakt tasdig‘i rol bermaydi; yangi qurilma va qayta berilgan raqam himoyasi. |
| Baza | DB-001 users, DB-002 user_contacts, DB-003 auth_challenges, DB-004 sessions, DB-005 mfa_credentials, DB-006 recovery_requests, DB-011 consent_events |
| Sahifalar | PG-001, PG-007, PG-008, PG-009, PG-010, PG-025 |

## CAP-003 Profil va CV

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | PROFILE_SELF / MVP |
| Kim | CANDIDATE, STUDENT |
| Scope va cheklov | O‘z candidate_profile. 18+; talabalik umumiy arizaga majburiy emas; fayl clean bo‘lishi kerak. |
| Baza | DB-012 candidate_profiles, DB-014 candidate_skills, DB-013 skills, DB-018 files |
| Sahifalar | PG-012, PG-014 |

## CAP-004 Ta’lim tarixi va tasdiq

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | EDUCATION_SELF / MVP |
| Kim | CANDIDATE, STUDENT |
| Scope va cheklov | O‘z enrollmenti. Bitirish umumiy ish huquqini yo‘qotmaydi; APPROVED enrollmentgina student talabini qoplaydi. |
| Baza | DB-015 enrollments, DB-028 institutions, DB-019 verification_cases, DB-020 verification_evidence, DB-018 files |
| Sahifalar | PG-012, PG-014 |

## CAP-005 Bo‘sh vaqt va istisno

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | AVAILABILITY_SELF / MVP |
| Kim | CANDIDATE, STUDENT |
| Scope va cheklov | O‘z vaqti. 28kun, yarim ochiq intervallar, 30min commute; UNKNOWN alohida. |
| Baza | DB-016 availability_rules, DB-017 availability_exceptions |
| Sahifalar | PG-002, PG-012, PG-015 |

## CAP-006 E’lon saqlash

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | SAVE_JOB / MVP |
| Kim | CANDIDATE, STUDENT |
| Scope va cheklov | O‘z saved qatori. Unique candidate/opportunity; yopilganini arxiv belgisi bilan ko‘rsatish. |
| Baza | DB-040 saved_opportunities, DB-035 opportunities |
| Sahifalar | PG-002, PG-016 |

## CAP-007 Ariza va qayta ariza

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | APPLY / MVP |
| Kim | CANDIDATE, STUDENT |
| Scope va cheklov | O‘z arizasi. E’lon eligibilitysi; STRICT jadval to‘sig‘i; snapshot, 24h va 3/30kun qayta urinish. |
| Baza | DB-041 applications, DB-042 application_attempts, DB-043 application_events, DB-036 opportunity_revisions, DB-090 idempotency_keys |
| Sahifalar | PG-003, PG-013, PG-017, PG-018 |

## CAP-008 Nomzodni ko‘rish va saralash

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | APPLICATION_HR / MVP |
| Kim | OWNER, HR, HOST_COORDINATOR |
| Scope va cheklov | Aynan e’longa berilgan HR/host scope. Faol org va rol; HOST_COORDINATOR faqat INTERNSHIP, HR/owner tegishli e’lon assignmenti. Global CV bazasi yo‘q. |
| Baza | DB-039 opportunity_hr_assignments, DB-041 applications, DB-042 application_attempts, DB-043 application_events, DB-018 files |
| Sahifalar | PG-028, PG-033, PG-034 |

## CAP-009 Suhbat belgilash/javob

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | INTERVIEW / MVP |
| Kim | CANDIDATE, STUDENT, OWNER, HR |
| Scope va cheklov | Ariza tomoni yoki ajratilgan HR. Vaqt o‘zgarishi ikkala tomonga; tashqi kalendar sync MVP emas. |
| Baza | DB-044 interviews, DB-045 interview_responses, DB-041 applications |
| Sahifalar | PG-018, PG-034 |

## CAP-010 Taklif yaratish/bekor qilish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | OFFER_ISSUE / MVP |
| Kim | OWNER, HR, HOST_COORDINATOR |
| Scope va cheklov | Ajratilgan e’lon. HR/host tegishli kind va assignment; terms snapshot, TTL; yuborish joyni band qilmaydi. |
| Baza | DB-046 offers, DB-041 applications, DB-042 application_attempts |
| Sahifalar | PG-034 |

## CAP-011 Taklif qabul qilish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | OFFER_ACCEPT / MVP |
| Kim | CANDIDATE, STUDENT |
| Scope va cheklov | O‘z offeri. Row lock capacity; bir o‘rin uchun ikki parallel acceptdan biri409; expiry va version tekshiriladi. |
| Baza | DB-046 offers, DB-041 applications, DB-035 opportunities, DB-047 job_engagements, DB-049 placements, DB-090 idempotency_keys |
| Sahifalar | PG-018 |

## CAP-012 Ish boshlandi/yakun/nizo

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | JOB_CONFIRM / MVP |
| Kim | CANDIDATE, STUDENT, OWNER, HR |
| Scope va cheklov | O‘z ish munosabati yoki HR scope. 2tomon STARTdan keyin ACTIVE; bir tomon da’vosi avtomatik salbiy reyting emas. |
| Baza | DB-047 job_engagements, DB-048 engagement_confirmations, DB-041 applications |
| Sahifalar | PG-019, PG-034 |

## CAP-013 Tashkilot va birinchi vakil

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | ORG_VERIFY / MVP |
| Kim | OWNER, HOST_COORDINATOR |
| Scope va cheklov | O‘z organization so‘rovi. STIR unique, mustaqil reviewer; hujjat yuborish vakolat tasdig‘i emas. |
| Baza | DB-021 organizations, DB-022 organization_capabilities, DB-019 verification_cases, DB-020 verification_evidence, DB-027 org_ownership_events |
| Sahifalar | PG-027, PG-029 |

## CAP-014 Xodim taklif va rol bekori

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | STAFF_MANAGE / MVP |
| Kim | OWNER |
| Scope va cheklov | Aynan o‘z orgi. 24h taklif, explicit roles; oxirgi owner himoyasi; revoked scope darhol yopiladi. |
| Baza | DB-023 org_memberships, DB-024 org_role_grants, DB-025 org_invitations, DB-026 org_invitation_roles, DB-027 org_ownership_events |
| Sahifalar | PG-030 |

## CAP-015 Xodim taklifini qabul

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | INVITE_ACCEPT / MVP |
| Kim | GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| Scope va cheklov | Kontaktga mos o‘z taklifi. GET token bo‘yicha minimal taklif; POST uchun login, verified target kontakt va TTL. Yangi odamdan hali olmagan rol talab qilinmaydi; assignment alohida qabul. |
| Baza | DB-025 org_invitations, DB-026 org_invitation_roles, DB-023 org_memberships, DB-033 institution_invitations, DB-032 institution_appointments, DB-030 institution_memberships |
| Sahifalar | PG-011 |

## CAP-016 E’lon yaratish/nashr/tahrir

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | JOB_PUBLISH / MVP |
| Kim | OWNER, HR, HOST_COORDINATOR |
| Scope va cheklov | Ajratilgan org capabilitysi. PART_TIME uchun maosh; INTERNSHIP end/is_paid; material tahrir yangi revision va moderation. |
| Baza | DB-035 opportunities, DB-036 opportunity_revisions, DB-037 opportunity_skills, DB-038 opportunity_shifts, DB-039 opportunity_hr_assignments, DB-075 service_entitlements |
| Sahifalar | PG-031, PG-032 |

## CAP-017 Amaliyot reja va mentor

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | HOST_PLAN / MVP |
| Kim | OWNER, HOST_COORDINATOR |
| Scope va cheklov | O‘z host placementi. Mentor active membership va shaxsiy accept; normal job kundalik talab qilmaydi. |
| Baza | DB-049 placements, DB-050 placement_terms, DB-053 plan_tasks, DB-051 mentor_assignments, DB-054 placement_decisions |
| Sahifalar | PG-028, PG-035 |

## CAP-018 Amaliyot shartlari va assignment qabuli

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | PLACEMENT_ACCEPT / MVP |
| Kim | CANDIDATE, STUDENT, MENTOR, TEACHER |
| Scope va cheklov | Aniq placement/assignment. O‘z roli shartini qabul qiladi; boshqa tomon nomidan accept yo‘q. |
| Baza | DB-049 placements, DB-050 placement_terms, DB-051 mentor_assignments, DB-052 academic_assignments, DB-054 placement_decisions |
| Sahifalar | PG-013, PG-020, PG-021, PG-036, PG-042 |

## CAP-019 Rasmiy muassasa va tayinlov

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | INSTITUTION_VERIFY / MVP |
| Kim | COORDINATOR |
| Scope va cheklov | O‘z rasmiy topshirig‘i. Platforma tekshiradi; domen yetarli emas; academic agreement va legal basis kerak. |
| Baza | DB-028 institutions, DB-029 institution_agreements, DB-032 institution_appointments, DB-033 institution_invitations, DB-019 verification_cases |
| Sahifalar | PG-007, PG-039 |

## CAP-020 Talaba va o‘qituvchi biriktirish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | SUPERVISION_ASSIGN / MVP |
| Kim | COORDINATOR |
| Scope va cheklov | O‘z muassasasidagi aniq enrollmentlar. Enrollment, agreement, appointment muassasasi teng; teacher self-assignment yo‘q. |
| Baza | DB-034 student_supervisions, DB-015 enrollments, DB-030 institution_memberships, DB-031 institution_role_grants, DB-052 academic_assignments |
| Sahifalar | PG-040, PG-041 |

## CAP-021 Akademik jarayonni kuzatish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | ACADEMIC_VIEW / MVP |
| Kim | COORDINATOR, TEACHER |
| Scope va cheklov | Koordinator purpose yoki qabul qilingan teacher assignment. Boshqa talaba/ish arizasi va maosh bazasi ochilmaydi; revoked scope old sessiyada ham yopiq. |
| Baza | DB-034 student_supervisions, DB-052 academic_assignments, DB-049 placements, DB-055 daily_logs, DB-056 log_revisions |
| Sahifalar | PG-040, PG-042, PG-043 |

## CAP-022 Amaliyot kundaligi va dalil

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | LOG_WRITE / MVP |
| Kim | CANDIDATE, STUDENT |
| Scope va cheklov | O‘z ACTIVE placementi. Sana/reja/sum/overlap, 7kun, immutable submitted revision, conflict412 va idempotency. |
| Baza | DB-055 daily_logs, DB-056 log_revisions, DB-057 log_task_entries, DB-058 log_evidence, DB-018 files, DB-061 log_amendment_requests |
| Sahifalar | PG-022 |

## CAP-023 Ish joyi kundaligini tasdiqlash

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | LOG_MENTOR / MVP |
| Kim | MENTOR |
| Scope va cheklov | Qabul qilingan faol mentor assignmenti. O‘z yozuvini tasdiqlash yo‘q. Eski revision approval yangisini yopmaydi; 3ishkun eskalatsiya. |
| Baza | DB-059 workplace_log_reviews, DB-051 mentor_assignments, DB-055 daily_logs, DB-056 log_revisions, DB-057 log_task_entries, DB-058 log_evidence |
| Sahifalar | PG-036, PG-037 |

## CAP-024 Akademik fikr va yakun

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | LOG_ACADEMIC / MVP |
| Kim | TEACHER |
| Scope va cheklov | Qabul qilingan academic assignment. Workplace approval o‘rnini bosmaydi; rasmiy baho/imzo alohida kelishuvga. |
| Baza | DB-060 academic_log_reviews, DB-052 academic_assignments, DB-056 log_revisions, DB-054 placement_decisions |
| Sahifalar | PG-043 |

## CAP-025 Amaliyot yakuni/chiqish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | PLACEMENT_CLOSE / MVP |
| Kim | CANDIDATE, STUDENT, HOST_COORDINATOR, MENTOR, TEACHER, COORDINATOR |
| Scope va cheklov | O‘z munosabatidagi tomon. Reja/soat, returned yozuvlar va tegishli ikki review yopiladi; sana o‘zi COMPLETED qilmaydi. |
| Baza | DB-054 placement_decisions, DB-049 placements, DB-050 placement_terms, DB-053 plan_tasks, DB-055 daily_logs |
| Sahifalar | PG-020, PG-035 |

## CAP-026 Amaliyot hisobotini olish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | REPORT_EXPORT / MVP |
| Kim | CANDIDATE, STUDENT, MENTOR, TEACHER, COORDINATOR |
| Scope va cheklov | O‘ziga ruxsatli placement va minimal data. Qayta auth va short-lived link; axborot PDFsi, rasmiy imzo emas. |
| Baza | DB-049 placements, DB-055 daily_logs, DB-056 log_revisions, DB-059 workplace_log_reviews, DB-060 academic_log_reviews, DB-018 files, DB-089 audit_events |
| Sahifalar | PG-021, PG-040 |

## CAP-027 Munosabatdan keyin baho

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | RATING_SUBMIT / PILOT_FLAG |
| Kim | CANDIDATE, STUDENT, HR, HOST_COORDINATOR, MENTOR, TEACHER |
| Scope va cheklov | Completed relation ishtirokchisi. Self-rating yo‘q, rubric va scope mos; blind14kun, default OFF. |
| Baza | DB-062 rubric_versions, DB-063 rubric_criteria, DB-064 rating_submissions, DB-065 rating_revisions, DB-066 rating_scores |
| Sahifalar | PG-019, PG-023 |

## CAP-028 Bahoga e’tiroz va agregat

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | RATING_APPEAL / PILOT_FLAG |
| Kim | CANDIDATE, STUDENT, OWNER, HR, MENTOR, TEACHER, MODERATOR |
| Scope va cheklov | Baho tomoni; independent reviewer. 14kun murojaat; n<5 public score yo‘q; MVP searchda ishlatilmaydi. |
| Baza | DB-067 rating_appeals, DB-064 rating_submissions, DB-065 rating_revisions, DB-068 rating_aggregates, DB-078 moderation_cases |
| Sahifalar | PG-023 |

## CAP-029 Tarif, order va hisob

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | BILLING / BILLING_GATE |
| Kim | OWNER, BILLING |
| Scope va cheklov | O‘z organizationi. Nomzod bepul; narx snapshot; post muddati nashrdan; callback verifieddan keyin aktivatsiya. |
| Baza | DB-069 products, DB-070 price_versions, DB-071 orders, DB-072 invoices, DB-073 payment_attempts, DB-075 service_entitlements, DB-077 billing_ledger |
| Sahifalar | PG-028, PG-038 |

## CAP-030 Pul qaytarish va reconciliation

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | REFUND / BILLING_GATE |
| Kim | OWNER, BILLING, FINANCE |
| Scope va cheklov | O‘z buyurtmasi yoki navbatdagi moliya case. So‘rovchi o‘zini tasdiqlamaydi; capture limit va idempotency; rol to‘liq CVni ochmaydi. |
| Baza | DB-076 refunds, DB-073 payment_attempts, DB-074 payment_events, DB-077 billing_ledger, DB-071 orders |
| Sahifalar | PG-038, PG-046 |

## CAP-031 Xabar va kanal sozlash

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | NOTIFICATION / MVP |
| Kim | CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| Scope va cheklov | O‘z inboxi/sozlamasi. Opt-in marketing, private matn tashqi kanalga yo‘q; revoke keyin havola qayta scope tekshiradi. |
| Baza | DB-085 notification_preferences, DB-087 notifications, DB-088 notification_deliveries, DB-086 outbox_events, DB-011 consent_events |
| Sahifalar | PG-013, PG-024 |

## CAP-032 Shikoyat va apellyatsiya

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | REPORT_ABUSE / MVP |
| Kim | CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, TEACHER, COORDINATOR |
| Scope va cheklov | Ko‘rilgan public yoki o‘z munosabat targeti. Yordamga dalil, retaliation himoyasi; avtomatik qora ro‘yxat yo‘q. |
| Baza | DB-078 moderation_cases, DB-079 moderation_actions, DB-018 files |
| Sahifalar | PG-003 |

## CAP-033 Tekshirish/moderatsiya

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | MODERATE / MVP |
| Kim | MODERATOR |
| Scope va cheklov | Biriktirilgan navbat, minimum evidence. Own case review rad; pulga reyting yashirilmaydi; barcha qaror audit. |
| Baza | DB-019 verification_cases, DB-020 verification_evidence, DB-078 moderation_cases, DB-079 moderation_actions, DB-021 organizations, DB-035 opportunities |
| Sahifalar | PG-044 |

## CAP-034 Yordam murojaati

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | SUPPORT / MVP |
| Kim | CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| Scope va cheklov | O‘z ticketi yoki ajratilgan SUPPORT operator. Har authenticated odam own-ticket ochadi; operator queue faqat SUPPORT. Internal note foydalanuvchiga chiqmaydi; OTP/parol so‘ralmaydi. |
| Baza | DB-080 support_tickets, DB-081 support_messages, DB-018 files |
| Sahifalar | PG-026, PG-045 |

## CAP-035 Rozilik, eksport, tuzatish/o‘chirish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | PRIVACY / MVP |
| Kim | CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| Scope va cheklov | O‘z data subject so‘rovi yoki maxsus vakolatli SUPPORT operator. Huquqiy retention va legal hold; eksportsiz boshqalar data; backup expiry va redelete manifest. Own request huquqi operator resolve bermaydi. |
| Baza | DB-082 privacy_requests, DB-083 retention_policies, DB-084 legal_holds, DB-011 consent_events, DB-018 files |
| Sahifalar | PG-025, PG-045 |

## CAP-036 Audit va vaqtli admin kirish

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | ADMIN_AUDIT / MVP |
| Kim | ADMIN |
| Scope va cheklov | Vaqtli approved platform scope. Biznes rolini o‘ziga berish yo‘q; break-glass reason, expiry, ikkinchi ko‘ruvchi. |
| Baza | DB-089 audit_events, DB-010 platform_role_grants, DB-009 role_permissions, DB-008 role_catalog, DB-007 permission_catalog, DB-004 sessions, DB-093 incidents |
| Sahifalar | PG-047 |

## CAP-037 Flag, incident, backup va o‘lchov

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | OPERATIONS / MVP |
| Kim | ADMIN |
| Scope va cheklov | Vaqtli texnik operator scope. Target SLO faqat o‘lchanganda qabul; billing PITR/reconciliation shart. Texnik rol pul approval bermaydi. |
| Baza | DB-092 feature_flags, DB-093 incidents, DB-094 restore_runs, DB-091 analytics_events, DB-086 outbox_events |
| Sahifalar | PG-048 |

## CAP-038 Moliyaviy hisobot

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | FINANCE_REPORT / BILLING_GATE |
| Kim | OWNER, BILLING, FINANCE |
| Scope va cheklov | O‘z orgi yoki platforma moliya agregati. FINANCE texnik flag yoki biznes CVni ochmaydi; cash va xizmat majburiyati ajratiladi. |
| Baza | DB-077 billing_ledger, DB-071 orders, DB-072 invoices, DB-075 service_entitlements |
| Sahifalar | PG-046 |

## CAP-039 Ochiq xizmat va siyosat ma’lumoti

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | PUBLIC_INFO / MVP |
| Kim | GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR, MENTOR, BILLING, COORDINATOR, TEACHER, MODERATOR, SUPPORT, FINANCE, ADMIN |
| Scope va cheklov | Faqat public katalog va versiyali siyosat matni. Public javobda boshqa odam roziligi yoki yopiq flag konfiguratsiyasi yo‘q; siyosat matni versiyali faylda, consent_events faqat qabulda yoziladi. |
| Baza | DB-069 products, DB-070 price_versions, DB-011 consent_events, DB-092 feature_flags |
| Sahifalar | PG-005, PG-006 |

## CAP-040 Korxonaning ochiq reytingi

| Qism | Texnik talab |
| --- | --- |
| Kod / bosqich | RATING_PUBLIC / PILOT_FLAG |
| Kim | GUEST, CANDIDATE, STUDENT, OWNER, HR, HOST_COORDINATOR |
| Scope va cheklov | Faqat ruxsatli public agregat. Flag OFF yoki n<5 bo‘lsa score qaytmaydi; individual akademik baho ommaga yo‘q. |
| Baza | DB-068 rating_aggregates, DB-062 rubric_versions, DB-021 organizations, DB-092 feature_flags |
| Sahifalar | PG-004 |


# Sahifalar va har bir bo‘limning indeksi

Sahifa ID va bo‘lim ID o‘zgarmas traceability kodi. Route ichidagi {id}/{org}/{inst} parametr, ketma-ket raqam emas. Public sahifadagi shaxsiy bo‘lim login talabini ko‘rsatadi; unda yopiq ma’lumot oldindan yuklanmaydi. Bir route oilasidagi yangi ekran keyingi versiyada alohida S indeks oladi. Umumiy header, footer, navigatsiya, cookie/rozilik, login talabi, error/empty/loading/offline holatlari UI-G01..G08 umumiy komponentlaridir.

| UI indeksi | Umumiy komponent |
| --- | --- |
| UI-G01 | Header va faol account/scope tanlovi |
| UI-G02 | Desktop/mobile role navigatsiyasi |
| UI-G03 | Footer: aloqa, shartlar va maxfiylik |
| UI-G04 | Rozilik va marketing tanlovi |
| UI-G05 | Loading/empty/offline va retry |
| UI-G06 | Validation/error/conflict/limit va request_id |
| UI-G07 | No-access/login/MFA talabi |
| UI-G08 | Fokus, keyboard, label va til/vaqt formatlari |

## PG-001 Bosh sahifa

Route: `/`. Sahifa kirishi: GUEST. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-001.S01 Qidiruv va xizmatlar | CAP-001; API-001 GET /api/v1/opportunities | DB-035, DB-036, DB-037, DB-038, DB-021, DB-013. Public xizmat kartalari va qidiruv boshlash |
| PG-001.S02 Yangi e’lonlar | CAP-001; API-001 GET /api/v1/opportunities | DB-035, DB-036, DB-037, DB-038, DB-021, DB-013. Expired chiqarilgan e’lonlar |
| PG-001.S03 Hisob ochish yo‘li | CAP-002; API-002 GET /api/v1/onboarding/options | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. Nomzod, ish beruvchi, host va rasmiy xodim yo‘llari |

## PG-002 Ish va amaliyot qidirish

Route: `/ishlar`. Sahifa kirishi: GUEST, CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-002.S01 Filtr va natijalar | CAP-001; API-001 GET /api/v1/opportunities | DB-035, DB-036, DB-037, DB-038, DB-021, DB-013. UZ/RU, hudud, kind, salary, skill, schedule; stable cursor |
| PG-002.S02 Moslik izohi | CAP-005; API-003 POST /api/v1/matching/preview | DB-016, DB-017. MATCH/CONFLICT/UNKNOWN, formula versiyasi va sabab |
| PG-002.S03 Saqlanganlar | CAP-006; API-004 POST /api/v1/saved-opportunities | DB-040, DB-035. Toggle idempotent, faqat o‘z nomzodi |

## PG-003 E’lon tafsiloti

Route: `/ishlar/{id}/{slug}`. Sahifa kirishi: GUEST, CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-003.S01 Shartlar va tashkilot | CAP-001; API-005 GET /api/v1/opportunities/{id} | DB-035, DB-036, DB-037, DB-038, DB-021, DB-013. Public immutable published revision, maosh, eligibility va vacancy |
| PG-003.S02 Ariza yuborish | CAP-007; API-006 POST /api/v1/opportunities/{id}/applications | DB-041, DB-042, DB-043, DB-036, DB-090. Eligibility/schedule snapshot va Idempotency-Key |
| PG-003.S03 Shikoyat | CAP-032; API-007 POST /api/v1/moderation-cases | DB-078, DB-079, DB-018. Target FK va asos |

## PG-004 Korxonaning ochiq sahifasi

Route: `/korxonalar/{id}`. Sahifa kirishi: GUEST. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-004.S01 Korxona va tasdiq belgisi | CAP-001; API-008 GET /api/v1/organizations/{id}/public | DB-035, DB-036, DB-037, DB-038, DB-021, DB-013. Dalil hujjatini ochmasdan capability holati |
| PG-004.S02 Faol e’lonlar | CAP-001; API-009 GET /api/v1/organizations/{id}/opportunities | DB-035, DB-036, DB-037, DB-038, DB-021, DB-013. Faqat publish e’lon |
| PG-004.S03 Munosabatlar bahosi | CAP-040; API-010 GET /api/v1/organizations/{id}/rating-summary | DB-068, DB-062, DB-021, DB-092. Flag OFFda ko‘rsatilmaydi; n<5 score yo‘q |

## PG-005 Xizmatlar va narxlar

Route: `/xizmatlar`. Sahifa kirishi: GUEST. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-005.S01 Bepul nomzod xizmatlari | CAP-039; API-011 GET /api/v1/services/public | DB-069, DB-070, DB-011, DB-092. Kimga, qanday shart, real xizmat chegarasi |
| PG-005.S02 Korxona tariflari | CAP-039; API-012 GET /api/v1/prices/public | DB-069, DB-070, DB-011, DB-092. Taklif narxi, 30kun, aktivatsiya va refund qoidasi |

## PG-006 Yordam va huquqiy sahifa

Route: `/yordam/{document}`. Sahifa kirishi: GUEST. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-006.S01 Qo‘llanma va tezkor savollar | CAP-039; API-013 GET /api/v1/help/{document} | DB-069, DB-070, DB-011, DB-092. Faqat ma’lumot mazmuni; CMS matni alohida versiyalanadi |
| PG-006.S02 Shartlar/maxfiylik/reyting siyosati | CAP-039; API-014 GET /api/v1/policies/{document} | DB-069, DB-070, DB-011, DB-092. Ochiq hujjat versiyasi, amal sanasi va aloqa |

## PG-007 Ro‘yxatdan o‘tish

Route: `/royxatdan-otish`. Sahifa kirishi: GUEST. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-007.S01 Yo‘l va 18+ tanlovi | CAP-002; API-015 POST /api/v1/auth/register | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. Bitta user, deklaratsiya va shart versiyasi |
| PG-007.S02 Kontakt va kanal tanlovi | CAP-002; API-016 POST /api/v1/auth/challenges | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. Email yoki PHONE WhatsApp/SMS; enumeration himoyasi |
| PG-007.S03 Muassasa xizmat havolasi | CAP-019; API-017 GET /api/v1/institution-onboarding/options | DB-028, DB-029, DB-032, DB-033, DB-019. Tayinlov hujjati va keyingi tekshiruv izohi |

## PG-008 Kirish

Route: `/kirish`. Sahifa kirishi: GUEST. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-008.S01 Email/parol yoki telefon kodi | CAP-002; API-018 POST /api/v1/auth/login | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. Rate limit, generic failure va sessiya |
| PG-008.S02 Qo‘shimcha omil | CAP-002; API-019 POST /api/v1/auth/mfa/verify | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. Sezgir rol TOTP/passkey; telefon kodi ikki omil emas |

## PG-009 Kontaktni tasdiqlash

Route: `/tasdiqlash`. Sahifa kirishi: GUEST. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-009.S01 Kodni kiritish | CAP-002; API-020 POST /api/v1/auth/challenges/{id}/consume | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. 5min/5urinish, purpose va atomic consume |
| PG-009.S02 Qayta yuborish/kanal almashtirish | CAP-002; API-021 POST /api/v1/auth/challenges/{id}/resend | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. 60s; old kod invalid; provider failure holati |

## PG-010 Hisobni tiklash

Route: `/tiklash`. Sahifa kirishi: GUEST. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-010.S01 Tiklash so‘rovi | CAP-002; API-022 POST /api/v1/auth/recovery | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. Generic response, egasi tekshiriladi |
| PG-010.S02 Dalil va natija | CAP-002; API-023 GET /api/v1/auth/recovery/{id} | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. Yangi raqam eski shaxsiy data ochmaydi, cheklangan recovery |

## PG-011 Taklifni qabul qilish

Route: `/taklif/{token}`. Sahifa kirishi: GUEST, CANDIDATE, HR, MENTOR, TEACHER. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-011.S01 Taklif va ochiq rol | CAP-015; API-024 GET /api/v1/invitations/{token} | DB-025, DB-026, DB-023, DB-033, DB-032, DB-030. Token serverda digest, org/institution va TTL |
| PG-011.S02 Shaxsiy qabul | CAP-015; API-025 POST /api/v1/invitations/{token}/accept | DB-025, DB-026, DB-023, DB-033, DB-032, DB-030. Kontakt mosligi, login va idempotent membership |

## PG-012 Nomzod boshlang‘ich sozlash

Route: `/nomzod/boshlash`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-012.S01 Kasb va asosiy profil | CAP-003; API-026 PATCH /api/v1/me/candidate | DB-012, DB-014, DB-013, DB-018. Minimal ma’lumot, talaba emasman yo‘li |
| PG-012.S02 Talabalik ixtiyoriy | CAP-004; API-027 POST /api/v1/me/enrollments | DB-015, DB-028, DB-019, DB-020, DB-018. Umumiy ishga to‘sqinlik qilmaydi |
| PG-012.S03 Bo‘sh vaqt | CAP-005; API-028 PUT /api/v1/me/availability | DB-016, DB-017. Haftalik intervallar va vaqt zonasi |

## PG-013 Nomzod kabineti

Route: `/nomzod`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-013.S01 Mening jarayonlarim | CAP-007; API-029 GET /api/v1/me/applications/summary | DB-041, DB-042, DB-043, DB-036, DB-090. Ariza/suhbat/offer ko‘rsatkichlari |
| PG-013.S02 Amaliyot vazifalari | CAP-018; API-030 GET /api/v1/me/placements | DB-049, DB-050, DB-051, DB-052, DB-054. Faqat o‘z munosabatlari |
| PG-013.S03 Xabarlar | CAP-031; API-031 GET /api/v1/me/notifications | DB-085, DB-087, DB-088, DB-086, DB-011. O‘z unread xabarlar |

## PG-014 Profil va rezyume

Route: `/nomzod/profil`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-014.S01 Profil, ko‘nikma va tajriba | CAP-003; API-032 PATCH /api/v1/me/candidate/skills | DB-012, DB-014, DB-013, DB-018. Self-declared va verified ajratiladi |
| PG-014.S02 CV va maxfiylik | CAP-003; API-033 POST /api/v1/me/candidate/cv | DB-012, DB-014, DB-013, DB-018. Karantin va scan; private file |
| PG-014.S03 Ta’lim tarixi | CAP-004; API-034 GET /api/v1/me/enrollments | DB-015, DB-028, DB-019, DB-020, DB-018. Enrollment status, end va tekshiruv navbati |

## PG-015 Mavjudlik jadvali

Route: `/nomzod/vaqt`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-015.S01 Haftalik jadval | CAP-005; API-035 GET /api/v1/me/availability | DB-016, DB-017. Union qilingan interval muharriri |
| PG-015.S02 Istisnolar | CAP-005; API-036 PUT /api/v1/me/availability/exceptions | DB-016, DB-017. Sana bo‘yicha AVAILABLE/UNAVAILABLE |
| PG-015.S03 Moslik sinovi | CAP-005; API-003 POST /api/v1/matching/preview | DB-016, DB-017. 28kun, commute, ALL/ANY, izoh |

## PG-016 Saqlangan e’lonlar

Route: `/nomzod/saqlangan`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-016.S01 Saqlangan ro‘yxat | CAP-006; API-037 GET /api/v1/me/saved-opportunities | DB-040, DB-035. Yopilgan e’lon statusi saqlanadi |
| PG-016.S02 Olib tashlash | CAP-006; API-038 DELETE /api/v1/me/saved-opportunities/{id} | DB-040, DB-035. Faqat o‘z qatori; repeat204 |

## PG-017 Arizalar ro‘yxati

Route: `/nomzod/arizalar`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-017.S01 Status filtri va ro‘yxat | CAP-007; API-039 GET /api/v1/me/applications | DB-041, DB-042, DB-043, DB-036, DB-090. Stable cursor, o‘z arizalari |
| PG-017.S02 Qayta yuborish sababi | CAP-007; API-040 POST /api/v1/me/applications/{id}/reapply | DB-041, DB-042, DB-043, DB-036, DB-090. 24h va limit; HR reopen zarur bo‘lsa izoh |

## PG-018 Ariza tafsiloti

Route: `/nomzod/arizalar/{id}`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-018.S01 Ariza va tarixiy shartlar | CAP-007; API-041 GET /api/v1/me/applications/{id} | DB-041, DB-042, DB-043, DB-036, DB-090. Original attempt snapshot va status timeline |
| PG-018.S02 Suhbat va javob | CAP-009; API-042 POST /api/v1/interviews/{id}/responses | DB-044, DB-045, DB-041. Candidate javobi |
| PG-018.S03 Taklifni qabul/rad | CAP-011; API-043 POST /api/v1/offers/{id}/respond | DB-046, DB-041, DB-035, DB-047, DB-049, DB-090. Expiry/capacity, taklif joyni kafolatlamasligi |
| PG-018.S04 Arizani qaytarish | CAP-007; API-044 POST /api/v1/me/applications/{id}/withdraw | DB-041, DB-042, DB-043, DB-036, DB-090. Transition sabab va audit |

## PG-019 Mening ish munosabatim

Route: `/nomzod/ishlar/{id}`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-019.S01 Shart va boshlanish | CAP-012; API-045 GET /api/v1/me/engagements/{id} | DB-047, DB-048, DB-041. Oddiy ish, kundalik majburiy emas |
| PG-019.S02 Boshlash/yakun/nizo | CAP-012; API-046 POST /api/v1/engagements/{id}/confirmations | DB-047, DB-048, DB-041. Tomon bo‘yicha ikki tasdiq |
| PG-019.S03 Fikr bildirish | CAP-027; API-047 POST /api/v1/engagements/{id}/ratings | DB-062, DB-063, DB-064, DB-065, DB-066. Flag va completed eligibility |

## PG-020 Amaliyotlarim

Route: `/nomzod/amaliyot`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-020.S01 Amaliyot ro‘yxati | CAP-018; API-030 GET /api/v1/me/placements | DB-049, DB-050, DB-051, DB-052, DB-054. PLANNED/ACTIVE va yakun holati |
| PG-020.S02 Shart va mentor qabuli | CAP-018; API-048 POST /api/v1/placements/{id}/accept | DB-049, DB-050, DB-051, DB-052, DB-054. O‘z candidate side qabuli |
| PG-020.S03 Amaliyotni yakunlash | CAP-025; API-049 POST /api/v1/placements/{id}/completion-requests | DB-054, DB-049, DB-050, DB-053, DB-055. Ochiq qaytgan log va reja sababi |

## PG-021 Amaliyot rejasi

Route: `/amaliyot/{id}/reja`. Sahifa kirishi: CANDIDATE, STUDENT, MENTOR, TEACHER, HOST_COORDINATOR, COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-021.S01 Reja va vazifalar | CAP-018; API-050 GET /api/v1/placements/{id}/plan | DB-049, DB-050, DB-051, DB-052, DB-054. Versiya va taraflar qabuli |
| PG-021.S02 Tayinlovni qabul | CAP-018; API-051 POST /api/v1/placements/{id}/assignments/{assignment}/accept | DB-049, DB-050, DB-051, DB-052, DB-054. Faqat tayinlangan shaxs |
| PG-021.S03 Yakuniy hisobot | CAP-026; API-052 POST /api/v1/placements/{id}/exports | DB-049, DB-055, DB-056, DB-059, DB-060, DB-018, DB-089. Re-auth, audit, axborot PDF |

## PG-022 Amaliyot kundaligi

Route: `/amaliyot/{id}/kundalik`. Sahifa kirishi: CANDIDATE, STUDENT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-022.S01 Kunlar va ko‘rib chiqish | CAP-022; API-053 GET /api/v1/placements/{id}/logs | DB-055, DB-056, DB-057, DB-058, DB-018, DB-061. Local_date, workplace va academic alohida |
| PG-022.S02 Qoralama va topshiriqlar | CAP-022; API-054 PUT /api/v1/placements/{id}/logs/{date} | DB-055, DB-056, DB-057, DB-058, DB-018, DB-061. Version/If-Match, task minute SUM |
| PG-022.S03 Dalil fayllari | CAP-022; API-055 POST /api/v1/log-entries/{id}/evidence | DB-055, DB-056, DB-057, DB-058, DB-018, DB-061. Private file va scan |
| PG-022.S04 Topshirish/o‘zgartirish | CAP-022; API-056 POST /api/v1/logs/{id}/submit | DB-055, DB-056, DB-057, DB-058, DB-018, DB-061. Future/past/overlap/limit va idempotency |

## PG-023 Reyting va e’tiroz

Route: `/mening-reytingim`. Sahifa kirishi: CANDIDATE, STUDENT, OWNER, MENTOR, TEACHER. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-023.S01 Mezonlar va fikr | CAP-027; API-057 GET /api/v1/me/ratings | DB-062, DB-063, DB-064, DB-065, DB-066. Rubric versiya, n, score yo‘qligi tushuntiriladi |
| PG-023.S02 E’tiroz | CAP-028; API-058 POST /api/v1/ratings/{id}/appeals | DB-067, DB-064, DB-065, DB-068, DB-078. 14kun, mustaqil queue, aggregate recompute |

## PG-024 Xabarlar

Route: `/xabarlar`. Sahifa kirishi: CANDIDATE, STUDENT, OWNER, HR, MENTOR, TEACHER, COORDINATOR, BILLING. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-024.S01 Inbox va o‘qildi | CAP-031; API-031 GET /api/v1/me/notifications | DB-085, DB-087, DB-088, DB-086, DB-011. O‘z xabar, havolada joriy scope |
| PG-024.S02 Kanallar va reklama | CAP-031; API-059 PUT /api/v1/me/notification-preferences | DB-085, DB-087, DB-088, DB-086, DB-011. Transactional/marketing alohida |

## PG-025 Hisob va xavfsizlik

Route: `/sozlamalar`. Sahifa kirishi: CANDIDATE, STUDENT, OWNER, HR, MENTOR, TEACHER, COORDINATOR, BILLING. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-025.S01 Kontakt/parol/qo‘shimcha omil | CAP-002; API-060 PATCH /api/v1/me/security | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. Step-up va kontaktni qayta tekshirish |
| PG-025.S02 Qurilmalar va chiqish | CAP-002; API-061 DELETE /api/v1/me/sessions/{id} | DB-001, DB-002, DB-003, DB-004, DB-005, DB-006, DB-011. Joriy yoki boshqa sessiyani revoke |
| PG-025.S03 Maxfiylik va hisob o‘chirish | CAP-035; API-062 POST /api/v1/me/privacy-requests | DB-082, DB-083, DB-084, DB-011, DB-018. Export/delete/rectify, legal hold sababi |

## PG-026 Yordam murojaatlari

Route: `/yordam/murojaatlar`. Sahifa kirishi: CANDIDATE, STUDENT, OWNER, HR, MENTOR, TEACHER, COORDINATOR, BILLING. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-026.S01 Murojaatlar va muddat | CAP-034; API-063 GET /api/v1/me/support-tickets | DB-080, DB-081, DB-018. O‘z ticketlari, SLA va status |
| PG-026.S02 Yangi murojaat/yozishma | CAP-034; API-064 POST /api/v1/support-tickets/{id}/messages | DB-080, DB-081, DB-018. Private ilova, xodim OTP so‘ramaydi |

## PG-027 Tashkilotni ulash

Route: `/tashkilot/boshlash`. Sahifa kirishi: OWNER, HOST_COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-027.S01 STIR va tashkilot | CAP-013; API-065 POST /api/v1/organizations | DB-021, DB-022, DB-019, DB-020, DB-027. STIR dedup, mavjud orgga mansublik request |
| PG-027.S02 Vakil va capability dalili | CAP-013; API-066 POST /api/v1/organizations/{id}/verification | DB-021, DB-022, DB-019, DB-020, DB-027. JOB_EMPLOYER/INTERNSHIP_HOST alohida |
| PG-027.S03 Tekshiruv holati | CAP-013; API-067 GET /api/v1/organizations/{id}/verification | DB-021, DB-022, DB-019, DB-020, DB-027. 2ishkun nishon, sabab va evidence revision |

## PG-028 Korxona kabineti

Route: `/tashkilot/{org}`. Sahifa kirishi: OWNER, HR, HOST_COORDINATOR, BILLING. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-028.S01 E’lon/ariza ko‘rsatkichlari | CAP-008; API-068 GET /api/v1/organizations/{org}/dashboard | DB-039, DB-041, DB-042, DB-043, DB-018. Faqat foydalanuvchi scope agregati |
| PG-028.S02 Amaliyot kuzatuvi | CAP-017; API-069 GET /api/v1/organizations/{org}/placements | DB-049, DB-050, DB-053, DB-051, DB-054. Host capability va scope |
| PG-028.S03 Tarif holati | CAP-029; API-070 GET /api/v1/organizations/{org}/entitlements | DB-069, DB-070, DB-071, DB-072, DB-073, DB-075, DB-077. Billing/ownerga muddat va kvota |

## PG-029 Korxona profili

Route: `/tashkilot/{org}/profil`. Sahifa kirishi: OWNER, HOST_COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-029.S01 Public ma’lumot | CAP-013; API-071 PATCH /api/v1/organizations/{org} | DB-021, DB-022, DB-019, DB-020, DB-027. Material tekshiruv ma’lumotiga yangi case |
| PG-029.S02 Capability va dalillar | CAP-013; API-072 GET /api/v1/organizations/{org}/capabilities | DB-021, DB-022, DB-019, DB-020, DB-027. Public belgilar va private dalil ajratilgan |

## PG-030 Xodimlar va vakolatlar

Route: `/tashkilot/{org}/xodimlar`. Sahifa kirishi: OWNER. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-030.S01 A’zolar va rollar | CAP-014; API-073 GET /api/v1/organizations/{org}/memberships | DB-023, DB-024, DB-025, DB-026, DB-027. Org/role/assignment kesishmasi |
| PG-030.S02 Taklif yuborish | CAP-014; API-074 POST /api/v1/organizations/{org}/invitations | DB-023, DB-024, DB-025, DB-026, DB-027. 24h, target kontakt va explicit rol |
| PG-030.S03 Vakolat bekori/egani almashtirish | CAP-014; API-075 POST /api/v1/organizations/{org}/memberships/{id}/revoke | DB-023, DB-024, DB-025, DB-026, DB-027. Last-owner himoyasi va darhol revoke |

## PG-031 E’lonlar boshqaruvi

Route: `/tashkilot/{org}/elonlar`. Sahifa kirishi: OWNER, HR, HOST_COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-031.S01 E’lonlar va status | CAP-016; API-076 GET /api/v1/organizations/{org}/opportunities | DB-035, DB-036, DB-037, DB-038, DB-039, DB-075. Scope bo‘yicha ro‘yxat |
| PG-031.S02 Nashr/pauza/yopish | CAP-016; API-077 POST /api/v1/opportunities/{id}/transition | DB-035, DB-036, DB-037, DB-038, DB-039, DB-075. Moderation, entitlement va transition lock |

## PG-032 E’lon yaratish/tahrir

Route: `/tashkilot/{org}/elonlar/{id}/tahrir`. Sahifa kirishi: OWNER, HR, HOST_COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-032.S01 Tur va asosiy vazifa | CAP-016; API-078 PUT /api/v1/opportunities/{id}/draft | DB-035, DB-036, DB-037, DB-038, DB-039, DB-075. PART_TIME va INTERNSHIP formasi ajratiladi |
| PG-032.S02 Maosh va eligibility | CAP-016; API-079 PUT /api/v1/opportunities/{id}/draft/terms | DB-035, DB-036, DB-037, DB-038, DB-039, DB-075. Salary, unpaid, end, talaba talabi validatsiya |
| PG-032.S03 Smena, skill va o‘rin | CAP-016; API-080 PUT /api/v1/opportunities/{id}/draft/schedule | DB-035, DB-036, DB-037, DB-038, DB-039, DB-075. ALL/ANY, STRICT/NEGOTIABLE, capacity>=occupied |
| PG-032.S04 Ko‘rib chiqish va nashr | CAP-016; API-081 POST /api/v1/opportunities/{id}/publish | DB-035, DB-036, DB-037, DB-038, DB-039, DB-075. Yangi revision, moderation va entitlement boshlanishi |

## PG-033 Nomzodlar saralashi

Route: `/tashkilot/{org}/elonlar/{id}/arizalar`. Sahifa kirishi: OWNER, HR, HOST_COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-033.S01 Status bo‘yicha arizalar | CAP-008; API-082 GET /api/v1/opportunities/{id}/applications | DB-039, DB-041, DB-042, DB-043, DB-018. Boshqa e’lon nomzodlari ochilmaydi |
| PG-033.S02 Tanlash/rad/suhbat | CAP-008; API-083 POST /api/v1/applications/{id}/transition | DB-039, DB-041, DB-042, DB-043, DB-018. Audit va allowed transition |

## PG-034 Nomzod arizasi HR ko‘rinishi

Route: `/tashkilot/{org}/arizalar/{id}`. Sahifa kirishi: OWNER, HR, HOST_COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-034.S01 Ariza nusxasi va CV | CAP-008; API-084 GET /api/v1/applications/{id}/hr | DB-039, DB-041, DB-042, DB-043, DB-018. Aynan attemptdagi minimal snapshot |
| PG-034.S02 Suhbat belgilash | CAP-009; API-085 POST /api/v1/applications/{id}/interviews | DB-044, DB-045, DB-041. Timezone va javob |
| PG-034.S03 Taklif shartlari | CAP-010; API-086 POST /api/v1/applications/{id}/offers | DB-046, DB-041, DB-042. Narx/shart snapshot, expiry, capacity izohi |
| PG-034.S04 Ish holatini tasdiqlash | CAP-012; API-046 POST /api/v1/engagements/{id}/confirmations | DB-047, DB-048, DB-041. Faqat PART_TIME munosabati |

## PG-035 Host amaliyotlari

Route: `/tashkilot/{org}/amaliyot`. Sahifa kirishi: OWNER, HOST_COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-035.S01 O‘rin va amaliyotlar | CAP-017; API-069 GET /api/v1/organizations/{org}/placements | DB-049, DB-050, DB-053, DB-051, DB-054. Host capability va haqiqiy qabul |
| PG-035.S02 Reja/mentor tayinlash | CAP-017; API-087 POST /api/v1/placements/{id}/mentor-assignments | DB-049, DB-050, DB-053, DB-051, DB-054. Ayni orgning faol MENTORi va qabul |
| PG-035.S03 Yakun/nizo | CAP-025; API-088 POST /api/v1/placements/{id}/host-decisions | DB-054, DB-049, DB-050, DB-053, DB-055. Soat/vazifa va review shartlari |

## PG-036 Mentor kabineti

Route: `/mentor`. Sahifa kirishi: MENTOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-036.S01 Tayinlovlarni qabul | CAP-018; API-089 GET /api/v1/me/mentor-assignments | DB-049, DB-050, DB-051, DB-052, DB-054. Qabuldan oldin yopiq kundalik yo‘q |
| PG-036.S02 Ko‘rib chiqish navbati | CAP-023; API-090 GET /api/v1/me/mentor-review-queue | DB-059, DB-051, DB-055, DB-056, DB-057, DB-058. Faqat own accepted assignment; due eskalatsiya |

## PG-037 Kundalikni mentor ko‘rishi

Route: `/mentor/kundalik/{revision}`. Sahifa kirishi: MENTOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-037.S01 Aynan topshirilgan revision | CAP-023; API-091 GET /api/v1/log-revisions/{revision}/workplace | DB-059, DB-051, DB-055, DB-056, DB-057, DB-058. Vazifa, vaqt, reja va ruxsatli dalil |
| PG-037.S02 Tasdiqlash/qaytarish | CAP-023; API-092 POST /api/v1/log-revisions/{revision}/workplace-reviews | DB-059, DB-051, DB-055, DB-056, DB-057, DB-058. O‘z logi rad; qaror revisionga bog‘liq |

## PG-038 Tarif va to‘lovlar

Route: `/tashkilot/{org}/tolovlar`. Sahifa kirishi: OWNER, BILLING. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-038.S01 Tarif va muddatlar | CAP-029; API-093 GET /api/v1/organizations/{org}/billing | DB-069, DB-070, DB-071, DB-072, DB-073, DB-075, DB-077. Plan/post, snapshot va ishlatilgan huquq |
| PG-038.S02 Buyurtma va to‘lov | CAP-029; API-094 POST /api/v1/organizations/{org}/orders | DB-069, DB-070, DB-071, DB-072, DB-073, DB-075, DB-077. Verified callback; pending/double/failure holat |
| PG-038.S03 Hisob va qaytarish | CAP-030; API-095 POST /api/v1/orders/{id}/refund-requests | DB-076, DB-073, DB-074, DB-077, DB-071. Qoidaga mos request; finance mustaqil approval |

## PG-039 Muassasani ulash

Route: `/muassasa/boshlash`. Sahifa kirishi: COORDINATOR, TEACHER. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-039.S01 Muassasa va rasmiy topshiriq | CAP-019; API-096 POST /api/v1/institution-appointments | DB-028, DB-029, DB-032, DB-033, DB-019. Rasmiy hujjat, identity va agreement |
| PG-039.S02 Tekshiruv/taklif qabuli | CAP-019; API-097 GET /api/v1/institution-appointments/{id} | DB-028, DB-029, DB-032, DB-033, DB-019. 3ishkun nishon; domen yetarli emas |

## PG-040 Muassasa kabineti

Route: `/muassasa/{inst}`. Sahifa kirishi: COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-040.S01 Biriktirilgan talabalar | CAP-021; API-098 GET /api/v1/institutions/{inst}/supervisions | DB-034, DB-052, DB-049, DB-055, DB-056. Aniq enrollment va purpose scope |
| PG-040.S02 Kutilayotgan biriktirish | CAP-020; API-099 GET /api/v1/institutions/{inst}/assignment-queue | DB-034, DB-015, DB-030, DB-031, DB-052. Faqat o‘z muassasasi |
| PG-040.S03 Minimal hisobot | CAP-026; API-100 POST /api/v1/institutions/{inst}/exports | DB-049, DB-055, DB-056, DB-059, DB-060, DB-018, DB-089. Faqat ruxsatli placements, re-auth, audit |

## PG-041 Talaba va rahbar biriktirish

Route: `/muassasa/{inst}/biriktirish`. Sahifa kirishi: COORDINATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-041.S01 Enrollment va agreement | CAP-020; API-101 POST /api/v1/student-supervisions | DB-034, DB-015, DB-030, DB-031, DB-052. Uchala institution bir xil va legal basis |
| PG-041.S02 O‘qituvchi tayinlash | CAP-020; API-102 POST /api/v1/placements/{id}/academic-assignments | DB-034, DB-015, DB-030, DB-031, DB-052. Faol appointment, teacher accept |
| PG-041.S03 Bekor qilish/almashtirish | CAP-020; API-103 POST /api/v1/academic-assignments/{id}/revoke | DB-034, DB-015, DB-030, DB-031, DB-052. Eski kirish yopiladi, tarix qoladi |

## PG-042 O‘qituvchi kabineti

Route: `/oqituvchi`. Sahifa kirishi: TEACHER. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-042.S01 Shaxsiy tayinlovlar | CAP-018; API-104 GET /api/v1/me/academic-assignments | DB-049, DB-050, DB-051, DB-052, DB-054. Faqat o‘z taklifi, accept kerak |
| PG-042.S02 Talabalar va kundalik navbati | CAP-021; API-105 GET /api/v1/me/academic-review-queue | DB-034, DB-052, DB-049, DB-055, DB-056. Accepted assignment doirasi |

## PG-043 Kundalik akademik ko‘rinishi

Route: `/oqituvchi/kundalik/{revision}`. Sahifa kirishi: TEACHER. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-043.S01 Workplace qarori va dalil | CAP-021; API-106 GET /api/v1/log-revisions/{revision}/academic | DB-034, DB-052, DB-049, DB-055, DB-056. Minimum academic purpose |
| PG-043.S02 Akademik fikr | CAP-024; API-107 POST /api/v1/log-revisions/{revision}/academic-reviews | DB-060, DB-052, DB-056, DB-054. REVIEWED/NEEDS_REVISION, mentor o‘rniga emas |
| PG-043.S03 Yakuniy xulosa | CAP-024; API-108 POST /api/v1/placements/{id}/academic-decisions | DB-060, DB-052, DB-056, DB-054. Rasmiy grade/imzo flag va agreementga |

## PG-044 Tekshiruv va moderatsiya navbati

Route: `/operator/moderatsiya`. Sahifa kirishi: MODERATOR. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-044.S01 Tekshiruv navbati | CAP-033; API-109 GET /api/v1/operator/verification-cases | DB-019, DB-020, DB-078, DB-079, DB-021, DB-035. Assigned queue, due va revision |
| PG-044.S02 Dalil/qaror | CAP-033; API-110 POST /api/v1/operator/verification-cases/{id}/decide | DB-019, DB-020, DB-078, DB-079, DB-021, DB-035. Own-case taqiq, sabab majburiy |
| PG-044.S03 E’lon/shikoyat/apellyatsiya | CAP-033; API-111 POST /api/v1/operator/moderation-cases/{id}/actions | DB-019, DB-020, DB-078, DB-079, DB-021, DB-035. Independent appeal, vaqtli hide va audit |

## PG-045 Yordam operatori

Route: `/operator/yordam`. Sahifa kirishi: SUPPORT. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-045.S01 Ticketlar va SLA | CAP-034; API-112 GET /api/v1/operator/support-tickets | DB-080, DB-081, DB-018. Ajratilgan minimal ticket scope |
| PG-045.S02 Javob/eskalatsiya | CAP-034; API-113 POST /api/v1/operator/support-tickets/{id}/messages | DB-080, DB-081, DB-018. Internal/public farqi |
| PG-045.S03 Maxfiylik so‘rovlari | CAP-035; API-114 POST /api/v1/operator/privacy-requests/{id}/resolve | DB-082, DB-083, DB-084, DB-011, DB-018. Shaxs tasdig‘i, hold va ruxsatli data |

## PG-046 Moliya operatori

Route: `/operator/moliya`. Sahifa kirishi: FINANCE. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-046.S01 Provider reconciliation | CAP-030; API-115 GET /api/v1/operator/reconciliation | DB-076, DB-073, DB-074, DB-077, DB-071. Ledger va provider farqi, PII emas |
| PG-046.S02 Refund approval | CAP-030; API-116 POST /api/v1/operator/refunds/{id}/approve | DB-076, DB-073, DB-074, DB-077, DB-071. Independent actor, capture sum lock |
| PG-046.S03 Tushum va majburiyatlar | CAP-038; API-117 GET /api/v1/operator/finance-summary | DB-077, DB-071, DB-072, DB-075. Cash/recognized revenue/deferred farqi |

## PG-047 Audit va ruxsatlar

Route: `/operator/audit`. Sahifa kirishi: ADMIN. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-047.S01 Audit qidiruvi | CAP-036; API-118 GET /api/v1/operator/audit-events | DB-089, DB-010, DB-009, DB-008, DB-007, DB-004, DB-093. Append-only, object tarixiy identifikator |
| PG-047.S02 Vaqtli grant/break-glass | CAP-036; API-119 POST /api/v1/operator/access-requests | DB-089, DB-010, DB-009, DB-008, DB-007, DB-004, DB-093. Reason+expiry+independent approval |
| PG-047.S03 Sessiya bekori | CAP-036; API-120 POST /api/v1/operator/users/{id}/revoke-sessions | DB-089, DB-010, DB-009, DB-008, DB-007, DB-004, DB-093. Faqat dalilli incident recovery, audit |

## PG-048 Tizim holati va reliz

Route: `/operator/tizim`. Sahifa kirishi: ADMIN. Bo‘lim amali uchun quyidagi CAP scope tekshiriladi.

| Bo‘lim ID va nomi | Imkoniyat / API | Data va xatti-harakat |
| --- | --- | --- |
| PG-048.S01 Flag va konfiguratsiya | CAP-037; API-121 PATCH /api/v1/operator/feature-flags/{code} | DB-092, DB-093, DB-094, DB-091, DB-086. Change reason, default OFF capabilityni bermaydi |
| PG-048.S02 Incident va navbatchi | CAP-037; API-122 POST /api/v1/operator/incidents | DB-092, DB-093, DB-094, DB-091, DB-086. P1 commander va tiklash reja |
| PG-048.S03 Backup/restore dalili | CAP-037; API-123 GET /api/v1/operator/restore-runs | DB-092, DB-093, DB-094, DB-091, DB-086. RPO/RTO o‘lchov; pullik checkout gate |
| PG-048.S04 Mahsulot ko‘rsatkichlari | CAP-037; API-124 GET /api/v1/operator/analytics | DB-092, DB-093, DB-094, DB-091, DB-086. Dedup, cohort, ikkala tomon START tasdig‘i |


# Kamchiliklarni to‘ldirish va qabul mezonlari

Oldingi 25 masala va keyingi kirish/operatsion bo‘shliqlar quyidagi qarorlarga birlashtirildi. Holat barcha satrlar uchun: TALABDA TO‘LDIRILDI; DASTUR VA AMALIY TEST BAJARILMAGAN. Qabul testlari rejalashtirilgan, test natijasi emas.


## AC-001 REG-01 - Talaba bo‘lmagan nomzod

18+ nonstudent profil ochadi va ALL_CANDIDATES ishga talabalik dalilisiz ariza beradi; student-only alohida422.

Bog‘lanish: CAP-003; DB-012, DB-015. Qaror: 01_product: Hisob ochish.

## AC-002 REG-02 - Qayta berilgan raqam

Yangi qurilmadagi telefon OTP eski hisobning CV/kundaligini ochmaydi; eski ishonchli omil yoki recovery kerak.

Bog‘lanish: CAP-002; DB-002, DB-004, DB-006. Qaror: 01_product: Email WhatsApp.

## AC-003 REG-03 - Tekshiruv navbati va SLA

1/2/3ishkun due va reviewer bor; muddat oshishi tasdiq emas, eskalatsiya.

Bog‘lanish: CAP-033; DB-019, DB-020. Qaror: 01_product: Hisob ochish.

## AC-004 REG-04 - Birinchi va oxirgi egasi

Birinchi egani boshqa reviewer tekshiradi; ikki parallel revoke oxirgi ownerni yo‘qotmaydi.

Bog‘lanish: CAP-014; DB-023, DB-027. Qaror: 01_product: Hisob ochish.

## AC-005 REG-05 - Dublikat hisob va kanal xatosi

Kontakt collision avtomatik merge emas; SMS uzilishida user tanlagan email/WhatsApp yo‘li, eski kod invalid.

Bog‘lanish: CAP-002; DB-001, DB-002, DB-003, DB-006. Qaror: 01_product: Email WhatsApp.

## AC-006 DB-01 - Profil va ta’lim tarixi

Bitirgan/almashtirgan enrollment tarixi saqlanadi, umumiy profil va arizalar qoladi.

Bog‘lanish: CAP-004; DB-012, DB-015. Qaror: 01_product: Rollar.

## AC-007 DB-02 - FK, UNIQUE va scope

Orphan FK DBda rad; boshqa org/muassasa IDsi read/list/create/exportda403/404; oddiy entitylarda polymorphic target yo‘q.

Bog‘lanish: CAP-036; DB-041, DB-023, DB-034. Qaror: 04_architecture: INV-01..16.

## AC-008 DB-03 - Immutable shartlar

Maosh/jadval keyin o‘zgarsa oldingi attempt va qabul sharti bir xil qoladi; nashrdagi revision update rad.

Bog‘lanish: CAP-016; DB-036, DB-042, DB-050. Qaror: 02_workflows: E’lon.

## AC-009 DB-04 - Hisob, attempt, refund

Takror/out-of-order callback bitta capture/huquq; jami refund captured summadan oshmaydi.

Bog‘lanish: CAP-030; DB-071, DB-070, DB-072, DB-073, DB-074, DB-076, DB-077. Qaror: 03_services: Tariflar.

## AC-010 DB-05 - Qayta ariza va kundalik entry

Bir applicationda ko‘p attempt; kunlik total entry summasi; retry application/logni ko‘paytirmaydi.

Bog‘lanish: CAP-022; DB-042, DB-057, DB-090. Qaror: 02_workflows: Ariza va Kundalik.

## AC-011 SVC-01 - Katalog va eligibility

Paid part-time, umumiy internship, academic track va nonstudent chegaralari UI/APIga mos.

Bog‘lanish: CAP-039; DB-069, DB-070, DB-022. Qaror: 01_product: Xizmatlar.

## AC-012 SVC-02 - O‘rin bandligi

Bir qolgan o‘ringa ikki parallel ACCEPT: biri200, biri409, occupied_count=capacity.

Bog‘lanish: CAP-011; DB-035, DB-046, DB-041. Qaror: 02_workflows: Bo‘sh o‘rin.

## AC-013 SVC-03 - Muddatsiz ish va kelishiladigan vaqt

PART_TIME end_date NULL mumkin; NEGOTIABLE arizada konflikt ochiq, STRICT blok, UNKNOWN alohida.

Bog‘lanish: CAP-016; DB-036, DB-038, DB-016. Qaror: 02_workflows: Moslik.

## AC-014 SVC-04 - Ish boshlanishi va yakuni

OFFER ACCEPT darhol employed_countni oshirmaydi; ikki tomon START tasdig‘idan keyin ACTIVE.

Bog‘lanish: CAP-012; DB-047, DB-048. Qaror: 02_workflows: Ariza va ish.

## AC-015 SVC-05 - Nashr muddati/refund/kredit

POST30kun publishdan boshlanadi; rad etilgan unused order refund yo‘li; takror kompensatsiya yo‘q.

Bog‘lanish: CAP-029; DB-075, DB-071, DB-076, DB-077. Qaror: 03_services: Tariflar.

## AC-016 LOG-01 - Oddiy ish kundaligi chegarasi

PART_TIME nomzodga diary topshirish majburiyati yo‘q; /logs orqali jobengagementga kundalik ochilmaydi.

Bog‘lanish: CAP-012; DB-047, DB-049. Qaror: 02_workflows: Amaliyotni faollashtirish.

## AC-017 LOG-02 - Sana, jami va kesishma

Kelajak/enddan tashqari sana rad; ikki timed entry kesishmasi rad; daqiqa-onlyga noaniqlik izohi.

Bog‘lanish: CAP-022; DB-055, DB-056, DB-057. Qaror: 02_workflows: Kundalik.

## AC-018 LOG-03 - Reja, dalil va sir

Vazifa ayni reja/placementdan; karantin fayl ko‘rinmaydi; mijoz siri majburiy emas; signed access scope.

Bog‘lanish: CAP-017; DB-050, DB-053, DB-058, DB-018. Qaror: 02_workflows: Kundalik.

## AC-019 LOG-04 - Review va yangi revision

Mentor3ishkun reminder; teacher separate; old revision approval yangi tahrirni avtomatik tasdiqlamaydi.

Bog‘lanish: CAP-023; DB-059, DB-060, DB-056. Qaror: 02_workflows: Kundalik.

## AC-020 LOG-05 - Qoralama, offline va yakun

Logout private draftni tozalaydi; stale version412; reja/soat/returned yopilmasa COMPLETED rad.

Bog‘lanish: CAP-025; DB-055, DB-056, DB-054. Qaror: 02_workflows: Kundalik.

## AC-021 RAT-01 - Formula va versiya

Weights100, to‘liq required scores; schema/rubric revision o‘zgarmas; academic/workplace ajratiladi.

Bog‘lanish: CAP-027; DB-062, DB-063, DB-065, DB-066. Qaror: 02_workflows: Reyting.

## AC-022 RAT-02 - Kim baholashi va antifraud

Faqat completed relation ishtirokchisi; self-rating va bir relation/rater/rubric dublikat rad.

Bog‘lanish: CAP-027; DB-064, DB-049, DB-047. Qaror: 02_workflows: Reyting.

## AC-023 RAT-03 - Kam baho va unrated

n<5 score public emas; yangi user0 emas; n, vaqt va versiya ko‘rinadi; bir munosabat bir ovoz.

Bog‘lanish: CAP-040; DB-068, DB-062. Qaror: 02_workflows: Reyting.

## AC-024 RAT-04 - Ikki tomon fikri va retaliation

Blind ikkala submission yoki14kun; private academy assessment public emas; haqorat/PII review.

Bog‘lanish: CAP-027; DB-064, DB-065, DB-078. Qaror: 02_workflows: Reyting.

## AC-025 RAT-05 - E’tiroz va search ta’siri

14kun appeal, independent review; nizoli ovoz/n qayta hisoblanadi; MVP search rating ishlatmaydi.

Bog‘lanish: CAP-028; DB-067, DB-068, DB-079. Qaror: 02_workflows: Reyting.

## AC-026 AUTH-01 - Email/WhatsApp/SMS

VERIFY_CONTACT kodi LOGIN yoki RECOVERYga o‘tmaydi; 5min/5urinish/60s, replay va resend testi.

Bog‘lanish: CAP-002; DB-003, DB-002, DB-005. Qaror: 01_product: Email WhatsApp.

## AC-027 AUTH-02 - Rol va appointment qabuli

Yangi odam olmagan rolini oldindan talab qilmasdan tokenni o‘z verified kontaktida qabul qiladi; appointment o‘zi student scope bermaydi.

Bog‘lanish: CAP-015; DB-025, DB-032, DB-052. Qaror: 01_product: Ulanish.

## AC-028 SEC-01 - Scope bekori va self-review

Revoked membership eski sessiyada ham ishlamaydi; list/export/jobs bir xil guard; self-review403.

Bog‘lanish: CAP-036; DB-004, DB-023, DB-051, DB-052. Qaror: 04_architecture: INV-15.

## AC-029 SEC-02 - Fayl va private kesh

MIME/magic/size/scan; signed URL current authorization; private javob no-store, shared cacheda yo‘q.

Bog‘lanish: CAP-003; DB-018, DB-058. Qaror: 04_architecture: Xavfsizlik.

## AC-030 OPS-01 - Outbox va xarajat

DB commitdan keyin crash/retry bir inbox va cheklangan delivery; private matn tashqariga chiqmaydi.

Bog‘lanish: CAP-031; DB-086, DB-087, DB-088. Qaror: 03_services: Xabarlar.

## AC-031 OPS-02 - Scam, moderation va appeal

Jiddiy flag vaqtli hide; inson qarori/sabab; appeal boshqa reviewer, existing relation dalili saqlanadi.

Bog‘lanish: CAP-033; DB-078, DB-079. Qaror: 03_services: Firibgarlik.

## AC-032 OPS-03 - Support va incident

Business-hours due, P1 navbatchi dalili; internal note mijozga chiqmaydi; parol/OTP so‘ralmaydi.

Bog‘lanish: CAP-034; DB-080, DB-081, DB-093. Qaror: 03_services: Yordam.

## AC-033 OPS-04 - Retention va restore-delete

Eksport boshqa odam data bermaydi; delete manifest backup restoreda qayta qo‘llanadi, legal hold aniq muddatli.

Bog‘lanish: CAP-035; DB-082, DB-083, DB-084, DB-094. Qaror: 03_services: Maxfiylik.

## AC-034 OPS-05 - Backup va pul tiklash

Real izolyatsiyalangan restoreda RPO/RTO o‘lchanadi; provider orqali oxirgi capture/refund moslashtiriladi.

Bog‘lanish: CAP-037; DB-094, DB-077, DB-073. Qaror: 04_architecture: Tiklash.

## AC-035 OPS-06 - Qidiruv, SEO va qulaylik

Expired searchdan chiqadi; noindex private auth o‘rniga emas; 320/360px va klaviatura, WCAG2.2AA dalili.

Bog‘lanish: CAP-001; DB-035, DB-036, DB-013. Qaror: 03_services: Public sahifalar.

## AC-036 OPS-07 - Yuklama va o‘lchov

100sessiya/10rps/20min workload p95 va5xx o‘lchanadi; cohort/dedup va 2tomon START statistikasi.

Bog‘lanish: CAP-037; DB-091, DB-093. Qaror: 04_architecture: Kuzatuv.

## AC-037 OPS-08 - Moliya va ishga chiqish

62,72mln sezgirlik misoli taxmin deb belgilangan; postMRRemas; merchant/fiskal/legal hujjatlar tashqi gate.

Bog‘lanish: CAP-038; DB-071, DB-072, DB-077. Qaror: 03_services: Moliyaviy reja.

## AC-038 OPS-09 - Migratsiya va rollback

UUID/history saqlanadi; dryrun duplicates/orphans/sums; expand-contract, backup va smoke test dalili.

Bog‘lanish: CAP-036; DB-012, DB-015, DB-041. Qaror: 04_architecture: Migratsiya.
