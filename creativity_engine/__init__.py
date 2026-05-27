"""
Sovereign Creativity Engine
Civilizational knowledge corpus (47 traditions), novelty metrics,
creative assessment neural network, and training pipeline.

Integrates insights from Sufi dhikr, Kashmiri Shaivism, Ibn Arabi's Barzakh,
Vedantic consciousness, Koestler's bisociation, Bogdanov's tektology,
Ubuntu philosophy, Aboriginal Dreamtime, and 40 more traditions
into Sovereign's neural architecture.
"""

from .novelty_metric import kolmogorov_novelty, normalized_compression_distance, batch_novelty_scores

try:
    from .civilizational_corpus import CivilizationalTradition, CORPUS
except ImportError:
    CORPUS = []
    CivilizationalTradition = None

try:
    from .creativity_nn import CreativityAssessmentNN, FEATURE_NAMES, OUTPUT_NAMES
except ImportError:
    CreativityAssessmentNN = None

try:
    from .corpus_ingester import ingest_corpus, get_corpus_stats
except ImportError:
    ingest_corpus = None
    get_corpus_stats = None

try:
    from .training_pipeline import CreativityTrainingPipeline
except ImportError:
    CreativityTrainingPipeline = None

# Tier 2: Cross-domain bisociation detection
try:
    from .cross_domain_linker import CrossDomainLinker, BisociationLink
except ImportError:
    CrossDomainLinker = None
    BisociationLink = None

# Tier 2: Stochastic resonance for creativity amplification
try:
    from .stochastic_resonance import StochasticResonanceEngine, apply_stochastic_resonance
except ImportError:
    StochasticResonanceEngine = None
    apply_stochastic_resonance = None

# Tier 2: Quality-Diversity archive (MAP-Elites)
try:
    from .quality_diversity import QualityDiversityArchive, CreativeOutput
except ImportError:
    QualityDiversityArchive = None
    CreativeOutput = None

__all__ = [
    # Novelty metrics
    'kolmogorov_novelty',
    'normalized_compression_distance',
    'batch_novelty_scores',
    # Corpus
    'CivilizationalTradition',
    'CORPUS',
    # Neural model
    'CreativityAssessmentNN',
    'FEATURE_NAMES',
    'OUTPUT_NAMES',
    # Ingestion
    'ingest_corpus',
    'get_corpus_stats',
    # Training
    'CreativityTrainingPipeline',
    # Tier 2: Bisociation
    'CrossDomainLinker',
    'BisociationLink',
    # Tier 2: Stochastic Resonance
    'StochasticResonanceEngine',
    'apply_stochastic_resonance',
    # Tier 2: Quality-Diversity
    'QualityDiversityArchive',
    'CreativeOutput',
]
