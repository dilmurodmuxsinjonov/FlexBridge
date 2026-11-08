"""Self-service profile writes never grant education, skill verification or file access."""
from sqlalchemy import select, or_

from app.core.audit import AppendOnlyAuditStore
from app.db.storage import table, transaction, now
from app.services.auth import AuthError
from app.services.placements import insert_row

audit = AppendOnlyAuditStore()


def own_profile(conn, user_id, lock=False):
    profiles = table('candidate_profiles')
    query = select(profiles).where(profiles.c.user_id == user_id)
    row = conn.execute(query.with_for_update() if lock else query).mappings().first()
    if not row:
        raise AuthError('CANDIDATE_PROFILE_REQUIRED', 'Candidate profile required', 403)
    return dict(row)


class CandidateService:
    def get_profile(self, user_id):
        with transaction() as conn:
            profile = own_profile(conn, user_id)
            skills, catalog, cases = table('candidate_skills'), table('skills'), table('verification_cases')
            rows = conn.execute(select(skills.c.skill_id, skills.c.level, catalog.c.code,
                catalog.c.name_uz, catalog.c.name_ru, catalog.c.active,
                cases.c.status.label('case_status'), cases.c.candidate_id.label('case_candidate_id'))
                .join(catalog, catalog.c.id == skills.c.skill_id)
                .outerjoin(cases, cases.c.id == skills.c.verification_case_id)
                .where(skills.c.candidate_id == profile['id']).order_by(catalog.c.code)).mappings()
            profile['skills'] = [{k: r[k] for k in ('skill_id', 'level', 'code', 'name_uz', 'name_ru', 'active')}
                | {'verified': r['case_status'] == 'APPROVED' and r['case_candidate_id'] == profile['id']}
                for r in rows]
            return profile

    def update_profile(self, user_id, changes):
        with transaction() as conn:
            profile = own_profile(conn, user_id, True)
            if changes:
                conn.execute(table('candidate_profiles').update().where(
                    table('candidate_profiles').c.id == profile['id']).values(**changes, updated_at=now()))
                audit.append_audit_event(actor_id=user_id, action='CANDIDATE_PROFILE_UPDATED',
                    entity_type='candidate_profile', entity_id=profile['id'], metadata={'fields': sorted(changes)})
            return self.get_profile(user_id)

    def update_skills(self, user_id, skills, remove_skill_ids):
        ids = [str(s['skill_id']) for s in skills]
        removals = [str(value) for value in remove_skill_ids]
        if len(ids) != len(set(ids)) or len(removals) != len(set(removals)) or set(ids) & set(removals):
            raise AuthError('DUPLICATE_SKILL', 'Each skill may appear only once', 422)
        with transaction() as conn:
            profile = own_profile(conn, user_id, True)
            catalog, candidates = table('skills'), table('candidate_skills')
            if ids:
                active = set(conn.execute(select(catalog.c.id).where(catalog.c.id.in_(ids), catalog.c.active.is_(True))).scalars())
                if set(ids) != active:
                    raise AuthError('INVALID_SKILL', 'Select an active catalog skill', 422)
            current = {r['skill_id']: r for r in conn.execute(select(candidates).where(
                candidates.c.candidate_id == profile['id'])).mappings()}
            if removals:
                conn.execute(candidates.delete().where(candidates.c.candidate_id == profile['id'], candidates.c.skill_id.in_(removals)))
            for item in skills:
                skill_id = str(item['skill_id'])
                existing = current.get(skill_id)
                if existing:
                    if existing['level'] != item['level']:
                        conn.execute(candidates.update().where(candidates.c.id == existing['id']).values(
                            level=item['level'], verification_case_id=None, updated_at=now()))
                else:
                    insert_row(conn, 'candidate_skills', candidate_id=profile['id'], skill_id=skill_id,
                        level=item['level'], verification_case_id=None)
            audit.append_audit_event(actor_id=user_id, action='CANDIDATE_SKILLS_UPDATED',
                entity_type='candidate_profile', entity_id=profile['id'])
            return self.get_profile(user_id)

    def link_cv(self, user_id, file_id):
        with transaction() as conn:
            profile = own_profile(conn, user_id, True)
            if file_id is not None:
                files = table('files')
                file = conn.execute(select(files).where(files.c.id == str(file_id),
                    files.c.owner_user_id == user_id).with_for_update()).mappings().first()
                if not file:
                    raise AuthError('FILE_ACCESS_DENIED', 'Use your own CV file', 403)
                if file['deleted_at'] or file['scan_status'] != 'CLEAN' or file['mime_type'] != 'application/pdf':
                    raise AuthError('CV_NOT_CLEAN', 'Complete upload and scanning first', 409)
            conn.execute(table('candidate_profiles').update().where(table('candidate_profiles').c.id == profile['id'])
                .values(cv_file_id=str(file_id) if file_id else None, updated_at=now()))
            audit.append_audit_event(actor_id=user_id, action='CANDIDATE_CV_LINKED' if file_id else 'CANDIDATE_CV_UNLINKED',
                entity_type='candidate_profile', entity_id=profile['id'])
            return {'candidate_id': profile['id'], 'cv_file_id': str(file_id) if file_id else None}

    def catalog(self, query='', limit=50):
        skills = table('skills')
        statement = select(skills.c.id, skills.c.code, skills.c.name_uz, skills.c.name_ru).where(skills.c.active.is_(True))
        if query:
            statement = statement.where(or_(skills.c.code.icontains(query, autoescape=True),
                skills.c.name_uz.icontains(query, autoescape=True), skills.c.name_ru.icontains(query, autoescape=True)))
        with transaction() as conn:
            return [dict(r) for r in conn.execute(statement.order_by(skills.c.code).limit(limit)).mappings()]


candidate_service = CandidateService()
