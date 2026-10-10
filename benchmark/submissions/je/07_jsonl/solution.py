"""JSONL sales aggregation task.

Public API:
    process(source, sink) -> dict

The function consumes ``source`` line by line (never via ``read``/``readlines``)
and emits one JSON object per accepted customer to ``sink`` as JSONL.
"""

from __future__ import annotations

import json
import os
import sys
from typing import TextIO


def _validate_sale(obj: dict) -> str | None:
    """Validate a sale object.

    Returns the stripped customer name when valid, otherwise ``None``.
    """
    customer = obj.get("customer")
    amount = obj.get("amount")

    if not isinstance(customer, str):
        return None
    customer = customer.strip()
    if not customer:
        return None

    # bool is a subclass of int; reject it explicitly.
    if isinstance(amount, bool) or not isinstance(amount, int):
        return None
    if amount < 0:
        return None

    return customer


def process(source: TextIO, sink: TextIO) -> dict:
    """Process JSONL sales from ``source`` and write aggregates to ``sink``.

    Returns a stats dict with ``accepted``, ``invalid`` and ``ignored`` counts.
    """
    totals: dict[str, int] = {}
    counts: dict[str, int] = {}
    accepted = 0
    invalid = 0
    ignored = 0

    for line in source:
        if not line.strip():
            ignored += 1
            continue

        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            invalid += 1
            continue

        if not isinstance(obj, dict):
            invalid += 1
            continue

        if obj.get("type") != "sale":
            ignored += 1
            continue

        customer = _validate_sale(obj)
        if customer is None:
            invalid += 1
            continue

        accepted += 1
        totals[customer] = totals.get(customer, 0) + obj["amount"]
        counts[customer] = counts.get(customer, 0) + 1

    for customer in sorted(totals):
        record = {
            "customer": customer,
            "total": totals[customer],
            "count": counts[customer],
        }
        sink.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {"accepted": accepted, "invalid": invalid, "ignored": ignored}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python solution.py INPUT OUTPUT", file=sys.stderr)
        return 2

    input_path = os.path.realpath(argv[1])
    output_path = os.path.realpath(argv[2])

    if input_path == output_path:
        print("error: input and output resolve to the same path", file=sys.stderr)
        return 1

    with open(input_path, "r", encoding="utf-8") as source:
        with open(output_path, "w", encoding="utf-8") as sink:
            stats = process(source, sink)

    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
