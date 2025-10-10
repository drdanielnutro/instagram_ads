from __future__ import annotations

import json
import logging
from typing import Any, Mapping

_SEVERITY_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def log_struct_event(
    logger: logging.Logger,
    payload: Mapping[str, Any] | None,
    *,
    severity: str = "INFO",
) -> None:
    """Log structured payloads when supported, with graceful fallback."""

    if payload is None:
        payload_dict: dict[str, Any] = {"message": "(empty payload)"}
    elif isinstance(payload, Mapping):
        payload_dict = dict(payload)
    else:
        payload_dict = {"message": str(payload)}

    severity_key = severity.upper() if severity else "INFO"
    level = _SEVERITY_MAP.get(severity_key, logging.INFO)

    log_struct = getattr(logger, "log_struct", None)
    if callable(log_struct):
        try:
            log_struct(payload_dict, severity=severity_key)
            return
        except Exception:  # pragma: no cover - defensive fallback
            logger.debug("log_struct_event fallback for payload: %s", payload_dict)

    logger.log(level, json.dumps(payload_dict, ensure_ascii=False))


__all__ = ["log_struct_event"]
