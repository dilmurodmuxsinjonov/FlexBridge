"""Candidate full resume builder: achievements, work experiences, languages, career preferences & direct PDF file upload (API-026 / CAP-002)."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.services import pdf_intake
from app.api.dependencies import ActorContext, candidate_id_for
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import (
    files_table,
    load_domain_record,
    now,
    save_domain_record,
    table,
    transaction,
)
from app.services.auth import AuthError
from app.services.authority import account_authority

audit = AppendOnlyAuditStore()

RESUME_DETAILS_NAMESPACE = "candidate_resume_details"


def _bounded_int(value: Any, low: int, high: int) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return max(low, min(high, number))

ALLOWED_ACHIEVEMENT_CATEGORIES = {
    "OLYMPIAD",
    "SCHOLARSHIP",
    "HACKATHON",
    "AWARD",
    "PUBLICATION",
    "COMPETITION",
    "OTHER",
}

ALLOWED_WORK_TYPES = {
    "INTERNSHIP",
    "PART_TIME",
    "FREELANCE",
    "FULL_TIME",
    "PROJECT",
    "VOLUNTEER",
}

ALLOWED_LANGUAGE_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2", "NATIVE"}
ALLOWED_WORK_MODES = {"ONSITE", "REMOTE", "HYBRID", "FLEXIBLE"}


def _default_resume_details(cand_id: str) -> dict[str, Any]:
    return {
        "candidate_id": cand_id,
        "achievements": [],
        "work_experiences": [],
        "languages": [],
        "education_details": {
            "faculty": "",
            "study_year": "",
            "gpa": "",
            "graduation_year": "",
            "courses": [],
        },
        "career_preferences": {
            "desired_salary_uzs": None,
            "preferred_work_mode": "FLEXIBLE",
            "github_url": "",
            "linkedin_url": "",
            "telegram_username": "",
            "website_url": "",
            "career_objective": "",
        },
        "updated_at": None,
    }


class CandidateResumeBuilderService:
    def get_resume_details(self, actor: ActorContext) -> dict[str, Any]:
        with transaction() as conn:
            cand_id = str(candidate_id_for(actor))
            account_authority(conn, actor)

            stored = load_domain_record(RESUME_DETAILS_NAMESPACE, cand_id)
            base = _default_resume_details(cand_id)
            if isinstance(stored, dict):
                base["achievements"] = stored.get("achievements") or []
                base["work_experiences"] = stored.get("work_experiences") or []
                base["languages"] = stored.get("languages") or []
                if isinstance(stored.get("education_details"), dict):
                    base["education_details"].update(stored["education_details"])
                if isinstance(stored.get("career_preferences"), dict):
                    base["career_preferences"].update(stored["career_preferences"])
                base["updated_at"] = stored.get("updated_at")

            return {
                "ok": True,
                "contract_id": "API-026-RESUME-DETAILS",
                **base,
            }

    def update_resume_details(self, actor: ActorContext, payload: dict[str, Any]) -> dict[str, Any]:
        with transaction() as conn:
            cand_id = str(candidate_id_for(actor))
            account_authority(conn, actor)

            existing = load_domain_record(RESUME_DETAILS_NAMESPACE, cand_id)
            state = _default_resume_details(cand_id)
            if isinstance(existing, dict):
                state.update(existing)

            # 1. Validate & normalize achievements (Erishgan yutuqlar)
            if "achievements" in payload:
                raw_ach = payload["achievements"]
                if not isinstance(raw_ach, list) or len(raw_ach) > 50:
                    raise AuthError("INVALID_ACHIEVEMENTS", "Achievements must be a list of at most 50 items", 422)
                normalized_ach = []
                for item in raw_ach:
                    if not isinstance(item, dict):
                        raise AuthError("INVALID_ACHIEVEMENT_ITEM", "Each achievement must be an object", 422)
                    title = str(item.get("title") or "").strip()
                    if not 2 <= len(title) <= 200:
                        raise AuthError("INVALID_ACHIEVEMENT_TITLE", "Achievement title must be 2-200 chars", 422)
                    issuer = str(item.get("issuer") or "").strip()
                    if not 2 <= len(issuer) <= 200:
                        raise AuthError("INVALID_ACHIEVEMENT_ISSUER", "Achievement issuer must be 2-200 chars", 422)
                    category = str(item.get("category") or "AWARD").upper().strip()
                    if category not in ALLOWED_ACHIEVEMENT_CATEGORIES:
                        category = "AWARD"
                    normalized_ach.append(
                        {
                            "id": str(item.get("id") or uuid4()),
                            "title": title,
                            "issuer": issuer,
                            "date": str(item.get("date") or "").strip() or None,
                            "category": category,
                            "description": str(item.get("description") or "").strip()[:2000],
                            "url": str(item.get("url") or "").strip()[:500] or None,
                        }
                    )
                state["achievements"] = normalized_ach

            # 2. Validate & normalize work_experiences (Qilingan ishlar va tajriba)
            if "work_experiences" in payload:
                raw_work = payload["work_experiences"]
                if not isinstance(raw_work, list) or len(raw_work) > 50:
                    raise AuthError(
                        "INVALID_WORK_EXPERIENCES", "Work experiences must be a list of at most 50 items", 422
                    )
                normalized_work = []
                for item in raw_work:
                    if not isinstance(item, dict):
                        raise AuthError("INVALID_WORK_ITEM", "Each work experience must be an object", 422)
                    company_name = str(item.get("company_name") or "").strip()
                    if not 2 <= len(company_name) <= 200:
                        raise AuthError("INVALID_COMPANY_NAME", "Company name must be 2-200 chars", 422)
                    position = str(item.get("position") or "").strip()
                    if not 2 <= len(position) <= 200:
                        raise AuthError("INVALID_POSITION", "Position must be 2-200 chars", 422)
                    work_type = str(item.get("work_type") or "INTERNSHIP").upper().strip()
                    if work_type not in ALLOWED_WORK_TYPES:
                        work_type = "INTERNSHIP"
                    start_date = str(item.get("start_date") or "").strip() or None
                    end_date = str(item.get("end_date") or "").strip() or None
                    is_current = bool(item.get("is_current", False))
                    if start_date and end_date and not is_current and end_date < start_date:
                        raise AuthError("INVALID_WORK_DATE_RANGE", "End date cannot be before start date", 422)
                    normalized_work.append(
                        {
                            "id": str(item.get("id") or uuid4()),
                            "company_name": company_name,
                            "position": position,
                            "work_type": work_type,
                            "start_date": start_date,
                            "end_date": None if is_current else end_date,
                            "is_current": is_current,
                            "responsibilities": str(item.get("responsibilities") or "").strip()[:3000],
                            "achievements_summary": str(item.get("achievements_summary") or "").strip()[:2000],
                            "location": str(item.get("location") or "").strip()[:120],
                            "technologies": [str(v).strip()[:40] for v in (item.get("technologies") or []) if isinstance(v, str) and str(v).strip()][:20],
                        }
                    )
                state["work_experiences"] = normalized_work

            # 3. Validate & normalize languages (Xorijiy tillar)
            if "languages" in payload:
                raw_langs = payload["languages"]
                if not isinstance(raw_langs, list) or len(raw_langs) > 25:
                    raise AuthError("INVALID_LANGUAGES", "Languages must be a list of at most 25 items", 422)
                normalized_langs = []
                for item in raw_langs:
                    if not isinstance(item, dict):
                        raise AuthError("INVALID_LANGUAGE_ITEM", "Each language item must be an object", 422)
                    lang_name = str(item.get("language_name") or "").strip()
                    if not 2 <= len(lang_name) <= 100:
                        raise AuthError("INVALID_LANGUAGE_NAME", "Language name must be 2-100 chars", 422)
                    level = str(item.get("level") or "B2").upper().strip()
                    if level not in ALLOWED_LANGUAGE_LEVELS:
                        raise AuthError("INVALID_LANGUAGE_LEVEL", f"Level must be one of {sorted(ALLOWED_LANGUAGE_LEVELS)}", 422)
                    normalized_langs.append(
                        {
                            "id": str(item.get("id") or uuid4()),
                            "language_name": lang_name,
                            "level": level,
                            "certificate_score": str(item.get("certificate_score") or "").strip()[:100] or None,
                        }
                    )
                state["languages"] = normalized_langs

            # 4. Education details
            if "education_details" in payload and isinstance(payload["education_details"], dict):
                ed = payload["education_details"]
                courses = ed.get("courses")
                if not isinstance(courses, list):
                    courses = []
                state["education_details"] = {
                    "faculty": str(ed.get("faculty") or "").strip()[:200],
                    "study_year": str(ed.get("study_year") or "").strip()[:50],
                    "gpa": str(ed.get("gpa") or "").strip()[:20],
                    "graduation_year": str(ed.get("graduation_year") or "").strip()[:10],
                    "courses": [str(c).strip()[:150] for c in courses if str(c).strip()][:30],
                    "university_name": str(ed.get("university_name") or "").strip()[:200],
                    "major": str(ed.get("major") or "").strip()[:200],
                    "degree_level": str(ed.get("degree_level") or "").strip()[:40],
                    "thesis_topic": str(ed.get("thesis_topic") or "").strip()[:300],
                }

            # 5. Career preferences & social links
            if "career_preferences" in payload and isinstance(payload["career_preferences"], dict):
                cp = payload["career_preferences"]
                work_mode = str(cp.get("preferred_work_mode") or "FLEXIBLE").upper().strip()
                if work_mode not in ALLOWED_WORK_MODES:
                    work_mode = "FLEXIBLE"
                desired_salary = cp.get("desired_salary_uzs")
                if desired_salary is not None and desired_salary != "":
                    try:
                        desired_salary = max(0, int(desired_salary))
                    except (ValueError, TypeError):
                        desired_salary = None
                else:
                    desired_salary = None
                state["career_preferences"] = {
                    "desired_salary_uzs": desired_salary,
                    "preferred_work_mode": work_mode,
                    "github_url": str(cp.get("github_url") or "").strip()[:300],
                    "linkedin_url": str(cp.get("linkedin_url") or "").strip()[:300],
                    "telegram_username": str(cp.get("telegram_username") or "").strip()[:100],
                    "website_url": str(cp.get("website_url") or "").strip()[:300],
                    "career_objective": str(cp.get("career_objective") or "").strip()[:2000],
                    "desired_roles": [str(r).strip()[:80] for r in (cp.get("desired_roles") or [])
                                      if isinstance(r, str) and str(r).strip()][:10],
                    "preferred_weekly_hours": _bounded_int(cp.get("preferred_weekly_hours"), 0, 60),
                }

            state["candidate_id"] = cand_id
            state["updated_at"] = now().isoformat()
            save_domain_record(RESUME_DETAILS_NAMESPACE, cand_id, state)

            audit.append_audit_event(
                actor_id=actor.user_id,
                action="CANDIDATE_RESUME_DETAILS_UPDATED",
                entity_type="candidate_profile",
                entity_id=cand_id,
                metadata={
                    "achievements_count": len(state["achievements"]),
                    "work_experiences_count": len(state["work_experiences"]),
                    "languages_count": len(state["languages"]),
                },
            )

            return {
                "ok": True,
                "contract_id": "API-026-RESUME-DETAILS",
                **state,
            }

    def upload_candidate_pdf_file(
        self,
        actor: ActorContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Direct candidate PDF upload. Fail-closed: the bytes must be a real PDF the
        student supplied, the antivirus must confirm it clean and the private object
        must be stored before a CLEAN file record exists (no generated blank PDFs).
        The scan and the object write run outside any database transaction."""
        with transaction() as conn:
            cand_id = str(candidate_id_for(actor))
            account_authority(conn, actor)

        filename = pdf_intake.clean_filename(payload.get("filename"))
        purpose = str(payload.get("purpose") or "CERTIFICATE").upper().strip()
        raw_bytes = pdf_intake.decode_pdf(payload.get("content_base64"))
        pdf_intake.scan_and_validate(raw_bytes)

        file_id = str(uuid4())
        stored = pdf_intake.store(f"private/candidates/{cand_id}/{file_id}.pdf", raw_bytes)
        storage_key, sha256_hash, byte_size = stored.storage_key, stored.sha256, stored.byte_size
        bucket_name, version_id, etag = stored.bucket, stored.version_id, stored.etag

        with transaction() as conn:
            account_authority(conn, actor)
            ts = now()
            conn.execute(
                files_table.insert().values(
                    id=file_id,
                    created_at=ts,
                    updated_at=ts,
                    owner_user_id=actor.user_id,
                    storage_key=storage_key,
                    filename=filename,
                    mime_type="application/pdf",
                    byte_size=byte_size,
                    sha256=sha256_hash,
                    scan_status="CLEAN",
                    scanned_at=ts,
                    retention_class="CANDIDATE_CERTIFICATE",
                    object_version=version_id,
                    storage_bucket=bucket_name,
                    storage_version_id=version_id,
                    storage_etag=etag,
                )
            )

            # If purpose == 'CV', automatically link cv_file_id on candidate_profiles
            if purpose == "CV":
                t_cand = table("candidate_profiles")
                conn.execute(
                    t_cand.update()
                    .where(t_cand.c.id == cand_id)
                    .values(cv_file_id=file_id, updated_at=ts)
                )

            audit.append_audit_event(
                actor_id=actor.user_id,
                action="CANDIDATE_PDF_FILE_UPLOADED_AND_SCANNED",
                entity_type="file",
                entity_id=file_id,
                metadata={
                    "candidate_id": cand_id,
                    "filename": filename,
                    "purpose": purpose,
                    "byte_size": byte_size,
                    "sha256": sha256_hash,
                },
            )

            return {
                "ok": True,
                "contract_id": "API-026-DIRECT-UPLOAD",
                "file_id": file_id,
                "filename": filename,
                "mime_type": "application/pdf",
                "byte_size": byte_size,
                "sha256": sha256_hash,
                "scan_status": "CLEAN",
                "purpose": purpose,
                "linked_as_cv": purpose == "CV",
                "created_at": ts.isoformat(),
            }


candidate_resume_builder_service = CandidateResumeBuilderService()
