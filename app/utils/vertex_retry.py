from __future__ import annotations

import logging
import os
import random
import threading
import time
from contextlib import contextmanager
from typing import Callable, Iterable, Optional, TypeVar

try:  # pragma: no cover - optional dependency during tests
    from google.api_core import exceptions as gcloud_exceptions
except Exception:  # pragma: no cover
    gcloud_exceptions = None

try:  # pragma: no cover - optional dependency during tests
    from google.genai.errors import ClientError as GenAiClientError
except Exception:  # pragma: no cover
    GenAiClientError = None

try:  # pragma: no cover - optional dependency during tests
    from app.utils.metrics import record_vertex_429
except Exception:  # pragma: no cover
    def record_vertex_429(_: dict[str, str] | None = None) -> None:  # type: ignore[override]
        return


logger = logging.getLogger(__name__)

_T = TypeVar("_T")

_DEFAULT_MAX_ATTEMPTS = int(os.getenv("VERTEX_RETRY_MAX_ATTEMPTS", "5"))
_DEFAULT_INITIAL_BACKOFF = float(os.getenv("VERTEX_RETRY_INITIAL_BACKOFF", "1.0"))
_DEFAULT_MAX_BACKOFF = float(os.getenv("VERTEX_RETRY_MAX_BACKOFF", "30.0"))
_DEFAULT_BACKOFF_MULTIPLIER = float(os.getenv("VERTEX_RETRY_BACKOFF_MULTIPLIER", "2.0"))
_DEFAULT_JITTER = float(os.getenv("VERTEX_RETRY_JITTER", "1.5"))

_CONCURRENCY_LIMIT = max(1, int(os.getenv("VERTEX_CONCURRENCY_LIMIT", "3")))
_semaphore = threading.Semaphore(_CONCURRENCY_LIMIT)


class VertexRetryExceededError(RuntimeError):
    """Raised when retry attempts are exhausted while calling Vertex AI."""

    def __init__(self, message: str, *, attempts: int, last_exception: BaseException, retry_after: float | None) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception
        self.retry_after = retry_after


def _extract_status_code(exc: BaseException) -> int | None:
    for attr in ("code", "status_code", "http_status", "status"):  # pragma: no branch - tiny loop
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        if hasattr(value, "value") and isinstance(value.value, int):
            return value.value
    return None


def _extract_retry_after(exc: BaseException) -> float | None:
    header = None
    for candidate in ("retry_after", "Retry-After", "retry-after"):
        if hasattr(exc, candidate):
            header = getattr(exc, candidate)
            break
    response = getattr(exc, "response", None)
    if response is not None:
        headers = getattr(response, "headers", None)
        if headers and isinstance(headers, dict):
            header = header or headers.get("Retry-After") or headers.get("retry-after")
    if header is None:
        return None
    try:
        if isinstance(header, (int, float)):
            return float(header)
        return float(str(header))
    except (TypeError, ValueError):
        return None


def _is_retryable_exception(exc: BaseException) -> bool:
    status = _extract_status_code(exc)
    if status in {408, 429, 500, 503}:
        return True
    if gcloud_exceptions and isinstance(exc, gcloud_exceptions.ResourceExhausted):
        return True
    if gcloud_exceptions and isinstance(exc, gcloud_exceptions.TooManyRequests):
        return True
    if gcloud_exceptions and isinstance(exc, gcloud_exceptions.ServiceUnavailable):
        return True
    if GenAiClientError and isinstance(exc, GenAiClientError):
        if status is None:
            return True
        return status in {408, 429, 500, 503}
    return False


@contextmanager
def limit_vertex_concurrency() -> Iterable[None]:
    _semaphore.acquire()
    try:
        yield
    finally:
        _semaphore.release()


def call_with_vertex_retry(
    func: Callable[[], _T],
    *,
    logger_obj: logging.Logger | None = None,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    initial_backoff: float = _DEFAULT_INITIAL_BACKOFF,
    max_backoff: float = _DEFAULT_MAX_BACKOFF,
    multiplier: float = _DEFAULT_BACKOFF_MULTIPLIER,
    jitter: float = _DEFAULT_JITTER,
) -> _T:
    """Execute ``func`` applying exponential backoff when Vertex AI throttles the request."""

    attempts = 0
    last_exception: Optional[BaseException] = None
    retry_after_hint: float | None = None
    log = logger_obj or logger

    while attempts < max_attempts:
        attempts += 1
        try:
            with limit_vertex_concurrency():
                return func()
        except Exception as exc:  # broad catch on purpose for retryable errors
            last_exception = exc
            if not _is_retryable_exception(exc):
                raise

            retry_after_hint = _extract_retry_after(exc)
            delay = min(max_backoff, initial_backoff * (multiplier ** (attempts - 1)))
            if retry_after_hint:
                delay = max(delay, retry_after_hint)
            delay += random.uniform(0, jitter)

            status_code = _extract_status_code(exc)
            if status_code == 429:
                try:
                    record_vertex_429({"stage": "storybrand_langextract"})
                except Exception:  # pragma: no cover - metrics backend failure
                    logger.debug("Failed to record vertex429 metric", exc_info=True)

            log.warning(
                "vertex_call_retry",
                extra={
                    "attempt": attempts,
                    "max_attempts": max_attempts,
                    "retry_after": retry_after_hint,
                    "delay": round(delay, 2),
                    "status_code": _extract_status_code(exc),
                    "exception": exc.__class__.__name__,
                },
            )
            time.sleep(delay)

    assert last_exception is not None  # for mypy/static type checking
    message = "Vertex AI call failed after %s attempts" % attempts
    raise VertexRetryExceededError(message, attempts=attempts, last_exception=last_exception, retry_after=retry_after_hint)
