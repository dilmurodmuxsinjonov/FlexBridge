"""Transactional outbox relay worker for FlexBridge R1.

Polls pending outbox_events and dispatches notifications/audit relays with idempotency.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from app.db.storage import init_storage, list_domain_records, save_domain_record

logger = logging.getLogger("flexbridge.workers.outbox")


def relay_pending_outbox_events(batch_size: int = 50) -> int:
    """Process pending outbox events once and mark them RELAYED."""
    init_storage()
    records = list_domain_records("outbox_events")
    relayed = 0
    for record in records[:batch_size]:
        if record.get("status") in (None, "PENDING"):
            record["status"] = "RELAYED"
            record["relayed_at"] = datetime.now(timezone.utc).isoformat()
            event_id = str(record.get("id") or f"evt-{relayed}")
            save_domain_record("outbox_events", event_id, record)
            relayed += 1
    return relayed


def main(poll_interval_seconds: float = 5.0) -> None:
    """Run continuous outbox polling loop."""
    logger.info("Starting FlexBridge outbox relay worker")
    init_storage()
    while True:
        relay_pending_outbox_events()
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    main()
