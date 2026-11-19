# FIX-CODEX-002 va CAN-CODEX-001

2026-11-07, Asia/Tashkent; Codex. Foydalanuvchi “davon ettir” dedi.
Avval REV-004dagi uchta muammo tuzatildi, so'ng CAN backend paketi bajarildi.
Oldindan mavjud ishchi o'zgarishlar va tarixiy review artefaktlari saqlandi.
Git push/deploy yoki boshqa agent ishlatilmadi.

## Natija

Profil, malaka, private CVni ulash va canonical jadval APIlari yozildi.
Matching 28 kunlik haqiqiy sanalar, amal muddati, istisnolar, ALL/ANY guruhlar,
qatnov buferi va yarim tun chegarasi bilan hisoblaydi. Backend qo'llanma:
`backend/CANDIDATE.md`. Butun R1/pilot hali qabul qilinmagan.

**Umumiy suite: 150 passed, 1 warning, 459.33s; exit 0.**
**Yakuniy CAN: 44 passed, 1 warning, 123.53s; exit 0.**
Failure/error/skip har ikkala yurishda 0. Ogohlantirish avvaldan mavjud bo'lgan
Starlette TestClient/httpx deprecationidir. Bu ikki yurishdagi testlar ustma-ust;
150 va 44 sonlari qo'shib hisoblanmaydi.

## Tuzatishlar va implementatsiya

1. Availability `valid_from`/`valid_to` inclusive chegaralari SQL filtri va har
   bir haqiqiy smena sanasida tekshiriladi. Expired/future qoida moslik bermaydi.
2. STIPEND yozuvi MONTH salary davridan qayta tiklanadi; lentada HOURLYga yo'qolmaydi.
3. Matching batchlari at most 100 e'lon. To'rt SELECT: published current revisions,
   shu revisionlarning smenalari, o'z nomzodining sana bo'yicha qoidalari/istisnolari.
   UUID cursor oxirgi tekshirilgan e'longa tegishli, shu sabab bo'sh match sahifasi
   keyingi sahifani to'smaydi. Bu query dalili, production load benchmarki emas.
4. `API-026`, `032`, `033`, `028`, `035`, `036` placeholderlari haqiqiy handlerga
   almashtirildi. Own profile GET va active skill catalog GET qo'shimcha yordamchilar.
5. Profil faqat sessiya actoriga; talabalik majburiy emas. Client ID/verification/
   visibilityni o'zgartira olmaydi. Skill faqat catalogdan, self-declared; APPROVED
   va shu nomzodga bog'liq casegina verified. Level o'zgarishi verified bog'lanishni tozalaydi.
6. CV faqat own, nondeleted CLEAN PDF. PENDING_SCAN/SCANNING/QUARANTINED va begona
   fayl rad etiladi. Link/unlink audit bilan atomik; o'zga actorlarga download huquqi berilmaydi.
7. Weekly PUT to'liq o'z jadvalini almashtiradi; same validity/timezone intervallar
   union qilinadi. Exception PUT faqat inclusive sana oynasini almashtiradi.
   GiST EXCLUDE zid intervalni rad etadi va butun yozuv rollback bo'ladi.
8. WRITElar candidate profile row lock bilan ketma-ket. Matching REPEATABLE READ
   snapshoti concurrent edit paytida eski/yangi qoidalarni aralashtirmaydi.
9. Preview faqat current PUBLISHED/unexpired revisionga. 28 kunlik oyna e'lon
   start/end sanalari bilan kesiladi; `checked_to` exclusive. ALL/ANY har bir
   guruhning real occurrence'lariga qo'llanadi; bo'sh tekshiruvdan MATCH yo'q.
10. ONSITE/HYBRID default oldin/keyin 30 min, REMOTE 0; client aniq 0–180 tanlashi
    mumkin. Qatnov buferi o'lchangan transport vaqti emas. Yarim tun va yakshanba
    oldingi/keyingi haqiqiy sana bilan tekshiriladi. Formula `1.4.1-can`.
11. Private profile/schedule/matching/file javoblari no-store; body limiti va
    max-length/range/extra-field tekshiruvlari bor. Auditga CV yoki profil matni yozilmaydi.

## Inventar va ma'lumotlar

`contracts.json`: **132 canonical, 33 explicit handler, 99 ta 501, missing 0**.
Bu butun mahsulot tayyorligi foizi emas. Shu paketda yangi dependency yoki DDL yo'q;
schema 0003_iam_flows, 98 jadval bo'lib qoladi. Mavjud user bazasi ko'chirilmadi/
o'chirilmadi. Native PostgreSQLdagi barcha yozuvlar disposable random test DBlarda.

## Sinov dalillari

- FIX maqsadli sinovlari: 8 passed, 27 deselected, 1 warning, 14.25s; CAN algoritmi
  qo'shilgach yana 8 passed, 14.48s. Uch e'lon uchun ham 4 filtrlangan SELECT.
- CAN maqsadli yurishi: 43 passed, 1 warning, 50.73s (`candidate_junit.xml`).
- Umumiy suite `run_validation.py` bilan 150 test yig'ilgan holatda bajarildi.
  U boshlanganidan keyin generic-preview uchun avvalgi top-level result/window
  metadata saqlanishi tuzatildi va bittadan qo'shimcha test qo'shildi.
  Shu oxirgi o'zgarishdan keyin barcha 44 CAN testi `run_validation.py candidate`
  orqali qayta bajarildi (to'liq eski suite ikkinchi marta takrorlanmadi).
  Dalillar: `summary.json`, `junit.xml`, `pytest_stdout.txt` va
  `candidate_final_summary.json`, `candidate_final_junit.xml`, tegishli chiqish fayllari.
- `git diff --check` xatosiz (Git LF/CRLF bildirishnomalari); o'zgargan Python
  fayllar AST parse tekshiruvidan o'tdi. `source_hashes.json` yakuniy source dalili.
- Test bazalarining qolmagani admin katalogida tekshirildi; ishga tushirilgan
  dedicated PostgreSQL serveri yakunda to'xtatildi. Mavjud loyiha bazalariga tegilmadi.

Yangi testlar: actor isolation, malicious fields, catalog va skill verification,
CV holatlari/egalik/deleted/MIME, interval union/subtraction, conflict rollback,
parallel replacements, repeatable snapshot, validity boundaries, 28-kunlik exception,
remote/onsite va Sunday midnight, zero occurrences, cursor advancement va auth.
Oldingi group matching testining availability fixturelari talabdagi 30 minutlik
qatnov buferiga kengaytirildi; ALL/ANY kutilmalari kuchsizlantirilmadi.

Oraliq CAN yurishida CLEAN test fixtureda storage version/scanned_at yetishmagani
uchun DB constraint uni rad etdi (1 failed, 31 passed). Fixture to'liq metadata bilan
tuzatildi; constraint o'zgartirilmadi. Ilk targeted collectiondagi import typo ham
sinovdan oldin tuzatildi. Bu holatlar yakuniy natija sifatida berilmaydi.

## Chegara va keyingi ish

- R1 jadval zonasi Asia/Tashkent. Yangi request boshqa zonani rad etadi; oldindan
  DBga kiritilgan boshqa zona UNKNOWN beradi. CV/skill level va jadval input shakllari
  mavjud modelga mos implementatsiya qarorlari, alohida foydalanuvchi siyosati deb belgilanmaydi.
- EDU enrollment va mustaqil skill/education review workflow bu paketga kirmaydi.
  Self-service ularning o'rniga tasdiq bermaydi. Skill catalog alohida provision qilinadi.
- APP doirasidagi HR CV access hali yo'q. CV mavjud fayl retention classini meros
  oladi; CV-specific retention va linked-file-aware purge OPSda alohida hal qilinadi.
- Frontend/browser, real SMS/payment, live MinIO/ClamAV, Docker deployment va DR drill
  ushbu paketda sinalmagan. Oldingi adapter tests/test doubles live integration dalili emas.
- To'liq search/ranking va application eligibility/schedule-policy enforcement JOB/APPda
  qoladi; 28 kunlik preview butun kelajak ish muddatiga kafolat emas.
- Navbatdagi kichik bo'lim: ORG — organization onboarding, capability va dastlabki
  boshqaruvchining mustaqil tekshiruv oqimi. Keyin EDU va qolgan canonical modullar.
