"""Smoke tests for :func:`solution.normalize`."""

from __future__ import annotations

import unittest

from solution import normalize


class NormalizeTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(normalize([]), [])

    def test_empty_generator(self) -> None:
        self.assertEqual(normalize(iter(())), [])

    def test_single(self) -> None:
        self.assertEqual(normalize([(1, 3)]), [(1, 3)])

    def test_overlapping_merged(self) -> None:
        self.assertEqual(normalize([(1, 5), (2, 6)]), [(1, 6)])
        self.assertEqual(normalize([(10, 20), (0, 5), (5, 11)]), [(0, 20)])

    def test_touching_merged(self) -> None:
        self.assertEqual(normalize([(1, 2), (2, 3)]), [(1, 3)])
        self.assertEqual(normalize([(0, 2), (4, 6), (2, 4)]), [(0, 6)])

    def test_adjacent_after_sort(self) -> None:
        self.assertEqual(normalize([(5, 6), (1, 2), (2, 3), (3, 5)]), [(1, 6)])

    def test_nested_range_absorbed(self) -> None:
        self.assertEqual(normalize([(0, 10), (2, 4)]), [(0, 10)])

    def test_duplicates(self) -> None:
        self.assertEqual(normalize([(1, 4), (1, 4), (1, 4)]), [(1, 4)])

    def test_negatives(self) -> None:
        self.assertEqual(normalize([(-5, -1), (-3, 2), (2, 7)]), [(-5, 7)])
        self.assertEqual(normalize([(-10, -5), (-2, 0)]), [(-10, -5), (-2, 0)])

    def test_does_not_mutate_caller_list(self) -> None:
        data = [(5, 6), (1, 3), (2, 4)]
        snapshot = list(data)
        normalize(data)
        self.assertEqual(data, snapshot)

    def test_accepts_generator(self) -> None:
        gen = ((i, i + 2) for i in range(0, 10, 2))
        self.assertEqual(normalize(gen), [(0, 10)])

    def test_accepts_lists_as_pairs(self) -> None:
        self.assertEqual(normalize([[1, 2], [2, 3]]), [(1, 3)])

    def test_large_input(self) -> None:
        n = 50_000
        data = [(i, i + 1) for i in range(n)]
        result = normalize(iter(data))
        self.assertEqual(result, [(0, n)])

    # --- validation -----------------------------------------------------

    def test_start_equal_end_invalid(self) -> None:
        with self.assertRaises(ValueError):
            normalize([(3, 3)])

    def test_start_greater_than_end_invalid(self) -> None:
        with self.assertRaises(ValueError):
            normalize([(5, 1)])

    def test_invalid_pair_swallowed_by_merge_still_raises(self) -> None:
        with self.assertRaises(ValueError):
            normalize([(0, 10), (3, 3)])

    def test_non_integer_start_invalid(self) -> None:
        with self.assertRaises(TypeError):
            normalize([(1.5, 3)])

    def test_non_integer_end_invalid(self) -> None:
        with self.assertRaises(TypeError):
            normalize([(1, "3")])

    def test_bool_endpoints_invalid(self) -> None:
        with self.assertRaises(TypeError):
            normalize([(True, 3)])
        with self.assertRaises(TypeError):
            normalize([(0, False)])

    def test_wrong_arity_invalid(self) -> None:
        with self.assertRaises(TypeError):
            normalize([(1, 2, 3)])
        with self.assertRaises(TypeError):
            normalize([(1,)])

    def test_string_pair_invalid(self) -> None:
        with self.assertRaises(TypeError):
            normalize(["ab"])

    def test_non_iterable_pair_invalid(self) -> None:
        with self.assertRaises(TypeError):
            normalize([5])


if __name__ == "__main__":
    unittest.main()
