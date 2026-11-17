"""Security, contract, and confidentiality tests for Rating Appeal Submission (API-058 / CAP-028 / DB-067 / AC-025).

Verifies:
1. Canonical Contract ID API-058 and schema conformance (POST /api/v1/ratings/{id}/appeals).
2. Party to rating authority ("Baho tomoni" / AC-025): Target user and rater can appeal.
3. Unrelated third party is strictly rejected (403 Forbidden).
4. 14-day appeal window enforcement (AC-025 / RAT-05):
   - Appeal within 14 days of publication succeeds (201 Created).
   - Appeal after 14 days expires and is rejected (422 Unprocessable Entity).
5. Anti-duplication and idempotent replay:
   - Identical appeal replay returns existing appeal (200/201).
   - Conflicting pending appeal rejected (409 Conflict).
6. Disputed rating status updated to 'UNDER_APPEAL' and queued in moderation_cases (DB-078).
7. Aggregate recomputation: Disputed rating excluded; when count drops below 5 (n < 5),
   score is withheld (score: null, status: WITHHELD_INSUFFICIENT_SAMPLE) (AC-025).
8. Independent review resolution and reviewer conflict prevention (AC-025, AC-028).
9. Unauthenticated request rejected (401 Unauthorized).
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.api.dependencies import ActorContext
from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from app.services.user_ratings import user_ratings_service
from test_academic_admission import pending_http


def create_test_rubric(status: str = "ACTIVE") -> str:
    """Create an active rubric version with criteria summing to 100%."""
    rubric_id = str(uuid4())
    now_ts = now()
    with transaction() as conn:
        insert_row(
            conn,
            "rubric_versions",
            id=rubric_id,
            family="GENERAL_INTERNSHIP",
            version=1,
            status=status,
            scale_min=1,
            scale_max=5,
            published_at=now_ts,
        )
        insert_row(
            conn,
            "rubric_criteria",
            rubric_id=rubric_id,
            code="PUNCTUALITY",
            title="Punctuality and Attendance",
            weight=40,
            required=True,
        )
        insert_row(
            conn,
            "rubric_criteria",
            rubric_id=rubric_id,
            code="TECHNICAL_EXECUTION",
            title="Technical Skills and Execution",
            weight=60,
            required=True,
        )
    return rubric_id


def setup_completed_placement(client, identities, organization, status: str = "COMPLETED") -> dict:
    """Create a fully valid intake-proven placement and set final status."""
    f = pending_http(client, identities, organization)
    pid = f["placement"]["id"]
    if status != "PLANNED":
        with transaction() as conn:
            conn.execute(
                table("placements").update().where(table("placements").c.id == pid).values(status=status)
            )
        f["placement"]["status"] = status
    return f


def create_published_rating(
    placement_id: str,
    rater_id: str,
    target_user_id: str,
    rubric_id: str,
    days_ago: int = 2,
    score_punctuality: int = 4,
    score_technical: int = 5,
) -> tuple[str, str]:
    """Helper creating a published rating submission, revision, and scores."""
    now_ts = now()
    pub_ts = now_ts - timedelta(days=days_ago)
    sub_id = str(uuid4())
    rev_id = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn,
            "rating_submissions",
            id=sub_id,
            placement_id=placement_id,
            engagement_id=None,
            rubric_id=rubric_id,
            rater_id=rater_id,
            target_user_id=target_user_id,
            target_org_id=None,
            version=1,
            status="PUBLISHED",
            comment="Ijobiy amaliyot natijalari va mas'uliyat",
            submitted_at=pub_ts,
            publish_after=pub_ts,
        )
        insert_row(
            conn,
            "rating_revisions",
            id=rev_id,
            submission_id=sub_id,
            version=1,
            comment="Ijobiy amaliyot natijalari va mas'uliyat",
            submitted_at=pub_ts,
            rubric_snapshot={"version": 1},
        )
        t_crit = table("rubric_criteria")
        crit_rows = conn.execute(
            select(t_crit.c.id, t_crit.c.code).where(t_crit.c.rubric_id == rubric_id)
        ).mappings().all()

        for c in crit_rows:
            sc = score_punctuality if c["code"] == "PUNCTUALITY" else score_technical
            insert_row(
                conn,
                "rating_scores",
                rating_revision_id=rev_id,
                criterion_id=c["id"],
                score=sc,
                rubric_id=rubric_id,
            )

    return sub_id, rev_id


def test_rating_appeal_canonical_contract_and_schema(client, identities, organization):
    """API-058 / CAP-028: POST /api/v1/ratings/{id}/appeals returns 201 Created with canonical payload."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
    rubric_id = create_test_rubric()

    sub_id, rev_id = create_published_rating(
        placement_id=f["placement"]["id"],
        rater_id=owner["user_id"],
        target_user_id=candidate["user_id"],
        rubric_id=rubric_id,
        days_ago=3,
    )

    appeal_payload = {
        "reason": "Baholash faktik ma'lumotlarga to'g'ri kelmaydi va hisobotlar inobatga olinmagan.",
        "category": "FACTUAL_DISPUTE",
        "evidence_notes": "Kundalik yozuvlarim va amaliyot hisobotim to'liq topshirilgan.",
    }

    res = client.post(
        f"/api/v1/ratings/{sub_id}/appeals",
        json=appeal_payload,
        headers=candidate["headers"],
    )
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["contract_id"] == "API-058"
    assert data["status"] == "PENDING"
    assert data["rating_id"] == sub_id
    assert data["rating_revision_id"] == rev_id
    assert data["appellant_id"] == candidate["user_id"]
    assert data["disputed_submission_status"] == "UNDER_APPEAL"
    assert data["aggregate_recomputed"] is True
    assert "moderation_case_id" in data
    assert data["reason"] == appeal_payload["reason"]


def test_unrelated_third_party_appeal_rejected_403(client, identities, organization):
    """AC-025: Unrelated third party who is not a party to the rating cannot appeal (403 Forbidden)."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
    stranger = identities()  # Completely unrelated actor
    rubric_id = create_test_rubric()

    sub_id, _ = create_published_rating(
        placement_id=f["placement"]["id"],
        rater_id=owner["user_id"],
        target_user_id=candidate["user_id"],
        rubric_id=rubric_id,
        days_ago=1,
    )

    res = client.post(
        f"/api/v1/ratings/{sub_id}/appeals",
        json={"reason": "Begona foydalanuvchi sifatida e'tiroz bildirmoqdaman."},
        headers=stranger["headers"],
    )
    assert res.status_code == 403, res.text
    assert "RATING_APPEAL_FORBIDDEN" in res.text


def test_14_day_appeal_window_enforcement_expired_rejected(client, identities, organization):
    """AC-025 / RAT-05: Appeal submitted after 14 calendar days from publication is rejected (422)."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
    rubric_id = create_test_rubric()

    # Published 16 days ago (> 14 days)
    sub_id, _ = create_published_rating(
        placement_id=f["placement"]["id"],
        rater_id=owner["user_id"],
        target_user_id=candidate["user_id"],
        rubric_id=rubric_id,
        days_ago=16,
    )

    res = client.post(
        f"/api/v1/ratings/{sub_id}/appeals",
        json={"reason": "Muddati o'tgan e'tiroz sababi va dalillari bu yerda."},
        headers=candidate["headers"],
    )
    assert res.status_code == 422, res.text
    assert "RATING_APPEAL_WINDOW_EXPIRED" in res.text or "tugagan" in res.text.lower()


def test_duplicate_appeal_idempotent_replay(client, identities, organization):
    """AC-025: Submitting an identical appeal while pending returns idempotent replay."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
    rubric_id = create_test_rubric()

    sub_id, _ = create_published_rating(
        placement_id=f["placement"]["id"],
        rater_id=owner["user_id"],
        target_user_id=candidate["user_id"],
        rubric_id=rubric_id,
        days_ago=2,
    )

    payload = {"reason": "Ushbu baholashdagi mezonlar xato hisoblangan deb hisoblayman."}

    # First attempt
    res1 = client.post(f"/api/v1/ratings/{sub_id}/appeals", json=payload, headers=candidate["headers"])
    assert res1.status_code == 201, res1.text
    appeal_id = res1.json()["appeal_id"]

    # Replay identical attempt
    res2 = client.post(f"/api/v1/ratings/{sub_id}/appeals", json=payload, headers=candidate["headers"])
    assert res2.status_code in (200, 201), res2.text
    data2 = res2.json()
    assert data2["appeal_id"] == appeal_id
    assert data2["idempotent_replay"] is True


def test_conflicting_duplicate_appeal_rejected_409(client, identities, organization):
    """AC-025: Submitting a conflicting appeal with different reason while pending is rejected (409)."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
    rubric_id = create_test_rubric()

    sub_id, _ = create_published_rating(
        placement_id=f["placement"]["id"],
        rater_id=owner["user_id"],
        target_user_id=candidate["user_id"],
        rubric_id=rubric_id,
        days_ago=2,
    )

    # First attempt
    res1 = client.post(
        f"/api/v1/ratings/{sub_id}/appeals",
        json={"reason": "Birinchi asosli e'tiroz matni bu yerda ko'rsatilgan."},
        headers=candidate["headers"],
    )
    assert res1.status_code == 201, res1.text

    # Conflicting second attempt
    res2 = client.post(
        f"/api/v1/ratings/{sub_id}/appeals",
        json={"reason": "Mutlaqo boshqa sabab bilan ikkinchi ziddiyatli e'tiroz."},
        headers=candidate["headers"],
    )
    assert res2.status_code == 409, res2.text
    assert "APPEAL_ALREADY_PENDING" in res2.text


def test_aggregate_recomputation_n_less_than_5_withholding(client, identities, organization):
    """AC-025 / RAT-05: Disputed rating drops published sample below 5 (n=4 < 5); score is withheld."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    rubric_id = create_test_rubric()

    # Create 5 independent published ratings from 5 different raters
    sub_ids: list[str] = []
    for _ in range(5):
        rater_i = identities()
        s_id, _ = create_published_rating(
            placement_id=f["placement"]["id"],
            rater_id=rater_i["user_id"],
            target_user_id=candidate["user_id"],
            rubric_id=rubric_id,
            days_ago=3,
            score_punctuality=5,
            score_technical=5,
        )
        sub_ids.append(s_id)

    # Compute baseline aggregate
    with transaction() as conn:
        user_ratings_service.recompute_aggregate(
            conn,
            target_user_id=candidate["user_id"],
            rubric_id=rubric_id,
        )

    # Verify baseline: 5 ratings -> published score 5.0
    res_base = client.get("/api/v1/me/ratings", headers=candidate["headers"])
    assert res_base.status_code == 200, res_base.text
    base_agg = res_base.json()["aggregate"]
    assert base_agg["sample_size"] == 5
    assert base_agg["score"] == 5.0
    assert base_agg["score_status"] == "PUBLISHED"

    # Now candidate appeals 1 of the ratings
    appeal_target_sub_id = sub_ids[0]
    res_appeal = client.post(
        f"/api/v1/ratings/{appeal_target_sub_id}/appeals",
        json={"reason": "Ushbu bitta baholash bo'yicha nizoli holat yuzaga keldi va e'tiroz berildi."},
        headers=candidate["headers"],
    )
    assert res_appeal.status_code == 201, res_appeal.text

    # Re-fetch candidate's ratings view: sample drops to 4, score is withheld!
    res_after = client.get("/api/v1/me/ratings", headers=candidate["headers"])
    assert res_after.status_code == 200, res_after.text
    after_agg = res_after.json()["aggregate"]

    assert after_agg["sample_size"] == 4  # 5 - 1 disputed = 4
    assert after_agg["score"] is None  # n < 5 -> WITHHELD!
    assert after_agg["score_status"] == "WITHHELD_INSUFFICIENT_SAMPLE"
    assert "yashirilgan" in after_agg["explanation"].lower() or "withheld" in after_agg["explanation"].lower()


def test_appeal_resolution_by_independent_reviewer(client, identities, organization):
    """AC-025 / AC-028: Independent reviewer resolves appeal; updates submission status and recomputes."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
    rubric_id = create_test_rubric()

    sub_id, _ = create_published_rating(
        placement_id=f["placement"]["id"],
        rater_id=owner["user_id"],
        target_user_id=candidate["user_id"],
        rubric_id=rubric_id,
        days_ago=2,
    )

    # Submit appeal
    res = client.post(
        f"/api/v1/ratings/{sub_id}/appeals",
        json={"reason": "Baho noto'g'ri qo'yilgan deb hisoblayman va qayta tekshirishni so'rayman."},
        headers=candidate["headers"],
    )
    assert res.status_code == 201, res.text
    appeal_id = res.json()["appeal_id"]

    # Independent reviewer (not rater, not appellant)
    reviewer = identities("MODERATOR")
    reviewer_actor = ActorContext(
        user_id=reviewer["user_id"],
        session_id=reviewer["session_id"],
        roles=("MODERATOR",),
    )

    # Reviewer accepts the appeal
    resolve_res = user_ratings_service.resolve_rating_appeal(
        appeal_id=appeal_id,
        reviewer=reviewer_actor,
        decision="ACCEPTED",
        decision_notes="E'tiroz o'rganildi va asosli deb topildi; baho bekor qilindi.",
    )
    assert resolve_res["status"] == "RESOLVED"
    assert resolve_res["decision"] == "ACCEPTED"
    assert resolve_res["submission_status"] == "REVOKED"


def test_appeal_reviewer_conflict_self_review_rejected_403(client, identities, organization):
    """AC-025 / AC-028: Reviewer conflict: appellant or rater cannot resolve their own appeal (403)."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
    rubric_id = create_test_rubric()

    sub_id, _ = create_published_rating(
        placement_id=f["placement"]["id"],
        rater_id=owner["user_id"],
        target_user_id=candidate["user_id"],
        rubric_id=rubric_id,
        days_ago=2,
    )

    # Submit appeal
    res = client.post(
        f"/api/v1/ratings/{sub_id}/appeals",
        json={"reason": "O'zim bahoga e'tiroz bermoqdaman va ko'rib chiqilishini so'rayman."},
        headers=candidate["headers"],
    )
    assert res.status_code == 201, res.text
    appeal_id = res.json()["appeal_id"]

    # Appellant attempts to act as their own reviewer (self-review)
    appellant_actor = ActorContext(
        user_id=candidate["user_id"],
        session_id=candidate["session_id"],
        roles=("MODERATOR",),
    )

    with pytest.raises(Exception) as exc_info:
        user_ratings_service.resolve_rating_appeal(
            appeal_id=appeal_id,
            reviewer=appellant_actor,
            decision="ACCEPTED",
        )
    assert "APPEAL_REVIEWER_CONFLICT" in str(exc_info.value) or getattr(exc_info.value, "status_code", None) == 403


def test_unauthenticated_request_rejected_401(client):
    """Unauthenticated call to POST /api/v1/ratings/{id}/appeals is rejected (401 Unauthorized)."""
    random_id = str(uuid4())
    res = client.post(
        f"/api/v1/ratings/{random_id}/appeals",
        json={"reason": "Autentifikatsiyasiz e'tiroz berishga urinish."},
    )
    assert res.status_code == 401, res.text
