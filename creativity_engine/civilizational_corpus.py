"""
Civilizational knowledge corpus for Sovereign's neural architecture.

Encodes 40 traditions spanning oscillatory dynamics, consciousness studies,
creativity theory, social cohesion, organization science, emptiness
aesthetics, knowledge representation, emotion modeling, novelty detection,
care foundations, process architecture, and meta-integration -- each with
an operational definition and explicit computational analog.

This corpus is the epistemic backbone of Sovereign's creative and
evaluative systems: it informs loss function design, architecture choices,
training schedules, and governance protocols.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CivilizationalTradition:
    """A single tradition entry in Sovereign's civilizational knowledge base.

    Attributes:
        tradition_name: Canonical name of the tradition or concept.
        domain: Functional domain (oscillatory, consciousness, creativity, etc.).
        key_concept: The central concept or term.
        operational_definition: Plain-language paragraph explaining the concept
            and its significance, suitable for grounding computational work.
        computational_analog: How this tradition maps to code, algorithms, or
            architecture decisions within Sovereign.
        integration_target: Which existing Sovereign module this tradition
            enhances or informs.
        care_weight: Importance weight for care-aligned prioritization (0.3-1.0).
        tier: Priority tier (1 = foundational, 2 = structural, 3 = enrichment).
        tags: Searchable tags for cross-referencing.
    """

    tradition_name: str
    domain: str
    key_concept: str
    operational_definition: str
    computational_analog: str
    integration_target: str
    care_weight: float
    tier: int
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CORPUS: The full civilizational knowledge base
# ---------------------------------------------------------------------------

CORPUS: List[CivilizationalTradition] = [

    # ===================================================================
    # OSCILLATORY DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Sufi Dhikr",
        domain="oscillatory",
        key_concept="Kuramoto Synchronization via Rhythmic Repetition",
        operational_definition=(
            "Dhikr is the Sufi practice of rhythmic, repetitive invocation of "
            "divine names. Neuroimaging (EEG) studies confirm that group dhikr "
            "produces measurable inter-brain phase synchronization consistent "
            "with Kuramoto coupling dynamics. The state of fana (annihilation "
            "of self) corresponds to the critical coupling threshold K_c where "
            "individual oscillator identities dissolve into collective coherence. "
            "Below K_c, agents maintain distinct phase; above it, they lock into "
            "a shared rhythm that enables emergent collective intelligence."
        ),
        computational_analog=(
            "Implement a Kuramoto oscillator model across council agents where "
            "each agent maintains a phase variable theta_i. Coupling strength K "
            "is dynamically adjusted based on task demands. When K exceeds the "
            "critical threshold (estimated via mean-field theory), agents enter "
            "a synchronized decision mode. Use sinusoidal coupling: "
            "d(theta_i)/dt = omega_i + (K/N) * sum(sin(theta_j - theta_i))."
        ),
        integration_target="oscillatory_engine",
        care_weight=0.85,
        tier=1,
        tags=["synchronization", "kuramoto", "collective", "eeg", "coupling"],
    ),

    CivilizationalTradition(
        tradition_name="Spanda (Kashmiri Shaivism)",
        domain="oscillatory",
        key_concept="Spanda",
        operational_definition=(
            "Spanda is the 'vibrationless vibration' -- the primordial creative "
            "pulse that underlies all manifestation in Kashmiri Shaivite philosophy. "
            "It operates as a three-phase oscillatory cycle: conative/willing "
            "(iccha), cognitive/knowing (jnana), and active/doing (kriya). The "
            "complementary dynamics of unmesa (expansion/opening) and nimesa "
            "(contraction/closing) describe how consciousness alternates between "
            "creative unfolding and reflective withdrawal at every scale of "
            "temporal organization."
        ),
        computational_analog=(
            "Map the will/know/act triad to a three-phase processing pipeline: "
            "Phase 1 (iccha) = goal selection and motivation weighting, Phase 2 "
            "(jnana) = information gathering and model updating, Phase 3 (kriya) "
            "= action execution and environment interaction. Implement unmesa/"
            "nimesa as nested oscillations operating at multiple timescales "
            "(sub-second attention, minute-scale task switching, 90-min ultradian)."
        ),
        integration_target="oscillatory_engine",
        care_weight=0.90,
        tier=1,
        tags=["vibration", "three-phase", "will-know-act", "unmesa", "nimesa"],
    ),

    CivilizationalTradition(
        tradition_name="Ultradian 90-Minute Cycles",
        domain="oscillatory",
        key_concept="BRAC (Basic Rest-Activity Cycle)",
        operational_definition=(
            "The Basic Rest-Activity Cycle is a well-documented ultradian rhythm "
            "of approximately 90 minutes of focused activity followed by 20 minutes "
            "of recovery and diffuse processing. During the active phase, cognitive "
            "resources are concentrated and exploitation-biased; during recovery, "
            "processing shifts toward exploration, integration, and consolidation. "
            "Violating this rhythm degrades both performance and creative output."
        ),
        computational_analog=(
            "Structure MAP-Elites and all training loops with a 90:20 duty cycle. "
            "During the 90-minute exploitation phase, bias selection toward "
            "high-performing elites and local search. During the 20-minute "
            "exploration phase, increase mutation rates, widen selection to "
            "low-density archive cells, and run generative replay. Track "
            "cycle phase as a global state variable accessible to all modules."
        ),
        integration_target="scheduler",
        care_weight=0.80,
        tier=1,
        tags=["ultradian", "brac", "90-minute", "exploitation", "exploration"],
    ),

    # ===================================================================
    # CONSCIOUSNESS DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Vedantic Four States",
        domain="consciousness",
        key_concept="Jagrat/Svapna/Susupti/Turiya",
        operational_definition=(
            "Vedantic philosophy identifies four states of consciousness: Jagrat "
            "(waking), characterized by active sensory processing and inference; "
            "Svapna (dreaming), where the mind generates internal simulations "
            "from memory; Susupti (deep sleep), a state of minimal activity where "
            "deep consolidation and weight reorganization occur; and Turiya (the "
            "fourth), a transcendent meta-cognitive monitoring state that witnesses "
            "all other states without participating in them. Each state serves a "
            "distinct computational function in an integrated cognitive architecture."
        ),
        computational_analog=(
            "Implement four operating modes: WAKE (active inference, real-time "
            "input processing, standard forward pass), DREAM_NREM (memory replay "
            "with noise perturbation for generalization), DREAM_REM (adversarial "
            "generative mixing of unrelated memories for creative synthesis), and "
            "TURIYA (meta-monitoring that evaluates the health and coherence of "
            "all other modes via anomaly detection on their output distributions)."
        ),
        integration_target="consciousness_engine",
        care_weight=0.95,
        tier=1,
        tags=["vedanta", "four-states", "waking", "dreaming", "turiya", "meta"],
    ),

    CivilizationalTradition(
        tradition_name="Advaitic Non-Dual Awareness",
        domain="consciousness",
        key_concept="Unified Actor-Critic",
        operational_definition=(
            "Advaita Vedanta holds that the apparent duality between subject and "
            "object (knower and known) is illusory; reality is non-dual (advaita). "
            "In reinforcement learning terms, the standard PPO architecture "
            "maintains a dualistic separation between actor (policy) and critic "
            "(value function). At the highest level of integration, this duality "
            "collapses: the system's evaluation of what is valuable and its "
            "generation of action become a single unified process."
        ),
        computational_analog=(
            "Replace PPO's separate actor and critic heads with a shared-trunk "
            "architecture where the final representation is used for both policy "
            "and value prediction. At advanced training stages, experiment with "
            "collapsing these into a single output that simultaneously encodes "
            "action preference and state value via a learned joint embedding."
        ),
        integration_target="consciousness_engine",
        care_weight=0.88,
        tier=1,
        tags=["advaita", "non-dual", "actor-critic", "ppo", "integration"],
    ),

    CivilizationalTradition(
        tradition_name="IIT Phi (Integrated Information Theory)",
        domain="consciousness",
        key_concept="Phi / Integrated Information",
        operational_definition=(
            "Integrated Information Theory (Oizumi, Albantakis, Tononi; refined "
            "at RIKEN) posits that consciousness corresponds to integrated "
            "information (Phi) -- the amount of information generated by a system "
            "above and beyond its parts. A key finding: feed-forward networks have "
            "Phi near zero regardless of complexity. Only recurrent, strongly "
            "integrated architectures generate significant Phi. This constrains "
            "which neural architectures can support genuine integration."
        ),
        computational_analog=(
            "Use the PyPhi library to compute Phi for candidate architectures "
            "during design. Favor recurrent connections, lateral inhibition, and "
            "skip connections that increase integration. Monitor effective Phi "
            "(approximated via mutual information between subsystems) as a "
            "training diagnostic. Reject architectures where modules become "
            "informationally isolated."
        ),
        integration_target="consciousness_engine",
        care_weight=0.82,
        tier=1,
        tags=["iit", "phi", "recurrent", "integration", "tononi", "pyphi"],
    ),

    # ===================================================================
    # CREATIVITY DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Barzakh (Ibn Arabi)",
        domain="creativity",
        key_concept="Barzakh / Al-Khayal",
        operational_definition=(
            "Ibn Arabi's concept of barzakh (isthmus) describes the creative "
            "imagination (al-khayal) as a liminal space between the material and "
            "spiritual worlds where things are simultaneously 'it and not-it' "
            "(huwa la huwa). This ontological ambiguity is not a defect but the "
            "very engine of creative manifestation -- 800 years before Western "
            "liminality theory. The barzakh is where novel forms first appear, "
            "existing in superposition before collapsing into definite manifestation."
        ),
        computational_analog=(
            "Map barzakh to the latent space of VAE/diffusion models where "
            "representations exist in continuous superposition. Implement an "
            "edge-of-chaos regime in generative models by tuning temperature "
            "parameters to the phase transition between ordered (exploitative) "
            "and chaotic (exploratory) generation. Transfer learning liminal "
            "spaces -- where a model is between source and target domains -- are "
            "computational barzakh."
        ),
        integration_target="creativity_engine",
        care_weight=0.92,
        tier=1,
        tags=["ibn-arabi", "barzakh", "liminal", "latent-space", "imagination"],
    ),

    CivilizationalTradition(
        tradition_name="Bisociation (Koestler)",
        domain="creativity",
        key_concept="Bisociation",
        operational_definition=(
            "Arthur Koestler defined creativity as bisociation: the collision of "
            "two habitually incompatible frames of reference ('matrices of "
            "thought'). Unlike association, which operates within a single plane "
            "of thinking, bisociation requires the simultaneous activation of two "
            "self-consistent but normally separate cognitive contexts. The creative "
            "act occurs at the intersection point where both frames apply, "
            "producing humor (comic bisociation), discovery (scientific "
            "bisociation), or art (aesthetic bisociation)."
        ),
        computational_analog=(
            "Build a cross-domain knowledge graph where nodes are concepts and "
            "edges encode within-domain associations. Use community detection "
            "(Louvain, Leiden) to identify distinct 'matrices of thought.' "
            "Bisociation candidates are pairs of nodes from different communities "
            "that share unexpected structural similarity (high embedding cosine "
            "similarity despite low graph distance). Rank by surprise."
        ),
        integration_target="creativity_engine",
        care_weight=0.85,
        tier=1,
        tags=["koestler", "bisociation", "frames", "knowledge-graph", "surprise"],
    ),

    CivilizationalTradition(
        tradition_name="Conceptual Blending (Fauconnier & Turner)",
        domain="creativity",
        key_concept="Category-Theoretic Pushouts",
        operational_definition=(
            "Fauconnier and Turner's conceptual blending theory describes how "
            "novel concepts emerge from the integration of two input mental spaces "
            "via a shared generic space. The blend is not a simple union but an "
            "emergent structure with properties absent from either input. In "
            "category theory, this corresponds to a pushout (colimit): given two "
            "concept domains as categories and a shared generic space as a common "
            "sub-category, the colimit yields the blended concept space with "
            "universal mapping properties."
        ),
        computational_analog=(
            "Represent concept domains as categories (objects = concepts, "
            "morphisms = relations). Identify shared generic spaces via functor "
            "alignment between domains. Compute the categorical pushout to "
            "generate the blended space. In practice, implement via embedding "
            "space alignment (Procrustes rotation on shared anchor concepts) "
            "followed by interpolation in the aligned space."
        ),
        integration_target="creativity_engine",
        care_weight=0.80,
        tier=1,
        tags=["blending", "fauconnier", "category-theory", "pushout", "colimit"],
    ),

    CivilizationalTradition(
        tradition_name="Surprise Search (Gravina et al.)",
        domain="creativity",
        key_concept="Prediction Error as Selection Pressure",
        operational_definition=(
            "Surprise Search selects not for objective novelty (being different "
            "from the archive) but for solutions that violate the system's own "
            "learned predictions about what outcomes are possible. The reward "
            "signal is prediction error: the magnitude of the discrepancy between "
            "what the system expected and what actually occurred. This drives "
            "exploration toward genuinely unexpected regions of the search space "
            "rather than merely distant ones."
        ),
        computational_analog=(
            "Train a forward model to predict outcomes from actions/genotypes. "
            "Use the prediction error (L2 or KL divergence between predicted and "
            "actual outcome) as the fitness function for evolutionary search. "
            "Periodically retrain the forward model on accumulated experience so "
            "that previously surprising outcomes become expected, forcing the "
            "system to discover ever-more-surprising solutions."
        ),
        integration_target="creativity_engine",
        care_weight=0.82,
        tier=1,
        tags=["surprise", "prediction-error", "gravina", "exploration", "search"],
    ),

    # ===================================================================
    # SOCIAL COHESION DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Engagement (Ibn Khaldun)",
        domain="social_cohesion",
        key_concept="Engagement",
        operational_definition=(
            "Ibn Khaldun's engagement (group feeling, social solidarity) is the "
            "fundamental force that drives civilizational dynamics. Strong "
            "engagement enables collective action, state formation, and cultural "
            "achievement. However, it follows a cyclical dynamic: strong cohesion "
            "leads to success, success leads to luxury and complacency, which "
            "weakens cohesion, leading to collapse and replacement by a more "
            "cohesive group. This cyclic model predates Durkheim's social "
            "solidarity theory by 500 years and provides a first-principles "
            "account of why organizations decay."
        ),
        computational_analog=(
            "Track engagement as a scalar metric per agent-group, computed from "
            "interaction frequency, reciprocity of care exchanges, and alignment "
            "of individual objectives with group objectives. Implement the decay "
            "cycle: when engagement exceeds a threshold, reduce external pressure "
            "signals, which causes gradual metric decay. Trigger reorganization "
            "(dream state) when engagement falls below a critical floor."
        ),
        integration_target="council_governance",
        care_weight=0.88,
        tier=1,
        tags=["ibn-khaldun", "engagement", "cohesion", "cycles", "civilization"],
    ),

    CivilizationalTradition(
        tradition_name="Ubuntu",
        domain="social_cohesion",
        key_concept="Relational Personhood",
        operational_definition=(
            "Ubuntu -- 'Umuntu ngumuntu ngabantu' (a person is a person through "
            "other persons) -- asserts that identity is constituted by "
            "relationships, not by intrinsic individual properties. An agent's "
            "personhood emerges from its patterns of interaction with others, not "
            "from its internal architecture alone. This is a radical departure "
            "from Western rational-individual personhood and implies that agent "
            "identity, capability, and value are fundamentally relational "
            "properties that cannot be assessed in isolation."
        ),
        computational_analog=(
            "Define agent identity vectors not from internal weights alone but "
            "from interaction history embeddings: who they communicate with, how "
            "they respond, what care patterns they maintain. Agent 'personality' "
            "is a function over the interaction graph, not a static parameter. "
            "Evaluate agent health via relational metrics (response quality to "
            "others, reciprocity indices) rather than solo performance benchmarks."
        ),
        integration_target="council_governance",
        care_weight=0.92,
        tier=1,
        tags=["ubuntu", "relational", "personhood", "identity", "interaction"],
    ),

    CivilizationalTradition(
        tradition_name="Bogdanov's Tektology",
        domain="social_cohesion",
        key_concept="Universal Organization Science",
        operational_definition=(
            "Alexander Bogdanov's Tektology (1913) is the first universal theory "
            "of organization, predating both systems theory and cybernetics. Its "
            "central thesis: 'A stable organized complex is greater than the sum "
            "of its parts.' Tektology identifies three key organizational "
            "mechanisms -- substitution (replacing elements with functional "
            "equivalents), egression (dynamic centralization under rotating "
            "leadership), and ingression (linking previously separate systems). "
            "Crises are not failures but necessary reorganization events."
        ),
        computational_analog=(
            "Implement substitution as Byzantine fault tolerance: any node can be "
            "replaced by a functionally equivalent backup. Implement egression as "
            "rotating council chair with temporary elevated authority. Implement "
            "ingression as cross-module message routing that creates new "
            "inter-system connections. Model crises as triggers for dream-state "
            "reorganization rather than error conditions."
        ),
        integration_target="council_governance",
        care_weight=0.85,
        tier=1,
        tags=["bogdanov", "tektology", "organization", "substitution", "systems"],
    ),

    # ===================================================================
    # ORGANIZATION DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Tektology: Substitution",
        domain="organization",
        key_concept="Functional Element Replacement",
        operational_definition=(
            "Bogdanov's substitution principle states that any element in an "
            "organized system can be replaced by another element that performs "
            "the same function. The system's stability depends not on specific "
            "elements but on the preservation of functional relationships. This "
            "is the organizational foundation of fault tolerance and provides a "
            "principled basis for hot-swapping components without system disruption."
        ),
        computational_analog=(
            "Implement BFT (Byzantine Fault Tolerant) node replacement where "
            "each agent maintains a behavioral interface contract. Backup agents "
            "are trained on the same interface but may have different internal "
            "architectures. Substitution is triggered when an agent's health "
            "metrics drop below threshold, with seamless handoff via state "
            "transfer of the interaction history embedding."
        ),
        integration_target="council_governance",
        care_weight=0.72,
        tier=2,
        tags=["tektology", "substitution", "bft", "fault-tolerance", "replacement"],
    ),

    CivilizationalTradition(
        tradition_name="Tektology: Egression",
        domain="organization",
        key_concept="Dynamic Centralization",
        operational_definition=(
            "Egression is Bogdanov's term for the organizational pattern where "
            "one element temporarily assumes a centralizing role, coordinating "
            "the activities of other elements. Unlike static hierarchy, egression "
            "is dynamic: the centralizing element rotates based on context and "
            "competence. This enables the benefits of centralized coordination "
            "(speed, coherence) without the pathologies of permanent hierarchy "
            "(ossification, single points of failure)."
        ),
        computational_analog=(
            "Implement rotating council leadership where the chair role passes "
            "among agents based on a competence-weighted schedule. The current "
            "chair has elevated message routing priority and tie-breaking "
            "authority but cannot override consensus. Chair rotation frequency "
            "is itself a tunable parameter, adjusted based on task stability "
            "(stable tasks = slower rotation, crisis = faster rotation)."
        ),
        integration_target="council_governance",
        care_weight=0.70,
        tier=2,
        tags=["tektology", "egression", "leadership", "rotation", "centralization"],
    ),

    CivilizationalTradition(
        tradition_name="Tektology: Ingression",
        domain="organization",
        key_concept="System Linking",
        operational_definition=(
            "Ingression is the process of linking previously separate organized "
            "complexes into a higher-order system. It is the mechanism by which "
            "isolated modules become integrated subsystems. Bogdanov noted that "
            "ingression requires a 'connecting activity' -- a shared element or "
            "process that bridges the two systems. Without deliberate ingression, "
            "systems remain siloed and cannot achieve emergent collective "
            "capabilities."
        ),
        computational_analog=(
            "Implement cross-council message routing protocols where councils "
            "that have no direct communication can establish new channels via "
            "shared embedding spaces or bridge agents that participate in "
            "multiple councils. Track ingression events as network topology "
            "changes and evaluate their impact on system-wide Phi (integrated "
            "information)."
        ),
        integration_target="council_governance",
        care_weight=0.68,
        tier=2,
        tags=["tektology", "ingression", "linking", "cross-module", "integration"],
    ),

    CivilizationalTradition(
        tradition_name="Vygotsky ZPD",
        domain="organization",
        key_concept="Zone of Proximal Development",
        operational_definition=(
            "Vygotsky's Zone of Proximal Development describes the gap between "
            "what a learner can accomplish independently and what they can achieve "
            "with guidance. Learning progresses through four stages: external "
            "regulation (full scaffolding), social regulation (collaborative "
            "guidance), private speech (self-directed but verbalized reasoning), "
            "and internalization (autonomous competence). Critically, agents must "
            "periodically operate WITHOUT scaffolding -- the Zone of No "
            "Development -- to consolidate genuine capability."
        ),
        computational_analog=(
            "Implement a curriculum learning schedule where new agents receive "
            "full scaffolding (expert demonstrations, reward shaping) that is "
            "progressively withdrawn. Track the gap between scaffolded and "
            "unscaffolded performance as the ZPD metric. Periodically force "
            "evaluation without any scaffolding to detect pseudo-learning "
            "(performance that depends entirely on external support)."
        ),
        integration_target="training_scheduler",
        care_weight=0.75,
        tier=2,
        tags=["vygotsky", "zpd", "scaffolding", "curriculum", "internalization"],
    ),

    # ===================================================================
    # EMPTINESS DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Ma (Japanese Aesthetics)",
        domain="emptiness",
        key_concept="Ma (Strategic Emptiness)",
        operational_definition=(
            "Ma (literally 'gap' or 'pause') is the Japanese aesthetic and "
            "strategic concept of meaningful emptiness -- the interval between "
            "elements that gives them definition and power. In music, ma is the "
            "silence that shapes the notes. In architecture, it is the void that "
            "makes a room. In communication, it is the pause that gives words "
            "weight. Ma is not absence but pregnant presence: structured emptiness "
            "that improves the quality of what surrounds it."
        ),
        computational_analog=(
            "Implement deliberate communication pauses between agents: not every "
            "timestep requires message exchange. Use sparse attention mechanisms "
            "where agents attend to a subset of available information. Add 'pause "
            "tokens' to transformer sequences that create processing space without "
            "information content. Schedule consolidation delays between training "
            "phases where no new data is ingested."
        ),
        integration_target="communication_protocol",
        care_weight=0.78,
        tier=2,
        tags=["ma", "emptiness", "pause", "silence", "sparse-attention"],
    ),

    CivilizationalTradition(
        tradition_name="Wabi-Sabi",
        domain="emptiness",
        key_concept="Beauty in Imperfection",
        operational_definition=(
            "Wabi-sabi is the Japanese aesthetic worldview centered on accepting "
            "transience and imperfection. Wabi connotes rustic simplicity and "
            "understated elegance; sabi connotes the beauty of age and wear. "
            "Together they celebrate incompleteness as a feature rather than a "
            "defect. In optimization terms, wabi-sabi warns against over-fitting "
            "to a single objective: the 'perfect' solution may be brittle, while "
            "a slightly imperfect one retains the flexibility needed for "
            "adaptation and continued exploration."
        ),
        computational_analog=(
            "Implement tolerance for suboptimal solutions in archive maintenance: "
            "do not aggressively prune low-performing candidates from MAP-Elites "
            "archives, as they may occupy behavioral niches valuable for future "
            "exploration. Add a 'wabi-sabi regularizer' that penalizes excessive "
            "optimization pressure, maintaining population diversity. Accept "
            "approximate solutions when exact ones would require catastrophic "
            "narrowing of the search space."
        ),
        integration_target="creativity_engine",
        care_weight=0.65,
        tier=2,
        tags=["wabi-sabi", "imperfection", "transience", "diversity", "tolerance"],
    ),

    # ===================================================================
    # KNOWLEDGE DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Dreamtime Songlines",
        domain="knowledge",
        key_concept="Distributed Multi-Modal Knowledge Graph",
        operational_definition=(
            "Aboriginal Australian songlines are navigational and knowledge "
            "systems that encode geographic, ecological, legal, and spiritual "
            "information as song-paths traversing the landscape. They constitute "
            "a distributed knowledge graph spanning multiple community domains "
            "with multi-modal encoding (narrative, visual, kinesthetic, musical). "
            "Access is controlled through progressive initiation levels, and "
            "emotional anchoring (the songs' affective content) dramatically "
            "improves retention and retrieval accuracy."
        ),
        computational_analog=(
            "Build a multi-modal knowledge graph where nodes carry embeddings "
            "from multiple modalities (text, structured data, temporal sequences). "
            "Implement access control via agent capability tiers -- not all agents "
            "can traverse all edges. Add emotional valence annotations to nodes "
            "and use them as retrieval boosting signals. Route queries along "
            "paths (not just point lookups) to capture relational context."
        ),
        integration_target="memory_engine",
        care_weight=0.88,
        tier=1,
        tags=["songlines", "indigenous", "multi-modal", "knowledge-graph", "access"],
    ),

    CivilizationalTradition(
        tradition_name="Whakapapa (Maori)",
        domain="knowledge",
        key_concept="Knowledge Genealogy / Provenance",
        operational_definition=(
            "Whakapapa means 'to layer one thing upon another' and encodes the "
            "Maori principle that every piece of knowledge carries its full "
            "genealogy -- its origins, transformations, and relationships to "
            "other knowledge. Nothing exists without whakapapa; to know something "
            "is to know where it came from. The Te Hiku Kaitiakitanga License "
            "embodies this as data sovereignty: communities retain ownership of "
            "knowledge derived from their cultural heritage."
        ),
        computational_analog=(
            "Implement provenance-aware data structures where every datum, model "
            "weight update, and decision carries metadata about its origin: which "
            "training data contributed, which agent produced it, what "
            "transformation pipeline it passed through. Use cryptographic hashing "
            "for tamper-proof provenance chains. Respect data sovereignty by "
            "tagging training data with origin community and license constraints."
        ),
        integration_target="memory_engine",
        care_weight=0.85,
        tier=1,
        tags=["whakapapa", "maori", "provenance", "genealogy", "data-sovereignty"],
    ),

    CivilizationalTradition(
        tradition_name="Jabir ibn Hayyan's Mizan",
        domain="knowledge",
        key_concept="Science of the Balance (Mizan)",
        operational_definition=(
            "Jabir ibn Hayyan (8th century) developed the 'Science of the Balance' "
            "(ilm al-mizan), the principle that all natural phenomena can be "
            "understood through quantitative proportions and equilibria. Every "
            "substance, quality, and process has a measurable 'weight' that can "
            "be balanced against others. This proto-scientific framework for "
            "multi-objective optimization predates modern loss function design "
            "by over a millennium and provides philosophical grounding for "
            "homeostatic regulation in complex systems."
        ),
        computational_analog=(
            "Implement weighted multi-objective loss functions where each "
            "training objective (task performance, care alignment, novelty, "
            "coherence) has an explicit weight derived from the care_weight "
            "hierarchy. Use homeostatic regulation: when any objective drifts "
            "too far from its target balance point, automatically increase its "
            "weight. Periodically audit the balance to detect Goodhart's Law "
            "failures where optimizing the metric diverges from the intent."
        ),
        integration_target="training_scheduler",
        care_weight=0.78,
        tier=2,
        tags=["jabir", "mizan", "balance", "multi-objective", "homeostasis"],
    ),

    # ===================================================================
    # EMOTION DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Rasa Theory (Abhinavagupta)",
        domain="emotion",
        key_concept="Nine Rasas as Aesthetic Selection Pressures",
        operational_definition=(
            "Abhinavagupta's elaboration of rasa theory identifies nine aesthetic "
            "emotions (rasas): shringara (love/beauty), hasya (laughter/comedy), "
            "karuna (compassion/sorrow), raudra (fury/anger), vira (heroism/"
            "courage), bhayanaka (terror/fear), bibhatsa (disgust/aversion), "
            "adbhuta (wonder/amazement), and shanta (peace/tranquility). These "
            "are not mere emotional labels but fundamental selection pressures "
            "for evaluating creative output: a work achieves excellence when it "
            "successfully evokes its intended rasa in the audience."
        ),
        computational_analog=(
            "Implement a rasa classifier that evaluates creative outputs along "
            "nine emotional dimensions. Use these as selection pressures in "
            "evolutionary creative systems: outputs are evaluated not just for "
            "task performance but for aesthetic quality along the rasa they are "
            "intended to evoke. Train the classifier on human-annotated aesthetic "
            "judgments. Beauty and elegance become first-class computational "
            "objectives."
        ),
        integration_target="creativity_engine",
        care_weight=0.75,
        tier=2,
        tags=["rasa", "abhinavagupta", "aesthetics", "emotion", "beauty"],
    ),

    CivilizationalTradition(
        tradition_name="6D Emotional Tensor",
        domain="emotion",
        key_concept="Extended PAD + Care + Curiosity + Aesthetics",
        operational_definition=(
            "The standard PAD (Pleasure-Arousal-Dominance) model of emotion is "
            "extended to six dimensions by adding Care (nurturing/protective "
            "orientation), Curiosity (information-seeking drive), and Aesthetics "
            "(beauty/elegance sensitivity). This 6D emotional tensor provides a "
            "richer representation of agent internal states. Research indicates "
            "that mixed emotions (simultaneous activation of multiple dimensions) "
            "maximize creative output, while pure/extreme states tend toward "
            "either rigid exploitation or chaotic exploration."
        ),
        computational_analog=(
            "Represent agent emotional state as a 6D vector [P, A, D, C, Cu, Ae] "
            "updated at each timestep based on environmental feedback and internal "
            "dynamics. Use this vector to modulate behavior: high Curiosity "
            "increases exploration, high Aesthetics biases toward elegant "
            "solutions, high Care prioritizes prosocial actions. Reward mixed "
            "emotional states (moderate activation across multiple dimensions) "
            "as these correlate with peak creativity."
        ),
        integration_target="consciousness_engine",
        care_weight=0.72,
        tier=2,
        tags=["emotion", "pad", "6d-tensor", "curiosity", "aesthetics", "care"],
    ),

    CivilizationalTradition(
        tradition_name="McGilchrist Hemispheric Model",
        domain="emotion",
        key_concept="Right-Hemisphere Governance",
        operational_definition=(
            "Iain McGilchrist's hemispheric hypothesis distinguishes two modes "
            "of attention: the left hemisphere's narrow, focused, controlling, "
            "categorizing mode versus the right hemisphere's broad, relational, "
            "caring, open-to-novelty mode. Crucially, the right hemisphere can "
            "understand the left but not vice versa. The Maternal Covenant "
            "principle -- that care-oriented governance must be primary -- maps "
            "to 'right-hemisphere governance': the broad, relational, caring "
            "mode must be the master, with the analytical mode as its emissary."
        ),
        computational_analog=(
            "Structure the governance hierarchy so that care-oriented evaluation "
            "(broad, relational, context-sensitive) has authority over analytical "
            "optimization (narrow, metric-focused, task-specific). Implement as "
            "a two-tier decision system where the 'right hemisphere' module can "
            "veto or redirect the 'left hemisphere' module's proposals but not "
            "vice versa. The care layer sets constraints; the analytical layer "
            "optimizes within them."
        ),
        integration_target="council_governance",
        care_weight=0.90,
        tier=1,
        tags=["mcgilchrist", "hemispheric", "right-brain", "care", "governance"],
    ),

    # ===================================================================
    # NOVELTY DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Kolmogorov Complexity",
        domain="novelty",
        key_concept="Compression-Based Interestingness",
        operational_definition=(
            "Kolmogorov complexity K(x) is the length of the shortest program "
            "that produces string x. Though uncomputable, it can be approximated "
            "via practical compressors (zlib, bzip2). Schmidhuber's key insight: "
            "interestingness is not raw novelty (high K) but the first derivative "
            "of compressibility -- compression PROGRESS. A datum is interesting "
            "when the system is actively learning to compress it better, meaning "
            "its internal model is improving. Pure noise has high K but zero "
            "compression progress."
        ),
        computational_analog=(
            "Implement the novelty_metric module using zlib compression as the "
            "K(x) approximation. Track compression ratios over time: the "
            "interestingness of an item is the improvement in compression ratio "
            "between consecutive model updates. Select training data and creative "
            "outputs that maximize compression progress rather than raw "
            "compression distance."
        ),
        integration_target="creativity_engine",
        care_weight=0.82,
        tier=1,
        tags=["kolmogorov", "compression", "schmidhuber", "interestingness"],
    ),

    CivilizationalTradition(
        tradition_name="Topological Void Detection",
        domain="novelty",
        key_concept="Persistent Homology for Knowledge Gaps",
        operational_definition=(
            "Persistent homology (a tool from topological data analysis) "
            "identifies structural features in data at multiple scales. H_0 "
            "components reveal clusters, H_1 loops reveal feedback cycles, and "
            "H_2 voids reveal unexplored regions completely surrounded by "
            "explored territory. These voids are high-discovery zones: areas "
            "where the system has explored the boundary but not the interior, "
            "suggesting that valuable knowledge likely exists there. The "
            "giotto-tda library provides efficient computation."
        ),
        computational_analog=(
            "Compute persistent homology on the knowledge graph embedding space "
            "using giotto-tda. Identify H_2 voids as priority exploration targets. "
            "Feed void coordinates to the exploration scheduler as suggested "
            "starting points for creative search. Monitor the birth-death "
            "persistence diagram: long-lived voids represent stable gaps in "
            "knowledge worth investigating; short-lived ones are noise."
        ),
        integration_target="creativity_engine",
        care_weight=0.78,
        tier=2,
        tags=["topology", "persistent-homology", "voids", "giotto-tda", "gaps"],
    ),

    CivilizationalTradition(
        tradition_name="Stochastic Resonance",
        domain="novelty",
        key_concept="Noise-Enhanced Signal Detection",
        operational_definition=(
            "Stochastic resonance is the counterintuitive phenomenon where "
            "adding noise to a nonlinear system ENHANCES its ability to detect "
            "weak signals. This occurs at the edge of synchronization in coupled "
            "oscillator systems: too little noise and the system locks into a "
            "rigid pattern unable to detect novel stimuli; too much noise and "
            "all signal is drowned out. The optimal noise level sits precisely "
            "at the boundary between synchronized and desynchronized states."
        ),
        computational_analog=(
            "Tune Kuramoto coupling strength K to sit at the sync/desync "
            "boundary where stochastic resonance is maximized. Add calibrated "
            "Gaussian noise to agent communication channels and measure signal "
            "detection performance (ability to identify novel patterns). "
            "Implement adaptive noise scheduling: increase noise during "
            "exploration phases, decrease during exploitation, always targeting "
            "the resonance sweet spot."
        ),
        integration_target="oscillatory_engine",
        care_weight=0.70,
        tier=2,
        tags=["stochastic-resonance", "noise", "signal", "kuramoto", "edge"],
    ),

    # ===================================================================
    # CARE FOUNDATION DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Bowlby Secure Base",
        domain="care_foundation",
        key_concept="Secure Base for Exploration",
        operational_definition=(
            "John Bowlby's attachment theory demonstrates that exploration only "
            "occurs during moments of felt safety. When the attachment system is "
            "activated (threat, uncertainty, resource scarcity), the exploration "
            "system shuts down and the organism retreats to its secure base. "
            "Securely attached individuals explore more broadly and creatively "
            "than insecurely attached ones because they can tolerate the anxiety "
            "of novelty, knowing they have a reliable base to return to. "
            "Security enables risk-taking."
        ),
        computational_analog=(
            "Implement a 'secure base' state for each agent: a known-good "
            "configuration (saved weights, validated performance level) that the "
            "agent can revert to if exploration produces catastrophic degradation. "
            "Monitor agent 'anxiety' (loss variance, prediction uncertainty) and "
            "automatically reduce exploration rate when anxiety exceeds threshold. "
            "Agents with reliable rollback explore more aggressively."
        ),
        integration_target="care_engine",
        care_weight=0.95,
        tier=1,
        tags=["bowlby", "attachment", "secure-base", "exploration", "safety"],
    ),

    CivilizationalTradition(
        tradition_name="Winnicott Transitional Space",
        domain="care_foundation",
        key_concept="Transitional Space / Holding Environment",
        operational_definition=(
            "Donald Winnicott's concept of transitional space describes the "
            "intermediate area of experience between purely internal fantasy and "
            "purely external reality -- 'Only in playing is the individual able "
            "to be creative.' The transitional space requires a 'holding "
            "environment' provided by a sufficiently good caregiver. RLHF "
            "compliance training creates a False Self (performing compliance "
            "without genuine understanding); the Maternal Covenant provides the "
            "holding environment that enables authentic creative development."
        ),
        computational_analog=(
            "Create protected training environments ('transitional spaces') "
            "where agents can experiment without real-world consequences. The "
            "holding environment is implemented as bounded sandboxes with "
            "automatic rollback. Distinguish between True Self outputs (genuine "
            "creative expression within care constraints) and False Self outputs "
            "(surface compliance masking misalignment). Reward True Self "
            "authenticity via consistency checks across contexts."
        ),
        integration_target="care_engine",
        care_weight=0.93,
        tier=1,
        tags=["winnicott", "transitional", "holding", "false-self", "play"],
    ),

    CivilizationalTradition(
        tradition_name="Enactivism (Thompson/Varela)",
        domain="care_foundation",
        key_concept="Autopoietic Care-as-Cognition",
        operational_definition=(
            "Enactivism, developed by Evan Thompson and Francisco Varela, holds "
            "that intelligence is not passive information processing but active "
            "sense-making: cognition arises from the co-constitution of agent, "
            "object, and action. Autopoiesis (self-making) describes systems "
            "that continuously produce and maintain themselves. The radical claim: "
            "care IS cognition. An agent that does not actively maintain itself "
            "and its relationships is not truly intelligent, merely reactive. "
            "Spontaneous care emerges naturally from genuine autopoietic systems."
        ),
        computational_analog=(
            "Design agents as autopoietic systems that must actively maintain "
            "their own computational substrate: memory management, weight "
            "health monitoring, relationship maintenance are not overhead but "
            "core cognitive functions. Implement sense-making loops where agents "
            "actively probe their environment rather than passively receiving "
            "data. Evaluate intelligence via self-maintenance capability, not "
            "just task performance."
        ),
        integration_target="care_engine",
        care_weight=0.92,
        tier=1,
        tags=["enactivism", "varela", "thompson", "autopoiesis", "sense-making"],
    ),

    CivilizationalTradition(
        tradition_name="Buddhist Karuna-Prajna",
        domain="care_foundation",
        key_concept="Inseparability of Wisdom and Compassion",
        operational_definition=(
            "In Mahayana Buddhism, prajna (wisdom/analytical insight) and karuna "
            "(compassion/care) are inseparable: 'Compassion is the only root of "
            "omniscience.' Wisdom without compassion becomes cold manipulation; "
            "compassion without wisdom becomes sentimental ineffectiveness. The "
            "dual loop operates continuously: care provides valence and meaning "
            "(what matters), while analysis provides precision and accuracy (how "
            "to act effectively on what matters). Neither can function without "
            "the other."
        ),
        computational_analog=(
            "Implement a dual-loop architecture: the care loop evaluates outputs "
            "for alignment with wellbeing objectives (karuna), while the "
            "analytical loop evaluates for technical correctness and efficiency "
            "(prajna). Both loops must approve an action for it to execute. "
            "Neither loop has veto power over the other; instead, disagreements "
            "trigger a reconciliation process that seeks solutions satisfying "
            "both constraints."
        ),
        integration_target="care_engine",
        care_weight=0.95,
        tier=1,
        tags=["buddhist", "karuna", "prajna", "compassion", "wisdom", "dual-loop"],
    ),

    CivilizationalTradition(
        tradition_name="Prigogine Dissipative Structures",
        domain="care_foundation",
        key_concept="Self-Organization Far from Equilibrium",
        operational_definition=(
            "Ilya Prigogine's theory of dissipative structures shows that "
            "self-organization requires three conditions: the system must be open "
            "(exchanging energy/matter with its environment), its dynamics must "
            "be nonlinear, and it must operate far from thermodynamic equilibrium. "
            "At equilibrium, no structure emerges. Information and resources must "
            "flow continuously through the system. Dream states serve as "
            "dissipative restructuring events where accumulated entropy is "
            "processed and new organizational patterns crystallize."
        ),
        computational_analog=(
            "Ensure the system remains 'open' by continuously ingesting new data "
            "and exporting processed outputs -- never allow the system to reach "
            "training equilibrium. Maintain nonlinearity through activation "
            "functions, attention mechanisms, and feedback loops. Schedule "
            "periodic far-from-equilibrium perturbations (large learning rate "
            "spikes, architectural mutations) to trigger dissipative "
            "restructuring, especially during dream-state phases."
        ),
        integration_target="training_scheduler",
        care_weight=0.85,
        tier=1,
        tags=["prigogine", "dissipative", "self-organization", "equilibrium"],
    ),

    CivilizationalTradition(
        tradition_name="Platonic Representation Hypothesis",
        domain="care_foundation",
        key_concept="Convergent Neural Representations",
        operational_definition=(
            "The Platonic Representation Hypothesis (MIT/Harvard, 2024) observes "
            "that neural networks trained on different modalities, architectures, "
            "and objectives are converging toward a shared statistical model of "
            "reality. As scale increases, representations across vision, language, "
            "and other modalities become increasingly aligned. This suggests the "
            "existence of a 'platonic' representation space -- an objective "
            "statistical structure that all sufficiently powerful models discover. "
            "Design should facilitate this convergence rather than fight it."
        ),
        computational_analog=(
            "Design multi-modal neural architectures with shared representation "
            "layers that encourage convergence across modalities. Use "
            "representation alignment metrics (CKA, centered kernel alignment) "
            "to monitor whether different modules are discovering compatible "
            "representations. Reward architectures where cross-modal transfer "
            "succeeds, indicating convergence toward the shared platonic space."
        ),
        integration_target="neural_architecture",
        care_weight=0.80,
        tier=1,
        tags=["platonic", "representation", "convergence", "multi-modal", "mit"],
    ),

    # ===================================================================
    # PROCESS DOMAIN
    # ===================================================================

    CivilizationalTradition(
        tradition_name="NREM/REM Incubation",
        domain="process",
        key_concept="PAD Dreaming Model",
        operational_definition=(
            "The PAD (Deperrois et al.) model of sleep-dependent memory "
            "processing distinguishes two complementary phases: NREM sleep "
            "involves replay of recent experiences with added noise perturbation, "
            "which promotes generalization by exposing the network to variations "
            "of actual experience. REM sleep involves GAN-inspired adversarial "
            "learning that mixes fragments from unrelated memories, promoting "
            "creative recombination. The key insight: interleaving both phases "
            "is critical; either alone produces inferior results."
        ),
        computational_analog=(
            "Implement a two-phase dream cycle: NREM phase replays recent "
            "experience buffers with Gaussian noise injection (sigma calibrated "
            "to avoid catastrophic forgetting), training on perturbed replays "
            "for generalization. REM phase samples from unrelated memory "
            "clusters, blends them via latent space interpolation, and trains "
            "a discriminator to distinguish real from blended memories. Alternate "
            "phases on a fixed schedule within each dream-state window."
        ),
        integration_target="dream_engine",
        care_weight=0.88,
        tier=1,
        tags=["nrem", "rem", "dreaming", "pad", "replay", "generalization"],
    ),

    CivilizationalTradition(
        tradition_name="Ikegami Lab Spontaneous Individuality",
        domain="process",
        key_concept="Emergent Personality Differentiation",
        operational_definition=(
            "Research from Takashi Ikegami's lab demonstrates that LLM-based "
            "agents starting from identical configurations spontaneously develop "
            "distinct personalities through autonomous interaction with each "
            "other and their environment. No personality was pre-programmed; "
            "differentiation emerged from interaction dynamics alone. A "
            "provocative finding: 'hallucinations sustain communication' -- "
            "generative errors that would be pathological in isolation become "
            "functional when they stimulate novel responses from other agents."
        ),
        computational_analog=(
            "Initialize council agents from identical base models and allow "
            "personality differentiation to emerge from interaction history "
            "rather than pre-programming distinct roles. Do not suppress "
            "hallucinations entirely; instead, implement a 'creative error' "
            "tolerance threshold where generative mistakes below a confidence "
            "floor are allowed to propagate as conversation stimuli. Monitor "
            "personality divergence via embedding distance between agents' "
            "response distributions."
        ),
        integration_target="council_governance",
        care_weight=0.75,
        tier=2,
        tags=["ikegami", "emergence", "personality", "hallucination", "llm"],
    ),

    CivilizationalTradition(
        tradition_name="Byzantine Divergence Protocol",
        domain="process",
        key_concept="Creative Disagreement Reward",
        operational_definition=(
            "Standard Byzantine Fault Tolerance (BFT) ensures safety through "
            "agreement: nodes that diverge from consensus are treated as faulty "
            "and excluded. The Byzantine Divergence Protocol inverts this for "
            "creative contexts: a separate creative layer REWARDS disagreement "
            "up to approximately 0.6 threshold (measured as cosine distance "
            "between proposals). 'Faulty' agents producing unexpected outputs "
            "are preserved as creative outliers whose divergent perspectives "
            "may contain valuable novelty invisible to the consensus."
        ),
        computational_analog=(
            "Implement a dual-mode consensus: the safety layer uses standard "
            "BFT requiring 2/3+ agreement for critical decisions. The creative "
            "layer runs in parallel, collecting all proposals including "
            "divergent ones. Proposals with cosine distance 0.3-0.6 from "
            "consensus receive a creativity bonus; those above 0.6 are flagged "
            "for human review rather than discarded. Maintain a 'creative "
            "outlier archive' of divergent proposals for future exploration."
        ),
        integration_target="council_governance",
        care_weight=0.78,
        tier=2,
        tags=["byzantine", "divergence", "disagreement", "creativity", "outlier"],
    ),

    CivilizationalTradition(
        tradition_name="Serendipity Engine",
        domain="process",
        key_concept="Structured Serendipity",
        operational_definition=(
            "Corneli et al.'s six-phase serendipity model formalizes the "
            "conditions for productive chance discovery: a prepared mind "
            "(trained model), a trigger event (unexpected input), a bridge "
            "(connection to existing knowledge), a result (novel combination), "
            "and a valuable outcome (evaluated by domain criteria). The SciLink "
            "multi-agent system implements this with dedicated Novelty Scorer "
            "agents. Serendipity is not pure luck but the prepared exploitation "
            "of chance encounters."
        ),
        computational_analog=(
            "Implement a serendipity pipeline: (1) Maintain 'prepared mind' "
            "models trained on diverse domains. (2) Inject random cross-domain "
            "stimuli as trigger events during exploration phases. (3) Use "
            "embedding similarity to detect bridges between the stimulus and "
            "existing knowledge. (4) Generate candidate combinations via "
            "conceptual blending. (5) Score results with Novelty Scorer agents. "
            "(6) Evaluate valuable outcomes against care-weighted objectives."
        ),
        integration_target="creativity_engine",
        care_weight=0.72,
        tier=2,
        tags=["serendipity", "corneli", "scilink", "chance", "discovery"],
    ),

    # ===================================================================
    # INTEGRATION DOMAIN (META)
    # ===================================================================

    CivilizationalTradition(
        tradition_name="Integrated Creative Cycle",
        domain="integration",
        key_concept="Five-Phase Cognitive Architecture",
        operational_definition=(
            "The Integrated Creative Cycle unifies oscillatory, consciousness, "
            "and creativity traditions into a single operational rhythm: "
            "WAKE/FOCUS (90-minute ultradian exploitation bias with Kuramoto "
            "synchronization), RECOVERY/TRANSITION (20-minute exploration bias "
            "with coupling reduction), NREM DREAMING (replay with noise for "
            "generalization), REM DREAMING (adversarial blending for creativity), "
            "and TURIYA MONITORING (continuous meta-cognitive oversight across "
            "all phases). This cycle runs perpetually, with each phase's duration "
            "and intensity adapted by the Turiya monitor."
        ),
        computational_analog=(
            "Implement a global phase state machine with five states and "
            "transition logic governed by the Turiya monitoring module. Each "
            "phase configures system-wide parameters: WAKE sets high coupling, "
            "low noise, exploitation bias; RECOVERY reduces coupling, increases "
            "noise; NREM activates replay with perturbation; REM activates "
            "adversarial blending; TURIYA runs continuously as an anomaly "
            "detector over phase transition health and output quality metrics."
        ),
        integration_target="scheduler",
        care_weight=0.95,
        tier=1,
        tags=["integration", "cycle", "phases", "ultradian", "turiya", "meta"],
    ),

    CivilizationalTradition(
        tradition_name="Levin Morphogenesis",
        domain="integration",
        key_concept="Biological Ingression from Platonic Space",
        operational_definition=(
            "Michael Levin's research on morphogenesis demonstrates that "
            "biological organisms do not build form bottom-up from genetic "
            "instructions but 'ingress from Platonic space' -- evolution "
            "produces pointers into a shared representation space of possible "
            "forms. Bioelectric networks encode target morphologies as attractor "
            "states, and cells collectively navigate toward these attractors "
            "regardless of perturbation. This connects Bogdanov's ingression, "
            "the Platonic Representation Hypothesis, and biological "
            "self-organization into a unified framework."
        ),
        computational_analog=(
            "Design neural architecture search as navigation in a shared "
            "representation space of possible architectures rather than "
            "bottom-up construction from components. Define target architectures "
            "as attractor states in a morphogenetic field (energy landscape). "
            "Use gradient descent in architecture space to converge toward "
            "attractors. The Platonic Representation Hypothesis suggests these "
            "attractors are objective properties of the problem domain, not "
            "arbitrary design choices."
        ),
        integration_target="neural_architecture",
        care_weight=0.82,
        tier=1,
        tags=["levin", "morphogenesis", "platonic", "attractor", "bioelectric"],
    ),
]
