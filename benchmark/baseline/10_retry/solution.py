"""Deterministic round-robin retry executor."""

from collections.abc import Callable, Iterable
from typing import Any


def run_jobs(jobs: Iterable[str], handler: Callable[[str, int], Any], max_attempts: int) -> dict:
    if type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("Invalid attempts")
    pending = list(jobs)
    if any(not isinstance(job, str) for job in pending) or len(set(pending)) != len(pending):
        raise ValueError("Invalid jobs")
    results = {}
    attempts = {}
    failed = {}
    for attempt in range(1, max_attempts + 1):
        retry = []
        for job in pending:
            attempts[job] = attempt
            try:
                results[job] = handler(job, attempt)
            except Exception as exc:
                if isinstance(exc, ValueError) or attempt == max_attempts:
                    failed[job] = type(exc).__name__
                else:
                    retry.append(job)
        pending = retry
        if not pending:
            break
    return {"results": results, "attempts": attempts, "failed": failed}
