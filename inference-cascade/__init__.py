"""MEOKCLAW Split-Inference Cascade Engine

Routes every query to the optimal model tier (L0-L3) based on:
- Intent classification (L0 router)
- Device capability detection
- Latency requirements
- Privacy preferences (on-device vs cloud)
- Cost optimization

Usage:
    from inference_cascade import CascadeRouter
    router = CascadeRouter()
    result = await router.route("Write a Python function...")
"""
from __future__ import annotations

from .router import CascadeRouter, InferenceTier, RoutingDecision
from .device_profile import DeviceProfile, detect_device_profile
from .model_registry import ModelRegistry, ModelCapability

__all__ = [
    "CascadeRouter",
    "InferenceTier",
    "RoutingDecision",
    "DeviceProfile",
    "detect_device_profile",
    "ModelRegistry",
    "ModelCapability",
]
