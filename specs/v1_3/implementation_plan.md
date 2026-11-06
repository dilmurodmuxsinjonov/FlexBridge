# FlexBridge amalga oshirish rejasi 1.3

2026-10-30. Ushbu reja ilova qurilganini bildirmaydi.

Arxitektura: modulli monolit; TypeScript web, Django/DRF API, PostgreSQL, private fayl ombori va outbox worker. Versiyalar qurish boshida qo‘llab-quvvatlanadigan patch bilan lock qilinadi. SQL capacity, offer, billing va scope invariantlarini bir tranzaksiyada saqlash uchun tanlandi. Yakka dasturchi uchun minimal deploy/CI; katta infratuzilma o‘lchovsiz qo‘shilmaydi.

G0 - mahsulot/huquq/retention/narx/kvota va muassasa kelishuvi.
G1 - identity/candidate/org/institution; DDLni migratsiyaga aylantirish, INV-01..16, ruxsat va recovery.
G2 - publish/matching/application/interview/offer/job-confirm; nonstudent va student UAT, free pilot.
G3 - host/academic assignment, reja, kundalik, ikki alohida review, axborot hisobot.
G4 - moderatsiya/support/privacy/notification, incident, restore, load va qulaylik.
G5 - merchant/callback/refund/fiskal/PITR/reconciliation; shundan keyin paid_checkout.
G6 - tasdiqlangan rubric va independent appeal; shundan keyin rating flag.

backend/apps: identity, candidates, organizations, institutions, opportunities, matching, applications, internships, diary, ratings, billing, notifications, moderation, support, privacy, audit.
web/features va route oilalari sahifalar_va_bolimlar.csv bilan; docs ER/OpenAPI/runbook; infra deploy/backup; tests haqiqiy PostgreSQLdagi business invariant/permission/concurrency/contract va UAT.

Baza: 94 jadval, 923 maydon, 205 FK. Model JSON, ER SVG/Mermaid va dictionary bir metadata manbasidan. schema_loyihasi.sql production migratsiya emas; cross-table qoidalar va privilege/triggerlar yakunlanishi shart.

Mavjud student ma’lumotlaridan ko‘chirish UUID/historyni saqlaydi; dry-run dublikat/orphan/sum/scope; expand-backfill-read-check-write-contract. Production reset yo‘q. Har reliz oldin backup/restore dalili, keyin smoke va rollback reja.
