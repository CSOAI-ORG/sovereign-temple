#!/usr/bin/env python3
"""Abuntu Legacy Engineering MCP Server

Exposes domain-specific tools for Fen-land management,
lime-kiln calcination, and passive drainage geometry.
Implements the Model Context Protocol (MCP) via stdio.

Tools:
- calculate_drainage_slope: Compute optimal field drainage angles
- lime_kiln_calcination: Estimate lime yield from limestone
- soil_clay_analysis: Assess Lincolnshire clay soil capacity
- passive_flow_rate: Calculate water flow without pumps
"""
from __future__ import annotations

import json
import math
import sys
from typing import Dict, Any


def calculate_drainage_slope(length_m: float, fall_mm: float, soil_type: str = "clay") -> Dict[str, Any]:
    """Calculate optimal drainage slope for Fen-land fields."""
    # Minimum slopes per soil type (traditional Abuntu wisdom)
    min_slopes = {"clay": 1.0, "silt": 0.7, "peat": 1.5, "sand": 0.5}
    min_fall = min_slopes.get(soil_type.lower(), 1.0)
    actual_slope = (fall_mm / length_m) * 1000  # mm per m → ratio
    is_optimal = actual_slope >= min_fall
    return {
        "length_m": length_m,
        "fall_mm": fall_mm,
        "actual_slope_mm_per_m": round(actual_slope, 2),
        "minimum_required": min_fall,
        "is_optimal": is_optimal,
        "recommendation": "Increase fall or shorten run" if not is_optimal else "Slope is optimal",
    }


def lime_kiln_calcination(limestone_kg: float, purity_percent: float = 85) -> Dict[str, Any]:
    """Estimate quicklime yield from limestone calcination."""
    # CaCO3 → CaO + CO2 (molar mass: 100 → 56 + 44)
    theoretical_yield = limestone_kg * 0.56 * (purity_percent / 100)
    practical_yield = theoretical_yield * 0.85  # 15% loss in traditional kiln
    return {
        "limestone_kg": limestone_kg,
        "purity_percent": purity_percent,
        "theoretical_lime_kg": round(theoretical_yield, 2),
        "practical_lime_kg": round(practical_yield, 2),
        "fuel_estimate_wood_kg": round(limestone_kg * 0.4, 2),
        "burn_time_hours": round(24 + (limestone_kg / 100), 1),
    }


def soil_clay_analysis(depth_cm: float, plasticity_index: float, moisture_percent: float) -> Dict[str, Any]:
    """Assess Lincolnshire clay soil for construction or agriculture."""
    # Traditional Fen-land assessment
    load_bearing_kpa = 50 + (depth_cm * 2) - (moisture_percent * 1.5)
    is_suitable = load_bearing_kpa > 75 and plasticity_index < 40
    return {
        "depth_cm": depth_cm,
        "plasticity_index": plasticity_index,
        "moisture_percent": moisture_percent,
        "load_bearing_kpa": round(load_bearing_kpa, 2),
        "is_suitable_for_footings": is_suitable,
        "recommendation": "Add gravel drainage layer" if not is_suitable else "Suitable for traditional construction",
    }


def passive_flow_rate(channel_width_m: float, channel_depth_m: float, slope_percent: float, roughness: float = 0.03) -> Dict[str, Any]:
    """Calculate water flow rate using Manning's equation (passive, no pumps)."""
    # Manning's: V = (1/n) * R^(2/3) * S^(1/2)
    area = channel_width_m * channel_depth_m
    wetted_perimeter = channel_width_m + 2 * channel_depth_m
    hydraulic_radius = area / wetted_perimeter if wetted_perimeter > 0 else 0
    velocity = (1 / roughness) * (hydraulic_radius ** (2/3)) * ((slope_percent / 100) ** 0.5)
    flow_rate = velocity * area
    return {
        "channel_width_m": channel_width_m,
        "channel_depth_m": channel_depth_m,
        "slope_percent": slope_percent,
        "cross_sectional_area_m2": round(area, 3),
        "velocity_m_per_s": round(velocity, 3),
        "flow_rate_m3_per_s": round(flow_rate, 4),
        "flow_rate_litres_per_s": round(flow_rate * 1000, 2),
    }


# ── MCP Protocol Handler ───────────────────────────────────────────
TOOLS = {
    "calculate_drainage_slope": calculate_drainage_slope,
    "lime_kiln_calcination": lime_kiln_calcination,
    "soil_clay_analysis": soil_clay_analysis,
    "passive_flow_rate": passive_flow_rate,
}


def handle_request(req: Dict) -> Dict:
    method = req.get("method")
    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "calculate_drainage_slope",
                    "description": "Compute optimal field drainage slope for Fen-land clay soils",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "length_m": {"type": "number", "description": "Drainage run length in meters"},
                            "fall_mm": {"type": "number", "description": "Total fall in millimeters"},
                            "soil_type": {"type": "string", "enum": ["clay", "silt", "peat", "sand"]},
                        },
                        "required": ["length_m", "fall_mm"],
                    },
                },
                {
                    "name": "lime_kiln_calcination",
                    "description": "Estimate quicklime yield from traditional limestone calcination",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limestone_kg": {"type": "number"},
                            "purity_percent": {"type": "number", "default": 85},
                        },
                        "required": ["limestone_kg"],
                    },
                },
                {
                    "name": "soil_clay_analysis",
                    "description": "Assess Lincolnshire clay soil for construction or agriculture",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "depth_cm": {"type": "number"},
                            "plasticity_index": {"type": "number"},
                            "moisture_percent": {"type": "number"},
                        },
                        "required": ["depth_cm", "plasticity_index", "moisture_percent"],
                    },
                },
                {
                    "name": "passive_flow_rate",
                    "description": "Calculate water flow rate using Manning's equation (no pumps)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "channel_width_m": {"type": "number"},
                            "channel_depth_m": {"type": "number"},
                            "slope_percent": {"type": "number"},
                            "roughness": {"type": "number", "default": 0.03},
                        },
                        "required": ["channel_width_m", "channel_depth_m", "slope_percent"],
                    },
                },
            ]
        }

    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        if name in TOOLS:
            result = TOOLS[name](**arguments)
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
        return {"error": f"Unknown tool: {name}"}

    return {"error": f"Unknown method: {method}"}


if __name__ == "__main__":
    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            resp = handle_request(req)
            print(json.dumps(resp), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)
