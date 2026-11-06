# To‘liq ma’lumotlar bazasi lug‘ati

Bu mantiqiy/texnik model. `?` NULL mumkinligini anglatadi. Har FK parent.idga; parentda 0..N child bo‘lishi mumkin, childda nullable bo‘lmasa aynan1 parent. Birga UNIQUE bo‘lgan FK jufti1:1 yoki shu munosabatning bitta nusxasini cheklaydi. Jadvallar ko‘pligi modulli monolitni mikroservisga aylantirmaydi.


## IAM - Hisob, kirish va ruxsatlar


### DB-001 users

Bitta shaxsning asosiy hisobi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| display_name | text / NO | - |
| status | text / NO | - |
| password_hash | text / YES | - |
| locale | text / NO | - |
| timezone | text / NO | - |
| adult_declared_at | timestamptz / YES | - |
| last_login_at | timestamptz / YES | - |

CHECK: status IN ('ACTIVE','LIMITED','SUSPENDED','DELETION_PENDING','ANONYMIZED')

INDEX: status,created_at

Parol xeshi framework orqali; ochiq parol saqlanmaydi. Tahrir updated_at server vaqti bilan.

Imkoniyatlar: CAP-002.

### DB-002 user_contacts

Tasdiqlangan yoki kutilayotgan login kontaktlari.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| channel | text / NO | - |
| normalized_value | text / NO | - |
| verified_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |
| is_primary | boolean / NO | - |

UNIQUE: channel,normalized_value

CHECK: channel IN ('EMAIL','PHONE')

INDEX: user_id,channel

WhatsApp va SMS bir PHONE kontaktining yetkazish kanali. Revoked kontakt qayta berilishi faqat tekshirilgan recovery bilan; avtomatik account merge yo‘q.

Imkoniyatlar: CAP-002.

### DB-003 auth_challenges

Maqsadga bog‘langan bir martalik kod.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / YES | DB-001 users.id |
| contact_id | uuid / YES | DB-002 user_contacts.id |
| destination_digest | text / NO | - |
| channel | text / NO | - |
| purpose | text / NO | - |
| code_hmac | text / NO | - |
| expires_at | timestamptz / NO | - |
| attempts | integer / NO | - |
| consumed_at | timestamptz / YES | - |
| superseded_at | timestamptz / YES | - |

CHECK: attempts >= 0 AND attempts <= 5

INDEX: destination_digest,purpose,created_at; expires_at

Kontakt hali mavjud bo‘lmasa digest ishlaydi; raw manzil faqat qisqa muddatli shifrlangan delivery payload. Har consume atomar va bir martalik.

Imkoniyatlar: CAP-002.

### DB-004 sessions

Qurilma va sessiyani bekor qilish.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| token_digest | text / NO | - |
| device_key_digest | text / YES | - |
| assurance | text / NO | - |
| expires_at | timestamptz / NO | - |
| revoked_at | timestamptz / YES | - |
| last_seen_at | timestamptz / NO | - |

UNIQUE: token_digest

INDEX: user_id,revoked_at; expires_at

Cookie HttpOnly/Secure; yangi qurilmada PHONE-only eski ma’lumotni ochmaydi. Revoke barcha sezgir so‘rovlarda tekshiriladi.

Imkoniyatlar: CAP-002, CAP-036.

### DB-005 mfa_credentials

TOTP/passkey va tiklash omili.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| kind | text / NO | - |
| credential_key | text / NO | - |
| secret_encrypted | text / YES | - |
| public_key | text / YES | - |
| sign_count | integer / NO | - |
| verified_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |

UNIQUE: credential_key

INDEX: user_id,revoked_at

TOTP siri kalit boshqaruvi bilan shifrlanadi. Passkey private key serverda bo‘lmaydi; recovery kodlar alohida xeshlangan qiymatlar.

Imkoniyatlar: CAP-002.

### DB-006 recovery_requests

Kontakt, dublikat va oxirgi egani tiklash.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / YES | DB-001 users.id |
| kind | text / NO | - |
| status | text / NO | - |
| requester_contact_digest | text / NO | - |
| reviewer_id | uuid / YES | DB-001 users.id |
| evidence_file_id | uuid / YES | DB-018 files.id |
| resolved_at | timestamptz / YES | - |

INDEX: status,created_at

Reviewer requester bo‘la olmaydi. Account merge FKlarni auditlangan migratsiya bilan ko‘chiradi; uchinchi tomon huquqlarini qo‘shib yubormaydi.

Imkoniyatlar: CAP-002.

### DB-007 permission_catalog

Atomar imkoniyat kodi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| code | text / NO | - |
| description | text / NO | - |

UNIQUE: code

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-036.

### DB-008 role_catalog

Rol va uning ruxsat doirasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| code | text / NO | - |
| scope_kind | text / NO | - |
| description | text / NO | - |

UNIQUE: code

CHECK: scope_kind IN ('SELF','ORG','INSTITUTION','PLATFORM')

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-036.

### DB-009 role_permissions

Rol-imkoniyat bog‘lanishi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| role_id | uuid / NO | DB-008 role_catalog.id |
| permission_id | uuid / NO | DB-007 permission_catalog.id |

UNIQUE: role_id,permission_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-036.

### DB-010 platform_role_grants

Operatorning vaqtli vakolati.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| role_id | uuid / NO | DB-008 role_catalog.id |
| granted_by_id | uuid / NO | DB-001 users.id |
| expires_at | timestamptz / NO | - |
| revoked_at | timestamptz / YES | - |

INDEX: user_id,expires_at

Faqat PLATFORM role; grantor o‘ziga grant bera olmaydi. Sezgir grant ikki mustaqil tasdiq va audit bilan.

Imkoniyatlar: CAP-036.

### DB-011 consent_events

Rozilik va huquqiy asos tarixi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| purpose | text / NO | - |
| policy_version | text / NO | - |
| action | text / NO | - |
| legal_basis | text / NO | - |
| occurred_at | timestamptz / NO | - |

INDEX: user_id,purpose,occurred_at

Append-only. Marketing opt-in alohida; xizmat uchun zarur ishlovga majburiy marketing ulanmaydi.

Imkoniyatlar: CAP-002, CAP-031, CAP-035, CAP-039.

## CAN - Nomzod, malaka va vaqt


### DB-012 candidate_profiles

Talaba bo‘lmagan va talaba nomzodning umumiy profili.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| headline | text / NO | - |
| region | text / NO | - |
| bio | text / YES | - |
| experience_months | integer / NO | - |
| visibility | text / NO | - |
| cv_file_id | uuid / YES | DB-018 files.id |

UNIQUE: user_id

CHECK: experience_months >= 0

INDEX: region

Talabalik bu jadvalning majburiy ustuni emas. CV faqat nomzod va arizasi bo‘yicha ruxsatli HRga; global ochiq eksport yo‘q.

Imkoniyatlar: CAP-003.

### DB-013 skills

UZ/RU qidiruv uchun malaka katalogi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| code | text / NO | - |
| name_uz | text / NO | - |
| name_ru | text / NO | - |
| aliases | jsonb / NO | - |
| active | boolean / NO | - |

UNIQUE: code

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-001, CAP-003.

### DB-014 candidate_skills

Malaka va tasdiq manbasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| candidate_id | uuid / NO | DB-012 candidate_profiles.id |
| skill_id | uuid / NO | DB-013 skills.id |
| level | text / NO | - |
| verification_case_id | uuid / YES | DB-019 verification_cases.id |

UNIQUE: candidate_id,skill_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Self-declared va tasdiqlangan malaka farqlanadi; case APPROVED bo‘lmasa verified ko‘rinmaydi.

Imkoniyatlar: CAP-003.

### DB-015 enrollments

Muassasaga oid ta’lim tarixi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| candidate_id | uuid / NO | DB-012 candidate_profiles.id |
| institution_id | uuid / NO | DB-028 institutions.id |
| program | text / NO | - |
| student_ref_digest | text / YES | - |
| start_date | date / NO | - |
| end_date | date / YES | - |
| status | text / NO | - |
| verification_case_id | uuid / YES | DB-019 verification_cases.id |

CHECK: end_date IS NULL OR end_date >= start_date

INDEX: candidate_id,status; institution_id,status

Tarix saqlanadi. Bir nechta ta’lim bo‘lishi mumkin; biriktirish aniq enrollmentga. Tasdiq muddati bitganda umumiy ish huquqi qoladi.

Imkoniyatlar: CAP-004, CAP-020.

### DB-016 availability_rules

Haftalik mavjudlik.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| candidate_id | uuid / NO | DB-012 candidate_profiles.id |
| weekday | integer / NO | - |
| start_minute | integer / NO | - |
| end_minute | integer / NO | - |
| valid_from | date / NO | - |
| valid_to | date / YES | - |
| timezone | text / NO | - |

CHECK: weekday BETWEEN 1 AND 7; start_minute >= 0 AND end_minute <= 1440 AND start_minute < end_minute; valid_to IS NULL OR valid_to >= valid_from

INDEX: candidate_id,weekday,valid_from

Oraliqlar [start,end). Kesishgan mavjudlik union qilinadi, daqiqalar ikki marta sanalmaydi.

Imkoniyatlar: CAP-005.

### DB-017 availability_exceptions

Sana bo‘yicha dars/istisno.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| candidate_id | uuid / NO | DB-012 candidate_profiles.id |
| local_date | date / NO | - |
| kind | text / NO | - |
| start_minute | integer / NO | - |
| end_minute | integer / NO | - |

CHECK: kind IN ('AVAILABLE','UNAVAILABLE'); start_minute >= 0 AND end_minute <= 1440 AND start_minute < end_minute

INDEX: candidate_id,local_date



Imkoniyatlar: CAP-005.

### DB-018 files

Xususiy, skanerdan o‘tadigan fayl.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| owner_user_id | uuid / NO | DB-001 users.id |
| storage_key | text / NO | - |
| filename | text / NO | - |
| mime_type | text / NO | - |
| byte_size | integer / NO | - |
| sha256 | text / NO | - |
| scan_status | text / NO | - |
| retention_class | text / NO | - |
| deleted_at | timestamptz / YES | - |

UNIQUE: storage_key

CHECK: byte_size > 0

INDEX: owner_user_id,created_at; scan_status,created_at

Baza fayl tanasini saqlamaydi. Karantin, MIME/magic tekshiruvi, hajm limiti, qisqa signed URL va yuklash huquqi shart. Maxfiylikni key nomi bilan hal qilib bo‘lmaydi.

Imkoniyatlar: CAP-003, CAP-004, CAP-008, CAP-022, CAP-026, CAP-032, CAP-034, CAP-035.

### DB-019 verification_cases

Shaxs, tashkilot yoki ta’limni tekshirish navbati.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| requester_id | uuid / NO | DB-001 users.id |
| candidate_id | uuid / YES | DB-012 candidate_profiles.id |
| organization_id | uuid / YES | DB-021 organizations.id |
| institution_id | uuid / YES | DB-028 institutions.id |
| enrollment_id | uuid / YES | DB-015 enrollments.id |
| appointment_id | uuid / YES | DB-032 institution_appointments.id |
| kind | text / NO | - |
| status | text / NO | - |
| current_revision | integer / NO | - |
| assigned_reviewer_id | uuid / YES | DB-001 users.id |
| due_at | timestamptz / NO | - |
| decision_reason | text / YES | - |
| decided_at | timestamptz / YES | - |

CHECK: num_nonnulls(candidate_id,organization_id,institution_id,enrollment_id,appointment_id) = 1; current_revision > 0

INDEX: status,due_at; assigned_reviewer_id,status

Har tur uchun haqiqiy FK, target_type/target_id jufti yo‘q. Tekshiruvchi o‘z murojaatini tasdiqlamaydi.

Imkoniyatlar: CAP-004, CAP-013, CAP-019, CAP-033.

### DB-020 verification_evidence

Tekshiruvga topshirilgan revision dalili.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| case_id | uuid / NO | DB-019 verification_cases.id |
| revision | integer / NO | - |
| file_id | uuid / YES | DB-018 files.id |
| note | text / YES | - |

CHECK: revision > 0; file_id IS NOT NULL OR note IS NOT NULL

INDEX: case_id,revision



Imkoniyatlar: CAP-004, CAP-013, CAP-033.

## ORG - Tashkilot va xodimlar


### DB-021 organizations

STIR bo‘yicha yagona ish beruvchi/host.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| tax_id | text / NO | - |
| legal_name | text / NO | - |
| public_name | text / NO | - |
| region | text / NO | - |
| description | text / YES | - |
| website | text / YES | - |
| status | text / NO | - |

UNIQUE: tax_id

INDEX: status,region

Mavjud STIR yangi tashkilot yaratmaydi. Birinchi vakil mustaqil tekshiruvdan so‘ng; public ma’lumot va maxfiy dalil ajratiladi.

Imkoniyatlar: CAP-001, CAP-013, CAP-033, CAP-040.

### DB-022 organization_capabilities

Ish e’loni va host huquqi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| organization_id | uuid / NO | DB-021 organizations.id |
| capability | text / NO | - |
| status | text / NO | - |
| approved_case_id | uuid / YES | DB-019 verification_cases.id |

UNIQUE: organization_id,capability

CHECK: capability IN ('JOB_EMPLOYER','INTERNSHIP_HOST')

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Tasdiqlangan capability ham faol a’zo rolini almashtirmaydi.

Imkoniyatlar: CAP-013.

### DB-023 org_memberships

Xodimning tashkilotga mansubligi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| organization_id | uuid / NO | DB-021 organizations.id |
| user_id | uuid / NO | DB-001 users.id |
| status | text / NO | - |
| accepted_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |

UNIQUE: organization_id,user_id; id,organization_id

INDEX: user_id,status

Ownerdan boshqa a’zolik pul va egalik huquqini avtomatik bermaydi. Oxirgi active owner tranzaksiyada himoyalanadi.

Imkoniyatlar: CAP-014, CAP-015.

### DB-024 org_role_grants

Tashkilot ichidagi rol.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| membership_id | uuid / NO | DB-023 org_memberships.id |
| role_id | uuid / NO | DB-008 role_catalog.id |
| granted_by_id | uuid / NO | DB-001 users.id |
| revoked_at | timestamptz / YES | - |

UNIQUE: membership_id,role_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Faqat ORG role. Ruxsat aktif membership, role va assignment kesishmasi; global union emas.

Imkoniyatlar: CAP-014.

### DB-025 org_invitations

Aniq kontaktga vaqtli taklif.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| organization_id | uuid / NO | DB-021 organizations.id |
| inviter_membership_id | uuid / NO | DB-023 org_memberships.id |
| contact_digest | text / NO | - |
| token_digest | text / NO | - |
| expires_at | timestamptz / NO | - |
| accepted_by_id | uuid / YES | DB-001 users.id |
| accepted_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |

UNIQUE: token_digest

INDEX: organization_id,expires_at

24 soat; inviter ayni orgga mansub; kontakt va qabul qiluvchi mos; repeat accept idempotent.

Imkoniyatlar: CAP-014, CAP-015.

### DB-026 org_invitation_roles

Taklifdagi ochiq ko‘rsatilgan rol.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| invitation_id | uuid / NO | DB-025 org_invitations.id |
| role_id | uuid / NO | DB-008 role_catalog.id |

UNIQUE: invitation_id,role_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-014, CAP-015.

### DB-027 org_ownership_events

Birinchi va keyingi egani tayinlash dalili.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| organization_id | uuid / NO | DB-021 organizations.id |
| new_membership_id | uuid / NO | DB-023 org_memberships.id |
| previous_membership_id | uuid / YES | DB-023 org_memberships.id |
| verification_case_id | uuid / NO | DB-019 verification_cases.id |
| approved_by_id | uuid / NO | DB-001 users.id |
| effective_at | timestamptz / NO | - |

INDEX: organization_id,effective_at

Grant mustaqil reviewer bilan; oxirgi egani yo‘qotishdan oldin o‘rinbosar yoki recovery. Append-only.

Imkoniyatlar: CAP-013, CAP-014.

## EDU - Muassasa va rasmiy biriktirish


### DB-028 institutions

Hamkor o‘quv muassasasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| registry_code | text / NO | - |
| name | text / NO | - |
| region | text / NO | - |
| status | text / NO | - |

UNIQUE: registry_code

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-004, CAP-019.

### DB-029 institution_agreements

Akademik xizmatning rasmiy chegarasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| institution_id | uuid / NO | DB-028 institutions.id |
| version | integer / NO | - |
| status | text / NO | - |
| valid_from | date / NO | - |
| valid_to | date / YES | - |
| purposes | jsonb / NO | - |
| signed_file_id | uuid / YES | DB-018 files.id |

UNIQUE: institution_id,version

CHECK: version > 0; valid_to IS NULL OR valid_to >= valid_from

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Rasmiy baho, imzo, eksport va ishlov asosi kelishuvga bog‘liq; umumiy platforma PDFsi imzo deb taqdim etilmaydi.

Imkoniyatlar: CAP-019.

### DB-030 institution_memberships

Rasmiy xodim mansubligi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| institution_id | uuid / NO | DB-028 institutions.id |
| user_id | uuid / NO | DB-001 users.id |
| status | text / NO | - |
| accepted_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |

UNIQUE: institution_id,user_id; id,institution_id

INDEX: user_id,status



Imkoniyatlar: CAP-015, CAP-020.

### DB-031 institution_role_grants

Koordinator/o‘qituvchi roli.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| membership_id | uuid / NO | DB-030 institution_memberships.id |
| role_id | uuid / NO | DB-008 role_catalog.id |
| appointment_id | uuid / NO | DB-032 institution_appointments.id |
| revoked_at | timestamptz / YES | - |

UNIQUE: membership_id,role_id,appointment_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Faqat INSTITUTION role va ayni muassasaning faol rasmiy appointmenti bilan.

Imkoniyatlar: CAP-020.

### DB-032 institution_appointments

Muassasa topshirig‘i va dalili.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| institution_id | uuid / NO | DB-028 institutions.id |
| user_id | uuid / NO | DB-001 users.id |
| document_file_id | uuid / NO | DB-018 files.id |
| status | text / NO | - |
| verification_case_id | uuid / YES | DB-019 verification_cases.id |
| valid_from | date / NO | - |
| valid_to | date / YES | - |
| accepted_at | timestamptz / YES | - |

CHECK: valid_to IS NULL OR valid_to >= valid_from

INDEX: institution_id,status

Email domeni o‘zi tayinlov emas. Tayinlangan shaxs taklifni qabul qiladi, moderator o‘zini tayinlamaydi.

Imkoniyatlar: CAP-015, CAP-019.

### DB-033 institution_invitations

Muassasa tayinlovi taklifi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| appointment_id | uuid / NO | DB-032 institution_appointments.id |
| contact_digest | text / NO | - |
| token_digest | text / NO | - |
| expires_at | timestamptz / NO | - |
| accepted_by_id | uuid / YES | DB-001 users.id |
| accepted_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |

UNIQUE: token_digest

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-015, CAP-019.

### DB-034 student_supervisions

Koordinatorning aniq ta’lim yozuviga doirasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| enrollment_id | uuid / NO | DB-015 enrollments.id |
| coordinator_membership_id | uuid / NO | DB-030 institution_memberships.id |
| agreement_id | uuid / NO | DB-029 institution_agreements.id |
| purpose | text / NO | - |
| status | text / NO | - |
| legal_basis | text / NO | - |
| accepted_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |

UNIQUE: enrollment_id,coordinator_membership_id,purpose

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Uch yozuvning institution_id qiymati teng. O‘quvchi boshqa muassasaga o‘tsa eski scope ko‘chmaydi; mas’ulga berilgan maqsad bilangina ko‘rinadi.

Imkoniyatlar: CAP-020, CAP-021.

## JOB - E’lon va qidiruv


### DB-035 opportunities

E’lon identifikatori va band o‘rin.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| organization_id | uuid / NO | DB-021 organizations.id |
| kind | text / NO | - |
| status | text / NO | - |
| current_revision_id | uuid / YES | DB-036 opportunity_revisions.id |
| capacity | integer / NO | - |
| occupied_count | integer / NO | - |
| published_at | timestamptz / YES | - |
| expires_at | timestamptz / YES | - |
| closed_at | timestamptz / YES | - |

CHECK: kind IN ('PART_TIME','INTERNSHIP'); capacity > 0; occupied_count >= 0 AND occupied_count <= capacity

INDEX: status,published_at,id; organization_id,status

Counter va offer qabuli bir tranzaksiya/lockda. Active occupied applications bilan kunlik reconciliation; counter mustaqil tahrirlanmaydi.

Imkoniyatlar: CAP-001, CAP-006, CAP-011, CAP-016, CAP-033.

### DB-036 opportunity_revisions

E’lon shartlarining o‘zgarmas nusxasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| opportunity_id | uuid / NO | DB-035 opportunities.id |
| revision | integer / NO | - |
| author_id | uuid / NO | DB-001 users.id |
| title | text / NO | - |
| description | text / NO | - |
| region | text / NO | - |
| work_mode | text / NO | - |
| eligibility | text / NO | - |
| program_required | text / YES | - |
| salary_min | numeric(18,2) / YES | - |
| salary_max | numeric(18,2) / YES | - |
| currency | text / NO | - |
| salary_period | text / YES | - |
| salary_basis | text / YES | - |
| is_paid | boolean / NO | - |
| start_date | date / NO | - |
| end_date | date / YES | - |
| schedule_policy | text / NO | - |
| shift_match_mode | text / NO | - |
| snapshot_schema | integer / NO | - |
| published_at | timestamptz / YES | - |

UNIQUE: opportunity_id,revision; id,opportunity_id

CHECK: revision > 0; end_date IS NULL OR end_date >= start_date; salary_min IS NULL OR salary_min > 0; salary_max IS NULL OR salary_max >= salary_min

INDEX: opportunity_id,revision

PART_TIME va pullik INTERNSHIP uchun salary_min/max, UZS, davr/brutto-netto; INTERNSHIP end majburiy; unpaidda salary null. Bu cross-table qoidalar publish tranzaksiyasi va acceptance test bilan. Nashrdagi qator update qilinmaydi.

Imkoniyatlar: CAP-001, CAP-007, CAP-016.

### DB-037 opportunity_skills

E’lon revisionining malaka talabi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| revision_id | uuid / NO | DB-036 opportunity_revisions.id |
| skill_id | uuid / NO | DB-013 skills.id |
| required | boolean / NO | - |
| minimum_level | text / YES | - |

UNIQUE: revision_id,skill_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-001, CAP-016.

### DB-038 opportunity_shifts

E’lon revisioni smenalari.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| revision_id | uuid / NO | DB-036 opportunity_revisions.id |
| weekday | integer / NO | - |
| start_minute | integer / NO | - |
| end_minute | integer / NO | - |
| timezone | text / NO | - |

CHECK: weekday BETWEEN 1 AND 7; start_minute >= 0 AND end_minute <= 1440 AND start_minute < end_minute

INDEX: revision_id,weekday

Tungi smena ikki sana/hafta kuniga bo‘linadi; barcha intervallar yarim ochiq.

Imkoniyatlar: CAP-001, CAP-016.

### DB-039 opportunity_hr_assignments

HRning aynan e’longa doirasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| opportunity_id | uuid / NO | DB-035 opportunities.id |
| membership_id | uuid / NO | DB-023 org_memberships.id |
| assigned_by_id | uuid / NO | DB-001 users.id |
| accepted_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |

UNIQUE: opportunity_id,membership_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

E’lon va membership tashkiloti teng, HR roli aktiv. Organization owner ham ko‘rish amalida shu maqsad va audit talabiga bo‘ysunadi.

Imkoniyatlar: CAP-008, CAP-016.

### DB-040 saved_opportunities

Nomzod saqlagan e’lon.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| candidate_id | uuid / NO | DB-012 candidate_profiles.id |
| opportunity_id | uuid / NO | DB-035 opportunities.id |

UNIQUE: candidate_id,opportunity_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-006.

## APP - Ariza, suhbat va ish


### DB-041 applications

Bitta nomzod va bitta e’lon munosabati.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| candidate_id | uuid / NO | DB-012 candidate_profiles.id |
| opportunity_id | uuid / NO | DB-035 opportunities.id |
| status | text / NO | - |
| current_attempt_id | uuid / YES | DB-042 application_attempts.id |
| version | integer / NO | - |
| occupied_at | timestamptz / YES | - |
| released_at | timestamptz / YES | - |

UNIQUE: candidate_id,opportunity_id; id,candidate_id,opportunity_id

CHECK: version > 0

INDEX: opportunity_id,status,created_at; candidate_id,created_at

Retry yangi application yaratmaydi. Version conditional update, transition va capacity bir tranzaksiyada.

Imkoniyatlar: CAP-007, CAP-008, CAP-009, CAP-010, CAP-011, CAP-012.

### DB-042 application_attempts

Qayta ariza va o‘sha paytdagi shartlar.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| application_id | uuid / NO | DB-041 applications.id |
| attempt_no | integer / NO | - |
| revision_id | uuid / NO | DB-036 opportunity_revisions.id |
| enrollment_id | uuid / YES | DB-015 enrollments.id |
| profile_snapshot | jsonb / NO | - |
| schedule_result | text / NO | - |
| matching_version | text / NO | - |
| proposed_slots | jsonb / YES | - |
| submitted_at | timestamptz / NO | - |
| idempotency_key | text / NO | - |

UNIQUE: application_id,attempt_no; idempotency_key

CHECK: attempt_no > 0

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Revision ayni e’longa, enrollment ayni candidatega tegishli. Snapshot schema-valid va minimallashtirilgan; keyinchalik CV o‘zgarishi tarixni buzmaydi.

Imkoniyatlar: CAP-007, CAP-008, CAP-010.

### DB-043 application_events

Holat o‘zgarishi va qayta ochish.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| application_id | uuid / NO | DB-041 applications.id |
| attempt_id | uuid / YES | DB-042 application_attempts.id |
| actor_id | uuid / NO | DB-001 users.id |
| from_status | text / YES | - |
| to_status | text / NO | - |
| reason | text / YES | - |
| occurred_at | timestamptz / NO | - |

INDEX: application_id,occurred_at

Append-only. REJECTED/EXPIREDdan qayta ochish HR ruxsati bilan; 24h va 3/30kun limit service tranzaksiyasida.

Imkoniyatlar: CAP-007, CAP-008.

### DB-044 interviews

Suhbat va uning jadvali.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| application_id | uuid / NO | DB-041 applications.id |
| organizer_membership_id | uuid / NO | DB-023 org_memberships.id |
| starts_at | timestamptz / NO | - |
| ends_at | timestamptz / NO | - |
| timezone | text / NO | - |
| mode | text / NO | - |
| location_or_link | text / YES | - |
| status | text / NO | - |
| version | integer / NO | - |

CHECK: ends_at > starts_at; version > 0

INDEX: application_id,starts_at

Tashkilot doirasi tekshiriladi; o‘zgarishlar audit/eventga. MVP platformadagi tasdiq, tashqi calendar sync emas.

Imkoniyatlar: CAP-009.

### DB-045 interview_responses

Suhbatga tomonlarning javobi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| interview_id | uuid / NO | DB-044 interviews.id |
| user_id | uuid / NO | DB-001 users.id |
| response | text / NO | - |
| responded_at | timestamptz / YES | - |

UNIQUE: interview_id,user_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-009.

### DB-046 offers

Muddati va shartlari aniq taklif.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| application_id | uuid / NO | DB-041 applications.id |
| attempt_id | uuid / NO | DB-042 application_attempts.id |
| revision_id | uuid / NO | DB-036 opportunity_revisions.id |
| issuer_membership_id | uuid / NO | DB-023 org_memberships.id |
| terms_snapshot | jsonb / NO | - |
| status | text / NO | - |
| expires_at | timestamptz / NO | - |
| accepted_at | timestamptz / YES | - |
| idempotency_key | text / NO | - |

UNIQUE: idempotency_key

INDEX: application_id,status; status,expires_at

Bir applicationda bir ACTIVE offer uchun partial unique index. OFFERED joyni kafolatlamaydi; ACCEPT atomar capacity tekshiradi; expires_at serverda ham tekshiriladi.

Imkoniyatlar: CAP-010, CAP-011.

### DB-047 job_engagements

Oddiy maoshli ishning boshlanish/yakun holati.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| application_id | uuid / NO | DB-041 applications.id |
| offer_id | uuid / NO | DB-046 offers.id |
| status | text / NO | - |
| start_date | date / NO | - |
| end_date | date / YES | - |
| terms_snapshot | jsonb / NO | - |
| confirmed_started_at | timestamptz / YES | - |

UNIQUE: application_id; offer_id

CHECK: end_date IS NULL OR end_date >= start_date

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Faqat PART_TIME. Ikki tomon STARTni tasdiqlamaguncha haqiqiy ishga joylashish statistikasi emas; kundalik avtomatik ochilmaydi.

Imkoniyatlar: CAP-011, CAP-012.

### DB-048 engagement_confirmations

Ish munosabatining ikki tomon tasdig‘i.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| engagement_id | uuid / NO | DB-047 job_engagements.id |
| user_id | uuid / NO | DB-001 users.id |
| side | text / NO | - |
| action | text / NO | - |
| response | text / NO | - |
| occurred_at | timestamptz / NO | - |

UNIQUE: engagement_id,side,action

CHECK: side IN ('CANDIDATE','EMPLOYER')

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Nomzod o‘zi yoki berilgan vakolatli HR; side foydalanuvchi tanlagan erkin satrga ishonib berilmaydi.

Imkoniyatlar: CAP-012.

## INT - Amaliyot va reja


### DB-049 placements

Qabul qilingan amaliyot munosabati.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| application_id | uuid / NO | DB-041 applications.id |
| offer_id | uuid / NO | DB-046 offers.id |
| candidate_id | uuid / NO | DB-012 candidate_profiles.id |
| organization_id | uuid / NO | DB-021 organizations.id |
| enrollment_id | uuid / YES | DB-015 enrollments.id |
| academic_track | boolean / NO | - |
| status | text / NO | - |
| start_date | date / NO | - |
| end_date | date / NO | - |
| current_terms_id | uuid / YES | DB-050 placement_terms.id |
| version | integer / NO | - |

UNIQUE: application_id; offer_id

CHECK: end_date >= start_date; NOT academic_track OR enrollment_id IS NOT NULL; version > 0

INDEX: candidate_id,status; organization_id,status

Faqat INTERNSHIP. Nomzod/application/offer/host bir-biriga mos. Academic ACTIVEda faol agreement, supervisor va mentor qabuli kerak.

Imkoniyatlar: CAP-011, CAP-017, CAP-018, CAP-021, CAP-025, CAP-026.

### DB-050 placement_terms

Amaliyot rejasining immutable versiyasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| placement_id | uuid / NO | DB-049 placements.id |
| version | integer / NO | - |
| schema_version | integer / NO | - |
| terms_snapshot | jsonb / NO | - |
| daily_limit_minutes | integer / NO | - |
| weekly_limit_minutes | integer / NO | - |
| required_minutes | integer / NO | - |
| candidate_accepted_at | timestamptz / YES | - |
| host_accepted_at | timestamptz / YES | - |

UNIQUE: placement_id,version; id,placement_id

CHECK: version > 0; daily_limit_minutes > 0 AND daily_limit_minutes <= 1440; weekly_limit_minutes > 0 AND weekly_limit_minutes <= 10080; required_minutes >= 0

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-017, CAP-018, CAP-025.

### DB-051 mentor_assignments

Korxona ustozi shaxsiy qabuli.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| placement_id | uuid / NO | DB-049 placements.id |
| membership_id | uuid / NO | DB-023 org_memberships.id |
| assigned_by_id | uuid / NO | DB-001 users.id |
| assigned_at | timestamptz / NO | - |
| accepted_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |

INDEX: placement_id,revoked_at; membership_id,revoked_at

Faqat host orgidagi faol MENTOR. Self-review yo‘q; bir vaqtda bitta asosiy accepted mentor partial unique bilan.

Imkoniyatlar: CAP-017, CAP-018, CAP-023.

### DB-052 academic_assignments

O‘qituvchining ayni amaliyotga qabuli.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| placement_id | uuid / NO | DB-049 placements.id |
| teacher_membership_id | uuid / NO | DB-030 institution_memberships.id |
| supervision_id | uuid / NO | DB-034 student_supervisions.id |
| assigned_by_id | uuid / NO | DB-001 users.id |
| assigned_at | timestamptz / NO | - |
| accepted_at | timestamptz / YES | - |
| revoked_at | timestamptz / YES | - |

INDEX: placement_id,revoked_at; teacher_membership_id,revoked_at

Teacher muassasasi enrollment va supervisionga mos. Bir vaqtda bitta asosiy accepted teacher. O‘z kundaligini boshqa rol bilan ko‘rish/tasdiqlash rad.

Imkoniyatlar: CAP-018, CAP-020, CAP-021, CAP-024.

### DB-053 plan_tasks

Rejaga bog‘langan natija va topshiriq.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| terms_id | uuid / NO | DB-050 placement_terms.id |
| code | text / NO | - |
| title | text / NO | - |
| expected_result | text / NO | - |
| required | boolean / NO | - |
| target_minutes | integer / YES | - |

UNIQUE: terms_id,code

CHECK: target_minutes IS NULL OR target_minutes >= 0

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-017, CAP-025.

### DB-054 placement_decisions

Faollashtirish/yakun/bekor qilish dalili.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| placement_id | uuid / NO | DB-049 placements.id |
| actor_id | uuid / NO | DB-001 users.id |
| side | text / NO | - |
| decision | text / NO | - |
| terms_id | uuid / NO | DB-050 placement_terms.id |
| reason | text / YES | - |
| decided_at | timestamptz / NO | - |

INDEX: placement_id,decided_at

Tegishli tomon vakolati va reja versiyasi tekshiriladi; completion shartlari yopilmaguncha COMPLETED emas.

Imkoniyatlar: CAP-017, CAP-018, CAP-024, CAP-025.

## LOG - Kundalik va dalillar


### DB-055 daily_logs

Placement va mahalliy sana uchun bitta kun.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| placement_id | uuid / NO | DB-049 placements.id |
| local_date | date / NO | - |
| current_revision_id | uuid / YES | DB-056 log_revisions.id |
| version | integer / NO | - |

UNIQUE: placement_id,local_date; id,placement_id

CHECK: version > 0

INDEX: placement_id,local_date



Imkoniyatlar: CAP-021, CAP-022, CAP-023, CAP-025, CAP-026.

### DB-056 log_revisions

Qoralama va topshirilgan kun versiyasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| daily_log_id | uuid / NO | DB-055 daily_logs.id |
| revision | integer / NO | - |
| terms_id | uuid / NO | DB-050 placement_terms.id |
| author_id | uuid / NO | DB-001 users.id |
| day_type | text / NO | - |
| summary | text / YES | - |
| total_minutes | integer / NO | - |
| status | text / NO | - |
| submitted_at | timestamptz / YES | - |
| idempotency_key | text / NO | - |

UNIQUE: daily_log_id,revision; idempotency_key; id,daily_log_id

CHECK: revision > 0; total_minutes >= 0

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

total_minutes faqat task_entries SUMidan serverda; SUBMITTED immutable. Sana, placement, kechikish, overlap, reja chegaralari topshirish tranzaksiyasida.

Imkoniyatlar: CAP-021, CAP-022, CAP-023, CAP-024, CAP-026.

### DB-057 log_task_entries

Kun ichidagi bajarilgan ishlar.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| revision_id | uuid / NO | DB-056 log_revisions.id |
| plan_task_id | uuid / YES | DB-053 plan_tasks.id |
| result_text | text / NO | - |
| minutes | integer / NO | - |
| start_minute | integer / YES | - |
| end_minute | integer / YES | - |

CHECK: minutes > 0; (start_minute IS NULL AND end_minute IS NULL) OR (start_minute >= 0 AND end_minute <= 1440 AND end_minute > start_minute AND minutes = end_minute - start_minute)

INDEX: revision_id

plan_task ayni placement rejasidan. Oraliq berilgan ishlar kesishmaydi; daqiqa-only yozuvga soxta aniq overlap da’vosi qilinmaydi.

Imkoniyatlar: CAP-022, CAP-023.

### DB-058 log_evidence

Topshiriq dalili uchun private fayl.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| entry_id | uuid / NO | DB-057 log_task_entries.id |
| file_id | uuid / NO | DB-018 files.id |
| visibility | text / NO | - |

UNIQUE: entry_id,file_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Muallif yuklash huquqi, clean scan va host confidentiality; ko‘ruvchi assignmenti tekshiriladi.

Imkoniyatlar: CAP-022, CAP-023.

### DB-059 workplace_log_reviews

Mentorning aynan revisionga qarori.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| revision_id | uuid / NO | DB-056 log_revisions.id |
| mentor_assignment_id | uuid / NO | DB-051 mentor_assignments.id |
| decision | text / NO | - |
| comment | text / YES | - |
| decided_at | timestamptz / NO | - |

UNIQUE: revision_id,mentor_assignment_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

APPROVED/RETURNED; faqat qabul qilingan faol assignment. Muallifga o‘zini tasdiqlash taqiqlangan; oldingi qaror yangi revisionni tasdiqlamaydi.

Imkoniyatlar: CAP-023, CAP-026.

### DB-060 academic_log_reviews

O‘qituvchining alohida fikri.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| revision_id | uuid / NO | DB-056 log_revisions.id |
| academic_assignment_id | uuid / NO | DB-052 academic_assignments.id |
| decision | text / NO | - |
| comment | text / YES | - |
| decided_at | timestamptz / NO | - |

UNIQUE: revision_id,academic_assignment_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

REVIEWED/NEEDS_REVISION, workplace approval o‘rnini bosa olmaydi.

Imkoniyatlar: CAP-024, CAP-026.

### DB-061 log_amendment_requests

Yopilgan/kech kundalikni o‘zgartirish.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| daily_log_id | uuid / NO | DB-055 daily_logs.id |
| requester_id | uuid / NO | DB-001 users.id |
| reason | text / NO | - |
| status | text / NO | - |
| reviewer_id | uuid / YES | DB-001 users.id |
| resolved_at | timestamptz / YES | - |

INDEX: status,created_at

Mustaqil review va audit; texnik uzilish sababli avtomatik jazo yo‘q.

Imkoniyatlar: CAP-022.

## RAT - Baholash va apellyatsiya


### DB-062 rubric_versions

Versiyali baholash mezonlari.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| family | text / NO | - |
| version | integer / NO | - |
| status | text / NO | - |
| scale_min | integer / NO | - |
| scale_max | integer / NO | - |
| published_at | timestamptz / YES | - |

UNIQUE: family,version

CHECK: version > 0; scale_max > scale_min

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Workplace/academic/employer/mentor oilalari ajratiladi. Formula o‘zgarsa yangi immutable version.

Imkoniyatlar: CAP-027, CAP-040.

### DB-063 rubric_criteria

Mezon va vazn.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| rubric_id | uuid / NO | DB-062 rubric_versions.id |
| code | text / NO | - |
| title | text / NO | - |
| weight | integer / NO | - |
| required | boolean / NO | - |

UNIQUE: rubric_id,code

CHECK: weight > 0 AND weight <= 100

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

ACTIVE qilishda required mezonlar yig‘indisi 100 va to‘liqlik tekshiriladi.

Imkoniyatlar: CAP-027.

### DB-064 rating_submissions

Haqiqiy yakuniy munosabatdan baho.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| placement_id | uuid / YES | DB-049 placements.id |
| engagement_id | uuid / YES | DB-047 job_engagements.id |
| rubric_id | uuid / NO | DB-062 rubric_versions.id |
| rater_id | uuid / NO | DB-001 users.id |
| target_user_id | uuid / YES | DB-001 users.id |
| target_org_id | uuid / YES | DB-021 organizations.id |
| version | integer / NO | - |
| status | text / NO | - |
| comment | text / YES | - |
| submitted_at | timestamptz / YES | - |
| publish_after | timestamptz / YES | - |

CHECK: num_nonnulls(placement_id,engagement_id) = 1; num_nonnulls(target_user_id,target_org_id) = 1; target_user_id IS NULL OR target_user_id <> rater_id; version > 0

INDEX: target_user_id,status; target_org_id,status

Bir rater/relation/rubric uchun bitta final; partial unique indexes. Haqiqiy completed ishtirok, target va rubrika doirasi service tekshiradi. Rating feature flag boshlang‘ich OFF.

Imkoniyatlar: CAP-027, CAP-028.

### DB-065 rating_revisions

Bahoning o‘zgarmas matn va formula nusxasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| submission_id | uuid / NO | DB-064 rating_submissions.id |
| version | integer / NO | - |
| comment | text / YES | - |
| submitted_at | timestamptz / NO | - |
| rubric_snapshot | jsonb / NO | - |

UNIQUE: submission_id,version

CHECK: version > 0

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Submitted revision update qilinmaydi; tuzatish yangi revision, eski ball va e’tiroz dalili saqlanadi.

Imkoniyatlar: CAP-027, CAP-028.

### DB-066 rating_scores

Har mezonning dalilli bali.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| rating_revision_id | uuid / NO | DB-065 rating_revisions.id |
| criterion_id | uuid / NO | DB-063 rubric_criteria.id |
| score | integer / NO | - |
| evidence_revision_id | uuid / YES | DB-056 log_revisions.id |

UNIQUE: rating_revision_id,criterion_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Criterion submissionning ayni rubricidan; score min/max ichida. Akademik va workplace bir songa aralashmaydi.

Imkoniyatlar: CAP-027.

### DB-067 rating_appeals

Reyting nizosi va mustaqil qaror.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| rating_revision_id | uuid / NO | DB-065 rating_revisions.id |
| appellant_id | uuid / NO | DB-001 users.id |
| reason | text / NO | - |
| status | text / NO | - |
| reviewer_id | uuid / YES | DB-001 users.id |
| decision | text / YES | - |
| resolved_at | timestamptz / YES | - |

INDEX: status,created_at

14kun murojaat, 5ishkun nishon; nizoli baho vaqtincha aggregate tashqarisida. Reviewer munosabat ishtirokchisi emas.

Imkoniyatlar: CAP-028.

### DB-068 rating_aggregates

Qayta hisoblanadigan ommaviy kesh.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| target_user_id | uuid / YES | DB-001 users.id |
| target_org_id | uuid / YES | DB-021 organizations.id |
| rubric_id | uuid / NO | DB-062 rubric_versions.id |
| sample_size | integer / NO | - |
| score | numeric(18,2) / YES | - |
| window_start | date / NO | - |
| window_end | date / NO | - |
| computed_at | timestamptz / NO | - |

CHECK: num_nonnulls(target_user_id,target_org_id) = 1; sample_size >= 0; window_end >= window_start

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Haqiqat manbai submission, bu kesh. n<5da score public emas; unrated 0 emas. Bir relation bir ovoz; appeals bilan qayta hisob. Partial unique target/rubric/window.

Imkoniyatlar: CAP-028, CAP-040.

## BIL - Tarif, hisob va to‘lov


### DB-069 products

Sotiladigan xizmat turi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| code | text / NO | - |
| name | text / NO | - |
| service_kind | text / NO | - |
| active | boolean / NO | - |

UNIQUE: code

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Candidate search free. POST_30D va ORG_PLAN_30D pilot narxlari; amaliyot/akademik xizmat shartnoma bo‘lmasa pullik va’da qilinmaydi.

Imkoniyatlar: CAP-029, CAP-039.

### DB-070 price_versions

Tarif narxining immutable nusxasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| product_id | uuid / NO | DB-069 products.id |
| version | integer / NO | - |
| amount | numeric(18,2) / NO | - |
| currency | text / NO | - |
| duration_days | integer / NO | - |
| tax_included | boolean / NO | - |
| valid_from | timestamptz / NO | - |
| valid_to | timestamptz / YES | - |

UNIQUE: product_id,version

CHECK: amount >= 0; duration_days > 0; valid_to IS NULL OR valid_to > valid_from

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.



Imkoniyatlar: CAP-029, CAP-039.

### DB-071 orders

Tashkilot buyurtmasi va narx snapshot.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| organization_id | uuid / NO | DB-021 organizations.id |
| purchaser_id | uuid / NO | DB-001 users.id |
| price_id | uuid / NO | DB-070 price_versions.id |
| opportunity_id | uuid / YES | DB-035 opportunities.id |
| amount | numeric(18,2) / NO | - |
| currency | text / NO | - |
| price_snapshot | jsonb / NO | - |
| status | text / NO | - |
| idempotency_key | text / NO | - |

UNIQUE: idempotency_key

CHECK: amount >= 0

INDEX: organization_id,created_at

Org billing vakolati; order e’loni ayni orgga. Stavka keyin o‘zgarsa eski order o‘zgarmaydi.

Imkoniyatlar: CAP-029, CAP-030, CAP-038.

### DB-072 invoices

Hisob va fiskal hujjat holati.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| order_id | uuid / NO | DB-071 orders.id |
| number | text / NO | - |
| amount | numeric(18,2) / NO | - |
| currency | text / NO | - |
| fiscal_status | text / NO | - |
| fiscal_reference | text / YES | - |
| issued_at | timestamptz / NO | - |
| paid_at | timestamptz / YES | - |

UNIQUE: number; order_id

CHECK: amount >= 0

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Fiskal talab operatorning huquqiy shakliga mos mutaxassis bilan; oddiy PDFni fiskal chek deb atamaslik.

Imkoniyatlar: CAP-029, CAP-038.

### DB-073 payment_attempts

Provayder tranzaksiyasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| order_id | uuid / NO | DB-071 orders.id |
| provider | text / NO | - |
| provider_transaction_id | text / YES | - |
| amount | numeric(18,2) / NO | - |
| currency | text / NO | - |
| status | text / NO | - |
| requested_at | timestamptz / NO | - |
| confirmed_at | timestamptz / YES | - |

UNIQUE: provider,provider_transaction_id

CHECK: amount >= 0

INDEX: order_id,status

Bir order ko‘p attempt; muvaffaqiyat entitlementsni bir marta beradi. Callback protokoli provayderga mos; brauzer success pul tasdig‘i emas.

Imkoniyatlar: CAP-029, CAP-030.

### DB-074 payment_events

Takror keluvchi callback deduplikatsiyasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| attempt_id | uuid / NO | DB-073 payment_attempts.id |
| provider | text / NO | - |
| event_key | text / NO | - |
| payload_digest | text / NO | - |
| normalized_payload | jsonb / NO | - |
| processed_at | timestamptz / YES | - |
| received_at | timestamptz / NO | - |

UNIQUE: provider,event_key

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Server auth/protokol, amount/order/currency mosligi. Kartaning maxfiy rekvizitlari saqlanmaydi; payload PII minimallashtirilgan.

Imkoniyatlar: CAP-030.

### DB-075 service_entitlements

Amaldagi xizmat, muddat va kvota.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| organization_id | uuid / NO | DB-021 organizations.id |
| order_id | uuid / YES | DB-071 orders.id |
| opportunity_id | uuid / YES | DB-035 opportunities.id |
| service_kind | text / NO | - |
| status | text / NO | - |
| starts_at | timestamptz / YES | - |
| ends_at | timestamptz / YES | - |
| quota | integer / YES | - |
| granted_by_id | uuid / YES | DB-001 users.id |
| grant_reason | text / YES | - |

CHECK: ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at; quota IS NULL OR quota >= 0

INDEX: organization_id,status,ends_at

POST_30D muddati publishdan, pul tushgan kundan emas. Org plan birinchi publish yoki aniq aktivatsiyadan boshlanadi; auto-renew MVPda OFF. Bepul pilot grant auditlanadi.

Imkoniyatlar: CAP-016, CAP-029, CAP-038.

### DB-076 refunds

Qaytarish va ikkita tasdiq.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| payment_attempt_id | uuid / NO | DB-073 payment_attempts.id |
| requester_id | uuid / NO | DB-001 users.id |
| approver_id | uuid / YES | DB-001 users.id |
| amount | numeric(18,2) / NO | - |
| currency | text / NO | - |
| reason | text / NO | - |
| status | text / NO | - |
| provider_refund_id | text / YES | - |
| resolved_at | timestamptz / YES | - |

UNIQUE: provider_refund_id

CHECK: amount > 0; approver_id IS NULL OR approver_id <> requester_id

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Yig‘indi muvaffaqiyatli refunds captured summadan oshmaydi; lock + callback idempotency. Katta summaga ikkinchi mustaqil tasdiq audit_eventda.

Imkoniyatlar: CAP-030.

### DB-077 billing_ledger

Pul va kreditning append-only jurnali.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| organization_id | uuid / NO | DB-021 organizations.id |
| order_id | uuid / YES | DB-071 orders.id |
| payment_attempt_id | uuid / YES | DB-073 payment_attempts.id |
| refund_id | uuid / YES | DB-076 refunds.id |
| entry_kind | text / NO | - |
| amount | numeric(18,2) / NO | - |
| currency | text / NO | - |
| occurred_at | timestamptz / NO | - |
| dedupe_key | text / NO | - |

UNIQUE: dedupe_key

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Capture/refund/credit manbasi ko‘rsatiladi; balans tahrirlanmaydi. Reconciliation bank/provider natijasiga; bu nomzod ish haqi yoki escrow hamyoni emas.

Imkoniyatlar: CAP-029, CAP-030, CAP-038.

## OPS - Moderatsiya, yordam va maxfiylik


### DB-078 moderation_cases

E’lon, tashkilot, fayl yoki bahoga shikoyat.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| reporter_id | uuid / NO | DB-001 users.id |
| opportunity_id | uuid / YES | DB-035 opportunities.id |
| organization_id | uuid / YES | DB-021 organizations.id |
| rating_id | uuid / YES | DB-064 rating_submissions.id |
| file_id | uuid / YES | DB-018 files.id |
| category | text / NO | - |
| status | text / NO | - |
| severity | text / NO | - |
| assigned_to_id | uuid / YES | DB-001 users.id |
| due_at | timestamptz / NO | - |
| decision | text / YES | - |
| decided_at | timestamptz / YES | - |

CHECK: num_nonnulls(opportunity_id,organization_id,rating_id,file_id) = 1

INDEX: status,severity,due_at

Target FK bilan. Avtomatik signal navbat yaratadi; sudsiz qora ro‘yxat yoki pulga yashirish yo‘q. Scam bo‘lsa vaqtli hide va mustaqil review.

Imkoniyatlar: CAP-028, CAP-032, CAP-033.

### DB-079 moderation_actions

Cheklash/ochish/apellyatsiya tarixi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| case_id | uuid / NO | DB-078 moderation_cases.id |
| actor_id | uuid / NO | DB-001 users.id |
| action | text / NO | - |
| reason | text / NO | - |
| expires_at | timestamptz / YES | - |
| appealed_action_id | uuid / YES | DB-079 moderation_actions.id |
| occurred_at | timestamptz / NO | - |

INDEX: case_id,occurred_at

Append-only; apellyatsiyani dastlabki qaror egasi yakka hal qilmaydi. E’lon yashirilsa accepted munosabat/o‘z dalili yo‘qolmaydi.

Imkoniyatlar: CAP-032, CAP-033.

### DB-080 support_tickets

Foydalanuvchi yordami.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| requester_id | uuid / NO | DB-001 users.id |
| category | text / NO | - |
| priority | text / NO | - |
| status | text / NO | - |
| assignee_id | uuid / YES | DB-001 users.id |
| subject | text / NO | - |
| first_response_due_at | timestamptz / NO | - |
| resolved_at | timestamptz / YES | - |

INDEX: status,priority,first_response_due_at; requester_id,created_at

Ruxsatli yordam xodimi zarur qismni ko‘radi; parol/OTP so‘ramaydi.

Imkoniyatlar: CAP-034.

### DB-081 support_messages

Yordam yozishmasi va ilova.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| ticket_id | uuid / NO | DB-080 support_tickets.id |
| author_id | uuid / NO | DB-001 users.id |
| body | text / NO | - |
| file_id | uuid / YES | DB-018 files.id |
| internal | boolean / NO | - |

INDEX: ticket_id,created_at

Internal note foydalanuvchi eksportiga chiqmaydi; ilova ayni ticketga ruxsat bilan.

Imkoniyatlar: CAP-034.

### DB-082 privacy_requests

Eksport, tuzatish va o‘chirish.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| kind | text / NO | - |
| status | text / NO | - |
| verified_at | timestamptz / YES | - |
| due_at | timestamptz / NO | - |
| result_file_id | uuid / YES | DB-018 files.id |
| resolved_at | timestamptz / YES | - |
| reason | text / YES | - |

INDEX: status,due_at

Eksport qayta auth, qisqa TTL link. O‘chirish moliya/legal hold bilan retention siyosatiga muvofiq; muddat huquqiy tasdiqdan so‘ng.

Imkoniyatlar: CAP-035.

### DB-083 retention_policies

Ma’lumot toifasi va saqlash rejasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| data_class | text / NO | - |
| policy_version | integer / NO | - |
| active_days | integer / YES | - |
| backup_expiry_days | integer / NO | - |
| legal_basis | text / NO | - |
| status | text / NO | - |

UNIQUE: data_class,policy_version

CHECK: active_days IS NULL OR active_days >= 0; backup_expiry_days > 0

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Taklif va qonuniy muddat ajratiladi; NULL muddatsiz saqlash ruxsati emas, qaror kutilmoqda. Legal approval bo‘lmagan toifa pilotda yig‘ilmaydi.

Imkoniyatlar: CAP-035.

### DB-084 legal_holds

Nizo uchun minimal saqlash to‘xtatgichi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / YES | DB-001 users.id |
| organization_id | uuid / YES | DB-021 organizations.id |
| case_id | uuid / YES | DB-078 moderation_cases.id |
| reason | text / NO | - |
| authorized_by_id | uuid / NO | DB-001 users.id |
| expires_at | timestamptz / NO | - |
| released_at | timestamptz / YES | - |

CHECK: num_nonnulls(user_id,organization_id,case_id) = 1

INDEX: expires_at,released_at

Vakolatli asos va aniq muddat; barcha hisobni cheksiz saqlash uchun bahona emas.

Imkoniyatlar: CAP-035.

## SYS - Xabar, audit va boshqaruv


### DB-085 notification_preferences

Kanal va maqsad sozlamasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| channel | text / NO | - |
| purpose | text / NO | - |
| enabled | boolean / NO | - |
| consent_event_id | uuid / YES | DB-011 consent_events.id |

UNIQUE: user_id,channel,purpose

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Marketing opt-in; zarur statuslar sayt ichida qoladi. External kanal tanloviga hurmat qilinadi.

Imkoniyatlar: CAP-031.

### DB-086 outbox_events

DB tranzaksiyasi bilan chiqadigan hodisa.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| event_type | text / NO | - |
| schema_version | integer / NO | - |
| aggregate_key | text / NO | - |
| payload | jsonb / NO | - |
| dedupe_key | text / NO | - |
| available_at | timestamptz / NO | - |
| processed_at | timestamptz / YES | - |
| attempts | integer / NO | - |

UNIQUE: dedupe_key

CHECK: schema_version > 0; attempts >= 0

INDEX: processed_at,available_at

Append-only biznes hodisa; payload PII emas yoki minimal opaque ID. Consumer eng kamida bir marta kelishiga chidamli; aggregate_key audit/routing uchun, domain FK o‘rniga emas.

Imkoniyatlar: CAP-031, CAP-037.

### DB-087 notifications

Foydalanuvchiga sayt xabari.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| event_id | uuid / NO | DB-086 outbox_events.id |
| template_code | text / NO | - |
| opportunity_id | uuid / YES | DB-035 opportunities.id |
| application_id | uuid / YES | DB-041 applications.id |
| placement_id | uuid / YES | DB-049 placements.id |
| ticket_id | uuid / YES | DB-080 support_tickets.id |
| read_at | timestamptz / YES | - |

UNIQUE: user_id,event_id,template_code

INDEX: user_id,read_at,created_at

Havola ochilganda joriy huquq qayta tekshiriladi; xabarda maxfiy CV/log matni yo‘q.

Imkoniyatlar: CAP-031.

### DB-088 notification_deliveries

Kanalga yuborish urinishlari.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| notification_id | uuid / NO | DB-087 notifications.id |
| channel | text / NO | - |
| provider | text / NO | - |
| provider_message_id | text / YES | - |
| status | text / NO | - |
| attempt_no | integer / NO | - |
| next_retry_at | timestamptz / YES | - |
| delivered_at | timestamptz / YES | - |
| error_code | text / YES | - |

UNIQUE: notification_id,channel,attempt_no

CHECK: attempt_no > 0

INDEX: status,next_retry_at

Provider timeout retry backoff+jitter va xarajat limiti; callback foydalanuvchi tasdiqi emas. SMS/WhatsApp delivery OTP consume qilmaydi.

Imkoniyatlar: CAP-031.

### DB-089 audit_events

Vakolatli amallarning append-only izi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| actor_id | uuid / YES | DB-001 users.id |
| session_id | uuid / YES | DB-004 sessions.id |
| action | text / NO | - |
| object_type | text / NO | - |
| object_key | text / NO | - |
| scope_snapshot | jsonb / NO | - |
| before_digest | text / YES | - |
| after_digest | text / YES | - |
| reason | text / YES | - |
| request_id | text / NO | - |
| occurred_at | timestamptz / NO | - |

INDEX: actor_id,occurred_at; object_type,object_key,occurred_at; request_id

Object nomi tarixiy audit identifikatori, aktiv domain FK emas. Sir/OTP/raw CV yo‘q; DB roli update/delete qilolmaydi, tashqi immutable nusxa. Aktyor pseudonymi tarixni saqlaydi.

Imkoniyatlar: CAP-026, CAP-036.

### DB-090 idempotency_keys

Sezgir HTTP amallarining bir marta natijasi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| user_id | uuid / NO | DB-001 users.id |
| operation | text / NO | - |
| key | text / NO | - |
| request_digest | text / NO | - |
| response_status | integer / YES | - |
| response_ref | text / YES | - |
| expires_at | timestamptz / NO | - |

UNIQUE: user_id,operation,key

INDEX: expires_at

Body digest boshqa bo‘lsa409. Token ownership, operation va scope bilan. Biznes UNIQUE constraintlar TTLdan keyin ham takror moliya yaratishni to‘sadi.

Imkoniyatlar: CAP-007, CAP-011.

### DB-091 analytics_events

O‘lchov va segment, PII emas.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| event_key | text / NO | - |
| event_name | text / NO | - |
| actor_pseudonym | text / YES | - |
| cohort | text / YES | - |
| properties | jsonb / NO | - |
| occurred_at | timestamptz / NO | - |
| schema_version | integer / NO | - |

UNIQUE: event_key

INDEX: event_name,occurred_at

Kontakt/log/CV yo‘q; rozilik asosli statistika. Ish boshlash faqat 2tomon tasdiq hodisasi, raw click bilan teng emas.

Imkoniyatlar: CAP-037.

### DB-092 feature_flags

Xizmatni boshqariladigan ishga tushirish.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| code | text / NO | - |
| enabled | boolean / NO | - |
| rule_schema | jsonb / NO | - |
| changed_by_id | uuid / NO | DB-001 users.id |
| reason | text / NO | - |

UNIQUE: code

INDEX: PK/UNIQUE va FK leading-column indekslar; schema_loyihasi.sqlga qarang.

Default OFF: ratings, academic_official_export, WhatsApp, paid_checkout. Flag ruxsatni chetlab o‘tmaydi; o‘zgarish auditlanadi.

Imkoniyatlar: CAP-037, CAP-039, CAP-040.

### DB-093 incidents

Uzilish, egalik va tiklash dalili.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| severity | text / NO | - |
| status | text / NO | - |
| commander_id | uuid / NO | DB-001 users.id |
| summary | text / NO | - |
| started_at | timestamptz / NO | - |
| resolved_at | timestamptz / YES | - |
| postmortem_ref | text / YES | - |

INDEX: status,severity,started_at

24/7 yordam va’dasi faqat amaldagi navbatchi bilan; hozir P1 on-call tashkil etilishi reliz sharti.

Imkoniyatlar: CAP-036, CAP-037.

### DB-094 restore_runs

Backupni tiklash tekshiruvi.

| Maydon | Type / NULL | PK yoki FK |
| --- | --- | --- |
| id | uuid / NO | PK |
| created_at | timestamptz / NO | - |
| updated_at | timestamptz / NO | - |
| started_at | timestamptz / NO | - |
| finished_at | timestamptz / YES | - |
| backup_ref | text / NO | - |
| status | text / NO | - |
| recovered_through | timestamptz / YES | - |
| measured_rpo_minutes | integer / YES | - |
| measured_rto_minutes | integer / YES | - |
| checked_by_id | uuid / NO | DB-001 users.id |
| evidence_ref | text / YES | - |

INDEX: started_at

Backup fayli borligi restore testi emas. Billing yoqilishidan oldin PITR/ledger reconciliation dalili.

Imkoniyatlar: CAP-037.
