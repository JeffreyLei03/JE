"""Streaming JSONL sales aggregation and CLI."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import TextIO


def process(source: TextIO, sink: TextIO) -> dict:
    stats = {"accepted": 0, "invalid": 0, "ignored": 0}
    totals = defaultdict(lambda: [0, 0])
    for line in source:
        if not line.strip():
            stats["ignored"] += 1
            continue
        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            stats["invalid"] += 1
            continue
        if not isinstance(record, dict):
            stats["invalid"] += 1
        elif record.get("type") != "sale":
            stats["ignored"] += 1
        elif (
            not isinstance(record.get("customer"), str)
            or not record["customer"].strip()
            or type(record.get("amount")) is not int
            or record["amount"] < 0
        ):
            stats["invalid"] += 1
        else:
            bucket = totals[record["customer"].strip()]
            bucket[0] += record["amount"]
            bucket[1] += 1
            stats["accepted"] += 1
    for customer, (total, count) in sorted(totals.items()):
        sink.write(
            json.dumps({"customer": customer, "total": total, "count": count}, ensure_ascii=False)
            + "\n"
        )
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    if Path(args.input).resolve() == Path(args.output).resolve():
        parser.error("Input and output are the same path")
    with (
        open(args.input, encoding="utf-8") as source,
        open(args.output, "w", encoding="utf-8") as sink,
    ):
        print(json.dumps(process(source, sink)))
