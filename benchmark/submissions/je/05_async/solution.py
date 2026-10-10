"""Async bounded-concurrency map.

Public API:
    bounded_map(func, items, limit) -> list

Awaits ``func(item)`` for every item with at most ``limit`` calls in flight,
while preserving the input order in the returned list.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


async def bounded_map(
    func: Callable[[T], Awaitable[R]],
    items: Iterable[T],
    limit: int,
) -> list[R]:
    """Apply ``func`` to each item with bounded concurrency.

    Args:
        func: Async callable invoked once per item.
        items: Any iterable, including generators. Consumed lazily.
        limit: Maximum number of concurrent ``func`` calls. Must be a
            positive ``int`` (``bool`` is rejected).

    Returns:
        Results aligned with the iteration order of ``items``.

    Raises:
        ValueError: If ``limit`` is not a positive non-bool int.
        BaseException: Whatever ``func``/the iterator raises. All remaining
            workers are cancelled and awaited before it propagates.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")

    iterator = iter(items)
    results: list[R] = []

    async def worker() -> None:
        while True:
            try:
                item = next(iterator)
            except StopIteration:
                return
            # ``next`` + slot reservation are synchronous, so no two workers
            # can observe the same item or the same index.
            index = len(results)
            results.append(None)  # type: ignore[arg-type]
            results[index] = await func(item)

    # One task per unit of concurrency; each pulls work until exhausted.
    workers = [asyncio.ensure_future(worker()) for _ in range(limit)]
    try:
        await asyncio.gather(*workers)
    except BaseException:
        # Covers both task errors and caller cancellation: tear down every
        # remaining worker and wait for them, then re-raise the original
        # exception/cancellation untouched.
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        raise

    return results
