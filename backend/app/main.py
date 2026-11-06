"""FastAPI application entrypoint for FlexBridge 1.4 (S2.1.1).

Exposes:
- `GET /api/v1/health/live` (`API-X05` liveness check)
- `GET /api/v1/health/ready` (`API-X06` readiness & schema verification check)
- `GET /api/v1/meta/schema-summary` (1.4 schema, retention policy v1, and invariant status)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException

from app.api.v1.auth import router as auth_router
from app.core.config import settings
from app.db.schema import get_retention_policies_v1, get_schema_summary

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FlexBridge 1.4 R1 Backend API",
)
app.include_router(auth_router)


@app.get("/api/v1/health/live", tags=["health"])
def health_live() -> dict[str, Any]:
    """API-X05: Liveness probe endpoint."""
    return {
        "status": "alive",
        "service": settings.app_name,
        "version": settings.app_version,
        "contract_id": "API-X05",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/health/ready", tags=["health"])
def health_ready() -> dict[str, Any]:
    """API-X06: Readiness probe verifying 1.4 schema artifacts and PostgreSQL invariant checks."""
    summary = get_schema_summary()
    pg_ver = summary["postgres_verification"]
    counts = summary["counts"]

    is_ready = (
        summary["schema_sql_exists"]
        and counts.get("tables") == 94
        and counts.get("fields") == 935
        and counts.get("foreign_keys") == 214
        and counts.get("reference_errors") == 0
        and pg_ver.get("all_checks_passed") is True
    )
    if not is_ready:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SERVICE_NOT_READY",
                "contract_id": "API-X06",
                "summary": summary,
            },
        )

    return {
        "status": "ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "contract_id": "API-X06",
        "p1_finance_circuit_breaker_enabled": settings.p1_finance_circuit_breaker_enabled,
        "schema_counts": counts,
        "postgres_verification": pg_ver,
    }


@app.get("/api/v1/meta/schema-summary", tags=["meta"])
def meta_schema_summary() -> dict[str, Any]:
    """Return the verified 1.4 schema summary and DB-083 retention policies."""
    return {
        "summary": get_schema_summary(),
        "retention_policies_v1": get_retention_policies_v1(),
    }
