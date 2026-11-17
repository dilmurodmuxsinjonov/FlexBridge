"""Operator Finance and Reconciliation Service (API-115 / API-117 / CAP-030 / CAP-038).

Contracts:
- API-115: GET /api/v1/operator/reconciliation (Ledger vs Gateway reconciliation, zero customer PII)
- API-117: GET /api/v1/operator/finance-summary (Cash received, recognized revenue, deferred revenue, active subscriptions)

Invariants:
- Strict FINANCE or ADMIN platform role verification; non-staff denied with 403 PERMISSION_DENIED.
- Zero customer PII leakage in reconciliation and summary data.
- Discrepancy detection between internal billing_ledger and external payment gateways/refunds.
- Date window filtering (start_date, end_date) and keyset cursor pagination.
- Pure R1 scope without freelance logic.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text

from app.api.dependencies import ActorContext
from app.db.storage import now, table, transaction
from app.services.authority import account_authority


FINANCE_ROLES = frozenset({"FINANCE", "ADMIN"})


class FinanceError(Exception):
    """Base exception for operator finance service."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class FinanceForbiddenError(FinanceError):
    def __init__(self, code: str = "PERMISSION_DENIED", message: str = "Operator huquqi talab qilinadi") -> None:
        super().__init__(code=code, message=message, status_code=403)


class FinanceValidationError(FinanceError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=422)


class OperatorFinanceService:
    """Enterprise finance and billing reconciliation service."""

    def _verify_finance_authority(self, conn: Any, actor: ActorContext) -> None:
        """Verify that caller holds platform role FINANCE or ADMIN."""
        # 1. Quick check in actor.roles
        actor_roles = set(actor.roles or [])
        if FINANCE_ROLES.intersection(actor_roles):
            return

        # 2. Database verification via platform_role_grants
        t_grants = table("platform_role_grants")
        t_catalog = table("role_catalog")
        now_utc = now()

        found = conn.execute(
            select(t_grants.c.id)
            .select_from(t_grants.join(t_catalog, t_grants.c.role_id == t_catalog.c.id))
            .where(
                t_grants.c.user_id == str(actor.user_id),
                t_grants.c.revoked_at.is_(None),
                t_grants.c.expires_at > now_utc,
                t_catalog.c.scope_kind == "PLATFORM",
                t_catalog.c.code.in_(FINANCE_ROLES),
            )
        ).first()

        if not found:
            raise FinanceForbiddenError("PERMISSION_DENIED", "Ushbu amal faqat Moliya (FINANCE) operatorlari uchun ruxsat etilgan")

    def _parse_date(self, val: str | None, param_name: str) -> datetime | None:
        """Parse ISO-8601 or YYYY-MM-DD date parameter safely."""
        if not val:
            return None
        val_clean = val.strip()
        try:
            if len(val_clean) == 10:
                return datetime.strptime(val_clean, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(val_clean.replace("Z", "+00:00"))
        except Exception as exc:
            raise FinanceValidationError(
                "INVALID_DATE_FORMAT", f"{param_name} sana formati noto'g'ri (YYYY-MM-DD yoki ISO-8601 talab etiladi)"
            ) from exc

    def _encode_cursor(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    def _decode_cursor(self, cursor: str) -> dict[str, Any]:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            raw = base64.urlsafe_b64decode(padded.encode("ascii"))
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Cursor payload is not a JSON object")
            return data
        except Exception as exc:
            raise FinanceValidationError("INVALID_CURSOR", "Yaroqsiz sahifalash kursori") from exc

    def get_reconciliation(
        self,
        *,
        actor: ActorContext,
        start_date: str | None = None,
        end_date: str | None = None,
        provider: str | None = None,
        discrepancy_only: bool = False,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """API-115: Reconcile billing ledger entries with payment attempts and refunds (zero customer PII)."""
        dt_start = self._parse_date(start_date, "start_date")
        dt_end = self._parse_date(end_date, "end_date")

        if dt_start and dt_end and dt_start > dt_end:
            raise FinanceValidationError("INVALID_DATE_RANGE", "start_date end_date dan katta bo'lishi mumkin emas")

        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        with transaction() as conn:
            account_authority(conn, actor)
            self._verify_finance_authority(conn, actor)

            t_ledger = table("billing_ledger")
            t_pa = table("payment_attempts")
            t_inv = table("invoices")
            t_ref = table("refunds")

            conditions: list[Any] = []

            if dt_start:
                conditions.append(t_ledger.c.occurred_at >= dt_start)
            if dt_end:
                conditions.append(t_ledger.c.occurred_at <= dt_end)

            if provider:
                conditions.append(t_pa.c.provider == provider.strip().upper())

            # Keyset pagination cursor over (occurred_at DESC, id DESC)
            if cursor:
                cursor_data = self._decode_cursor(cursor)
                try:
                    cursor_occurred_at = datetime.fromisoformat(cursor_data["o"])
                    cursor_id = str(UUID(cursor_data["i"]))
                except (KeyError, ValueError, TypeError) as exc:
                    raise FinanceValidationError("INVALID_CURSOR", "Yaroqsiz sahifalash kursori") from exc

                conditions.append(
                    or_(
                        t_ledger.c.occurred_at < cursor_occurred_at,
                        and_(
                            t_ledger.c.occurred_at == cursor_occurred_at,
                            t_ledger.c.id < cursor_id,
                        ),
                    )
                )

            where_clause = and_(*conditions) if conditions else True

            # Query with joins
            query = (
                select(
                    t_ledger.c.id.label("ledger_entry_id"),
                    t_ledger.c.occurred_at,
                    t_ledger.c.entry_kind,
                    t_ledger.c.organization_id,
                    t_ledger.c.order_id,
                    t_ledger.c.payment_attempt_id,
                    t_ledger.c.refund_id,
                    t_ledger.c.amount.label("ledger_amount"),
                    t_ledger.c.currency.label("ledger_currency"),
                    t_pa.c.id.label("pa_id"),
                    t_pa.c.provider,
                    t_pa.c.provider_transaction_id,
                    t_pa.c.amount.label("attempt_amount"),
                    t_pa.c.currency.label("attempt_currency"),
                    t_pa.c.status.label("attempt_status"),
                    t_inv.c.id.label("invoice_id"),
                    t_inv.c.amount.label("invoice_amount"),
                    t_inv.c.paid_at.label("invoice_paid_at"),
                    t_ref.c.id.label("ref_id"),
                    t_ref.c.amount.label("refund_amount"),
                    t_ref.c.status.label("refund_status"),
                )
                .select_from(
                    t_ledger
                    .outerjoin(t_pa, t_pa.c.id == t_ledger.c.payment_attempt_id)
                    .outerjoin(t_inv, t_inv.c.order_id == t_ledger.c.order_id)
                    .outerjoin(t_ref, t_ref.c.id == t_ledger.c.refund_id)
                )
                .where(where_clause)
                .order_by(t_ledger.c.occurred_at.desc(), t_ledger.c.id.desc())
                .limit(limit + 1)
            )

            rows = conn.execute(query).mappings().all()

            has_more = len(rows) > limit
            page_rows = rows[:limit]

            next_cursor = None
            if has_more and page_rows:
                last_r = page_rows[-1]
                next_cursor = self._encode_cursor({
                    "o": last_r["occurred_at"].isoformat(),
                    "i": str(last_r["ledger_entry_id"]),
                })

            items: list[dict[str, Any]] = []
            total_discrepancies = 0

            for r in page_rows:
                discrepancy_flags: list[str] = []
                entry_kind = r["entry_kind"]
                ledger_amount = float(r["ledger_amount"]) if r["ledger_amount"] is not None else 0.0

                if entry_kind == "PAYMENT_CAPTURED":
                    if r["payment_attempt_id"] and not r["pa_id"]:
                        discrepancy_flags.append("missing_gateway_attempt")
                    elif r["attempt_amount"] is not None:
                        attempt_amount = float(r["attempt_amount"])
                        if abs(ledger_amount - attempt_amount) > 0.01:
                            discrepancy_flags.append("amount_mismatch")
                    if r["attempt_status"] and r["attempt_status"] != "CAPTURED":
                        discrepancy_flags.append("status_discrepancy")

                elif entry_kind == "REFUND_EXECUTED":
                    if r["refund_id"] and not r["ref_id"]:
                        discrepancy_flags.append("missing_refund_record")
                    elif r["refund_amount"] is not None:
                        ref_amount = float(r["refund_amount"])
                        if abs(abs(ledger_amount) - ref_amount) > 0.01:
                            discrepancy_flags.append("amount_mismatch")
                    if r["refund_status"] and r["refund_status"] != "REFUNDED":
                        discrepancy_flags.append("status_discrepancy")

                is_discrepant = len(discrepancy_flags) > 0
                if is_discrepant:
                    total_discrepancies += 1

                if discrepancy_only and not is_discrepant:
                    continue

                items.append({
                    "ledger_entry_id": str(r["ledger_entry_id"]),
                    "occurred_at": r["occurred_at"].isoformat() if r["occurred_at"] else None,
                    "entry_kind": entry_kind,
                    "organization_id": str(r["organization_id"]) if r["organization_id"] else None,
                    "order_id": str(r["order_id"]) if r["order_id"] else None,
                    "payment_attempt_id": str(r["payment_attempt_id"]) if r["payment_attempt_id"] else None,
                    "refund_id": str(r["refund_id"]) if r["refund_id"] else None,
                    "provider": r["provider"],
                    "provider_transaction_id": r["provider_transaction_id"],
                    "ledger_amount_uzs": ledger_amount,
                    "gateway_amount_uzs": float(r["attempt_amount"]) if r["attempt_amount"] is not None else None,
                    "currency": r["ledger_currency"] or "UZS",
                    "ledger_status": "CAPTURED" if entry_kind == "PAYMENT_CAPTURED" else ("REFUNDED" if entry_kind == "REFUND_EXECUTED" else "PROCESSED"),
                    "gateway_status": r["attempt_status"] or r["refund_status"],
                    "is_discrepant": is_discrepant,
                    "discrepancy_flags": discrepancy_flags,
                })

            # Total ledger count in this window
            count_conditions = []
            if dt_start:
                count_conditions.append(t_ledger.c.occurred_at >= dt_start)
            if dt_end:
                count_conditions.append(t_ledger.c.occurred_at <= dt_end)
            count_where = and_(*count_conditions) if count_conditions else True
            total_count = conn.execute(
                select(func.count()).select_from(t_ledger).where(count_where)
            ).scalar() or 0

            return {
                "contract_id": "API-115",
                "capability": "FINANCE",
                "items": items,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "total_records": total_count,
                "summary": {
                    "total_reconciled": len(items),
                    "total_discrepancies": total_discrepancies,
                    "matched_count": len(items) - total_discrepancies,
                },
            }

    def get_finance_summary(
        self,
        *,
        actor: ActorContext,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """API-117: Financial accounting summary (cash, recognized revenue, deferred revenue, active subscriptions)."""
        dt_start = self._parse_date(start_date, "start_date")
        dt_end = self._parse_date(end_date, "end_date")

        if dt_start and dt_end and dt_start > dt_end:
            raise FinanceValidationError("INVALID_DATE_RANGE", "start_date end_date dan katta bo'lishi mumkin emas")

        now_utc = now()
        cutoff_date = dt_end if dt_end and dt_end < now_utc else now_utc

        with transaction() as conn:
            account_authority(conn, actor)
            self._verify_finance_authority(conn, actor)

            t_inv = table("invoices")
            t_ref = table("refunds")
            t_ent = table("service_entitlements")
            t_ord = table("orders")

            # 1. Cash received: paid invoices
            cash_conds = [t_inv.c.paid_at.is_not(None)]
            if dt_start:
                cash_conds.append(t_inv.c.paid_at >= dt_start)
            if dt_end:
                cash_conds.append(t_inv.c.paid_at <= dt_end)

            cash_received = conn.execute(
                select(func.coalesce(func.sum(t_inv.c.amount), 0)).where(and_(*cash_conds))
            ).scalar() or 0.0

            # 2. Refunded amount: executed refunds
            ref_conds = [t_ref.c.status == "REFUNDED"]
            if dt_start:
                ref_conds.append(t_ref.c.resolved_at >= dt_start)
            if dt_end:
                ref_conds.append(t_ref.c.resolved_at <= dt_end)

            refunded_amount = conn.execute(
                select(func.coalesce(func.sum(t_ref.c.amount), 0)).where(and_(*ref_conds))
            ).scalar() or 0.0

            # 3. Active subscriptions count
            active_subscriptions = conn.execute(
                select(func.count(t_ent.c.id)).where(
                    t_ent.c.status == "ACTIVE",
                    t_ent.c.starts_at <= now_utc,
                    t_ent.c.ends_at > now_utc,
                )
            ).scalar() or 0

            # 4. Recognized revenue & deferred revenue per service entitlement
            ent_query = (
                select(
                    t_ent.c.id,
                    t_ent.c.service_kind,
                    t_ent.c.status,
                    t_ent.c.starts_at,
                    t_ent.c.ends_at,
                    t_ord.c.amount.label("order_amount"),
                )
                .select_from(t_ent.join(t_ord, t_ord.c.id == t_ent.c.order_id))
                .where(t_ord.c.status == "COMPLETED")
            )
            ent_rows = conn.execute(ent_query).mappings().all()

            total_recognized = 0.0
            total_deferred = 0.0
            plans_stats: dict[str, dict[str, Any]] = {}

            for r in ent_rows:
                order_amt = float(r["order_amount"]) if r["order_amount"] else 0.0
                plan = r["service_kind"] or "UNKNOWN"

                if plan not in plans_stats:
                    plans_stats[plan] = {
                        "plan_code": plan,
                        "total_entitlements": 0,
                        "active_count": 0,
                        "cash_received_uzs": 0.0,
                        "recognized_revenue_uzs": 0.0,
                        "deferred_revenue_uzs": 0.0,
                    }

                plans_stats[plan]["total_entitlements"] += 1
                plans_stats[plan]["cash_received_uzs"] += order_amt

                starts_at = r["starts_at"]
                ends_at = r["ends_at"]

                if starts_at and ends_at and ends_at > starts_at:
                    total_duration = max((ends_at - starts_at).total_seconds() / 86400.0, 1.0)
                    if cutoff_date < starts_at:
                        elapsed = 0.0
                    elif cutoff_date > ends_at:
                        elapsed = total_duration
                    else:
                        elapsed = (cutoff_date - starts_at).total_seconds() / 86400.0

                    fraction = min(max(elapsed / total_duration, 0.0), 1.0)
                    rec = round(order_amt * fraction, 2)
                    def_amt = round(order_amt - rec, 2) if (r["status"] == "ACTIVE" and ends_at > cutoff_date) else 0.0
                else:
                    rec = order_amt
                    def_amt = 0.0

                if r["status"] == "ACTIVE" and starts_at <= now_utc and ends_at > now_utc:
                    plans_stats[plan]["active_count"] += 1

                plans_stats[plan]["recognized_revenue_uzs"] += rec
                plans_stats[plan]["deferred_revenue_uzs"] += def_amt

                total_recognized += rec
                total_deferred += def_amt

            cash_float = float(cash_received)
            refund_float = float(refunded_amount)
            net_revenue = round(cash_float - refund_float, 2)

            return {
                "contract_id": "API-117",
                "capability": "FINANCE_REPORT",
                "period": {
                    "start_date": dt_start.isoformat() if dt_start else None,
                    "end_date": dt_end.isoformat() if dt_end else None,
                },
                "cash_received_uzs": cash_float,
                "recognized_revenue_uzs": round(total_recognized, 2),
                "deferred_revenue_uzs": round(total_deferred, 2),
                "refunded_amount_uzs": refund_float,
                "net_revenue_uzs": net_revenue,
                "active_subscriptions_count": int(active_subscriptions),
                "plans_breakdown": list(plans_stats.values()),
                "currency": "UZS",
            }


operator_finance_service = OperatorFinanceService()
