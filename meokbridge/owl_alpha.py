"""
Owl Alpha Integration — OpenRouter's free agentic model
1M context, 262K output, tool-native, code generation
Updated: May 27, 2026
"""
from .core import Node, NodeType, BridgeResult

# OpenRouter model IDs (May 2026)
OWL_ALPHA = "openrouter/owl-alpha"
DEEPSEEK_V4_FLASH = "deepseek/deepseek-v4-flash"
GEMMA4_27B = "google/gemma-4-27b-it"
GEMMA4_31B = "google/gemma-4-31b-it"
NEMOTRON3_SUPER = "nvidia/nemotron-3-super"
BAIDU_COBUDDY = "baidu/cobuddy"
LYRIA3_PRO = "google/lyria-3-pro"

def get_free_tier_nodes():
    """Return all free-tier OpenRouter nodes for council mode."""
    return [
        {"id": "owl-alpha", "model": OWL_ALPHA, "tags": ["free", "agentic", "tool-use", "1m-context"]},
        {"id": "deepseek-v4-flash", "model": DEEPSEEK_V4_FLASH, "tags": ["free", "reasoning", "1m-context"]},
        {"id": "gemma4-27b", "model": GEMMA4_27B, "tags": ["free", "vision", "multimodal"]},
        {"id": "baidu-cobuddy", "model": BAIDU_COBUDDY, "tags": ["free", "131k-context"]},
    ]

async def chat_with_owl(bridge, message: str, **kwargs) -> BridgeResult:
    """Use Owl Alpha for agentic tasks — FREE, 1M context, 262K output."""
    return await bridge.chat(message, node_id="owl-alpha", model=OWL_ALPHA, **kwargs)

async def code_with_deepseek_v4(bridge, message: str, **kwargs) -> BridgeResult:
    """Use DeepSeek V4 Flash for coding — FREE, 1M context, 384K output."""
    return await bridge.chat(message, node_id="deepseek-v4-flash", model=DEEPSEEK_V4_FLASH, **kwargs)

async def vision_with_gemma4(bridge, message: str, **kwargs) -> BridgeResult:
    """Use Gemma 4 for vision tasks — FREE, 27B, vision-capable."""
    return await bridge.chat(message, node_id="gemma4-27b-free", model=GEMMA4_27B, **kwargs)

async def reasoning_with_nemotron3(bridge, message: str, **kwargs) -> BridgeResult:
    """Use NVIDIA Nemotron 3 for reasoning."""
    return await bridge.chat(message, node_id="nemotron3-super", model=NEMOTRON3_SUPER, **kwargs)

async def creative_with_lyria(bridge, message: str, **kwargs) -> BridgeResult:
    """Use Google Lyria 3 for creative tasks."""
    return await bridge.chat(message, node_id="lyria3-pro", model=LYRIA3_PRO, **kwargs)

class FreeTierCouncil:
    """Council using only free-tier OpenRouter models for zero-cost inference."""
    
    def __init__(self, bridge):
        self.bridge = bridge
        self.models = get_free_tier_nodes()
    
    async def council_chat(self, message: str) -> dict:
        """Query all free-tier models in parallel, return consensus."""
        import asyncio
        
        tasks = []
        for node in self.models:
            tasks.append(self._query_safe(node["id"], node["model"], message))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid = [r for r in results if isinstance(r, dict) and r.get("success")]
        if not valid:
            return {"success": False, "error": "All free-tier models failed"}
        
        # Simple consensus: pick the response with highest confidence
        # In production, use semantic similarity clustering
        best = max(valid, key=lambda x: x.get("confidence", 0.5))
        return {
            "success": True,
            "text": best["text"],
            "model": best.get("model"),
            "votes": len(valid),
            "total": len(self.models),
            "cost_usd": 0.0  # All free
        }
    
    async def _query_safe(self, node_id: str, model: str, message: str):
        try:
            result = await self.bridge.chat(message, node_id=node_id, model=model, timeout=30)
            return {"success": True, "text": result.text, "model": model, "confidence": 0.8}
        except Exception as e:
            return {"success": False, "error": str(e), "model": model}
