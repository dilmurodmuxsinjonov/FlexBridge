# FlexBridge 1.4 — Markazlashtirilgan Hujjatlar va Jurnallar Katalogi (`docs/`)

Loyiha kodi (`frontend/` va `backend/`) toza saqlanishi uchun barcha `.md`, `.pdf`, `.pptx` va `.txt` hujjatlar ushbu `docs/` katalogi ichidagi mavzuli ichki papkalarga ajratilgan.

---

## 1. Ichki Papkalar Tuzilmasi

```
docs/
├── journals/                                # Loyiha xotirasi, arxitektura va bosqichlar jurnallari
│   ├── 01_AI_XOTIRASI_VA_QOIDALAR.md        # Tizim xotirasi va to'liq loglar (LOG-001..LOG-150)
│   ├── 02_TEXNIK_MODELLAR.md                # 1.4 texnik topshiriq va kanonik domen modellari
│   ├── 03_BOSQICHLAR_VA_HOLAT.md            # Barcha bosqichlar ijrosi va joriy holat
│   ├── 04_TAKLIFLAR_VA_TANLOVLAR.md         # Texnologik stek tanlovlari va qarorlar
│   ├── 05_S1_1_TALABLAR_VA_MANBALAR_XARITASI.md # Normativ hujjatlar va talablar xaritasi
│   └── FlexBridge_kelgusi_bosqichlar.md     # Kelgusi bosqichlar rejasi
│
├── protocols/                               # Agentlar boshqaruvi va Handoff protokollari
│   ├── ANTIGRAVITY_HANDOFF.md               # Antigravity joriy ish va davom ettirish tartibi
│   └── ANTIGRAVITY_MASTER_PROTOCOL.md       # Q016 Master succession va boshqaruv shartnomasi
│
├── presentations/                           # Taqdimotlar, Texnik Topshiriq PDF va Qo'llanmalar
│   ├── FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf
│   ├── FlexBridge_Investorlar_uchun.pdf
│   ├── FlexBridge_Investorlar_uchun.pptx
│   ├── FlexBridge_Ustoz_uchun_loyiha_izohi.md
│   ├── FlexBridge_Ustoz_uchun_loyiha_izohi.pdf
│   └── Oqish_tartibi.txt
│
└── backend/                                 # Backend xizmatlari va domen spetsifikatsiyalari (26 ta .md)
    ├── academic/                            # OTM, amaliyot, o'qituvchilar va akademik baholash (10 ta fayl)
    │   ├── ACADEMIC_ADMISSION.md
    │   ├── ACADEMIC_DECISIONS.md
    │   ├── ACADEMIC_LEGACY_NOTICES.md
    │   ├── ACADEMIC_RECORDS.md
    │   ├── ACADEMIC_REVIEWS.md
    │   ├── ACADEMIC_VIEWS.md
    │   ├── ENROLLMENTS.md
    │   ├── INSTITUTION_AUTHORITY.md
    │   ├── INSTITUTION_ONBOARDING.md
    │   └── PLACEMENT_ADMISSION.md
    ├── candidate/                           # Nomzod profili, ko'nikmalar, rezyume va vakolatlar (2 ta fayl)
    │   ├── CANDIDATE.md
    │   └── CANDIDATE_AUTHORITY.md
    ├── organization/                        # Ish beruvchi korxonalar, taklifnomalar, egalik va billing (7 ta fayl)
    │   ├── BILLING_AUTHORITY.md
    │   ├── INVITATIONS.md
    │   ├── ORGANIZATIONS.md
    │   ├── ORGANIZATION_AUTHORITY.md
    │   ├── OWNER_ADDITIONS.md
    │   ├── OWNER_CONTINUITY.md
    │   └── OWNER_TRANSFERS.md
    ├── security_iam/                        # IAM, autentifikatsiya, fayl karantini va S3 versiyalash (3 ta fayl)
    │   ├── FILE_AUTHORITY.md
    │   ├── IAM.md
    │   └── STORAGE_VERSIONS.md
    └── platform_ops/                        # Operatsiyalar, moderatsiya apellyatsiyalari va feature-flaglar (4 ta fayl)
        ├── FEATURE_FLAG_ADMINISTRATION.md
        ├── MODERATION_APPEALS.md
        ├── MODERATION_AUTHORITY.md
        └── OPERATIONS.md
```
