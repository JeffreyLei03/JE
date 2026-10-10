"""Smoke tests for :mod:`solution`."""

from __future__ import annotations

import unittest
from decimal import Decimal

from solution import summarize


class SummarizeTests(unittest.TestCase):
    def test_empty_and_header_only(self) -> None:
        self.assertEqual(summarize(""), [])
        self.assertEqual(summarize("customer,currency,amount\n"), [])
        self.assertEqual(summarize("\n\n"), [])

    def test_basic_aggregation_and_sorting(self) -> None:
        text = (
            "customer,currency,amount\n"
            "bob,usd,1.005\n"
            "alice,eur,2\n"
            "bob,USD,2.005\n"
            " alice , eur , 3.5 \n"
        )
        self.assertEqual(
            summarize(text),
            [
                {"customer": "alice", "currency": "EUR", "total": "5.50", "count": 2},
                {"customer": "bob", "currency": "USD", "total": "3.01", "count": 2},
            ],
        )

    def test_round_only_after_summation(self) -> None:
        text = "customer,currency,amount\n" "a,GBP,0.005\n" "a,GBP,0.005\n"
        # 0.005 + 0.005 = 0.010 -> "0.01" (rounding each first would give 0.02)
        self.assertEqual(
            summarize(text),
            [{"customer": "a", "currency": "GBP", "total": "0.01", "count": 2}],
        )

    def test_signed_amounts_and_extra_columns(self) -> None:
        text = (
            "customer,currency,amount,note\n"
            "a,USD,-10.25,x\n"
            "a,USD,5.25,y\n"
            "a,USD,100,z\n"
        )
        self.assertEqual(
            summarize(text),
            [{"customer": "a", "currency": "USD", "total": "95.00", "count": 3}],
        )

    def test_missing_required_column(self) -> None:
        with self.assertRaises(ValueError):
            summarize("customer,amount\n" "a,1\n")

    def test_row_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            summarize("customer,currency,amount\n" "a,USD\n")

    def test_empty_customer(self) -> None:
        with self.assertRaises(ValueError):
            summarize("customer,currency,amount\n" "   ,USD,1\n")

    def test_invalid_currency(self) -> None:
        for bad in ("US", "USDD", "U$D", "12A"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    summarize(f"customer,currency,amount\n" f"a,{bad},1\n")

    def test_invalid_amount(self) -> None:
        for bad in ("", "abc", "1,000", "nan", "inf", "-Infinity"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    summarize(f"customer,currency,amount\n" f"a,USD,{bad}\n")

    def test_no_binary_floats(self) -> None:
        # Exact decimal summation that binary floats would get wrong.
        text = (
            "customer,currency,amount\n"
            "a,USD,0.1\n"
            "a,USD,0.2\n"
        )
        result = summarize(text)
        self.assertEqual(result[0]["total"], "0.30")
        self.assertIsInstance(Decimal(result[0]["total"]), Decimal)


if __name__ == "__main__":
    unittest.main()
