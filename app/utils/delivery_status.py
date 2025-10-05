from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

REVIEW_STATUS_KEYS: tuple[str, ...] = (
    "deterministic_final_validation",
    "semantic_visual_review",
    "image_assets_review",
)


def _snapshot_review(state: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    if not state:
        return None

    review = state.get(key)
    data: dict[str, Any] = {}

    if isinstance(review, dict):
        grade = review.get("grade")
        if grade is not None:
            data["grade"] = grade
        issues = review.get("issues")
        if issues:
            data["issues"] = issues
        source = review.get("source")
        if source:
            data["source"] = source
        normalized = review.get("normalized_payload")
        if normalized:
            data["normalized_payload"] = normalized
    elif review is not None:
        data["grade"] = review

    failed_flag = state.get(f"{key}_failed")
    if failed_flag is not None:
        data["failed"] = bool(failed_flag)
        reason = state.get(f"{key}_failure_reason")
        if reason:
            data["failure_reason"] = reason

    return data or None

logger = logging.getLogger(__name__)

_META_DIR = Path("artifacts/ads_final/meta")
_FAILURE_SUFFIX = ".error.json"


def _ensure_meta_dir() -> None:
    try:
        _META_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:  # pragma: no cover - defensive filesystem guard
        logger.exception("delivery_status: failed to create meta directory %s", _META_DIR)


def write_failure_meta(
    *,
    session_id: str,
    user_id: str,
    reason: str,
    message: str,
    extra: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
) -> Path:
    """Persist a failure sidecar so the delivery endpoints can surface the error."""

    _ensure_meta_dir()
    payload = {
        "status": "failed",
        "reason": reason,
        "message": message,
        "user_id": user_id,
        "session_id": session_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if extra:
        payload.update(extra)

    for key in REVIEW_STATUS_KEYS:
        snapshot = _snapshot_review(state, key)
        if snapshot:
            payload[key] = snapshot

    path = _META_DIR / f"{session_id}{_FAILURE_SUFFIX}"
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:  # pragma: no cover - filesystem guard
        logger.exception("delivery_status: failed to persist failure meta for session %s", session_id)
    return path


def load_failure_meta(session_id: str) -> dict[str, Any] | None:
    """Load failure metadata for a session if it exists."""

    path = _META_DIR / f"{session_id}{_FAILURE_SUFFIX}"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - filesystem guard
        logger.exception("delivery_status: failed to read failure meta for session %s", session_id)
        return None


def clear_failure_meta(session_id: str, state: dict[str, Any] | None = None) -> None:
    """Remove failure metadata sidecar for a session if present."""

    path = _META_DIR / f"{session_id}{_FAILURE_SUFFIX}"
    if path.exists():
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except Exception:  # pragma: no cover - filesystem guard
            logger.exception("delivery_status: failed to remove failure meta for session %s", session_id)

    if state is not None:
        for key in REVIEW_STATUS_KEYS:
            state.pop(f"{key}_failed", None)
            state.pop(f"{key}_failure_reason", None)
