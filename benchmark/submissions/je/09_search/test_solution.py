"""Smoke tests for solution.rank / solution.tokenize."""

from __future__ import annotations

import unittest

from solution import rank, tokenize


class TestTokenize(unittest.TestCase):
    def test_basic_casefold(self) -> None:
        self.assertEqual(tokenize("Hello World"), ["hello", "world"])

    def test_underscore_is_separator(self) -> None:
        self.assertEqual(tokenize("foo_bar_baz"), ["foo", "bar", "baz"])

    def test_unicode_letters_and_digits(self) -> None:
        self.assertEqual(tokenize("Café Ünïcode 123"), ["café", "ünïcode", "123"])

    def test_punctuation_ignored(self) -> None:
        self.assertEqual(tokenize("a,b.c!d?"), ["a", "b", "c", "d"])


class TestRankArguments(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = {"a": "apple banana", "b": "apple cherry"}

    def test_empty_query(self) -> None:
        self.assertEqual(rank("", self.docs), [])
        self.assertEqual(rank("___ !!!", self.docs), [])

    def test_limit_zero(self) -> None:
        self.assertEqual(rank("apple", self.docs, limit=0), [])

    def test_negative_limit_raises(self) -> None:
        with self.assertRaises(ValueError):
            rank("apple", self.docs, limit=-1)

    def test_non_integer_limit_raises(self) -> None:
        with self.assertRaises(ValueError):
            rank("apple", self.docs, limit=2.5)  # type: ignore[arg-type]

    def test_bool_limit_raises(self) -> None:
        with self.assertRaises(ValueError):
            rank("apple", self.docs, limit=True)  # type: ignore[arg-type]


class TestRankScoring(unittest.TestCase):
    def test_all_terms_required(self) -> None:
        docs = {"a": "apple banana", "b": "apple cherry", "c": "banana cherry"}
        # Only "a" contains both apple and banana.
        self.assertEqual(rank("apple banana", docs), [("a", 2)])

    def test_score_sums_term_frequencies(self) -> None:
        docs = {
            "a": "apple apple banana",  # 2 + 1 = 3
            "b": "apple banana banana banana",  # 1 + 3 = 4
        }
        self.assertEqual(rank("apple banana", docs), [("b", 4), ("a", 3)])

    def test_sort_score_desc_then_id_asc(self) -> None:
        docs = {
            "z": "x x x",
            "a": "x x x",
            "m": "x",
        }
        self.assertEqual(rank("x", docs), [("a", 3), ("z", 3), ("m", 1)])

    def test_duplicate_query_terms_are_deduped(self) -> None:
        docs = {"a": "apple apple banana"}
        self.assertEqual(rank("apple apple banana", docs), [("a", 3)])

    def test_limit_applied_after_sort(self) -> None:
        docs = {"a": "x x x", "b": "x x", "c": "x"}
        self.assertEqual(rank("x", docs, limit=2), [("a", 3), ("b", 2)])

    def test_absent_term_yields_empty(self) -> None:
        docs = {"a": "apple banana"}
        self.assertEqual(rank("apple missing", docs), [])

    def test_default_limit_is_ten(self) -> None:
        docs = {f"d{i:02d}": "token" for i in range(15)}
        result = rank("token", docs)
        self.assertEqual(len(result), 10)

    def test_unicode_query(self) -> None:
        docs = {"a": "Café café", "b": "Cafe"}
        self.assertEqual(rank("CAFÉ", docs), [("a", 2)])

    def test_does_not_mutate_documents(self) -> None:
        docs = {"a": "apple apple", "b": "banana"}
        snapshot = dict(docs)
        rank("apple banana", docs)
        self.assertEqual(docs, snapshot)


if __name__ == "__main__":
    unittest.main()
