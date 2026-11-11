"""Adversarial security tests for Candidate Saved Opportunities (API-004, API-037, API-038).

Covers:
- Unauthenticated requests rejected (401).
- Non-candidate users rejected (403 CANDIDATE_PROFILE_REQUIRED).
- Cross-candidate save spoofing rejected (403 CANDIDATE_ACCESS_DENIED).
- Cross-candidate deletion rejected (403 SAVED_OPPORTUNITY_ACCESS_DENIED).
- Non-existent opportunity rejected (404 OPPORTUNITY_NOT_FOUND).
- Malformed UUID syntax validation (422).
- Immutable audit trail generation in audit_events.
"""

from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import table, transaction
from test_candidate import published_fixture


def test_unauthenticated_requests_rejected(client):
    fake_id = str(uuid4())

    r1 = client.post("/api/v1/saved-opportunities", json={"opportunity_id": fake_id})
    assert r1.status_code == 401

    r2 = client.get("/api/v1/me/saved-opportunities")
    assert r2.status_code == 401

    r3 = client.delete(f"/api/v1/me/saved-opportunities/{fake_id}")
    assert r3.status_code == 401


def test_non_candidate_cannot_save_or_list(client, identities, organization):
    # Remove candidate profile to simulate user without candidate profile
    user = identities("OWNER", organization)
    with transaction() as conn:
        t_cand = table("candidate_profiles")
        conn.execute(t_cand.delete().where(t_cand.c.user_id == user["user_id"]))

    fake_opp = str(uuid4())

    r1 = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": fake_opp},
        headers=user["headers"],
    )
    assert r1.status_code == 403
    assert r1.json()["detail"]["code"] == "CANDIDATE_PROFILE_REQUIRED"

    r2 = client.get("/api/v1/me/saved-opportunities", headers=user["headers"])
    assert r2.status_code == 403
    assert r2.json()["detail"]["code"] == "CANDIDATE_PROFILE_REQUIRED"


def test_candidate_cannot_save_for_another_candidate(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate_a = identities()
    candidate_b = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    # Candidate A passes Candidate B's candidate_id
    res = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id, "candidate_id": candidate_b["candidate_id"]},
        headers=candidate_a["headers"],
    )
    assert res.status_code == 403, res.text
    assert res.json()["detail"]["code"] == "CANDIDATE_ACCESS_DENIED"


def test_candidate_cannot_delete_another_candidates_saved_opportunity(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate_a = identities()
    candidate_b = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    # Candidate B saves the opportunity
    res_b = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id},
        headers=candidate_b["headers"],
    )
    assert res_b.status_code == 201
    saved_id_b = res_b.json()["id"]

    # Candidate A attempts to delete Candidate B's saved opportunity
    res_a = client.delete(
        f"/api/v1/me/saved-opportunities/{saved_id_b}",
        headers=candidate_a["headers"],
    )
    assert res_a.status_code == 403, res_a.text
    assert res_a.json()["detail"]["code"] == "SAVED_OPPORTUNITY_ACCESS_DENIED"

    # Verify Candidate B's saved opportunity remains intact
    with transaction() as conn:
        t_saved = table("saved_opportunities")
        row = conn.execute(
            select(t_saved.c.id).where(t_saved.c.id == saved_id_b)
        ).scalar_one_or_none()
        assert row is not None


def test_save_nonexistent_opportunity_rejected(client, identities):
    candidate = identities()
    fake_opp = str(uuid4())

    res = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": fake_opp},
        headers=candidate["headers"],
    )
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"


def test_invalid_uuid_syntax_validation(client, identities):
    candidate = identities()

    res1 = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": "invalid-uuid-format"},
        headers=candidate["headers"],
    )
    assert res1.status_code == 422

    res2 = client.delete(
        "/api/v1/me/saved-opportunities/not-a-valid-uuid",
        headers=candidate["headers"],
    )
    assert res2.status_code == 422


def test_audit_event_logged_on_save_and_unsave(client, identities, organization):
    owner = identities("OWNER", organization)
    candidate = identities()
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]

    # Save
    res_save = client.post(
        "/api/v1/saved-opportunities",
        json={"opportunity_id": opp_id},
        headers=candidate["headers"],
    )
    assert res_save.status_code == 201
    saved_id = res_save.json()["id"]

    # Unsave
    res_del = client.delete(
        f"/api/v1/me/saved-opportunities/{saved_id}",
        headers=candidate["headers"],
    )
    assert res_del.status_code == 204

    # Check audit events in DB
    with transaction() as conn:
        t_audit = table("audit_events")
        rows = conn.execute(
            select(t_audit.c.action, t_audit.c.object_type, t_audit.c.object_key, t_audit.c.actor_id)
            .where(
                t_audit.c.object_type == "saved_opportunity",
                t_audit.c.object_key == saved_id,
            )
            .order_by(t_audit.c.occurred_at.asc())
        ).mappings().all()

        actions = [r["action"] for r in rows]
        assert "OPPORTUNITY_SAVED" in actions
        assert "OPPORTUNITY_UNSAVED" in actions
        for r in rows:
            assert r["actor_id"] == candidate["user_id"]
