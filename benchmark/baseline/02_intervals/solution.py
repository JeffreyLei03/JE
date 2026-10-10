"""Validated immutable interval normalization."""


def normalize(intervals) -> list[tuple[int, int]]:
    values = []
    for pair in intervals:
        try:
            start, end = pair
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid interval") from exc
        if type(start) is not int or type(end) is not int or start >= end:
            raise ValueError("Invalid bounds")
        values.append((start, end))
    result = []
    for start, end in sorted(values):
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result
