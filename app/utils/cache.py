from __future__ import annotations

import json
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Hashable


@dataclass
class CacheEntry:
    value: Any
    expires_at: float | None


class InMemoryResponseCache:
    """Simple thread-safe LRU cache with optional TTL semantics."""

    def __init__(self, maxsize: int = 32, ttl_seconds: int | None = 900) -> None:
        self._store: OrderedDict[Hashable, CacheEntry] = OrderedDict()
        self._maxsize = max(1, maxsize)
        self._ttl = ttl_seconds if ttl_seconds and ttl_seconds > 0 else None
        self._lock = threading.Lock()

    def _purge_expired(self) -> None:
        if not self._store:
            return
        if self._ttl is None:
            return
        now = time.time()
        keys_to_delete = [
            key for key, entry in self._store.items() if entry.expires_at and entry.expires_at <= now
        ]
        for key in keys_to_delete:
            self._store.pop(key, None)

    def get(self, key: Hashable) -> Any | None:
        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                return None
            # refresh LRU order
            self._store.move_to_end(key)
            return entry.value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._purge_expired()
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = CacheEntry(
                value=value,
                expires_at=(time.time() + self._ttl) if self._ttl is not None else None,
            )
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)


def make_storybrand_cache_key(*parts: Any) -> str:
    """Generate a deterministic cache key combining hashable and JSON-serialisable parts."""

    normalized = []
    for part in parts:
        if isinstance(part, (str, int, float, bool)) or part is None:
            normalized.append(part)
        else:
            normalized.append(json.dumps(part, sort_keys=True, default=str))
    return json.dumps(normalized, separators=(",", ":"))


_storybrand_cache = InMemoryResponseCache(
    maxsize=int(os.getenv("STORYBRAND_CACHE_MAXSIZE", "32")),
    ttl_seconds=int(os.getenv("STORYBRAND_CACHE_TTL", "900")),
)


def get_storybrand_cache() -> InMemoryResponseCache:
    return _storybrand_cache
