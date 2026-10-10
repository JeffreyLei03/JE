"""A small LRU cache with per-entry TTL expiry.

The cache is driven entirely by a caller supplied clock so that tests can be
fully deterministic (no sleeping).  ``get`` is O(1): expired entries are removed
lazily on access and recency is tracked with an ``OrderedDict`` rather than by
scanning.

Expired entries are purged before any capacity eviction so a stale entry can
never cause a live one to be dropped.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable, Optional


class Cache:
    """LRU cache with per-entry time-to-live.

    Parameters
    ----------
    capacity:
        Maximum number of *entries* the cache may hold.  Must be a positive
        ``int``; ``bool`` is explicitly rejected because it is a subclass of
        ``int`` but not a meaningful capacity.
    clock:
        Callable returning the current time as a float.  Used for all expiry
        decisions; the cache never sleeps or reads the wall clock itself.
    """

    __slots__ = ("_capacity", "_clock", "_data")

    def __init__(self, capacity: int, clock: Callable[[], float]) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if not callable(clock):
            raise TypeError("clock must be callable")

        self._capacity = capacity
        self._clock = clock
        # key -> [value, expiry]; iteration order is LRU -> MRU.
        self._data: "OrderedDict[Any, list[Any]]" = OrderedDict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def put(self, key: Any, value: Any, ttl: float) -> None:
        """Insert or update ``key`` with ``value`` that expires after ``ttl``.

        A non-positive ``ttl`` removes the key.  Updating an existing key
        refreshes its value, expiry and recency.
        """
        if ttl <= 0:
            self._data.pop(key, None)
            return

        expiry = self._clock() + ttl
        entry = self._data.get(key)
        if entry is not None:
            entry[0] = value
            entry[1] = expiry
            self._data.move_to_end(key)
            return

        if len(self._data) >= self._capacity:
            self._purge_expired()
            if len(self._data) >= self._capacity:
                # Evict the least recently used *live* entry.
                self._data.popitem(last=False)

        self._data[key] = [value, expiry]

    def get(self, key: Any, default: Optional[Any] = None) -> Any:
        """Return the live value for ``key`` or ``default``.

        Accessing a live entry refreshes its LRU recency.  An expired entry is
        removed and ``default`` is returned.  Entry expires when
        ``clock() >= expiry``.
        """
        entry = self._data.get(key)
        if entry is None:
            return default

        value, expiry = entry
        if self._clock() >= expiry:
            del self._data[key]
            return default

        self._data.move_to_end(key)
        return value

    def __len__(self) -> int:
        """Number of live entries (expired entries are not counted)."""
        now = self._clock()
        return sum(1 for _, expiry in self._data.values() if now < expiry)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _purge_expired(self) -> None:
        """Drop every expired entry.  O(n), only run around eviction."""
        now = self._clock()
        expired = [key for key, (_, expiry) in self._data.items() if now >= expiry]
        for key in expired:
            del self._data[key]
