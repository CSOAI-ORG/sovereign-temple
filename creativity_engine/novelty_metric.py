"""
Kolmogorov complexity approximation via zlib compression.

Provides normalized compression distance (NCD) as a proxy for algorithmic
information distance, following Li & Vitanyi (2004) and Cilibrasi & Vitanyi
(2005). Schmidhuber's "interestingness = compression progress" principle
applies: we reward not raw novelty but the degree to which new content
resists being compressed against a known reference corpus.

All functions use only stdlib zlib. No external dependencies.
"""

from __future__ import annotations

import zlib
from typing import Any, Dict, List


def _compressed_length(data: str) -> int:
    """Return the length of zlib-compressed UTF-8 bytes for a string.

    Uses maximum compression level (9) for the tightest approximation
    of Kolmogorov complexity available through zlib's DEFLATE.
    """
    return len(zlib.compress(data.encode("utf-8"), level=9))


def normalized_compression_distance(x: str, y: str) -> float:
    """Compute the Normalized Compression Distance between two strings.

    NCD(x, y) = (C(xy) - min(C(x), C(y))) / max(C(x), C(y))

    where C(s) is the compressed length of s and xy is their concatenation.

    Returns a float in [0.0, 1.0+epsilon]:
        - 0.0 indicates x and y are essentially identical in information content.
        - 1.0 indicates x and y share no compressible structure.
        - Values slightly above 1.0 are possible due to compression artifacts;
          they are clamped to 1.0.

    Edge cases:
        - If both strings are empty, returns 0.0.
        - If one string is empty, returns 1.0.

    Args:
        x: First string.
        y: Second string.

    Returns:
        NCD score clamped to [0.0, 1.0].
    """
    if not x and not y:
        return 0.0
    if not x or not y:
        return 1.0

    cx = _compressed_length(x)
    cy = _compressed_length(y)
    cxy = _compressed_length(x + y)

    denominator = max(cx, cy)
    if denominator == 0:
        return 0.0

    ncd = (cxy - min(cx, cy)) / denominator
    return max(0.0, min(1.0, ncd))


def kolmogorov_novelty(new_content: str, reference_corpus: List[str]) -> float:
    """Measure the novelty of new_content against a reference corpus.

    Computes the mean NCD between new_content and every item in the
    reference corpus. A high score means the new content cannot be
    efficiently compressed using patterns found in the corpus -- it is
    informationally novel.

    Interpretation:
        0.0 - 0.3  : Highly redundant / near-duplicate of existing knowledge.
        0.3 - 0.6  : Moderate novelty; shares structural patterns with corpus.
        0.6 - 0.8  : Substantially novel; limited overlap with known material.
        0.8 - 1.0  : Radically novel; almost no shared compressible structure.

    The "sweet spot" for Schmidhuber-style interestingness is typically
    0.4 - 0.7: novel enough to be learnable but not so alien as to be
    incompressible noise.

    Args:
        new_content: The string to evaluate for novelty.
        reference_corpus: List of reference strings to compare against.

    Returns:
        Mean NCD score in [0.0, 1.0]. Returns 1.0 if the corpus is empty
        (maximally novel by definition -- no prior knowledge exists).
    """
    if not reference_corpus:
        return 1.0

    if not new_content:
        return 0.0

    total_ncd = 0.0
    for ref in reference_corpus:
        total_ncd += normalized_compression_distance(new_content, ref)

    return total_ncd / len(reference_corpus)


def batch_novelty_scores(
    items: List[str],
    reference: List[str],
) -> List[Dict[str, Any]]:
    """Score multiple items for novelty against a shared reference corpus.

    Useful for ranking a batch of candidate outputs (e.g., from MAP-Elites
    or a generative model) by their informational novelty relative to
    existing knowledge.

    Each result dict contains:
        - "index": Original index of the item in the input list.
        - "novelty": The kolmogorov_novelty score.
        - "compressed_length": Compressed size of the item alone (proxy for
          intrinsic complexity).
        - "content_preview": First 120 characters of the item for identification.

    Results are sorted by novelty descending (most novel first).

    Args:
        items: List of strings to score.
        reference: Reference corpus to compare against.

    Returns:
        List of score dicts sorted by novelty descending.
    """
    results: List[Dict[str, Any]] = []

    for idx, item in enumerate(items):
        novelty = kolmogorov_novelty(item, reference)
        compressed = _compressed_length(item) if item else 0
        results.append({
            "index": idx,
            "novelty": round(novelty, 6),
            "compressed_length": compressed,
            "content_preview": item[:120] if item else "",
        })

    results.sort(key=lambda r: r["novelty"], reverse=True)
    return results
