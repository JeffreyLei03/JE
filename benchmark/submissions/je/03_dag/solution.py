"""Topological planning with lexicographically-smallest ready-node ordering."""

from __future__ import annotations

import heapq
from collections import defaultdict
from typing import Iterable


def plan(graph: dict[str, list[str]]) -> list[str]:
    """Return a topological ordering of ``graph``.

    Each key is a node and its value lists the nodes it depends on. A node is
    "ready" once all of its dependencies have been emitted. Whenever several
    nodes are ready, the lexicographically smallest one is emitted first.

    Raises:
        ValueError: if a dependency references an unknown node, or if the
            graph contains a cycle (including a self loop).

    The input mapping and its lists are never mutated.
    """
    nodes: set[str] = set(graph)

    # Validate that every referenced dependency exists as a node.
    for deps in graph.values():
        for dep in deps:
            if dep not in nodes:
                raise ValueError(f"unknown node referenced: {dep!r}")

    # Build deduplicated edges without mutating the input.
    remaining: dict[str, int] = {node: 0 for node in nodes}
    dependents: dict[str, list[str]] = defaultdict(list)
    for node, deps in graph.items():
        unique_deps = set(deps)
        remaining[node] = len(unique_deps)
        for dep in unique_deps:
            dependents[dep].append(node)

    ready: list[str] = [node for node, count in remaining.items() if count == 0]
    heapq.heapify(ready)

    order: list[str] = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for dependent in dependents[node]:
            remaining[dependent] -= 1
            if remaining[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(order) != len(nodes):
        raise ValueError("graph contains a cycle")

    return order


__all__ = ["plan"]
