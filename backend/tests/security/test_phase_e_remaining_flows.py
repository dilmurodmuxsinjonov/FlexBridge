"""Security & contract tests for Phase E managed opportunity appeal metadata read model."""

from __future__ import annotations

from test_moderation_appeals import claim, decide, rejection, submit


def test_manage_opportunities_exposes_rejection_action_and_latest_appeal(client, identities, organization):
    owner, _, revision, original_action = rejection(client, identities, organization)
    opp_id = revision["opportunity_id"]

    # 1. Before appeal: REJECTED opportunity carries latest_rejection_action_id and no appeal yet
    before = client.get(
        f"/api/v1/organizations/{organization}/opportunities/manage",
        headers=owner["headers"],
    )
    assert before.status_code == 200, before.text
    row = next(item for item in before.json()["items"] if item["id"] == opp_id)
    assert row["status"] == "REJECTED"
    assert row["latest_rejection_action_id"] == original_action["id"]
    assert row["latest_appeal"] is None

    # 2. Employer submits appeal via real API-111 endpoint
    appeal_res = submit(client, owner, original_action)
    assert appeal_res.status_code == 201, appeal_res.text
    case_id = appeal_res.json()["case_id"]

    after_submit = client.get(
        f"/api/v1/organizations/{organization}/opportunities/manage",
        headers=owner["headers"],
    )
    assert after_submit.status_code == 200, after_submit.text
    row_after = next(item for item in after_submit.json()["items"] if item["id"] == opp_id)
    assert row_after["latest_appeal"] is not None
    assert row_after["latest_appeal"]["case_id"] == case_id
    assert row_after["latest_appeal"]["status"] == "OPEN"

    # 3. Independent moderator upholds -> manage read model reflects resolved appeal
    reviewer = identities("MODERATOR")
    assert claim(client, reviewer, case_id).status_code == 200
    assert decide(client, reviewer, case_id, decision="UPHOLD").status_code == 200

    after_decide = client.get(
        f"/api/v1/organizations/{organization}/opportunities/manage",
        headers=owner["headers"],
    )
    assert after_decide.status_code == 200, after_decide.text
    row_final = next(item for item in after_decide.json()["items"] if item["id"] == opp_id)
    assert row_final["latest_appeal"]["decision"] == "UPHOLD"
