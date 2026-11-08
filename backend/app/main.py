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
from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError, OperationalError, DataError, ProgrammingError
from app.services.auth import AuthError, auth_service
from app.services.billing import BillingInvariantError
from app.services.files_quarantine import FileQuarantineError

from app.api.v1.auth import router as auth_router
from app.api.v1.iam import router as iam_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.availability import router as availability_router
from app.api.v1.billing import router as billing_router
from app.api.v1.canonical_routes import register_remaining_canonical_model_routes, router as canonical_router
from app.api.v1.files import router as files_router
from app.api.v1.governance import router as governance_router
from app.api.v1.internship_logs import router as internship_logs_router
from app.api.v1.operations import router as operations_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.placements import router as placements_router
from app.services.placements import PlacementScopeError
from app.services.internship_logs import InternshipLogScopeError
from app.services.governance import GovernanceError
from app.services.opportunities import OpportunityConstraintError
from app.services.availability import AvailabilityConstraintError
from app.core.circuit_breaker import FinanceCircuitOpenError
from app.core.config import settings
from app.db.schema import get_retention_policies_v1, get_schema_summary

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FlexBridge 1.4 R1 Backend API",
)

@app.middleware('http')
async def authentication_boundary(request: Request, call_next):
    import re
    from app.core.iam_security import SENSITIVE_ROLES
    public = {'/api/v1/auth/register','/api/v1/auth/login','/api/v1/health/live','/api/v1/health/ready',
        '/api/v1/auth/options','/api/v1/auth/challenges','/api/v1/auth/recovery','/api/v1/auth/mfa/verify','/api/v1/auth/passkeys/options','/api/v1/auth/passkeys/verify'}
    public_path=request.url.path in public or bool(re.fullmatch(r'/api/v1/auth/(?:challenges/[^/]+/(?:consume|resend)|recovery/[^/]+(?:/complete)?)',request.url.path))
    public_path = public_path or (request.method in ('GET','HEAD') and bool(re.fullmatch(r'/api/v1/organizations/[^/]+/public',request.url.path)))
    public_path = public_path or (request.method in ('GET','HEAD') and bool(re.fullmatch(r'/api/v1/invitations/[^/]+',request.url.path)))
    if request.url.path.startswith('/api/v1/') and not public_path and not request.url.path.startswith('/api/v1/webhooks/payments/'):
        value=request.headers.get('authorization','')
        if not value.startswith('Bearer '):
            return JSONResponse(status_code=401,content={'detail':{'code':'AUTH_REQUIRED'}})
        try:
            session=await run_in_threadpool(auth_service.validate_session,value[7:].strip())
            self_service=request.url.path.startswith(('/api/v1/me/security','/api/v1/me/sessions/','/api/v1/auth/sessions/')) or request.url.path=='/api/v1/auth/me'
            if set(session['roles']) & SENSITIVE_ROLES and session['assurance']!='MFA' and not self_service:
                return JSONResponse(status_code=403,content={'detail':{'code':'MFA_ENROLLMENT_REQUIRED'}})
        except AuthError as exc:
            return JSONResponse(status_code=exc.status_code,content={'detail':{'code':exc.code}})
        except (OperationalError, ProgrammingError, RuntimeError):
            return JSONResponse(status_code=503,content={'detail':{'code':'AUTH_STORAGE_UNAVAILABLE'}})
    return await call_next(request)

from app.core.iam_http import IAMHTTPMiddleware
app.add_middleware(IAMHTTPMiddleware)

@app.exception_handler(PlacementScopeError)
@app.exception_handler(InternshipLogScopeError)
@app.exception_handler(GovernanceError)
@app.exception_handler(OpportunityConstraintError)
@app.exception_handler(AvailabilityConstraintError)
async def scope_error(request,exc):
    return JSONResponse(status_code=exc.status_code,content={'detail':{'code':exc.code}})

@app.exception_handler(AuthError)
async def auth_error(request,exc):
    return JSONResponse(status_code=exc.status_code,content={'detail':{'code':exc.code}})

@app.exception_handler(BillingInvariantError)
async def billing_error(request,exc):
    return JSONResponse(status_code=409,content={'detail':{'code':str(exc)}})

@app.exception_handler(FileQuarantineError)
async def file_error(request,exc):
    return JSONResponse(status_code=exc.status_code,content={'detail':{'code':exc.code}})

@app.exception_handler(IntegrityError)
async def integrity_error(request,exc):
    return JSONResponse(status_code=409,content={'detail':{'code':'CONSTRAINT_VIOLATION'}})

@app.exception_handler(DataError)
async def data_error(request,exc):
    return JSONResponse(status_code=422,content={'detail':{'code':'INVALID_IDENTIFIER_OR_VALUE'}})

@app.exception_handler(RuntimeError)
@app.exception_handler(OperationalError)
@app.exception_handler(ProgrammingError)
async def service_error(request,exc):
    return JSONResponse(status_code=503,content={'detail':{'code':'DEPENDENCY_UNAVAILABLE'}})


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
app.include_router(iam_router)
app.include_router(candidates_router)
app.include_router(organizations_router)
app.include_router(invitations_router)
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
    from app.core.readiness import dependency_readiness
    report=dependency_readiness()
    if not report['ready']: raise HTTPException(503,detail={'code':'SERVICE_NOT_READY',**report})
    return {'status':'ready',**report}


@app.get("/api/v1/meta/schema-summary", tags=["meta"])
def meta_schema_summary() -> dict[str, Any]:
    """Return the verified 1.4 schema summary and DB-083 retention policies."""
    return {
        "summary": get_schema_summary(),
        "retention_policies_v1": get_retention_policies_v1(),
    }


register_remaining_canonical_model_routes(app)
