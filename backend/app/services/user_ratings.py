"""User ratings view and evaluation service (API-057 / API-058 / CAP-027 / CAP-028 / DB-064 / DB-067 / AC-021..025).

Implements canonical `API-057` (`GET /api/v1/me/ratings`) and `API-058` (`POST /api/v1/ratings/{id}/appeals`):
- Displays active rubric, sample size (n), and explicit explanation when score is withheld or unrated (AC-023).
- Implements n < 5 privacy threshold: score is withheld until at least 5 independent ratings are received (RAT-03).
- Implements bilateral double-blind anti-retaliation protection (14-day blind window or mutual submission, AC-024).
- Distinguishes new unrated user (unrated, score=null) from zero rating (AC-023).
- Surfaces authored submissions and eligible completed relations (AC-022).
- Enforces 14-day appeal window from publication, independent reviewer assignment, anti-duplication, and aggregate recomputation (AC-025, RAT-05).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import ActorContext, candidate_id_for
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import table, transaction
from app.services.authority import account_authority
from app.services.feature_flags import FeatureFlagService
from app.services.placements import PlacementScopeError, insert_row


MIN_RATING_SAMPLE_SIZE = 5
BLIND_WINDOW_DAYS = 14
APPEAL_WINDOW_DAYS = 14


class RatingScopeError(PlacementScopeError):
    """Scoped exception for rating domain errors."""
    pass


class UserRatingsService:
    """Service handling personal rating summary, submissions, eligibility, and appeals."""

    def __init__(
        self,
        feature_flag_service: FeatureFlagService | None = None,
        audit_store: AppendOnlyAuditStore | None = None,
    ) -> None:
        self.feature_flag_service = feature_flag_service or FeatureFlagService()
        self.audit_store = audit_store or AppendOnlyAuditStore()

    def get_my_ratings_api_057(
        self,
        *,
        actor: ActorContext,
    ) -> dict[str, Any]:
        """Retrieve the authenticated actor's rating summary, received ratings, and given ratings."""
        with transaction() as conn:
            # 1. Verify authenticated actor authority and active status
            account_authority(conn, actor)

            # 2. Check feature flag status
            feature_enabled = False
            try:
                feature_enabled = bool(self.feature_flag_service.is_enabled('ratings'))
            except Exception:
                feature_enabled = False

            now_utc = datetime.now(timezone.utc)
            user_id = actor.user_id

            # 3. Retrieve rating aggregate for the user (target_user_id)
            t_agg = table('rating_aggregates')
            agg_row = conn.execute(
                select(
                    t_agg.c.id,
                    t_agg.c.sample_size,
                    t_agg.c.score,
                    t_agg.c.window_start,
                    t_agg.c.window_end,
                    t_agg.c.computed_at,
                    t_agg.c.rubric_id,
                ).where(t_agg.c.target_user_id == user_id)
            ).mappings().first()

            if agg_row:
                sample_size = agg_row['sample_size']
                raw_score = agg_row['score']
                rubric_id_str = str(agg_row['rubric_id']) if agg_row['rubric_id'] else None
                window_start = agg_row['window_start'].isoformat() if agg_row['window_start'] else None
                window_end = agg_row['window_end'].isoformat() if agg_row['window_end'] else None
                computed_at = agg_row['computed_at'].astimezone(timezone.utc).isoformat() if agg_row['computed_at'] else None

                if sample_size == 0:
                    score = None
                    score_status = 'UNRATED'
                    explanation = 'Yangi foydalanuvchi: hali baholar mavjud emas (baho 0 emas, baholanmagan / unrated, AC-023).'
                elif sample_size < MIN_RATING_SAMPLE_SIZE:
                    score = None
                    score_status = 'WITHHELD_INSUFFICIENT_SAMPLE'
                    explanation = (
                        f'Kam baholar soni (n = {sample_size} < {MIN_RATING_SAMPLE_SIZE}): '
                        'foydalanuvchi anonimligi va ishonchliligini taminlash uchun umumiy ball yashirilgan (AC-023).'
                    )
                else:
                    score = float(raw_score) if raw_score is not None else None
                    score_status = 'PUBLISHED' if score is not None else 'COMPUTATION_PENDING'
                    explanation = f'Umumiy ball {sample_size} ta mustaqil baholash asosida hisoblangan va tasdiqlangan.'
            else:
                sample_size = 0
                score = None
                score_status = 'UNRATED'
                explanation = 'Yangi foydalanuvchi: hali baholar mavjud emas (baho 0 emas, baholanmagan / unrated, AC-023).'
                rubric_id_str = None
                window_start = None
                window_end = None
                computed_at = None

            # 4. Retrieve received rating submissions (target_user_id == actor.user_id)
            t_sub = table('rating_submissions')
            received_rows = conn.execute(
                select(
                    t_sub.c.id,
                    t_sub.c.placement_id,
                    t_sub.c.engagement_id,
                    t_sub.c.rubric_id,
                    t_sub.c.rater_id,
                    t_sub.c.version,
                    t_sub.c.status,
                    t_sub.c.comment,
                    t_sub.c.submitted_at,
                    t_sub.c.publish_after,
                )
                .where(t_sub.c.target_user_id == user_id)
                .order_by(t_sub.c.submitted_at.desc().nullslast())
            ).mappings().all()

            submissions_received: list[dict[str, Any]] = []
            for r in received_rows:
                publish_after = r['publish_after']
                is_blind = publish_after is not None and publish_after > now_utc

                if is_blind:
                    # AC-024: Bilateral double-blind window active; redact rater details and comment to prevent retaliation
                    submissions_received.append({
                        'id': str(r['id']),
                        'rubric_id': str(r['rubric_id']),
                        'status': 'BLINDED_PENDING_WINDOW',
                        'blind_window_active': True,
                        'publish_after': publish_after.astimezone(timezone.utc).isoformat(),
                        'comment': None,
                        'rater_id': None,
                        'message': '14-kunlik himoya davrida baholovchi shaxsi va tafsilotlari maxfiy saqlanadi (AC-024).',
                    })
                else:
                    submissions_received.append({
                        'id': str(r['id']),
                        'placement_id': str(r['placement_id']) if r['placement_id'] else None,
                        'engagement_id': str(r['engagement_id']) if r['engagement_id'] else None,
                        'rubric_id': str(r['rubric_id']),
                        'status': r['status'],
                        'blind_window_active': False,
                        'comment': r['comment'],
                        'submitted_at': r['submitted_at'].astimezone(timezone.utc).isoformat() if r['submitted_at'] else None,
                        'publish_after': publish_after.astimezone(timezone.utc).isoformat() if publish_after else None,
                    })

            # 5. Retrieve authored rating submissions (rater_id == actor.user_id)
            given_rows = conn.execute(
                select(
                    t_sub.c.id,
                    t_sub.c.placement_id,
                    t_sub.c.engagement_id,
                    t_sub.c.rubric_id,
                    t_sub.c.target_user_id,
                    t_sub.c.target_org_id,
                    t_sub.c.version,
                    t_sub.c.status,
                    t_sub.c.comment,
                    t_sub.c.submitted_at,
                    t_sub.c.publish_after,
                )
                .where(t_sub.c.rater_id == user_id)
                .order_by(t_sub.c.submitted_at.desc().nullslast())
            ).mappings().all()

            submissions_given: list[dict[str, Any]] = []
            for g in given_rows:
                submissions_given.append({
                    'id': str(g['id']),
                    'placement_id': str(g['placement_id']) if g['placement_id'] else None,
                    'engagement_id': str(g['engagement_id']) if g['engagement_id'] else None,
                    'rubric_id': str(g['rubric_id']),
                    'target_user_id': str(g['target_user_id']) if g['target_user_id'] else None,
                    'target_org_id': str(g['target_org_id']) if g['target_org_id'] else None,
                    'version': g['version'],
                    'status': g['status'],
                    'comment': g['comment'],
                    'submitted_at': g['submitted_at'].astimezone(timezone.utc).isoformat() if g['submitted_at'] else None,
                    'publish_after': g['publish_after'].astimezone(timezone.utc).isoformat() if g['publish_after'] else None,
                })

            # 6. Retrieve eligible completed relations (AC-022: only completed relation participants)
            eligible_relations: list[dict[str, Any]] = []
            cand_id = candidate_id_for(actor)
            if cand_id:
                t_p = table('placements')
                p_rows = conn.execute(
                    select(
                        t_p.c.id,
                        t_p.c.organization_id,
                        t_p.c.status,
                        t_p.c.start_date,
                        t_p.c.end_date,
                    ).where(
                        t_p.c.candidate_id == cand_id,
                        t_p.c.status.in_(['COMPLETED', 'CLOSED']),
                    )
                ).mappings().all()
                for pr in p_rows:
                    eligible_relations.append({
                        'relation_type': 'PLACEMENT',
                        'relation_id': str(pr['id']),
                        'role': 'CANDIDATE',
                        'status': pr['status'],
                        'organization_id': str(pr['organization_id']),
                        'start_date': pr['start_date'].isoformat() if pr['start_date'] else None,
                        'end_date': pr['end_date'].isoformat() if pr['end_date'] else None,
                    })

            # 7. Active rubrics projection
            t_rub = table('rubric_versions')
            t_crit = table('rubric_criteria')
            rubrics = conn.execute(
                select(
                    t_rub.c.id,
                    t_rub.c.family,
                    t_rub.c.version,
                    t_rub.c.scale_min,
                    t_rub.c.scale_max,
                ).where(t_rub.c.status == 'ACTIVE')
            ).mappings().all()

            available_rubrics: list[dict[str, Any]] = []
            for rub in rubrics:
                criteria = conn.execute(
                    select(
                        t_crit.c.id,
                        t_crit.c.code,
                        t_crit.c.title,
                        t_crit.c.weight,
                        t_crit.c.required,
                    ).where(t_crit.c.rubric_id == rub['id'])
                    .order_by(t_crit.c.code)
                ).mappings().all()

                available_rubrics.append({
                    'id': str(rub['id']),
                    'family': rub['family'],
                    'version': rub['version'],
                    'scale_min': rub['scale_min'],
                    'scale_max': rub['scale_max'],
                    'criteria': [
                        {
                            'id': str(c['id']),
                            'code': c['code'],
                            'title': c['title'],
                            'weight': c['weight'],
                            'required': c['required'],
                        }
                        for c in criteria
                    ],
                })

            return {
                'contract_id': 'API-057',
                'target_user_id': str(user_id),
                'feature_enabled': feature_enabled,
                'feature_flag': 'ratings',
                'aggregate': {
                    'sample_size': sample_size,
                    'score': score,
                    'score_status': score_status,
                    'explanation': explanation,
                    'window_start': window_start,
                    'window_end': window_end,
                    'computed_at': computed_at,
                    'rubric_id': rubric_id_str,
                },
                'submissions_received': submissions_received,
                'submissions_given': submissions_given,
                'eligible_relations': eligible_relations,
                'available_rubrics': available_rubrics,
            }

    def submit_rating_appeal_api_058(
        self,
        *,
        rating_id: str,
        actor: ActorContext,
        reason: str,
        category: str = "FACTUAL_DISPUTE",
        evidence_notes: str | None = None,
    ) -> dict[str, Any]:
        """Submit a formal rating appeal (API-058 / CAP-028 / DB-067 / AC-025).

        Invariants:
        1. Authenticated actor must be a party to the rating (target_user, rater, or target_org member).
        2. Must be submitted within 14 calendar days of publication (AC-025 / RAT-05).
        3. Prevents duplicate pending appeals for the same rating revision.
        4. Rating marked as 'UNDER_APPEAL' and queued in moderation_cases (DB-078).
        5. Rating aggregate recalculated to exclude the disputed rating during dispute (AC-025).
        6. Independent reviewer queue: reviewer cannot be appellant or rater (AC-028).
        """
        clean_reason = reason.strip() if isinstance(reason, str) else ""
        if len(clean_reason) < 10 or len(clean_reason) > 4000:
            raise RatingScopeError(
                "APPEAL_REASON_INVALID",
                "E'tiroz sababi kamida 10 va ko'pi bilan 4000 belgidan iborat bo'lishi shart",
                status_code=422,
                sqlstate="22000",
            )

        now_utc = datetime.now(timezone.utc)
        user_id = actor.user_id

        with transaction() as conn:
            # 1. Verify actor authority
            account_authority(conn, actor)

            # 2. Resolve target rating submission and revision
            t_sub = table("rating_submissions")
            t_rev = table("rating_revisions")

            sub = conn.execute(
                select(t_sub).where(t_sub.c.id == rating_id)
            ).mappings().first()

            if not sub:
                # Check if rating_id is a rating_revisions.id
                rev = conn.execute(
                    select(t_rev).where(t_rev.c.id == rating_id)
                ).mappings().first()
                if rev:
                    sub = conn.execute(
                        select(t_sub).where(t_sub.c.id == rev["submission_id"])
                    ).mappings().first()
                    latest_revision = rev
                else:
                    raise RatingScopeError(
                        "RATING_NOT_FOUND",
                        "Baholash yozuvi topilmadi",
                        status_code=404,
                        sqlstate="02000",
                    )
            else:
                latest_revision = conn.execute(
                    select(t_rev)
                    .where(t_rev.c.submission_id == sub["id"])
                    .order_by(t_rev.c.version.desc())
                ).mappings().first()

            if not latest_revision:
                raise RatingScopeError(
                    "RATING_REVISION_NOT_FOUND",
                    "Baholash tahriri topilmadi",
                    status_code=404,
                    sqlstate="02000",
                )

            # 3. Verify actor is a party to the rating ("Baho tomoni" / AC-025)
            is_party = False
            if sub["target_user_id"] and str(sub["target_user_id"]) == str(user_id):
                is_party = True
            elif sub["rater_id"] and str(sub["rater_id"]) == str(user_id):
                is_party = True
            elif sub["target_org_id"]:
                t_mem = table("org_memberships")
                mem = conn.execute(
                    select(t_mem.c.role).where(
                        t_mem.c.organization_id == sub["target_org_id"],
                        t_mem.c.user_id == user_id,
                        t_mem.c.status == "ACTIVE",
                    )
                ).mappings().first()
                if mem and mem["role"] in ("OWNER", "HR", "HOST_COORDINATOR", "ADMIN"):
                    is_party = True

            if not is_party:
                actor_roles = getattr(actor, "roles", []) or []
                if any(r in ("MODERATOR", "ADMIN", "SUPPORT") for r in actor_roles):
                    is_party = True

            if not is_party:
                raise RatingScopeError(
                    "RATING_APPEAL_FORBIDDEN",
                    "Faqat baholash tomonlari yoki vakolatli shaxslar e'tiroz bera oladi (AC-025)",
                    status_code=403,
                    sqlstate="42501",
                )

            # 4. Check 14-day appeal window (AC-025 / RAT-05)
            published_at = sub.get("published_at")
            publish_after = sub.get("publish_after")
            submitted_at = sub.get("submitted_at")

            if published_at:
                base_time = published_at
            elif publish_after and now_utc >= publish_after:
                base_time = publish_after
            elif submitted_at:
                base_time = submitted_at
            else:
                base_time = sub["created_at"]

            if base_time.tzinfo is None:
                base_time = base_time.replace(tzinfo=timezone.utc)

            appeal_deadline = base_time + timedelta(days=APPEAL_WINDOW_DAYS)
            if now_utc > appeal_deadline:
                raise RatingScopeError(
                    "RATING_APPEAL_WINDOW_EXPIRED",
                    "14-kunlik e'tiroz bildirish muddati tugagan (AC-025)",
                    status_code=422,
                    sqlstate="22000",
                )

            # 5. Check duplicate pending appeal
            t_app = table("rating_appeals")
            existing = conn.execute(
                select(t_app).where(
                    t_app.c.rating_revision_id == latest_revision["id"],
                    t_app.c.appellant_id == user_id,
                    t_app.c.status.in_(("PENDING", "OPEN", "UNDER_REVIEW")),
                )
            ).mappings().first()

            if existing:
                if existing["reason"].strip() == clean_reason:
                    return {
                        "contract_id": "API-058",
                        "appeal_id": str(existing["id"]),
                        "rating_id": str(sub["id"]),
                        "rating_revision_id": str(latest_revision["id"]),
                        "appellant_id": str(user_id),
                        "status": existing["status"],
                        "reason": existing["reason"],
                        "category": category,
                        "created_at": existing["created_at"].astimezone(timezone.utc).isoformat(),
                        "idempotent_replay": True,
                        "aggregate_recomputed": True,
                        "disputed_submission_status": sub["status"],
                    }
                else:
                    raise RatingScopeError(
                        "APPEAL_ALREADY_PENDING",
                        "Ushbu baholash bo'yicha e'tiroz allaqachon ko'rib chiqilmoqda (AC-025)",
                        status_code=409,
                        sqlstate="23505",
                    )

            # 6. Record appeal in rating_appeals (DB-067)
            appeal_id = str(uuid4())
            insert_row(
                conn,
                "rating_appeals",
                id=appeal_id,
                rating_revision_id=latest_revision["id"],
                appellant_id=user_id,
                reason=clean_reason,
                status="PENDING",
                reviewer_id=None,
                decision=None,
                resolved_at=None,
            )

            # 7. Queue in moderation_cases (DB-078)
            case_id = str(uuid4())
            insert_row(
                conn,
                "moderation_cases",
                id=case_id,
                reporter_id=user_id,
                rating_id=sub["id"],
                category=category,
                status="PENDING",
                severity="NORMAL",
                due_at=now_utc + timedelta(days=14),
            )

            # 8. Update rating submission status to 'UNDER_APPEAL'
            conn.execute(
                t_sub.update()
                .where(t_sub.c.id == sub["id"])
                .values(status="UNDER_APPEAL", updated_at=now_utc)
            )

            # 9. Recalculate aggregate score excluding disputed rating (AC-025)
            agg_result = self.recompute_aggregate(
                conn,
                target_user_id=sub["target_user_id"],
                target_org_id=sub["target_org_id"],
                rubric_id=sub["rubric_id"],
            )

        # 10. Audit event
        self.audit_store.append_audit_event(
            actor_id=user_id,
            action="RATING_APPEAL_SUBMITTED",
            entity_type="rating_appeal",
            entity_id=appeal_id,
            metadata={
                "rating_id": str(sub["id"]),
                "rating_revision_id": str(latest_revision["id"]),
                "reason": clean_reason,
                "category": category,
                "evidence_notes": evidence_notes,
                "case_id": case_id,
            },
        )

        return {
            "contract_id": "API-058",
            "appeal_id": appeal_id,
            "rating_id": str(sub["id"]),
            "rating_revision_id": str(latest_revision["id"]),
            "appellant_id": str(user_id),
            "status": "PENDING",
            "reason": clean_reason,
            "category": category,
            "moderation_case_id": case_id,
            "created_at": now_utc.isoformat(),
            "idempotent_replay": False,
            "aggregate_recomputed": True,
            "aggregate_summary": agg_result,
            "disputed_submission_status": "UNDER_APPEAL",
        }

    def recompute_aggregate(
        self,
        conn,
        *,
        target_user_id: str | None = None,
        target_org_id: str | None = None,
        rubric_id: str,
    ) -> dict[str, Any]:
        """Recalculate published rating aggregate excluding disputed ratings (AC-025 / RAT-05)."""
        t_sub = table("rating_submissions")
        t_rev = table("rating_revisions")
        t_sco = table("rating_scores")
        t_crit = table("rubric_criteria")
        t_agg = table("rating_aggregates")
        now_utc = datetime.now(timezone.utc)

        cond = [
            t_sub.c.rubric_id == rubric_id,
            t_sub.c.status.notin_(("UNDER_APPEAL", "DISPUTED", "REVOKED", "DISMISSED")),
        ]
        if target_user_id:
            cond.append(t_sub.c.target_user_id == target_user_id)
        elif target_org_id:
            cond.append(t_sub.c.target_org_id == target_org_id)
        else:
            return {"sample_size": 0, "score": None, "score_status": "UNRATED"}

        valid_subs = conn.execute(
            select(t_sub.c.id, t_sub.c.publish_after).where(and_(*cond))
        ).mappings().all()

        eligible_sub_ids = [
            s["id"] for s in valid_subs
            if s["publish_after"] is None or s["publish_after"] <= now_utc
        ]

        composite_scores: list[float] = []
        for sub_id in eligible_sub_ids:
            latest_rev = conn.execute(
                select(t_rev.c.id)
                .where(t_rev.c.submission_id == sub_id)
                .order_by(t_rev.c.version.desc())
            ).mappings().first()
            if not latest_rev:
                continue

            scores_rows = conn.execute(
                select(t_sco.c.score, t_crit.c.weight)
                .join(t_crit, t_crit.c.id == t_sco.c.criterion_id)
                .where(t_sco.c.rating_revision_id == latest_rev["id"])
            ).mappings().all()

            if not scores_rows:
                continue

            total_weight = sum(r["weight"] for r in scores_rows)
            weighted_sum = sum(r["score"] * r["weight"] for r in scores_rows)
            if total_weight > 0:
                composite_scores.append(weighted_sum / total_weight)

        sample_size = len(composite_scores)
        if sample_size >= MIN_RATING_SAMPLE_SIZE:
            final_score = round(sum(composite_scores) / sample_size, 2)
            score_status = "PUBLISHED"
        elif sample_size > 0:
            final_score = None
            score_status = "WITHHELD_INSUFFICIENT_SAMPLE"
        else:
            final_score = None
            score_status = "UNRATED"

        # Update or insert into rating_aggregates
        agg_where = [t_agg.c.rubric_id == rubric_id]
        if target_user_id:
            agg_where.append(t_agg.c.target_user_id == target_user_id)
        else:
            agg_where.append(t_agg.c.target_org_id == target_org_id)

        existing_agg = conn.execute(select(t_agg).where(and_(*agg_where))).mappings().first()

        window_today = now_utc.date()
        window_start = window_today - timedelta(days=90)

        if existing_agg:
            conn.execute(
                t_agg.update()
                .where(t_agg.c.id == existing_agg["id"])
                .values(
                    sample_size=sample_size,
                    score=final_score,
                    computed_at=now_utc,
                    updated_at=now_utc,
                )
            )
            agg_id = existing_agg["id"]
        else:
            agg_id = str(uuid4())
            insert_row(
                conn,
                "rating_aggregates",
                id=agg_id,
                target_user_id=target_user_id,
                target_org_id=target_org_id,
                rubric_id=rubric_id,
                sample_size=sample_size,
                score=final_score,
                window_start=window_start,
                window_end=window_today,
                computed_at=now_utc,
            )

        return {
            "aggregate_id": str(agg_id),
            "sample_size": sample_size,
            "score": final_score,
            "score_status": score_status,
        }

    def resolve_rating_appeal(
        self,
        *,
        appeal_id: str,
        reviewer: ActorContext,
        decision: str,
        decision_notes: str | None = None,
    ) -> dict[str, Any]:
        """Resolve a rating appeal with conflict-free independent review (AC-025 / AC-028)."""
        decision_clean = decision.upper().strip()
        if decision_clean not in ("ACCEPTED", "DISMISSED", "REJECTED"):
            raise RatingScopeError(
                "INVALID_APPEAL_DECISION",
                "Qaror faqat ACCEPTED yoki DISMISSED bo'lishi mumkin",
                status_code=422,
                sqlstate="22000",
            )

        now_utc = datetime.now(timezone.utc)

        with transaction() as conn:
            account_authority(conn, reviewer)
            t_app = table("rating_appeals")
            t_rev = table("rating_revisions")
            t_sub = table("rating_submissions")

            appeal = conn.execute(
                select(t_app).where(t_app.c.id == appeal_id).with_for_update()
            ).mappings().first()
            if not appeal:
                raise RatingScopeError("APPEAL_NOT_FOUND", "E'tiroz topilmadi", status_code=404, sqlstate="02000")

            if appeal["status"] == "RESOLVED":
                raise RatingScopeError("APPEAL_ALREADY_RESOLVED", "E'tiroz allaqachon ko'rib chiqilgan", status_code=409, sqlstate="23505")

            rev = conn.execute(select(t_rev).where(t_rev.c.id == appeal["rating_revision_id"])).mappings().first()
            sub = conn.execute(select(t_sub).where(t_sub.c.id == rev["submission_id"])).mappings().first()

            # Reviewer conflict check: Reviewer cannot be appellant or rater (AC-028 / AC-025)
            reviewer_id = str(reviewer.user_id)
            if reviewer_id in (str(appeal["appellant_id"]), str(sub["rater_id"])):
                raise RatingScopeError(
                    "APPEAL_REVIEWER_CONFLICT",
                    "Mustaqil ko'rib chiquvchi o'z e'tirozi yoki o'z bahosini ko'rib chiqa olmaydi (AC-025, AC-028)",
                    status_code=403,
                    sqlstate="42501",
                )

            new_status = "REVOKED" if decision_clean == "ACCEPTED" else "PUBLISHED"
            conn.execute(
                t_sub.update().where(t_sub.c.id == sub["id"]).values(status=new_status, updated_at=now_utc)
            )

            conn.execute(
                t_app.update()
                .where(t_app.c.id == appeal["id"])
                .values(
                    status="RESOLVED",
                    reviewer_id=reviewer.user_id,
                    decision=decision_clean,
                    resolved_at=now_utc,
                    updated_at=now_utc,
                )
            )

            # Update linked moderation_case
            t_case = table("moderation_cases")
            conn.execute(
                t_case.update()
                .where(
                    t_case.c.rating_id == sub["id"],
                    t_case.c.category == "RATING_APPEAL",
                )
                .values(
                    status="RESOLVED",
                    decision=decision_clean,
                    decided_at=now_utc,
                    assigned_to_id=reviewer.user_id,
                    updated_at=now_utc,
                )
            )

            agg_result = self.recompute_aggregate(
                conn,
                target_user_id=sub["target_user_id"],
                target_org_id=sub["target_org_id"],
                rubric_id=sub["rubric_id"],
            )

        self.audit_store.append_audit_event(
            actor_id=reviewer.user_id,
            action="RATING_APPEAL_RESOLVED",
            entity_type="rating_appeal",
            entity_id=appeal_id,
            metadata={
                "decision": decision_clean,
                "decision_notes": decision_notes,
                "rating_id": str(sub["id"]),
                "submission_status": new_status,
            },
        )

        return {
            "contract_id": "API-058",
            "appeal_id": str(appeal_id),
            "status": "RESOLVED",
            "decision": decision_clean,
            "reviewer_id": reviewer_id,
            "submission_status": new_status,
            "resolved_at": now_utc.astimezone(timezone.utc).isoformat(),
            "aggregate_summary": agg_result,
        }


user_ratings_service = UserRatingsService()
