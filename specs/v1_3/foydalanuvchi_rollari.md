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
