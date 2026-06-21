#!/usr/bin/env python3
"""
SOV3 Mesh Node — libp2p Gossipsub bootstrap.
BFT vote broadcast, peer scoring.
Works on M2 Mac, RPi5, or Asimov edge controller.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr

PROTOCOL_ID = "/sov3/mesh/1.0.0"
GOSSIP_TOPIC = "sov3_bft_votes"


class Sov3MeshNode:
    """A single node in the SOV3 sovereign mesh."""

    def __init__(self, node_id: str, listen_addr: str = "/ip4/0.0.0.0/tcp/0"):
        self.node_id = node_id
        self.host = new_host()
        self.listen_addr = listen_addr
        self.peers: Dict[str, Any] = {}
        self.vote_log: List[Dict] = []
        self.running = False
        self.pubsub = None

    async def start(self, bootstrap_peers: Optional[List[str]] = None):
        await self.host.get_network().listen(Multiaddr(self.listen_addr))

        # Set up gossipsub
        try:
            from libp2p.pubsub.gossipsub import GossipSub
            from libp2p.pubsub.pubsub import Pubsub
            gossipsub_router = GossipSub(
                protocols=["gossipsub"],
                degree=3,
                degree_low=2,
                degree_high=4,
                time_to_live=60,
            )
            self.pubsub = Pubsub(self.host, gossipsub_router, self.host.get_id())
            await self.pubsub.subscribe(GOSSIP_TOPIC)
            asyncio.create_task(self._read_gossip())
            print(f"[{self.node_id}] Gossipsub active on topic: {GOSSIP_TOPIC}")
        except Exception as exc:
            print(f"[{self.node_id}] Gossipsub init warning: {exc}")

        if bootstrap_peers:
            for addr in bootstrap_peers:
                try:
                    info = info_from_p2p_addr(Multiaddr(addr))
                    await self.host.connect(info)
                    self.peers[str(info.peer_id)] = addr
                    print(f"[{self.node_id}] Connected to bootstrap: {addr}")
                except Exception as exc:
                    print(f"[{self.node_id}] Bootstrap failed for {addr}: {exc}")

        self.running = True
        addrs = self.host.get_addrs()
        print(f"[{self.node_id}] Mesh node listening on: {addrs}")

    async def _read_gossip(self):
        if not self.pubsub:
            return
        while self.running:
            try:
                msg = await self.pubsub.get_msg(GOSSIP_TOPIC)
                if msg:
                    data = json.loads(msg.data.decode())
                    print(f"[{self.node_id}] Gossip: {data.get('type')} from {data.get('from')}")
                    if data.get("type") == "bft_vote":
                        self.vote_log.append(data)
            except Exception:
                await asyncio.sleep(0.1)

    async def broadcast_vote(self, proposal_id: str, vote: str, signature: str):
        msg = {
            "type": "bft_vote",
            "from": self.node_id,
            "proposal_id": proposal_id,
            "vote": vote,
            "signature": signature,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if self.pubsub:
            await self.pubsub.publish(GOSSIP_TOPIC, json.dumps(msg).encode())
        else:
            print(f"[{self.node_id}] Pubsub not available, cannot broadcast.")

    async def stop(self):
        self.running = False
        await self.host.close()
        print(f"[{self.node_id}] Mesh node stopped.")


async def main():
    node = Sov3MeshNode(node_id="sov3_node_1", listen_addr="/ip4/127.0.0.1/tcp/10001")
    await node.start(bootstrap_peers=[])
    try:
        while True:
            await asyncio.sleep(10)
            print(f"[sov3_node_1] Peers: {len(node.peers)} | Votes: {len(node.vote_log)}")
    except asyncio.CancelledError:
        pass
    finally:
        await node.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMesh node shut down.")
