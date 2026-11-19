# FlexBridge 1.4 Verification Report: Candidate Ratings, Double-Blind Reviews, Rubrics & Appeals Hub (FB-166)

**Sana**: 2026-11-15  
**Bosqich**: FB-166 / Issue #166  
**Muallif**: Antigravity Autonomous Lead  
**Holat**: 100% YASHLI (ALL 10 PHASES PASSED, 105/105 TOTAL REGRESSION PASS)  

---

## 1. Qamrov va Maqsad
Ushbu bosqichda Nomzod Portalida baholash, ikki tomonlama maxfiy ko'rib chiqish (Bilateral Double-Blind), rubrika mezonlari asosida baholash, baholarga e'tiroz bildirish (Appeals) hamda saqlangan e'lonlarni boshqarish (Saved Opportunities) to'liq amalga oshirildi:
- `/nomzod/baholar` - Nomzod baholari, agregatsiyalangan ball, rubrika mezonlari, 14 kunlik Double-Blind himoya vizualizatori, yakunlangan munosabatlarni baholash va e'tiroz modal oynasi.
- `/nomzod/saqlanganlar` - Saqlangan vakansiyalar va amaliyot e'lonlari ro'yxati, ish rejimi va holat teglari, bir klik bilan o'chirish va ariza topshirish havolalari.

---

## 2. Kanonik API va BFF Shartnomalari
1. **API-057**: `GET /api/v1/me/ratings`
   - Proxied via: `GET /api/bff/candidate/ratings`
   - Nomzod umumiy reytingi, namunalar soni ($n$), hisoblash sanasi va maxfiylik holati (`UNRATED`, `WITHHELD_INSUFFICIENT_SAMPLE`, `PUBLISHED`).
   - `AC-023`: $n < 5$ bo'lganda anonimlik va ishonchlilik uchun ball yashiriladi va aniq izoh beriladi; $n = 0$ holati nol ball emas, baholanmagan deb belgilanadi.
   - `AC-024`: 14 kunlik Double-Blind himoyasi - har ikki tomon topshirmaguncha baholovchi shaxsi va sharh yashirin saqlanadi.
2. **API-047**: `POST /api/v1/engagements/{id}/ratings`
   - Proxied via: `POST /api/bff/candidate/engagements/[id]/ratings`
   - Yakunlangan ish munosabatini faol rubrika mezonlari (`rubric_criteria`) bo'yicha baholash (`scores: [{ criterion_id, score }]`).
   - Pydantic `extra="forbid"` sanitizatsiyasi va idempotency kaliti.
3. **API-058**: `POST /api/v1/ratings/{id}/appeals`
   - Proxied via: `POST /api/bff/candidate/ratings/[id]/appeals`
   - Nashr etilgan baholarga 14 kunlik apellyatsiya oynasida e'tiroz kiritish (`reason`, `category`, `evidence_notes`).
   - Takroriy e'tirozlarni bloklash (anti-duplication).
4. **API-004**: `POST /api/v1/saved-opportunities`
   - Proxied via: `POST /api/bff/candidate/saved-opportunities`
   - E'lonni nomzod ro'yxatiga saqlash (idempotent / toggle).
5. **API-037**: `GET /api/v1/me/saved-opportunities`
   - Proxied via: `GET /api/bff/candidate/saved-opportunities`
   - Saqlangan e'lonlar sahifalangan ro'yxati (holat, sarlavha, maosh va tashkilot metama'lumotlari).
6. **API-038**: `DELETE /api/v1/me/saved-opportunities/{id}`
   - Proxied via: `DELETE /api/bff/candidate/saved-opportunities/[id]`
   - E'lonni saqlanganlardan o'chirish (idempotent 204).

---

## 3. Xavfsizlik va Arxitektura Invariantlari
- **Frozen Main Invarianti**: `origin/main` strictly FROZEN at `764fb98496fa40857acb07844fd09fcafa99b7d6`. Zero mutations to main.
- **pg_live Invarianti**: Zero queries/mutations to `pg_live`. Barcha so'rovlar PgBouncer `127.0.0.1:5432/flexbridge` orqali.
- **Anti-CSRF Origin Guard**: Barcha mutatsiya qiluvchi BFF so'rovlarida (`POST`, `DELETE`) `verifyCsrfOrigin` orqali 403 `CSRF_ORIGIN_MISMATCH` tekshiruvi.
- **Strict IDOR Isolation**: Begona yoki mavjud bo'lmagan munosabatlar va baholarga kirish qat'iy 404/403 bilan to'siladi.
- **Anti-Slop UI Standartlari**: `#09090b` kanvas, `#121214` kartalar, Lucide SVG ikonkalari, `tabular-nums` raqamlar, 0 emojilar.

---

## 4. Test Natijalari (105/105 Yashil)
- `test_candidate_ratings_appeals_staging.py`: 10/10 PASS
- `test_candidate_offers_engagements_staging.py`: 10/10 PASS
- `test_employer_mentor_staging.py`: 8/8 PASS
- `test_university_placements_staging.py`: 7/7 PASS
- `test_candidate_profile_staging.py`: 7/7 PASS
- `test_operator_portal_staging.py`: 9/9 PASS
- `test_candidate_internship_logs_staging.py`: 8/8 PASS
- `test_university_academic_reviews_staging.py`: 8/8 PASS
- `test_employer_kanban_staging.py`: 12/12 PASS
- `test_candidate_applications_staging.py`: 12/12 PASS
- `test_opportunity_application_staging.py`: 6/6 PASS
- `test_bff_staging.py`: 8/8 PASS
