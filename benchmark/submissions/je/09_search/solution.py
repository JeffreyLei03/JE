"""Unicode-aware full-text ranking over an in-memory document collection.

Public API:
    rank(query, documents, limit=10) -> list[tuple[str, int]]

Tokenization splits on every run of Unicode alphanumeric characters that does
not include the underscore, matching the regex ``[^\\W_]+``.  Text is casefolded
before tokenization so that comparison is case-insensitive and Unicode aware.
"""

from __future__ import annotations

import re
from collections import Counter

__all__ = ["rank", "tokenize"]

# Unicode alphanumeric runs, treating the underscore as a separator.
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Return the casefolded alphanumeric tokens of ``text``.

    ``[^\\W_]+`` matches Unicode letters/digits while excluding ``_``, so
    ``"Hello_World"`` becomes ``["hello", "world"]``.
    """
    return _TOKEN_RE.findall(text.casefold())


def rank(
    query: str,
    documents: dict[str, str],
    limit: int = 10,
) -> list[tuple[str, int]]:
    """Rank documents by how often they contain every query term.

    A document is a candidate only when it contains *all* unique query terms.
    Its score is the sum, over each unique query term, of that term's frequency
    inside the document.  Results are ordered by score descending and then by
    document id ascending.

    Args:
        query: Free-text query; empty (or token-less) queries produce ``[]``.
        documents: Mapping of document id to text.  Never mutated.
        limit: Maximum number of results.  ``0`` yields ``[]``; a negative,
            non-integer, or boolean value raises :class:`ValueError`.

    Raises:
        ValueError: If ``limit`` is not a non-negative integer (bools rejected).
    """
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be a non-negative integer")
    if limit < 0:
        raise ValueError("limit must be a non-negative integer")
    if limit == 0:
        return []

    terms = list(dict.fromkeys(tokenize(query)))
    if not terms:
        return []

    # Build an inverted index: term -> {document_id: frequency}.  This lets us
    # intersect the postings of all query terms and score without rescanning.
    index: dict[str, dict[str, int]] = {}
    for doc_id, text in documents.items():
        counts = Counter(tokenize(text))
        for term, freq in counts.items():
            index.setdefault(term, {})[doc_id] = freq

    postings = []
    for term in terms:
        p = index.get(term)
        if not p:
            # A required term is absent from the whole collection.
            return []
        postings.append(p)

    # Intersect starting from the smallest posting list.
    postings.sort(key=len)
    candidates = set(postings[0].keys())
    for p in postings[1:]:
        candidates &= p.keys()
        if not candidates:
            return []

    scored = [
        (doc_id, sum(p[doc_id] for p in postings))
        for doc_id in candidates
    ]
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored[:limit]
