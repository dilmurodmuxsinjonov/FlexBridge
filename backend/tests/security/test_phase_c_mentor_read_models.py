"""Security & contract tests for Phase C host mentor discovery read models (`API-087`)."""

from __future__ import annotations

from uuid import uuid4

from test_academic_reviews import ready


def test_list_organization_mentors_and_placement_mentor_assignments(client, identities, organization):
    f, _, _ = ready(client, identities, organization, required_minutes=0)
    org_id = organization
    pid = f["placement"]["id"]
    owner_headers = f["owner"]["headers"]
    mentor_user_id = f["owner"]["user_id"]
    candidate_headers = f["candidate"]["headers"]

    # 1. Host lists org mentors -> includes active MENTOR role holder
    res = client.get(
        f"/api/v1/organizations/{org_id}/mentors",
        headers=owner_headers,
    )
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    assert any(m["user_id"] == mentor_user_id for m in items)

    # 2. Candidate/outsider cannot enumerate org mentors
    forbid = client.get(
        f"/api/v1/organizations/{org_id}/mentors",
        headers=candidate_headers,
    )
    assert forbid.status_code == 403, forbid.text

    # 3. Host lists non-revoked mentor assignments on placement
    asg_res = client.get(
        f"/api/v1/placements/{pid}/mentor-assignments",
        headers=owner_headers,
    )
    assert asg_res.status_code == 200, asg_res.text
    asg_items = asg_res.json()["items"]
    assert len(asg_items) >= 1
    assert any(a["mentor_user_id"] == mentor_user_id for a in asg_items)
    first_asg_id = asg_items[0]["id"]

    # 4. Candidate cannot call host mentor-assignments listing
    forbid_asg = client.get(
        f"/api/v1/placements/{pid}/mentor-assignments",
        headers=candidate_headers,
    )
    assert forbid_asg.status_code == 403, forbid_asg.text

    # 5. Revoked assignment drops out of active list (via real HTTP API-087 revoke)
    plan_res = client.get(f"/api/v1/placements/{pid}/plan", headers=owner_headers)
    assert plan_res.status_code == 200, plan_res.text
    plan_data = plan_res.json()
    revoke_res = client.post(
        f"/api/v1/placements/{pid}/mentor-assignments/{first_asg_id}/revoke",
        headers=owner_headers,
        json={
            "terms_id": plan_data["terms_id"],
            "version": plan_data["version"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert revoke_res.status_code == 200, revoke_res.text
    after_revoke = client.get(
        f"/api/v1/placements/{pid}/mentor-assignments",
        headers=owner_headers,
    )
    assert after_revoke.status_code == 200
    assert all(a["id"] != first_asg_id for a in after_revoke.json()["items"])

    # 6. Unknown org returns 403/404 cleanly
    miss = client.get(
        f"/api/v1/organizations/{uuid4()}/mentors",
        headers=owner_headers,
    )
    assert miss.status_code in (403, 404)
