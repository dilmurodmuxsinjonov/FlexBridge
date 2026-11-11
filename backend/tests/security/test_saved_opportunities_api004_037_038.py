"""Functional tests for Candidate Saved Opportunities (API-004, API-037, API-038 / CAP-006 / DB-040)."""

from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from test_candidate import published_fixture


def test_candidate_save_opportunity_success(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    res = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id},
        headers=candidate["headers"],
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["saved"] is True
    assert data["opportunity_id"] == opp_id
    assert data["candidate_id"] == candidate["candidate_id"]
    assert data["id"] is not None

    with transaction() as conn:
        t_saved = table("saved_opportunities")
        row = conn.execute(
            select(t_saved.c.id, t_saved.c.candidate_id, t_saved.c.opportunity_id)
            .where(t_saved.c.id == data["id"])
        ).mappings().first()
        assert row is not None
        assert row["candidate_id"] == candidate["candidate_id"]
        assert row["opportunity_id"] == opp_id


def test_candidate_save_opportunity_idempotent(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    # First save
    res1 = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id},
        headers=candidate["headers"],
    )
    assert res1.status_code == 201
    saved_id1 = res1.json()["id"]

    # Second save (repeat, toggle=False by default) -> idempotent 200 with same id
    res2 = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id},
        headers=candidate["headers"],
    )
    assert res2.status_code == 200, res2.text
    data2 = res2.json()
    assert data2["saved"] is True
    assert data2["id"] == saved_id1

    # Exactly one row exists in DB
    with transaction() as conn:
        t_saved = table("saved_opportunities")
        rows = conn.execute(
            select(t_saved.c.id).where(
                t_saved.c.candidate_id == candidate["candidate_id"],
                t_saved.c.opportunity_id == opp_id,
            )
        ).mappings().all()
        assert len(rows) == 1


def test_candidate_save_opportunity_toggle(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    # 1. Toggle when unsaved -> saved (201)
    res1 = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id, "toggle": True},
        headers=candidate["headers"],
    )
    assert res1.status_code == 201
    assert res1.json()["saved"] is True
    assert res1.json()["id"] is not None

    # 2. Toggle when saved -> unsaved (200, saved=False, id=None)
    res2 = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id, "toggle": True},
        headers=candidate["headers"],
    )
    assert res2.status_code == 200
    assert res2.json()["saved"] is False
    assert res2.json()["id"] is None

    # Verify deleted from DB
    with transaction() as conn:
        t_saved = table("saved_opportunities")
        row = conn.execute(
            select(t_saved.c.id).where(
                t_saved.c.candidate_id == candidate["candidate_id"],
                t_saved.c.opportunity_id == opp_id,
            )
        ).mappings().first()
        assert row is None

    # 3. Toggle again -> re-saved (201)
    res3 = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id, "toggle": True},
        headers=candidate["headers"],
    )
    assert res3.status_code == 201
    assert res3.json()["saved"] is True


def test_candidate_get_saved_opportunities_empty(client, identities):
    candidate = identities()
    res = client.get("/api/v1/me/saved-opportunities", headers=candidate["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_candidate_get_saved_opportunities_with_items(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()
    rev1 = published_fixture(owner, organization, title="Job Alpha")
    rev2 = published_fixture(owner, organization, title="Job Beta")

    # Save both
    client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": rev1["opportunity_id"]},
        headers=candidate["headers"],
    )
    client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": rev2["opportunity_id"]},
        headers=candidate["headers"],
    )

    res = client.get("/api/v1/me/saved-opportunities", headers=candidate["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    opp_ids = {item["opportunity_id"] for item in data["items"]}
    assert rev1["opportunity_id"] in opp_ids
    assert rev2["opportunity_id"] in opp_ids

    first_item = data["items"][0]
    assert "opportunity" in first_item
    assert "status" in first_item["opportunity"]
    assert "is_closed" in first_item["opportunity"]
    assert first_item["opportunity"]["is_closed"] is False


def test_candidate_get_saved_opportunities_preserves_closed_status(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = published_fixture(owner, organization, title="Closing Job")
    opp_id = rev["opportunity_id"]

    client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id},
        headers=candidate["headers"],
    )

    # Now close the opportunity in DB
    with transaction() as conn:
        t_opp = table("opportunities")
        conn.execute(
            t_opp.update()
            .where(t_opp.c.id == opp_id)
            .values(status="CLOSED", closed_at=now())
        )

    res = client.get("/api/v1/me/saved-opportunities", headers=candidate["headers"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["opportunity"]["id"] == opp_id
    assert item["opportunity"]["status"] == "CLOSED"
    assert item["opportunity"]["is_closed"] is True
    assert item["opportunity"]["closed_at"] is not None


def test_candidate_unsave_by_saved_id(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    res_save = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id},
        headers=candidate["headers"],
    )
    saved_id = res_save.json()["id"]

    res_del = client.delete(
        f"/api/v1/me/saved-opportunities/{saved_id}",
        headers=candidate["headers"],
    )
    assert res_del.status_code == 204

    # Verify deleted
    with transaction() as conn:
        t_saved = table("saved_opportunities")
        assert (
            conn.execute(
                select(t_saved.c.id).where(t_saved.c.id == saved_id)
            ).scalar_one_or_none()
            is None
        )


def test_candidate_unsave_by_opportunity_id(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id},
        headers=candidate["headers"],
    )

    # Delete specifying opportunity_id directly
    res_del = client.delete(
        f"/api/v1/me/saved-opportunities/{opp_id}",
        headers=candidate["headers"],
    )
    assert res_del.status_code == 204

    # Verify deleted
    with transaction() as conn:
        t_saved = table("saved_opportunities")
        assert (
            conn.execute(
                select(t_saved.c.id).where(
                    t_saved.c.candidate_id == candidate["candidate_id"],
                    t_saved.c.opportunity_id == opp_id,
                )
            ).scalar_one_or_none()
            is None
        )


def test_candidate_repeat_unsave_is_idempotent_repeat204(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id},
        headers=candidate["headers"],
    )

    # Delete 1st time
    res1 = client.delete(
        f"/api/v1/me/saved-opportunities/{opp_id}",
        headers=candidate["headers"],
    )
    assert res1.status_code == 204

    # Delete 2nd time (repeat204)
    res2 = client.delete(
        f"/api/v1/me/saved-opportunities/{opp_id}",
        headers=candidate["headers"],
    )
    assert res2.status_code == 204
