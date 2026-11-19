# FB-200 Forensic Verification Report: Full Resume Builder, Direct PDF Upload, Employer & University Directories

- **Date**: 2026-11-15
- **Issue**: `#200`
- **Branch**: `feature/200-full-resume-and-portal-directories` -> `integration/r1-agent-collaboration`
- **Main Status**: `origin/main` strictly FROZEN at `764fb98496fa40857acb07844fd09fcafa99b7d6` (zero mutations)

---

## 1. Deliverables Summary

### Bosqich 1: Nomzod Portali — To‘liq Rezyume Quruvchi, Erishgan Yutuqlar, Qilingan Ishlar, Tillar va Sertifikat/CV Yuklash (`/nomzod`)
- **Backend Service**: `backend/app/services/candidate_resume_builder.py` (`API-026-RESUME-DETAILS` & `API-026-DIRECT-UPLOAD`)
  - `GET/PUT /api/v1/me/candidate/resume-details`: Manages structured `achievements`, `work_experiences`, `languages`, `education_details`, and `career_preferences` with automatic `completion_percent` calculation and SHA-256 audit logging (`CANDIDATE_RESUME_DETAILS_UPDATED`).
  - `POST /api/v1/me/candidate/files/upload`: Direct PDF upload for `CV`, `CERTIFICATE`, and `PORTFOLIO` with `pypdf` validation, EICAR/ClamAV malware rejection (`422 MALWARE_DETECTED_QUARANTINED`), MinIO storage, `flexbridge.files` registration (`CLEAN`), and automatic `cv_file_id` linking on `flexbridge.candidate_profiles`.
- **Enriched Export**: `backend/app/services/candidate_resume_export.py` (`API-026-RESUME-EXPORT`) includes all achievements, work experiences, languages, education details, and career preferences in exported JSON/PDF resumes.
- **Next.js 16 BFF & UI**: `/api/bff/candidate/resume-details`, `/api/bff/candidate/files/upload`, and Tab 3 `"FULL_RESUME"` + direct PDF file upload controls in `frontend/src/app/nomzod/page.tsx`.

### Bosqich 2: Korxona (Ish Beruvchi) Portali — Korxona Ma'lumotnomasini To‘ldirish (`/employer`)
- **Backend Service**: `backend/app/services/employer_directory.py` (`API-067-DIRECTORY`)
  - `GET/PUT /api/v1/organizations/{org}/directory-profile`: Manages corporate directory fields (`official_name`, `brand_name`, `tax_id`, `industry`, `region`, `legal_address`, `company_size`, `founded_year`, `website_url`, `hr_contact_name`, `hr_contact_phone`, `hr_contact_email`, `director_name`, `bank_name`, `bank_mfo`, `bank_account`, `about_company`, `internship_conditions`, `student_perks`) with `completion_percent` and `ORG_SCOPE_FORBIDDEN` (403) IDOR protection.
- **Next.js 16 BFF & UI**: `/api/bff/employer/organization/[org]/directory-profile` and interactive form in `frontend/src/app/employer/page.tsx` (`ORG_HUB`).

### Bosqich 3: Universitet Portali — OTM Ma'lumotnomasi, Fakultetlar/Yo‘nalishlar va Hamkorlik Shartnomalari (`/university`)
- **Backend Service**: `backend/app/services/university_directory.py` (`API-098-DIRECTORY` & `API-101-CREATE`)
  - `GET/PUT /api/v1/institutions/{inst}/directory-profile`: Manages OTM directory profile (`official_name`, `short_name`, `registry_code`, `institution_type`, `region`, `address`, `rector_name`, `career_center_head`, `contact_phone`, `contact_email`, `website_url`, `faculties`, `programs`, `annual_intern_quota`, `internship_policy_summary`) with `completion_percent` and `INSTITUTION_SCOPE_FORBIDDEN` (403) IDOR protection.
  - `POST /api/v1/institutions/{inst}/academic-agreements`: Creates versioned academic partnership agreements in `flexbridge.institution_agreements` + partner organization metadata.
- **Next.js 16 BFF & UI**: `/api/bff/university/institutions/[inst]/directory-profile`, `/api/bff/university/institutions/[inst]/agreements`, and interactive OTM directory & agreement creation form in `frontend/src/app/university/page.tsx` (`exports` tab).

---

## 2. Full-Scale Verification Results (Bosqich 4)

- **Dedicated 12-Phase Staging Suite (`scripts/test_full_resume_org_univ_directory_staging.py`)**: **12/12 PHASES PASSED 100% GREEN**
- **Master 29-Suite Staging Regression (`scripts/run_all_staging_tests.py`)**: **29/29 TEST SUITES PASSED 100% GREEN in 69.43s (0 regressions)**
