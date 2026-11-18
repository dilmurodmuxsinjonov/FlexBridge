"""Security & contract tests for Phase D Passkeys & /me/security read-model metadata."""

from __future__ import annotations

from test_iam import PASSWORD, assertion_options, enroll_passkey


def test_me_security_lists_and_revokes_passkeys_without_leaking_key_material(client, identities):
    user = identities()

    empty_res = client.get("/api/v1/me/security", headers=user["headers"])
    assert empty_res.status_code == 200, empty_res.text
    empty_data = empty_res.json()
    assert empty_data["passkeys_count"] == 0
    assert empty_data["passkeys"] == []

    # Enroll passkey via WebAuthn test fixture; rotate_security invalidates prior session so re-auth via passkey
    authenticator, cid = enroll_passkey(client, user)
    opts = assertion_options(client)
    login_res = client.post(
        "/api/v1/auth/passkeys/verify",
        json={
            "ceremony_token": opts["ceremony_token"],
            "credential": authenticator.assertion(opts["public_key"]),
        },
    )
    assert login_res.status_code == 200, login_res.text
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    overview_res = client.get("/api/v1/me/security", headers=headers)
    assert overview_res.status_code == 200, overview_res.text
    overview = overview_res.json()
    assert overview["passkeys_count"] == 1
    assert len(overview["passkeys"]) == 1
    pk = overview["passkeys"][0]
    assert pk["id"] == cid
    assert "cose" not in pk
    assert "credential_key" not in pk

    revoke_res = client.request(
        "DELETE",
        f"/api/v1/me/security/passkeys/{cid}",
        headers=headers,
        json={"current_password": PASSWORD},
    )
    assert revoke_res.status_code == 200, revoke_res.text
    assert revoke_res.json()["status"] == "REVOKED"

    # Re-login with password (prior session rotated on passkey revoke) and verify empty list
    relogin = client.post(
        "/api/v1/auth/login",
        json={"user_id": user["user_id"], "password": PASSWORD},
    )
    assert relogin.status_code == 200, relogin.text
    fresh_headers = {"Authorization": f"Bearer {relogin.json()['access_token']}"}
    after_res = client.get("/api/v1/me/security", headers=fresh_headers)
    assert after_res.status_code == 200, after_res.text
    assert after_res.json()["passkeys_count"] == 0
    assert after_res.json()["passkeys"] == []
