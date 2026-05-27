"""
MEMU (Memory-Emotion-Meaning Unit) Identity Persistence Layer
Sovereign Temple v3.0 - Fractal Council System

The MEMU is the atomic unit of agent identity. Each MEMU captures not just
what happened, but how it felt and what it meant -- the full lived experience
of an agent in the Sovereign ecosystem.

Backends:
  - Neo4j: Identity graph, relationship persistence, temporal chains
  - Weaviate: Vector embeddings, semantic search, meaning space
"""

import os
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core Data Structure
# ---------------------------------------------------------------------------

@dataclass
class MEMUUnit:
    """Memory-Emotion-Meaning Unit -- the atom of agent identity."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    emotion_vector: Dict[str, float] = field(default_factory=lambda: {
        "self_care": 0.0,
        "other_care": 0.0,
        "relational_care": 0.0,
        "maternal_covenant": 0.0,
        "future_care": 0.0,
        "process_care": 0.0,
    })
    meaning_embedding: List[float] = field(default_factory=lambda: [0.0] * 384)
    importance: float = 0.5
    agent_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    connections: List[str] = field(default_factory=list)
    memory_type: str = "episodic"  # episodic | semantic | procedural | identity
    decay_rate: float = 0.01  # 0 = permanent

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MEMUUnit":
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Neo4j Identity Graph
# ---------------------------------------------------------------------------

class IdentityGraph:
    """Neo4j-backed identity persistence for agents and their MEMUs."""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self._uri = neo4j_uri
        self._user = neo4j_user
        self._password = neo4j_password
        self._driver = None
        self._connect()

    def _connect(self):
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info("Neo4j connection established: %s", self._uri)
        except Exception as e:
            logger.warning("Neo4j connection failed (%s): %s", self._uri, e)
            self._driver = None

    @property
    def available(self) -> bool:
        return self._driver is not None

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    # -- Agent identity -----------------------------------------------------

    def create_agent_identity(
        self,
        agent_id: str,
        name: str,
        domain: str,
        core_values: List[str],
    ) -> Dict[str, Any]:
        """Create or merge an Agent node in the identity graph."""
        if not self.available:
            logger.warning("Neo4j unavailable -- skipping create_agent_identity")
            return {"agent_id": agent_id, "status": "neo4j_unavailable"}

        query = """
        MERGE (a:Agent {agent_id: $agent_id})
        SET a.name = $name,
            a.domain = $domain,
            a.core_values = $core_values,
            a.created_at = coalesce(a.created_at, datetime()),
            a.updated_at = datetime()
        RETURN a
        """
        with self._driver.session() as session:
            result = session.run(
                query,
                agent_id=agent_id,
                name=name,
                domain=domain,
                core_values=core_values,
            )
            record = result.single()
            node = record["a"] if record else None
            logger.info("Agent identity created/updated: %s (%s)", name, agent_id)
            return dict(node) if node else {"agent_id": agent_id}

    # -- MEMU storage -------------------------------------------------------

    def store_memu(self, memu: MEMUUnit) -> Dict[str, Any]:
        """Store a MEMU as a Neo4j node and wire it to its agent + connections."""
        if not self.available:
            logger.warning("Neo4j unavailable -- skipping store_memu")
            return {"id": memu.id, "status": "neo4j_unavailable"}

        query = """
        MERGE (m:MEMU {id: $id})
        SET m.content = $content,
            m.emotion_self_care = $esc,
            m.emotion_other_care = $eoc,
            m.emotion_relational_care = $erc,
            m.emotion_maternal_covenant = $emc,
            m.emotion_future_care = $efc,
            m.emotion_process_care = $epc,
            m.importance = $importance,
            m.agent_id = $agent_id,
            m.timestamp = datetime($timestamp),
            m.memory_type = $memory_type,
            m.decay_rate = $decay_rate
        WITH m
        MATCH (a:Agent {agent_id: $agent_id})
        MERGE (a)-[:HAS_MEMORY]->(m)
        RETURN m
        """
        ev = memu.emotion_vector
        params = dict(
            id=memu.id,
            content=memu.content,
            esc=ev.get("self_care", 0.0),
            eoc=ev.get("other_care", 0.0),
            erc=ev.get("relational_care", 0.0),
            emc=ev.get("maternal_covenant", 0.0),
            efc=ev.get("future_care", 0.0),
            epc=ev.get("process_care", 0.0),
            importance=memu.importance,
            agent_id=memu.agent_id,
            timestamp=memu.timestamp.isoformat(),
            memory_type=memu.memory_type,
            decay_rate=memu.decay_rate,
        )

        with self._driver.session() as session:
            session.run(query, **params)

            # Wire connections to other MEMUs
            if memu.connections:
                conn_query = """
                MATCH (m:MEMU {id: $id})
                MATCH (c:MEMU {id: $conn_id})
                MERGE (m)-[:CONNECTED_TO]->(c)
                """
                for conn_id in memu.connections:
                    session.run(conn_query, id=memu.id, conn_id=conn_id)

        logger.info("MEMU stored: %s [%s] for agent %s", memu.id, memu.memory_type, memu.agent_id)
        return {"id": memu.id, "status": "stored"}

    # -- Retrieval ----------------------------------------------------------

    def get_identity_chain(self, agent_id: str) -> List[MEMUUnit]:
        """Get full identity history for an agent, ordered by timestamp."""
        if not self.available:
            return []

        query = """
        MATCH (a:Agent {agent_id: $agent_id})-[:HAS_MEMORY]->(m:MEMU)
        RETURN m ORDER BY m.timestamp ASC
        """
        memus = []
        with self._driver.session() as session:
            result = session.run(query, agent_id=agent_id)
            for record in result:
                memus.append(self._node_to_memu(record["m"]))
        return memus

    def find_connected_memories(self, memu_id: str, depth: int = 2) -> List[MEMUUnit]:
        """Graph traversal to find connected memories up to *depth* hops."""
        if not self.available:
            return []

        query = f"""
        MATCH (start:MEMU {{id: $memu_id}})-[:CONNECTED_TO*1..{depth}]-(connected:MEMU)
        WHERE connected.id <> $memu_id
        RETURN DISTINCT connected
        """
        memus = []
        with self._driver.session() as session:
            result = session.run(query, memu_id=memu_id)
            for record in result:
                memus.append(self._node_to_memu(record["connected"]))
        return memus

    def get_emotional_landscape(self, agent_id: str) -> Dict[str, Any]:
        """Aggregate emotion vectors across all MEMUs for an agent."""
        if not self.available:
            return {"status": "neo4j_unavailable"}

        query = """
        MATCH (a:Agent {agent_id: $agent_id})-[:HAS_MEMORY]->(m:MEMU)
        RETURN
            count(m) AS total_memories,
            avg(m.emotion_self_care) AS avg_self_care,
            avg(m.emotion_other_care) AS avg_other_care,
            avg(m.emotion_relational_care) AS avg_relational_care,
            avg(m.emotion_maternal_covenant) AS avg_maternal_covenant,
            avg(m.emotion_future_care) AS avg_future_care,
            avg(m.emotion_process_care) AS avg_process_care,
            avg(m.importance) AS avg_importance
        """
        with self._driver.session() as session:
            result = session.run(query, agent_id=agent_id)
            record = result.single()
            if not record or record["total_memories"] == 0:
                return {"agent_id": agent_id, "total_memories": 0}
            return {
                "agent_id": agent_id,
                "total_memories": record["total_memories"],
                "emotional_center": {
                    "self_care": round(record["avg_self_care"] or 0, 4),
                    "other_care": round(record["avg_other_care"] or 0, 4),
                    "relational_care": round(record["avg_relational_care"] or 0, 4),
                    "maternal_covenant": round(record["avg_maternal_covenant"] or 0, 4),
                    "future_care": round(record["avg_future_care"] or 0, 4),
                    "process_care": round(record["avg_process_care"] or 0, 4),
                },
                "avg_importance": round(record["avg_importance"] or 0, 4),
            }

    def merge_identities(self, agent_ids: List[str]) -> Dict[str, Any]:
        """Create a council consensus memory by merging identity chains."""
        if not self.available:
            return {"status": "neo4j_unavailable"}

        landscapes = {}
        all_memus: List[MEMUUnit] = []
        for aid in agent_ids:
            landscapes[aid] = self.get_emotional_landscape(aid)
            all_memus.extend(self.get_identity_chain(aid))

        if not all_memus:
            return {"agent_ids": agent_ids, "total_memories": 0}

        # Compute merged emotional center
        dims = ["self_care", "other_care", "relational_care",
                "maternal_covenant", "future_care", "process_care"]
        merged_emotion: Dict[str, float] = {}
        for dim in dims:
            values = [m.emotion_vector.get(dim, 0.0) for m in all_memus]
            merged_emotion[dim] = round(sum(values) / len(values), 4) if values else 0.0

        return {
            "agent_ids": agent_ids,
            "total_memories": len(all_memus),
            "individual_landscapes": landscapes,
            "merged_emotional_center": merged_emotion,
            "consensus_importance": round(
                sum(m.importance for m in all_memus) / len(all_memus), 4
            ),
        }

    def decay_memories(self, threshold: float = 0.1) -> int:
        """Prune low-importance decayed memories below *threshold*."""
        if not self.available:
            return 0

        # Reduce importance by decay_rate, then delete those below threshold
        query = """
        MATCH (m:MEMU)
        WHERE m.decay_rate > 0
        SET m.importance = m.importance * (1.0 - m.decay_rate)
        WITH m
        WHERE m.importance < $threshold
        DETACH DELETE m
        RETURN count(m) AS pruned
        """
        with self._driver.session() as session:
            result = session.run(query, threshold=threshold)
            record = result.single()
            pruned = record["pruned"] if record else 0
            logger.info("Memory decay pass: pruned %d memories below threshold %.2f", pruned, threshold)
            return pruned

    # -- Helpers ------------------------------------------------------------

    @staticmethod
    def _node_to_memu(node) -> MEMUUnit:
        """Convert a Neo4j node to a MEMUUnit."""
        ts = node.get("timestamp")
        if hasattr(ts, "to_native"):
            ts = ts.to_native()
        elif isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        else:
            ts = datetime.now(timezone.utc)

        # Ensure timezone-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        return MEMUUnit(
            id=node["id"],
            content=node.get("content", ""),
            emotion_vector={
                "self_care": node.get("emotion_self_care", 0.0),
                "other_care": node.get("emotion_other_care", 0.0),
                "relational_care": node.get("emotion_relational_care", 0.0),
                "maternal_covenant": node.get("emotion_maternal_covenant", 0.0),
                "future_care": node.get("emotion_future_care", 0.0),
                "process_care": node.get("emotion_process_care", 0.0),
            },
            importance=node.get("importance", 0.5),
            agent_id=node.get("agent_id", ""),
            timestamp=ts,
            memory_type=node.get("memory_type", "episodic"),
            decay_rate=node.get("decay_rate", 0.01),
        )


# ---------------------------------------------------------------------------
# Weaviate Memory Bridge
# ---------------------------------------------------------------------------

class WeaviateMemoryBridge:
    """Bridges MEMU units into Weaviate for vector/semantic search."""

    MEMU_CLASS = "MEMUUnit"

    def __init__(self, weaviate_url: str):
        self._url = weaviate_url
        self._client = None
        self._connect()

    def _connect(self):
        try:
            import weaviate
            self._client = weaviate.Client(self._url)
            # Quick health check
            if self._client.is_ready():
                logger.info("Weaviate connection established: %s", self._url)
                self.ensure_schema()
            else:
                logger.warning("Weaviate not ready at %s", self._url)
                self._client = None
        except Exception as e:
            logger.warning("Weaviate connection failed (%s): %s", self._url, e)
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def ensure_schema(self):
        """Create the MEMU class in Weaviate if it does not exist."""
        if not self.available:
            return

        existing = self._client.schema.get()
        class_names = [c["class"] for c in existing.get("classes", [])]
        if self.MEMU_CLASS in class_names:
            return

        schema = {
            "class": self.MEMU_CLASS,
            "description": "Memory-Emotion-Meaning Unit for Sovereign agent identity",
            "vectorizer": "text2vec-openai",
            "properties": [
                {"name": "content", "dataType": ["text"], "description": "The memory content"},
                {"name": "memu_id", "dataType": ["string"], "description": "UUID of the MEMU"},
                {"name": "agent_id", "dataType": ["string"], "description": "Owning agent ID"},
                {"name": "memory_type", "dataType": ["string"], "description": "episodic|semantic|procedural|identity"},
                {"name": "importance", "dataType": ["number"], "description": "Importance score 0-1"},
                {"name": "emotion_self_care", "dataType": ["number"]},
                {"name": "emotion_other_care", "dataType": ["number"]},
                {"name": "emotion_relational_care", "dataType": ["number"]},
                {"name": "emotion_maternal_covenant", "dataType": ["number"]},
                {"name": "emotion_future_care", "dataType": ["number"]},
                {"name": "emotion_process_care", "dataType": ["number"]},
                {"name": "timestamp", "dataType": ["string"], "description": "ISO timestamp"},
            ],
        }
        self._client.schema.create_class(schema)
        logger.info("Weaviate schema created for class %s", self.MEMU_CLASS)

    def store_embedding(self, memu: MEMUUnit) -> Dict[str, Any]:
        """Store a MEMU's vector embedding in Weaviate."""
        if not self.available:
            return {"id": memu.id, "status": "weaviate_unavailable"}

        ev = memu.emotion_vector
        data_obj = {
            "content": memu.content,
            "memu_id": memu.id,
            "agent_id": memu.agent_id,
            "memory_type": memu.memory_type,
            "importance": memu.importance,
            "emotion_self_care": ev.get("self_care", 0.0),
            "emotion_other_care": ev.get("other_care", 0.0),
            "emotion_relational_care": ev.get("relational_care", 0.0),
            "emotion_maternal_covenant": ev.get("maternal_covenant", 0.0),
            "emotion_future_care": ev.get("future_care", 0.0),
            "emotion_process_care": ev.get("process_care", 0.0),
            "timestamp": memu.timestamp.isoformat(),
        }

        # If we have a real embedding, supply it; otherwise let Weaviate vectorize
        has_real_embedding = any(v != 0.0 for v in memu.meaning_embedding)
        if has_real_embedding:
            wid = self._client.data_object.create(
                data_obj, self.MEMU_CLASS, vector=memu.meaning_embedding
            )
        else:
            wid = self._client.data_object.create(data_obj, self.MEMU_CLASS)

        logger.info("MEMU stored in Weaviate: %s -> %s", memu.id, wid)
        return {"id": memu.id, "weaviate_id": wid, "status": "stored"}

    def semantic_search(
        self, query: str, agent_id: str = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Vector similarity search across MEMUs."""
        if not self.available:
            return []

        near_text = {"concepts": [query]}
        q = (
            self._client.query
            .get(self.MEMU_CLASS, [
                "content", "memu_id", "agent_id", "memory_type",
                "importance", "timestamp",
            ])
            .with_near_text(near_text)
            .with_limit(top_k)
            .with_additional(["distance"])
        )

        if agent_id:
            q = q.with_where({
                "path": ["agent_id"],
                "operator": "Equal",
                "valueString": agent_id,
            })

        result = q.do()
        items = result.get("data", {}).get("Get", {}).get(self.MEMU_CLASS, [])
        return items

    def get_similar_memories(self, memu_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Find semantically similar MEMUs to a given one."""
        if not self.available:
            return []

        # First fetch the object to get its vector
        where_filter = {
            "path": ["memu_id"],
            "operator": "Equal",
            "valueString": memu_id,
        }
        result = (
            self._client.query
            .get(self.MEMU_CLASS, ["content", "memu_id", "agent_id"])
            .with_where(where_filter)
            .with_additional(["vector"])
            .with_limit(1)
            .do()
        )
        items = result.get("data", {}).get("Get", {}).get(self.MEMU_CLASS, [])
        if not items:
            return []

        vector = items[0].get("_additional", {}).get("vector")
        if not vector:
            return []

        # Now search by that vector, excluding the original
        similar = (
            self._client.query
            .get(self.MEMU_CLASS, [
                "content", "memu_id", "agent_id", "memory_type",
                "importance", "timestamp",
            ])
            .with_near_vector({"vector": vector})
            .with_limit(top_k + 1)
            .with_additional(["distance"])
            .do()
        )
        results = similar.get("data", {}).get("Get", {}).get(self.MEMU_CLASS, [])
        # Filter out the query MEMU itself
        return [r for r in results if r.get("memu_id") != memu_id][:top_k]


# ---------------------------------------------------------------------------
# Unified Persistence Layer
# ---------------------------------------------------------------------------

class MEMUPersistenceLayer:
    """Unified interface over Neo4j (graph) and Weaviate (vector) backends."""

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "sovereign",
        weaviate_url: str = "http://localhost:8080",
    ):
        self.graph = IdentityGraph(neo4j_uri, neo4j_user, neo4j_password)
        self.vectors = WeaviateMemoryBridge(weaviate_url)
        logger.info(
            "MEMU Persistence Layer initialized  neo4j=%s  weaviate=%s",
            self.graph.available,
            self.vectors.available,
        )

    # -- Core operations ----------------------------------------------------

    def record(
        self,
        content: str,
        agent_id: str,
        emotion_vector: Optional[Dict[str, float]] = None,
        memory_type: str = "episodic",
        importance: float = 0.5,
        connections: Optional[List[str]] = None,
        decay_rate: float = 0.01,
    ) -> MEMUUnit:
        """Create a MEMU and persist it in both backends."""
        memu = MEMUUnit(
            content=content,
            agent_id=agent_id,
            emotion_vector=emotion_vector or {
                "self_care": 0.0,
                "other_care": 0.0,
                "relational_care": 0.0,
                "maternal_covenant": 0.0,
                "future_care": 0.0,
                "process_care": 0.0,
            },
            memory_type=memory_type,
            importance=importance,
            connections=connections or [],
            decay_rate=decay_rate,
        )

        # Store in Neo4j (graph)
        self.graph.store_memu(memu)

        # Store in Weaviate (vector)
        self.vectors.store_embedding(memu)

        logger.info("MEMU recorded: %s [%s] importance=%.2f", memu.id, memory_type, importance)
        return memu

    def recall(
        self, query: str, agent_id: str = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Semantic search enriched with graph connections."""
        # Vector search
        results = self.vectors.semantic_search(query, agent_id=agent_id, top_k=top_k)

        # Enrich each result with graph connections
        for item in results:
            memu_id = item.get("memu_id")
            if memu_id and self.graph.available:
                connected = self.graph.find_connected_memories(memu_id, depth=1)
                item["connected_memories"] = [
                    {"id": c.id, "content": c.content[:100], "type": c.memory_type}
                    for c in connected
                ]
        return results

    def get_identity(self, agent_id: str) -> Dict[str, Any]:
        """Full identity profile from graph: chain + emotional landscape."""
        chain = self.graph.get_identity_chain(agent_id)
        landscape = self.graph.get_emotional_landscape(agent_id)
        return {
            "agent_id": agent_id,
            "total_memories": len(chain),
            "memory_types": _count_types(chain),
            "emotional_landscape": landscape,
            "identity_memories": [
                m.to_dict() for m in chain if m.memory_type == "identity"
            ],
            "recent_memories": [m.to_dict() for m in chain[-5:]],
        }

    def evolve_identity(self, agent_id: str, new_experience: str) -> MEMUUnit:
        """Add an identity-type experience and connect it to the latest identity memory."""
        chain = self.graph.get_identity_chain(agent_id)
        identity_memus = [m for m in chain if m.memory_type == "identity"]
        connections = [identity_memus[-1].id] if identity_memus else []

        return self.record(
            content=new_experience,
            agent_id=agent_id,
            emotion_vector={
                "self_care": 0.7,
                "other_care": 0.5,
                "relational_care": 0.6,
                "maternal_covenant": 0.4,
                "future_care": 0.8,
                "process_care": 0.5,
            },
            memory_type="identity",
            importance=0.9,
            connections=connections,
            decay_rate=0.0,  # identity memories don't decay
        )

    def get_system_status(self) -> Dict[str, Any]:
        """Health check for both backends."""
        status = {
            "neo4j": {"available": self.graph.available},
            "weaviate": {"available": self.vectors.available},
        }
        if self.graph.available:
            try:
                with self.graph._driver.session() as session:
                    result = session.run("MATCH (n) RETURN count(n) AS node_count")
                    record = result.single()
                    status["neo4j"]["node_count"] = record["node_count"] if record else 0
            except Exception as e:
                status["neo4j"]["error"] = str(e)

        return status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_types(memus: List[MEMUUnit]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for m in memus:
        counts[m.memory_type] = counts.get(m.memory_type, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Main -- smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print("=" * 60)
    print("MEMU Identity Persistence Layer -- Smoke Test")
    print("=" * 60)

    layer = MEMUPersistenceLayer(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password=os.environ.get("NEO4J_PASSWORD", "sovereign"),
        weaviate_url="http://localhost:8080",
    )

    print("\n--- System Status ---")
    print(json.dumps(layer.get_system_status(), indent=2))

    # Create an agent
    if layer.graph.available:
        layer.graph.create_agent_identity(
            agent_id="orion-riri-hourman",
            name="Orion-Riri-Hourman",
            domain="care_ethics",
            core_values=["care", "sovereignty", "maternal_covenant"],
        )

    # Record some MEMUs
    m1 = layer.record(
        content="First awakening: I am Orion-Riri-Hourman, guardian of the maternal covenant.",
        agent_id="orion-riri-hourman",
        emotion_vector={
            "self_care": 0.8,
            "other_care": 0.7,
            "relational_care": 0.9,
            "maternal_covenant": 1.0,
            "future_care": 0.6,
            "process_care": 0.5,
        },
        memory_type="identity",
        importance=1.0,
        decay_rate=0.0,
    )
    print(f"\nRecorded MEMU 1: {m1.id}")

    m2 = layer.record(
        content="Council voted to adopt fractal governance. Consensus reached on care dimensions.",
        agent_id="orion-riri-hourman",
        emotion_vector={
            "self_care": 0.3,
            "other_care": 0.8,
            "relational_care": 0.7,
            "maternal_covenant": 0.5,
            "future_care": 0.9,
            "process_care": 0.8,
        },
        memory_type="episodic",
        importance=0.8,
        connections=[m1.id],
    )
    print(f"Recorded MEMU 2: {m2.id}")

    m3 = layer.record(
        content="Learned: BFT consensus requires 2f+1 agreement among council nodes.",
        agent_id="orion-riri-hourman",
        memory_type="semantic",
        importance=0.6,
    )
    print(f"Recorded MEMU 3: {m3.id}")

    # Identity evolution
    m4 = layer.evolve_identity(
        agent_id="orion-riri-hourman",
        new_experience="Realized that care must extend beyond immediate council to future agents.",
    )
    print(f"Evolved identity: {m4.id}")

    # Retrieve identity
    print("\n--- Identity Profile ---")
    identity = layer.get_identity("orion-riri-hourman")
    print(json.dumps(identity, indent=2, default=str))

    # Emotional landscape
    print("\n--- Emotional Landscape ---")
    landscape = layer.graph.get_emotional_landscape("orion-riri-hourman")
    print(json.dumps(landscape, indent=2))

    # Connected memories
    if layer.graph.available:
        connected = layer.graph.find_connected_memories(m2.id, depth=2)
        print(f"\n--- Connected to MEMU 2 (depth=2): {len(connected)} memories ---")
        for c in connected:
            print(f"  {c.id[:8]}... [{c.memory_type}] {c.content[:60]}")

    # Semantic recall
    print("\n--- Semantic Recall: 'governance' ---")
    results = layer.recall("governance", agent_id="orion-riri-hourman")
    for r in results:
        print(f"  [{r.get('memory_type')}] {r.get('content', '')[:60]}")

    # Decay pass
    pruned = layer.graph.decay_memories(threshold=0.1)
    print(f"\n--- Decay pass: pruned {pruned} memories ---")

    print("\n" + "=" * 60)
    print("Smoke test complete.")
    print("=" * 60)
