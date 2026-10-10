"""Round-robin job execution with per-job retries."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Mapping


def run_jobs(
    jobs: Iterable[str],
    handler: Callable[[str, int], Any],
    max_attempts: int,
) -> Dict[str, Mapping[str, Any]]:
    """Run ``handler`` for every job round-robin, retrying transient failures.

    Attempt 1 runs for every job in input order.  Each subsequent attempt runs
    only for jobs that failed with a retryable (non-``ValueError``)
    :class:`Exception`, preserving input order.  Returns a dict with three
    mappings: ``results`` (successful job id -> returned value), ``attempts``
    (every job id -> number of handler executions) and ``failed`` (terminal
    failure job id -> exception class name).

    Validation happens before any handler invocation.  ``BaseException``
    subclasses that are not :class:`Exception` propagate to the caller.
    """
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise ValueError("max_attempts must be a positive integer")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be a positive integer")

    job_list = list(jobs)
    seen: set[str] = set()
    for job in job_list:
        if not isinstance(job, str):
            raise ValueError("job ids must be strings")
        if job in seen:
            raise ValueError("job ids must be unique")
        seen.add(job)

    results: Dict[str, Any] = {}
    attempts: Dict[str, int] = {job: 0 for job in job_list}
    failed: Dict[str, str] = {}

    pending = list(job_list)
    for attempt in range(1, max_attempts + 1):
        if not pending:
            break
        retry: list[str] = []
        for job in pending:
            attempts[job] += 1
            try:
                value = handler(job, attempt)
            except ValueError as exc:
                # Permanent failure: never retried.
                failed[job] = type(exc).__name__
            except Exception as exc:  # noqa: BLE001 - transient by contract
                if attempt >= max_attempts:
                    failed[job] = type(exc).__name__
                else:
                    retry.append(job)
            else:
                results[job] = value
        pending = retry

    return {"results": results, "attempts": attempts, "failed": failed}
