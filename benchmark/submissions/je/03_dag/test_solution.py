"""Smoke tests for solution.plan."""

from __future__ import annotations

import time
import unittest

from solution import plan


class PlanTests(unittest.TestCase):
    def test_empty_graph(self) -> None:
        self.assertEqual(plan({}), [])

    def test_no_dependencies(self) -> None:
        graph = {"b": [], "a": [], "c": []}
        self.assertEqual(plan(graph), ["a", "b", "c"])

    def test_simple_chain(self) -> None:
        graph = {"c": ["b"], "b": ["a"], "a": []}
        self.assertEqual(plan(graph), ["a", "b", "c"])

    def test_diamond(self) -> None:
        graph = {"d": ["b", "c"], "b": ["a"], "c": ["a"], "a": []}
        self.assertEqual(plan(graph), ["a", "b", "c", "d"])

    def test_lexicographic_ready_selection(self) -> None:
        # Initially ready: "b" and "c"; emit "b" (smallest). That unlocks
        # "a", which then beats the still-waiting "c".
        graph = {"a": ["b"], "b": [], "c": []}
        self.assertEqual(plan(graph), ["b", "a", "c"])

    def test_ready_order_not_final_sort(self) -> None:
        # Topological order must differ from simply sorting the final result:
        # "b" is the only ready node first, then "a" and "c" unlock.
        graph = {"a": ["b"], "b": [], "c": ["b"]}
        self.assertEqual(plan(graph), ["b", "a", "c"])
        self.assertNotEqual(plan(graph), sorted(graph))

    def test_duplicate_dependencies_count_once(self) -> None:
        graph = {"b": ["a", "a", "a"], "a": []}
        self.assertEqual(plan(graph), ["a", "b"])

    def test_unknown_dependency_raises(self) -> None:
        with self.assertRaises(ValueError):
            plan({"a": ["missing"]})

    def test_self_loop_raises(self) -> None:
        with self.assertRaises(ValueError):
            plan({"a": ["a"]})

    def test_cycle_raises(self) -> None:
        with self.assertRaises(ValueError):
            plan({"a": ["b"], "b": ["c"], "c": ["a"]})

    def test_two_node_cycle_raises(self) -> None:
        with self.assertRaises(ValueError):
            plan({"a": ["b"], "b": ["a"]})

    def test_no_mutation(self) -> None:
        graph = {"b": ["a"], "a": []}
        snapshot = {k: list(v) for k, v in graph.items()}
        plan(graph)
        self.assertEqual(graph, snapshot)

    def test_long_chain_no_recursion(self) -> None:
        n = 10000
        graph = {f"n{i:05d}": [f"n{i - 1:05d}"] for i in range(1, n)}
        graph["n00000"] = []
        start = time.perf_counter()
        order = plan(graph)
        elapsed = time.perf_counter() - start
        self.assertEqual(len(order), n)
        self.assertEqual(order, sorted(graph))
        self.assertLess(elapsed, 5.0)

    def test_lexicographically_smallest_among_ready(self) -> None:
        graph = {
            "root": [],
            "b": ["root"],
            "a": ["root"],
            "c": ["a"],
            "d": ["b"],
        }
        self.assertEqual(plan(graph), ["root", "a", "b", "c", "d"])


if __name__ == "__main__":
    unittest.main()
