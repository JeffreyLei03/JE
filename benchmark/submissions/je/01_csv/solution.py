"""CSV aggregation utilities.

Implements :func:`summarize`, which validates and aggregates CSV data using
:class:`decimal.Decimal` for exact monetary arithmetic (never binary floats).
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

__all__ = ["summarize"]

_REQUIRED = ("customer", "currency", "amount")
_CENTS = Decimal("0.01")


def _parse_currency(raw: str, line_no: int) -> str:
    value = raw.strip()
    if len(value) != 3 or not value.isascii() or not value.isalpha():
        raise ValueError(
            f"row {line_no}: invalid currency {raw!r}; expected three ASCII letters"
        )
    return value.upper()


def _parse_amount(raw: str, line_no: int) -> Decimal:
    try:
        amount = Decimal(raw.strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"row {line_no}: invalid amount {raw!r}") from exc
    if not amount.is_finite():
        raise ValueError(f"row {line_no}: non-finite amount {raw!r}")
    return amount


def summarize(text: str) -> list[dict]:
    """Aggregate CSV ``text`` by ``(customer, currency)``.

    The header must contain ``customer``, ``currency`` and ``amount`` columns
    (additional columns are permitted).  Each data row must have the same
    number of fields as the header.  Values are validated and totals are
    rounded HALF_UP to two decimal places only after summation.

    Raises:
        ValueError: for a missing required column, a malformed row length, an
            empty customer, an invalid currency or a missing/invalid/non-finite
            amount.
    """

    reader = csv.reader(io.StringIO(text, newline=""))

    header: list[str] | None = None
    index: dict[str, int] | None = None
    totals: dict[tuple[str, str], Decimal] = {}
    counts: dict[tuple[str, str], int] = {}

    for line_no, row in enumerate(reader, start=1):
        # Tolerate fully blank lines (e.g. a trailing newline).
        if not row:
            continue

        if header is None:
            header = [cell.strip() for cell in row]
            index = {}
            for name in _REQUIRED:
                if name not in header:
                    raise ValueError(f"missing required column: {name}")
                if name not in index:
                    index[name] = header.index(name)
            continue

        if len(row) != len(header):
            raise ValueError(
                f"row {line_no}: expected {len(header)} fields, got {len(row)}"
            )

        assert index is not None  # for type checkers
        customer = row[index["customer"]].strip()
        if not customer:
            raise ValueError(f"row {line_no}: empty customer")

        currency = _parse_currency(row[index["currency"]], line_no)
        amount = _parse_amount(row[index["amount"]], line_no)

        key = (customer, currency)
        totals[key] = totals.get(key, Decimal("0")) + amount
        counts[key] = counts.get(key, 0) + 1

    if header is None:
        return []

    result: list[dict] = []
    for key in sorted(totals):
        total = totals[key].quantize(_CENTS, rounding=ROUND_HALF_UP)
        result.append(
            {
                "customer": key[0],
                "currency": key[1],
                "total": format(total, "f"),
                "count": counts[key],
            }
        )
    return result
