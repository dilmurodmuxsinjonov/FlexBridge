"""Configuration settings for FlexBridge 1.4 Backend (S2.1.1).

Strictly aligned with `FlexBridge_1_4_tuzatilgan_texnik_topshiriq.pdf` (pages 2-8)
and user decision `Q-010` (`T-007` Variant A, `T-008` Variant A).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SPECS_V1_3_DIR = REPO_ROOT / "specs" / "v1_3"
SPECS_V1_4_DIR = REPO_ROOT / "specs" / "v1_4"

FORBIDDEN_PDF_TOKENS: tuple[str, ...] = (
    "/JS",
    "/JavaScript",
    "/AA",
    "/OpenAction",
    "/Launch",
    "/EmbeddedFiles",
    "/RichMedia",
    "/XFA",
)


@dataclass(frozen=True)
class Settings:
    """Immutable runtime and architectural configuration for FlexBridge 1.4."""

    app_name: str = "FlexBridge API"
    app_version: str = "1.4.0"
    api_prefix: str = "/api/v1"

    # Database & PgBouncer capacity parameters (1.4 PDF section 5)
    pg_max_connections: int = 80
    pgbouncer_pool_mode: str = "transaction"
    pgbouncer_default_pool_size: int = 20
    pgbouncer_max_client_conn: int = 400

    # Session & Role/Membership cache (INV-15, AC-017)
    permission_cache_ttl_seconds: int = 15
    immediate_revoke_invalidation: bool = True

    # Private Object Store & Malware/PDF Quarantine pipeline (INV-14, AC-042)
    quarantine_prefix: str = "quarantine/"
    signed_url_ttl_seconds: int = 60
    file_scan_timeout_seconds: int = 30
    pdf_max_pages: int = 50
    pdf_max_objects: int = 5000
    pdf_max_uncompressed_stream_mb: int = 20
    forbidden_pdf_tokens: tuple[str, ...] = field(default=FORBIDDEN_PDF_TOKENS)

    # Operational resilience & incident response (1.4 PDF section 7)
    p1_finance_circuit_breaker_enabled: bool = True
    rpo_hours: int = 24
    rto_hours: int = 4

    # Canonical specification paths
    schema_sql_path: Path = REPO_ROOT / "FlexBridge_1_4_schema.sql"
    model_json_path: Path = SPECS_V1_4_DIR / "FlexBridge_model_1_4.json"
    verifier_script_path: Path = SPECS_V1_4_DIR / "verify_v1_4_schema.mjs"
    verification_report_path: Path = SPECS_V1_4_DIR / "v1_4_schema_verification.json"


settings = Settings()
