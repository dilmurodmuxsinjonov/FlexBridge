"""Applications, Offers, Dual-Confirmed Placements, and `INV-08` Cross-Table Scope Service (S2.5.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class PlacementScopeError(Exception):
    """Raised when an application attempt, offer, or placement violates `INV-08` composite FK or state transition rules."""

    def __init__(self, code: str, message: str, status_code: int = 409, sqlstate: str = "23503") -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.sqlstate = sqlstate


@dataclass
class ApplicationPlacementService:
    """Manages `applications`, `application_attempts`, `offers`, and `placements` (`INV-08`)."""

    applications: dict[str, dict[str, Any]] = field(default_factory=dict)
    attempts: dict[str, dict[str, Any]] = field(default_factory=dict)
    offers: dict[str, dict[str, Any]] = field(default_factory=dict)
    placements: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create_application(
        self,
        *,
        opportunity_id: str,
        candidate_id: str,
    ) -> dict[str, Any]:
        app_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": app_id,
            "opportunity_id": opportunity_id,
            "candidate_id": candidate_id,
            "status": "SUBMITTED",
            "created_at": now,
        }
        self.applications[app_id] = record
        return dict(record)

    def create_application_attempt(
        self,
        *,
        application_id: str,
        opportunity_id: str,
        attempt_no: int = 1,
    ) -> dict[str, Any]:
        """Enforce `fk_application_attempts_app_opp` (`(application_id, opportunity_id)` composite FK, `INV-08`)."""
        app = self.applications.get(application_id)
        if not app or app["opportunity_id"] != opportunity_id:
            raise PlacementScopeError(
                code="FK_APPLICATION_ATTEMPTS_APP_OPP_VIOLATION",
                message=(
                    f"fk_application_attempts_app_opp (INV-08): application_id={application_id} "
                    f"va opportunity_id={opportunity_id} o'zaro mos emas"
                ),
                status_code=409,
                sqlstate="23503",
            )
        attempt_id = str(uuid4())
        record = {
            "id": attempt_id,
            "application_id": application_id,
            "opportunity_id": opportunity_id,
            "attempt_no": attempt_no,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.attempts[attempt_id] = record
        return dict(record)

    def create_offer(
        self,
        *,
        application_id: str,
        opportunity_id: str,
        candidate_id: str,
        offered_by: str,
    ) -> dict[str, Any]:
        """Create an offer enforcing composite scope match with `applications` (`INV-08`)."""
        app = self.applications.get(application_id)
        if (
            not app
            or app["opportunity_id"] != opportunity_id
            or app["candidate_id"] != candidate_id
        ):
            raise PlacementScopeError(
                code="FK_OFFERS_APPLICATION_SCOPE_VIOLATION",
                message="Offer application_id, opportunity_id va candidate_id bilan mos kelishi shart (INV-08)",
                status_code=409,
                sqlstate="23503",
            )
        offer_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": offer_id,
            "application_id": application_id,
            "opportunity_id": opportunity_id,
            "candidate_id": candidate_id,
            "offered_by": offered_by,
            "status": "ACCEPTED",
            "accepted_at": now,
            "created_at": now,
        }
        self.offers[offer_id] = record
        return dict(record)

    def create_placement(
        self,
        *,
        application_id: str,
        offer_id: str,
        opportunity_id: str,
        candidate_id: str,
        organization_id: str,
    ) -> dict[str, Any]:
        """Enforce `fk_placements_offer_scope` (`(offer_id, application_id, opportunity_id, candidate_id)`, `INV-08`)."""
        offer = self.offers.get(offer_id)
        if (
            not offer
            or offer["application_id"] != application_id
            or offer["opportunity_id"] != opportunity_id
            or offer["candidate_id"] != candidate_id
        ):
            raise PlacementScopeError(
                code="FK_PLACEMENTS_OFFER_SCOPE_VIOLATION",
                message=(
                    "fk_placements_offer_scope (INV-08): placement offer_id, application_id, "
                    "opportunity_id va candidate_id to'rtligi bilan mos emas"
                ),
                status_code=409,
                sqlstate="23503",
            )
        placement_id = str(uuid4())
        record = {
            "id": placement_id,
            "application_id": application_id,
            "offer_id": offer_id,
            "opportunity_id": opportunity_id,
            "candidate_id": candidate_id,
            "organization_id": organization_id,
            "status": "PENDING_START_CONFIRMATION",
            "candidate_confirmed_start_at": None,
            "org_confirmed_start_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.placements[placement_id] = record
        return dict(record)

    def confirm_placement_start(
        self,
        *,
        placement_id: str,
        party: str,
    ) -> dict[str, Any]:
        """Confirm start of work by `CANDIDATE` or `ORGANIZATION`; becomes `ACTIVE` only when both confirm."""
        placement = self.placements.get(placement_id)
        if not placement:
            raise PlacementScopeError("PLACEMENT_NOT_FOUND", "Placement topilmadi", status_code=404)

        now = datetime.now(timezone.utc).isoformat()
        if party == "CANDIDATE":
            placement["candidate_confirmed_start_at"] = now
        elif party == "ORGANIZATION":
            placement["org_confirmed_start_at"] = now
        else:
            raise PlacementScopeError("INVALID_CONFIRMATION_PARTY", "party CANDIDATE yoki ORGANIZATION bo'lishi kerak", status_code=422)

        if placement["candidate_confirmed_start_at"] and placement["org_confirmed_start_at"]:
            placement["status"] = "ACTIVE"
        return dict(placement)


placement_service = ApplicationPlacementService()
