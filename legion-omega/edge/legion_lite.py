"""
Legion Lite — Edge Deployment (Raspberry Pi 5 / Mac Mini)
20W power envelope | Brian2 SNN | Federated edge node
MEOK AI Labs
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Optional

import numpy as np
import redis

try:
    import brian2 as brian
    from brian2 import *
    brian.prefs.codegen.target = 'numpy'
    BRIAN2_AVAILABLE = True
except ImportError:
    BRIAN2_AVAILABLE = False
    print("[WARNING] Brian2 not available — using numpy fallback")


class LegionLiteNode:
    def __init__(self, node_id: str, parent_node: str):
        self.node_id = node_id
        self.parent = parent_node
        self.power_budget = int(os.getenv("POWER_BUDGET", "20"))
        self.federated = os.getenv("FEDERATED_UPLOAD", "true").lower() == "true"

        try:
            self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
            self.redis.ping()
        except Exception:
            self.redis = None

        self.snn = self._init_snn() if BRIAN2_AVAILABLE else None
        self.stats = {"inferences": 0, "power": 0.0}

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f"LegionLite-{node_id}")
        self.logger.info(f"Node {node_id} online | Budget: {self.power_budget}W")

    def _init_snn(self) -> Optional[Dict]:
        """Brian2 minimal SNN"""
        defaultclock.dt = 1 * ms
        N_in, N_hid, N_out = 128, 64, 16
        eqs = 'dv/dt = (I - v) / tau : 1 (unless refractory)\nI : 1\ntau : second'

        inp = NeuronGroup(N_in, eqs, threshold='v>1', reset='v=0', refractory=5*ms, method='euler')
        hid = NeuronGroup(N_hid, eqs, threshold='v>1', reset='v=0', refractory=5*ms, method='euler')
        out = NeuronGroup(N_out, eqs, threshold='v>1', reset='v=0', refractory=5*ms, method='euler')

        S1 = Synapses(inp, hid, 'w:1', on_pre='v_post += w')
        S1.connect(p=0.1)
        S1.w = 'rand() * 0.5'
        S2 = Synapses(hid, out, 'w:1', on_pre='v_post += w')
        S2.connect(p=0.1)
        S2.w = 'rand() * 0.5'

        inp.tau = '10*ms'
        hid.tau = '10*ms'
        out.tau = '10*ms'

        return {'input': inp, 'hidden': hid, 'output': out}

    async def run_inference(self, events: np.ndarray) -> np.ndarray:
        if self.snn and BRIAN2_AVAILABLE:
            self.snn['input'].I = events.flatten()[:128]
            run(50 * ms)
            result = np.array(self.snn['output'].v)
        else:
            result = np.random.rand(16)

        power = min(5.0 + np.random.uniform(0, 10), self.power_budget)
        self.stats['inferences'] += 1
        self.stats['power'] = power

        if self.federated and self.redis:
            await self._upload(result, power)

        return result

    async def _upload(self, output: np.ndarray, power: float):
        exp = {
            "node_id": self.node_id,
            "output": output.tolist(),
            "power": power,
            "timestamp": time.time()
        }
        noise = np.random.laplace(0, 1.0, len(exp["output"]))
        exp["output"] = (np.array(exp["output"]) + noise).tolist()
        self.redis.lpush(f"experience:{self.parent}", json.dumps(exp))
        self.redis.expire(f"experience:{self.parent}", 3600)

    async def heartbeat(self):
        while True:
            if self.redis:
                self.redis.hset(f"heartbeat:{self.node_id}", mapping={
                    "ts": time.time(), "status": "alive",
                    "power": self.stats['power'], "inferences": self.stats['inferences']
                })
                self.redis.expire(f"heartbeat:{self.node_id}", 15)
            await asyncio.sleep(5)

    async def run(self):
        asyncio.create_task(self.heartbeat())
        while True:
            fake_events = np.random.rand(128)
            result = await self.run_inference(fake_events)
            action = int(np.argmax(result))
            self.logger.info(f"Action: {action} | Power: {self.stats['power']:.1f}W | Inferences: {self.stats['inferences']}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    node_id = os.getenv("NODE_ID", "edge-001")
    parent = os.getenv("PARENT_NODE", "jarvis-core")
    node = LegionLiteNode(node_id, parent)
    asyncio.run(node.run())
