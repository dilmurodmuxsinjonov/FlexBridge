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
