"""Normalize a collection of half-open integer intervals.

``normalize`` accepts any iterable of ``(start, end)`` pairs, validates that
every endpoint is a real integer (booleans are rejected) and that every range
is non-empty (``start < end``), then returns a sorted list of disjoint merged
ranges.  Ranges that overlap *or merely touch* (``start == previous end``) are
combined.  The caller's data is never mutated and generators are accepted.
"""

from __future__ import annotations

from collections.abc import Iterable

__all__ = ["normalize"]

Interval = tuple[int, int]


def _coerce_pair(pair: object) -> Interval:
    """Validate and return *pair* as a canonical ``(start, end)`` tuple."""
    if isinstance(pair, (str, bytes, bytearray)):
        raise TypeError(f"interval must be a pair of integers, got {pair!r}")

    try:
        start, end = pair  # type: ignore[misc]
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"interval must be an iterable of exactly two integers, got {pair!r}"
        ) from exc

    if isinstance(start, bool) or not isinstance(start, int):
        raise TypeError(f"interval start must be an int, got {start!r}")
    if isinstance(end, bool) or not isinstance(end, int):
        raise TypeError(f"interval end must be an int, got {end!r}")
    if start >= end:
        raise ValueError(f"interval requires start < end, got ({start}, {end})")
    return start, end


def normalize(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Sort and merge half-open integer intervals.

    Args:
        intervals: An iterable of ``(start, end)`` pairs.  Generators are
            fully consumed; the input is never mutated.

    Returns:
        A new list of disjoint, sorted, merged ``(start, end)`` tuples.

    Raises:
        TypeError: If any element is not a pair of integers, or if a boolean
            or other non-integer endpoint is supplied.
        ValueError: If any pair has ``start >= end``; this is validated for
            every pair, even ones later swallowed by a merge.
    """
    # Materialize and validate up-front so that generators work, caller data
    # is untouched, and every pair (even subsumed ones) is checked.
    pairs = [_coerce_pair(pair) for pair in intervals]

    if not pairs:
        return []

    pairs.sort()

    result: list[Interval] = []
    append = result.append
    for start, end in pairs:
        if result and start <= result[-1][1]:
            last_start, last_end = result[-1]
            if end > last_end:
                result[-1] = (last_start, end)
        else:
            append((start, end))
    return result
