"""Smoke tests for :mod:`solution`."""

from __future__ import annotations

import time
import unittest

from solution import Cache


class FakeClock:
    """Deterministic clock for tests."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class CapacityValidationTests(unittest.TestCase):
    def test_rejects_zero_and_negative(self) -> None:
        clock = FakeClock()
        for bad in (0, -1, -100):
            with self.assertRaises(ValueError):
                Cache(bad, clock)

    def test_rejects_bool(self) -> None:
        clock = FakeClock()
        for bad in (True, False):
            with self.assertRaises(ValueError):
                Cache(bad, clock)  # type: ignore[arg-type]

    def test_rejects_non_int(self) -> None:
        clock = FakeClock()
        for bad in (1.0, "3", None):
            with self.assertRaises(ValueError):
                Cache(bad, clock)  # type: ignore[arg-type]

    def test_accepts_positive_int(self) -> None:
        Cache(1, FakeClock())
        Cache(20000, FakeClock())


class BasicPutGetTests(unittest.TestCase):
    def test_missing_returns_default(self) -> None:
        c = Cache(4, FakeClock())
        self.assertIsNone(c.get("nope"))
        self.assertEqual(c.get("nope", 42), 42)

    def test_roundtrip_and_none_value(self) -> None:
        c = Cache(4, FakeClock())
        c.put("a", None, 10)
        self.assertIsNone(c.get("a"))
        self.assertEqual(len(c), 1)

    def test_arbitrary_hashable_keys(self) -> None:
        c = Cache(4, FakeClock())
        keys = [(1, 2), frozenset({1, 2}), "text", 5]
        for i, k in enumerate(keys):
            c.put(k, i, 10)
        for i, k in enumerate(keys):
            self.assertEqual(c.get(k), i)


class ExpiryTests(unittest.TestCase):
    def test_expiry_at_boundary(self) -> None:
        clock = FakeClock(100.0)
        c = Cache(4, clock)
        c.put("a", 1, ttl=5)
        clock.advance(4.999)
        self.assertEqual(c.get("a"), 1)
        clock.now = 105.0  # now == expiry -> expired
        self.assertIsNone(c.get("a"))

    def test_non_positive_ttl_removes(self) -> None:
        c = Cache(4, FakeClock())
        c.put("a", 1, ttl=10)
        self.assertEqual(len(c), 1)
        c.put("a", 2, ttl=0)
        self.assertIsNone(c.get("a"))
        c.put("a", 3, ttl=-5)
        self.assertIsNone(c.get("a"))

    def test_len_counts_only_live(self) -> None:
        clock = FakeClock()
        c = Cache(4, clock)
        c.put("a", 1, 5)
        c.put("b", 2, 10)
        self.assertEqual(len(c), 2)
        clock.advance(6)
        self.assertEqual(len(c), 1)
        clock.advance(10)
        self.assertEqual(len(c), 0)


class LruTests(unittest.TestCase):
    def test_eviction_order_and_get_refresh(self) -> None:
        c = Cache(2, FakeClock())
        c.put("a", 1, 100)
        c.put("b", 2, 100)
        # Touch "a" so "b" becomes least recently used.
        self.assertEqual(c.get("a"), 1)
        c.put("c", 3, 100)
        self.assertIsNone(c.get("b"))
        self.assertEqual(c.get("a"), 1)
        self.assertEqual(c.get("c"), 3)

    def test_update_refreshes_value_expiry_recency(self) -> None:
        clock = FakeClock()
        c = Cache(2, clock)
        c.put("a", 1, 5)
        c.put("b", 2, 100)
        clock.advance(4)
        c.put("a", 99, 100)  # refresh value/expiry, move to MRU
        clock.advance(2)  # original a would have expired
        self.assertEqual(c.get("a"), 99)
        c.put("c", 3, 100)  # b is LRU now
        self.assertIsNone(c.get("b"))
        self.assertEqual(c.get("a"), 99)

    def test_expired_never_evicts_live(self) -> None:
        clock = FakeClock()
        c = Cache(2, clock)
        c.put("live", 1, 100)
        c.put("dead", 2, 5)
        clock.advance(10)  # "dead" has expired but is still stored
        c.put("new", 3, 100)
        # The expired entry is purged; the live entry must survive.
        self.assertEqual(c.get("live"), 1)
        self.assertEqual(c.get("new"), 3)
        self.assertIsNone(c.get("dead"))

    def test_expired_purge_with_multiple_live_evicts_lru_only(self) -> None:
        clock = FakeClock()
        c = Cache(3, clock)
        c.put("lru", 1, 100)
        c.put("live2", 2, 100)
        c.put("dead", 3, 1)
        clock.advance(5)
        c.put("new", 4, 100)
        # dead purged, capacity not exceeded -> nothing live evicted
        self.assertEqual(c.get("lru"), 1)
        self.assertEqual(c.get("live2"), 2)
        self.assertEqual(c.get("new"), 4)


class EfficiencyTests(unittest.TestCase):
    def test_repeated_get_at_large_capacity(self) -> None:
        c = Cache(20000, FakeClock())
        for i in range(20000):
            c.put(i, i, ttl=1_000_000)

        start = time.perf_counter()
        for _ in range(20):
            for i in range(20000):
                self.assertEqual(c.get(i), i)
        elapsed = time.perf_counter() - start
        # 400k lookups should be far below this generous bound on any machine.
        self.assertLess(elapsed, 5.0)


if __name__ == "__main__":
    unittest.main()
