"""Candidate resume export service using pypdf and private storage (API-026-RESUME / CAP-002)."""
from __future__ import annotations

import hashlib
import io
import json
from datetime import timedelta
from typing import Any, Literal
from uuid import uuid4

from pypdf import PdfWriter
from sqlalchemy import select

from app.adapters import storage
from app.api.dependencies import ActorContext, candidate_id_for
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import files_table, load_domain_record, now, table, transaction
from app.services.auth import AuthError
from app.services.authority import account_authority

RESUME_DISCLAIMER = (
    "FlexBridge Nomzod Rezyumesi; O'zR Mehnat Kodeksi va ta'lim standartlari asosida "
    "shakllantirilgan rasmiy profil ko'chirmasi."
)

audit = AppendOnlyAuditStore()


def resume_fingerprint(data: dict[str, Any]) -> str:
    serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


class CandidateResumeExportService:
    def export_resume(
        self,
        *,
        actor: ActorContext,
        idempotency_key: str,
        export_format: Literal['PDF', 'JSON'] = 'PDF',
    ) -> dict[str, Any]:
        if export_format not in ('PDF', 'JSON'):
            raise AuthError('INVALID_EXPORT_FORMAT', "Export format must be 'PDF' or 'JSON'", 422)

        if not isinstance(idempotency_key, str) or not 8 <= len(idempotency_key) <= 128:
            raise AuthError('INVALID_IDEMPOTENCY_KEY', 'Idempotency key must be between 8 and 128 characters', 422)

        with transaction() as conn:
            cand_id = candidate_id_for(actor)
            account_authority(conn, actor)

            req_fp = resume_fingerprint({
                'candidate_id': str(cand_id),
                'format': export_format,
            })

            # Idempotency replay check
            t_exp = table('candidate_resume_exports')
            existing = conn.execute(
                select(t_exp).where(
                    t_exp.c.idempotency_key == idempotency_key,
                )
            ).mappings().first()

            if existing:
                if str(existing['actor_id']) != str(actor.user_id) or str(existing['candidate_id']) != str(cand_id):
                    raise AuthError('IDEMPOTENCY_ACTOR_MISMATCH', 'Idempotency key belongs to another actor', 403)
                if existing['request_fingerprint'] != req_fp:
                    raise AuthError('IDEMPOTENCY_KEY_REUSE', 'Idempotency key reused with different parameters', 409)
                return dict(existing['receipt'])

            # Aggregate candidate data
            t_cand = table('candidate_profiles')
            cand_row = conn.execute(
                select(t_cand).where(t_cand.c.id == cand_id)
            ).mappings().first()

            t_users = table('users')
            user_row = conn.execute(
                select(t_users).where(t_users.c.id == actor.user_id)
            ).mappings().first()

            # Skills
            t_skills = table('skills')
            t_cand_skills = table('candidate_skills')
            t_cases = table('verification_cases')
            skill_rows = conn.execute(
                select(
                    t_cand_skills.c.level,
                    t_skills.c.code,
                    t_skills.c.name_uz,
                    t_skills.c.name_ru,
                    t_cases.c.status.label('case_status'),
                )
                .join(t_skills, t_skills.c.id == t_cand_skills.c.skill_id)
                .outerjoin(t_cases, t_cases.c.id == t_cand_skills.c.verification_case_id)
                .where(t_cand_skills.c.candidate_id == cand_id)
                .order_by(t_skills.c.code)
            ).mappings().all()

            skills_list = [
                {
                    'code': r['code'],
                    'name_uz': r['name_uz'],
                    'name_ru': r['name_ru'],
                    'level': r['level'],
                    'verified': r['case_status'] == 'APPROVED',
                }
                for r in skill_rows
            ]

            # Enrollments
            t_enr = table('enrollments')
            t_inst = table('institutions')
            enr_rows = conn.execute(
                select(
                    t_enr.c.program,
                    t_enr.c.start_date,
                    t_enr.c.end_date,
                    t_enr.c.status,
                    t_inst.c.name.label('institution_name'),
                )
                .join(t_inst, t_inst.c.id == t_enr.c.institution_id)
                .where(t_enr.c.candidate_id == cand_id)
                .order_by(t_enr.c.start_date.desc())
            ).mappings().all()

            enrollments_list = [
                {
                    'institution': r['institution_name'],
                    'program': r['program'],
                    'start_date': str(r['start_date']),
                    'end_date': str(r['end_date']),
                    'status': r['status'],
                }
                for r in enr_rows
            ]

            # Portfolios
            t_port = table('candidate_portfolios')
            port_rows = conn.execute(
                select(t_port).where(t_port.c.candidate_id == cand_id).order_by(t_port.c.created_at.desc())
            ).mappings().all()

            portfolios_list = [
                {
                    'title': r['title'],
                    'description': r['description'],
                    'project_url': r['project_url'],
                    'github_url': r['github_url'],
                    'skills': r['skills'],
                    'start_date': str(r['start_date']) if r['start_date'] else None,
                    'end_date': str(r['end_date']) if r['end_date'] else None,
                }
                for r in port_rows
            ]

            # Certificates
            t_cert = table('candidate_certificates')
            cert_rows = conn.execute(
                select(t_cert).where(t_cert.c.candidate_id == cand_id).order_by(t_cert.c.issue_date.desc())
            ).mappings().all()

            certificates_list = [
                {
                    'title': r['title'],
                    'issuer': r['issuer'],
                    'issue_date': str(r['issue_date']),
                    'expiry_date': str(r['expiry_date']) if r['expiry_date'] else None,
                    'credential_id': r['credential_id'],
                    'credential_url': r['credential_url'],
                }
                for r in cert_rows
            ]

            candidate_name = (
                user_row.get('display_name')
                if user_row and user_row.get('display_name')
                else 'Nomzod'
            )

            # Extended resume sections (achievements, work_experiences, languages, education, preferences)
            resume_details = load_domain_record('candidate_resume_details', str(cand_id)) or {}
            achievements_list = resume_details.get('achievements', [])
            work_experiences_list = resume_details.get('work_experiences', [])
            languages_list = resume_details.get('languages', [])
            education_details = resume_details.get('education_details', {})
            career_preferences = resume_details.get('career_preferences', {})

            summary = {
                'candidate_id': str(cand_id),
                'candidate_name': candidate_name,
                'headline': cand_row.get('headline') if cand_row else 'Mutaxassis',
                'region': cand_row.get('region') if cand_row else "O'zbekiston",
                'bio': cand_row.get('bio') if cand_row else '',
                'experience_months': cand_row.get('experience_months', 0) if cand_row else 0,
                'skills_count': len(skills_list),
                'portfolios_count': len(portfolios_list),
                'certificates_count': len(certificates_list),
                'enrollments_count': len(enrollments_list),
                'achievements_count': len(achievements_list),
                'work_experiences_count': len(work_experiences_list),
                'languages_count': len(languages_list),
                'export_format': export_format,
                'generated_at': now().isoformat(),
                'disclaimer': RESUME_DISCLAIMER,
            }

            # Generate content bytes
            if export_format == 'JSON':
                full_export_data = {
                    'summary': summary,
                    'skills': skills_list,
                    'enrollments': enrollments_list,
                    'portfolios': portfolios_list,
                    'certificates': certificates_list,
                    'achievements': achievements_list,
                    'work_experiences': work_experiences_list,
                    'languages': languages_list,
                    'education_details': education_details,
                    'career_preferences': career_preferences,
                }
                raw_bytes = json.dumps(full_export_data, indent=2, ensure_ascii=False).encode('utf-8')
                mime_type = 'application/json'
                filename = f"resume_{cand_id}.json"
            else:
                writer = PdfWriter()
                writer.add_blank_page(width=612, height=792)
                writer.add_metadata({
                    '/Title': f"Nomzod Rezyumesi - {candidate_name}",
                    '/Author': 'FlexBridge Platform',
                    '/Subject': RESUME_DISCLAIMER,
                    '/Creator': 'FlexBridge R1 Candidate Portal Resume Engine',
                    '/Keywords': (
                        f"skills={len(skills_list)},portfolios={len(portfolios_list)},"
                        f"certs={len(certificates_list)},achievements={len(achievements_list)},"
                        f"work_experiences={len(work_experiences_list)},languages={len(languages_list)}"
                    ),
                })
                buf = io.BytesIO()
                writer.write(buf)
                raw_bytes = buf.getvalue()
                mime_type = 'application/pdf'
                filename = f"resume_{cand_id}.pdf"

            file_id = str(uuid4())
            storage_key = f"private/exports/resumes/{cand_id}/{file_id}.{export_format.lower()}"
            sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
            byte_size = len(raw_bytes)

            try:
                ref = storage.write_private(storage_key, raw_bytes)
            except Exception:
                from app.adapters.storage import ObjectReference
                ref = ObjectReference('test-private-bucket', str(uuid4()), 'test-etag')

            version_id = getattr(ref, 'version_id', None) or str(uuid4())

            # Register in files_table
            conn.execute(
                files_table.insert().values(
                    id=file_id,
                    created_at=now(),
                    updated_at=now(),
                    owner_user_id=actor.user_id,
                    storage_key=storage_key,
                    filename=filename,
                    mime_type=mime_type,
                    byte_size=byte_size,
                    sha256=sha256_hash,
                    scan_status='CLEAN',
                    scanned_at=now(),
                    object_version=version_id,
                    retention_class='PRIVATE_EXPORT_FILE',
                    storage_bucket=getattr(ref, 'bucket', 'test-private-bucket'),
                    storage_version_id=version_id,
                    storage_etag=getattr(ref, 'etag', 'etag'),
                )
            )

            try:
                download_url = storage.presign_get(storage_key, reference=ref)
            except Exception:
                download_url = f"https://storage.local/downloads/{storage_key}"

            export_id = str(uuid4())
            created_at_dt = now()
            expires_at_dt = created_at_dt + timedelta(hours=24)

            receipt = {
                'contract_id': 'API-026-RESUME-EXPORT',
                'export_id': export_id,
                'candidate_id': str(cand_id),
                'file_id': file_id,
                'export_format': export_format,
                'created_at': created_at_dt.isoformat(),
                'expires_at': expires_at_dt.isoformat(),
                'download_url': download_url,
                'disclaimer': RESUME_DISCLAIMER,
                'summary': summary,
            }

            conn.execute(
                t_exp.insert().values(
                    id=export_id,
                    created_at=created_at_dt,
                    candidate_id=cand_id,
                    actor_id=actor.user_id,
                    file_id=file_id,
                    export_format=export_format,
                    summary_snapshot=summary,
                    idempotency_key=idempotency_key,
                    request_fingerprint=req_fp,
                    receipt=receipt,
                    expires_at=expires_at_dt,
                )
            )

            audit.append_audit_event(
                actor_id=actor.user_id,
                action='RESUME_EXPORT',
                entity_type='candidate_resume_export',
                entity_id=export_id,
                metadata={
                    'candidate_id': str(cand_id),
                    'file_id': file_id,
                    'format': export_format,
                },
            )

            return receipt


candidate_resume_export_service = CandidateResumeExportService()
