"""Support tickets and messaging service (API-063 / API-064 / CAP-033 / DB-080 / DB-081 / AC-032).

Implements canonical contracts:
- `API-063`: `GET /api/v1/me/support-tickets` (List personal support tickets) and `POST /api/v1/me/support-tickets` (Create ticket).
- `API-064`: `POST /api/v1/support-tickets/{id}/messages` (Reply to ticket) and `GET /api/v1/support-tickets/{id}/messages` (Conversation thread).
- Enforces strict role-based access: requesters only see their tickets and public messages; staff sees full thread and internal notes.
- Priority SLA response tracking (`first_response_due_at`).
- Append-only audit trails (`AppendOnlyAuditStore`).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select

from app.api.dependencies import ActorContext
from app.core.audit import AppendOnlyAuditStore
from app.db.storage import now, table, transaction
from app.services.authority import account_authority
from app.services.placements import insert_row


VALID_CATEGORIES = frozenset({"GENERAL", "TECHNICAL", "BILLING", "ACCOUNT", "PLACEMENT"})
VALID_PRIORITIES = frozenset({"LOW", "NORMAL", "HIGH", "URGENT"})
PRIORITY_SLA_HOURS = {"URGENT": 4, "HIGH": 12, "NORMAL": 24, "LOW": 48}
VALID_STATUSES = frozenset({"OPEN", "PENDING_SUPPORT", "PENDING_USER", "RESOLVED", "CLOSED"})
STAFF_ROLES = frozenset({"SUPPORT", "ADMIN", "MODERATOR"})


class SupportTicketError(Exception):
    """Base exception for support ticket operations."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class SupportTicketNotFoundError(SupportTicketError):
    def __init__(self, message: str = "Support ticket topilmadi") -> None:
        super().__init__(code="SUPPORT_TICKET_NOT_FOUND", message=message, status_code=404)


class SupportTicketForbiddenError(SupportTicketError):
    def __init__(self, message: str = "Support ticketga kirish taqiqlangan") -> None:
        super().__init__(code="SUPPORT_TICKET_FORBIDDEN", message=message, status_code=403)


class SupportTicketValidationError(SupportTicketError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=422)


class SupportTicketConflictError(SupportTicketError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=409)


class SupportTicketsService:
    """Enterprise support tickets and customer messaging service."""

    def _is_staff(self, actor: ActorContext) -> bool:
        return bool(STAFF_ROLES.intersection(set(actor.roles or [])))

    def create_ticket(
        self,
        *,
        actor: ActorContext,
        subject: str,
        body: str,
        category: str = "GENERAL",
        priority: str = "NORMAL",
        file_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new support ticket and post its initial message."""
        subj_clean = (subject or "").strip()
        body_clean = (body or "").strip()
        cat_clean = (category or "").strip().upper()
        pri_clean = (priority or "").strip().upper()

        if len(subj_clean) < 3 or len(subj_clean) > 255:
            raise SupportTicketValidationError(
                "INVALID_SUBJECT", "Ticket mavzusi 3 dan 255 belgigacha bo'lishi kerak"
            )
        if len(body_clean) < 5 or len(body_clean) > 4000:
            raise SupportTicketValidationError(
                "INVALID_BODY", "Ticket xabari 5 dan 4000 belgigacha bo'lishi kerak"
            )
        if cat_clean not in VALID_CATEGORIES:
            raise SupportTicketValidationError(
                "INVALID_CATEGORY",
                f"Kategoriya noto'g'ri. Mavjud kategoriyalar: {', '.join(sorted(VALID_CATEGORIES))}",
            )
        if pri_clean not in VALID_PRIORITIES:
            raise SupportTicketValidationError(
                "INVALID_PRIORITY",
                f"Muhimlik darajasi noto'g'ri. Mavjud darajalar: {', '.join(sorted(VALID_PRIORITIES))}",
            )

        with transaction() as conn:
            account_authority(conn, actor)
            user_id = str(actor.user_id)

            now_utc = now()
            sla_hours = PRIORITY_SLA_HOURS.get(pri_clean, 24)
            due_utc = now_utc + timedelta(hours=sla_hours)

            ticket_id = str(uuid4())
            msg_id = str(uuid4())

            # 1. Insert support ticket
            insert_row(
                conn,
                "support_tickets",
                id=ticket_id,
                created_at=now_utc,
                updated_at=now_utc,
                requester_id=user_id,
                category=cat_clean,
                priority=pri_clean,
                status="OPEN",
                assignee_id=None,
                subject=subj_clean,
                first_response_due_at=due_utc,
                resolved_at=None,
            )

            # 2. Insert initial message
            insert_row(
                conn,
                "support_messages",
                id=msg_id,
                created_at=now_utc,
                updated_at=now_utc,
                ticket_id=ticket_id,
                author_id=user_id,
                body=body_clean,
                file_id=str(UUID(file_id)) if file_id else None,
                internal=False,
            )

            # 3. Append-only audit logging
            AppendOnlyAuditStore().append_audit_event(
                actor_id=user_id,
                action="SUPPORT_TICKET_CREATED",
                entity_type="support_ticket",
                entity_id=ticket_id,
                metadata={
                    "category": cat_clean,
                    "priority": pri_clean,
                    "first_response_due_at": due_utc.isoformat(),
                },
            )

            return {
                "id": ticket_id,
                "requester_id": user_id,
                "category": cat_clean,
                "priority": pri_clean,
                "status": "OPEN",
                "assignee_id": None,
                "subject": subj_clean,
                "first_response_due_at": due_utc.isoformat(),
                "resolved_at": None,
                "created_at": now_utc.isoformat(),
                "updated_at": now_utc.isoformat(),
                "initial_message": {
                    "id": msg_id,
                    "ticket_id": ticket_id,
                    "author_id": user_id,
                    "body": body_clean,
                    "file_id": file_id,
                    "internal": False,
                    "created_at": now_utc.isoformat(),
                },
            }

    def get_my_tickets(
        self,
        *,
        actor: ActorContext,
        status: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Canonical API-063: List support tickets for authenticated user."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        with transaction() as conn:
            account_authority(conn, actor)
            user_id = str(actor.user_id)

            t_tickets = table("support_tickets")
            t_msgs = table("support_messages")

            conditions = [t_tickets.c.requester_id == user_id]

            if status:
                s_clean = status.strip().upper()
                if s_clean in VALID_STATUSES:
                    conditions.append(t_tickets.c.status == s_clean)

            if category:
                c_clean = category.strip().upper()
                if c_clean in VALID_CATEGORIES:
                    conditions.append(t_tickets.c.category == c_clean)

            where_clause = and_(*conditions)

            # Total count
            total_count = conn.execute(
                select(func.count()).select_from(t_tickets).where(where_clause)
            ).scalar() or 0

            # Message count subquery (visible user messages)
            msg_count_subq = (
                select(func.count(t_msgs.c.id))
                .where(
                    t_msgs.c.ticket_id == t_tickets.c.id,
                    t_msgs.c.internal.is_(False),
                )
                .scalar_subquery()
                .label("messages_count")
            )

            query = (
                select(t_tickets, msg_count_subq)
                .where(where_clause)
                .order_by(t_tickets.c.updated_at.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )

            rows = conn.execute(query).mappings().all()

            items = [
                {
                    "id": str(r["id"]),
                    "requester_id": str(r["requester_id"]),
                    "category": r["category"],
                    "priority": r["priority"],
                    "status": r["status"],
                    "assignee_id": str(r["assignee_id"]) if r["assignee_id"] else None,
                    "subject": r["subject"],
                    "first_response_due_at": r["first_response_due_at"].isoformat() if r["first_response_due_at"] else None,
                    "resolved_at": r["resolved_at"].isoformat() if r["resolved_at"] else None,
                    "messages_count": int(r["messages_count"]),
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
                }
                for r in rows
            ]

            return {
                "contract_id": "API-063",
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "items": items,
            }

    def post_message(
        self,
        *,
        actor: ActorContext,
        ticket_id: str,
        body: str,
        file_id: str | None = None,
        internal: bool = False,
    ) -> dict[str, Any]:
        """Canonical API-064: Post message to support ticket thread."""
        body_clean = (body or "").strip()
        if len(body_clean) < 1 or len(body_clean) > 4000:
            raise SupportTicketValidationError(
                "INVALID_BODY", "Xabar matni 1 dan 4000 belgigacha bo'lishi kerak"
            )

        with transaction() as conn:
            account_authority(conn, actor)
            user_id = str(actor.user_id)
            is_staff = self._is_staff(actor)

            # Regular users cannot write internal operator notes
            if internal and not is_staff:
                raise SupportTicketForbiddenError("Foydalanuvchilar ichki xizmat qaydlarini yoza olmaydi")

            t_tickets = table("support_tickets")
            ticket = conn.execute(
                select(t_tickets).where(t_tickets.c.id == ticket_id).with_for_update()
            ).mappings().first()

            if not ticket:
                raise SupportTicketNotFoundError("Support ticket topilmadi")

            # Access validation: author must be requester or platform staff
            if str(ticket["requester_id"]) != user_id and not is_staff:
                raise SupportTicketForbiddenError("Begona ticketga xabar yozish taqiqlanadi")

            if ticket["status"] == "CLOSED":
                raise SupportTicketConflictError(
                    "TICKET_CLOSED", "Yopilgan ticketga yangi xabar yozib bo'lmaydi"
                )

            now_utc = now()
            msg_id = str(uuid4())

            # Determine new status based on author
            if str(ticket["requester_id"]) == user_id:
                new_status = "PENDING_SUPPORT"
            elif is_staff and not internal:
                new_status = "PENDING_USER"
            else:
                new_status = ticket["status"]

            # 1. Insert message
            insert_row(
                conn,
                "support_messages",
                id=msg_id,
                created_at=now_utc,
                updated_at=now_utc,
                ticket_id=ticket_id,
                author_id=user_id,
                body=body_clean,
                file_id=str(UUID(file_id)) if file_id else None,
                internal=internal,
            )

            # 2. Update ticket status & updated_at
            conn.execute(
                t_tickets.update()
                .where(t_tickets.c.id == ticket_id)
                .values(status=new_status, updated_at=now_utc)
            )

            # 3. Append-only audit event
            AppendOnlyAuditStore().append_audit_event(
                actor_id=user_id,
                action="SUPPORT_MESSAGE_POSTED",
                entity_type="support_ticket",
                entity_id=ticket_id,
                metadata={"message_id": msg_id, "internal": internal, "new_status": new_status},
            )

            return {
                "id": msg_id,
                "ticket_id": ticket_id,
                "author_id": user_id,
                "body": body_clean,
                "file_id": file_id,
                "internal": internal,
                "ticket_status": new_status,
                "created_at": now_utc.isoformat(),
            }

    def get_ticket_messages(
        self,
        *,
        actor: ActorContext,
        ticket_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Retrieve conversation thread for support ticket."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 50

        with transaction() as conn:
            account_authority(conn, actor)
            user_id = str(actor.user_id)
            is_staff = self._is_staff(actor)

            t_tickets = table("support_tickets")
            t_msgs = table("support_messages")

            ticket = conn.execute(
                select(t_tickets).where(t_tickets.c.id == ticket_id)
            ).mappings().first()

            if not ticket:
                raise SupportTicketNotFoundError("Support ticket topilmadi")

            if str(ticket["requester_id"]) != user_id and not is_staff:
                raise SupportTicketForbiddenError("Begona ticket xabarlarini ko'rish taqiqlanadi")

            conditions = [t_msgs.c.ticket_id == ticket_id]

            # Requesters never see internal staff notes (AC-032 / DB-081)
            if not is_staff:
                conditions.append(t_msgs.c.internal.is_(False))

            where_clause = and_(*conditions)

            total_count = conn.execute(
                select(func.count()).select_from(t_msgs).where(where_clause)
            ).scalar() or 0

            query = (
                select(t_msgs)
                .where(where_clause)
                .order_by(t_msgs.c.created_at.asc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )

            rows = conn.execute(query).mappings().all()

            messages = [
                {
                    "id": str(r["id"]),
                    "ticket_id": str(r["ticket_id"]),
                    "author_id": str(r["author_id"]),
                    "body": r["body"],
                    "file_id": str(r["file_id"]) if r["file_id"] else None,
                    "internal": bool(r["internal"]),
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]

            return {
                "ticket_id": ticket_id,
                "ticket_status": ticket["status"],
                "subject": ticket["subject"],
                "total_messages": total_count,
                "page": page,
                "page_size": page_size,
                "messages": messages,
            }


support_tickets_service = SupportTicketsService()
