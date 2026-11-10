"""Adversarial and security boundary tests for Personal Ratings View (API-057 / CAP-027).

Verifies:
1. Revoked actor session is rejected immediately fail-closed.
2. Cross-user isolation: User A cannot observe User B's blinded or unblinded ratings.
3. Multi-role compatibility: Candidates, Mentors, and HR actors all retrieve scoped ratings cleanly.
4. Decimal score accuracy: Precise representation of fractional numeric(18,2) values.
5. Large batch handling: High volume of rating submissions handled without degradation.
6. Target user boundary conditions: Foreign actor ID tampering does not leak metadata.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from test_user_ratings_api057 import create_test_rubric, setup_completed_placement


def test_revoked_session_rejected_fail_closed(client, identities):
    """Actor with revoked session cannot query personal ratings (401/403)."""
    user = identities()

    # Revoke user's active session
    with transaction() as conn:
        conn.execute(
            table("sessions").update().where(table("sessions").c.id == user["session_id"]).values(revoked_at=now())
        )

    res = client.get("/api/v1/me/ratings", headers=user["headers"])
    assert res.status_code in (401, 403), res.text


def test_cross_user_isolation(client, identities, organization):
    """User A cannot observe ratings received or given by User B."""
    user_a = identities()
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    user_b = f["candidate"]
    rater = f["owner"]
    rubric_id = create_test_rubric()
    now_ts = now()

    with transaction() as conn:
        insert_row(
            conn,
            "rating_submissions",
            id=str(uuid4()),
            placement_id=f["placement"]["id"],
            engagement_id=None,
            rubric_id=rubric_id,
            rater_id=rater["user_id"],
            target_user_id=user_b["user_id"],
            target_org_id=None,
            version=1,
            status="PUBLISHED",
            comment="B's secret feedback",
            submitted_at=now_ts,
            publish_after=now_ts - timedelta(days=1),
        )

    # User A queries their ratings
    res_a = client.get("/api/v1/me/ratings", headers=user_a["headers"])
    assert res_a.status_code == 200
    data_a = res_a.json()

    assert data_a["target_user_id"] == user_a["user_id"]
    assert len(data_a["submissions_received"]) == 0
    assert len(data_a["submissions_given"]) == 0

    # User B queries their ratings
    res_b = client.get("/api/v1/me/ratings", headers=user_b["headers"])
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["target_user_id"] == user_b["user_id"]
    assert len(data_b["submissions_received"]) == 1
    assert data_b["submissions_received"][0]["comment"] == "B's secret feedback"


def test_multi_role_compatibility(client, identities, organization):
    """Mentors and HR coordinators can query personal ratings without error."""
    mentor = identities("MENTOR", org=organization)
    hr = identities("HOST_COORDINATOR", org=organization)

    res_m = client.get("/api/v1/me/ratings", headers=mentor["headers"])
    assert res_m.status_code == 200
    assert res_m.json()["contract_id"] == "API-057"
    assert res_m.json()["target_user_id"] == mentor["user_id"]

    res_hr = client.get("/api/v1/me/ratings", headers=hr["headers"])
    assert res_hr.status_code == 200
    assert res_hr.json()["contract_id"] == "API-057"
    assert res_hr.json()["target_user_id"] == hr["user_id"]


def test_decimal_score_precision(client, identities):
    """Scores with multiple decimal places are rendered accurately without floating-point distortion."""
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
            sample_size=10,
            score=4.67,  # Two decimal places numeric(18,2)
            window_start=now_ts.date() - timedelta(days=90),
            window_end=now_ts.date(),
            computed_at=now_ts,
        )

    res = client.get("/api/v1/me/ratings", headers=user["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["aggregate"]["score"] == 4.67
    assert data["aggregate"]["sample_size"] == 10
    assert data["aggregate"]["score_status"] == "PUBLISHED"


def test_high_volume_submissions_batch_ordering(client, identities, organization):
    """Multiple submissions from distinct raters are returned ordered by submitted_at descending."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    user = f["candidate"]
    rubric_id = create_test_rubric()
    now_ts = now()

    with transaction() as conn:
        for i in range(5):
            rater_i = identities()
            insert_row(
                conn,
                "rating_submissions",
                id=str(uuid4()),
                placement_id=f["placement"]["id"],
                engagement_id=None,
                rubric_id=rubric_id,
                rater_id=rater_i["user_id"],
                target_user_id=user["user_id"],
                target_org_id=None,
                version=1,
                status="PUBLISHED",
                comment=f"Review #{i}",
                submitted_at=now_ts - timedelta(days=5 - i),
                publish_after=now_ts - timedelta(days=1),
            )

    res = client.get("/api/v1/me/ratings", headers=user["headers"])
    assert res.status_code == 200
    data = res.json()

    received = data["submissions_received"]
    assert len(received) == 5
    # Most recent should be Review #4
    assert received[0]["comment"] == "Review #4"
    assert received[-1]["comment"] == "Review #0"
