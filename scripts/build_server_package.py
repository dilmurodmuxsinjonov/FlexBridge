"""Deterministic server-only deployment archive builder for FlexBridge 1.4.

Packages strictly the runtime source and Docker/Compose definitions required to
deploy FlexBridge on a target host, excluding AI histories, daily reviews,
presentations, v1.3 specs, test suites, .git, and secrets (.env).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tarfile
from typing import Iterable

DEFAULT_OUTPUT_DIR = Path("D:/Codex/FlexBridge-deploy")

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "archive/",
    "reviews/",
    ".git/",
    ".github/",
    ".githooks/",
    ".vscode/",
    ".agents/",
    ".claude/",
    ".gemini/",
    "backend/tests/",
    "docs/journals/",
    "docs/protocols/",
    "docs/backend/",
    "docs/frontend/",
    "contracts/",
    "specs/v1_3/",
)

FORBIDDEN_PARTS: frozenset[str] = frozenset({
    ".data",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    ".next",
})

FORBIDDEN_SUFFIXES: tuple[str, ...] = (
    ".pyc",
    ".pyo",
    ".sqlite3",
    ".sqlite3-wal",
    ".sqlite3-shm",
    ".pem",
    ".key",
    ".bundle",
    ".tsbuildinfo",
)

ROOT_RUNTIME_FILES: tuple[str, ...] = (
    ".dockerignore",
    "infra/compose.yaml",
    "infra/.env.example",
    "backend/Dockerfile",
    "backend/requirements.txt",
    "backend/pyproject.toml",
    "backend/alembic.ini",
    "backend/FlexBridge_1_4_schema.sql",
    "specs/v1_4/FlexBridge_model_1_4.json",
    "frontend/Dockerfile",
    "frontend/.dockerignore",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/next.config.js",
    "frontend/tsconfig.json",
    "frontend/tailwind.config.ts",
    "frontend/postcss.config.js",
    "docs/operations/SERVER_DEPLOY.md",
)

ARCHIVE_PATH_OVERRIDES: dict[str, str] = {
    "docs/operations/SERVER_DEPLOY.md": "SERVER_DEPLOY.md",
}


def _is_forbidden_runtime_path(rel_posix: str) -> str | None:
    if any(rel_posix.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return f"forbidden directory prefix: {rel_posix}"
    parts = rel_posix.split("/")
    for part in parts[:-1]:
        if part in FORBIDDEN_PARTS:
            return f"forbidden path segment {part!r}: {rel_posix}"
    name = parts[-1]
    if (name == ".env" or name.startswith(".env.")) and rel_posix != "infra/.env.example":
        return f"secret environment file excluded: {rel_posix}"
    if any(rel_posix.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
        return f"forbidden artifact suffix: {rel_posix}"
    if rel_posix.startswith("frontend/src/test/"):
        return f"frontend test helper excluded: {rel_posix}"
    if rel_posix.startswith("frontend/src/") and (
        name.endswith(".test.ts")
        or name.endswith(".test.tsx")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.tsx")
    ):
        return f"frontend unit test excluded: {rel_posix}"
    return None


def _iter_tree(repo_root: Path, rel_dir: str) -> Iterable[str]:
    base = repo_root / rel_dir
    if not base.is_dir():
        return
    for item in base.rglob("*"):
        if not item.is_file():
            continue
        rel_posix = item.relative_to(repo_root).as_posix()
        if _is_forbidden_runtime_path(rel_posix) is None:
            yield rel_posix


def collect_server_files(repo_root: Path) -> list[str]:
    """Return sorted relative POSIX paths of runtime-only files for server deployment."""
    root = repo_root.resolve()
    candidates: set[str] = set()

    for rel in ROOT_RUNTIME_FILES:
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(f"Required runtime file missing: {rel}")
        candidates.add(rel)

    for rel_dir in ("backend/app", "backend/alembic", "backend/scripts", "frontend/src", "frontend/public"):
        for rel in _iter_tree(root, rel_dir):
            candidates.add(rel)

    result = sorted(candidates)
    for rel in result:
        reason = _is_forbidden_runtime_path(rel)
        if reason is not None:
            raise RuntimeError(f"Fail-closed check rejected server file ({reason})")
    return result


def build_server_archive(repo_root: Path, output_path: Path) -> dict[str, object]:
    """Package runtime-only files into a gzip tarball and write a sibling SHA-256 manifest."""
    root = repo_root.resolve()
    files = collect_server_files(root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    with tarfile.open(output_path, "w:gz") as tar:
        for rel in files:
            src = root / rel
            arcname = ARCHIVE_PATH_OVERRIDES.get(rel, rel)
            total_bytes += src.stat().st_size
            info = tar.gettarinfo(str(src), arcname=arcname)
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            with src.open("rb") as fh:
                tar.addfile(info, fh)

    archive_bytes = output_path.read_bytes()
    sha256 = hashlib.sha256(archive_bytes).hexdigest()
    manifest = {
        "archive": str(output_path),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "archive_bytes": len(archive_bytes),
        "sha256": sha256,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = output_path.with_suffix("").with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build lean server deployment package for FlexBridge.")
    default_name = f"flexbridge-server-{datetime.now().strftime('%Y-%m-%d')}.tar.gz"
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR / default_name)
    args = parser.parse_args(argv)
    manifest = build_server_archive(args.repo_root, args.output)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
