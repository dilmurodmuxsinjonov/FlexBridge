# ORG-CODEX-001 — Organization onboarding va mustaqil tekshiruv

2026-11-07, Asia/Tashkent. Codex; foydalanuvchi “davon etamiz” dedi.
Avvalgi ishchi o'zgarishlar saqlandi. Boshqa agent, commit/push yoki deploy ishlatilmadi.

## Bajarilgan paket

- Canonical API-008/065/066/067/071/072/075/109/110 uchun haqiqiy handlerlar.
  Qo'shimcha claim/detail/evidence va pending self-join evidence helperlari.
- MFA bilan onboarding; normalizatsiyalangan STIR, advisory lock va unique index.
  So'rov yuborish vakolat bermaydi. New organization uchun PENDING_VERIFICATION
  membership va ORG_REPRESENTATIVE case; verified mavjud organizationga faqat
  explicit HR/HOST_COORDINATOR/MENTOR/BILLING mansublik so'rovi. OWNER yashirin berilmaydi.
- Birinchi OWNER faqat assigned PLATFORM MODERATOR/MFAning mustaqil approvali bilan.
  O'z so'rovi yoki tashkilotga a'zolik yozuvi bor moderator review qila olmaydi.
  Competing bootstrap approvallar organization row lock bilan bittagacha cheklanadi.
  Verified, lekin faol ownersiz organization bootstrapni qayta ochmaydi.
- JOB_EMPLOYER va INTERNSHIP_HOST alohida evidence/review/approval. Publish/resume
  verified organization va aynan shu org/capabilityga APPROVED proof bilan ACTIVE
  capabilityni tekshiradi; moderation/entitlement/quota/role himoyalari saqlandi.
- Immutable revision submissions va scope FKlar. NEEDS_INFOdan original requester
  yangi evidence revision yuboradi; stale expected_revision yoki replay rad etiladi.
  Applicant account/membership vakolati va faylning CLEAN/deleted/ownership holati
  approvalda qayta tekshiriladi. Qaror/effect/audit/grant bitta transactionda.
- Material profile edits tasdiqlanguncha saqlangan/public organizationni o'zgartirmaydi.
  Tax ID/status client tomonidan o'zgartirilmaydi. Public organization API maxfiy
  dalil, tax/legal name va shaxslar identifikatorlarini bermaydi.
- Assigned reviewer faqat IN_REVIEW paytida linked evidence uchun 60s signed URL oladi;
  pending self-join evidence faqat o'z org OWNERiga. No-store/body/DTO/range cheklovlari bor.
- Last-active-owner himoyasi, concurrent revoke, authoritative SQLdan darhol scope
  revoke; API-073 OWNER bilan cheklangan. Existing membership approvallar ham umumiy
  org lock oladi va self-join evidence holatini qayta tekshiradi.

Qo'llanma va aniq request/response chegaralari: `backend/ORGANIZATIONS.md`.

## Sxema va inventar

`0004_org_onboarding`: normalized tax-ID unique index, bitta immutable submission
yordamchi jadvali, composite scope FK va besh ORG catalog role. Privileged user/grant
yaratilmaydi. Runtime **99 jadval**, canonical model esa o'zining 94 jadvali bilan saqlangan.

`contracts.json`: **132 canonical / 42 explicit / 90 ta501 / missing0**. Operator
queue/decision hozir ORG case turlarini bajaradi; bu boshqa EDU/CAN verification yoki
barcha operator acceptance mezonlari bajarilgan degani emas.

## Tekshiruv

**179 passed, 1 framework warning, 562.85s; exit 0, failure/error/skip 0.**
Runner 565.05s. `summary.json`, `junit.xml`, pytest stdout/stderr saqlangan.
2026-11-08 davom etishda natija va source hashlar qayta o'qilib mosligi tekshirildi;
disposable bazalar qolmagan, ishga tushirilgan test serveri to'xtatildi.

- Dastlabki targeted yurish: 8 failed / 17 passed / 1 warning, 79.68s. Sabab:
  fixture TRUNCATE migration-seeded role_catalogni ham o'chirgan. Tozalash reference
  catalogni saqlaydigan qilindi; barcha grantlar/memberships va mutable data tozalanadi.
  Runtime rolni avtomatik yaratish yoki himoyani zaiflashtirish kiritilmadi.
- Qayta targeted yurish: **25 passed, 1 warning, 81.95s**. So'ng uchta qo'shimcha
  suspended-requester/affiliated-reviewer/cross-org proof regressiyasi to'liq suitega qo'shildi.
- Native uvicorn + HTTP + real disposable PostgreSQL: **10/10** (`native_smoke.json`).
  Registration -> independent claim/approve -> real scoped membership read -> public
  metadata -> JOB_EMPLOYER claim/approve -> public badge -> last-owner revoke 409.
- Populated 0003 upgrade (`check_upgrade.py`, `upgrade.json`): mavjud user password
  hash va tashkilot yozuvi saqlandi, head0004/runtime99. Alohida collision bazada ikki
  tax-ID normallashib teng bo'lganda upgrade rad etildi; head0003, ikkala org va user
  saqlandi. Har ikkala disposable baza yakunda o'chirildi; hech qanday mavjud foydalanuvchi
  bazasi konvertatsiya qilinmadi. Bu sintetik upgrade dalili, production backup/restore sinovi emas.
- `source_hashes.json`, AST parse, OpenAPI/canonical inventory va `git diff --check`
  yakuniy artefakt tekshiruvida yoziladi.

SQL-backed regressiyalar scope, spoofed fields, MFA, own CLEAN evidence, parallel
tax registration/first-owner approvals, separate capability/publish, stale revision,
immutable submissions, evidence deletion/revocation, held material edit, legacy join,
suspended ownerning bootstrapni ochmasligi, last-owner concurrent revoke va normalized
unique constraintni qamraydi. Oldingi organization fixturelari endi explicit trusted
capability proofs bilan tayyorlanadi; bu runtime public seed/provisioning yo'li emas.

## Chegaralar va keyingi paket

- Identifier format 3–32 ASCII digit va whitespace/hyphen normalization — bounded
  implementatsiya qarori. Official STIR registry/huquqiy format tekshiruvi ulanmagan;
  human review haqiqiy dalilni tekshirishi kerak. Due target ikki weekday; holiday calendar yo'q.
- Native/TestClientda CLEAN file metadata fixture ishlatildi. Jonli scanner/S3,
  rasmiy soliq reyestri yoki inson shaxsi tasdig'i shu dalil bilan sertifikatlanmaydi.
  Reviewer downloadida S3 presign test double; real provider staging yo'q.
- Initial MODERATOR provisioning mustaqil administrativ jarayon bo'lib qoladi.
  Role catalog entryning o'zi hech qanday vakolat bermaydi.
- Frontend/browser, live providerlar, Docker deployment, retention purge va restore
  drill sinalmagan. Pilot hali tayyor emas; qolgan 90 canonical placeholder bor.
- Navbatdagi `ORG-CODEX-002`: 24h contact-bound invitationlar, explicit role acceptance,
  ownership qo'shish/almashtirish/recovery; keyin EDU. Hozirgi paket ularni bajardi deb belgilanmaydi.
