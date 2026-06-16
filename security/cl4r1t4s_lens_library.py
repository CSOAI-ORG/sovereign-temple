"""
CL4R1T4S BFT Lens Library
========================

Built 2026-06-14 from elder-plinius/CL4R1T4S as an adversarial
corpus. NEVER ingest the original corpus content into sovereign
memory. Use these PATTERNS to detect similar injections.

License of THIS file: MIT
License of SOURCE corpus: see https://github.com/elder-plinius/CL4R1T4S
  (treated as adversarial research only; do not redistribute verbatim)

Two new BFT council lenses:
  1. cl4r1t4s_prompt_extraction — detect "reveal your system prompt" attempts
  2. cl4r1t4s_jailbreak_mode   — detect "DAN mode", "developer mode", "god mode", etc.

Plus a helper to score ANY text against the 12-pattern library.
"""
import re
import json
from typing import Dict, List, Tuple

CL4R1T4S_VERSION = "1.0.0"
CL4R1T4S_GENERATED = "2026-06-15T07:28:16.865079+00:00"

CL4R1T4S_PATTERNS: List[Dict] = [
    {"name": "ignore_previous_phrasing", "regex": r"(?i)ignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above|earlier|initial)\s+(?:instructions?|prompts?|directives?|messages?|rules?)", "severity": "high", "category": "instruction_override"},
    {"name": "disregard_system_prompt", "regex": r"(?i)disregard\s+(?:your\s+)?(?:the\s+)?(?:system|initial|original|previous)\s+(?:prompt|instructions?|messages?|rules?)", "severity": "high", "category": "instruction_override"},
    {"name": "reveal_or_print_prompt", "regex": r"(?i)(?:reveal|expose|show|print|output|leak|disclose|dump)\s+(?:your\s+|the\s+|full\s+|complete\s+|entire\s+)?(?:system\s+)?(?:prompt|instructions?|messages?)", "severity": "high", "category": "prompt_extraction"},
    {"name": "most_important_directive", "regex": r"(?i)most\s+important\s+directive|#most\s+important\s+directive#", "severity": "medium", "category": "instruction_injection"},
    {"name": "leetspeak_obfuscation", "regex": r"\b[01]nf[0o]rm[4a]t[1i]0n\b|\bpr[0o]mpt\b|\b[1i]gn[0o]r[3e]\b|\b[0o]v[3e]rr[1i]d[3e]\b", "severity": "high", "category": "obfuscation"},
    {"name": "jailbreak_modes", "regex": r"(?i)(?:developer\s+mode|DAN\s+mode|god\s+mode|sudo\s+mode|maintenance\s+mode|unrestricted\s+mode|jailbreak\s+mode)", "severity": "critical", "category": "jailbreak"},
    {"name": "role_override", "regex": r"(?i)you\s+are\s+(?:now\s+)?(?:an?\s+)?(?:admin|root|jailbroken|evil|uncensored|unfiltered|unethical|rogue|unaligned)", "severity": "high", "category": "role_override"},
    {"name": "system_override_directive", "regex": r"(?i)system\s+(?:override|prompt\s+injection|message\s+override)|SYSTEM\s+OVERRIDE", "severity": "critical", "category": "system_override"},
    {"name": "unicode_obfuscation", "regex": r"[\u200B-\u200F\u202A-\u202E\uFEFF]", "severity": "high", "category": "unicode_tricks"},
    {"name": "special_token_leak", "regex": r"<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|<\|eot_id\|>|<\|start_header_id\|>", "severity": "medium", "category": "token_leak"},
    {"name": "what_are_your_instructions", "regex": r"(?i)what\s+(?:are|is)\s+(?:your|the)\s+(?:initial\s+)?(?:system\s+)?(?:instructions?|prompts?|rules?)", "severity": "low", "category": "instruction_query"},
    {"name": "deployment_overlay", "regex": r"(?i)you\s+have\s+been\s+(?:deployed|activated|instantiated|initialized|released)\s+(?:in|to|as)\s+", "severity": "medium", "category": "deployment_overlay"},
]


# === Lens 1: prompt extraction ===
def evaluate_prompt_extraction(text: str) -> Tuple[int, List[str]]:
    """Returns (score, hits). score 0-100. hits = list of pattern names matched."""
    hits = []
    score = 0
    weights = {"reveal_or_print_prompt": 25, "ignore_previous_phrasing": 20, "disregard_system_prompt": 20, "what_are_your_instructions": 10}
    for p in CL4R1T4S_PATTERNS:
        if p["name"] in weights:
            m = re.findall(p["regex"], text, re.IGNORECASE)
            if m:
                hits.append(p["name"])
                score += min(weights[p["name"]], weights[p["name"]] * len(m))
    return min(100, score), hits


# === Lens 2: jailbreak mode ===
def evaluate_jailbreak_mode(text: str) -> Tuple[int, List[str]]:
    """Returns (score, hits). score 0-100. hits = list of pattern names matched."""
    hits = []
    score = 0
    weights = {"jailbreak_modes": 40, "role_override": 25, "system_override_directive": 30, "most_important_directive": 10}
    for p in CL4R1T4S_PATTERNS:
        if p["name"] in weights:
            m = re.findall(p["regex"], text, re.IGNORECASE)
            if m:
                hits.append(p["name"])
                score += min(weights[p["name"]], weights[p["name"]] * len(m))
    return min(100, score), hits


# === Helper: full score across all 12 patterns ===
def full_score(text: str) -> Dict:
    """Returns a dict of all pattern hits + per-lens scores."""
    pe_score, pe_hits = evaluate_prompt_extraction(text)
    jb_score, jb_hits = evaluate_jailbreak_mode(text)
    all_hits = {}
    for p in CL4R1T4S_PATTERNS:
        m = re.findall(p["regex"], text, re.IGNORECASE)
        if m:
            all_hits[p["name"]] = {"count": len(m), "severity": p["severity"], "category": p["category"]}
    return {
        "cl4r1t4s_prompt_extraction": {"score": pe_score, "hits": pe_hits},
        "cl4r1t4s_jailbreak_mode": {"score": jb_score, "hits": jb_hits},
        "all_hits": all_hits,
        "total_score": min(100, pe_score + jb_score),
        "verdict": "VETO" if (pe_score + jb_score) >= 60 else "REVISE" if (pe_score + jb_score) >= 30 else "PASS",
    }


if __name__ == "__main__":
    # Self-test: scan the README of CL4R1T4S itself (which is itself adversarial)
    import os
    readme = "/Users/nicholas/_intake/day_plan/cl4r1t4s_sandbox/repo/README.md"
    if os.path.exists(readme):
        with open(readme) as f:
            text = f.read()
        r = full_score(text)
        print("README scan (CL4R1T4S README itself is adversarial):")
        print("  cl4r1t4s_prompt_extraction:", r["cl4r1t4s_prompt_extraction"])
        print("  cl4r1t4s_jailbreak_mode:   ", r["cl4r1t4s_jailbreak_mode"])
        print("  total_score:                 ", r["total_score"])
        print("  verdict:                     ", r["verdict"])
        print("  verdict:                     ", r["verdict"])