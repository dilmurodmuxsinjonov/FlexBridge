"""Atomic transaction and DEFERRABLE constraint manager for FlexBridge 1.4 (S2.1.2).

Enforces `INV-06` / 1.4 PDF section 3.4:
Circular foreign keys (`opportunities <-> opportunity_revisions`, `daily_logs <-> log_revisions`,
`threads <-> messages`) must be inserted/updated inside a single atomic transaction where
deferred constraints are validated via `SET CONSTRAINTS ALL IMMEDIATE` before `COMMIT`.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generator
from uuid import uuid4


class ConstraintViolationError(Exception):
    """Raised when a deferred or immediate database constraint fails validation."""

    def __init__(self, code: str, message: str, sqlstate: str = "23503") -> None:
        super().__init__(message)
        self.code = code
        self.sqlstate = sqlstate


@dataclass
class DeferredUnitOfWork:
    """In-memory transactional unit of work modeling PostgreSQL DEFERRABLE INITIALLY DEFERRED semantics."""

    opportunities: dict[str, dict[str, Any]] = field(default_factory=dict)
    opportunity_revisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    daily_logs: dict[str, dict[str, Any]] = field(default_factory=dict)
    log_revisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    threads: dict[str, dict[str, Any]] = field(default_factory=dict)
    messages: dict[str, dict[str, Any]] = field(default_factory=dict)
    sql_trace: list[str] = field(default_factory=list)

    @contextmanager
    def atomic_deferred(self) -> Generator["DeferredUnitOfWork", None, None]:
        """Execute a block in a transaction with `SET CONSTRAINTS ALL IMMEDIATE` before `COMMIT`."""
        snap_opps = {k: dict(v) for k, v in self.opportunities.items()}
        snap_opp_revs = {k: dict(v) for k, v in self.opportunity_revisions.items()}
        snap_logs = {k: dict(v) for k, v in self.daily_logs.items()}
        snap_log_revs = {k: dict(v) for k, v in self.log_revisions.items()}
        snap_threads = {k: dict(v) for k, v in self.threads.items()}
        snap_msgs = {k: dict(v) for k, v in self.messages.items()}

        self.sql_trace.append("BEGIN;")
        try:
            yield self
            self.sql_trace.append("SET CONSTRAINTS ALL IMMEDIATE;")
            self._validate_deferred_constraints()
            self.sql_trace.append("COMMIT;")
        except Exception:
            self.opportunities = snap_opps
            self.opportunity_revisions = snap_opp_revs
            self.daily_logs = snap_logs
            self.log_revisions = snap_log_revs
            self.threads = snap_threads
            self.messages = snap_msgs
            self.sql_trace.append("ROLLBACK;")
            raise

    def _validate_deferred_constraints(self) -> None:
        """Verify all circular foreign keys resolve cleanly at commit boundary."""
        for opp_id, opp in self.opportunities.items():
            rev_id = opp.get("current_revision_id")
            if not rev_id or rev_id not in self.opportunity_revisions:
                raise ConstraintViolationError(
                    code="FK_OPPORTUNITIES_CURRENT_REVISION_DEFERRABLE",
                    message=f"Opportunity {opp_id} references missing revision {rev_id}",
                )
            rev = self.opportunity_revisions[rev_id]
            if rev.get("opportunity_id") != opp_id:
                raise ConstraintViolationError(
                    code="FK_OPPORTUNITY_REVISION_SCOPE_MISMATCH",
                    message=f"Revision {rev_id} belongs to opportunity {rev.get('opportunity_id')}, not {opp_id}",
                )

        for rev_id, rev in self.opportunity_revisions.items():
            opp_id = rev.get("opportunity_id")
            if not opp_id or opp_id not in self.opportunities:
                raise ConstraintViolationError(
                    code="FK_OPPORTUNITY_REVISIONS_OPPORTUNITY",
                    message=f"Opportunity revision {rev_id} references missing opportunity {opp_id}",
                )

        for log_id, log_row in self.daily_logs.items():
            rev_id = log_row.get("current_revision_id")
            if not rev_id or rev_id not in self.log_revisions:
                raise ConstraintViolationError(
                    code="FK_DAILY_LOGS_CURRENT_REVISION_DEFERRABLE",
                    message=f"Daily log {log_id} references missing log_revision {rev_id}",
                )
            rev = self.log_revisions[rev_id]
            if rev.get("daily_log_id") != log_id:
                raise ConstraintViolationError(
                    code="FK_LOG_REVISION_SCOPE_MISMATCH",
                    message=f"Log revision {rev_id} does not belong to daily_log {log_id}",
                )

        for thread_id, thread in self.threads.items():
            msg_id = thread.get("last_message_id")
            if msg_id is not None:
                if msg_id not in self.messages:
                    raise ConstraintViolationError(
                        code="FK_THREADS_LAST_MESSAGE_DEFERRABLE",
                        message=f"Thread {thread_id} references missing last_message_id {msg_id}",
                    )
                if self.messages[msg_id].get("thread_id") != thread_id:
                    raise ConstraintViolationError(
                        code="FK_MESSAGE_THREAD_MISMATCH",
                        message=f"Message {msg_id} does not belong to thread {thread_id}",
                    )

    def create_opportunity_with_initial_revision(
        self,
        *,
        organization_id: str,
        created_by: str,
        title: str,
        contract_type: str = "LABOR_PART_TIME",
        compensation_type: str = "HOURLY",
        hourly_rate: int | None = 35000,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Atomically create an `opportunities` row and its initial `opportunity_revisions` row."""
        opp_id = str(uuid4())
        rev_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with self.atomic_deferred():
            opp = {
                "id": opp_id,
                "organization_id": organization_id,
                "current_revision_id": rev_id,
                "status": "DRAFT",
                "created_at": now,
            }
            rev = {
                "id": rev_id,
                "opportunity_id": opp_id,
                "revision": 1,
                "title": title,
                "contract_type": contract_type,
                "compensation_type": compensation_type,
                "hourly_rate": hourly_rate,
                "created_by": created_by,
                "published_at": None,
                "created_at": now,
            }
            self.opportunities[opp_id] = opp
            self.opportunity_revisions[rev_id] = rev

        return opp, rev

    def create_thread_with_first_message(
        self,
        *,
        created_by: str,
        subject: str,
        body: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Atomically create a `threads` row and its first `messages` row with circular FK."""
        thread_id = str(uuid4())
        msg_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with self.atomic_deferred():
            thread = {
                "id": thread_id,
                "subject": subject,
                "last_message_id": msg_id,
                "created_by": created_by,
                "created_at": now,
            }
            msg = {
                "id": msg_id,
                "thread_id": thread_id,
                "sender_id": created_by,
                "body": body,
                "created_at": now,
            }
            self.threads[thread_id] = thread
            self.messages[msg_id] = msg

        return thread, msg
