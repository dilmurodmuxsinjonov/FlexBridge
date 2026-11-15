# FlexBridge 1.4: Avtomatlashtirilgan Staging Testlari Katalogi

Ushbu katalog FlexBridge 1.4 platformasining barcha 24 ta mustaqil staging test to‘plamlarini o‘z ichiga oladi. Barcha testlar Docker konteynerlaridagi haqiqiy backend (`127.0.0.1:8000`), PgBouncer (`127.0.0.1:5432/flexbridge`), va Next.js 16 BFF (`127.0.0.1:3000`) stekiga qarshi to‘g‘ridan-to‘g‘ri ishlaydi.

---

## 1. Yagona Master Runner

Barcha 24 ta test to‘plamini ketma-ket yurgazish, avtomatik rate-limit tozalash va umumiy ijro xulosasini olish uchun:

```powershell
python scripts/run_all_staging_tests.py
```

---

## 2. Test To‘plamlari Katalogi (Domenlar Bo‘yicha)

### A. Nomzod & Talabalar Bo‘limi (Candidate Workflows)
| Skript | Tekshiriladigan Xizmatlar & Shartnomalar |
| :--- | :--- |
| `test_candidate_profile_staging.py` | Profil tahriri, 14 ta hudud, ko‘nikmalar katalogi, haftalik dars jadvali (`API-026`, `API-028`, `API-032`, `API-035`). |
| `test_candidate_applications_staging.py` | Arizalar xulosasi, filtrlar, urinishlar tarixi, arizani qaytarib olish va qayta topshirish (`API-029`, `API-039`, `API-040`, `API-044`). |
| `test_candidate_saved_notifications_staging.py` | Saqlangan e’lonlar (bookmarks), bildirishnomalar oqimi va o‘qilganlik belgilari (`API-004`, `API-031`, `API-037`, `API-038`). |
| `test_candidate_internship_logs_staging.py` | Raqamli amaliyot kundaligi, 8-soatlik limit tekshiruvi, topshiriqlar va baholash feedbacki (`API-030`, `API-053`, `API-054`, `API-056`). |
| `test_candidate_offers_engagements_staging.py` | Ish taklifiga javob (Accept/Decline), ikki tomonlama boshlanish tasdig‘i va o‘quv rejasi (`API-043`, `API-045`, `API-046`, `API-048`, `API-050`). |
| `test_candidate_ratings_appeals_staging.py` | Ikki tomonlama maxfiy baholash (Double-Blind), sharhlar va apellyatsiya shikoyati (`API-047`, `API-057`, `API-058`). |
| `test_candidate_enrollments_exceptions_staging.py`| OTM talabalik hujjati (HEMIS), biriktiruvni yakunlash va sana bo‘yicha istisnolar (`API-027`, `API-034`, `API-036`). |

### B. Ish Beruvchi Tashkilotlar Bo‘limi (Employer Workflows)
| Skript | Tekshiriladigan Xizmatlar & Shartnomalar |
| :--- | :--- |
| `test_employer_kanban_staging.py` | HR arizalar voronkasi (Kanban), nomzodlar saralash, intervyu tayinlash va taklif berish (`API-068`, `API-083`, `API-084`, `API-085`). |
| `test_vacancy_lifecycle_interviews_staging.py` | Vakansiya nashr qilish, to‘xtatish, yopish va nomzod intervyu javoblari (`API-042`, `API-081`, `API-082`). |
| `test_employer_mentor_staging.py` | Korxona mentori kundaliklar navbati, shoshilinch eskalatsiya va kundalikni baholash (`API-089`, `API-090`, `API-091`, `API-092`). |
| `test_employer_organization_staging.py` | Tashkilot verifikatsiyasi (STIR), imkoniyatlar (Capabilities), jamoa a’zolari va taklifnomalar (`API-067`, `API-072`, `API-073`, `API-074`, `API-075`). |
| `test_employer_billing_staging.py` | To‘lovlar, xizmat kvotalari telemetriyasi, obuna buyurtmalari va pulni qaytarish (`API-070`, `API-093`, `API-094`, `API-095`). |

### C. Universitet & OTM Bo‘limi (University Workflows)
| Skript | Tekshiriladigan Xizmatlar & Shartnomalar |
| :--- | :--- |
| `test_university_academic_reviews_staging.py` | OTM kafedra nazoratchisi kundaliklar navbati va akademik baholash xulosasi (`API-105`, `API-106`, `API-107`). |
| `test_university_placements_staging.py` | Biriktirilgan amaliyotlar, butun amaliyot bo‘yicha yakuniy akademik xulosa va taqsimot (`API-102`, `API-103`, `API-104`, `API-108`). |
| `test_university_exports_staging.py` | Rasmiy amaliyot hisobotlari eksporti (PDF/JSON), superviziyalar va hamkorlik shartnomalari (`API-098`, `API-100`, `API-101`). |

### D. Tizim Operatori & SOC Bo‘limi (Operator Workflows)
| Skript | Tekshiriladigan Xizmatlar & Shartnomalar |
| :--- | :--- |
| `test_operator_portal_staging.py` | Kriptografik audit stream, verifikatsiya arizalari navbati, 4-ko‘z break-glass va sessiyalarni bekor qilish (`API-109`, `API-110`, `API-118`, `API-119`, `API-120`). |
| `test_operator_support_ops_staging.py` | Mijozlar murojaatlari navbati, ichki qaydlar, operatsion insidentlar va DR tiklash SLA ko‘rsatkichlari (`API-112`, `API-113`, `API-122`, `API-123`, `API-124`). |
| `test_operator_finance_staging.py` | Buxgalteriya moliyaviy balansi, to‘lov shlyuzlari solishtiruvi va 4-ko‘z tamoyilidagi qaytarishlar (`API-078`, `API-115`, `API-117`). |

### E. Xavfsizlik & Foydalanuvchi Boshqaruvi (Security & Auth)
| Skript | Tekshiriladigan Xizmatlar & Shartnomalar |
| :--- | :--- |
| `test_user_support_privacy_staging.py` | Foydalanuvchi qo‘llab-quvvatlash chiptalari, GDPR/APPI shaxsiy ma’lumotlar huquqlari va bildirishnoma sozlamalari (`API-059`, `API-062`, `API-063`, `API-064`, `API-114`). |
| `test_user_security_sessions_staging.py` | Parolni o‘zgartirish, TOTP 2FA ro‘yxatdan o‘tkazish/tasdiqlash, 8 ta favqulodda zaxira kodi va ko‘p qurilmali sessiyalar (`API-060`, `API-061`). |
| `test_standalone_auth_pages_staging.py` | Mustaqil `/kirish` (MFA challenge bilan), 3-qadamli `/royxatdan-otish` (SMS challenge & consume), va SSR navigatsiyasi (`API-002`, `CAP-002`). |

### F. Ommaviy Xizmatlar & Platforma Integratsiyasi
| Skript | Tekshiriladigan Xizmatlar & Shartnomalar |
| :--- | :--- |
| `test_bff_staging.py` | Next.js Server-Side BFF sessiya chegarasi, CSRF tekshiruvi va HttpOnly kuki xavfsizligi. |
| `test_opportunity_application_staging.py`| Ommaviy e’lon ko‘rish (`API-005`), takroriy ariza topshirishdan himoya va vakansiya qoralama yaratish (`API-006`, `API-068`). |
| `test_public_cms_footer_staging.py` | Ommaviy yuridik siyosatlar (`API-014`), qo‘llanmalar (`API-013`), `/shartlar`, `/maxfiylik`, `/haqida` va ko‘p ustunli zamonaviy footer. |
| `test_staging_e2e.py` | 5-bosqichli infratuzilma integratsiyasi (9 ta tayyorgarlik zondi, IAM, PgBouncer 20 parallel worker, MinIO va ClamAV antivirus). |

---

## 3. Alohida Test To‘plamini Ishga Tushirish

Istalgan test to‘plamini mustaqil ravishda ishga tushirish mumkin:

```powershell
python scripts/test_standalone_auth_pages_staging.py
python scripts/test_public_cms_footer_staging.py
python scripts/test_user_security_sessions_staging.py
```
