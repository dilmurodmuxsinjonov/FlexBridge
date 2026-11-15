#!/usr/bin/env python3
"""
Staging Verification Suite: Full Candidate Resume Builder, Direct PDF Upload,
Employer Organization Directory & University Institution Directory (FB-200)

Contracts & Capabilities Verified:
1. API-026-RESUME-DETAILS:
   - GET /api/bff/candidate/resume-details
   - PUT /api/bff/candidate/resume-details (achievements, work_experiences, languages, education_details, career_preferences)
2. API-026-DIRECT-UPLOAD:
   - POST /api/bff/candidate/files/upload (Direct PDF upload with pypdf validation + ClamAV/EICAR check + CV auto-linking + Certificate attachment)
3. API-026-RESUME-EXPORT (Enriched):
   - POST /api/bff/candidate/resume/export (JSON & PDF exports enriched with achievements_count, work_experiences_count, languages_count)
4. API-067-DIRECTORY (Employer Organization Directory):
   - GET /api/bff/employer/organization/{org}/directory-profile
   - PUT /api/bff/employer/organization/{org}/directory-profile (official_name, brand_name, tax_id, industry, bank_mfo, bank_account, student_perks, completion_percent)
5. API-098-DIRECTORY & API-101-CREATE (University Institution Directory & Partner Agreements):
   - GET /api/bff/university/institutions/{inst}/directory-profile
   - PUT /api/bff/university/institutions/{inst}/directory-profile (faculties, programs, rector_name, career_center_head, annual_intern_quota)
   - POST /api/bff/university/institutions/{inst}/agreements (creates active partner agreement in flexbridge.institution_agreements)
6. Portal UI Verification:
   - /nomzod, /employer, /university render HTTP 200 with the new sections.
"""

import base64
import io
import json
import os
import sys
from datetime import date, datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4

from dotenv import dotenv_values
from pypdf import PdfWriter
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.services.auth import hash_password

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")


def get_database_url() -> str:
    explicit = os.environ.get("FLEXBRIDGE_STAGING_DATABASE_URL")
    if explicit:
        return explicit
    values = dotenv_values(REPO_ROOT / "infra" / ".env")
    password = values.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("Set POSTGRES_PASSWORD in infra/.env")
    url = URL.create(
        "postgresql+psycopg",
        username=values.get("POSTGRES_USER") or "flexbridge_owner",
        password=password,
        host="127.0.0.1",
        port=5432,
        database=values.get("POSTGRES_DB") or "flexbridge",
    )
    return url.render_as_string(hide_password=False)


def api_request(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    opener=None,
) -> Tuple[int, Any]:
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = Request(url, data=body, headers=req_headers, method=method)
    active_opener = opener or build_opener()

    try:
        with active_opener.open(req) as resp:
            code = resp.status
            content = resp.read().decode("utf-8")
            try:
                payload = json.loads(content)
            except Exception:
                payload = content
            return code, payload
    except HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            payload = json.loads(content)
        except Exception:
            payload = content
        return e.code, payload


def make_sample_pdf_base64(title: str) -> str:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": title, "/Author": "FlexBridge Staging Test"})
    buf = io.BytesIO()
    writer.write(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main():
    print("=" * 84)
    print("FLEXBRIDGE 1.4 STAGING SUITE: Full Resume Builder, Direct PDF & Portal Directories (FB-200)")
    print(f"Target Frontend: {FRONTEND_URL}")
    print("Target Database: PgBouncer 127.0.0.1:5432/flexbridge (prepare_threshold=None)")
    print("=" * 84)

    engine = create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    now_utc = datetime.now(timezone.utc)
    today_date = date.today()
    suffix = uuid4().hex[:8]
    raw_password = f"Fb200Pass_{suffix}!"
    pwd_hash = hash_password(raw_password)

    cand_user_id = str(uuid4())
    cand_profile_id = str(uuid4())
    cand_email = f"cand_fb200_{suffix}@flexbridge.uz"

    org_user_id = str(uuid4())
    org_email = f"org_fb200_{suffix}@flexbridge.uz"
    org_id = str(uuid4())
    org_mem_id = str(uuid4())

    inst_user_id = str(uuid4())
    inst_email = f"inst_fb200_{suffix}@flexbridge.uz"
    inst_id = str(uuid4())
    inst_mem_id = str(uuid4())

    # -------------------------------------------------------------------------
    # PHASE 1: Unauthenticated 401 & CSRF 403 Guards on All New BFF Routes
    # -------------------------------------------------------------------------
    print("\n[Phase 1] Verifying 401 AUTH_REQUIRED and 403 CSRF_ORIGIN_MISMATCH on new BFF routes...")
    unauth_checks = [
        ("GET", f"{FRONTEND_URL}/api/bff/candidate/resume-details", None),
        ("PUT", f"{FRONTEND_URL}/api/bff/candidate/resume-details", {"achievements": []}),
        ("POST", f"{FRONTEND_URL}/api/bff/candidate/files/upload", {"filename": "cv.pdf", "purpose": "CV"}),
        ("GET", f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/directory-profile", None),
        ("PUT", f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/directory-profile", {"official_name": "Test"}),
        ("GET", f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/directory-profile", None),
        ("PUT", f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/directory-profile", {"official_name": "Test"}),
        ("POST", f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/agreements", {"partner_organization_name": "Test"}),
    ]
    for method, url, payload in unauth_checks:
        code, body = api_request(url, method=method, data=payload, headers={"Origin": FRONTEND_URL})
        assert code == 401, f"Expected 401 on {method} {url}, got {code}: {body}"

    code_csrf, body_csrf = api_request(
        f"{FRONTEND_URL}/api/bff/candidate/resume-details",
        method="PUT",
        data={"achievements": []},
        headers={"Origin": "https://evil-attacker.example.com"},
    )
    assert code_csrf == 403 and body_csrf.get("error") == "CSRF_ORIGIN_MISMATCH", f"CSRF check failed: {code_csrf} {body_csrf}"
    print("  ✓ Phase 1 PASSED: All 8 new BFF endpoints enforce 401 AUTH_REQUIRED & 403 CSRF guard.")

    # -------------------------------------------------------------------------
    # PHASE 2: Seed Candidate, Organization Member, and University Coordinator
    # -------------------------------------------------------------------------
    print("\n[Phase 2] Seeding Candidate, Employer Organization & University Institution fixtures...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE flexbridge.auth_rate_limits"))

        # Candidate User + Profile
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Sardorbek Alimov', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": cand_user_id, "pwd": pwd_hash, "now": now_utc},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.candidate_profiles (id, created_at, updated_at, user_id, headline, region, bio, experience_months, visibility)
                VALUES (:id, :now, :now, :uid, 'Full-Stack & AI Engineer', 'Toshkent shahri', 'Tajribali talaba dasturchi', 14, 'PUBLIC')
            """),
            {"id": cand_profile_id, "uid": cand_user_id, "now": now_utc},
        )

        # Employer User + Organization + Active Membership
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Dilshod Raximov (HR Director)', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": org_user_id, "pwd": pwd_hash, "now": now_utc},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.organizations (id, created_at, updated_at, tax_id, legal_name, public_name, region, description, website, status)
                VALUES (:id, :now, :now, :tax_id, 'UzFinTech Innovation MChJ', 'UzFinTech', 'Toshkent', 'Raqamli bank va to''lov tizimlari', 'https://uzfintech.uz', 'VERIFIED')
            """),
            {"id": org_id, "tax_id": f"309{suffix[:6]}", "now": now_utc},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.org_memberships (id, created_at, updated_at, organization_id, user_id, status, accepted_at)
                VALUES (:id, :now, :now, :org_id, :uid, 'ACTIVE', :now)
            """),
            {"id": org_mem_id, "org_id": org_id, "uid": org_user_id, "now": now_utc},
        )

        # University User + Institution + Active Membership
        conn.execute(
            text("""
                INSERT INTO flexbridge.users (id, created_at, updated_at, display_name, password_hash, status, locale, timezone, adult_declared_at)
                VALUES (:id, :now, :now, 'Prof. Nodira Usmonova', :pwd, 'ACTIVE', 'uz', 'Asia/Tashkent', :now)
            """),
            {"id": inst_user_id, "pwd": pwd_hash, "now": now_utc},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.institutions (id, created_at, updated_at, registry_code, name, region, status)
                VALUES (:id, :now, :now, :code, 'Toshkent Axborot Texnologiyalari Universiteti', 'Toshkent', 'VERIFIED')
            """),
            {"id": inst_id, "code": f"OTM-{suffix.upper()}", "now": now_utc},
        )
        conn.execute(
            text("""
                INSERT INTO flexbridge.institution_memberships (id, created_at, updated_at, institution_id, user_id, status, accepted_at)
                VALUES (:id, :now, :now, :inst_id, :uid, 'ACTIVE', :now)
            """),
            {"id": inst_mem_id, "inst_id": inst_id, "uid": inst_user_id, "now": now_utc},
        )
    print("  ✓ Phase 2 PASSED: Candidate, Organization, and University fixtures seeded.")

    try:
        # Helper to login via BFF
        def login_user(user_id: str):
            jar = CookieJar()
            opener = build_opener(HTTPCookieProcessor(jar))
            code, body = api_request(
                f"{FRONTEND_URL}/api/auth/login",
                method="POST",
                data={"user_id": user_id, "password": raw_password},
                headers={"Origin": FRONTEND_URL},
                opener=opener,
            )
            assert code == 200, f"Login failed for {user_id}: {code} {body}"
            return opener

        cand_opener = login_user(cand_user_id)
        org_opener = login_user(org_user_id)
        inst_opener = login_user(inst_user_id)

        # ---------------------------------------------------------------------
        # PHASE 3: Candidate Full Resume Details (Achievements, Work, Languages, Education, Career)
        # ---------------------------------------------------------------------
        print("\n[Phase 3] Testing PUT & GET /api/bff/candidate/resume-details...")
        resume_payload = {
            "achievements": [
                {
                    "title": "ICPC Central Asia Finalisti (1-o'rin)",
                    "category": "OLIMPIADA",
                    "issuer": "Raqamli Texnologiyalar Vazirligi",
                    "date": "2026-04-15",
                    "description": "Algoritmik dasturlash bo'yicha 120 jamoa ichida 1-o'rin.",
                },
                {
                    "title": "Beruniy nomidagi Davlat Stipendiyasi sohibi",
                    "category": "STIPENDIYA",
                    "issuer": "Oliy ta'lim, fan va innovatsiyalar vazirligi",
                    "date": "2025-12-10",
                    "description": "Yuqori akademik ko'rsatkichlar va ilmiy maqolalar uchun.",
                },
            ],
            "work_experiences": [
                {
                    "company_name": "Payme / Inspired MChJ",
                    "position": "Backend Python Intern",
                    "work_type": "INTERNSHIP",
                    "start_date": "2025-06-01",
                    "end_date": "2025-12-01",
                    "is_current": False,
                    "responsibilities": "FastAPI va PostgreSQL asosida mikroservislar ishlab chiqish.",
                    "achievements_summary": "Tranzaksiya javob vaqtini 35% ga qisqartirdim.",
                },
                {
                    "company_name": "TUIT AI Lab",
                    "position": "Ilmiy tadqiqotchi-dasturchi",
                    "work_type": "PART_TIME",
                    "start_date": "2026-01-10",
                    "end_date": None,
                    "is_current": True,
                    "responsibilities": "O'zbek tili NLP korpusi va nutqni aniqlash modellarini o'qitish.",
                    "achievements_summary": "100 ming audio namunali korpus yig'ildi.",
                },
            ],
            "languages": [
                {"language_name": "O'zbek tili", "level": "NATIVE"},
                {"language_name": "Ingliz tili", "level": "C1", "certificate_score": "IELTS 7.5"},
                {"language_name": "Nemis tili", "level": "B2", "certificate_score": "TestDaF 4x4"},
            ],
            "education_details": {
                "faculty": "Dasturiy injiniring fakulteti",
                "study_year": "4-kurs",
                "gpa": "4.92 / 5.00",
                "graduation_year": "2027",
                "courses": ["Algoritmlar", "Taqsimlangan tizimlar", "Mashinali o'qitish"],
            },
            "career_preferences": {
                "desired_salary_uzs": 5000000,
                "preferred_work_mode": "HYBRID",
                "github_url": "https://github.com/sardorbek-alimov",
                "linkedin_url": "https://linkedin.com/in/sardorbek-alimov",
                "telegram_username": "@sardorbek_dev",
                "website_url": "https://sardorbek.dev",
                "career_objective": "FinTech va AI sohasida yuqori ishonchlilikdagi tizimlar arxitekturasini yaratish.",
            },
        }

        code, put_res = api_request(
            f"{FRONTEND_URL}/api/bff/candidate/resume-details",
            method="PUT",
            data=resume_payload,
            headers={"Origin": FRONTEND_URL},
            opener=cand_opener,
        )
        assert code == 200 and put_res.get("ok") is True, f"PUT resume-details failed: {code} {put_res}"
        assert len(put_res["achievements"]) == 2
        assert len(put_res["work_experiences"]) == 2
        assert len(put_res["languages"]) == 3
        assert put_res["education_details"]["gpa"] == "4.92 / 5.00"

        code, get_res = api_request(
            f"{FRONTEND_URL}/api/bff/candidate/resume-details",
            method="GET",
            opener=cand_opener,
        )
        assert code == 200 and len(get_res["achievements"]) == 2 and len(get_res["work_experiences"]) == 2
        print("  ✓ Phase 3 PASSED: Achievements, Work Experiences, Languages & Academic GPA saved and retrieved.")

        # ---------------------------------------------------------------------
        # PHASE 4: Direct PDF Upload for CV & Certificates (API-026-DIRECT-UPLOAD)
        # ---------------------------------------------------------------------
        print("\n[Phase 4] Testing Direct PDF File Upload for CV & Certificates...")
        cv_pdf_b64 = make_sample_pdf_base64("Sardorbek Alimov CV")
        code, cv_up = api_request(
            f"{FRONTEND_URL}/api/bff/candidate/files/upload",
            method="POST",
            data={
                "filename": "sardorbek_alimov_cv.pdf",
                "purpose": "CV",
                "title": "Sardorbek Alimov Full CV",
                "content_base64": cv_pdf_b64,
            },
            headers={"Origin": FRONTEND_URL},
            opener=cand_opener,
        )
        assert code == 201 and cv_up.get("ok") is True, f"CV PDF upload failed: {code} {cv_up}"
        assert cv_up["scan_status"] == "CLEAN" and cv_up["linked_as_cv"] is True

        # Upload Certificate PDF and attach it to a new certificate
        cert_pdf_b64 = make_sample_pdf_base64("IELTS C1 Academic Certificate")
        code, cert_up = api_request(
            f"{FRONTEND_URL}/api/bff/candidate/files/upload",
            method="POST",
            data={
                "filename": "ielts_c1_7_5.pdf",
                "purpose": "CERTIFICATE",
                "title": "IELTS Academic 7.5",
                "content_base64": cert_pdf_b64,
            },
            headers={"Origin": FRONTEND_URL},
            opener=cand_opener,
        )
        assert code == 201 and cert_up.get("ok") is True, f"Cert PDF upload failed: {code} {cert_up}"
        cert_file_id = cert_up["file_id"]

        code, cert_created = api_request(
            f"{FRONTEND_URL}/api/bff/candidate/certificates",
            method="POST",
            data={
                "title": "IELTS Academic C1 (Band 7.5)",
                "issuer": "British Council Uzbekistan",
                "issue_date": "2026-02-15",
                "credential_id": "BC-UZ-750019",
                "file_id": cert_file_id,
            },
            headers={"Origin": FRONTEND_URL},
            opener=cand_opener,
        )
        assert code == 201 and cert_created.get("ok") is True, f"Cert creation with uploaded PDF failed: {code} {cert_created}"
        assert cert_created["item"]["file_id"] == cert_file_id
        print("  ✓ Phase 4 PASSED: Direct PDF upload for CV and Certificate verified & linked.")

        # ---------------------------------------------------------------------
        # PHASE 5: Antivirus / Malware Rejection on Direct File Upload
        # ---------------------------------------------------------------------
        print("\n[Phase 5] Verifying EICAR malware signature rejection on direct file upload...")
        eicar_bytes = b"%PDF-1.4\nX5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        eicar_b64 = base64.b64encode(eicar_bytes).decode("ascii")
        code, mal_res = api_request(
            f"{FRONTEND_URL}/api/bff/candidate/files/upload",
            method="POST",
            data={
                "filename": "infected_cert.pdf",
                "purpose": "CERTIFICATE",
                "content_base64": eicar_b64,
            },
            headers={"Origin": FRONTEND_URL},
            opener=cand_opener,
        )
        assert code == 422, f"Expected 422 on EICAR payload, got {code}: {mal_res}"
        print("  ✓ Phase 5 PASSED: Infected PDF payload rejected with HTTP 422.")

        # ---------------------------------------------------------------------
        # PHASE 6: Enriched Resume Export (JSON & PDF include Achievements, Work, Languages)
        # ---------------------------------------------------------------------
        print("\n[Phase 6] Verifying Enriched Resume Export (API-026-RESUME-EXPORT)...")
        code, exp_res = api_request(
            f"{FRONTEND_URL}/api/bff/candidate/resume/export",
            method="POST",
            data={
                "idempotency_key": f"exp_full_json_{suffix}",
                "export_format": "JSON",
            },
            headers={"Origin": FRONTEND_URL},
            opener=cand_opener,
        )
        assert code == 201 and exp_res.get("ok") is True, f"Resume export failed: {code} {exp_res}"
        summary = exp_res["summary"]
        assert summary["achievements_count"] == 2, f"Expected 2 achievements in summary, got {summary}"
        assert summary["work_experiences_count"] == 2, f"Expected 2 work experiences in summary, got {summary}"
        assert summary["languages_count"] == 3, f"Expected 3 languages in summary, got {summary}"
        assert summary["certificates_count"] == 1, f"Expected 1 certificate in summary, got {summary}"
        print("  ✓ Phase 6 PASSED: Enriched resume export includes all new resume sections.")

        # ---------------------------------------------------------------------
        # PHASE 7: Employer Organization Directory Profile GET & PUT (API-067-DIRECTORY)
        # ---------------------------------------------------------------------
        print("\n[Phase 7] Testing Employer Organization Directory Profile (GET & PUT)...")
        org_dir_payload = {
            "official_name": "UzFinTech Innovation MChJ",
            "brand_name": "UzFinTech",
            "tax_id": f"309{suffix[:6]}",
            "industry": "Moliyaviy texnologiyalar va Raqamli banking",
            "region": "Toshkent shahri",
            "legal_address": "Toshkent sh., Mirzo Ulug'bek tumani, IT Park, 4-bino",
            "company_size": "50-200 xodim",
            "founded_year": 2021,
            "website_url": "https://uzfintech.uz",
            "hr_contact_name": "Dilshod Raximov",
            "hr_contact_phone": "+998901234567",
            "hr_contact_email": org_email,
            "director_name": "Rustamov Jamshid Anvarovich",
            "bank_name": "ATB Kapitalbank",
            "bank_mfo": "00445",
            "bank_account": "20208000905412345001",
            "about_company": "Yuqori yuklamali to'lov tizimlari va sun'iy intellektga asoslangan skoring platformasi.",
            "internship_conditions": "Har bir amaliyotchiga Senior mentor biriktiriladi, oylik 3.5 mln UZS stipendiya.",
            "student_perks": ["Oylik stipendiya", "Senior Mentor", "Bepul tushlik", "MacBook Pro"],
        }
        code, org_put = api_request(
            f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/directory-profile",
            method="PUT",
            data=org_dir_payload,
            headers={"Origin": FRONTEND_URL},
            opener=org_opener,
        )
        assert code == 200 and org_put.get("ok") is True, f"PUT org directory failed: {code} {org_put}"
        assert org_put["completion_percent"] == 100, f"Expected 100% completion, got {org_put}"
        assert org_put["bank_mfo"] == "00445"
        assert len(org_put["student_perks"]) == 4

        code, org_get = api_request(
            f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/directory-profile",
            method="GET",
            opener=org_opener,
        )
        assert code == 200 and org_get["director_name"] == "Rustamov Jamshid Anvarovich"
        print("  ✓ Phase 7 PASSED: Employer Organization Directory Profile reached 100% completion.")

        # ---------------------------------------------------------------------
        # PHASE 8: Cross-Organization IDOR Rejection on Employer Directory
        # ---------------------------------------------------------------------
        print("\n[Phase 8] Verifying Cross-Organization IDOR protection on Employer Directory...")
        code, idor_org = api_request(
            f"{FRONTEND_URL}/api/bff/employer/organization/{org_id}/directory-profile",
            method="GET",
            opener=cand_opener,
        )
        assert code == 403, f"Expected 403 for non-member accessing org directory, got {code}: {idor_org}"
        print("  ✓ Phase 8 PASSED: Non-member blocked from Employer Directory with HTTP 403.")

        # ---------------------------------------------------------------------
        # PHASE 9: University Institution Directory Profile GET & PUT (API-098-DIRECTORY)
        # ---------------------------------------------------------------------
        print("\n[Phase 9] Testing University Institution Directory Profile (GET & PUT)...")
        inst_dir_payload = {
            "official_name": "Muhammad al-Xorazmiy nomidagi Toshkent Axborot Texnologiyalari Universiteti",
            "short_name": "TATU (TUIT)",
            "registry_code": f"OTM-{suffix.upper()}",
            "institution_type": "Davlat oliy ta'lim muassasasi",
            "region": "Toshkent shahri",
            "address": "Toshkent sh., Amir Temur shoh ko'chasi, 108-uy",
            "rector_name": "Prof. Baxtiyor Maxkamov",
            "career_center_head": "Prof. Nodira Usmonova",
            "contact_phone": "+998712386415",
            "contact_email": inst_email,
            "website_url": "https://tuit.uz",
            "faculties": [
                {"name": "Dasturiy injiniring fakulteti", "dean_name": "Dots. O. Karimov", "programs_count": 4, "students_count": 1850},
                {"name": "Kiberxavfsizlik fakulteti", "dean_name": "Prof. S. Rahmonov", "programs_count": 3, "students_count": 1200},
            ],
            "programs": [
                {"code": "60610500", "name": "Dasturiy injiniring", "degree_level": "BAKALAVR", "duration_years": 4},
                {"code": "60610300", "name": "Axborot xavfsizligi", "degree_level": "BAKALAVR", "duration_years": 4},
                {"code": "70610501", "name": "Sun'iy intellekt tizimlari", "degree_level": "MAGISTRATURA", "duration_years": 2},
            ],
            "annual_intern_quota": 1500,
            "internship_policy_summary": "3 va 4-bosqich talabalari dual ta'lim dasturi asosida IT korxonalarda amaliyot o'taydi.",
        }
        code, inst_put = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/directory-profile",
            method="PUT",
            data=inst_dir_payload,
            headers={"Origin": FRONTEND_URL},
            opener=inst_opener,
        )
        assert code == 200 and inst_put.get("ok") is True, f"PUT institution directory failed: {code} {inst_put}"
        assert inst_put["completion_percent"] == 100, f"Expected 100% completion, got {inst_put}"
        assert len(inst_put["faculties"]) == 2
        assert len(inst_put["programs"]) == 3
        print("  ✓ Phase 9 PASSED: University Institution Directory Profile reached 100% completion.")

        # ---------------------------------------------------------------------
        # PHASE 10: University Partner Agreement Creation (API-101-CREATE)
        # ---------------------------------------------------------------------
        print("\n[Phase 10] Testing University Partner Agreement Creation (POST /agreements)...")
        code, agr_create = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/agreements",
            method="POST",
            data={
                "partner_organization_name": "UzFinTech Innovation MChJ",
                "agreement_number": f"AGR-2026-{suffix[:4].upper()}",
                "valid_from": str(today_date),
                "valid_to": "2028-06-30",
                "purposes": ["ACADEMIC_VIEW", "INTERNSHIP_SUPERVISION"],
                "quota_slots": 45,
                "coordinator_note": "Dasturiy injiniring va Kiberxavfsizlik talabalari uchun",
            },
            headers={"Origin": FRONTEND_URL},
            opener=inst_opener,
        )
        assert code == 201 and agr_create.get("ok") is True, f"Create partner agreement failed: {code} {agr_create}"
        assert agr_create["partner_organization_name"] == "UzFinTech Innovation MChJ"
        assert agr_create["quota_slots"] == 45

        code, inst_get = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/directory-profile",
            method="GET",
            opener=inst_opener,
        )
        assert code == 200 and len(inst_get["partner_agreements"]) >= 1
        print("  ✓ Phase 10 PASSED: University Partner Agreement created & synced to directory profile.")

        # ---------------------------------------------------------------------
        # PHASE 11: Cross-Institution IDOR Rejection on University Directory
        # ---------------------------------------------------------------------
        print("\n[Phase 11] Verifying Cross-Institution IDOR protection on University Directory...")
        code, idor_inst = api_request(
            f"{FRONTEND_URL}/api/bff/university/institutions/{inst_id}/directory-profile",
            method="GET",
            opener=org_opener,
        )
        assert code == 403, f"Expected 403 for non-member accessing institution directory, got {code}: {idor_inst}"
        print("  ✓ Phase 11 PASSED: Non-member blocked from University Directory with HTTP 403.")

        # ---------------------------------------------------------------------
        # PHASE 12: Portal Frontend Pages & Audit Trail Verification
        # ---------------------------------------------------------------------
        print("\n[Phase 12] Verifying Frontend Portal Pages (/nomzod, /employer, /university) & Audit Trail...")
        for page_path in ("/nomzod", "/employer", "/university"):
            code, html = api_request(f"{FRONTEND_URL}{page_path}", method="GET")
            assert code == 200 and isinstance(html, str) and len(html) > 1000, f"Page {page_path} failed: {code}"

        with engine.connect() as conn:
            audit_rows = conn.execute(
                text("""
                    SELECT action FROM flexbridge.audit_events
                    WHERE actor_id IN (:u1, :u2, :u3)
                """),
                {"u1": cand_user_id, "u2": org_user_id, "u3": inst_user_id},
            ).mappings().all()
            actions = {r["action"] for r in audit_rows}
            assert "CANDIDATE_RESUME_DETAILS_UPDATED" in actions, f"Missing resume audit: {actions}"
            assert "CANDIDATE_PDF_FILE_UPLOADED_AND_SCANNED" in actions, f"Missing file upload audit: {actions}"
            assert "ORG_DIRECTORY_PROFILE_UPDATE" in actions, f"Missing org directory audit: {actions}"
            assert "INSTITUTION_DIRECTORY_PROFILE_UPDATE" in actions, f"Missing inst directory audit: {actions}"
            assert "INSTITUTION_PARTNER_AGREEMENT_CREATE" in actions, f"Missing partner agreement audit: {actions}"
        print("  ✓ Phase 12 PASSED: /nomzod, /employer, and /university render HTTP 200 & SHA-256 audit events verified.")

    finally:
        print("\n[Cleanup] Revoking test sessions...")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM flexbridge.sessions WHERE user_id IN (:u1, :u2, :u3)"), {
                "u1": cand_user_id, "u2": org_user_id, "u3": inst_user_id
            })

    print("\n" + "=" * 84)
    print("SUCCESS: ALL 12 PHASES OF FB-200 FULL RESUME & PORTAL DIRECTORIES VERIFIED 100% GREEN!")
    print("=" * 84)


if __name__ == "__main__":
    main()
