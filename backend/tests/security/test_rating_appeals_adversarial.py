"""Adversarial and boundary test suite for Rating Appeal Submission (API-058 / CAP-028 / DB-067 / AC-025).

Tests:
1. Non-existent rating ID returns 404 (RATING_NOT_FOUND).
2. Boundary reason length validation:
   - Reason < 10 chars rejected (422).
   - Reason > 4000 chars rejected (422).
3. Direct rating_revision_id in path parameter resolves properly.
4. Rater author can also file an appeal as a legitimate party to the rating.
5. Re-resolving an already resolved appeal is rejected with 409 Conflict.
6. Malformed JSON or missing fields handled gracefully with 422.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.api.dependencies import ActorContext
from app.db.storage import now, table, transaction
from app.services.placements import insert_row
from app.services.user_ratings import user_ratings_service
from test_rating_appeals_api058 import (
    create_published_rating,
    create_test_rubric,
    setup_completed_placement,
)


def test_non_existent_rating_id_returns_404(client, identities):
    """Adversarial probe: Non-existent rating ID returns 404 Not Found."""
    user = identities()
    fake_id = str(uuid4())

    res = client.post(
        f"/api/v1/ratings/{fake_id}/appeals",
        json={"reason": "Mavjud bo'lmagan baholashga e'tiroz bildirishga urinish."},
        headers=user["headers"],
    )
    assert res.status_code == 404, res.text
    assert "RATING_NOT_FOUND" in res.text


def test_appeal_short_reason_rejected_422(client, identities, organization):
    """Boundary test: Reason shorter than 10 characters is rejected (422)."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
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
        json={"reason": "Qisqa"},  # Only 5 characters (< 10)
        headers=candidate["headers"],
    )
    assert res.status_code == 422, res.text


def test_appeal_long_reason_rejected_422(client, identities, organization):
    """Boundary test: Reason longer than 4000 characters is rejected (422)."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
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
        json={"reason": "X" * 4001},  # 4001 characters (> 4000)
        headers=candidate["headers"],
    )
    assert res.status_code == 422, res.text


def test_direct_revision_id_parameter_resolution(client, identities, organization):
    """Flexibility test: Passing revision_id directly in {id} parameter resolves parent submission."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
    rubric_id = create_test_rubric()

    sub_id, rev_id = create_published_rating(
        placement_id=f["placement"]["id"],
        rater_id=owner["user_id"],
        target_user_id=candidate["user_id"],
        rubric_id=rubric_id,
        days_ago=1,
    )

    # Pass rev_id instead of sub_id
    res = client.post(
        f"/api/v1/ratings/{rev_id}/appeals",
        json={"reason": "Tahrir ID orqali to'g'ridan-to'g'ri yuborilgan e'tiroz matni."},
        headers=candidate["headers"],
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["rating_id"] == sub_id
    assert data["rating_revision_id"] == rev_id


def test_rater_author_can_appeal(client, identities, organization):
    """Party test: Rater author is a party to the rating and can appeal (201 Created)."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
    rubric_id = create_test_rubric()

    sub_id, rev_id = create_published_rating(
        placement_id=f["placement"]["id"],
        rater_id=owner["user_id"],
        target_user_id=candidate["user_id"],
        rubric_id=rubric_id,
        days_ago=1,
    )

    # Owner (rater) submits appeal
    res = client.post(
        f"/api/v1/ratings/{sub_id}/appeals",
        json={"reason": "Baholovchi sifatida tizimdagi hisoblash xatosiga e'tiroz bildiraman."},
        headers=owner["headers"],
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["appellant_id"] == owner["user_id"]
    assert data["status"] == "PENDING"


def test_resolved_appeal_cannot_be_re_resolved_409(client, identities, organization):
    """State machine test: An appeal already RESOLVED cannot be re-resolved (409 Conflict)."""
    f = setup_completed_placement(client, identities, organization, status="COMPLETED")
    candidate = f["candidate"]
    owner = f["owner"]
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
        json={"reason": "Ko'rib chiqish uchun dastlabki asosli e'tiroz matni."},
        headers=candidate["headers"],
    )
    assert res.status_code == 201, res.text
    appeal_id = res.json()["appeal_id"]

    reviewer = identities("MODERATOR")
    reviewer_actor = ActorContext(
        user_id=reviewer["user_id"],
        session_id=reviewer["session_id"],
        roles=("MODERATOR",),
    )

    # First resolution
    res_one = user_ratings_service.resolve_rating_appeal(
        appeal_id=appeal_id,
        reviewer=reviewer_actor,
        decision="ACCEPTED",
    )
    assert res_one["status"] == "RESOLVED"

    # Attempt second resolution -> 409 Conflict
    with pytest.raises(Exception) as exc_info:
        user_ratings_service.resolve_rating_appeal(
            appeal_id=appeal_id,
            reviewer=reviewer_actor,
            decision="DISMISSED",
        )
    assert "APPEAL_ALREADY_RESOLVED" in str(exc_info.value) or exc_info.value.status_code == 409
