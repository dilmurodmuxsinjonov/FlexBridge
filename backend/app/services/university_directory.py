"""University institution directory profile & partnership agreements service (API-098-DIRECTORY / API-101-CREATE).

Enables University Coordinators and Staff to maintain complete OTM directory information
(official name, registry code, rector, career center head, faculties, educational programs,
internship quotas, and partnership agreements).
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.institution_scope import TASHKENT
from app.db.storage import load_domain_record, now, save_domain_record, table, transaction
from app.services.authority import account_authority
from app.services.governance import GovernanceError
from app.services.placements import get_row, insert_row

audit = AppendOnlyAuditStore()
INST_DIRECTORY_NAMESPACE = 'institution_directory_profile'
INST_AGREEMENTS_NAMESPACE = 'institution_partner_agreements'


def _verify_institution_member(conn: Any, actor: ActorContext, inst_id: str) -> dict[str, Any]:
    account_authority(conn, actor)
    inst = get_row(conn, 'institutions', inst_id)
    members = table('institution_memberships')
    member = conn.execute(
        select(members).where(
            members.c.institution_id == inst_id,
            members.c.user_id == actor.user_id,
            members.c.status == 'ACTIVE',
            members.c.revoked_at.is_(None),
        )
    ).mappings().first()
    if not member:
        raise GovernanceError('INSTITUTION_SCOPE_FORBIDDEN', status_code=403)
    return dict(inst)


def _calculate_inst_completion(profile: dict[str, Any]) -> int:
    tracked = (
        'official_name',
        'short_name',
        'registry_code',
        'institution_type',
        'region',
        'address',
        'rector_name',
        'career_center_head',
        'contact_phone',
        'contact_email',
        'website_url',
        'internship_policy_summary',
    )
    filled = sum(1 for k in tracked if str(profile.get(k) or '').strip())
    if profile.get('faculties'):
        filled += 1
    if profile.get('programs'):
        filled += 1
    if int(profile.get('annual_intern_quota') or 0) > 0:
        filled += 1
    total = len(tracked) + 3
    return min(100, int(round((filled / total) * 100)))


class UniversityDirectoryService:
    def get_directory_profile(self, actor: ActorContext, inst_id: str) -> dict[str, Any]:
        with transaction() as conn:
            inst = _verify_institution_member(conn, actor, inst_id)
            stored = load_domain_record(INST_DIRECTORY_NAMESPACE, str(inst_id)) or {}
            agreements_meta = load_domain_record(INST_AGREEMENTS_NAMESPACE, str(inst_id)) or {}

            t_agr = table('institution_agreements')
            db_agreements = conn.execute(
                select(t_agr)
                .where(t_agr.c.institution_id == inst_id)
                .order_by(t_agr.c.version.desc())
            ).mappings().all()

            meta_by_id = {
                str(item.get('id')): item
                for item in (agreements_meta.get('items') or [])
                if isinstance(item, dict) and item.get('id')
            }

            agreements_list = []
            for row in db_agreements:
                aid = str(row['id'])
                extra = meta_by_id.get(aid, {})
                agreements_list.append({
                    'id': aid,
                    'version': int(row['version']),
                    'status': row['status'],
                    'valid_from': str(row['valid_from']),
                    'valid_to': str(row['valid_to']) if row['valid_to'] else None,
                    'purposes': row['purposes'] if isinstance(row['purposes'], list) else ['ACADEMIC_VIEW'],
                    'partner_organization_name': extra.get('partner_organization_name') or 'Hamkor korxona (Umumiy akademik kelishuv)',
                    'agreement_number': extra.get('agreement_number') or f"AGR-{row['version']:03d}",
                    'quota_slots': int(extra.get('quota_slots') or 25),
                    'coordinator_note': extra.get('coordinator_note') or '',
                })

            profile = {
                'institution_id': str(inst_id),
                'status': inst.get('status', 'VERIFIED'),
                'official_name': stored.get('official_name') or inst.get('name') or '',
                'short_name': stored.get('short_name') or '',
                'registry_code': stored.get('registry_code') or inst.get('registry_code') or '',
                'institution_type': stored.get('institution_type') or 'Davlat oliy ta\'lim muassasasi',
                'region': stored.get('region') or inst.get('region') or 'Toshkent',
                'address': stored.get('address') or '',
                'rector_name': stored.get('rector_name') or '',
                'career_center_head': stored.get('career_center_head') or '',
                'contact_phone': stored.get('contact_phone') or '',
                'contact_email': stored.get('contact_email') or '',
                'website_url': stored.get('website_url') or '',
                'faculties': stored.get('faculties') if isinstance(stored.get('faculties'), list) else [],
                'programs': stored.get('programs') if isinstance(stored.get('programs'), list) else [],
                'annual_intern_quota': int(stored.get('annual_intern_quota') or 500),
                'internship_policy_summary': stored.get('internship_policy_summary') or '',
                'partner_agreements': agreements_list,
                'updated_at': stored.get('updated_at'),
            }
            profile['completion_percent'] = _calculate_inst_completion(profile)
            return {
                'contract_id': 'API-098-DIRECTORY',
                **profile,
            }

    def update_directory_profile(
        self,
        actor: ActorContext,
        inst_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with transaction() as conn:
            inst = _verify_institution_member(conn, actor, inst_id)
            current = load_domain_record(INST_DIRECTORY_NAMESPACE, str(inst_id)) or {}

            faculties_raw = payload.get('faculties', current.get('faculties', []))
            faculties = []
            for item in (faculties_raw if isinstance(faculties_raw, list) else [])[:50]:
                if not isinstance(item, dict):
                    continue
                name = str(item.get('name') or '').strip()
                if len(name) < 2:
                    continue
                faculties.append({
                    'id': str(item.get('id') or uuid4()),
                    'name': name[:200],
                    'dean_name': str(item.get('dean_name') or '').strip()[:160],
                    'programs_count': max(1, int(item.get('programs_count') or 1)),
                    'students_count': max(0, int(item.get('students_count') or 0)),
                })

            programs_raw = payload.get('programs', current.get('programs', []))
            programs = []
            for item in (programs_raw if isinstance(programs_raw, list) else [])[:100]:
                if not isinstance(item, dict):
                    continue
                name = str(item.get('name') or '').strip()
                if len(name) < 2:
                    continue
                programs.append({
                    'id': str(item.get('id') or uuid4()),
                    'code': str(item.get('code') or '60610100').strip()[:40],
                    'name': name[:200],
                    'degree_level': str(item.get('degree_level') or 'BAKALAVR').strip()[:40],
                    'duration_years': max(1, min(10, int(item.get('duration_years') or 4))),
                })

            updated = {
                'institution_id': str(inst_id),
                'status': inst.get('status', 'VERIFIED'),
                'official_name': str(payload.get('official_name', current.get('official_name') or inst.get('name') or '')).strip()[:250],
                'short_name': str(payload.get('short_name', current.get('short_name') or '')).strip()[:80],
                'registry_code': str(payload.get('registry_code', current.get('registry_code') or inst.get('registry_code') or '')).strip()[:64],
                'institution_type': str(payload.get('institution_type', current.get('institution_type') or 'Davlat oliy ta\'lim muassasasi')).strip()[:120],
                'region': str(payload.get('region', current.get('region') or inst.get('region') or 'Toshkent')).strip()[:100],
                'address': str(payload.get('address', current.get('address') or '')).strip()[:500],
                'rector_name': str(payload.get('rector_name', current.get('rector_name') or '')).strip()[:160],
                'career_center_head': str(payload.get('career_center_head', current.get('career_center_head') or '')).strip()[:160],
                'contact_phone': str(payload.get('contact_phone', current.get('contact_phone') or '')).strip()[:40],
                'contact_email': str(payload.get('contact_email', current.get('contact_email') or '')).strip()[:160],
                'website_url': str(payload.get('website_url', current.get('website_url') or '')).strip()[:500],
                'faculties': faculties,
                'programs': programs,
                'annual_intern_quota': max(0, int(payload.get('annual_intern_quota') or current.get('annual_intern_quota') or 500)),
                'internship_policy_summary': str(payload.get('internship_policy_summary', current.get('internship_policy_summary') or '')).strip()[:4000],
                'updated_at': now().isoformat(),
            }
            updated['completion_percent'] = _calculate_inst_completion(updated)

        save_domain_record(INST_DIRECTORY_NAMESPACE, str(inst_id), updated)

        audit.append_audit_event(
            actor_id=actor.user_id,
            action='INSTITUTION_DIRECTORY_PROFILE_UPDATE',
            entity_type='institution',
            entity_id=str(inst_id),
            metadata={
                'completion_percent': updated['completion_percent'],
                'faculties_count': len(faculties),
                'programs_count': len(programs),
            },
        )
        return self.get_directory_profile(actor, inst_id)

    def create_partner_agreement(
        self,
        actor: ActorContext,
        inst_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with transaction() as conn:
            _verify_institution_member(conn, actor, inst_id)
            t_agr = table('institution_agreements')
            max_ver = conn.execute(
                select(func.coalesce(func.max(t_agr.c.version), 0)).where(
                    t_agr.c.institution_id == inst_id
                )
            ).scalar_one()
            next_version = int(max_ver) + 1

            today = now().astimezone(TASHKENT).date()
            valid_from_raw = payload.get('valid_from')
            if isinstance(valid_from_raw, date):
                valid_from_val = valid_from_raw
            elif isinstance(valid_from_raw, str) and valid_from_raw.strip():
                valid_from_val = date.fromisoformat(valid_from_raw.strip())
            else:
                valid_from_val = today

            valid_to_raw = payload.get('valid_to')
            if isinstance(valid_to_raw, date):
                valid_to_val = valid_to_raw
            elif isinstance(valid_to_raw, str) and valid_to_raw.strip():
                valid_to_val = date.fromisoformat(valid_to_raw.strip())
            else:
                valid_to_val = None

            if valid_to_val is not None and valid_to_val < valid_from_val:
                raise GovernanceError('INVALID_INSTITUTION_AGREEMENT_DATES', status_code=422)

            purposes_raw = payload.get('purposes')
            purposes = [
                str(p).strip().upper()
                for p in (purposes_raw if isinstance(purposes_raw, list) and purposes_raw else ['ACADEMIC_VIEW', 'INTERNSHIP_SUPERVISION'])
                if str(p).strip()
            ]

            row = insert_row(
                conn,
                'institution_agreements',
                institution_id=inst_id,
                version=next_version,
                status='ACTIVE',
                valid_from=valid_from_val,
                valid_to=valid_to_val,
                purposes=purposes,
                signed_file_id=str(payload['signed_file_id']) if payload.get('signed_file_id') else None,
            )

        agreements_meta = load_domain_record(INST_AGREEMENTS_NAMESPACE, str(inst_id)) or {'items': []}
        items = list(agreements_meta.get('items') or [])
        meta_entry = {
            'id': str(row['id']),
            'version': next_version,
            'status': 'ACTIVE',
            'valid_from': str(valid_from_val),
            'valid_to': str(valid_to_val) if valid_to_val else None,
            'purposes': purposes,
            'partner_organization_name': str(payload.get('partner_organization_name') or 'Hamkor korxona').strip()[:200],
            'agreement_number': str(payload.get('agreement_number') or f"AGR-{next_version:03d}").strip()[:80],
            'quota_slots': max(1, int(payload.get('quota_slots') or 25)),
            'coordinator_note': str(payload.get('coordinator_note') or '').strip()[:1000],
        }
        items.insert(0, meta_entry)
        save_domain_record(INST_AGREEMENTS_NAMESPACE, str(inst_id), {'items': items})

        audit.append_audit_event(
            actor_id=actor.user_id,
            action='INSTITUTION_PARTNER_AGREEMENT_CREATE',
            entity_type='institution_agreement',
            entity_id=str(row['id']),
            metadata={
                'institution_id': str(inst_id),
                'version': next_version,
                'partner_organization_name': meta_entry['partner_organization_name'],
            },
        )
        return {
            'contract_id': 'API-101-CREATE',
            **meta_entry,
        }


university_directory_service = UniversityDirectoryService()
