"""In-memory cache helpers for reference image metadata."""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Any, Dict, Mapping, MutableMapping, Protocol

from app.config import config
from app.schemas.reference_assets import ReferenceImageMetadata


logger = logging.getLogger(__name__)


class ReferenceMetadataCacheBackend(Protocol):
    """Protocol for cache backends storing reference metadata."""

    def set(self, metadata: ReferenceImageMetadata) -> None: ...

    def get(self, reference_id: str) -> ReferenceImageMetadata | None: ...

    def purge_expired(self) -> None: ...


class InMemoryReferenceMetadataCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = max(int(ttl_seconds), 0)
        self._store: MutableMapping[str, tuple[ReferenceImageMetadata, float]] = {}
        self._lock = Lock()

    def set(self, metadata: ReferenceImageMetadata) -> None:
        expires_at = (
            time.monotonic() + self.ttl_seconds if self.ttl_seconds else float("inf")
        )
        with self._lock:
            self._store[metadata.id] = (metadata, expires_at)
        logger.debug("Cached reference metadata for %s", metadata.id)

    def get(self, reference_id: str) -> ReferenceImageMetadata | None:
        now = time.monotonic()
        with self._lock:
            item = self._store.get(reference_id)
            if not item:
                return None
            metadata, expires_at = item
            if expires_at < now:
                del self._store[reference_id]
                logger.debug("Reference metadata %s expired from cache", reference_id)
                return None
            return metadata.model_copy(deep=True)

    def purge_expired(self) -> None:
        now = time.monotonic()
        with self._lock:
            expired = [
                key for key, (_, expires_at) in self._store.items() if expires_at < now
            ]
            for key in expired:
                del self._store[key]
            if expired:
                logger.debug(
                    "Purged %d expired reference metadata entries", len(expired)
                )


_backend: ReferenceMetadataCacheBackend = InMemoryReferenceMetadataCache(
    ttl_seconds=config.reference_cache_ttl_seconds
)


def configure_reference_cache(backend: ReferenceMetadataCacheBackend) -> None:
    """Override the cache backend (e.g., Redis/Datastore)."""

    global _backend
    _backend = backend
    logger.info(
        "Reference metadata cache backend configured: %s", backend.__class__.__name__
    )


def cache_reference_metadata(metadata: ReferenceImageMetadata) -> None:
    """Persist metadata in the configured cache backend."""

    _backend.set(metadata)


def resolve_reference_metadata(
    reference_id: str | None,
) -> ReferenceImageMetadata | None:
    """Retrieve metadata for a given reference ID, respecting TTL."""

    if not reference_id:
        return None
    metadata = _backend.get(reference_id)
    if metadata is None:
        logger.debug("Reference metadata %s not found in cache", reference_id)
    return metadata


def merge_user_description(
    metadata: ReferenceImageMetadata | None,
    description: str | None,
) -> dict[str, Any] | None:
    """Combine metadata with a user-provided description when available."""

    normalized_description = (description or "").strip() or None
    if metadata is None:
        if normalized_description:
            return {"user_description": normalized_description}
        return None

    payload = metadata.to_state_dict()
    if normalized_description is not None:
        payload["user_description"] = normalized_description
    return payload


def build_reference_summary(
    reference_images: Mapping[str, dict[str, Any] | None],
    payload: Mapping[str, Any] | None,
) -> dict[str, str | None]:
    """Build human-readable summaries for prompts and logging."""

    del payload  # reserved for future use (extended metadata merges)
    summary: Dict[str, str | None] = {
        "character": None,
        "product": None,
        "safe_search_notes": None,
    }

    notes: list[str] = []
    for ref_type in ("character", "product"):
        data = reference_images.get(ref_type) if reference_images else None
        if not data:
            continue
        description = (data.get("user_description") or "").strip()
        labels = data.get("labels") or []
        safe_flags = data.get("safe_search_flags") or {}

        parts: list[str] = []
        if description:
            parts.append(description)
        if labels:
            parts.append("Labels: " + ", ".join(labels[:5]))

        flagged = [
            f"{key}={value}"
            for key, value in safe_flags.items()
            if value in {"LIKELY", "VERY_LIKELY"}
        ]
        if flagged:
            notes.append(f"{ref_type}: {', '.join(flagged)}")

        summary[ref_type] = " | ".join(parts) if parts else None

    summary["safe_search_notes"] = "; ".join(notes) if notes else None
    return summary


__all__ = [
    "InMemoryReferenceMetadataCache",
    "ReferenceMetadataCacheBackend",
    "build_reference_summary",
    "cache_reference_metadata",
    "configure_reference_cache",
    "merge_user_description",
    "resolve_reference_metadata",
]
