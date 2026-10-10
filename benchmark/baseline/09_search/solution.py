"""Unicode term-frequency AND search."""

import re
from collections import Counter


def rank(query: str, documents: dict[str, str], limit: int = 10) -> list[tuple[str, int]]:
    if type(limit) is not int or limit < 0:
        raise ValueError("Invalid limit")
    terms = set(re.findall(r"[^\W_]+", query.casefold()))
    if not terms or limit == 0:
        return []
    results = []
    for identifier, text in documents.items():
        counts = Counter(re.findall(r"[^\W_]+", text.casefold()))
        if terms.issubset(counts):
            results.append((identifier, sum(counts[term] for term in terms)))
    return sorted(results, key=lambda pair: (-pair[1], pair[0]))[:limit]
