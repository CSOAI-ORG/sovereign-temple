"""Device capability detection for optimal tier selection."""
from __future__ import annotations

import platform
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceProfile:
    """Hardware capability profile for routing decisions."""
    platform: str = "unknown"  # ios, android, windows, macos, linux, web
    arch: str = "unknown"      # arm64, x86_64, wasm32
    ram_gb: float = 4.0
    vram_gb: float = 0.0
    has_npu: bool = False
    has_gpu: bool = False
    gpu_vendor: str = "none"   # apple, nvidia, amd, qualcomm, mali
    browser: Optional[str] = None  # chrome, safari, firefox, edge
    webgpu_supported: bool = False
    webgl_supported: bool = False
    thermal_state: str = "nominal"  # nominal, fair, serious, critical
    battery_level: Optional[float] = None

    def __str__(self) -> str:
        return f"{self.platform}/{self.arch} RAM:{self.ram_gb}GB VRAM:{self.vram_gb}GB NPU:{self.has_npu} GPU:{self.has_gpu}"


def detect_device_profile() -> DeviceProfile:
    """Auto-detect device capabilities from environment."""
    prof = DeviceProfile()

    # Platform detection
    sys_platform = platform.system().lower()
    if sys_platform == "darwin":
        prof.platform = "macos"
        prof.arch = platform.machine()
        prof.has_gpu = True  # All modern Macs have Metal
        prof.gpu_vendor = "apple"
        # Check for Apple Silicon NPU (Neural Engine)
        if prof.arch == "arm64":
            prof.has_npu = True
    elif sys_platform == "windows":
        prof.platform = "windows"
        prof.arch = platform.machine()
    elif sys_platform == "linux":
        prof.platform = "linux"
        prof.arch = platform.machine()

    # RAM detection
    try:
        import psutil
        prof.ram_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        pass

    # GPU/VRAM detection (NVIDIA)
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            prof.vram_gb = int(result.stdout.strip()) / 1024
            prof.has_gpu = True
            prof.gpu_vendor = "nvidia"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Web environment overrides (set by client JS)
    if os.environ.get("MEOKCLAW_PLATFORM") == "web":
        prof.platform = "web"
        prof.browser = os.environ.get("MEOKCLAW_BROWSER")
        prof.webgpu_supported = os.environ.get("MEOKCLAW_WEBGPU") == "1"
        prof.webgl_supported = os.environ.get("MEOKCLAW_WEBGL") == "1"
        prof.ram_gb = float(os.environ.get("MEOKCLAW_RAM_GB", "4"))
        prof.has_gpu = prof.webgpu_supported

    return prof
