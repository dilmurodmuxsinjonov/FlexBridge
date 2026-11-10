"""User ratings view and evaluation service (API-057 / CAP-027 / DB-064 / AC-021..024).

Implements canonical `API-057` (`GET /api/v1/me/ratings`):
- Displays active rubric, sample size (n), and explicit explanation when score is withheld or unrated (AC-023).
- Implements n < 5 privacy threshold: score is withheld until at least 5 independent ratings are received (RAT-03).
- Implements bilateral double-blind anti-retaliation protection (14-day blind window or mutual submission, AC-024).
- Distinguishes new unrated user (unrated, score=null) from zero rating (AC-023).
- Surfaces authored submissions and eligible completed relations (AC-022).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import ActorContext, candidate_id_for
from app.db.storage import table, transaction
from app.services.authority import account_authority
from app.services.feature_flags import FeatureFlagService
from app.services.placements import PlacementScopeError


MIN_RATING_SAMPLE_SIZE = 5
BLIND_WINDOW_DAYS = 14


class RatingScopeError(PlacementScopeError):
    """Scoped exception for rating domain errors."""
    pass


class UserRatingsService:
    """Service handling personal rating summary, submissions, and eligibility."""

    def __init__(self, feature_flag_service: FeatureFlagService | None = None) -> None:
        self.feature_flag_service = feature_flag_service or FeatureFlagService()

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


user_ratings_service = UserRatingsService()
