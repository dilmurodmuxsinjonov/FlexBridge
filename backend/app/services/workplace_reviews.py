"""Workplace Reviews & Mentor Review Queue Service.

Implements canonical contracts under CAP-021 and CAP-023:
- API-090: GET /api/v1/me/mentor-review-queue
- API-091: GET /api/v1/log-revisions/{revision}/workplace
- API-092: POST /api/v1/log-revisions/{revision}/workplace-reviews
"""

from __future__ import annotations

import base64
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, or_, select

from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.api.dependencies import ActorContext
from app.services.placements import get_row, insert_row

TASHKENT_TZ = timezone(timedelta(hours=5))


class WorkplaceReviewError(Exception):
    def __init__(self, code: str, message: str = "", status_code: int = 409, sqlstate: str = "23503"):
        super().__init__(message or code)
        self.code = code
        self.message = message or code
        self.status_code = status_code
        self.sqlstate = sqlstate


class WorkplaceReviewsService:
    def __init__(self) -> None:
        self.audit_store = AppendOnlyAuditStore()

    def _encode_cursor(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, separators=(",", ":"), default=str)
        return base64.urlsafe_b64encode(serialized.encode("utf-8")).decode("utf-8").rstrip("=")

    def _decode_cursor(self, cursor: str) -> dict[str, Any]:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            raw = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Cursor payload is not a JSON object")
            return data
        except Exception as exc:
            raise WorkplaceReviewError("INVALID_CURSOR", "Cursor decode failed", status_code=400) from exc

    def _resolve_mentor_assignment(
        self,
        conn: Any,
        placement_id: str | UUID,
        actor_user_id: str | UUID,
    ) -> dict[str, Any] | None:
        """Find active, accepted mentor assignment for given placement and user."""
        t_ma = table("mentor_assignments")
        t_proof = table("mentor_assignment_proofs")
        t_mem = table("org_memberships")

        # 1. Match via mentor_assignment_proofs
        stmt_proof = (
            select(t_ma)
            .select_from(t_ma.join(t_proof, t_proof.c.assignment_id == t_ma.c.id))
            .where(
                t_ma.c.placement_id == str(placement_id),
                t_proof.c.mentor_user_id == str(actor_user_id),
                t_ma.c.accepted_at.is_not(None),
                t_ma.c.revoked_at.is_(None),
            )
        )
        row = conn.execute(stmt_proof).mappings().first()
        if row:
            return dict(row)

        # 2. Match via org_memberships
        stmt_mem = (
            select(t_ma)
            .select_from(t_ma.join(t_mem, t_mem.c.id == t_ma.c.membership_id))
            .where(
                t_ma.c.placement_id == str(placement_id),
                t_mem.c.user_id == str(actor_user_id),
                t_ma.c.accepted_at.is_not(None),
                t_ma.c.revoked_at.is_(None),
            )
        )
        row_mem = conn.execute(stmt_mem).mappings().first()
        if row_mem:
            return dict(row_mem)

        return None

    def list_mentor_review_queue(
        self,
        *,
        actor: ActorContext,
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """API-090 (GET /api/v1/me/mentor-review-queue): Mentor review queue containing only own accepted assignments."""
        if not actor or not actor.user_id:
            raise WorkplaceReviewError("UNAUTHENTICATED", "Authentication required", status_code=401)

        limit = max(1, min(limit, 100))
        cursor_data = self._decode_cursor(cursor) if cursor else None

        with transaction() as conn:
            conn.execute(table("log_revisions").select().limit(0))  # read-committed

            t_ma = table("mentor_assignments")
            t_proof = table("mentor_assignment_proofs")
            t_mem = table("org_memberships")
            t_p = table("placements")
            t_dl = table("daily_logs")
            t_rev = table("log_revisions")
            t_cand = table("candidate_profiles")
            t_u = table("users")
            t_wlr = table("workplace_log_reviews")

            # 1. Gather all active accepted placement_ids for this mentor
            proof_assignments = select(t_ma.c.placement_id).select_from(
                t_ma.join(t_proof, t_proof.c.assignment_id == t_ma.c.id)
            ).where(
                t_proof.c.mentor_user_id == actor.user_id,
                t_ma.c.accepted_at.is_not(None),
                t_ma.c.revoked_at.is_(None),
            )

            mem_assignments = select(t_ma.c.placement_id).select_from(
                t_ma.join(t_mem, t_mem.c.id == t_ma.c.membership_id)
            ).where(
                t_mem.c.user_id == actor.user_id,
                t_ma.c.accepted_at.is_not(None),
                t_ma.c.revoked_at.is_(None),
            )

            mentor_placements_subquery = proof_assignments.union(mem_assignments).subquery()

            # 2. Query pending SUBMITTED daily logs for these placements
            query = (
                select(
                    t_rev.c.id.label("revision_id"),
                    t_rev.c.daily_log_id,
                    t_rev.c.revision,
                    t_rev.c.day_type,
                    t_rev.c.summary,
                    t_rev.c.total_minutes,
                    t_rev.c.status.label("revision_status"),
                    t_rev.c.submitted_at,
                    t_rev.c.author_id,
                    t_dl.c.placement_id,
                    t_dl.c.local_date,
                    t_p.c.candidate_id,
                    t_p.c.organization_id,
                    t_p.c.status.label("placement_status"),
                    t_cand.c.user_id.label("candidate_user_id"),
                    t_cand.c.headline.label("candidate_headline"),
                    t_u.c.display_name.label("candidate_full_name"),
                )
                .select_from(
                    t_rev.join(t_dl, t_dl.c.id == t_rev.c.daily_log_id)
                    .join(t_p, t_p.c.id == t_dl.c.placement_id)
                    .join(t_cand, t_cand.c.id == t_p.c.candidate_id)
                    .join(t_u, t_u.c.id == t_cand.c.user_id)
                )
                .where(
                    t_dl.c.placement_id.in_(select(mentor_placements_subquery)),
                    t_dl.c.current_revision_id == t_rev.c.id,
                    t_rev.c.status == "SUBMITTED",
                    t_p.c.status == "ACTIVE",
                    t_rev.c.id.not_in(select(t_wlr.c.revision_id)),
                )
            )

            # Cursor filter over (submitted_at ASC, revision_id ASC)
            if cursor_data:
                try:
                    c_submitted_at = datetime.fromisoformat(cursor_data["submitted_at"])
                    c_rev_id = str(UUID(cursor_data["revision_id"]))
                    query = query.where(
                        or_(
                            t_rev.c.submitted_at > c_submitted_at,
                            and_(
                                t_rev.c.submitted_at == c_submitted_at,
                                t_rev.c.id > c_rev_id,
                            ),
                        )
                    )
                except Exception as exc:
                    raise WorkplaceReviewError("INVALID_CURSOR", "Malformed cursor payload", status_code=400) from exc

            # Order by submitted_at ASC (oldest first for prompt escalation handling), id ASC
            query = query.order_by(t_rev.c.submitted_at.asc(), t_rev.c.id.asc()).limit(limit + 1)
            rows = conn.execute(query).mappings().all()

            has_more = len(rows) > limit
            items_rows = rows[:limit]

            current_time = now()
            items = []
            for r in items_rows:
                sub_at = r["submitted_at"]
                # 3 days escalation deadline (due_at)
                due_at = sub_at + timedelta(days=3) if sub_at else None
                is_escalated = (current_time > due_at) if due_at else False

                items.append({
                    "revision_id": str(r["revision_id"]),
                    "daily_log_id": str(r["daily_log_id"]),
                    "placement_id": str(r["placement_id"]),
                    "organization_id": str(r["organization_id"]),
                    "log_date": r["local_date"].isoformat() if r["local_date"] else None,
                    "day_type": r["day_type"],
                    "summary": r["summary"],
                    "total_minutes": r["total_minutes"],
                    "status": r["revision_status"],
                    "submitted_at": sub_at.isoformat() if sub_at else None,
                    "due_at": due_at.isoformat() if due_at else None,
                    "is_escalated": is_escalated,
                    "candidate": {
                        "id": str(r["candidate_id"]),
                        "user_id": str(r["candidate_user_id"]),
                        "full_name": r["candidate_full_name"],
                        "headline": r["candidate_headline"],
                    },
                })

            next_cursor = None
            if has_more and items:
                last_row = items_rows[-1]
                next_cursor = self._encode_cursor({
                    "submitted_at": last_row["submitted_at"].isoformat(),
                    "revision_id": str(last_row["revision_id"]),
                })

            return {
                "contract_id": "API-090",
                "items": items,
                "total": len(items),
                "next_cursor": next_cursor,
            }

    def get_workplace_log_revision_detail(
        self,
        *,
        revision_id: str | UUID,
        actor: ActorContext,
    ) -> dict[str, Any]:
        """API-091 (GET /api/v1/log-revisions/{revision}/workplace): Workplace view of daily log revision."""
        if not actor or not actor.user_id:
            raise WorkplaceReviewError("UNAUTHENTICATED", "Authentication required", status_code=401)

        try:
            rev_uid = str(UUID(str(revision_id)))
        except (ValueError, TypeError):
            raise WorkplaceReviewError("LOG_REVISION_NOT_FOUND", "Revision not found", status_code=404)

        with transaction() as conn:
            conn.execute(table("log_revisions").select().limit(0))

            t_rev = table("log_revisions")
            t_dl = table("daily_logs")
            t_p = table("placements")
            t_cand = table("candidate_profiles")
            t_u = table("users")
            t_te = table("log_task_entries")
            t_ev = table("log_evidence")
            t_wlr = table("workplace_log_reviews")
            t_terms = table("placement_terms")

            # 1. Retrieve revision and placement
            stmt = (
                select(
                    t_rev.c.id.label("revision_id"),
                    t_rev.c.daily_log_id,
                    t_rev.c.revision,
                    t_rev.c.terms_id,
                    t_rev.c.author_id,
                    t_rev.c.day_type,
                    t_rev.c.summary,
                    t_rev.c.total_minutes,
                    t_rev.c.status.label("revision_status"),
                    t_rev.c.submitted_at,
                    t_rev.c.created_at.label("revision_created_at"),
                    t_dl.c.placement_id,
                    t_dl.c.local_date,
                    t_p.c.organization_id,
                    t_p.c.candidate_id,
                    t_p.c.status.label("placement_status"),
                    t_cand.c.user_id.label("candidate_user_id"),
                    t_cand.c.headline.label("candidate_headline"),
                    t_u.c.display_name.label("candidate_full_name"),
                )
                .select_from(
                    t_rev.join(t_dl, t_dl.c.id == t_rev.c.daily_log_id)
                    .join(t_p, t_p.c.id == t_dl.c.placement_id)
                    .join(t_cand, t_cand.c.id == t_p.c.candidate_id)
                    .join(t_u, t_u.c.id == t_cand.c.user_id)
                )
                .where(t_rev.c.id == rev_uid)
            )
            row = conn.execute(stmt).mappings().first()
            if not row:
                raise WorkplaceReviewError("LOG_REVISION_NOT_FOUND", "Revision not found", status_code=404)

            # 2. Authorization check (IDOR protection)
            # Mentor assigned to placement OR organization owner/coordinator
            mentor_assignment = self._resolve_mentor_assignment(conn, row["placement_id"], actor.user_id)
            if not mentor_assignment:
                # Check if actor is OWNER or HOST_COORDINATOR of this organization
                t_mem = table("org_memberships")
                t_grants = table("org_role_grants")
                t_roles = table("role_catalog")
                staff_stmt = (
                    select(t_roles.c.code)
                    .select_from(
                        t_mem.join(t_grants, t_grants.c.membership_id == t_mem.c.id)
                        .join(t_roles, t_roles.c.id == t_grants.c.role_id)
                    )
                    .where(
                        t_mem.c.organization_id == row["organization_id"],
                        t_mem.c.user_id == actor.user_id,
                        t_mem.c.status == "ACTIVE",
                        t_mem.c.revoked_at.is_(None),
                        t_grants.c.revoked_at.is_(None),
                        t_roles.c.code.in_(["OWNER", "HOST_COORDINATOR"]),
                    )
                )
                staff_role = conn.execute(staff_stmt).scalar_one_or_none()
                if not staff_role:
                    # Uniform 404 IDOR anti-enumeration defense
                    raise WorkplaceReviewError("LOG_REVISION_NOT_FOUND", "Revision not found", status_code=404)

            # 3. Fetch task entries
            tasks_stmt = (
                select(
                    t_te.c.id.label("task_id"),
                    t_te.c.result_text,
                    t_te.c.minutes,
                    t_te.c.start_minute,
                    t_te.c.end_minute,
                )
                .where(t_te.c.revision_id == rev_uid)
                .order_by(t_te.c.start_minute.asc().nulls_last(), t_te.c.id.asc())
            )
            task_rows = conn.execute(tasks_stmt).mappings().all()

            task_ids = [r["task_id"] for r in task_rows]

            # 4. Fetch evidence, excluding ACADEMIC_ONLY
            evidence_map: dict[str, list[dict[str, Any]]] = {str(tid): [] for tid in task_ids}
            if task_ids:
                ev_stmt = (
                    select(
                        t_ev.c.id.label("evidence_id"),
                        t_ev.c.entry_id,
                        t_ev.c.file_id,
                        t_ev.c.visibility,
                        t_ev.c.created_at,
                    )
                    .where(
                        t_ev.c.entry_id.in_(task_ids),
                        t_ev.c.visibility.in_(["HOST_AND_ACADEMIC", "HOST_ONLY", "PUBLIC_EVIDENCE"]),
                    )
                    .order_by(t_ev.c.created_at.asc())
                )
                ev_rows = conn.execute(ev_stmt).mappings().all()
                for ev in ev_rows:
                    evidence_map[str(ev["entry_id"])].append({
                        "evidence_id": str(ev["evidence_id"]),
                        "file_id": str(ev["file_id"]),
                        "visibility": ev["visibility"],
                        "created_at": ev["created_at"].isoformat() if ev["created_at"] else None,
                    })

            tasks = []
            for tr in task_rows:
                tid_str = str(tr["task_id"])
                tasks.append({
                    "task_id": tid_str,
                    "title": tr["result_text"],
                    "minutes": tr["minutes"],
                    "start_minute": tr["start_minute"],
                    "end_minute": tr["end_minute"],
                    "evidence": evidence_map.get(tid_str, []),
                })

            # 5. Fetch terms details
            terms_info = None
            if row["terms_id"]:
                terms_row = conn.execute(
                    select(t_terms).where(t_terms.c.id == row["terms_id"])
                ).mappings().first()
                if terms_row:
                    terms_info = {
                        "terms_id": str(terms_row["id"]),
                        "daily_limit_minutes": terms_row.get("daily_limit_minutes", 480),
                        "weekly_limit_hours": terms_row.get("weekly_limit_hours", 40),
                    }

            # 6. Fetch existing review if already decided
            existing_review = None
            review_row = conn.execute(
                select(t_wlr).where(t_wlr.c.revision_id == rev_uid)
            ).mappings().first()
            if review_row:
                existing_review = {
                    "review_id": str(review_row["id"]),
                    "decision": review_row["decision"],
                    "comment": review_row["comment"],
                    "decided_at": review_row["decided_at"].isoformat() if review_row["decided_at"] else None,
                }

            sub_at = row["submitted_at"]
            due_at = sub_at + timedelta(days=3) if sub_at else None
            is_escalated = (now() > due_at) if due_at else False

            return {
                "contract_id": "API-091",
                "revision_id": str(row["revision_id"]),
                "daily_log_id": str(row["daily_log_id"]),
                "placement_id": str(row["placement_id"]),
                "organization_id": str(row["organization_id"]),
                "log_date": row["local_date"].isoformat() if row["local_date"] else None,
                "day_type": row["day_type"],
                "summary": row["summary"],
                "total_minutes": row["total_minutes"],
                "status": row["revision_status"],
                "submitted_at": sub_at.isoformat() if sub_at else None,
                "due_at": due_at.isoformat() if due_at else None,
                "is_escalated": is_escalated,
                "candidate": {
                    "id": str(row["candidate_id"]),
                    "user_id": str(row["candidate_user_id"]),
                    "full_name": row["candidate_full_name"],
                    "headline": row["candidate_headline"],
                },
                "terms": terms_info,
                "tasks": tasks,
                "existing_review": existing_review,
            }

    def submit_workplace_review(
        self,
        *,
        revision_id: str | UUID,
        decision: str,
        comment: str | None = None,
        actor: ActorContext,
    ) -> dict[str, Any]:
        """API-092 (POST /api/v1/log-revisions/{revision}/workplace-reviews): Submit workplace review decision."""
        if not actor or not actor.user_id:
            raise WorkplaceReviewError("UNAUTHENTICATED", "Authentication required", status_code=401)

        allowed_decisions = {"APPROVED", "CHANGES_REQUESTED", "REJECTED"}
        if decision not in allowed_decisions:
            raise WorkplaceReviewError(
                "INVALID_REVIEW_DECISION",
                f"Invalid decision '{decision}'. Allowed: {sorted(allowed_decisions)}",
                status_code=422,
            )

        try:
            rev_uid = str(UUID(str(revision_id)))
        except (ValueError, TypeError):
            raise WorkplaceReviewError("LOG_REVISION_NOT_FOUND", "Revision not found", status_code=404)

        with transaction() as conn:
            conn.execute(table("log_revisions").select().limit(0))

            t_rev = table("log_revisions")
            t_dl = table("daily_logs")
            t_p = table("placements")
            t_cand = table("candidate_profiles")
            t_wlr = table("workplace_log_reviews")

            # 1. Atomic row lock on revision, daily_log, and placement
            rev_stmt = (
                select(
                    t_rev.c.id.label("revision_id"),
                    t_rev.c.daily_log_id,
                    t_rev.c.revision,
                    t_rev.c.author_id,
                    t_rev.c.status.label("revision_status"),
                    t_dl.c.placement_id,
                    t_dl.c.current_revision_id,
                    t_dl.c.local_date,
                    t_p.c.organization_id,
                    t_p.c.candidate_id,
                    t_p.c.status.label("placement_status"),
                    t_cand.c.user_id.label("candidate_user_id"),
                )
                .select_from(
                    t_rev.join(t_dl, t_dl.c.id == t_rev.c.daily_log_id)
                    .join(t_p, t_p.c.id == t_dl.c.placement_id)
                    .join(t_cand, t_cand.c.id == t_p.c.candidate_id)
                )
                .where(t_rev.c.id == rev_uid)
                .with_for_update(of=(t_p, t_dl, t_rev))
            )
            row = conn.execute(rev_stmt).mappings().first()
            if not row:
                raise WorkplaceReviewError("LOG_REVISION_NOT_FOUND", "Revision not found", status_code=404)

            # 2. AC-028 / SEC-01 INVARIANT: Self-review strictly forbidden
            if str(row["candidate_user_id"]) == str(actor.user_id) or str(row["author_id"]) == str(actor.user_id):
                raise WorkplaceReviewError(
                    "SELF_REVIEW_FORBIDDEN",
                    "Candidate cannot review their own daily log",
                    status_code=403,
                )

            # 3. Role and Mentor Assignment check
            mentor_assignment = self._resolve_mentor_assignment(conn, row["placement_id"], actor.user_id)
            if not mentor_assignment:
                # Also allow active OWNER / HOST_COORDINATOR to review on behalf of the org
                t_mem = table("org_memberships")
                t_grants = table("org_role_grants")
                t_roles = table("role_catalog")
                staff_stmt = (
                    select(t_roles.c.code)
                    .select_from(
                        t_mem.join(t_grants, t_grants.c.membership_id == t_mem.c.id)
                        .join(t_roles, t_roles.c.id == t_grants.c.role_id)
                    )
                    .where(
                        t_mem.c.organization_id == row["organization_id"],
                        t_mem.c.user_id == actor.user_id,
                        t_mem.c.status == "ACTIVE",
                        t_mem.c.revoked_at.is_(None),
                        t_grants.c.revoked_at.is_(None),
                        t_roles.c.code.in_(["OWNER", "HOST_COORDINATOR"]),
                    )
                )
                staff_role = conn.execute(staff_stmt).scalar_one_or_none()
                if not staff_role:
                    # Anti-enumeration uniform 404
                    raise WorkplaceReviewError("LOG_REVISION_NOT_FOUND", "Revision not found", status_code=404)

            # 4. Placement must be active
            if row["placement_status"] != "ACTIVE":
                raise WorkplaceReviewError("ACTIVE_PLACEMENT_REQUIRED", "Placement is not active", status_code=409)

            # 5. Check if revision already has a decision in workplace_log_reviews
            existing_rev = conn.execute(
                select(t_wlr).where(t_wlr.c.revision_id == rev_uid).with_for_update()
            ).mappings().first()

            if existing_rev:
                # Idempotent match check
                if existing_rev["decision"] == decision:
                    return {
                        "contract_id": "API-092",
                        "id": str(existing_rev["id"]),
                        "revision_id": str(rev_uid),
                        "placement_id": str(row["placement_id"]),
                        "decision": decision,
                        "comment": existing_rev["comment"],
                        "status": row["revision_status"],
                        "decided_at": existing_rev["decided_at"].isoformat() if existing_rev["decided_at"] else None,
                    }
                raise WorkplaceReviewError(
                    "REVISION_ALREADY_REVIEWED",
                    f"Revision has already been reviewed with decision '{existing_rev['decision']}'",
                    status_code=409,
                )

            # 6. Revision must be in SUBMITTED status to accept a new review
            if row["revision_status"] != "SUBMITTED":
                if row["revision_status"] == "DRAFT":
                    raise WorkplaceReviewError(
                        "SUBMITTED_REVISION_REQUIRED",
                        "Draft daily logs cannot be reviewed until submitted",
                        status_code=409,
                    )
                raise WorkplaceReviewError(
                    "REVISION_NOT_SUBMITTED",
                    f"Cannot review revision in status '{row['revision_status']}'",
                    status_code=409,
                )

            # 7. Insert review record
            review_id = str(uuid4())
            decided_at = now()
            conn.execute(
                t_wlr.insert().values(
                    id=review_id,
                    created_at=decided_at,
                    updated_at=decided_at,
                    revision_id=rev_uid,
                    mentor_assignment_id=mentor_assignment["id"] if mentor_assignment else None,
                    decision=decision,
                    comment=comment,
                    decided_at=decided_at,
                    placement_id=row["placement_id"],
                )
            )

            # 8. Audit event in AppendOnlyAuditStore
            self.audit_store.append_audit_event(
                actor_id=actor.user_id,
                action="WORKPLACE_LOG_REVIEWED",
                entity_type="workplace_log_review",
                entity_id=review_id,
                metadata={
                    "decision": decision,
                    "placement_id": str(row["placement_id"]),
                    "revision_id": str(rev_uid),
                },
            )

            return {
                "contract_id": "API-092",
                "id": str(review_id),
                "revision_id": str(rev_uid),
                "placement_id": str(row["placement_id"]),
                "decision": decision,
                "comment": comment,
                "decided_at": decided_at.isoformat(),
            }


workplace_review_service = WorkplaceReviewsService()
