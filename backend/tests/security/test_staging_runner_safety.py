"""Safety checks for direct SQL in the container E2E runner.

These checks do not claim that the five container phases ran: Docker/WSL is a
separate runtime gate.
"""
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "test_staging_e2e.py"


def runner():
    spec = importlib.util.spec_from_file_location("staging_e2e_safety", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_uses_ignored_compose_credentials_instead_of_inherited_database_url(tmp_path, monkeypatch):
    monkeypatch.delenv("FLEXBRIDGE_STAGING_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://live:never@prod.example:5432/pg_live")
    sample = tmp_path / ".env"
    sample.write_text("POSTGRES_USER=staging_user\nPOSTGRES_PASSWORD=local_test_only_123\nPOSTGRES_DB=flexbridge\n")
    url = make_url(runner().staging_database_url(sample))
    assert (url.host, url.port, url.database, url.username, url.password) == (
        "127.0.0.1", 5432, "flexbridge", "staging_user", "local_test_only_123"
    )


@pytest.mark.parametrize("target", [
    "postgresql+psycopg://u:p@prod.example:5432/flexbridge",
    "postgresql+psycopg://u:p@127.0.0.1:55440/flexbridge",
    "postgresql+psycopg://u:p@127.0.0.1:5432/pg_live",
    "sqlite:///local.db",
])
def test_non_staging_direct_sql_targets_are_rejected(monkeypatch, target):
    monkeypatch.setenv("FLEXBRIDGE_STAGING_DATABASE_URL", target)
    with pytest.raises(RuntimeError, match="Staging SQL target"):
        runner().staging_database_url()


def test_runner_masks_the_database_password_even_when_a_phase_fails(monkeypatch, capsys):
    secret = "unique-local-staging-secret-do-not-print"
    monkeypatch.setenv("FLEXBRIDGE_STAGING_DATABASE_URL", "postgresql+psycopg://u:"+secret+"@127.0.0.1:5432/flexbridge")
    module = runner()

    def fail_before_network(_client):
        raise RuntimeError(secret)

    monkeypatch.setattr(module, "phase_1_infrastructure_and_health", fail_before_network)
    assert module.main() == 1
    output = capsys.readouterr().out
    assert secret not in output
    assert "***" in output
    assert "RuntimeError" in output
