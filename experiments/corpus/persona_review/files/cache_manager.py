"""Thread-safe in-memory cache with TTL expiration and LRU eviction.

Supports typed get/set operations, batch operations, and cache statistics.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, TypeVar, Generic

T = TypeVar("T")

DEFAULT_TTL = 300  # 5 minutes
DEFAULT_MAX_SIZE = 1000


@dataclass
class CacheEntry:
    """A single cached value with expiration metadata."""

    value: Any
    created_at: float
    ttl: float
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    current_size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


class Cache:
    """Thread-safe LRU cache with TTL expiration."""

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_SIZE,
        default_ttl: float = DEFAULT_TTL,
    ) -> None:
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._stats = CacheStats(max_size=max_size)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the cache.

        Returns the cached value if present and not expired,
        otherwise returns the default.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats.misses += 1
                return default

            if entry.is_expired:
                del self._store[key]
                self._stats.expirations += 1
                self._stats.misses += 1
                return default

            # Move to end (most recently used)
            self._store.move_to_end(key)
            entry.access_count += 1
            self._stats.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a value in the cache with optional custom TTL."""
        effective_ttl = ttl if ttl is not None else self._default_ttl

        with self._lock:
            # If key exists, update in place
            if key in self._store:
                self._store[key] = CacheEntry(
                    value=value, created_at=time.time(), ttl=effective_ttl
                )
                self._store.move_to_end(key)
                return

            # Evict if at capacity
            while len(self._store) >= self._max_size:
                self._store.popitem(last=False)
                self._stats.evictions += 1

            self._store[key] = CacheEntry(
                value=value, created_at=time.time(), ttl=effective_ttl
            )
            self._stats.current_size = len(self._store)

    def delete(self, key: str) -> bool:
        """Remove a key from the cache. Returns True if the key existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._stats.current_size = len(self._store)
                return True
            return False

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Retrieve multiple values in a single operation."""
        results = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                results[key] = value
        return results

    def set_many(self, items: dict[str, Any], ttl: float | None = None) -> None:
        """Store multiple values in a single operation."""
        for key, value in items.items():
            self.set(key, value, ttl=ttl)

    def clear(self) -> int:
        """Remove all entries from the cache. Returns the number of entries cleared."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            self._stats.current_size = 0
            return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns the number of entries removed."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._store.items() if entry.is_expired
            ]
            for key in expired_keys:
                del self._store[key]
            self._stats.expirations += len(expired_keys)
            self._stats.current_size = len(self._store)
            return len(expired_keys)

    @property
    def stats(self) -> CacheStats:
        """Return a snapshot of cache statistics."""
        with self._lock:
            self._stats.current_size = len(self._store)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                expirations=self._stats.expirations,
                current_size=self._stats.current_size,
                max_size=self._stats.max_size,
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._store[key]
                return False
            return True
