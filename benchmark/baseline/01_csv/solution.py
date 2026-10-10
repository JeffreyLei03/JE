"""Exact-decimal CSV totals."""

import csv
import io
import re
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def summarize(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return []
    if not {"customer", "currency", "amount"}.issubset(reader.fieldnames):
        raise ValueError("Missing header")
    totals = defaultdict(lambda: [Decimal(0), 0])
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed row")
        customer = row["customer"].strip()
        currency = row["currency"].strip().upper()
        if not customer or not re.fullmatch("[A-Z]{3}", currency):
            raise ValueError("Invalid identity")
        try:
            amount = Decimal(row["amount"])
        except InvalidOperation as exc:
            raise ValueError("Invalid amount") from exc
        if not amount.is_finite():
            raise ValueError("Nonfinite amount")
        bucket = totals[customer, currency]
        bucket[0] += amount
        bucket[1] += 1
    return [
        {
            "customer": customer,
            "currency": currency,
            "total": format(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f"),
            "count": count,
        }
        for (customer, currency), (total, count) in sorted(totals.items())
    ]
