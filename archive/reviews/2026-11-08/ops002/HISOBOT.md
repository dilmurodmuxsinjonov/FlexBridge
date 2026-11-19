# OPS-CODEX-002 — mustaqil opportunity apellyatsiyasi

Haqiqiy current-MFA OWNER/HR/HOST_COORDINATOR oxirgi REJECT qaroriga o'z tashkiloti doirasida apellyatsiya beradi. Appellant request sessiyasidan olinadi. Alohida mustaqil current-MFA MODERATOR ishni claim qiladi va faqat shu reviewer API-111 orqali UPHOLD yoki REOPEN qarorini chiqaradi. REOPEN faqat DRAFTga qaytaradi; moderation approval, payment yoki publish cheklovini chetlab o'tmaydi.

PostgreSQL original qaror/sabab va revision/skill/shift nusxasini saqlaydi. Salary maydonlari decimal string, snapshot limiti aynan PostgreSQL jsonb::text baytlari bilan o'lchanadi. INSERT va RESOLVED triggerlari latest/current REJECTED/revision/dalilni tekshiradi. Asl so'rov, snapshot va moderation_actions SQL orqali o'zgartirilmaydi/o'chirilmaydi. State/action/audit bitta tranzaksiyada; accepted relation va application evidence saqlanadi.

Vakolat business locklardan keyin qayta tekshiriladi; user/session/platform grant/catalog FOR SHARE orqali commitgacha saqlanadi. O'z qarorini ko'rish, appellant/revision author va har qanday org membership tarixi bo'lgan reviewer bloklanadi. Revocation avval commit bo'lsa keyingi amal rad etiladi; vakolat locki avval olinsa revocation shu operatsiya commitini kutadi. Unassigned queue faqat minimal metadata, dalil faqat appellant yoki assigned independent reviewerga. Private javoblar no-store, request body bounded.

Tekshiruv dalili:

- Final source `c46ff70215b20101cbda457350c5af705cdeafa5`: native PostgreSQL **250 passed**, failure/error/skip0, bitta framework deprecation warning,586.00s. `full_junit.xml`, `summary.json`. Run davomida runtime/migration/test source o'zgarmadi.
- O'sha commit uchun GitHub CI42497555184 va42497559426 successful, complete250 test. Evidence-only commit uchun ham CI tekshiriladi. `source_manifest.json` committed Git byte hashlarini beradi; Windows newline normalizatsiyasi bilan farq qilishi mumkin.
- Alohida regressiyalar: post-peer selected25 va authority-lock2 passed. Parallel submit/claim/decision, replay/conflict, mid-request role/session revocation, lock serialization, audit rollback, stale state/content/latest decision, original rationale access, SQL fake snapshot rejection, Unicode/escape limit va full decimal precision tekshirildi.
- Ikkinchi Python jarayoni PostgreSQL yozuvini o'qidi. HTTP sinovlar TestClient orqali; bu native Uvicorn/server-restart/browser yoki live-provider E2E degani emas. Accepted relation preservation explicit trusted legacy SQL fixture bilan tekshirildi, frontend oqimi deb ko'rsatilmaydi.
- Populated0006→0007 native upgrade:100→101 runtime jadval; original rejection aynan saqlandi va uning UPDATE amali bloklandi. `verify_upgrade.py`, `upgrade.json`. Canonical94 model soni o'zgarmadi.

Actual read-only GitHub Copilot CLI review bajarildi; modeli mustaqil aniqlanmadi. Revocation oraliği, original rationale yetishmasligi va DB evidence integrity tuzatildi; size boundary PostgreSQL bilan tenglashtirildi. Reviewning password-only fixture haqidagi xulosasi noto'g'ri: test avval PASSWORD session yaratib, keyin SQLda MODERATOR grant beradi. `copilot_review.md` va `copilot_assessment.md` tafsilotni ajratadi; bu avtomatik approval emas.

Dastlabki fixture application/opportunity mapping xatosi va keyingi revoked-session401 o'rniga403 kutgan test xatosi alohida saqlandi. Runtime ularni o'tkazish uchun yumshatilmadi: final test aynan401 AUTH_REVOKED va403 FORBIDDEN_ROLE talab qiladi. Failed full JUnitdagi ephemeral test secretlar niqoblandi; yakuniy dalil sifatida initial failure fayllari ishlatilmaydi.

132 canonical/helper kontraktda46 explicit handler va86 placeholder501, missing0. Bu ro'yxatdan o'tgan handler soni; API-111ning qo'llangan doirasi opportunity rejection appeal. Boshqa moderation/scam/public-report/rating, frontend/live provider/DR va barcha42 AC hali qabul qilinmagan. **pilot_ready false**. Keyingi: Issue41 / ORG-CODEX-003A.
