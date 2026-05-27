#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  WINDOWS BRIDGE — MEOKCLAW on Windows 10/11                                 ║
║                                                                              ║
║  Brings the Mac Mesh to Windows PCs via:                                     ║
║    • ONNX Runtime (CPU/GPU) for local inference                              ║
║    • DirectML for AMD/Intel/NVIDIA GPU acceleration                          ║
║    • WSL2 fallback for Linux-compatible stacks                               ║
║    • Mesh client mode — Windows joins as a peer, not a command center        ║
║                                                                              ║
║  Target hardware:                                                            ║
║    • Gaming PCs (RTX 3060+) → L2 inference                                   ║
║    • Office laptops (iGPU) → L1 inference + mesh client                      ║
║    • Surface Pro (NPU) → L0 routing + embeddings                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

MESH_ORCHESTRATOR = os.environ.get("MESH_ORCHESTRATOR", "http://m4-macbook.local:3202")
WINDOWS_NODE_ID = os.environ.get("WINDOWS_NODE_ID", "windows-peer")
LOCAL_BACKEND = os.environ.get("LOCAL_BACKEND", "onnx")  # onnx, directml, wsl2

# ═══════════════════════════════════════════════════════════════════════════════
# Hardware Detection
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WindowsProfile:
    node_id: str
    os_version: str
    cpu_cores: int
    ram_gb: float
    has_nvidia: bool
    has_amd: bool
    has_intel_arc: bool
    has_npu: bool
    gpu_vram_gb: float
    backend: str
    status: str = "online"


def detect_windows_hardware() -> WindowsProfile:
    """Detect Windows hardware capabilities."""
    import ctypes
    from ctypes import wintypes

    # RAM
    kernel32 = ctypes.windll.kernel32
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    mem = MEMORYSTATUSEX()
    mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
    ram_gb = mem.ullTotalPhys / (1024 ** 3)

    # CPU cores
    cpu_cores = os.cpu_count() or 4

    # GPU detection (simplified — check for NVIDIA/AMD via common libs)
    has_nvidia = False
    has_amd = False
    has_intel_arc = False
    has_npu = False
    gpu_vram_gb = 0.0

    try:
        import torch
        if torch.cuda.is_available():
            has_nvidia = True
            gpu_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    except ImportError:
        pass

    # Check for DirectML
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if "DmlExecutionProvider" in providers:
            has_npu = True  # DirectML covers NPU/GPU
    except ImportError:
        pass

    return WindowsProfile(
        node_id=WINDOWS_NODE_ID,
        os_version=f"Windows {platform.version()}",
        cpu_cores=cpu_cores,
        ram_gb=ram_gb,
        has_nvidia=has_nvidia,
        has_amd=has_amd,
        has_intel_arc=has_intel_arc,
        has_npu=has_npu,
        gpu_vram_gb=gpu_vram_gb,
        backend=LOCAL_BACKEND,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ONNX Local Inference
# ═══════════════════════════════════════════════════════════════════════════════

class WindowsInference:
    """Local inference on Windows using ONNX Runtime."""

    def __init__(self, profile: WindowsProfile):
        self.profile = profile
        self.session = None
        self.model_loaded = False

    def load_model(self, model_path: str) -> bool:
        """Load an ONNX model with optimal execution provider."""
        try:
            import onnxruntime as ort

            providers = ["CPUExecutionProvider"]
            if self.profile.has_nvidia:
                providers.insert(0, "CUDAExecutionProvider")
            elif self.profile.has_npu:
                providers.insert(0, "DmlExecutionProvider")

            self.session = ort.InferenceSession(model_path, providers=providers)
            self.model_loaded = True
            return True
        except Exception as e:
            print(f"[WINDOWS] Failed to load ONNX model: {e}")
            return False

    def infer(self, input_data) -> Optional[dict]:
        """Run inference."""
        if not self.session:
            return None
        try:
            input_name = self.session.get_inputs()[0].name
            outputs = self.session.run(None, {input_name: input_data})
            return {"outputs": outputs}
        except Exception as e:
            print(f"[WINDOWS] Inference failed: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# Mesh Client — Windows joins the Mac Mesh
# ═══════════════════════════════════════════════════════════════════════════════

class WindowsMeshClient:
    """Windows peer in the Mac Mesh. Does not run orchestrator."""

    def __init__(self, orchestrator_url: str = MESH_ORCHESTRATOR):
        self.orchestrator = orchestrator_url
        self.profile = detect_windows_hardware()
        self.inference = WindowsInference(self.profile)
        self._client = httpx.AsyncClient(timeout=120.0)

    async def register(self):
        """Register Windows node with mesh orchestrator."""
        try:
            await self._client.post(
                f"{self.orchestrator}/v1/nodes/windows/register",
                json={
                    "node_id": self.profile.node_id,
                    "os": self.profile.os_version,
                    "ram_gb": self.profile.ram_gb,
                    "gpu_vram_gb": self.profile.gpu_vram_gb,
                    "backend": self.profile.backend,
                    "capabilities": ["onnx", "directml"] if self.profile.has_npu else ["onnx"],
                },
            )
            print(f"[WINDOWS] Registered with mesh orchestrator")
        except Exception as e:
            print(f"[WINDOWS] Registration failed: {e}")

    async def chat(self, message: str, use_local: bool = False) -> dict:
        """Chat via mesh orchestrator. Optionally use local ONNX first."""
        if use_local and self.inference.model_loaded:
            # Try local ONNX inference first
            # This is a placeholder — real implementation depends on model tokenizer
            pass

        # Fallback to mesh orchestrator
        try:
            resp = await self._client.post(
                f"{self.orchestrator}/v1/chat",
                json={
                    "message": message,
                    "use_speculative": True,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e), "text": "Mesh unreachable. Check connection to Mac Mesh."}

    async def heartbeat(self):
        """Send periodic heartbeat."""
        while True:
            try:
                await self._client.post(
                    f"{self.orchestrator}/v1/nodes/windows/heartbeat",
                    json={
                        "node_id": self.profile.node_id,
                        "status": "online",
                        "timestamp": time.time(),
                    },
                )
            except Exception:
                pass
            await asyncio.sleep(30)

    async def close(self):
        await self._client.aclose()


# ═══════════════════════════════════════════════════════════════════════════════
# WSL2 Bridge — Run Linux Ollama inside WSL2
# ═══════════════════════════════════════════════════════════════════════════════

class WSL2Bridge:
    """Bridge to Ollama running inside WSL2."""

    WSL_OLLAMA_HOST = "localhost"  # WSL2 forwards ports to Windows host
    WSL_OLLAMA_PORT = 11434

    @classmethod
    def is_wsl2_running(cls) -> bool:
        """Check if WSL2 is available."""
        import subprocess
        try:
            result = subprocess.run(["wsl", "--status"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def start_ollama_in_wsl(cls):
        """Start Ollama service in WSL2."""
        import subprocess
        subprocess.Popen(
            ["wsl", "bash", "-c", "ollama serve > /tmp/ollama.log 2>&1 &"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        print("[WSL2] Ollama started in WSL2. Accessible at localhost:11434")

    @classmethod
    async def list_models(cls) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"http://{cls.WSL_OLLAMA_HOST}:{cls.WSL_OLLAMA_PORT}/api/tags")
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("=" * 60)
    print("MEOKCLAW Windows Bridge")
    print("=" * 60)

    profile = detect_windows_hardware()
    print(f"\nHardware Profile:")
    print(f"  OS: {profile.os_version}")
    print(f"  CPU: {profile.cpu_cores} cores")
    print(f"  RAM: {profile.ram_gb:.1f} GB")
    print(f"  GPU: {'NVIDIA' if profile.has_nvidia else 'AMD' if profile.has_amd else 'Intel Arc' if profile.has_intel_arc else 'iGPU'}")
    print(f"  GPU VRAM: {profile.gpu_vram_gb:.1f} GB")
    print(f"  NPU/DirectML: {'Yes' if profile.has_npu else 'No'}")
    print(f"  Backend: {profile.backend}")

    # Check WSL2
    if WSL2Bridge.is_wsl2_running():
        print(f"\n[WSL2] Detected. Models: {await WSL2Bridge.list_models()}")
    else:
        print("\n[WSL2] Not detected. Install WSL2 for best experience.")

    # Register with mesh
    client = WindowsMeshClient()
    await client.register()

    # Interactive mode
    print("\nEntering interactive mode. Type 'exit' to quit.")
    while True:
        try:
            msg = input("\nYou: ").strip()
            if msg.lower() in ("exit", "quit"):
                break
            if not msg:
                continue

            result = await client.chat(msg)
            text = result.get("text", result.get("error", "No response"))
            node = result.get("node", "unknown")
            print(f"[{node}] {text[:500]}")
        except KeyboardInterrupt:
            break

    await client.close()
    print("\n[WINDOWS] Bridge closed.")


if __name__ == "__main__":
    asyncio.run(main())
