from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

logger = logging.getLogger(__name__)


def resolve_state(callback_context: Any) -> dict[str, Any]:
    """Return the shared state dict from different callback context types."""

    state = getattr(callback_context, "state", None)
    if isinstance(state, MutableMapping):
        return state  # type: ignore[return-value]

    session = getattr(callback_context, "session", None)
    if session is not None:
        session_state = getattr(session, "state", None)
        if isinstance(session_state, MutableMapping):
            return session_state  # type: ignore[return-value]

    invocation_ctx = getattr(callback_context, "_invocation_context", None)
    if invocation_ctx is not None:
        session = getattr(invocation_ctx, "session", None)
        if session is not None:
            session_state = getattr(session, "state", None)
            if isinstance(session_state, MutableMapping):
                return session_state  # type: ignore[return-value]

    logger.debug("resolve_state: unable to locate mutable state on %s", type(callback_context))
    return {}


def safe_session_id(callback_context: Any) -> str:
    """Best-effort extraction of session identifier from callback context."""

    try:
        session = getattr(callback_context, "session", None)
        if session is not None:
            return (
                getattr(session, "id", None)
                or getattr(session, "session_id", None)
                or "nosession"
            )
    except Exception:  # pragma: no cover - defensive guardrail
        logger.debug("safe_session_id: failed to read id from session attribute", exc_info=True)

    try:
        invocation_ctx = getattr(callback_context, "_invocation_context", None)
        if invocation_ctx and getattr(invocation_ctx, "session", None):
            session = invocation_ctx.session
            return (
                getattr(session, "id", None)
                or getattr(session, "session_id", None)
                or "nosession"
            )
    except Exception:  # pragma: no cover - defensive guardrail
        logger.debug("safe_session_id: failed to read id from invocation context", exc_info=True)

    state = resolve_state(callback_context)
    return str(state.get("session_id", "nosession"))


def safe_user_id(callback_context: Any) -> str:
    """Best-effort extraction of user identifier from callback context."""

    try:
        session = getattr(callback_context, "session", None)
        if session is not None:
            user_id = getattr(session, "user_id", None)
            if user_id:
                return str(user_id)
    except Exception:  # pragma: no cover - defensive guardrail
        logger.debug("safe_user_id: failed to read user_id from session attribute", exc_info=True)

    try:
        invocation_ctx = getattr(callback_context, "_invocation_context", None)
        if invocation_ctx and getattr(invocation_ctx, "session", None):
            session = invocation_ctx.session
            user_id = getattr(session, "user_id", None)
            if user_id:
                return str(user_id)
    except Exception:  # pragma: no cover - defensive guardrail
        logger.debug("safe_user_id: failed to read user_id from invocation context", exc_info=True)

    state = resolve_state(callback_context)
    user_id = state.get("user_id")
    if user_id:
        return str(user_id)
    return "anonymous"
