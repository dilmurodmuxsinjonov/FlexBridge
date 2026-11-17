# Backend — domen spetsifikatsiyalari indeksi

Kod xaritasi va qoidalar: [`backend/AGENTS.md`](../../backend/AGENTS.md). Ishga tushirish, migratsiya va testlar: [`backend/README.md`](../../backend/README.md). API matritsasi: [`contracts/r1_api_matrix.csv`](../../contracts/r1_api_matrix.csv).

## Xavfsizlik, IAM va fayllar (`security_iam/`)

| Fayl | Mavzu (faylning o'z sarlavhasi) |
| --- | --- |
| [FILE_AUTHORITY.md](security_iam/FILE_AUTHORITY.md) | Current-session authority for owner file operations |
| [IAM.md](security_iam/IAM.md) | IAM — hisob, kirish va xavfsizlik |
| [STORAGE_VERSIONS.md](security_iam/STORAGE_VERSIONS.md) | Explicit versions for scanned private objects |
| [TELEGRAM_BOT.md](security_iam/TELEGRAM_BOT.md) | Telegram bot orqali telefon raqamni tasdiqlash |

## Nomzod (talaba) (`candidate/`)

| Fayl | Mavzu (faylning o'z sarlavhasi) |
| --- | --- |
| [CANDIDATE.md](candidate/CANDIDATE.md) | Candidate backend (CAN-CODEX-001) |
| [CANDIDATE_AUTHORITY.md](candidate/CANDIDATE_AUTHORITY.md) | Current-session authority for candidate self-service |

## Tashkilot, egalik va billing (`organization/`)

| Fayl | Mavzu (faylning o'z sarlavhasi) |
| --- | --- |
| [BILLING_AUTHORITY.md](organization/BILLING_AUTHORITY.md) | Human money authority |
| [INVITATIONS.md](organization/INVITATIONS.md) | Organization invitations (ORG-CODEX-002) |
| [ORGANIZATIONS.md](organization/ORGANIZATIONS.md) | Organization onboarding (ORG-CODEX-001) |
| [ORGANIZATION_AUTHORITY.md](organization/ORGANIZATION_AUTHORITY.md) | Organization authority and transaction ordering |
| [OWNER_ADDITIONS.md](organization/OWNER_ADDITIONS.md) | Independently reviewed additional owners |
| [OWNER_CONTINUITY.md](organization/OWNER_CONTINUITY.md) | Existing-staff OWNER continuity |
| [OWNER_TRANSFERS.md](organization/OWNER_TRANSFERS.md) | Reviewed OWNER departure |

## Akademik: OTM, amaliyot, talabalik (`academic/`)

| Fayl | Mavzu (faylning o'z sarlavhasi) |
| --- | --- |
| [ACADEMIC_ADMISSION.md](academic/ACADEMIC_ADMISSION.md) | Pending academic admission |
| [ACADEMIC_DECISIONS.md](academic/ACADEMIC_DECISIONS.md) | Placement-wide academic conclusion contract (Issue76) |
| [ACADEMIC_LEGACY_NOTICES.md](academic/ACADEMIC_LEGACY_NOTICES.md) | Fresh academic acceptance on retained scope (Issue70) |
| [ACADEMIC_RECORDS.md](academic/ACADEMIC_RECORDS.md) | Minimum academic record view (Issue67, LOG-072) |
| [ACADEMIC_REVIEWS.md](academic/ACADEMIC_REVIEWS.md) | Exact-revision academic feedback (Issue67, LOG-073) |
| [ACADEMIC_VIEWS.md](academic/ACADEMIC_VIEWS.md) | Current academic lists and coordinator notices (LOG-071) |
| [ENROLLMENTS.md](academic/ENROLLMENTS.md) | Own education history and enrollment verification |
| [INSTITUTION_AUTHORITY.md](academic/INSTITUTION_AUTHORITY.md) | Current institutional authority gate |
| [INSTITUTION_ONBOARDING.md](academic/INSTITUTION_ONBOARDING.md) | Reviewed institution appointments |
| [PLACEMENT_ADMISSION.md](academic/PLACEMENT_ADMISSION.md) | Placement admission — current draft |

## Platforma operatsiyalari va moderatsiya (`platform_ops/`)

| Fayl | Mavzu (faylning o'z sarlavhasi) |
| --- | --- |
| [FEATURE_FLAG_ADMINISTRATION.md](platform_ops/FEATURE_FLAG_ADMINISTRATION.md) | Global feature flag state administration |
| [MODERATION_APPEALS.md](platform_ops/MODERATION_APPEALS.md) | Opportunity rejection appeals |
| [MODERATION_AUTHORITY.md](platform_ops/MODERATION_AUTHORITY.md) | Initial moderation authority |
| [OPERATIONS.md](platform_ops/OPERATIONS.md) | Operational evaluations |

## Yangi spetsifikatsiya qo'shish

Domen papkasini tanlang, faylga endpointlar, vakolat qoidalari, xato kodlari, migratsiya va testlarni yozing; shu indeksga qator qo'shing.
