"""Regression tests for deterministic runtime-only server archive packaging."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
_BUILDER_PATH = ROOT / "scripts" / "build_server_package.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_server_package", _BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_builder = _load_builder()
build_server_archive = _builder.build_server_archive
collect_server_files = _builder.collect_server_files


def test_collect_server_files_includes_runtime_and_excludes_non_runtime() -> None:
    files = collect_server_files(ROOT)
    file_set = set(files)

    expected_runtime = {
        ".dockerignore",
        "infra/compose.yaml",
        "infra/.env.example",
        "backend/Dockerfile",
        "backend/requirements.txt",
        "backend/FlexBridge_1_4_schema.sql",
        "backend/app/main.py",
        "backend/scripts/bootstrap_super_admin.py",
        "specs/v1_4/FlexBridge_model_1_4.json",
        "frontend/Dockerfile",
        "frontend/.dockerignore",
        "frontend/package.json",
        "frontend/package-lock.json",
        "frontend/src/app/tolovlar/page.tsx",
        "docs/operations/SERVER_DEPLOY.md",
    }
    missing = expected_runtime - file_set
    assert not missing, f"Missing expected runtime files: {sorted(missing)}"

    forbidden_prefixes = (
        "archive/",
        "reviews/",
        ".git/",
        ".agents/",
        ".claude/",
        ".gemini/",
        "backend/tests/",
        "docs/journals/",
        "docs/protocols/",
        "specs/v1_3/",
        "contracts/",
    )
    for rel in files:
        assert not rel.startswith(forbidden_prefixes), f"Forbidden file leaked into server package: {rel}"
        assert "/__pycache__/" not in rel
        assert "/.data/" not in rel
        assert not rel.endswith((".test.ts", ".test.tsx", ".sqlite3", ".pem", ".key", ".pyc"))
        if Path(rel).name.startswith(".env"):
            assert rel == "infra/.env.example", f"Secret env file must never be packaged: {rel}"


def test_build_server_archive_writes_tarball_and_verified_manifest(tmp_path: Path) -> None:
    output = tmp_path / "flexbridge-server-test.tar.gz"
    manifest = build_server_archive(ROOT, output)

    assert output.is_file()
    manifest_path = tmp_path / "flexbridge-server-test.manifest.json"
    assert manifest_path.is_file()

    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_sha = hashlib.sha256(output.read_bytes()).hexdigest()
    assert loaded["sha256"] == actual_sha
    assert manifest["file_count"] > 100

    with tarfile.open(output, "r:gz") as tar:
        names = set(tar.getnames())
    assert "SERVER_DEPLOY.md" in names
    assert "infra/compose.yaml" in names
    assert "infra/.env" not in names
    assert "backend/app/main.py" in names
    assert "frontend/src/app/tolovlar/page.tsx" in names
    assert not any(n.startswith(("archive/", "reviews/", "backend/tests/")) for n in names)
