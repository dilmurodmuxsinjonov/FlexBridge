"""Security, contract, and confidentiality tests for Personal Ratings View (API-057 / CAP-027 / DB-064 / AC-021..024).

Verifies:
1. Canonical Contract ID API-057 and schema conformance.
2. New unrated user returns score=None, status="UNRATED", and clear distinction from 0.0 (AC-023).
3. Low rating count (n < 5) strictly withholds score: status="WITHHELD_INSUFFICIENT_SAMPLE" (AC-023).
4. Sufficient rating count (n >= 5) reveals published aggregate score (AC-023).
5. Bilateral double-blind protection: 14-day window active masks rater identity and comment (AC-024).
6. Bilateral double-blind window elapsed: unblinded submission details revealed (AC-024).
7. Authored submissions surfaced in submissions_given.
8. Eligible completed relations surfaced in eligible_relations (AC-022).
9. Active rubric versions and weighted criteria projected.
10. Feature flag status reflected accurately (default locked/off in R1).
11. Unauthenticated request rejected (401 Unauthorized).
"""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_academic_admission import pending_http


def create_test_rubric(status: str = "ACTIVE") -> str:
    """Create a test rubric version with criteria summing to 100%."""
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


def test_unrated_user_returns_score_null_and_unrated_status(client, identities):
    """AC-023: A new user with no ratings receives score: null and status: UNRATED (not 0.0)."""
    user = identities()

    res = client.get("/api/v1/me/ratings", headers=user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["contract_id"] == "API-057"
    assert data["target_user_id"] == user["user_id"]
    assert data["feature_flag"] == "ratings"
    assert data["feature_enabled"] is False  # Locked to false in R1

    agg = data["aggregate"]
    assert agg["sample_size"] == 0
    assert agg["score"] is None
    assert agg["score_status"] == "UNRATED"
    assert "unrated" in agg["explanation"].lower() or "baholanmagan" in agg["explanation"].lower()


def test_low_count_user_withholds_score(client, identities):
    """AC-023: When n < 5, aggregate score is withheld from the response to protect rater privacy."""
    user = identities()
    rubric_id = create_test_rubric()
    now_ts = now()

    with transaction() as conn:
        insert_row(
            conn,
            "rating_aggregates",
            target_user_id=user["user_id"],
            target_org_id=None,
            rubric_id=rubric_id,
            sample_size=3,  # n < 5
            score=4.75,
            window_start=now_ts.date() - timedelta(days=30),
            window_end=now_ts.date(),
            computed_at=now_ts,
        )

    res = client.get("/api/v1/me/ratings", headers=user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    agg = data["aggregate"]
    assert agg["sample_size"] == 3
    assert agg["score"] is None  # Strictly withheld!
    assert agg["score_status"] == "WITHHELD_INSUFFICIENT_SAMPLE"
    assert "n = 3 < 5" in agg["explanation"]
    assert "AC-023" in agg["explanation"]


def test_sufficient_count_user_reveals_published_score(client, identities):
    """AC-023: Once n >= 5 independent ratings are received, published aggregate score is revealed."""
    user = identities()
    rubric_id = create_test_rubric()
    now_ts = now()

    with transaction() as conn:
        insert_row(
            conn,
            "rating_aggregates",
            target_user_id=user["user_id"],
            target_org_id=None,
            rubric_id=rubric_id,
            sample_size=5,  # n >= 5 threshold met
            score=4.85,
            window_start=now_ts.date() - timedelta(days=60),
            window_end=now_ts.date(),
            computed_at=now_ts,
        )

    res = client.get("/api/v1/me/ratings", headers=user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    agg = data["aggregate"]
    assert agg["sample_size"] == 5
    assert agg["score"] == 4.85  # Revealed!
    assert agg["score_status"] == "PUBLISHED"
    assert agg["rubric_id"] == rubric_id


def test_bilateral_double_blind_protection_active(client, identities, organization):
    """AC-024: Bilateral double-blind protection masks rater identity and comment during 14-day window."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    target_user = f["candidate"]
    rater_user = f["owner"]
    rubric_id = create_test_rubric()
    now_ts = now()

    # Rater submits rating with publish_after = now + 14 days
    publish_after_ts = now_ts + timedelta(days=14)
    sub_id = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn,
            "rating_submissions",
            id=sub_id,
            placement_id=f["placement"]["id"],
            engagement_id=None,
            rubric_id=rubric_id,
            rater_id=rater_user["user_id"],
            target_user_id=target_user["user_id"],
            target_org_id=None,
            version=1,
            status="SUBMITTED",
            comment="Ajoyib natija va mas'uliyat",
            submitted_at=now_ts,
            publish_after=publish_after_ts,
        )

    res = client.get("/api/v1/me/ratings", headers=target_user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    received = data["submissions_received"]
    assert len(received) == 1
    sub = received[0]

    assert sub["id"] == sub_id
    assert sub["status"] == "BLINDED_PENDING_WINDOW"
    assert sub["blind_window_active"] is True
    assert sub["comment"] is None  # Masked!
    assert sub["rater_id"] is None  # Redacted!
    assert "14-kunlik" in sub["message"]


def test_bilateral_double_blind_window_elapsed(client, identities, organization):
    """AC-024: Once 14-day blind window has elapsed, submission comments and metadata are unmasked."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    target_user = f["candidate"]
    rater_user = f["owner"]
    rubric_id = create_test_rubric()
    now_ts = now()

    # Rater submitted rating with publish_after in the past (window elapsed)
    publish_after_ts = now_ts - timedelta(hours=2)
    sub_id = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn,
            "rating_submissions",
            id=sub_id,
            placement_id=f["placement"]["id"],
            engagement_id=None,
            rubric_id=rubric_id,
            rater_id=rater_user["user_id"],
            target_user_id=target_user["user_id"],
            target_org_id=None,
            version=1,
            status="PUBLISHED",
            comment="Kutilgandan ham a'lo darajadagi amaliyotchi",
            submitted_at=now_ts - timedelta(days=15),
            publish_after=publish_after_ts,
        )

    res = client.get("/api/v1/me/ratings", headers=target_user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    received = data["submissions_received"]
    assert len(received) == 1
    sub = received[0]

    assert sub["id"] == sub_id
    assert sub["status"] == "PUBLISHED"
    assert sub["blind_window_active"] is False
    assert sub["comment"] == "Kutilgandan ham a'lo darajadagi amaliyotchi"


def test_authored_submissions_surfaced_in_given(client, identities, organization):
    """Authored rating submissions are returned in submissions_given with complete transparency."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    author = f["owner"]
    target_user = f["candidate"]
    rubric_id = create_test_rubric()
    now_ts = now()
    sub_id = str(uuid4())

    with transaction() as conn:
        insert_row(
            conn,
            "rating_submissions",
            id=sub_id,
            placement_id=f["placement"]["id"],
            engagement_id=None,
            rubric_id=rubric_id,
            rater_id=author["user_id"],
            target_user_id=target_user["user_id"],
            target_org_id=None,
            version=1,
            status="SUBMITTED",
            comment="Faol va tirishqoq talaba",
            submitted_at=now_ts,
            publish_after=now_ts + timedelta(days=14),
        )

    res = client.get("/api/v1/me/ratings", headers=author["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    given = data["submissions_given"]
    assert len(given) == 1
    assert given[0]["id"] == sub_id
    assert given[0]["target_user_id"] == target_user["user_id"]
    assert given[0]["comment"] == "Faol va tirishqoq talaba"


def test_eligible_completed_relations_surfaced(client, identities, organization):
    """AC-022: Surfaces completed placements eligible for rating evaluation."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    cand = f["candidate"]

    res = client.get("/api/v1/me/ratings", headers=cand["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    eligible = data["eligible_relations"]
    assert len(eligible) >= 1
    matching = [r for r in eligible if r["relation_id"] == f["placement"]["id"]]
    assert len(matching) == 1
    assert matching[0]["status"] == "COMPLETED"


def test_active_rubrics_and_criteria_projected(client, identities):
    """Surfaces active rubric versions and weighted criteria in available_rubrics."""
    user = identities()
    rubric_id = create_test_rubric(status="ACTIVE")

    res = client.get("/api/v1/me/ratings", headers=user["headers"])
    assert res.status_code == 200, res.text
    data = res.json()

    rubrics = data["available_rubrics"]
    matching = [r for r in rubrics if r["id"] == rubric_id]
    assert len(matching) == 1
    r = matching[0]
    assert r["family"] == "GENERAL_INTERNSHIP"
    assert len(r["criteria"]) == 2
    codes = {c["code"]: c["weight"] for c in r["criteria"]}
    assert codes == {"PUNCTUALITY": 40, "TECHNICAL_EXECUTION": 60}


def test_unauthenticated_request_rejected(client):
    """Calling GET /api/v1/me/ratings without authorization header fails fail-closed."""
    res = client.get("/api/v1/me/ratings")
    assert res.status_code in (401, 403), res.text
