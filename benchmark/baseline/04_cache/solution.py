"""Lazy TTL expiry with heap and O(1) LRU hits."""

import heapq
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Any


class Cache:
    def __init__(self, capacity: int, clock: Callable[[], float]) -> None:
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("Invalid capacity")
        self.capacity = capacity
        self.clock = clock
        self.data: OrderedDict[Hashable, tuple[Any, float, int]] = OrderedDict()
        self.expiry: list[tuple[float, int, Hashable]] = []
        self.version = 0

    def _purge(self) -> None:
        now = self.clock()
        while self.expiry and self.expiry[0][0] <= now:
            _, version, key = heapq.heappop(self.expiry)
            entry = self.data.get(key)
            if entry is not None and entry[2] == version:
                del self.data[key]
        if len(self.expiry) > max(64, len(self.data) * 3):
            self.expiry = [
                (expiry, version, key) for key, (_, expiry, version) in self.data.items()
            ]
            heapq.heapify(self.expiry)

    def put(self, key: Hashable, value: Any, ttl: float) -> None:
        self._purge()
        self.data.pop(key, None)
        if ttl <= 0:
            return
        self.version += 1
        expiry = self.clock() + ttl
        self.data[key] = (value, expiry, self.version)
        heapq.heappush(self.expiry, (expiry, self.version, key))
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)

    def get(self, key: Hashable, default: Any = None) -> Any:
        self._purge()
        if key not in self.data:
            return default
        self.data.move_to_end(key)
        return self.data[key][0]

    def __len__(self) -> int:
        self._purge()
        return len(self.data)
