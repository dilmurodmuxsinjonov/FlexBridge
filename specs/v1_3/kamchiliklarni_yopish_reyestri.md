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
