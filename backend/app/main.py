"""FastAPI application entrypoint for FlexBridge 1.4 (S2.1.1, FIX-01, FIX-13).

Exposes:
- `GET /api/v1/health/live` (`API-X05` liveness check)
- `GET /api/v1/health/ready` (`API-X06` readiness & schema verification check)
- `GET /api/v1/meta/schema-summary` (1.4 schema, retention policy v1, and invariant status)
- Global `FinanceCircuitOpenError` handler returning HTTP `503 P1_FINANCE_CIRCUIT_OPEN` (`R-09`)
- All 132 canonical API routes from `FlexBridge_model_1_4.json` (`R-07`)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.availability import router as availability_router
from app.api.v1.billing import router as billing_router
from app.api.v1.canonical_routes import register_remaining_canonical_model_routes, router as canonical_router
from app.api.v1.files import router as files_router
from app.api.v1.governance import router as governance_router
from app.api.v1.internship_logs import router as internship_logs_router
from app.api.v1.operations import router as operations_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.placements import router as placements_router
from app.core.circuit_breaker import FinanceCircuitOpenError
from app.core.config import settings
from app.db.schema import get_retention_policies_v1, get_schema_summary

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FlexBridge 1.4 R1 Backend API",
)


@app.exception_handler(FinanceCircuitOpenError)
async def finance_circuit_open_exception_handler(
    request: Request,
    exc: FinanceCircuitOpenError,
) -> JSONResponse:
    """Return 503 Service Unavailable (`P1_FINANCE_CIRCUIT_OPEN`) when P1 finance circuit-breaker is OPEN (`FIX-13`, `R-09`)."""
    body: dict[str, Any] = {
        "detail": {
            "code": exc.code,
            "reason_code": exc.reason_code,
            "incident_id": exc.incident_id,
            "message": str(exc),
        }
    }
    if exc.invoice_id is not None:
        body["invoice_id"] = exc.invoice_id
    if exc.order_id is not None:
        body["order_id"] = exc.order_id
    return JSONResponse(status_code=503, content=body)


app.include_router(auth_router)
app.include_router(governance_router)
app.include_router(availability_router)
app.include_router(opportunities_router)
app.include_router(placements_router)
app.include_router(internship_logs_router)
app.include_router(files_router)
app.include_router(billing_router)
app.include_router(operations_router)
app.include_router(canonical_router)


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


register_remaining_canonical_model_routes(app)
