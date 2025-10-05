"""Utilities for recording delivery audit events in the agent state."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger(__name__)


def append_delivery_audit_event(
    state: dict[str, Any],
    *,
    stage: str,
    status: str,
    detail: str | None = None,
    **extras: Any,
) -> None:
    """Append a structured audit event to the state."""

    events = list(state.get("delivery_audit_trail", []))
    event: dict[str, Any] = {
        "stage": stage,
        "status": status,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    if detail:
        event["detail"] = detail

    for key, value in extras.items():
        if value is not None:
            event[key] = value

    events.append(event)
    state["delivery_audit_trail"] = events

    logger.info("delivery_audit_event", extra={"event": event})

