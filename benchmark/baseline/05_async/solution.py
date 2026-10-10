"""Bounded workers with structured cleanup."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Any


async def bounded_map(
    func: Callable[[Any], Awaitable[Any]], items: Iterable[Any], limit: int
) -> list[Any]:
    if type(limit) is not int or limit <= 0:
        raise ValueError("Invalid limit")
    values = list(items)
    results = [None] * len(values)
    iterator = iter(enumerate(values))

    async def worker() -> None:
        for index, item in iterator:
            results[index] = await func(item)

    tasks = [asyncio.create_task(worker()) for _ in range(min(limit, len(values)))]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    return results
