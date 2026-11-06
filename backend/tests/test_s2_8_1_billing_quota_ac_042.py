"""S2.8.1 Tests: Tariffs, 5-Slot Concurrent Quota (ORG_PLAN_30D), Payment Idempotency & Dual-Control Refunds."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_org_plan_30d_concurrent_5_slot_quota_and_slot_release_ac_042():
    """Verifies AC-042 & INV-04: ORG_PLAN_30D allows 5 concurrent PUBLISHED slots, blocks 6th, and frees slot on CLOSED."""
    order_res = client.post(
        "/api/v1/billing/orders",
        json={
            "organization_id": "org-quota-1",
            "plan_code": "ORG_PLAN_30D",
            "created_by": "emp-owner-1",
        },
    )
    assert order_res.status_code == 201
    invoice_id = order_res.json()["invoice_id"]
    assert order_res.json()["amount_uzs"] == 599_000

    # Pay invoice idempotently (API-073 / DB-072)
    pay_res_1 = client.post(
        "/api/v1/billing/payments/attempts",
        json={
            "invoice_id": invoice_id,
            "provider_code": "PAYME",
            "idempotency_key": "idem-org-quota-1",
            "amount_uzs": 599_000,
            "actor_user_id": "emp-owner-1",
        },
    )
    assert pay_res_1.status_code == 200
    attempt_1 = pay_res_1.json()

    # Replay same idempotency_key -> returns identical attempt without error or double charge
    pay_res_2 = client.post(
        "/api/v1/billing/payments/attempts",
        json={
            "invoice_id": invoice_id,
            "provider_code": "PAYME",
            "idempotency_key": "idem-org-quota-1",
            "amount_uzs": 599_000,
            "actor_user_id": "emp-owner-1",
        },
    )
    assert pay_res_2.status_code == 200
    assert pay_res_2.json()["attempt_id"] == attempt_1["attempt_id"]
    assert pay_res_2.json()["entitlement_id"] == attempt_1["entitlement_id"]

    # Publish 5 opportunities concurrently -> all 5 succeed
    for i in range(1, 6):
        pub_res = client.post(
            "/api/v1/billing/slots/publish",
            json={
                "organization_id": "org-quota-1",
                "opportunity_id": f"opp-{i}",
                "actor_user_id": "emp-owner-1",
            },
        )
        assert pub_res.status_code == 200
        assert pub_res.json()["active_published_count"] == i

    # Attempt to publish 6th opportunity while 5 are PUBLISHED -> 409 CONCURRENT_QUOTA_REACHED (AC-042)
    sixth_res = client.post(
        "/api/v1/billing/slots/publish",
        json={
            "organization_id": "org-quota-1",
            "opportunity_id": "opp-6",
            "actor_user_id": "emp-owner-1",
        },
    )
    assert sixth_res.status_code == 409
    assert "CONCURRENT_QUOTA_REACHED" in sixth_res.json()["detail"]

    # Close opp-1 -> active_published_count drops to 4
    close_res = client.patch(
        "/api/v1/billing/slots/status",
        json={
            "organization_id": "org-quota-1",
            "opportunity_id": "opp-1",
            "new_status": "CLOSED",
            "actor_user_id": "emp-owner-1",
        },
    )
    assert close_res.status_code == 200
    assert close_res.json()["active_published_count"] == 4

    # Now publishing opp-6 succeeds! (AC-042)
    sixth_retry = client.post(
        "/api/v1/billing/slots/publish",
        json={
            "organization_id": "org-quota-1",
            "opportunity_id": "opp-6",
            "actor_user_id": "emp-owner-1",
        },
    )
    assert sixth_retry.status_code == 200
    assert sixth_retry.json()["active_published_count"] == 5


def test_refund_enforces_invoice_ceiling_inv_05_and_dual_control_inv_11():
    """Verifies INV-05 (refund <= invoice) and INV-11 (distinct requested_by, approved_by, second_approver_id)."""
    order_res = client.post(
        "/api/v1/billing/orders",
        json={
            "organization_id": "org-refund-1",
            "plan_code": "SINGLE_POST_30D",
            "created_by": "emp-2",
        },
    )
    invoice_id = order_res.json()["invoice_id"]
    assert order_res.json()["amount_uzs"] == 149_000

    client.post(
        "/api/v1/billing/payments/attempts",
        json={
            "invoice_id": invoice_id,
            "provider_code": "CLICK",
            "idempotency_key": "idem-single-post-1",
            "amount_uzs": 149_000,
            "actor_user_id": "emp-2",
        },
    )

    # Refund exceeding invoice amount (150,000 > 149,000) -> 409 INV-05 violation
    over_refund = client.post(
        "/api/v1/billing/refunds",
        json={
            "invoice_id": invoice_id,
            "amount_uzs": 150_000,
            "reason": "Over-refund attempt",
            "requested_by": "fin-admin-1",
            "approved_by": "fin-admin-2",
            "second_approver_id": "super-admin-1",
        },
    )
    assert over_refund.status_code == 409
    assert "INV-05" in over_refund.json()["detail"]

    # Self-approval (requested_by == approved_by) -> 409 INV-11 violation
    self_refund = client.post(
        "/api/v1/billing/refunds",
        json={
            "invoice_id": invoice_id,
            "amount_uzs": 149_000,
            "reason": "Self approval attempt",
            "requested_by": "fin-admin-1",
            "approved_by": "fin-admin-1",
            "second_approver_id": "super-admin-1",
        },
    )
    assert self_refund.status_code == 409
    assert "INV-11" in self_refund.json()["detail"]

    # Valid Dual-Control refund -> 201
    valid_refund = client.post(
        "/api/v1/billing/refunds",
        json={
            "invoice_id": invoice_id,
            "amount_uzs": 149_000,
            "reason": "Duplicate purchase refund approved by dual control",
            "requested_by": "fin-admin-1",
            "approved_by": "fin-admin-2",
            "second_approver_id": "super-admin-1",
        },
    )
    assert valid_refund.status_code == 201
    assert valid_refund.json()["status"] == "APPROVED"
