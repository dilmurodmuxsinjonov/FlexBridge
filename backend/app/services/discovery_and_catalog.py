"""Public Discovery, Onboarding Options, and Knowledge / CMS Policies Service.

Implements:
- API-002: GET /api/v1/onboarding/options (`CAP-002`, `AUTH_SELF`)
- API-011: GET /api/v1/services/public (`CAP-039`, `PUBLIC_INFO`)
- API-012: GET /api/v1/prices/public (`CAP-039`, `PUBLIC_INFO`)
- API-013: GET /api/v1/help/{document} (`CAP-039`, `PUBLIC_INFO`)
- API-014: GET /api/v1/policies/{document} (`CAP-039`, `PUBLIC_INFO`)

Stage 2 Directive:
Freelance paths are decoupled and clearly designated as PLANNED / Stage 2 extension points
without contaminating R1 operational logic.
"""

from __future__ import annotations

from typing import Any
from fastapi import HTTPException


class DiscoveryAndCatalogService:
    """Manages public onboarding tracks, catalog offerings, pricing, and versioned CMS documents."""

    HELP_DOCUMENTS: dict[str, dict[str, Any]] = {
        "faq": {
            "title": "Ko'p Beriladigan Savollar (FAQ)",
            "version": "1.0",
            "effective_date": "2026-01-01",
            "content_markdown": "# Ko'p Beriladigan Savollar\n\n### 1. FlexBridge nima?\nFlexBridge — talabalar va yosh mutaxassislarni haqiqiy ish beruvchilar hamda amaliyot bazalari bilan bog'lovchi milliy platforma.\n\n### 2. Dars jadvali bilan moslik qanday tekshiriladi?\nPlatforma algoritmik tekshiruv (API-003) orqali talabaning o'quv darslari va korxona smenalarini to'liq solishtiradi va ziddiyatlarga yo'l qo'ymaydi.\n\n### 3. Amaliyot kundaligi qanday yuritiladi?\nTalaba har kuni bajargan ishlarini kiritadi, korxona mentori tasdiqlaydi va OTM koordinatori nazorat qiladi.",
            "sections": [
                {"heading": "FlexBridge haqida", "anchor": "flexbridge-haqida"},
                {"heading": "Dars jadvali va moslik", "anchor": "dars-jadvali-va-moslik"},
                {"heading": "Raqamli amaliyot kundaligi", "anchor": "raqamli-amaliyot-kundaligi"},
            ],
        },
        "getting-started": {
            "title": "Platformada Ish Boshlash Qo'llanmasi",
            "version": "1.0",
            "effective_date": "2026-01-01",
            "content_markdown": "# Ish Boshlash Qo'llanmasi\n\n1. Telefon raqamingiz orqali ro'yxatdan o'ting.\n2. Tegishli rolingizni (Talaba, Nomzod, Ish beruvchi yoki OTM) tanlang.\n3. Profil ma'lumotlarini to'ldiring va o'zingizga mos imkoniyatlarni toping.",
            "sections": [
                {"heading": "Ro'yxatdan o'tish", "anchor": "royxatdan-otish"},
                {"heading": "Rolni tanlash", "anchor": "rolni-tanlash"},
                {"heading": "Profilni tasdiqlash", "anchor": "profilni-tasdiqlash"},
            ],
        },
        "candidate-guide": {
            "title": "Nomzod va Talabalar Uchun Qo'llanma",
            "version": "1.0",
            "effective_date": "2026-01-01",
            "content_markdown": "# Nomzodlar Uchun Qo'llanma\n\n- E'lonlar katalogidan o'zingizga qiziq bo'sh ish o'rinlarini qidiring.\n- Jadvalingizga mos keladigan smenalarga ariza topshiring.\n- Ariza holatini shaxsiy kabinetingizda kuzatib boring.",
            "sections": [
                {"heading": "E'lonlarni saralash", "anchor": "elonlarni-saralash"},
                {"heading": "Ariza topshirish qoidalari", "anchor": "ariza-topshirish-qoidalari"},
            ],
        },
        "employer-guide": {
            "title": "Ish Beruvchilar va Tashkilotlar Uchun Qo'llanma",
            "version": "1.0",
            "effective_date": "2026-01-01",
            "content_markdown": "# Ish Beruvchilar Qo'llanmasi\n\n- Korxonangiz profilini yarating va STIR orqali tasdiqlang.\n- Yangi bo'sh ish o'rni yoki amaliyot e'lonini joylashtiring.\n- Tushgan arizalarni ko'rib chiqing va intervyular belgilang.",
            "sections": [
                {"heading": "Tashkilotni ro'yxatdan o'tkazish", "anchor": "tashkilotni-royxatdan-otkazish"},
                {"heading": "E'lon berish", "anchor": "elon-berish"},
                {"heading": "Arizachilarni baholash", "anchor": "arizachilarni-baholash"},
            ],
        },
        "academic-guide": {
            "title": "OTMlar va Kafedra Koordinatorlari Qo'llanmasi",
            "version": "1.0",
            "effective_date": "2026-01-01",
            "content_markdown": "# OTMlar Uchun Qo'llanma\n\n- Talabalar ro'yxatini va amaliyot buyruqlarini boshqaring.\n- Amaliyot bazalarini biriktiring va kafedra o'qituvchilarini mas'ul etib belgilang.\n- Raqamli amaliyot kundaliklarini tasdiqlang va hisobotlarni eksport qiling.",
            "sections": [
                {"heading": "OTM integratsiyasi", "anchor": "otm-integratsiyasi"},
                {"heading": "Kafedra nazorati", "anchor": "kafedra-nazorati"},
            ],
        },
        "schedule-matching": {
            "title": "Jadval Mosligi (Matching Engine) Ishlash Tamoyili",
            "version": "1.0",
            "effective_date": "2026-01-01",
            "content_markdown": "# Jadval Mosligi Tamoyili\n\nFlexBridge algoritmi talabaning dars jadvalini, qatnov buferini (commute buffer) va ish smenalarini daqiqama-daqiqa taqqoslaydi. Har qanday kesishuv bo'lsa, ariza rad etiladi yoki ogohlantirish beriladi.",
            "sections": [
                {"heading": "Vaqt buferi", "anchor": "vaqt-buferi"},
                {"heading": "Algoritmik solishtirish", "anchor": "algoritmik-solishtirish"},
            ],
        },
    }

    POLICIES: dict[str, dict[str, Any]] = {
        "terms": {
            "title": "Foydalanish Shartlari (Terms of Service)",
            "version": "2026.1",
            "effective_date": "2026-01-01",
            "contact_email": "legal@flexbridge.uz",
            "content_markdown": "# Foydalanish Shartlari\n\n1. Ushbu shartlar platformadan foydalanishning umumiy tartibini belgilaydi.\n2. Barcha ishtirokchilar faqat haqqoniy va tasdiqlangan ma'lumotlarni taqdim etishi shart.\n3. Mehnat va ta'lim to'g'risidagi qonunchilik talablari qat'iy bajarilishi lozim.",
            "clauses": [
                {"id": "TERMS-01", "title": "Umumiy qoidalar", "summary": "Platforma xizmatlaridan foydalanish asoslari."},
                {"id": "TERMS-02", "title": "Tomonlarning majburiyatlari", "summary": "Nomzod, ish beruvchi va OTM majburiyatlari."},
                {"id": "TERMS-03", "title": "Javobgarlik chegarasi", "summary": "Xizmat ko'rsatish va xavfsizlik kafolatlari."},
            ],
        },
        "privacy": {
            "title": "Maxfiylik Siyosati (Privacy Policy)",
            "version": "2026.1",
            "effective_date": "2026-01-01",
            "contact_email": "privacy@flexbridge.uz",
            "content_markdown": "# Maxfiylik Siyosati\n\n1. Foydalanuvchilarning shaxsiy ma'lumotlari O'zbekiston Respublikasi 'Shaxsiy ma'lumotlar to'g'risida'gi qonuniga muvofiq himoyalanadi.\n2. AC-023 talabiga muvofiq, tashkilot va foydalanuvchilarning baholash ko'rsatkichlari 5 tadan kam bo'lganda maxfiy tutiladi.\n3. Ma'lumotlar uchinchi shaxslarga tijoriy maqsadda sotilmaydi.",
            "clauses": [
                {"id": "PRIV-01", "title": "Ma'lumotlar to'plami", "summary": "To'planadigan shaxsiy ma'lumotlar turlari."},
                {"id": "PRIV-02", "title": "Differensial maxfiylik", "summary": "AC-023 maxfiylik chegarasi va anonimlashtirish."},
                {"id": "PRIV-03", "title": "Ma'lumotlarni o'chirish huquqi", "summary": "Foydalanuvchining hisobni o'chirish huquqi."},
            ],
        },
        "cookies": {
            "title": "Cookie Fayllari Siyosati (Cookie Policy)",
            "version": "2026.1",
            "effective_date": "2026-01-01",
            "contact_email": "support@flexbridge.uz",
            "content_markdown": "# Cookie Siyosati\n\nPlatforma faqat sessiyani xavfsiz saqlash va tizim ishlashini ta'minlash uchun zaruriy cookie fayllaridan foydalanadi.",
            "clauses": [
                {"id": "COOKIE-01", "title": "Zaruriy fayllar", "summary": "Autentifikatsiya va CSRF himoyasi cookie fayllari."},
            ],
        },
        "acceptable-use": {
            "title": "Maqbul Foydalanish Qoidalari (Acceptable Use Policy)",
            "version": "2026.1",
            "effective_date": "2026-01-01",
            "contact_email": "abuse@flexbridge.uz",
            "content_markdown": "# Maqbul Foydalanish Qoidalari\n\nPlatformada soxta e'lonlar, firibgarlik, diskriminatsiya va xavfsizlik tizimlarini buzish qat'iyan man etiladi.",
            "clauses": [
                {"id": "AUP-01", "title": "Taqiqlangan faoliyat", "summary": "Spam, soxta e'lonlar va kiberhujumlar taqiqlanadi."},
            ],
        },
        "rating-guidelines": {
            "title": "Xolis Baholash Qoidalari (Rating Guidelines)",
            "version": "2026.1",
            "effective_date": "2026-01-01",
            "contact_email": "ratings@flexbridge.uz",
            "content_markdown": "# Baholash Qoidalari\n\nAC-024 bo'yicha baholash ikki tomonlama maxfiy (double-blind) tartibda o'tkaziladi. Har ikki tomon baholaguncha natija ko'rsatilmaydi.",
            "clauses": [
                {"id": "RATE-01", "title": "Ikki tomonlama maxfiylik", "summary": "Qasoskor baholashning oldini olish mexanizmi."},
            ],
        },
    }

    def get_onboarding_options_api_002(self) -> dict[str, Any]:
        """Canonical API-002: Nomzod, ish beruvchi, host va rasmiy xodim yo'llari (`CAP-002`).
        
        Strict Stage 2 Freelance Directive:
        Freelance persona is explicitly designated as PLANNED / Stage 2 extension point
        without operational logic in R1.
        """
        return {
            "contract_id": "API-002",
            "version": "1.0",
            "active_stage": 1,
            "options": [
                {
                    "persona": "CANDIDATE",
                    "title": "Nomzod (Ish izlovchi / Bitiruvchi)",
                    "is_active": True,
                    "stage": 1,
                    "status": "AVAILABLE",
                    "description": "Talabalar va mustaqil ish qidiruvchilar uchun tasdiqlangan bo'sh ish o'rinlari.",
                    "registration_path": "/api/v1/auth/register",
                    "required_fields": ["phone", "full_name", "date_of_birth"],
                    "capabilities": ["CAP-001", "CAP-002", "CAP-007", "CAP-012"],
                },
                {
                    "persona": "STUDENT",
                    "title": "Talaba (Akademik amaliyotchi)",
                    "is_active": True,
                    "stage": 1,
                    "status": "AVAILABLE",
                    "description": "Oliy o'quv yurtlari talabalari uchun uch tomonlama amaliyot va dars jadvaliga mos ishlar.",
                    "registration_path": "/api/v1/auth/register",
                    "required_fields": ["phone", "full_name", "institution_id", "student_id"],
                    "capabilities": ["CAP-001", "CAP-002", "CAP-003", "CAP-007", "CAP-018"],
                },
                {
                    "persona": "EMPLOYER",
                    "title": "Ish beruvchi (Kompaniya / Korxona)",
                    "is_active": True,
                    "stage": 1,
                    "status": "AVAILABLE",
                    "description": "Talabalar va bitiruvchilarni ishga qabul qiluvchi tashkilotlar uchun.",
                    "registration_path": "/api/v1/auth/register",
                    "required_fields": ["phone", "full_name", "tin", "legal_name"],
                    "capabilities": ["CAP-008", "CAP-009", "CAP-011", "CAP-015"],
                },
                {
                    "persona": "HOST_ORGANIZATION",
                    "title": "Amaliyot bazasi (Host tashkilot)",
                    "is_active": True,
                    "stage": 1,
                    "status": "AVAILABLE",
                    "description": "Talabalar amaliyotini qabul qiluvchi va mentor biriktiruvchi tashkilotlar.",
                    "registration_path": "/api/v1/auth/register",
                    "required_fields": ["phone", "full_name", "tin", "legal_name"],
                    "capabilities": ["CAP-015", "CAP-018", "CAP-021"],
                },
                {
                    "persona": "INSTITUTION",
                    "title": "Ta'lim muassasasi (OTM / Kollej)",
                    "is_active": True,
                    "stage": 1,
                    "status": "AVAILABLE",
                    "description": "Dekanat, amaliyot bo'limi boshliqlari va kafedra o'qituvchilari.",
                    "registration_path": "/api/v1/auth/register",
                    "required_fields": ["phone", "full_name", "tin", "edu_institution_code"],
                    "capabilities": ["CAP-018", "CAP-030"],
                },
                {
                    "persona": "FREELANCER",
                    "title": "Frilanser (Mustaqil mutaxassis)",
                    "is_active": False,
                    "stage": 2,
                    "status": "PLANNED",
                    "description": "2-bosqichda faollashtiriladigan mustaqil loyihalar va to'g'ridan-to'g'ri buyurtmalar xizmati.",
                    "note": "R1 bosqichida faollashtirilmagan; kelajakdagi 2-bosqich kengaytmasi uchun ajratilgan karkas.",
                    "capabilities": [],
                },
            ],
        }

    def get_public_services_api_011(self) -> dict[str, Any]:
        """Canonical API-011: Kimga, qanday shart, real xizmat chegarasi (`CAP-039`)."""
        return {
            "contract_id": "API-011",
            "currency": "UZS",
            "updated_at": "2026-11-11T00:00:00Z",
            "services": [
                {
                    "code": "ACADEMIC_INTERNSHIP",
                    "name_uz": "Uch tomonlama akademik amaliyot",
                    "target_audience": "Talabalar, OTMlar va Host tashkilotlar",
                    "is_active": True,
                    "stage": 1,
                    "description": "Raqamli kundaliklar, mentor baholashlari va kafedra tasdiqlari bilan ta'minlangan amaliyot dasturi.",
                    "conditions": ["Tasdiqlangan OTM buyrug'i", "Mentor biriktirilishi", "Kundalik hisoboti"],
                },
                {
                    "code": "PART_TIME_EMPLOYMENT",
                    "name_uz": "Moslashuvchan yarim stavkali ish",
                    "target_audience": "Talabalar va ish beruvchilar",
                    "is_active": True,
                    "stage": 1,
                    "description": "Dars jadvali bilan ziddiyatlarni algoritmik tekshirish (API-003) orqali xavfsiz bandlik.",
                    "conditions": ["Dars jadvali mosligi", "Ikki tomonlama ish boshlash tasdig'i"],
                },
                {
                    "code": "DOUBLE_BLIND_EVALUATION",
                    "name_uz": "Ikki tomonlama xolis baholash tizimi",
                    "target_audience": "Nomzodlar va ish beruvchilar",
                    "is_active": True,
                    "stage": 1,
                    "description": "Ikkala tomon ham baho bermaguncha maxfiy saqlanuvchi va qasos xavfini yo'qotuvchi tizim.",
                    "conditions": ["Ish yakunlangan bo'lishi", "14 kunlik kutish oynasi"],
                },
                {
                    "code": "FREELANCE_MARKETPLACE",
                    "name_uz": "Frilans buyurtmalar bozori",
                    "target_audience": "Mustaqil mutaxassislar va buyurtmachilar",
                    "is_active": False,
                    "stage": 2,
                    "description": "Kafolatlangan depozit (escrow) bilan mustaqil loyihalar va topshiriqlar xizmati.",
                    "conditions": ["2-bosqichda joriy qilinadi"],
                },
            ],
        }

    def get_public_prices_api_012(self) -> dict[str, Any]:
        """Canonical API-012: Taklif narxi, 30kun, aktivatsiya va refund qoidasi (`CAP-039`)."""
        from app.services.billing import TARIFF_CATALOG
        single_price = TARIFF_CATALOG.get("SINGLE_POST_30D", {}).get("price_uzs", 149000)
        org_price = TARIFF_CATALOG.get("ORG_PLAN_30D", {}).get("price_uzs", 599000)
        return {
            "contract_id": "API-012",
            "currency": "UZS",
            "pricing_model": "SUBSCRIPTION_AND_LISTING",
            "plans": [
                {
                    "tier": "PILOT_FREE",
                    "title": "Pilot sinov tarifi",
                    "plan_code": "PILOT_FREE",
                    "price_uzs": 0,
                    "duration_days": 30,
                    "description": "Akademik hamkorlar va akkreditatsiyalangan host tashkilotlar uchun dastlabki bepul e'lonlar.",
                    "opportunity_slots": 5,
                },
                {
                    "tier": "SINGLE_POST_30D",
                    "title": "Bitta e'lon uchun 30 kunlik tarif",
                    "plan_code": "SINGLE_POST_30D",
                    "price_uzs": single_price,
                    "duration_days": 30,
                    "description": "Bitta e'lonni 30 kun davomida faol saqlash va mos keluvchi nomzodlarni qidirish.",
                    "opportunity_slots": 1,
                },
                {
                    "tier": "ORG_PLAN_30D",
                    "title": "Tashkilot oylik korporativ tarifi",
                    "plan_code": "ORG_PLAN_30D",
                    "price_uzs": org_price,
                    "duration_days": 30,
                    "description": "Bir vaqtning o'zida 5 tagacha faol e'lonlarni boshqarish.",
                    "opportunity_slots": 5,
                },
            ],
            "activation_rules": {
                "speed": "INSTANT",
                "provider": "ONLINE_GATEWAY",
                "currency": "UZS",
            },
            "refund_policy": {
                "policy": "PRORATED_BEFORE_FIRST_APPLICATION",
                "full_refund_window_hours": 24,
                "description": "E'lon nashr qilinganidan keyin 24 soat ichida va birorta ariza tushmagan bo'lsa 100% qaytariladi. Ariza tushgandan keyin pul qaytarilmaydi.",
                "circuit_breaker_guarantee": True,
            },
        }

    def get_public_help_api_013(self, document: str) -> dict[str, Any]:
        """Canonical API-013: Faqat ma'lumot mazmuni; CMS matni alohida versiyalanadi (`CAP-039`)."""
        slug = str(document).strip().lower()
        doc = self.HELP_DOCUMENTS.get(slug)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"code": "DOCUMENT_NOT_FOUND", "message": f"Help document '{slug}' not found."},
            )
        return {
            "contract_id": "API-013",
            "slug": slug,
            "title": doc["title"],
            "version": doc["version"],
            "effective_date": doc["effective_date"],
            "content_markdown": doc["content_markdown"],
            "sections": doc["sections"],
        }

    def get_public_policies_api_014(self, document: str) -> dict[str, Any]:
        """Canonical API-014: Ochiq hujjat versiyasi, amal sanasi va aloqa (`CAP-039`)."""
        slug = str(document).strip().lower()
        doc = self.POLICIES.get(slug)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"code": "POLICY_NOT_FOUND", "message": f"Policy document '{slug}' not found."},
            )
        return {
            "contract_id": "API-014",
            "document": slug,
            "title": doc["title"],
            "version": doc["version"],
            "effective_date": doc["effective_date"],
            "contact_email": doc["contact_email"],
            "content_markdown": doc["content_markdown"],
            "clauses": doc["clauses"],
        }


discovery_and_catalog_service = DiscoveryAndCatalogService()
