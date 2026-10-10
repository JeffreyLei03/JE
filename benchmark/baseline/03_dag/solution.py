"""Heap-based deterministic topological planning."""

import heapq


def plan(graph: dict[str, list[str]]) -> list[str]:
    counts = {}
    dependents = {node: [] for node in graph}
    for node, dependencies in graph.items():
        unique = set(dependencies)
        if any(dependency not in graph for dependency in unique):
            raise ValueError("Unknown dependency")
        counts[node] = len(unique)
        for dependency in unique:
            dependents[dependency].append(node)
    ready = [node for node, count in counts.items() if count == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        node = heapq.heappop(ready)
        result.append(node)
        for child in dependents[node]:
            counts[child] -= 1
            if counts[child] == 0:
                heapq.heappush(ready, child)
    if len(result) != len(graph):
        raise ValueError("Cycle")
    return result
