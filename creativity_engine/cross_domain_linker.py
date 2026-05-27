"""
Cross-Domain Bisociation Linker — finds surprising connections between traditions.

Implements Koestler's bisociation principle: creativity emerges when two
previously unconnected frames of reference collide. Uses TF-IDF + cosine
similarity to compute semantic distances between all 40 civilizational
traditions, then identifies the most surprising (high-distance yet
high-care-weight) cross-domain links.

These links feed directly into:
- REM dream phase (creative recombination targets)
- CreativityAssessmentNN (cross_domain_links feature)
- AgentCouncil proposals (novel synthesis suggestions)

Dependencies: sklearn (already installed), numpy (already installed)
"""

from __future__ import annotations

import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from .civilizational_corpus import CORPUS, CivilizationalTradition
except ImportError:
    CORPUS = []


class BisociationLink:
    """A surprising connection between two traditions from different domains."""

    __slots__ = (
        "tradition_a", "tradition_b", "domain_a", "domain_b",
        "semantic_distance", "combined_care", "bisociation_score",
        "synthesis_prompt",
    )

    def __init__(
        self,
        tradition_a: str,
        tradition_b: str,
        domain_a: str,
        domain_b: str,
        semantic_distance: float,
        combined_care: float,
    ):
        self.tradition_a = tradition_a
        self.tradition_b = tradition_b
        self.domain_a = domain_a
        self.domain_b = domain_b
        self.semantic_distance = semantic_distance
        self.combined_care = combined_care
        # Bisociation score: high distance × high care = most creative potential
        self.bisociation_score = semantic_distance * combined_care
        self.synthesis_prompt = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tradition_a": self.tradition_a,
            "tradition_b": self.tradition_b,
            "domain_a": self.domain_a,
            "domain_b": self.domain_b,
            "semantic_distance": round(self.semantic_distance, 4),
            "combined_care": round(self.combined_care, 4),
            "bisociation_score": round(self.bisociation_score, 4),
            "synthesis_prompt": self.synthesis_prompt,
        }


class CrossDomainLinker:
    """Finds and ranks cross-domain bisociation links between traditions.

    Core algorithm:
    1. TF-IDF vectorize all tradition descriptions
    2. Compute pairwise cosine distances (1 - similarity)
    3. Filter to cross-domain pairs only
    4. Rank by bisociation_score = distance × combined_care_weight
    5. Generate synthesis prompts for top links

    The result is an ordered list of the most promising creative collisions.
    """

    def __init__(self, corpus: Optional[List] = None):
        self.corpus = corpus or CORPUS
        self.similarity_matrix: Optional[np.ndarray] = None
        self.distance_matrix: Optional[np.ndarray] = None
        self.tfidf_matrix = None
        self.vectorizer = None
        self.links: List[BisociationLink] = []
        self._is_computed = False

    def _tradition_text(self, t) -> str:
        """Extract full searchable text from a tradition."""
        parts = [
            t.tradition_name,
            t.domain,
            t.key_concept,
            t.operational_definition,
            t.computational_analog,
            t.integration_target,
        ]
        return " ".join(str(p) for p in parts if p)

    def compute_distances(self) -> np.ndarray:
        """Compute pairwise semantic distances between all traditions.

        Returns:
            Distance matrix of shape (n_traditions, n_traditions).
        """
        if not HAS_SKLEARN:
            raise RuntimeError("sklearn required for TF-IDF vectorization")
        if not self.corpus:
            raise ValueError("No corpus loaded")

        # Build document collection
        documents = [self._tradition_text(t) for t in self.corpus]

        # TF-IDF with sublinear TF (dampens frequent terms)
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words="english",
            sublinear_tf=True,
            ngram_range=(1, 2),  # Unigrams + bigrams for concept detection
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(documents)

        # Cosine similarity → distance
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)
        self.distance_matrix = 1.0 - self.similarity_matrix

        # Clamp to [0, 1]
        self.distance_matrix = np.clip(self.distance_matrix, 0.0, 1.0)

        self._is_computed = True
        return self.distance_matrix

    def find_bisociations(
        self,
        min_distance: float = 0.4,
        top_k: int = 30,
        cross_domain_only: bool = True,
    ) -> List[BisociationLink]:
        """Find the most promising cross-domain bisociation links.

        Args:
            min_distance: Minimum semantic distance threshold (0-1).
            top_k: Return top-k links by bisociation score.
            cross_domain_only: If True, only return links between different domains.

        Returns:
            Sorted list of BisociationLink objects.
        """
        if not self._is_computed:
            self.compute_distances()

        n = len(self.corpus)
        links = []

        for i in range(n):
            for j in range(i + 1, n):
                t_a = self.corpus[i]
                t_b = self.corpus[j]

                # Skip same-domain pairs if requested
                if cross_domain_only and t_a.domain == t_b.domain:
                    continue

                dist = float(self.distance_matrix[i, j])
                if dist < min_distance:
                    continue

                combined_care = (t_a.care_weight + t_b.care_weight) / 2.0

                link = BisociationLink(
                    tradition_a=t_a.tradition_name,
                    tradition_b=t_b.tradition_name,
                    domain_a=t_a.domain,
                    domain_b=t_b.domain,
                    semantic_distance=dist,
                    combined_care=combined_care,
                )

                # Generate synthesis prompt
                link.synthesis_prompt = (
                    f"What emerges when {t_a.key_concept} ({t_a.domain}) "
                    f"meets {t_b.key_concept} ({t_b.domain})? "
                    f"How might {t_a.computational_analog} inform or transform "
                    f"{t_b.computational_analog}?"
                )

                links.append(link)

        # Sort by bisociation score (descending)
        links.sort(key=lambda l: l.bisociation_score, reverse=True)
        self.links = links[:top_k]
        return self.links

    def get_domain_distance_map(self) -> Dict[str, Dict[str, float]]:
        """Compute average semantic distance between each pair of domains.

        Returns:
            Nested dict: domain_a → domain_b → average_distance
        """
        if not self._is_computed:
            self.compute_distances()

        domain_distances: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

        n = len(self.corpus)
        for i in range(n):
            for j in range(i + 1, n):
                d_a = self.corpus[i].domain
                d_b = self.corpus[j].domain
                dist = float(self.distance_matrix[i, j])
                domain_distances[d_a][d_b].append(dist)
                domain_distances[d_b][d_a].append(dist)

        # Average distances
        result: Dict[str, Dict[str, float]] = {}
        for d_a, inner in domain_distances.items():
            result[d_a] = {}
            for d_b, dists in inner.items():
                result[d_a][d_b] = round(float(np.mean(dists)), 4)

        return result

    def suggest_dream_targets(self, n: int = 5) -> List[Dict[str, Any]]:
        """Suggest tradition pairs for REM dream creative recombination.

        Selects from top bisociation links with some randomness to avoid
        always recombining the same pairs.

        Args:
            n: Number of dream targets to suggest.

        Returns:
            List of dicts with tradition pairs and synthesis prompts.
        """
        if not self.links:
            self.find_bisociations()

        if not self.links:
            return []

        # Weighted random selection — higher bisociation score = more likely
        scores = np.array([l.bisociation_score for l in self.links])
        if scores.sum() == 0:
            probs = np.ones(len(scores)) / len(scores)
        else:
            probs = scores / scores.sum()

        n = min(n, len(self.links))
        indices = np.random.choice(len(self.links), size=n, replace=False, p=probs)

        targets = []
        for idx in indices:
            link = self.links[idx]
            targets.append({
                "tradition_a": link.tradition_a,
                "tradition_b": link.tradition_b,
                "domains": f"{link.domain_a} × {link.domain_b}",
                "bisociation_score": round(link.bisociation_score, 4),
                "synthesis_prompt": link.synthesis_prompt,
            })

        return targets

    def get_tradition_connectivity(self) -> List[Dict[str, Any]]:
        """Rank traditions by how many strong cross-domain links they have.

        Traditions with high connectivity are "bridge concepts" —
        they connect many disparate domains and are especially valuable
        for creative synthesis.
        """
        if not self.links:
            self.find_bisociations()

        connectivity: Dict[str, Dict[str, Any]] = {}
        for link in self.links:
            for name, domain in [
                (link.tradition_a, link.domain_a),
                (link.tradition_b, link.domain_b),
            ]:
                if name not in connectivity:
                    connectivity[name] = {
                        "tradition": name,
                        "domain": domain,
                        "link_count": 0,
                        "total_bisociation": 0.0,
                        "connected_domains": set(),
                    }
                connectivity[name]["link_count"] += 1
                connectivity[name]["total_bisociation"] += link.bisociation_score
                other_domain = link.domain_b if name == link.tradition_a else link.domain_a
                connectivity[name]["connected_domains"].add(other_domain)

        # Convert sets to lists and sort by total bisociation score
        result = []
        for info in connectivity.values():
            result.append({
                "tradition": info["tradition"],
                "domain": info["domain"],
                "link_count": info["link_count"],
                "total_bisociation": round(info["total_bisociation"], 4),
                "connected_domains": sorted(info["connected_domains"]),
                "domain_reach": len(info["connected_domains"]),
            })

        result.sort(key=lambda x: x["total_bisociation"], reverse=True)
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get linker statistics."""
        if not self._is_computed:
            return {"computed": False, "corpus_size": len(self.corpus)}

        return {
            "computed": True,
            "corpus_size": len(self.corpus),
            "total_links": len(self.links),
            "avg_distance": round(float(np.mean(self.distance_matrix)), 4),
            "max_distance": round(float(np.max(self.distance_matrix)), 4),
            "avg_bisociation": round(
                float(np.mean([l.bisociation_score for l in self.links])), 4
            ) if self.links else 0.0,
            "top_link": self.links[0].to_dict() if self.links else None,
        }
