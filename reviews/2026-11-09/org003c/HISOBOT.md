# ORG-CODEX-003C1 — fixed-revision existing-staff OWNER continuity

Existing active staff current MFA/own verified-contact bilan faqat o'ziga murojaat
qiladi. Original staff grant, account version, contact/24h consent/evidence va exact
active OWNER roster immutable. MODERATORning RECOMMEND qarori grant bermaydi; alohida
assigned current-MFA COMPLIANCE tasdig'i grant/event/case/recovery/auditni bitta UOWda
yozadi. Eski OWNER/member/staff grantlari saqlanadi. Fixed revision1, terminal NEEDS_INFO
uchun yangi murojaat kerak. Generic review/resubmit va account recovery alohida yopildi.

Joriy native PostgreSQL dalili:

- Fresh DDL0010 smoke:107 runtime table. Canonical94 o'zgarmadi.
- Initial4-case run:3 failed/1 passed,14.998s. Runtime submit javobi insert_rowdagi
  partial case dictionarydan decision_reason olishga uringandi; UOW rollback bo'ldi.
  Javob persisted rowdan olindi; test yoki SQL himoya yumshatilmadi. Initial failure
  `initial_flow_junit.xml`da saqlandi. Keyingi3 flow passed,12.18s.
- Security29 passed,1 framework warning,127.62s: real role/MFA/independence, private
  evidence, type-forgery, stale contact/account/grant/roster/evidence, actual DB clock
  expiry (test-only shortened deadline), timezone-stable contact binding.
- History8 passed,46.54s: HTTP revoke/reinvite va reviewed OWNER regrantdan keyin yangi
  request; platform grant replacement stale claimni jonlantirmaydi; immutable SQL proof,
  account-kind isolation, second-process service receipt. Bu bearer transport testi emas.
- Transactions16 passed,77.85s: parallel same/different-applicant intake, duplicate claims/
  recommendation/finalization single effect; owner objection/withdrawal race; grant,
  review/event/audit failures va late reviewer expiry/deferred actor/route proof rollback;
  initial intent/claim/recommendation audit failureda partial SQL qolmaydi.
- Populated0009->0010:105->107; old initial/addition predicate tail va full departure
  function saqlandi, revoked grant/event row aynan saqlandi; distinct new grant,
  duplicate-active rejection va history immutability o'tdi. Bu trusted SQL index/upgrade
  probe, HTTP grant/legal identity dalili emas.

fa40e54 bilan old IAM/ownership/appeal/C birlashgan native263 passed,0 failure/error/skip,
1 warning,857.152s. GitHub393-test CI42528552035/42528625943 ikkovi ham successful.
Keyin Copilot actual pinned source review matching POST stale closure'ni chetlab o'tganini
topdi: yangi4 testdan3 failed/1 passed (`initial_replay_junit.xml`). Old yashil testlar
bu holatlarni qamramagan. Approval freshness guardi oldindan bor edi.

ef4a94b matching receiptni case lock/prelock/prune bilan tuzatdi. Izolyatsiyalangan worktree
sinovi keyin aynan shu commitga saqlandi; root branch fast-forward qilindi. Post-review
native9 passed,43.74s: replay4, negative outcomes3, account reset isolation1, parallel
full-flow1. Native263 fa40e54 baseline natijasidir, ef4da yana263 passed deb aytilmaydi.
Final ef4a94b uchun full401-test CI42534534532/42534538671 successful,
219.40s/257.95s. Follow-up Copilot read-only review exit0: replay/outcome bo'yicha
concrete defect topilmadi; u testlarni ishlatmagan yoki SHAni tekshirmagan. Codex
Git tree/SHA va CI natijalarini tekshirdi. Ikki planning review actual exit0, initial e'tirozlar
asosida fixed-revision scope toraytirildi. Model identity mustaqil aniqlanmadi; planning
review implementatsiya/test approval emas. Source implementation Codexda.

SQL relational metadata/quorum/current-role proof, actual bearer MFA/contact HMAC API
chegarasida; direct database writers trusted. Human reviewers authority evidence'ni
baholaydi; kod legal identity, document truth yoki owner inaccessibilityni isbotlamaydi.
TestClient/synthetic role/contact/CLEAN-file metadata ishlatildi. Zero-active-owner/no-staff
va manual same-account recovery, live providers/browser/UI/DR va42 AC umumiy qabuli ochiq.
Canonical inventory46 explicit/86 placeholder bo'lib qoladi. **pilot_ready false**.

Alohida confirmed qoldiq: API075 old organization membership revoke transient MFA
preflightdan keyin actual HTTP session revocation tugasa ham200 va REVOKED beradi.
Bu oldindan authenticated in-flight request; anonim bypass emas. Izolyatsiyalangan
probe1 failed dalili bilan Issue47ga ajratildi; ORG003C1 qabuli uni yopmaydi.
