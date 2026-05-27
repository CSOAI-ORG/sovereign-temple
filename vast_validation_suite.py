#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  VAST.AI NEURAL VALIDATION SUITE v2.0                                        ║
║                                                                              ║
║  Production-grade validation for remote GPU instances on Vast.ai.            ║
║  Verifies:                                                                   ║
║    • GPU detection (CUDA, ROCm, or CPU fallback)                             ║
║    • SOV3 substrate forward pass (Mamba/SSM + Global Workspace)              ║
║    • Memory recursion stability (2K context window)                          ║
║    • Mesh orchestrator connectivity (M2/M4 bridge)                           ║
║    • Ollama inference sanity (model load + generate)                         ║
║    • Alchemical Flow latency benchmarks                                      ║
║    • Network throughput (SSH tunnel health)                                  ║
║                                                                              ║
║  Usage:                                                                      ║
║    python3 vast_validation_suite.py [--mesh-url http://m4:3202]              ║
║                                       [--ollama-url http://localhost:11436]  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

MESH_ORCHESTRATOR = os.environ.get("MESH_ORCHESTRATOR", "http://localhost:3202")
OLLAMA_URL = os.environ.get("VAST_OLLAMA_URL", "http://localhost:11434")
REPORT_PATH = Path("/workspace/meokclaw-sov3/vast_validation_report.json")


# ═══════════════════════════════════════════════════════════════════════════════
# Result Tracking
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    details: Dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ValidationReport:
    timestamp: str
    hostname: str
    gpu_info: Dict
    tests: List[TestResult]
    overall_score: int = 0  # 0-100
    status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "hostname": self.hostname,
            "gpu_info": self.gpu_info,
            "tests": [asdict(t) for t in self.tests],
            "overall_score": self.overall_score,
            "status": self.status,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GPU Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_gpu() -> Dict:
    """Detect available GPU and report specs."""
    gpu_info = {
        "cuda_available": False,
        "rocm_available": False,
        "device_name": "CPU",
        "vram_total_gb": 0.0,
        "vram_free_gb": 0.0,
        "cuda_version": None,
        "driver_version": None,
    }

    try:
        import torch
        if torch.cuda.is_available():
            gpu_info["cuda_available"] = True
            props = torch.cuda.get_device_properties(0)
            gpu_info["device_name"] = torch.cuda.get_device_name(0)
            gpu_info["vram_total_gb"] = props.total_memory / (1024 ** 3)
            gpu_info["vram_free_gb"] = (props.total_memory - torch.cuda.memory_allocated(0)) / (1024 ** 3)
            gpu_info["cuda_version"] = torch.version.cuda
            gpu_info["driver_version"] = torch.cuda.get_device_capability(0)
            gpu_info["multi_gpu"] = torch.cuda.device_count() > 1
            gpu_info["gpu_count"] = torch.cuda.device_count()
    except ImportError:
        pass

    # ROCm check
    try:
        import torch
        if hasattr(torch.version, 'hip') and torch.version.hip is not None:
            gpu_info["rocm_available"] = True
            gpu_info["device_name"] = f"AMD ROCm {torch.version.hip}"
    except ImportError:
        pass

    return gpu_info


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Hardware Check
# ═══════════════════════════════════════════════════════════════════════════════

def test_hardware() -> TestResult:
    """Test 1: Detect and validate GPU hardware."""
    start = time.perf_counter()
    gpu_info = detect_gpu()
    duration = (time.perf_counter() - start) * 1000

    passed = gpu_info["cuda_available"] or gpu_info["rocm_available"]
    if not passed:
        return TestResult(
            name="hardware_check",
            passed=False,
            duration_ms=duration,
            details=gpu_info,
            error="No GPU detected. Running on CPU is not recommended for production.",
        )

    return TestResult(
        name="hardware_check",
        passed=True,
        duration_ms=duration,
        details=gpu_info,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: SOV3 Substrate Forward Pass
# ═══════════════════════════════════════════════════════════════════════════════

def test_sov3_substrate() -> TestResult:
    """Test 2: Initialize SOV3 architecture and run forward pass."""
    start = time.perf_counter()

    try:
        from sovereign_architecture_v3 import SovereignArchitectureV3
        import torch

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Scale embed_dim and num_layers for cloud capacity
        model = SovereignArchitectureV3(
            vocab_size=32000,
            embed_dim=1024,
            hidden_size=1024,
            num_layers=8,
        ).to(device)

        params = sum(p.numel() for p in model.parameters())

        # Forward pass
        batch_size = 8
        seq_len = 64
        input_ids = torch.randint(0, 32000, (batch_size, seq_len)).to(device)

        with torch.no_grad():
            output = model(input_ids)

        duration = (time.perf_counter() - start) * 1000

        return TestResult(
            name="sov3_substrate",
            passed=True,
            duration_ms=duration,
            details={
                "parameters": params,
                "batch_size": batch_size,
                "seq_len": seq_len,
                "device": str(device),
                "output_shape": list(output.shape) if hasattr(output, 'shape') else None,
            },
        )

    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            name="sov3_substrate",
            passed=False,
            duration_ms=duration,
            error=str(e),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: Memory Recursion Stability (2K context)
# ═══════════════════════════════════════════════════════════════════════════════

def test_memory_recursion() -> TestResult:
    """Test 3: Verify SSM recursion stability with long context."""
    start = time.perf_counter()

    try:
        from sovereign_architecture_v3 import SovereignArchitectureV3
        import torch

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = SovereignArchitectureV3(
            vocab_size=32000,
            embed_dim=512,  # Smaller for long context test
            hidden_size=512,
            num_layers=4,
        ).to(device)

        long_ctx = torch.randint(0, 32000, (1, 2048)).to(device)

        with torch.no_grad():
            _ = model(long_ctx)

        duration = (time.perf_counter() - start) * 1000

        return TestResult(
            name="memory_recursion",
            passed=True,
            duration_ms=duration,
            details={"context_length": 2048, "device": str(device)},
        )

    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            name="memory_recursion",
            passed=False,
            duration_ms=duration,
            error=str(e),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Alchemical Flow Latency Benchmark
# ═══════════════════════════════════════════════════════════════════════════════

def test_alchemical_flow() -> TestResult:
    """Test 4: Benchmark inference latency for complex reasoning."""
    start = time.perf_counter()

    try:
        from sovereign_architecture_v3 import SovereignArchitectureV3
        import torch

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = SovereignArchitectureV3(
            vocab_size=32000,
            embed_dim=1024,
            hidden_size=1024,
            num_layers=8,
        ).to(device)

        # Complex batch: multiple sequence lengths
        batch_configs = [(4, 128), (2, 512), (1, 1024)]
        latencies = []

        for bs, sl in batch_configs:
            input_ids = torch.randint(0, 32000, (bs, sl)).to(device)

            # Warmup
            with torch.no_grad():
                _ = model(input_ids)
            if device.type == "cuda":
                torch.cuda.synchronize()

            # Benchmark
            t0 = time.perf_counter()
            with torch.no_grad():
                _ = model(input_ids)
            if device.type == "cuda":
                torch.cuda.synchronize()
            t1 = time.perf_counter()

            latencies.append({
                "batch_size": bs,
                "seq_len": sl,
                "latency_ms": (t1 - t0) * 1000,
            })

        duration = (time.perf_counter() - start) * 1000
        avg_latency = sum(l["latency_ms"] for l in latencies) / len(latencies)

        return TestResult(
            name="alchemical_flow",
            passed=True,
            duration_ms=duration,
            details={
                "batch_results": latencies,
                "average_latency_ms": avg_latency,
            },
        )

    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            name="alchemical_flow",
            passed=False,
            duration_ms=duration,
            error=str(e),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Ollama Inference Sanity
# ═══════════════════════════════════════════════════════════════════════════════

def test_ollama_sanity(ollama_url: str = OLLAMA_URL) -> TestResult:
    """Test 5: Verify Ollama is running and can generate text."""
    start = time.perf_counter()

    try:
        import urllib.request
        import json

        # Check if Ollama is reachable
        req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            models = json.loads(resp.read()).get("models", [])

        if not models:
            duration = (time.perf_counter() - start) * 1000
            return TestResult(
                name="ollama_sanity",
                passed=False,
                duration_ms=duration,
                error="Ollama running but no models loaded.",
            )

        # Try a simple generation
        model_name = models[0]["name"]
        payload = json.dumps({
            "model": model_name,
            "prompt": "Say 'VAST VALIDATED' and nothing else.",
            "stream": False,
            "options": {"num_predict": 10},
        }).encode()

        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            response_text = result.get("response", "")

        duration = (time.perf_counter() - start) * 1000

        return TestResult(
            name="ollama_sanity",
            passed=True,
            duration_ms=duration,
            details={
                "model": model_name,
                "models_available": len(models),
                "response_preview": response_text[:100],
            },
        )

    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            name="ollama_sanity",
            passed=False,
            duration_ms=duration,
            error=str(e),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: Mesh Orchestrator Connectivity
# ═══════════════════════════════════════════════════════════════════════════════

def test_mesh_connectivity(mesh_url: str = MESH_ORCHESTRATOR) -> TestResult:
    """Test 6: Verify connectivity back to Mac Mesh orchestrator."""
    start = time.perf_counter()

    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{mesh_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        duration = (time.perf_counter() - start) * 1000

        nodes_online = data.get("healthy_nodes", 0)
        speculative_ready = data.get("speculative_ready", False)

        return TestResult(
            name="mesh_connectivity",
            passed=nodes_online > 0,
            duration_ms=duration,
            details={
                "nodes_online": nodes_online,
                "speculative_ready": speculative_ready,
                "mesh_status": data.get("mesh_status", "unknown"),
            },
        )

    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            name="mesh_connectivity",
            passed=False,
            duration_ms=duration,
            error=str(e),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: Network Throughput (SSH Tunnel Health)
# ═══════════════════════════════════════════════════════════════════════════════

def test_network_throughput() -> TestResult:
    """Test 7: Measure effective bandwidth to/from Vast instance."""
    start = time.perf_counter()

    try:
        # Download test: fetch a ~1MB file from a fast CDN
        import urllib.request
        test_url = "https://speed.hetzner.de/10MB.bin"

        t0 = time.perf_counter()
        req = urllib.request.Request(test_url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read(1024 * 1024)  # Read 1MB
        t1 = time.perf_counter()

        bytes_read = len(data)
        duration_sec = t1 - t0
        throughput_mbps = (bytes_read * 8) / (duration_sec * 1024 * 1024)

        total_duration = (time.perf_counter() - start) * 1000

        return TestResult(
            name="network_throughput",
            passed=throughput_mbps > 10,  # At least 10 Mbps
            duration_ms=total_duration,
            details={
                "bytes_read": bytes_read,
                "duration_sec": round(duration_sec, 2),
                "throughput_mbps": round(throughput_mbps, 2),
            },
        )

    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            name="network_throughput",
            passed=False,
            duration_ms=duration,
            error=str(e),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def run_all_tests(mesh_url: str, ollama_url: str) -> ValidationReport:
    """Run the complete validation suite."""
    print(f"\n{'=' * 60}")
    print("MEOKCLAW VAST.AI NEURAL VALIDATION SUITE v2.0")
    print(f"{'=' * 60}")
    print(f"Mesh Orchestrator: {mesh_url}")
    print(f"Ollama URL: {ollama_url}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"{'=' * 60}\n")

    tests = [
        test_hardware,
        test_sov3_substrate,
        test_memory_recursion,
        test_alchemical_flow,
        lambda: test_ollama_sanity(ollama_url),
        lambda: test_mesh_connectivity(mesh_url),
        test_network_throughput,
    ]

    results = []
    for test_fn in tests:
        result = test_fn()
        results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"[{status}] {result.name}: {result.duration_ms:.1f}ms")
        if result.error:
            print(f"         Error: {result.error[:100]}")

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    score = int((passed / total) * 100)

    report = ValidationReport(
        timestamp=datetime.utcnow().isoformat(),
        hostname=socket.gethostname(),
        gpu_info=detect_gpu(),
        tests=results,
        overall_score=score,
        status="READY" if score == 100 else "DEGRADED" if score >= 70 else "FAILED",
    )

    # Save report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"RESULT: {report.status} — {score}/100 ({passed}/{total} tests passed)")
    print(f"Report saved to: {REPORT_PATH}")
    print(f"{'=' * 60}\n")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MEOKCLAW Vast.ai Validation Suite")
    parser.add_argument("--mesh-url", default=MESH_ORCHESTRATOR, help="Mac Mesh orchestrator URL")
    parser.add_argument("--ollama-url", default=OLLAMA_URL, help="Ollama URL on Vast instance")
    args = parser.parse_args()

    report = run_all_tests(args.mesh_url, args.ollama_url)

    # Exit code: 0 for 100/100, 1 otherwise
    sys.exit(0 if report.overall_score == 100 else 1)
