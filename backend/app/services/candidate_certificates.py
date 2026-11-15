"""Candidate certificates service with antivirus verification (API-026 / CAP-002)."""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.api.dependencies import ActorContext, candidate_id_for
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.services.auth import AuthError
from app.services.authority import account_authority

audit = AppendOnlyAuditStore()


class CandidateCertificatesService:
    def list_certificates(
        self,
        actor: ActorContext,
        limit: int = 50,
        after_id: str | None = None,
    ) -> dict[str, Any]:
        with transaction() as conn:
            cand_id = candidate_id_for(actor)
            account_authority(conn, actor)

            t_cert = table('candidate_certificates')
            t_files = table('files')

            query = (
                select(
                    t_cert,
                    t_files.c.filename.label('file_name'),
                    t_files.c.scan_status.label('file_scan_status'),
                )
                .select_from(t_cert.outerjoin(t_files, t_files.c.id == t_cert.c.file_id))
                .where(t_cert.c.candidate_id == cand_id)
            )

            if after_id:
                after_row = conn.execute(
                    select(t_cert.c.issue_date).where(t_cert.c.id == after_id)
                ).first()
                if after_row:
                    query = query.where(t_cert.c.issue_date < after_row[0])

            query = query.order_by(t_cert.c.issue_date.desc(), t_cert.c.created_at.desc()).limit(min(limit, 100))
            rows = conn.execute(query).mappings().all()

            count_query = select(t_cert.c.id).where(t_cert.c.candidate_id == cand_id)
            total = len(conn.execute(count_query).all())

            items = []
            for r in rows:
                item = dict(r)
                if item.get('issue_date') and hasattr(item['issue_date'], 'isoformat'):
                    item['issue_date'] = item['issue_date'].isoformat()
                if item.get('expiry_date') and hasattr(item['expiry_date'], 'isoformat'):
                    item['expiry_date'] = item['expiry_date'].isoformat()
                if item.get('created_at') and hasattr(item['created_at'], 'isoformat'):
                    item['created_at'] = item['created_at'].isoformat()
                if item.get('updated_at') and hasattr(item['updated_at'], 'isoformat'):
                    item['updated_at'] = item['updated_at'].isoformat()
                items.append(item)

            return {
                'contract_id': 'API-026-CERT-LIST',
                'items': items,
                'total': total,
            }

    def create_certificate(
        self,
        actor: ActorContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with transaction() as conn:
            cand_id = candidate_id_for(actor)
            account_authority(conn, actor)

            title = str(payload.get('title', '')).strip()
            if not 2 <= len(title) <= 200:
                raise AuthError('INVALID_CERTIFICATE_TITLE', 'Title must be 2-200 characters', 422)

            issuer = str(payload.get('issuer', '')).strip()
            if not 2 <= len(issuer) <= 200:
                raise AuthError('INVALID_CERTIFICATE_ISSUER', 'Issuer must be 2-200 characters', 422)

            issue_date = payload.get('issue_date')
            if not issue_date:
                raise AuthError('INVALID_ISSUE_DATE', 'Issue date is required', 422)

            expiry_date = payload.get('expiry_date')
            if expiry_date and str(expiry_date) < str(issue_date):
                raise AuthError('INVALID_DATE_RANGE', 'Expiry date must be greater than or equal to issue date', 422)

            file_id = payload.get('file_id')
            file_name = None
            if file_id is not None:
                files = table('files')
                f_row = conn.execute(
                    select(files).where(files.c.id == str(file_id))
                ).mappings().first()

                if not f_row:
                    raise AuthError('FILE_NOT_FOUND', 'File not found', 404)

                # Strict file ownership check (Anti-IDOR)
                if str(f_row['owner_user_id']) != str(actor.user_id):
                    raise AuthError('FILE_ACCESS_DENIED', 'Cannot attach file owned by another user', 403)

                # Antivirus and quarantine pipeline check
                if f_row.get('deleted_at') or f_row.get('scan_status') != 'CLEAN':
                    raise AuthError('CERTIFICATE_FILE_NOT_CLEAN', 'Certificate file must be scanned and CLEAN', 409)

                file_name = f_row.get('filename')

            cert_id = str(uuid4())
            ts = now()
            conn.execute(
                table('candidate_certificates').insert().values(
                    id=cert_id,
                    created_at=ts,
                    updated_at=ts,
                    candidate_id=cand_id,
                    title=title,
                    issuer=issuer,
                    issue_date=issue_date,
                    expiry_date=expiry_date,
                    credential_id=payload.get('credential_id'),
                    credential_url=payload.get('credential_url'),
                    file_id=str(file_id) if file_id else None,
                    verification_case_id=payload.get('verification_case_id'),
                )
            )

            audit.append_audit_event(
                actor_id=actor.user_id,
                action='CANDIDATE_CERTIFICATE_ADDED',
                entity_type='candidate_certificate',
                entity_id=cert_id,
                metadata={'candidate_id': cand_id, 'title': title, 'issuer': issuer},
            )

            return {
                'id': cert_id,
                'candidate_id': cand_id,
                'title': title,
                'issuer': issuer,
                'issue_date': str(issue_date),
                'expiry_date': str(expiry_date) if expiry_date else None,
                'credential_id': payload.get('credential_id'),
                'credential_url': payload.get('credential_url'),
                'file_id': str(file_id) if file_id else None,
                'file_name': file_name,
                'created_at': ts.isoformat(),
                'updated_at': ts.isoformat(),
            }

    def delete_certificate(self, actor: ActorContext, cert_id: str) -> None:
        with transaction() as conn:
            cand_id = candidate_id_for(actor)
            account_authority(conn, actor)

            t_cert = table('candidate_certificates')
            existing = conn.execute(
                select(t_cert).where(t_cert.c.id == cert_id)
            ).mappings().first()

            if not existing:
                raise AuthError('CERTIFICATE_NOT_FOUND', 'Certificate not found', 404)

            # IDOR defense: Certificate must belong to caller's candidate_id
            if str(existing['candidate_id']) != cand_id:
                raise AuthError('CERTIFICATE_ACCESS_DENIED', 'Cannot delete certificate belonging to another candidate', 403)

            conn.execute(t_cert.delete().where(t_cert.c.id == cert_id))

            audit.append_audit_event(
                actor_id=actor.user_id,
                action='CANDIDATE_CERTIFICATE_DELETED',
                entity_type='candidate_certificate',
                entity_id=cert_id,
                metadata={'candidate_id': cand_id},
            )


candidate_certificates_service = CandidateCertificatesService()
