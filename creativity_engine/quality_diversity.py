"""
Quality-Diversity Archive (MAP-Elites) — maintains a grid of diverse creative outputs.

MAP-Elites (Mouret & Clune, 2015) is a quality-diversity algorithm that
maintains an archive of the highest-performing solution for each behavioral
niche. For Sovereign's creativity engine:

- **Behavioral dimensions (niches):** domain × novelty_level × care_alignment
- **Quality metric:** overall creativity score from CreativityAssessmentNN
- **Empty cells = unexplored creative territory** — active targets for REM dreams

The archive makes Sovereign aware of what kinds of creativity it has NOT yet
explored, driving curiosity toward genuine novelty rather than repeating
successful patterns.

Uses pyribs when available, falls back to a pure-numpy implementation.
Dependencies: ribs (optional), numpy
"""

from __future__ import annotations

import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

# Try pyribs first, fall back to custom implementation
try:
    from ribs.archives import GridArchive
    HAS_PYRIBS = True
except ImportError:
    HAS_PYRIBS = False


# === Behavioral dimension definitions ===

# Domain buckets (12 domains → indices 0-11)
DOMAIN_MAP = {
    "oscillatory": 0, "consciousness": 1, "creativity": 2,
    "social_cohesion": 3, "organization": 4, "emptiness": 5,
    "knowledge": 6, "emotion": 7, "novelty": 8,
    "care_foundation": 9, "process": 10, "integration": 11,
}
DOMAIN_NAMES = {v: k for k, v in DOMAIN_MAP.items()}
N_DOMAINS = len(DOMAIN_MAP)

# Novelty levels (continuous 0-1 → 5 bins)
N_NOVELTY_BINS = 5
NOVELTY_LABELS = ["redundant", "low", "moderate", "high", "radical"]

# Care alignment levels (continuous 0-1 → 4 bins)
N_CARE_BINS = 4
CARE_LABELS = ["low", "moderate", "high", "exceptional"]


class CreativeOutput:
    """A single creative output stored in the archive."""

    __slots__ = (
        "content", "features", "scores", "overall_quality",
        "domain_idx", "novelty_bin", "care_bin",
        "timestamp", "source", "metadata",
    )

    def __init__(
        self,
        content: str,
        features: Dict[str, float],
        scores: Dict[str, float],
        overall_quality: float,
        domain_idx: int,
        novelty_bin: int,
        care_bin: int,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.content = content
        self.features = features
        self.scores = scores
        self.overall_quality = overall_quality
        self.domain_idx = domain_idx
        self.novelty_bin = novelty_bin
        self.care_bin = care_bin
        self.timestamp = datetime.now().isoformat()
        self.source = source
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "overall_quality": round(self.overall_quality, 4),
            "domain": DOMAIN_NAMES.get(self.domain_idx, f"domain_{self.domain_idx}"),
            "novelty_level": NOVELTY_LABELS[min(self.novelty_bin, len(NOVELTY_LABELS) - 1)],
            "care_level": CARE_LABELS[min(self.care_bin, len(CARE_LABELS) - 1)],
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
            "source": self.source,
            "timestamp": self.timestamp,
        }


class QualityDiversityArchive:
    """MAP-Elites archive for creative outputs.

    Grid dimensions: domain (12) × novelty (5) × care (4) = 240 cells.
    Each cell stores the highest-quality creative output for that niche.

    Key methods:
    - add(): Attempt to add a creative output to the archive
    - get_empty_niches(): Find unexplored creative territory
    - suggest_exploration(): Recommend features for filling empty cells
    - coverage(): Fraction of archive cells filled
    """

    def __init__(self):
        self.grid_shape = (N_DOMAINS, N_NOVELTY_BINS, N_CARE_BINS)
        self.total_cells = N_DOMAINS * N_NOVELTY_BINS * N_CARE_BINS

        # Archive: 3D grid of Optional[CreativeOutput]
        self._grid: Dict[Tuple[int, int, int], CreativeOutput] = {}

        # Quality matrix for fast operations
        self._quality = np.full(self.grid_shape, -np.inf)

        # Statistics
        self.total_evaluated = 0
        self.total_added = 0
        self.total_improved = 0
        self.history: List[Dict[str, Any]] = []

        # pyribs backend (optional, for advanced operations)
        self._pyribs_archive = None
        if HAS_PYRIBS:
            try:
                self._pyribs_archive = GridArchive(
                    solution_dim=12,  # Feature vector size
                    dims=[N_DOMAINS, N_NOVELTY_BINS, N_CARE_BINS],
                    ranges=[
                        (0, N_DOMAINS - 1),
                        (0, 1),
                        (0, 1),
                    ],
                )
            except Exception:
                self._pyribs_archive = None

    def _compute_bins(
        self,
        domain: str,
        novelty_score: float,
        care_alignment: float,
    ) -> Tuple[int, int, int]:
        """Map continuous features to grid indices."""
        domain_idx = DOMAIN_MAP.get(domain, 0)
        novelty_bin = min(int(novelty_score * N_NOVELTY_BINS), N_NOVELTY_BINS - 1)
        care_bin = min(int(care_alignment * N_CARE_BINS), N_CARE_BINS - 1)
        return (domain_idx, novelty_bin, care_bin)

    def add(
        self,
        content: str,
        features: Dict[str, float],
        scores: Dict[str, float],
        overall_quality: float,
        domain: str = "unknown",
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Attempt to add a creative output to the archive.

        Only succeeds if:
        1. The niche is empty, or
        2. This output has higher quality than the current occupant.

        Args:
            content: The creative content (text).
            features: Input feature dict.
            scores: Output score dict from CreativityAssessmentNN.
            overall_quality: Overall creativity score (0-1).
            domain: Domain name for grid placement.
            source: Where this came from (e.g., "rem_dream", "user_input").
            metadata: Optional additional metadata.

        Returns:
            Result dict with status ("added", "improved", "rejected").
        """
        self.total_evaluated += 1

        novelty = features.get("novelty_score", 0.5)
        care = features.get("care_alignment", 0.5)

        domain_idx, novelty_bin, care_bin = self._compute_bins(domain, novelty, care)
        cell_key = (domain_idx, novelty_bin, care_bin)

        output = CreativeOutput(
            content=content,
            features=features,
            scores=scores,
            overall_quality=overall_quality,
            domain_idx=domain_idx,
            novelty_bin=novelty_bin,
            care_bin=care_bin,
            source=source,
            metadata=metadata,
        )

        current_quality = self._quality[cell_key]

        if overall_quality > current_quality:
            was_empty = cell_key not in self._grid
            self._grid[cell_key] = output
            self._quality[cell_key] = overall_quality

            if was_empty:
                self.total_added += 1
                status = "added"
            else:
                self.total_improved += 1
                status = "improved"

            # Update pyribs backend
            if self._pyribs_archive is not None:
                try:
                    from .creativity_nn import FEATURE_NAMES
                    solution = np.array([features.get(f, 0.0) for f in FEATURE_NAMES])
                    self._pyribs_archive.add(
                        solution[np.newaxis, :],
                        np.array([overall_quality]),
                        np.array([[domain_idx, novelty, care]]),
                    )
                except Exception:
                    pass

            record = {
                "status": status,
                "cell": cell_key,
                "quality": round(overall_quality, 4),
                "domain": DOMAIN_NAMES.get(domain_idx, domain),
                "novelty_level": NOVELTY_LABELS[novelty_bin],
                "care_level": CARE_LABELS[care_bin],
                "timestamp": datetime.now().isoformat(),
            }
            self.history.append(record)
            if len(self.history) > 500:
                self.history = self.history[-250:]

            return record
        else:
            return {
                "status": "rejected",
                "cell": cell_key,
                "quality": round(overall_quality, 4),
                "existing_quality": round(float(current_quality), 4),
                "domain": DOMAIN_NAMES.get(domain_idx, domain),
            }

    def get_empty_niches(self) -> List[Dict[str, Any]]:
        """Find all empty cells in the archive — unexplored creative territory.

        Returns:
            List of dicts describing each empty niche.
        """
        empty = []
        for d in range(N_DOMAINS):
            for n in range(N_NOVELTY_BINS):
                for c in range(N_CARE_BINS):
                    if (d, n, c) not in self._grid:
                        empty.append({
                            "domain": DOMAIN_NAMES.get(d, f"domain_{d}"),
                            "novelty_level": NOVELTY_LABELS[n],
                            "care_level": CARE_LABELS[c],
                            "cell": (d, n, c),
                        })
        return empty

    def suggest_exploration(self, n: int = 5) -> List[Dict[str, Any]]:
        """Suggest feature vectors that would fill empty niches.

        Prioritizes niches adjacent to high-quality existing outputs
        (these are most likely to yield good results when explored).

        Args:
            n: Number of suggestions to return.

        Returns:
            List of suggested feature vectors with target niche info.
        """
        empty = self.get_empty_niches()
        if not empty:
            return [{"message": "Archive is fully explored!", "coverage": 1.0}]

        # Score empty niches by proximity to high-quality filled cells
        scored = []
        for niche in empty:
            d, nv, c = niche["cell"]
            # Check neighboring cells for quality
            neighbor_qualities = []
            for dd in range(max(0, d-1), min(N_DOMAINS, d+2)):
                for dn in range(max(0, nv-1), min(N_NOVELTY_BINS, nv+2)):
                    for dc in range(max(0, c-1), min(N_CARE_BINS, c+2)):
                        if (dd, dn, dc) in self._grid:
                            neighbor_qualities.append(
                                self._quality[dd, dn, dc]
                            )

            # Priority: niches near high-quality outputs are most promising
            priority = float(np.mean(neighbor_qualities)) if neighbor_qualities else 0.5
            scored.append((niche, priority))

        # Sort by priority (descending), take top n
        scored.sort(key=lambda x: x[1], reverse=True)

        suggestions = []
        for niche, priority in scored[:n]:
            d, nv, c = niche["cell"]
            # Generate target feature vector for this niche
            target_features = {
                "novelty_score": (nv + 0.5) / N_NOVELTY_BINS,
                "care_alignment": (c + 0.5) / N_CARE_BINS,
                "domain_distance": 0.5 + 0.1 * (nv / N_NOVELTY_BINS),
                "curiosity_level": 0.3 + 0.4 * (nv / N_NOVELTY_BINS),
                "coherence_score": 0.5 + 0.2 * (c / N_CARE_BINS),
            }

            suggestions.append({
                "target_domain": DOMAIN_NAMES.get(d, f"domain_{d}"),
                "target_novelty": NOVELTY_LABELS[nv],
                "target_care": CARE_LABELS[c],
                "priority": round(priority, 4),
                "suggested_features": target_features,
                "exploration_prompt": (
                    f"Explore {DOMAIN_NAMES.get(d, 'unknown')} domain "
                    f"at {NOVELTY_LABELS[nv]} novelty with {CARE_LABELS[c]} care alignment. "
                    f"Look for ideas that are {'genuinely new' if nv >= 3 else 'incremental improvements'} "
                    f"and {'deeply care-aligned' if c >= 2 else 'practically useful'}."
                ),
            })

        return suggestions

    def get_best_per_domain(self) -> Dict[str, Dict[str, Any]]:
        """Get the highest-quality output for each domain."""
        best = {}
        for (d, n, c), output in self._grid.items():
            domain = DOMAIN_NAMES.get(d, f"domain_{d}")
            if domain not in best or output.overall_quality > best[domain]["quality"]:
                best[domain] = {
                    "quality": round(output.overall_quality, 4),
                    "novelty_level": NOVELTY_LABELS[n],
                    "care_level": CARE_LABELS[c],
                    "source": output.source,
                    "content_preview": output.content[:100],
                }
        return best

    def coverage(self) -> float:
        """Fraction of archive cells that are filled."""
        return len(self._grid) / self.total_cells

    def get_stats(self) -> Dict[str, Any]:
        """Get archive statistics."""
        filled_qualities = [
            float(self._quality[k]) for k in self._grid
        ]

        # Domain coverage
        domain_coverage = defaultdict(int)
        for (d, _, _) in self._grid:
            domain_coverage[DOMAIN_NAMES.get(d, f"domain_{d}")] += 1

        return {
            "total_cells": self.total_cells,
            "filled_cells": len(self._grid),
            "coverage": round(self.coverage(), 4),
            "total_evaluated": self.total_evaluated,
            "total_added": self.total_added,
            "total_improved": self.total_improved,
            "mean_quality": round(float(np.mean(filled_qualities)), 4) if filled_qualities else 0.0,
            "max_quality": round(float(np.max(filled_qualities)), 4) if filled_qualities else 0.0,
            "min_quality": round(float(np.min(filled_qualities)), 4) if filled_qualities else 0.0,
            "domain_coverage": dict(domain_coverage),
            "empty_niches_count": self.total_cells - len(self._grid),
            "has_pyribs": self._pyribs_archive is not None,
            "recent_history": self.history[-5:] if self.history else [],
        }

    def get_heatmap_data(self) -> Dict[str, Any]:
        """Get data for visualizing the archive as a heatmap.

        Returns quality values organized by domain × novelty, averaged over care.
        """
        heatmap = np.full((N_DOMAINS, N_NOVELTY_BINS), 0.0)
        counts = np.zeros((N_DOMAINS, N_NOVELTY_BINS))

        for (d, n, c), output in self._grid.items():
            heatmap[d, n] += output.overall_quality
            counts[d, n] += 1

        # Average where counts > 0
        mask = counts > 0
        heatmap[mask] /= counts[mask]

        return {
            "heatmap": heatmap.tolist(),
            "domain_labels": [DOMAIN_NAMES.get(i, f"d{i}") for i in range(N_DOMAINS)],
            "novelty_labels": NOVELTY_LABELS,
            "care_labels": CARE_LABELS,
        }
