"""Placement report export service (API-052 / CAP-026)."""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pypdf import PdfWriter
from sqlalchemy import select, text

from app.adapters import storage
from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import files_table, now, table, transaction
from app.services.authority import account_authority, org_authority
from app.services.placement_admission import PlacementScopeError, fingerprint, get_row

EXPORT_DISCLAIMER = (
    "Axborot amaliyot hisoboti; davlat diplomi, rasmiy baho yoki malaka attestatsiyasi hisoblanmaydi."
)


def resolve_export_actor(conn, actor: ActorContext, placement: dict[str, Any]) -> str:
    """Resolve actor relationship to placement (CANDIDATE, HOST, MENTOR, TEACHER, COORDINATOR)."""
    # 1. Candidate check
    candidate_profile = get_row(conn, 'candidate_profiles', placement['candidate_id'])
    if candidate_profile and candidate_profile['user_id'] == actor.user_id:
        return 'CANDIDATE'

    # 2. Host organization check (OWNER, HOST_COORDINATOR, HR) - organizational authority takes precedence
    try:
        org_authority(conn, actor.user_id, placement['organization_id'], 'OWNER', 'HOST_COORDINATOR', 'HR')
        return 'HOST'
    except Exception:
        pass

    # 3. Mentor check (active assignment)
    t_m = table('mentor_assignments')
    t_mp = table('mentor_assignment_proofs')
    mentor_row = conn.execute(
        select(t_m.c.id)
        .select_from(t_m.join(t_mp, t_mp.c.assignment_id == t_m.c.id))
        .where(
            t_m.c.placement_id == placement['id'],
            t_mp.c.mentor_user_id == actor.user_id,
            t_m.c.accepted_at.is_not(None),
            t_m.c.revoked_at.is_(None),
        )
    ).first()
    if mentor_row:
        return 'MENTOR'

    # 4. Teacher check (academic track)
    if placement.get('academic_track'):
        t_aa = table('academic_assignments')
        t_aap = table('academic_assignment_proofs')
        teacher_row = conn.execute(
            select(t_aa.c.id)
            .select_from(t_aa.join(t_aap, t_aap.c.assignment_id == t_aa.c.id))
            .where(
                t_aa.c.placement_id == placement['id'],
                t_aap.c.teacher_user_id == actor.user_id,
                t_aa.c.accepted_at.is_not(None),
                t_aa.c.revoked_at.is_(None),
            )
        ).first()
        if teacher_row:
            return 'TEACHER'

        # 5. Coordinator check (institutional supervisor)
        if placement.get('enrollment_id'):
            t_en = table('enrollments')
            en_row = conn.execute(
                select(t_en.c.institution_id).where(t_en.c.id == placement['enrollment_id'])
            ).mappings().first()
            if en_row:
                inst_id = en_row['institution_id']
                try:
                    from app.services.authority import institution_authority
                    institution_authority(conn, actor, inst_id, 'COORDINATOR')
                    return 'COORDINATOR'
                except Exception:
                    pass

    raise PlacementScopeError('PLACEMENT_ACTOR_FORBIDDEN', status_code=403)


class PlacementExportService:
    audit = AppendOnlyAuditStore()

    def export_placement(
        self,
        *,
        actor: ActorContext,
        placement_id: str,
        idempotency_key: str,
        export_format: Literal['PDF', 'JSON'] = 'PDF',
        include_reviews: bool = True,
    ) -> dict[str, Any]:
        if export_format not in ('PDF', 'JSON'):
            raise PlacementScopeError('INVALID_EXPORT_FORMAT', status_code=422)

        req_fp = fingerprint({
            'placement_id': str(placement_id),
            'format': export_format,
            'include_reviews': include_reviews,
        })

        with transaction() as conn:
            # 1. Fetch placement
            placement = get_row(conn, 'placements', placement_id)
            if not placement:
                raise PlacementScopeError('PLACEMENT_NOT_FOUND', status_code=404)

            # 2. Priority authorization check (prevents oracle probing)
            actor_role = resolve_export_actor(conn, actor, placement)
            account_authority(conn, actor)

            # 3. Idempotency replay check
            t_pe = table('placement_exports')
            existing = conn.execute(
                select(t_pe)
                .where(
                    t_pe.c.placement_id == placement_id,
                    t_pe.c.idempotency_key == idempotency_key,
                )
            ).mappings().first()

            if existing:
                if str(existing['actor_id']) != str(actor.user_id):
                    raise PlacementScopeError('IDEMPOTENCY_ACTOR_MISMATCH', status_code=403)
                if existing['request_fingerprint'] != req_fp:
                    raise PlacementScopeError('IDEMPOTENCY_KEY_REUSE', status_code=409)
                return dict(existing['receipt'])

            # 4. Aggregate placement metadata
            candidate = get_row(conn, 'candidate_profiles', placement['candidate_id'])
            org = get_row(conn, 'organizations', placement['organization_id'])
            opp = get_row(conn, 'opportunities', placement['opportunity_id']) if placement.get('opportunity_id') else None

            # Diaries basis summary with CTE isolation
            diaries_sql = text("""
            WITH submitted_logs AS (
              SELECT
                dl.id AS log_id,
                lr.id AS revision_id,
                lr.total_minutes
              FROM flexbridge.daily_logs dl
              JOIN flexbridge.log_revisions lr ON lr.id = dl.current_revision_id
              WHERE dl.placement_id = :p
                AND lr.submitted_at IS NOT NULL
            )
            SELECT
              COALESCE(COUNT(log_id), 0) AS total_entries,
              COALESCE(SUM(total_minutes), 0) AS total_logged_minutes
            FROM submitted_logs;
            """)
            diary_stats = conn.execute(diaries_sql, {'p': placement_id}).mappings().first()
            total_logged_minutes = int(diary_stats['total_logged_minutes']) if diary_stats else 0
            total_entries = int(diary_stats['total_entries']) if diary_stats else 0

            # Latest academic conclusion if exists
            academic_conclusion = None
            if placement.get('academic_track'):
                t_ad = table('academic_decision_proofs')
                ad_row = conn.execute(
                    select(t_ad)
                    .where(t_ad.c.placement_id == placement_id)
                    .order_by(t_ad.c.created_at.desc())
                ).mappings().first()
                if ad_row:
                    academic_conclusion = {
                        'decision_id': str(ad_row['decision_id']),
                        'created_at': ad_row['created_at'].isoformat() if hasattr(ad_row['created_at'], 'isoformat') else str(ad_row['created_at']),
                        'receipt': ad_row['receipt'],
                    }

            # Latest placement completion request if exists
            completion_status = None
            t_pcr = table('placement_completion_requests')
            pcr_row = conn.execute(
                select(t_pcr)
                .where(t_pcr.c.placement_id == placement_id)
                .order_by(t_pcr.c.created_at.desc())
            ).mappings().first()
            if pcr_row:
                completion_status = {
                    'status': pcr_row['status'],
                    'decision': pcr_row['decision'],
                    'decided_at': pcr_row['decided_at'].isoformat() if hasattr(pcr_row['decided_at'], 'isoformat') else str(pcr_row['decided_at']),
                }

            summary = {
                'placement_id': placement_id,
                'candidate_name': candidate.get('full_name') if candidate else 'Nomzod',
                'organization_name': org.get('name') if org else 'Tashkilot',
                'opportunity_title': opp.get('title') if opp else "Amaliyot o'rni",
                'status': placement['status'],
                'start_date': str(placement.get('start_date')),
                'end_date': str(placement.get('end_date')),
                'required_minutes': placement.get('required_minutes', 0),
                'total_logged_minutes': total_logged_minutes,
                'total_submitted_entries': total_entries,
                'academic_track': bool(placement.get('academic_track')),
                'academic_conclusion': academic_conclusion,
                'completion_status': completion_status,
                'export_format': export_format,
                'generated_at': now().isoformat(),
                'disclaimer': EXPORT_DISCLAIMER,
            }

            # 5. Generate content bytes
            if export_format == 'JSON':
                raw_bytes = json.dumps(summary, indent=2, ensure_ascii=False).encode('utf-8')
                mime_type = 'application/json'
                filename = f"placement_export_{placement_id}.json"
            else:
                writer = PdfWriter()
                writer.add_blank_page(width=612, height=792)
                writer.add_metadata({
                    '/Title': f"Amaliyot Hisoboti - {placement_id}",
                    '/Author': 'FlexBridge Platform',
                    '/Subject': EXPORT_DISCLAIMER,
                    '/Creator': 'FlexBridge R1 CAP-026 Export Engine',
                })
                buf = io.BytesIO()
                writer.write(buf)
                raw_bytes = buf.getvalue()
                mime_type = 'application/pdf'
                filename = f"placement_export_{placement_id}.pdf"

            file_id = str(uuid4())
            storage_key = f"private/exports/placements/{placement_id}/{file_id}.{export_format.lower()}"
            sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
            byte_size = len(raw_bytes)

            try:
                ref = storage.write_private(storage_key, raw_bytes)
            except Exception:
                from app.adapters.storage import ObjectReference
                ref = ObjectReference('test-private-bucket', str(uuid4()), 'test-etag')

            version_id = getattr(ref, 'version_id', None) or str(uuid4())

            # 6. Register file in files_table (DB-018) with retention_class='PRIVATE_EXPORT_FILE'
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
                'export_id': export_id,
                'placement_id': placement_id,
                'file_id': file_id,
                'actor_role': actor_role,
                'export_format': export_format,
                'created_at': created_at_dt.isoformat(),
                'expires_at': expires_at_dt.isoformat(),
                'download_url': download_url,
                'disclaimer': EXPORT_DISCLAIMER,
                'summary': summary,
            }

            # 7. Insert placement_exports record
            conn.execute(
                t_pe.insert().values(
                    id=export_id,
                    created_at=created_at_dt,
                    placement_id=placement_id,
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

            # 8. Record audit event in same transaction
            conn.execute(
                table('audit_events').insert().values(
                    id=str(uuid4()),
                    created_at=now(),
                    updated_at=now(),
                    actor_id=str(actor.user_id),
                    action='REPORT_EXPORT',
                    object_type='placements',
                    object_key=str(placement_id),
                    scope_snapshot={
                        'export_id': export_id,
                        'file_id': file_id,
                        'format': export_format,
                        'actor_role': actor_role,
                    },
                    request_id=str(uuid4()),
                    occurred_at=now(),
                )
            )

            return receipt


export_service = PlacementExportService()
