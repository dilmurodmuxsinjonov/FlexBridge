"""Verify per-request session validation deduplication between middleware and ActorContext dependencies."""
from app.api.dependencies import require_actor_context
from app.services.auth import auth_service


def test_authenticated_request_validates_session_only_once(client, identities, monkeypatch):
    actor = identities()
    calls = []
    original = auth_service.validate_session

    defspy = lambda token: (calls.append(token), original(token))[1]
    monkeypatch.setattr(auth_service, "validate_session", defspy)

    resp = client.get("/api/v1/auth/me", headers=actor["headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["user_id"] == actor["user_id"]
    assert len(calls) == 1

    # Second request validates fresh against DB (no cross-request stale session leakage)
    resp2 = client.get("/api/v1/me/contacts", headers=actor["headers"])
    assert resp2.status_code == 200, resp2.text
    assert len(calls) == 2

    # Direct positional call without FastAPI Request object remains backward-compatible
    ctx = require_actor_context(actor["headers"]["Authorization"])
    assert ctx.user_id == actor["user_id"]
    assert len(calls) == 3
