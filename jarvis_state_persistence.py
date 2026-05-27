#!/usr/bin/env python3
"""
JARVIS LangGraph State Persistence
Features:
- Checkpoint saving for graph state recovery
- Automatic state snapshots
- Version history with rollback
- Crash recovery support

Run: python jarvis_state_persistence.py demo
"""

import json
import os
import shutil
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import threading


@dataclass
class GraphStateSnapshot:
    """Snapshot of graph state at a point in time"""

    snapshot_id: str
    graph_name: str
    state_data: Dict[str, Any]
    node_name: str
    step: int
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphCheckpoint:
    """Complete checkpoint of graph execution"""

    checkpoint_id: str
    graph_name: str
    state: Dict[str, Any]
    node_states: Dict[str, Any]  # State at each node
    current_node: str
    step: int
    parent_checkpoint: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class StatePersistence:
    """
    LangGraph-style state persistence with checkpoints and recovery
    """

    def __init__(
        self,
        storage_dir: str = ".checkpoints",
        max_checkpoints: int = 50,
        auto_save_interval: int = 10,  # Save every N steps
    ):
        self.storage_dir = storage_dir
        self.max_checkpoints = max_checkpoints
        self.auto_save_interval = auto_save_interval

        # Ensure storage directory
        os.makedirs(storage_dir, exist_ok=True)

        # Active graphs
        self.active_graphs: Dict[str, Dict] = {}

        # Checkpoint storage
        self.checkpoints: Dict[str, List[GraphCheckpoint]] = {}

        # Lock for thread safety
        self._lock = threading.Lock()

        # Load existing checkpoints
        self._load_index()

    def _load_index(self):
        """Load checkpoint index from disk"""
        index_file = os.path.join(self.storage_dir, "checkpoint_index.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    for graph_name, checkpoints in data.items():
                        self.checkpoints[graph_name] = [
                            GraphCheckpoint(**cp) for cp in checkpoints
                        ]
            except Exception as e:
                print(f"Warning: Could not load checkpoint index: {e}")

    def _save_index(self):
        """Save checkpoint index to disk"""
        index_file = os.path.join(self.storage_dir, "checkpoint_index.json")
        try:
            data = {
                name: [asdict(cp) for cp in checkpoints]
                for name, checkpoints in self.checkpoints.items()
            }
            with open(index_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save checkpoint index: {e}")

    def create_graph(self, graph_name: str, initial_state: Dict = None) -> str:
        """Create a new graph with state tracking"""
        graph_id = f"{graph_name}_{int(time.time() * 1000)}"

        self.active_graphs[graph_id] = {
            "name": graph_name,
            "state": initial_state or {},
            "current_node": None,
            "step": 0,
            "node_states": {},
            "history": deque(maxlen=1000),  # State history for debugging
        }

        return graph_id

    def update_state(self, graph_id: str, state_update: Dict, node: str = None):
        """Update state for a graph"""
        with self._lock:
            if graph_id not in self.active_graphs:
                return

            graph = self.active_graphs[graph_id]

            # Update state
            graph["state"].update(state_update)
            graph["step"] += 1

            if node:
                graph["current_node"] = node
                # Store node-specific state
                graph["node_states"][node] = graph["state"].copy()

            # Add to history
            graph["history"].append(
                {
                    "step": graph["step"],
                    "node": node,
                    "state": graph["state"].copy(),
                    "timestamp": datetime.now().isoformat(),
                }
            )

    def get_state(self, graph_id: str) -> Optional[Dict]:
        """Get current state of a graph"""
        if graph_id not in self.active_graphs:
            return None
        return self.active_graphs[graph_id]["state"].copy()

    def save_checkpoint(self, graph_id: str, metadata: Dict = None) -> str:
        """Save a checkpoint of current graph state"""
        with self._lock:
            if graph_id not in self.active_graphs:
                return None

            graph = self.active_graphs[graph_id]

            # Create checkpoint
            checkpoint = GraphCheckpoint(
                checkpoint_id=f"cp_{int(time.time() * 1000)}",
                graph_name=graph["name"],
                state=graph["state"].copy(),
                node_states=graph["node_states"].copy(),
                current_node=graph["current_node"],
                step=graph["step"],
                metadata=metadata or {},
            )

            # Store
            graph_name = graph["name"]
            if graph_name not in self.checkpoints:
                self.checkpoints[graph_name] = []

            self.checkpoints[graph_name].append(checkpoint)

            # Limit checkpoints
            if len(self.checkpoints[graph_name]) > self.max_checkpoints:
                # Remove oldest
                old_checkpoint = self.checkpoints[graph_name].pop(0)
                self._delete_checkpoint_files(old_checkpoint)

            # Save to disk
            self._save_checkpoint_to_disk(checkpoint)
            self._save_index()

            return checkpoint.checkpoint_id

    def _save_checkpoint_to_disk(self, checkpoint: GraphCheckpoint):
        """Save checkpoint data to disk"""
        cp_dir = os.path.join(self.storage_dir, checkpoint.graph_name)
        os.makedirs(cp_dir, exist_ok=True)

        cp_file = os.path.join(cp_dir, f"{checkpoint.checkpoint_id}.json")

        with open(cp_file, "w") as f:
            json.dump(asdict(checkpoint), f, indent=2)

    def _delete_checkpoint_files(self, checkpoint: GraphCheckpoint):
        """Delete checkpoint files from disk"""
        cp_file = os.path.join(
            self.storage_dir, checkpoint.graph_name, f"{checkpoint.checkpoint_id}.json"
        )
        if os.path.exists(cp_file):
            os.remove(cp_file)

    def load_checkpoint(
        self, graph_name: str, checkpoint_id: str = None
    ) -> Optional[GraphCheckpoint]:
        """Load a checkpoint (latest if not specified)"""
        if graph_name not in self.checkpoints:
            return None

        checkpoints = self.checkpoints[graph_name]
        if not checkpoints:
            return None

        if checkpoint_id:
            for cp in checkpoints:
                if cp.checkpoint_id == checkpoint_id:
                    return cp
            return None

        # Return latest
        return checkpoints[-1]

    def restore_from_checkpoint(
        self, graph_id: str, checkpoint: GraphCheckpoint
    ) -> bool:
        """Restore a graph from checkpoint"""
        with self._lock:
            if graph_id not in self.active_graphs:
                return False

            graph = self.active_graphs[graph_id]

            # Restore state
            graph["state"] = checkpoint.state.copy()
            graph["node_states"] = checkpoint.node_states.copy()
            graph["current_node"] = checkpoint.current_node
            graph["step"] = checkpoint.step

            return True

    def list_checkpoints(self, graph_name: str = None) -> List[Dict]:
        """List available checkpoints"""
        result = []

        for name, checkpoints in self.checkpoints.items():
            if graph_name and name != graph_name:
                continue

            for cp in checkpoints:
                result.append(
                    {
                        "graph_name": cp.graph_name,
                        "checkpoint_id": cp.checkpoint_id,
                        "step": cp.step,
                        "current_node": cp.current_node,
                        "created_at": cp.created_at,
                        "metadata": cp.metadata,
                    }
                )

        return sorted(result, key=lambda x: x["created_at"], reverse=True)

    def delete_checkpoint(self, graph_name: str, checkpoint_id: str) -> bool:
        """Delete a specific checkpoint"""
        if graph_name not in self.checkpoints:
            return False

        checkpoints = self.checkpoints[graph_name]
        for i, cp in enumerate(checkpoints):
            if cp.checkpoint_id == checkpoint_id:
                self._delete_checkpoint_files(cp)
                del checkpoints[i]
                self._save_index()
                return True

        return False

    def get_graph_history(self, graph_id: str) -> List[Dict]:
        """Get execution history for a graph"""
        if graph_id not in self.active_graphs:
            return []

        return list(self.active_graphs[graph_id]["history"])

    def clear_old_checkpoints(self, graph_name: str, keep_last: int = 10):
        """Clear old checkpoints, keeping only the most recent"""
        if graph_name not in self.checkpoints:
            return

        checkpoints = self.checkpoints[graph_name]

        if len(checkpoints) <= keep_last:
            return

        to_delete = checkpoints[:-keep_last]
        checkpoints = checkpoints[-keep_last:]

        for cp in to_delete:
            self._delete_checkpoint_files(cp)

        self.checkpoints[graph_name] = checkpoints
        self._save_index()


class LangGraphAdapter:
    """
    Adapter to integrate state persistence with LangGraph-style workflows
    """

    def __init__(self, persistence: StatePersistence):
        self.persistence = persistence

    def run_with_checkpointing(
        self,
        graph_name: str,
        initial_state: Dict,
        nodes: Dict[str, callable],
        start_node: str,
        max_steps: int = 100,
    ) -> Dict:
        """
        Run a simple LangGraph-style workflow with checkpointing
        """
        # Create graph
        graph_id = self.persistence.create_graph(graph_name, initial_state)

        current_node = start_node
        step = 0

        while step < max_steps:
            # Get current state
            state = self.persistence.get_state(graph_id)

            # Check if we've reached an end node
            if current_node not in nodes:
                break

            # Execute node
            node_fn = nodes[current_node]
            next_node = node_fn(state)

            # Update state
            self.persistence.update_state(graph_id, state, current_node)

            # Auto-checkpoint every N steps
            if step % self.persistence.auto_save_interval == 0:
                self.persistence.save_checkpoint(graph_id, {"auto": True})

            # Move to next node
            current_node = next_node
            step += 1

        # Final state
        return self.persistence.get_state(graph_id)


def demo():
    """Demo the state persistence"""
    print("=" * 50)
    print("LangGraph State Persistence Demo")
    print("=" * 50)

    persistence = StatePersistence(max_checkpoints=10)

    # Create a simple workflow
    print("\n1. Creating workflow graph...")
    graph_id = persistence.create_graph("demo_workflow", {"counter": 0, "logs": []})
    print(f"   Graph ID: {graph_id}")

    # Update state
    print("\n2. Updating state...")
    for i in range(5):
        persistence.update_state(
            graph_id, {"counter": i, "logs": [f"step {i}"]}, node=f"node_{i}"
        )

    state = persistence.get_state(graph_id)
    print(f"   Current state: {state}")

    # Save checkpoint
    print("\n3. Saving checkpoint...")
    cp_id = persistence.save_checkpoint(graph_id, {"reason": "demo"})
    print(f"   Checkpoint ID: {cp_id}")

    # List checkpoints
    print("\n4. Listing checkpoints...")
    checkpoints = persistence.list_checkpoints("demo_workflow")
    for cp in checkpoints:
        print(f"   - {cp['checkpoint_id']} (step {cp['step']})")

    # Simulate crash and recovery
    print("\n5. Simulating crash and recovery...")
    # Save another checkpoint
    persistence.update_state(graph_id, {"counter": 100, "status": "crashed"})
    cp_id2 = persistence.save_checkpoint(graph_id, {"reason": "before crash"})

    # Create new graph and restore
    new_graph_id = persistence.create_graph("demo_workflow")
    loaded_cp = persistence.load_checkpoint("demo_workflow")

    if loaded_cp:
        persistence.restore_from_checkpoint(new_graph_id, loaded_cp)
        restored_state = persistence.get_state(new_graph_id)
        print(f"   Restored state: {restored_state}")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print("Usage: python jarvis_state_persistence.py demo")
