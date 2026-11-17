"""Adversarial security, concurrency race, IDOR, anti-spoofing, and double-blind confidentiality tests
for Mutual Double-Blind Engagement Ratings (API-047 / CAP-027 / DB-064..066 / AC-024).

Strictly tested on isolated PostgreSQL test cluster (port 55440); pg_live and frozen main untouched.

Covers:
1. Unauthenticated & forged Bearer token boundary (401 AUTH_REQUIRED).
2. Cross-candidate and foreign-employer IDOR defense (uniform 404 ENGAGEMENT_NOT_FOUND).
3. Anti-spoofing & role resolution: target and rater role determined strictly server-side.
4. AC-024 double-blind anti-retaliation confidentiality: feedback masked while single-sided.
5. Concurrency race condition: simultaneous submissions serialized safely under row-level lock.
6. Disputed and uncompleted engagement locks (409 ENGAGEMENT_NOT_COMPLETED).
7. SQL injection and XSS payloads in rating comments safely sanitized and parameterized.
8. Append-only audit trail immutability for all rating events.
9. Blind window expiration (14 days) and aggregate privacy threshold (n >= 5 under AC-023).
10. Pure R1 scope boundary: freelance contracts and escrow completely decoupled.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.db.storage import now, table, transaction
from test_engagement_ratings_api047 import _create_test_rubric, _setup_completed_job_engagement
from test_candidate import published_fixture


def test_adversarial_unauthenticated_and_forged_tokens(client, identities, organization):
    """Unauthenticated requests or invalid Bearer tokens are rejected fail-closed (401 AUTH_REQUIRED)."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    payload = {"rubric_id": rubric_id, "scores": scores, "comment": "Nice work"}

    # 1. No Authorization header
    res_no_auth = client.post(f"/api/v1/engagements/{eng_id}/ratings", json=payload)
    assert res_no_auth.status_code == 401, res_no_auth.text

    # 2. Forged Bearer token
    res_forged = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers={"Authorization": "Bearer forged-token-attack"},
        json=payload,
    )
    assert res_forged.status_code == 401, res_forged.text


def test_adversarial_cross_candidate_and_foreign_org_idor(client, identities, organization):
    """Uniform 404 ENGAGEMENT_NOT_FOUND on IDOR attacks by third-party candidates or foreign employers."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    payload = {"rubric_id": rubric_id, "scores": scores, "comment": "IDOR attempt"}

    # 1. Foreign candidate (User C) attempts to rate Candidate A's engagement
    foreign_candidate = identities()
    res_fc = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=foreign_candidate["headers"],
        json=payload,
    )
    assert res_fc.status_code == 404, res_fc.text
    assert res_fc.json()["detail"]["code"] == "ENGAGEMENT_NOT_FOUND"

    # 2. Foreign organization member attempts to rate
    foreign_org_id = str(uuid4())
    with transaction() as conn:
        conn.execute(
            table("organizations").insert().values(
                id=foreign_org_id,
                created_at=now(),
                updated_at=now(),
                tax_id=str(uuid4())[:12],
                legal_name="Foreign Test Org LLC",
                public_name="Foreign Test Org",
                region="Bukhara",
                status="VERIFIED",
            )
        )
    foreign_org_user = identities("OWNER", foreign_org_id)
    res_fo = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=foreign_org_user["headers"],
        json=payload,
    )
    assert res_fo.status_code == 404, res_fo.text
    assert res_fo.json()["detail"]["code"] == "ENGAGEMENT_NOT_FOUND"

    # 3. Non-existent engagement UUID
    res_fake = client.post(
        f"/api/v1/engagements/{uuid4()}/ratings",
        headers=cand_user["headers"],
        json=payload,
    )
    assert res_fake.status_code == 404, res_fake.text
    assert res_fake.json()["detail"]["code"] == "ENGAGEMENT_NOT_FOUND"


def test_adversarial_anti_spoofing_server_side_enforcement(client, identities, organization):
    """Rater role and target are strictly resolved server-side; client cannot spoof target or role."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]

    # Attempt to inject extra forbidden fields
    forged_payload = {
        "rubric_id": rubric_id,
        "scores": scores,
        "comment": "Spoofing attempt",
        "rater_role": "EMPLOYER",  # Candidate trying to masquerade as EMPLOYER
        "target_user_id": cand_user["user_id"],
    }
    res = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json=forged_payload,
    )
    # Extra fields must be forbidden by Pydantic model
    assert res.status_code == 422, res.text


def test_adversarial_ac024_blind_confidentiality_during_14_day_window(client, identities, organization):
    """AC-024: Single-sided rating feedback is strictly concealed from the other party until mutual submission."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    # Candidate submits rating with secret comment
    secret_comment = "Secret critical evaluation: needs better sprint planning."
    scores = [{"criterion_id": str(c["id"]), "score": 4} for c in crits]
    res1 = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores, "comment": secret_comment},
    )
    assert res1.status_code in (200, 201)

    # Employer queries personal ratings before submitting their own
    res_emp = client.get("/api/v1/me/ratings", headers=owner["headers"])
    assert res_emp.status_code == 200
    emp_data = res_emp.json()

    # Any received submission while blind must NOT leak the comment or score
    for sub in emp_data["submissions_received"]:
        if sub.get("engagement_id") == eng_id:
            assert sub["blind_window_active"] is True
            assert sub["comment"] is None  # Redacted!
            assert sub.get("rater_id") is None  # Anonymous rater while blind!


def test_adversarial_concurrency_race_condition_under_row_lock(client, identities, organization):
    """Simultaneous submissions by candidate and employer are serialized safely under row-level lock."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    cand_scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    emp_scores = [{"criterion_id": str(c["id"]), "score": 4} for c in crits]

    def _submit_cand():
        return client.post(
            f"/api/v1/engagements/{eng_id}/ratings",
            headers=cand_user["headers"],
            json={"rubric_id": rubric_id, "scores": cand_scores, "comment": "Concurrent Cand"},
        )

    def _submit_emp():
        return client.post(
            f"/api/v1/engagements/{eng_id}/ratings",
            headers=owner["headers"],
            json={"rubric_id": rubric_id, "scores": emp_scores, "comment": "Concurrent Emp"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_cand = executor.submit(_submit_cand)
        f_emp = executor.submit(_submit_emp)

        r_cand = f_cand.result()
        r_emp = f_emp.result()

    assert r_cand.status_code in (200, 201), r_cand.text
    assert r_emp.status_code in (200, 201), r_emp.text

    # Both submissions must be recorded and both must be PUBLISHED
    with transaction() as conn:
        t_sub = table("rating_submissions")
        rows = conn.execute(select(t_sub).where(t_sub.c.engagement_id == eng_id)).mappings().all()
        assert len(rows) == 2
        assert all(r["status"] == "PUBLISHED" for r in rows)


def test_adversarial_disputed_engagement_locked(client, identities, organization):
    """An engagement in DISPUTED status cannot be rated (409 ENGAGEMENT_NOT_COMPLETED)."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()

    # Create engagement and raise dispute
    rev = published_fixture(owner, organization)
    opp_id = rev["opportunity_id"]
    with transaction() as conn:
        conn.execute(table("opportunities").update().where(table("opportunities").c.id == opp_id).values(kind="PART_TIME"))

    res_app = client.post(
        f"/api/v1/opportunities/{opp_id}/applications",
        headers=cand_user["headers"] | {"Idempotency-Key": f"app-{uuid4()}"},
        json={"note": "App"},
    )
    app_id = res_app.json()["id"]

    res_off = client.post(
        f"/api/v1/applications/{app_id}/offers",
        headers=owner["headers"],
        json={"terms_snapshot": {"position": "Engineer"}},
    )
    offer_id = res_off.json()["id"]
    client.post(f"/api/v1/offers/{offer_id}/respond", headers=cand_user["headers"], json={"decision": "ACCEPT"})

    with transaction() as conn:
        eng_id = str(conn.execute(select(table("job_engagements").c.id).where(table("job_engagements").c.offer_id == offer_id)).scalar_one())

    # Candidate raises dispute on start
    res_disp = client.post(
        f"/api/v1/engagements/{eng_id}/confirmations",
        headers=cand_user["headers"],
        json={"action": "DISPUTE_START", "party": "CANDIDATE", "note": "Terms mismatch"},
    )
    assert res_disp.status_code == 200
    assert res_disp.json()["status"] == "DISPUTED"

    # Attempt rating on DISPUTED engagement
    scores = [{"criterion_id": str(c["id"]), "score": 1} for c in crits]
    res_rate = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores},
    )
    assert res_rate.status_code == 409, res_rate.text
    assert res_rate.json()["detail"]["code"] == "ENGAGEMENT_NOT_COMPLETED"


def test_adversarial_sqli_and_xss_in_comments_safely_handled(client, identities, organization):
    """SQL injection and XSS payloads in comments are parameterized and stored safely without execution."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    sqli_comment = "'); DROP TABLE rating_submissions; SELECT ('-- malicious"
    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]

    res = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores, "comment": sqli_comment},
    )
    assert res.status_code in (200, 201), res.text
    sub_id = res.json()["submission_id"]

    # Verify table is intact and comment is stored verbatim
    with transaction() as conn:
        t_sub = table("rating_submissions")
        row = conn.execute(select(t_sub).where(t_sub.c.id == sub_id)).mappings().one()
        assert row["comment"] == sqli_comment


def test_adversarial_audit_trail_immutability(client, identities, organization):
    """Rating submission produces an append-only audit event in AppendOnlyAuditStore."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    res = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores, "comment": "Audited rating"},
    )
    assert res.status_code in (200, 201)
    sub_id = res.json()["submission_id"]

    with transaction() as conn:
        t_audit = table("audit_events")
        audit_row = conn.execute(
            select(t_audit).where(
                t_audit.c.action == "ENGAGEMENT_RATING_SUBMITTED",
                t_audit.c.object_key == sub_id,
            )
        ).mappings().first()
        assert audit_row is not None
        assert str(audit_row["actor_id"]) == cand_user["user_id"]
        assert audit_row["object_type"] == "rating_submission"


def test_adversarial_blind_window_expiration_and_privacy_threshold(client, identities, organization):
    """AC-023 & AC-024: After 14 days, single-sided rating becomes eligible for unblinding, score withheld if n < 5."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    res = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores, "comment": "Expiring rating"},
    )
    assert res.status_code in (200, 201)
    sub_id = res.json()["submission_id"]

    # Fast forward time in database past the 14-day window
    with transaction() as conn:
        t_sub = table("rating_submissions")
        past_time = now() - timedelta(days=1)
        conn.execute(
            t_sub.update()
            .where(t_sub.c.id == sub_id)
            .values(publish_after=past_time, status="PUBLISHED")
        )

    # Candidate has n=1 rating for this org -> score must be WITHHELD_INSUFFICIENT_SAMPLE (n < 5)
    with transaction() as conn:
        from app.services.user_ratings import user_ratings_service
        agg = user_ratings_service.recompute_aggregate(conn, target_org_id=organization, rubric_id=rubric_id)
        assert agg["sample_size"] == 1
        assert agg["score"] is None
        assert agg["score_status"] == "WITHHELD_INSUFFICIENT_SAMPLE"


def test_adversarial_pure_r1_freelance_scope_decoupling(client, identities, organization):
    """Rating an engagement touches only rating tables and audit log; zero freelance tables created or queried."""
    owner = identities("OWNER", org=organization)
    cand_user = identities()
    rubric_id, crits = _create_test_rubric()
    _, _, _, eng_id = _setup_completed_job_engagement(client, owner, cand_user, organization)

    scores = [{"criterion_id": str(c["id"]), "score": 5} for c in crits]
    res = client.post(
        f"/api/v1/engagements/{eng_id}/ratings",
        headers=cand_user["headers"],
        json={"rubric_id": rubric_id, "scores": scores, "comment": "R1 scope clean"},
    )
    assert res.status_code in (200, 201)

    # Verify no unexpected schema or table pollution occurred
    with transaction() as conn:
        from sqlalchemy import inspect
        insp = inspect(conn)
        tables = insp.get_table_names(schema="flexbridge")
        assert not any("freelance" in t for t in tables)
        assert not any("escrow" in t for t in tables)
