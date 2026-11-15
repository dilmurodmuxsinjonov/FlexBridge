"""Employer organization directory profile service (API-067-DIRECTORY).

Provides complete corporate directory data management (legal details, HR contacts,
banking/requisites, internship conditions, student benefits, and company profile)
for the Employer Portal (`ORG_TEAM` & Directory Hub).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import load_domain_record, now, save_domain_record, table, transaction
from app.services.authority import account_authority
from app.services.governance import GovernanceError
from app.services.placements import get_row

audit = AppendOnlyAuditStore()
DIRECTORY_NAMESPACE = 'organization_directory_profile'


def _verify_org_member(conn: Any, actor: ActorContext, org_id: str) -> dict[str, Any]:
    account_authority(conn, actor)
    org = get_row(conn, 'organizations', org_id)
    members = table('org_memberships')
    member = conn.execute(
        select(members).where(
            members.c.organization_id == org_id,
            members.c.user_id == actor.user_id,
        )
    ).mappings().first()
    if not member or member['revoked_at'] or member['status'] in ('REVOKED', 'REJECTED'):
        raise GovernanceError('ORG_SCOPE_FORBIDDEN', status_code=403)
    return dict(org)


def _calculate_org_completion(profile: dict[str, Any]) -> int:
    tracked_fields = (
        'official_name',
        'brand_name',
        'tax_id',
        'industry',
        'region',
        'legal_address',
        'company_size',
        'website_url',
        'hr_contact_name',
        'hr_contact_phone',
        'hr_contact_email',
        'director_name',
        'bank_name',
        'bank_mfo',
        'bank_account',
        'about_company',
        'internship_conditions',
    )
    filled = sum(1 for key in tracked_fields if str(profile.get(key) or '').strip())
    if profile.get('student_perks'):
        filled += 1
    total = len(tracked_fields) + 1
    return min(100, int(round((filled / total) * 100)))


class EmployerDirectoryService:
    def get_directory_profile(self, actor: ActorContext, org_id: str) -> dict[str, Any]:
        with transaction() as conn:
            org = _verify_org_member(conn, actor, org_id)
            stored = load_domain_record(DIRECTORY_NAMESPACE, str(org_id)) or {}

            profile = {
                'organization_id': str(org_id),
                'status': org.get('status', 'PENDING'),
                'official_name': stored.get('official_name') or org.get('legal_name') or '',
                'brand_name': stored.get('brand_name') or org.get('public_name') or '',
                'tax_id': stored.get('tax_id') or org.get('tax_id') or '',
                'industry': stored.get('industry') or 'Axborot texnologiyalari va FinTech',
                'region': stored.get('region') or org.get('region') or 'Toshkent',
                'legal_address': stored.get('legal_address') or '',
                'company_size': stored.get('company_size') or '50-200 xodim',
                'founded_year': stored.get('founded_year') or 2020,
                'website_url': stored.get('website_url') or org.get('website') or '',
                'hr_contact_name': stored.get('hr_contact_name') or '',
                'hr_contact_phone': stored.get('hr_contact_phone') or '',
                'hr_contact_email': stored.get('hr_contact_email') or '',
                'director_name': stored.get('director_name') or '',
                'bank_name': stored.get('bank_name') or '',
                'bank_mfo': stored.get('bank_mfo') or '',
                'bank_account': stored.get('bank_account') or '',
                'about_company': stored.get('about_company') or org.get('description') or '',
                'internship_conditions': stored.get('internship_conditions') or '',
                'student_perks': stored.get('student_perks') if isinstance(stored.get('student_perks'), list) else [],
                'updated_at': stored.get('updated_at'),
            }
            profile['completion_percent'] = _calculate_org_completion(profile)
            return {
                'contract_id': 'API-067-DIRECTORY',
                **profile,
            }

    def update_directory_profile(
        self,
        actor: ActorContext,
        org_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with transaction() as conn:
            org = _verify_org_member(conn, actor, org_id)
            current = load_domain_record(DIRECTORY_NAMESPACE, str(org_id)) or {}

            perks_raw = payload.get('student_perks', current.get('student_perks', []))
            student_perks = [
                str(item).strip()[:120]
                for item in (perks_raw if isinstance(perks_raw, list) else [])
                if str(item).strip()
            ][:30]

            updated = {
                'organization_id': str(org_id),
                'status': org.get('status', 'PENDING'),
                'official_name': str(payload.get('official_name', current.get('official_name') or org.get('legal_name') or '')).strip()[:250],
                'brand_name': str(payload.get('brand_name', current.get('brand_name') or org.get('public_name') or '')).strip()[:200],
                'tax_id': str(payload.get('tax_id', current.get('tax_id') or org.get('tax_id') or '')).strip()[:64],
                'industry': str(payload.get('industry', current.get('industry') or 'Axborot texnologiyalari va FinTech')).strip()[:160],
                'region': str(payload.get('region', current.get('region') or org.get('region') or 'Toshkent')).strip()[:100],
                'legal_address': str(payload.get('legal_address', current.get('legal_address') or '')).strip()[:500],
                'company_size': str(payload.get('company_size', current.get('company_size') or '50-200 xodim')).strip()[:80],
                'founded_year': int(payload.get('founded_year') or current.get('founded_year') or 2020),
                'website_url': str(payload.get('website_url', current.get('website_url') or org.get('website') or '')).strip()[:500],
                'hr_contact_name': str(payload.get('hr_contact_name', current.get('hr_contact_name') or '')).strip()[:160],
                'hr_contact_phone': str(payload.get('hr_contact_phone', current.get('hr_contact_phone') or '')).strip()[:40],
                'hr_contact_email': str(payload.get('hr_contact_email', current.get('hr_contact_email') or '')).strip()[:160],
                'director_name': str(payload.get('director_name', current.get('director_name') or '')).strip()[:160],
                'bank_name': str(payload.get('bank_name', current.get('bank_name') or '')).strip()[:200],
                'bank_mfo': str(payload.get('bank_mfo', current.get('bank_mfo') or '')).strip()[:20],
                'bank_account': str(payload.get('bank_account', current.get('bank_account') or '')).strip()[:40],
                'about_company': str(payload.get('about_company', current.get('about_company') or org.get('description') or '')).strip()[:5000],
                'internship_conditions': str(payload.get('internship_conditions', current.get('internship_conditions') or '')).strip()[:3000],
                'student_perks': student_perks,
                'updated_at': now().isoformat(),
            }
            updated['completion_percent'] = _calculate_org_completion(updated)

        save_domain_record(DIRECTORY_NAMESPACE, str(org_id), updated)

        audit.append_audit_event(
            actor_id=actor.user_id,
            action='ORG_DIRECTORY_PROFILE_UPDATE',
            entity_type='organization',
            entity_id=str(org_id),
            metadata={
                'completion_percent': updated['completion_percent'],
                'industry': updated['industry'],
                'region': updated['region'],
            },
        )
        return {
            'contract_id': 'API-067-DIRECTORY',
            **updated,
        }


employer_directory_service = EmployerDirectoryService()
