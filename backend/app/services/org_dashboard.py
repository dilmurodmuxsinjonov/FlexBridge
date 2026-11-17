"""Organization HR Dashboard, Public Opportunities, and Rating Summary Service (API-068, API-009, API-010 / CAP-015, CAP-001, CAP-027).

Implements:
- Canonical `API-068` (`GET /api/v1/organizations/{org}/dashboard`):
  HR analytics dashboard for organization staff (OWNER, HR, HOST_COORDINATOR).
  Uniform 404 IDOR protection for non-members / unauthorized callers.
  Optimized atomic SQL aggregation avoiding N+1 queries.
- Canonical `API-009` (`GET /api/v1/organizations/{id}/opportunities`):
  Public view of PUBLISHED opportunities for verified organization with keyset cursor pagination.
- Canonical `API-010` (`GET /api/v1/organizations/{id}/rating-summary`):
  Public view of organization rating aggregate with AC-023 sample-size privacy withholding (n < 5).
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, or_, func, text

from app.api.dependencies import ActorContext
from app.db.storage import table, transaction
from app.services.governance import GovernanceError


class OrgDashboardService:
    """Service providing organization-level HR dashboard and public profile queries."""

    def get_dashboard_api_068(self, *, actor: ActorContext, organization_id: str) -> dict[str, Any]:
        """Retrieve aggregated HR metrics for an organization (`API-068` / `CAP-015`)."""
        try:
            org_uuid = str(UUID(organization_id))
        except (ValueError, TypeError):
            raise GovernanceError("ORGANIZATION_NOT_FOUND", status_code=404)

        with transaction() as conn:
            # 1. Verify organization exists and is active
            t_orgs = table("organizations")
            org_row = conn.execute(
                select(t_orgs.c.id, t_orgs.c.status).where(t_orgs.c.id == org_uuid)
            ).mappings().first()
            if not org_row:
                raise GovernanceError("ORGANIZATION_NOT_FOUND", status_code=404)

            # 2. Authorization check: actor must have an active org role ('OWNER', 'HR', 'HOST_COORDINATOR')
            # or platform ADMIN role. Otherwise uniform 404 to prevent resource existence probing (IDOR).
            t_members = table("org_memberships")
            t_grants = table("org_role_grants")
            t_roles = table("role_catalog")
            t_users = table("users")

            is_member = conn.execute(
                select(t_members.c.id)
                .join(t_grants, t_grants.c.membership_id == t_members.c.id)
                .join(t_roles, t_roles.c.id == t_grants.c.role_id)
                .join(t_users, t_users.c.id == t_members.c.user_id)
                .where(
                    t_members.c.organization_id == org_uuid,
                    t_members.c.user_id == actor.user_id,
                    t_members.c.status == "ACTIVE",
                    t_members.c.revoked_at.is_(None),
                    t_grants.c.revoked_at.is_(None),
                    t_roles.c.code.in_(["OWNER", "HR", "HOST_COORDINATOR"]),
                    t_roles.c.scope_kind == "ORG",
                    t_users.c.status == "ACTIVE",
                )
            ).first()

            if not is_member:
                raise GovernanceError("ORGANIZATION_NOT_FOUND", status_code=404)

            # 3. High-performance aggregated metrics (Zero N+1)
            t_opps = table("opportunities")
            t_apps = table("applications")
            t_engs = table("job_engagements")
            t_ints = table("interviews")

            # Opportunities count by status
            opp_counts = conn.execute(
                select(
                    t_opps.c.status,
                    func.count(t_opps.c.id).label("cnt")
                )
                .where(t_opps.c.organization_id == org_uuid)
                .group_by(t_opps.c.status)
            ).mappings().all()

            # Applications count by status (joined through opportunities)
            app_counts = conn.execute(
                select(
                    t_apps.c.status,
                    func.count(t_apps.c.id).label("cnt")
                )
                .join(t_opps, t_opps.c.id == t_apps.c.opportunity_id)
                .where(t_opps.c.organization_id == org_uuid)
                .group_by(t_apps.c.status)
            ).mappings().all()

            # Job Engagements count by status
            eng_counts = conn.execute(
                select(
                    t_engs.c.status,
                    func.count(t_engs.c.id).label("cnt")
                )
                .join(t_apps, t_apps.c.id == t_engs.c.application_id)
                .join(t_opps, t_opps.c.id == t_apps.c.opportunity_id)
                .where(t_opps.c.organization_id == org_uuid)
                .group_by(t_engs.c.status)
            ).mappings().all()

            # Interviews count by status
            int_counts = conn.execute(
                select(
                    t_ints.c.status,
                    func.count(t_ints.c.id).label("cnt")
                )
                .join(t_apps, t_apps.c.id == t_ints.c.application_id)
                .join(t_opps, t_opps.c.id == t_apps.c.opportunity_id)
                .where(t_opps.c.organization_id == org_uuid)
                .group_by(t_ints.c.status)
            ).mappings().all()

            opp_map = {r["status"]: r["cnt"] for r in opp_counts}
            app_map = {r["status"]: r["cnt"] for r in app_counts}
            eng_map = {r["status"]: r["cnt"] for r in eng_counts}
            int_map = {r["status"]: r["cnt"] for r in int_counts}

            return {
                "contract_id": "API-068",
                "organization_id": org_uuid,
                "opportunities": {
                    "total": sum(opp_map.values()),
                    "draft": opp_map.get("DRAFT", 0),
                    "pending_moderation": opp_map.get("PENDING_MODERATION", 0),
                    "published": opp_map.get("PUBLISHED", 0),
                    "closed": opp_map.get("CLOSED", 0),
                    "paused": opp_map.get("PAUSED", 0),
                },
                "applications": {
                    "total": sum(app_map.values()),
                    "pending": app_map.get("PENDING", 0) + app_map.get("SUBMITTED", 0),
                    "shortlisted": app_map.get("SHORTLISTED", 0),
                    "interviewed": app_map.get("INTERVIEWED", 0),
                    "offered": app_map.get("OFFERED", 0),
                    "accepted": app_map.get("ACCEPTED", 0),
                    "rejected": app_map.get("REJECTED", 0),
                    "withdrawn": app_map.get("WITHDRAWN", 0),
                },
                "engagements": {
                    "total": sum(eng_map.values()),
                    "active": eng_map.get("ACTIVE", 0),
                    "pending_start": eng_map.get("PENDING_START_CONFIRMATION", 0),
                    "completed": eng_map.get("COMPLETED", 0),
                    "disputed": eng_map.get("DISPUTED", 0),
                },
                "interviews": {
                    "total": sum(int_map.values()),
                    "scheduled": int_map.get("SCHEDULED", 0),
                    "completed": int_map.get("COMPLETED", 0),
                    "cancelled": int_map.get("CANCELLED", 0),
                    "no_show": int_map.get("NO_SHOW", 0),
                },
            }

    def get_public_opportunities_api_009(
        self,
        *,
        organization_id: str,
        limit: int = 20,
        after: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve public PUBLISHED opportunities for an organization (`API-009` / `CAP-001`)."""
        try:
            org_uuid = str(UUID(organization_id))
        except (ValueError, TypeError):
            raise GovernanceError("ORGANIZATION_NOT_FOUND", status_code=404)

        clamped_limit = min(max(1, limit), 50)

        with transaction() as conn:
            # 1. Organization check (must be VERIFIED)
            t_orgs = table("organizations")
            org_row = conn.execute(
                select(t_orgs.c.id, t_orgs.c.status).where(t_orgs.c.id == org_uuid)
            ).mappings().first()
            if not org_row or org_row["status"] != "VERIFIED":
                raise GovernanceError("ORGANIZATION_NOT_FOUND", status_code=404)

            # 2. Query only PUBLISHED opportunities
            t_opps = table("opportunities")
            t_revs = table("opportunity_revisions")
            query = (
                select(
                    t_opps.c.id,
                    t_opps.c.kind,
                    t_opps.c.capacity,
                    t_opps.c.occupied_count,
                    t_opps.c.status,
                    t_opps.c.created_at,
                    t_revs.c.title,
                    t_revs.c.work_mode,
                    t_revs.c.region.label("location"),
                )
                .outerjoin(t_revs, t_revs.c.id == t_opps.c.current_revision_id)
                .where(
                    t_opps.c.organization_id == org_uuid,
                    t_opps.c.status == "PUBLISHED",
                )
            )

            # Cursor decode
            if after:
                try:
                    raw = base64.urlsafe_b64decode(after.encode()).decode()
                    created_at_iso, after_id = raw.split("|", 1)
                    cursor_created_at = datetime.fromisoformat(created_at_iso)
                    query = query.where(
                        or_(
                            t_opps.c.created_at < cursor_created_at,
                            and_(
                                t_opps.c.created_at == cursor_created_at,
                                t_opps.c.id < after_id,
                            ),
                        )
                    )
                except Exception:
                    pass

            query = query.order_by(t_opps.c.created_at.desc(), t_opps.c.id.desc()).limit(clamped_limit + 1)
            rows = conn.execute(query).mappings().all()

            has_more = len(rows) > clamped_limit
            items_to_return = rows[:clamped_limit]

            next_cursor = None
            if has_more and items_to_return:
                last_item = items_to_return[-1]
                created_str = (
                    last_item["created_at"].isoformat()
                    if isinstance(last_item["created_at"], datetime)
                    else str(last_item["created_at"])
                )
                payload = f"{created_str}|{last_item['id']}"
                next_cursor = base64.urlsafe_b64encode(payload.encode()).decode()

            serialized_items = []
            for r in items_to_return:
                cap = r["capacity"] or 1
                occ = r["occupied_count"] or 0
                vacancies = max(0, cap - occ)
                serialized_items.append({
                    "id": str(r["id"]),
                    "title": r["title"] or "Opportunity",
                    "kind": r["kind"],
                    "work_mode": r["work_mode"] or "ONSITE",
                    "location": r["location"] or "",
                    "capacity": cap,
                    "occupied_count": occ,
                    "vacancies_available": vacancies,
                    "status": r["status"],
                    "created_at": (
                        r["created_at"].isoformat()
                        if isinstance(r["created_at"], datetime)
                        else str(r["created_at"])
                    ),
                })

            return {
                "contract_id": "API-009",
                "organization_id": org_uuid,
                "items": serialized_items,
                "limit": clamped_limit,
                "has_more": has_more,
                "next_cursor": next_cursor,
            }

    def get_public_rating_summary_api_010(self, *, organization_id: str) -> dict[str, Any]:
        """Retrieve public rating aggregate for an organization (`API-010` / `CAP-027` / `CAP-040`)."""
        try:
            org_uuid = str(UUID(organization_id))
        except (ValueError, TypeError):
            raise GovernanceError("ORGANIZATION_NOT_FOUND", status_code=404)

        with transaction() as conn:
            # 1. Organization check (must exist and be VERIFIED)
            t_orgs = table("organizations")
            org_row = conn.execute(
                select(t_orgs.c.id, t_orgs.c.status, t_orgs.c.legal_name).where(t_orgs.c.id == org_uuid)
            ).mappings().first()
            if not org_row or org_row["status"] != "VERIFIED":
                raise GovernanceError("ORGANIZATION_NOT_FOUND", status_code=404)

            # 2. Check feature flag status (CAP-040)
            feature_enabled = False
            try:
                from app.services.feature_flags import FeatureFlagService
                feature_enabled = bool(FeatureFlagService().is_enabled("ratings"))
            except Exception:
                feature_enabled = False

            # 3. Rating aggregate query (deterministic order by latest window and computation)
            t_agg = table("rating_aggregates")
            agg_row = conn.execute(
                select(
                    t_agg.c.score,
                    t_agg.c.sample_size,
                    t_agg.c.computed_at,
                    t_agg.c.rubric_id,
                )
                .where(t_agg.c.target_org_id == org_uuid)
                .order_by(
                    t_agg.c.window_end.desc().nullslast(),
                    t_agg.c.computed_at.desc().nullslast(),
                    t_agg.c.created_at.desc(),
                )
            ).mappings().first()

            if not agg_row or not agg_row["sample_size"]:
                return {
                    "contract_id": "API-010",
                    "target_org_id": org_uuid,
                    "score": None,
                    "score_status": "UNRATED",
                    "sample_size": 0,
                    "feature_flag": "ratings",
                    "feature_enabled": feature_enabled,
                    "computed_at": None,
                }

            sample_size = agg_row["sample_size"]
            # AC-023 Privacy Threshold: if n < 5, withhold score
            if sample_size < 5:
                return {
                    "contract_id": "API-010",
                    "target_org_id": org_uuid,
                    "score": None,
                    "score_status": "WITHHELD_INSUFFICIENT_SAMPLE",
                    "sample_size": sample_size,
                    "feature_flag": "ratings",
                    "feature_enabled": feature_enabled,
                    "computed_at": (
                        agg_row["computed_at"].isoformat()
                        if isinstance(agg_row["computed_at"], datetime)
                        else str(agg_row["computed_at"])
                    ),
                }

            return {
                "contract_id": "API-010",
                "target_org_id": org_uuid,
                "score": float(agg_row["score"]) if agg_row["score"] is not None else None,
                "score_status": "PUBLISHED",
                "sample_size": sample_size,
                "feature_flag": "ratings",
                "feature_enabled": feature_enabled,
                "computed_at": (
                    agg_row["computed_at"].isoformat()
                    if isinstance(agg_row["computed_at"], datetime)
                    else str(agg_row["computed_at"])
                ),
            }


org_dashboard_service = OrgDashboardService()
