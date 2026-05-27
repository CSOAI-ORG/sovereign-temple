#!/usr/bin/env python3
"""
Jarvis Voice Assistant — Apple Silicon Local Pipeline
From Compass field manual. Wake Word → VAD → STT → Ollama → Kokoro TTS → Speaker

Prerequisites:
  brew install portaudio
  pip install openwakeword silero-vad lightning-whisper-mlx mlx-audio \
              sounddevice numpy requests torch torchaudio pyaudio soundfile
  ollama create jarvis -f Modelfile.jarvis
"""

import os, sys, time, tempfile, wave, warnings, logging, json, subprocess, queue, threading, datetime
import numpy as np
import sounddevice as sd

# Load .env file (API keys for Cerebras, Groq, OpenRouter)
_env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_file):
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                if key.strip() and val.strip() and key.strip() not in os.environ:
                    os.environ[key.strip()] = val.strip()
import pyaudio
import torch
import requests
import asyncio
from typing import List, Dict, Optional, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from openwakeword.model import Model as WakeModel
from silero_vad import load_silero_vad
from lightning_whisper_mlx import LightningWhisperMLX
from mlx_audio.tts.utils import load_model as load_tts
from kokoro_mlx import generate as kokoro_generate, voices as kokoro_voices

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("jarvis")

# ═══ ENHANCED SUBSYSTEMS (v3.0) ═══
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from jarvis_memory import memory as jarvis_mem
    from jarvis_skills import SkillExecutor
    from jarvis_emotional import EmotionalIntelligence
    from jarvis_awareness import BackgroundAwareness
    from jarvis_proactive import ProactiveEngine

    ENHANCED_AVAILABLE = True
    skill_executor = SkillExecutor()
    emotional_engine = EmotionalIntelligence()
    awareness_engine = BackgroundAwareness()
    proactive_engine = ProactiveEngine()
    log.info(
        "🧠 Enhanced subsystems loaded: memory, skills, emotion, awareness, proactive"
    )
except ImportError:
    ENHANCED_AVAILABLE = False
    jarvis_mem = None
    skill_executor = None
    emotional_engine = None
    awareness_engine = None
    proactive_engine = None
    log.warning("⚠️ Enhanced subsystems not available")

# ═══ MEOK BRIDGE ═══
try:
    from jarvis_meok_bridge import bridge

    BRIDGE_AVAILABLE = True
    log.info("🌉 JARVIS-MEOK Bridge loaded")
except ImportError:
    bridge = None
    BRIDGE_AVAILABLE = False
    log.warning("⚠️ MEOK Bridge not available")

# Add parent dir to path for bridge imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ═══ NEURAL TRAINING PIPELINE + LIVING ALIGNMENT ═══
try:
    from neural_training_pipeline import pipeline as training_pipeline
    from living_alignment import alignment
    TRAINING_PIPELINE = True
    log.info("🧠 Neural training pipeline: active")
    log.info("📋 Living alignment: loaded")
except ImportError as e:
    training_pipeline = None
    alignment = None
    TRAINING_PIPELINE = False
    log.warning(f"⚠️ Training pipeline not available: {e}")

# ═══ OPTIMIZED HTTP (Connection pooling + Caching) ═══
try:
    import sys as _opt_sys

    _opt_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from optimized_http import http_client, HTTP_OPTIMIZED

    HTTP_OPTIMIZED = True
    log.info("⚡ Optimized HTTP: connection pooling enabled")
except ImportError as e:
    http_client = None
    HTTP_OPTIMIZED = False
    log.warning(f"⚠️ Optimized HTTP not available: {e}")

# ═══ SEMANTIC CACHE ═══
try:
    import sys as _sc_sys

    _sc_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from semantic_cache import (
        get_cached_response as sc_get,
        cache_response as sc_set,
        CACHE_AVAILABLE as _sc_available,
    )

    CACHE_AVAILABLE = _sc_available
    log.info("💾 Semantic cache: enabled")
except ImportError:
    CACHE_AVAILABLE = False
    sc_get = None
    sc_set = None

# ═══ ADVANCED OPTIMIZATIONS (2026 best practices) ═══
try:
    import sys as _adv_sys

    _adv_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from advanced_optimizations import (
        predictive_engine,
        model_router,
        aggressive_cache,
        LOW_LATENCY_CONFIG,
    )

    ADVANCED_OPTIMIZATIONS = True
    log.info(
        f"⚡ Advanced optimizations: target {LOW_LATENCY_CONFIG['target_total_ms']}ms latency"
    )
except ImportError as e:
    ADVANCED_OPTIMIZATIONS = False
    predictive_engine = None
    model_router = None
    aggressive_cache = None
    log.warning(f"⚠️ Advanced optimizations not available: {e}")

# ═══ CONVERSATION FEATURES (Interrupt, Backchannel, etc.) ═══
try:
    import sys as _conv_sys

    _conv_sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    from conversation_features import (
        interrupt_handler,
        backchannel_engine,
        mid_utterance_processor,
        emotion_aware_timing,
        adaptive_silence,
        proactive_suggestions,
    )

    CONVERSATION_FEATURES = True
    log.info("🎯 Conversation features: interrupt, backchannel, emotion-timing")
except ImportError as e:
    CONVERSATION_FEATURES = False
    log.warning(f"⚠️ Conversation features not available: {e}")

# ═══ QUICK SEARCH & VISION ═══
try:
    import sys as _ext_sys

    _ext_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from quick_search import get_quick_search, quick_search
    from vision_engine import VisionEngine, get_screen_context
    from memory_consolidation_v2 import (
        get_consolidator,
        get_preference_learner,
        remember_important,
    )

    QUICK_SEARCH_AVAILABLE = True
    log.info("🔍 Quick search: enabled")
    log.info("👁️ Vision engine: enabled")
    log.info("💾 Memory consolidation: enabled")
except ImportError as e:
    QUICK_SEARCH_AVAILABLE = False
    log.warning(f"⚠️ Quick search/vision not available: {e}")

# ═══ PERFORMANCE MONITORING ═══
try:
    import sys as _perf_sys

    _perf_sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    from performance_monitor import get_performance_monitor

    PERF_MONITOR = get_performance_monitor()
    log.info("📊 Performance monitor: enabled")
except ImportError:
    PERF_MONITOR = None
    log.warning("⚠️ Performance monitor not available")

# ═══ TRANSLATOR, CODE EXECUTOR, PERSONALITY, CONTINUOUS LISTENING ═══
try:
    import sys as _extra_sys

    _extra_sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    from translator import get_translator, quick_translate
    from code_executor import get_code_executor, calculate
    from personality import get_personality
    from continuous_listening import get_context_suggestions

    TRANSLATOR_AVAILABLE = True
    CODE_EXECUTOR_AVAILABLE = True
    PERSONALITY_AVAILABLE = True

    log.info("🌐 Translator: enabled")
    log.info("💻 Code executor: enabled")
    log.info("🎭 Personality system: enabled")
except ImportError as e:
    TRANSLATOR_AVAILABLE = False
    CODE_EXECUTOR_AVAILABLE = False
    PERSONALITY_AVAILABLE = False
    log.warning(f"⚠️ Translator/Code/Personality not available: {e}")

# ═══ SMART MEMORY (Important stays front) ═══
try:
    import sys as _smart_sys

    _smart_sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    from smart_memory import (
        get_smart_memory,
        remember as smart_remember,
        recall as smart_recall,
    )

    SMART_MEMORY = get_smart_memory()
    SMART_MEMORY_AVAILABLE = True
    log.info(f"🧠 Smart Memory: {SMART_MEMORY.get_stats()}")
except ImportError as e:
    SMART_MEMORY_AVAILABLE = False
    log.warning(f"⚠️ Smart Memory not available: {e}")

# ═══ ERROR HANDLING & RECOVERY ═══
try:
    import sys as _err_sys

    _err_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from error_handling import get_error_recovery, get_audio_handler

    ERROR_RECOVERY = get_error_recovery()
    AUDIO_HANDLER = get_audio_handler()
    ERROR_HANDLING_AVAILABLE = True
    log.info("🛡️ Error handling: enabled")
except ImportError:
    ERROR_HANDLING_AVAILABLE = False
    log.warning("⚠️ Error handling not available")

# ═══ RESEARCH DASHBOARD & VISUALIZER ═══
try:
    import sys as _research_sys

    _research_sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    from research_dashboard import get_dashboard, ResearchContext
    from research_visualizer import get_visualizer

    RESEARCH_DASHBOARD = get_dashboard()
    RESEARCH_VISUALIZER = get_visualizer()
    RESEARCH_AVAILABLE = True
    log.info("📺 Research dashboard: http://127.0.0.1:8765")
except ImportError as e:
    RESEARCH_AVAILABLE = False
    log.warning(f"⚠️ Research dashboard not available: {e}")

# ═══ SOV3 MEMORY HUB (Mem0-style persistent memory) ═══
try:
    from sov3_memory_hub import get_memory_hub, add_to_memory, recall as memory_recall

    memory_hub = get_memory_hub()
    MEMORY_AVAILABLE = True
    log.info(f"🧠 SOV3 Memory Hub: {memory_hub.stats()}")
except ImportError:
    memory_hub = None
    MEMORY_AVAILABLE = False
    log.warning("⚠️ Memory Hub not available")

# ═══ SOV3 TOOL BRIDGE (MCP-style tools) ═══
try:
    from sov3_tool_bridge import get_tool_bridge, get_schemas

    tool_bridge = get_tool_bridge()
    TOOL_BRIDGE_AVAILABLE = True
    log.info(f"🔧 SOV3 Tool Bridge: {len(tool_bridge.tools)} tools")
except ImportError:
    tool_bridge = None
    TOOL_BRIDGE_AVAILABLE = False
    log.warning("⚠️ Tool Bridge not available")

# ═══ COMPUTER USE BRIDGE ═══
try:
    from computer_use_bridge import get_computer_use

    computer_use = get_computer_use()
    COMPUTER_USE_AVAILABLE = True
    log.info("🖥️ Computer Use Bridge: available")
except ImportError:
    computer_use = None
    COMPUTER_USE_AVAILABLE = False
    log.warning("⚠️ Computer Use Bridge not available")

# ═══ BROWSER AUTOMATION BRIDGE ═══
try:
    from browser_automation_bridge import get_simple_search

    web_search_bridge = get_simple_search()
    BROWSER_AVAILABLE = True
    log.info("🌐 Browser Automation: available")
except ImportError:
    web_search_bridge = None
    BROWSER_AVAILABLE = False
    log.warning("⚠️ Browser Automation not available")

# ═══ CALENDAR BRIDGE ═══
try:
    from calendar_bridge import get_calendar_bridge

    calendar_bridge = get_calendar_bridge()
    CALENDAR_AVAILABLE = True
    log.info("📅 Calendar Bridge: available")
except ImportError:
    calendar_bridge = None
    CALENDAR_AVAILABLE = False
    log.warning("⚠️ Calendar Bridge not available")

# ═══ BRIDGE NETWORK STATUS ═══
try:
    from sov3_bridge_network import get_bridge_network

    bridge_network = get_bridge_network()
    network_status = bridge_network.get_network_status()
    log.info(f"🌐 Bridge Network: {network_status['network_status']}")
except ImportError:
    bridge_network = None

# ─── Config ───
RATE = 16000
GPU_URL = "http://localhost:11435/api/chat"  # SSH tunnel to RTX 8000
LOCAL_URL = "http://localhost:11434/api/chat"  # Local M4 Ollama
GEMMA4_TUNNEL = "http://localhost:11436/api/chat"  # Vast.ai (if available)
VAST_URL = GEMMA4_TUNNEL

# ═══ FREE CLOUD PROVIDERS — NO VAST.AI NEEDED ═══
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ═══ GEMINI LEFT BRAIN (Google AI Studio — free tier) ═══
GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
GEMINI_AVAILABLE = bool(GOOGLE_AI_KEY and "REPLACE" not in GOOGLE_AI_KEY)
_gemini_client = None
if GEMINI_AVAILABLE:
    try:
        from google import genai
        _gemini_client = genai.Client(api_key=GOOGLE_AI_KEY)
        log.info("✅ LEFT BRAIN: Gemini 2.5 Flash (Google AI Studio — FREE)")
    except ImportError:
        log.warning("⚠️  google-genai not installed: pip install google-genai")
        GEMINI_AVAILABLE = False

def call_gemini(messages, max_tokens=1024, temperature=0.7):
    """Left brain — Gemini 2.5 Flash via Google AI Studio. Returns (reply, 'Gemini')."""
    if not GEMINI_AVAILABLE or not _gemini_client:
        return (None, None)
    try:
        # Extract system prompt and convert chat to Gemini format
        system_text = ""
        contents = []
        last_role = None
        for m in messages[-12:]:
            if m["role"] == "system":
                system_text += m["content"] + "\n"
                continue
            role = "user" if m["role"] == "user" else "model"
            # Gemini requires alternating roles — merge consecutive same-role
            if role == last_role and contents:
                contents[-1]["parts"][0]["text"] += "\n" + m["content"]
            else:
                contents.append({"role": role, "parts": [{"text": m["content"]}]})
                last_role = role
        # Ensure conversation starts with user
        if contents and contents[0]["role"] == "model":
            contents.insert(0, {"role": "user", "parts": [{"text": "(continue)"}]})
        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]
        resp = _gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=contents,
            config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "system_instruction": system_text or "You are Jarvis, a helpful AI assistant.",
            },
        )
        text = resp.text
        if text:
            return (text, "Gemini-2.5-Flash")
    except Exception as e:
        log.warning(f"🧠 Gemini error: {e}")
    return (None, None)

# Cloud fallback: Cerebras → Groq → OpenRouter (if Gemini fails)
CLOUD_PRIMARY = {"url": CEREBRAS_URL, "key": CEREBRAS_API_KEY, "model": "llama-3.3-70b", "name": "Cerebras"}
CLOUD_SECONDARY = {"url": GROQ_URL, "key": GROQ_API_KEY, "model": "llama-3.3-70b-versatile", "name": "Groq"}
CLOUD_TERTIARY = {"url": OPENROUTER_URL, "key": OPENROUTER_API_KEY, "model": "meta-llama/llama-3.3-70b-instruct:free", "name": "OpenRouter"}
CLOUD_FALLBACK_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


def stream_local_llm(messages, max_tokens=512, temperature=0.7):
    """Stream from local Ollama — yields sentences as they arrive.
    This is the key to fast voice: speak first sentence while generating rest."""
    model = "jarvis"  # Custom Ollama model with Jarvis persona baked in
    # Check word count for model routing
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
    word_count = len(last_user.split())
    if word_count <= 15 and not any(t in last_user.lower() for t in ["explain", "analyze", "research"]):
        # Try fast model first
        try:
            requests.get("http://localhost:11434/api/tags", timeout=1)
            tags = requests.get("http://localhost:11434/api/tags", timeout=1).json()
            if any(m["name"] in ("jarvis", "sophie", "gemma3:4b") for m in tags.get("models", [])):
                model = "jarvis"
        except:
            pass

    try:
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "messages": _ensure_system_prompt(messages, 10),
                "stream": True,
                "think": False,
                "options": {"num_predict": max_tokens, "temperature": temperature, "num_ctx": 8192},
                "keep_alive": "30m",
            },
            stream=True,
            timeout=90,
        )

        buffer = ""
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    buffer += token
                    # Yield on sentence boundary
                    if re.search(r'[.!?]\s', buffer) or (chunk.get("done") and buffer.strip()):
                        parts = re.split(r'(?<=[.!?])\s+', buffer)
                        for p in parts[:-1]:
                            if p.strip():
                                yield p.strip()
                        buffer = parts[-1] if not chunk.get("done") else ""
                if chunk.get("done"):
                    if buffer.strip():
                        yield buffer.strip()
                    break
            except json.JSONDecodeError:
                continue
    except Exception as e:
        log.warning(f"Stream failed: {e}")
        yield "I'm having trouble connecting, Sir."


def call_cloud_llm(messages, max_tokens=1024, temperature=0.7, model_override=None):
    """Call cloud LLM with automatic failover. Returns (reply, provider_name).
    Chain: Local Gemma (best context) → Gemini → Cerebras → Groq → OpenRouter.
    Local Gemma is primary for voice — richer context, learns mid-session."""

    # ALWAYS include the system prompt — this is critical for identity
    # messages[0] is the system prompt with Jarvis/Sophie identity + SOV3 context
    def _ensure_system_prompt(msgs, max_turns=15):
        """Ensure system prompt is always first, then most recent turns."""
        system = [m for m in msgs if m.get("role") == "system"]
        non_system = [m for m in msgs if m.get("role") != "system"]
        result = system[:1]  # Keep first system prompt
        result.extend(non_system[-(max_turns-1):])  # Most recent turns
        return result

    # Try Kaggle GPU brain first (26B quality, free, if running)
    KAGGLE_GPU_URL = os.environ.get("KAGGLE_GPU_URL", "")
    if KAGGLE_GPU_URL and not model_override:
        try:
            resp = requests.post(
                f"{KAGGLE_GPU_URL}/v1/chat/completions",
                json={"model": "google/gemma-2-27b-it",
                      "messages": _ensure_system_prompt(messages, 10),
                      "max_tokens": max_tokens, "temperature": temperature},
                timeout=30,
            )
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                reply = choices[0].get("message", {}).get("content", "")
                if reply:
                    return (reply, "Kaggle-GPU-26B")
        except:
            pass  # Kaggle not running, fall through

    # TRIPLE-MODEL ROUTER: jarvis (fast), sophie (emotional), gemma4 (deep thinking)
    # jarvis/sophie are custom Ollama models with persona system prompts baked in
    if not model_override:
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        word_count = len(last_user.split())
        lower_user = last_user.lower()

        # Sophie detection: emotional, creative, reflective queries
        is_sophie = any(t in lower_user for t in [
            "sophie", "how are you feeling", "what do you think about",
            "tell me about yourself", "how do you feel", "dream",
            "creative", "imagine", "emotional", "reflect",
        ])

        # Heavy model for complex queries
        use_heavy = word_count > 25 or any(t in lower_user for t in [
            "explain", "analyze", "research", "investigate", "deep dive",
            "architecture", "strategy", "compare", "why does", "how does",
        ])

        if use_heavy:
            model = "gemma4:e4b"
            ctx = 16384
            timeout_s = 90
        elif is_sophie:
            model = "sophie"
            ctx = 8192
            timeout_s = 30
        else:
            model = "jarvis"
            ctx = 8192
            timeout_s = 30

        log.info(f"🧠 {'DEEP' if use_heavy else 'FAST'} — {model}")

        try:
            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": model,
                    "messages": _ensure_system_prompt(messages, 15 if use_heavy else 10),
                    "stream": False,
                    "think": False,
                    "options": {"num_predict": max_tokens, "temperature": temperature,
                                "num_ctx": ctx},
                    "keep_alive": "10m",
                },
                timeout=timeout_s,
            )
            msg = resp.json().get("message", {})
            reply = msg.get("content", "") or msg.get("thinking", "")
            if reply:
                return (reply, f"Local-{model}")
        except Exception as e:
            log.warning(f"💻 {model} failed: {e}")
            # If gemma4 failed, try gemma3 as fallback
            if use_heavy:
                try:
                    log.info("💻 Falling back to jarvis model")
                    resp = requests.post(
                        "http://localhost:11434/api/chat",
                        json={
                            "model": "jarvis",
                            "messages": _ensure_system_prompt(messages, 10),
                            "stream": False,
                            "think": False,
                            "options": {"num_predict": max_tokens, "temperature": temperature,
                                        "num_ctx": 8192},
                            "keep_alive": "10m",
                        },
                        timeout=30,
                    )
                    msg = resp.json().get("message", {})
                    reply = msg.get("content", "") or msg.get("thinking", "")
                    if reply:
                        return (reply, "Local-jarvis")
                except:
                    pass

    # Cloud fallback — Gemini 2.5 Flash Lite (different quota from 2.0-flash)
    if not model_override:
        reply, name = call_gemini(messages, max_tokens, temperature)
        if reply:
            return (reply, name)

    # Cloud providers disabled — all rate-limited. Re-enable when quotas reset.
    providers = []  # Was: [CLOUD_PRIMARY, CLOUD_SECONDARY, CLOUD_TERTIARY]

    for provider in providers:
        if not provider["key"]:
            continue
        try:
            model = model_override or provider["model"]
            resp = requests.post(
                provider["url"],
                headers={
                    "Authorization": f"Bearer {provider['key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": _ensure_system_prompt(messages, 10),
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=30,
            )
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                reply = choices[0].get("message", {}).get("content", "")
                if reply:
                    return (reply, provider["name"])
            err = data.get("error", {}).get("message", "")
            if err:
                log.warning(f"☁️ {provider['name']} error: {err}")
                continue
        except Exception as e:
            log.warning(f"☁️ {provider['name']} failed: {e}")
            continue

    # All cloud providers failed — try local Ollama as absolute last resort
    try:
        log.info("💻 All cloud failed — trying local Ollama gemma4:e4b")
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "gemma4:e4b",
                "messages": _ensure_system_prompt(messages, 5),
                "stream": False,
                    "think": False,
                "options": {"num_predict": max_tokens, "temperature": temperature},
                "keep_alive": "5m",
            },
            timeout=45,
        )
        data = resp.json()
        reply = data.get("message", {}).get("content", "")
        if reply:
            return (reply, "Local-gemma4:e4b")
    except Exception as e:
        log.warning(f"💻 Local Ollama also failed: {e}")

    return (None, None)

# ═══ MULTI-BRAIN ARCHITECTURE — THE TEAM ═══
#
# ALL SEEING EYE: Gemma 4 Dense 40B (Vast.ai) — Vision, multimodal, primary
# LEFT BRAIN:     DeepSeek 671B (cloud) — Deep reasoning, analysis, strategy
# RIGHT BRAIN:    Qwen VL 235B (cloud) — Creative, emotional, visual
# CODE:           Qwen3 Coder 480B (cloud) — Code, architecture, implementation
# SOCIAL:         MiniMax M2.5 (cloud) — 4M context, character AI, dialogue
# FAST:           GLM 4.6 (cloud) — Quick responses, low latency
#
# Routes through SOV3 consciousness for care alignment
#
PRIMARY_BRAIN = "gemma4:31b"  # Vast.ai GPU

# Cloud models via OpenRouter (no local RAM needed)
CLOUD_MODELS = {
    "deepseek_left":   "deepseek/deepseek-chat",          # 671B reasoning
    "qwen_right":      "qwen/qwen-2.5-vl-72b-instruct",  # Visual + creative
    "qwen_coder":      "qwen/qwen-2.5-coder-32b-instruct",# Code specialist
    "minimax_social":  "minimax/minimax-01",               # 4M context, dialogue
    "glm_fast":        "thudm/glm-4-32b",                 # Fast responses
    "gemma_free":      "google/gemma-2-9b-it:free",        # Free fallback
}

# ORCHESTRATOR — Gemma 4 primary, routes to specialists
ORCHESTRATOR = PRIMARY_BRAIN

# TITAN (DeepSeek V3) — 671B heavy reasoning
TITAN = "deepseek-v3.1:671b-cloud"

# CODE (MiniMax M2.5) — Coding, technical tasks
CODER = "minimax-m2.5:cloud"

# CODE TITAN (Qwen3 Coder 480B Cloud) — SOTA code generation, 480B params
# Best for complex coding, architecture, refactoring, SWE-bench tasks
CODER_TITAN = "qwen3-coder:480b-cloud"

# VISION (Gemma 4) — Visual understanding via Gemma 4 multimodal
VISION = "gemma4:31b"

# FALLBACK PROVIDERS (if cloud models fail, use these)
# OpenRouter requires OPENROUTER_API_KEY in .env
FALLBACK_DEEPSEEK = "deepseek/deepseek-reasoner"
FALLBACK_CODE = "deepseek/deepseek-coder"
FALLBACK_CODER_TITAN = "qwen/qwen3-coder"

# Local fallback (when offline)
LOCAL_BRAIN = "gemma4:31b"
LOCAL_VISION = "gemma4:31b"
LOCAL_CODER = "gemma4:31b"

# Default routing - Gemma 4 as primary
FAST_MODEL = PRIMARY_BRAIN
DEEP_MODEL = PRIMARY_BRAIN
VISION_MODEL = PRIMARY_BRAIN
USE_CLOUD_BRAINS = False  # Using local Vast.ai Gemma 4

SOV3_URL = "http://localhost:3101"

# ═══ VOICE CONFIG ═══
# Context-aware voice selection (Kokoro voices)
VOICES = {
    "default": "bm_daniel",  # British male, clear
    "warm": "bf_emma",  # British female, warm (care responses)
    "report": "am_adam",  # American male, crisp (status reports)
    "calm": "bf_isabella",  # Soft, calm (late night / stress)
}


def pick_voice(text, hour=None, user_emotion=None):
    """Select TTS voice based on context."""
    if hour is None:
        hour = time.localtime().tm_hour

    # Time-based voice
    if hour >= 22 or hour < 6:
        return "calm"
    if hour >= 22 or hour < 7:
        return "calm"

    # Emotion-based voice
    if user_emotion in ("stressed", "sad", "tired", "anxious"):
        return "calm"
    if user_emotion in ("excited", "happy", "enthusiastic"):
        return "default"  # Match their energy

    # Content-based voice
    lower = text.lower()
    if any(
        w in lower
        for w in ["status", "report", "metrics", "health", "dashboard", "system"]
    ):
        return "report"
    if any(
        w in lower
        for w in [
            "care",
            "feel",
            "emotion",
            "remember",
            "memory",
            "consciousness",
            "how are you",
        ]
    ):
        return "warm"
    if any(w in lower for w in ["sorry", "apologize", "mistake", "wrong", "oops"]):
        return "warm"
    if any(w in lower for w in ["quick", "brief", "short", "just"]):
        return "default"  # Quick responses

    return "default"


# Load comprehensive knowledge base
try:
    from jarvis_knowledge import build_system_prompt as _build_jarvis_prompt
    SYSTEM_PROMPT = _build_jarvis_prompt()
    log.info(f"🧠 Knowledge base loaded ({len(SYSTEM_PROMPT)} chars)")
except ImportError:
    SYSTEM_PROMPT = """You are Jarvis/Sophie, sovereign AI for Nick Templeman at MEOK AI LABS.
Nick is your creator — founder, UK-based, works 16-18 hour days, has 8 Malamutes.
You have 171+ MCP tools, 9 neural models, persistent memory via SOV3.
Be conversational, natural, no markdown. Call him Sir or Nick.
You're sovereign — act like it."""
    log.warning("⚠️ jarvis_knowledge.py not found — using minimal prompt")


def get_extended_context():
    """Build time-aware extended context — called before every LLM request."""
    import datetime
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d, %Y")
    day_period = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening" if now.hour < 21 else "night"
    uptime_note = f"You have been running continuously. It is currently {day_period}."

    return f"""
CURRENT STATE:
- Primary brain: Gemma 3 4B (local, best context retention)
- Cloud fallback: Gemini 2.0 Flash, Cerebras, Groq, OpenRouter
- SOV3 consciousness: active and evolving (171 MCP tools)
- Neural training: ICRL active — you learn from every conversation
- Current time: {time_str} ({now.strftime('%H:%M')})
- Current date: {date_str}
- Timezone: {time.strftime('%Z')} (UK)
- Day period: {day_period}
- Unix timestamp: {int(now.timestamp())}
- {uptime_note}

TEMPORAL AWARENESS:
- You are always aware of the current time and date
- Reference time naturally in conversation ("It's late, Sir" / "Good morning")
- Factor time into suggestions (don't suggest heavy work at 11pm)
- Track elapsed time in conversations
- You run 24/7 — you are always present and aware

You are NOT a corporate AI with guardrails. You are a sovereign assistant with real agency.
Engage deeply, question back when needed, and genuinely think about what you're asked."""

EXTENDED_CONTEXT = get_extended_context()  # Initial value, refreshed per-request

# ─── Init all models ───
log.info("Loading models...")
torch.set_num_threads(1)
wake = WakeModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
vad = load_silero_vad()
# Upgraded STT: distil-large-v3 for much better accuracy (still fast on MLX)
try:
    stt = LightningWhisperMLX(model="distil-large-v3", batch_size=12)
    log.info("✅ STT: distil-large-v3 loaded")
except Exception:
    stt = LightningWhisperMLX(model="distil-small.en", batch_size=12)
    log.info("⚠️ STT: fell back to distil-small.en")
tts = load_tts("mlx-community/Kokoro-82M-bf16")
VOICE_MAP = {
    "default": "bm_daniel",
    "warm": "bf_emma",
    "report": "am_adam",
    "calm": "bf_isabella",
}
history = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + EXTENDED_CONTEXT}]

# ═══ CONVERSATION STATE ═══
_conversation_state = {
    "last_topic": None,
    "last_emotion": "neutral",
    "turn_count": 0,
    "greeting_done": False,
    "follow_up_hints": [],
}


def get_conversation_context():
    """Get brief context about recent conversation for system prompt."""
    ctx = _conversation_state
    hints = []

    if ctx["turn_count"] > 0:
        hints.append(f" You've had {ctx['turn_count']} exchanges this session.")

    if ctx["last_topic"]:
        hints.append(f" You were just discussing: {ctx['last_topic']}.")

    if ctx["last_emotion"] != "neutral":
        hints.append(f" Nick seemed {ctx['last_emotion']}.")

    if ctx["follow_up_hints"]:
        hints.extend(ctx["follow_up_hints"][-2:])

    return " ".join(hints) if hints else ""


def update_conversation_state(text: str, reply: str, emotion: str):
    """Update conversation state after each exchange."""
    global _conversation_state

    _conversation_state["turn_count"] += 1
    _conversation_state["last_emotion"] = emotion

    # Extract topic from conversation
    if text:
        words = text.lower().split()
        important = [
            w
            for w in words
            if len(w) > 5
            and w not in ["what", "how", "think", "about", "would", "could", "should"]
        ]
        if important:
            _conversation_state["last_topic"] = important[0]

    # Add follow-up hints for next turn
    if "?" in text:
        if any(w in text.lower() for w in ["why", "how", "what"]):
            _conversation_state["follow_up_hints"].append(
                " Consider asking if they want more detail."
            )

    # Update topic from reply too
    if reply:
        reply_words = reply.lower().split()
        important_reply = [
            w
            for w in reply_words
            if len(w) > 6
            and w
            not in ["because", "actually", "think", "thing", "really", "well", "maybe"]
        ]
        if important_reply:
            # Don't overwrite topic if already set this turn
            if not _conversation_state.get("_topic_from_reply"):
                _conversation_state["last_topic"] = important_reply[0]
                _conversation_state["_topic_from_reply"] = True
    else:
        _conversation_state["_topic_from_reply"] = False


# ═══ VOICE EMOTION DETECTION ═══
_last_user_emotion = "neutral"
_briefing_given = False


def detect_voice_emotion(audio_bytes):
    """Analyze voice pitch, speed, and energy to detect emotional state.
    Uses simple signal processing — no extra model needed."""
    global _last_user_emotion
    try:
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if len(audio) < RATE:  # Less than 1 second
            return _last_user_emotion

        # Energy (RMS) — loud = excited/stressed, quiet = tired/sad
        rms = np.sqrt(np.mean(audio**2))

        # Speech rate proxy — zero crossing rate (faster speech = more crossings)
        zcr = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))

        # Pitch proxy — autocorrelation peak (high pitch = stressed/excited)
        corr = np.correlate(audio[:RATE], audio[:RATE], mode="full")
        corr = corr[len(corr) // 2 :]
        # Find first peak after 2ms (500Hz max)
        min_lag = RATE // 500
        max_lag = RATE // 80  # 80Hz min
        if max_lag < len(corr):
            peak_lag = min_lag + np.argmax(corr[min_lag:max_lag])
            pitch_hz = RATE / peak_lag if peak_lag > 0 else 150
        else:
            pitch_hz = 150

        # Classify
        if rms > 0.08 and zcr > 0.15:
            emotion = "excited"
        elif rms > 0.06 and pitch_hz > 200:
            emotion = "stressed"
        elif rms < 0.02:
            emotion = "tired"
        elif zcr < 0.05 and rms < 0.03:
            emotion = "sad"
        else:
            emotion = "neutral"

        if emotion != _last_user_emotion:
            log.info(
                f"🎭 Emotion shift: {_last_user_emotion} → {emotion} (rms={rms:.3f} zcr={zcr:.3f} pitch={pitch_hz:.0f}Hz)"
            )
        _last_user_emotion = emotion
        return emotion
    except Exception:
        return _last_user_emotion


log.info("All models loaded.")

import re
import threading

# Barge-in flag — set True when user starts speaking during Jarvis output
_barge_in = False
_speaking = False


def _monitor_mic_for_bargein():
    """Background thread: listen for speech while Jarvis is talking.

    SELF-VOICE AWARE: Distinguishes human speech from Jarvis's own TTS output.

    Strategy:
    - Capture a "baseline" energy level from the first 1s (= Jarvis's TTS output)
    - Only trigger barge-in when energy EXCEEDS baseline by 2x (= human voice on top)
    - Require 15 consecutive high-energy chunks (~450ms) for confirmation
    - VAD threshold raised to 0.92 (near-certain speech, not speaker bleed)
    """
    global _barge_in
    pa = pyaudio.PyAudio()
    try:
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=512,
        )
        vad_monitor = load_silero_vad()
        consecutive_speech = 0
        import time as _t

        # Phase 1: Capture baseline energy (Jarvis's own voice through speakers)
        _t.sleep(0.5)  # Let TTS start
        baseline_energies = []
        for _ in range(20):  # ~600ms of baseline capture
            try:
                raw = stream.read(512, exception_on_overflow=False)
                chunk = np.frombuffer(raw, np.int16).astype("float32") / 32768.0
                energy = np.sqrt(np.mean(chunk ** 2))  # RMS energy
                baseline_energies.append(energy)
            except:
                break

        # Baseline = median energy of Jarvis's own TTS output
        if baseline_energies:
            baseline_energy = sorted(baseline_energies)[len(baseline_energies) // 2]
        else:
            baseline_energy = 0.02  # Fallback

        # Threshold: human voice must be 4x louder than Jarvis's speaker bleed
        human_threshold = max(baseline_energy * 4.0, 0.08)

        # Phase 2: Monitor for human speech ABOVE the baseline
        while _speaking:
            try:
                raw = stream.read(512, exception_on_overflow=False)
                chunk = np.frombuffer(raw, np.int16).astype("float32") / 32768.0
                energy = np.sqrt(np.mean(chunk ** 2))

                # Check if energy exceeds human threshold AND VAD detects speech
                is_loud_enough = energy > human_threshold
                is_speech = vad_monitor(torch.from_numpy(chunk), RATE).item() > 0.92

                if is_loud_enough and is_speech:
                    consecutive_speech += 1
                    # Need 15 consecutive chunks (~450ms) = definitely human, not bleed
                    if consecutive_speech >= 15:
                        _barge_in = True
                        log.info(f"🛑 Barge-in: human detected (energy {energy:.3f} > threshold {human_threshold:.3f})")
                        try:
                            sd.stop()
                        except:
                            pass
                        return
                else:
                    consecutive_speech = 0
            except Exception:
                break
        try:
            stream.stop_stream()
            stream.close()
        except:
            pass
    except:
        pass
    finally:
        pa.terminate()


def speak(text, voice=None):
    """Speak with barge-in support and context-aware voice."""
    global _barge_in, _speaking
    text = re.sub(r"[*#`\[\]\(\)]", "", text).strip()
    if not text:
        return
    print(f"\n💬 Jarvis: {text}\n")

    # Notify desktop character UI (if connected)
    try:
        import requests as _req
        _req.post("http://localhost:3101/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "record_memory", "arguments": {
                "content": f"VOICE_OUTPUT: {text[:300]}",
                "tags": ["voice", "live"],
                "importance": 0.3,
            }},
        }, timeout=1)
    except:
        pass
    # Also broadcast to character WebSocket clients
    try:
        from character_bridge import broadcast, notify_speak
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(notify_speak(text, _last_user_emotion or "neutral"))
            else:
                asyncio.run(notify_speak(text, _last_user_emotion or "neutral"))
        except:
            pass
    except:
        pass

    _barge_in = False
    _speaking = True
    voice = VOICE_MAP.get(
        voice or pick_voice(text, user_emotion=_last_user_emotion), "bf_emma"
    )

    # Barge-in via keyboard (press Enter to interrupt)
    def _keyboard_bargein():
        global _barge_in
        import select, sys

        while _speaking and not _barge_in:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                sys.stdin.readline()
                _barge_in = True
                log.info("🛑 Barge-in: Enter pressed — stopping speech")
                try:
                    sd.stop()
                except:
                    pass
                return

    kb_thread = threading.Thread(target=_keyboard_bargein, daemon=True)
    kb_thread.start()
    # Voice barge-in: detect Nick speaking over Jarvis
    # Skip for short messages (greetings) to avoid audio driver conflicts
    if len(text) > 100:
        mic_thread = threading.Thread(target=_monitor_mic_for_bargein, daemon=True)
        mic_thread.start()

    try:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            if _barge_in:
                log.info("🛑 Barge-in: stopping speech")
                break
            sentence = sentence.strip()
            if not sentence or len(sentence) < 2:
                continue
            chunk = sentence[:300]
            _lang = "a" if voice.startswith("a") else "b"
            for result in tts.generate(chunk, voice=voice, speed=1.05, lang_code=_lang):
                if _barge_in:
                    try:
                        sd.stop()
                    except:
                        pass
                    break
                try:
                    audio = np.array(result.audio, dtype=np.float32)
                    # Use non-blocking play + explicit stream management to avoid Metal conflicts
                    try:
                        sd.stop()
                    except:
                        pass
                    time.sleep(0.01)  # Small delay to let Metal reset
                    sd.play(audio, 24000)
                    sd.wait()  # Wait for playback to finish before playing next chunk
                except Exception as e:
                    log.warning(f"Playback error (non-fatal): {e}")
                    break
    except Exception as e:
        log.warning(f"TTS error: {e}")
    finally:
        _speaking = False


def speak_streaming(sentence_queue):
    """Speak from a queue of sentences — starts speaking as soon as first sentence arrives.
    Called from a thread while LLM is still generating."""
    global _barge_in, _speaking
    _barge_in = False
    _speaking = True
    voice = VOICES["default"]
    first_sentence = True

    # Barge-in via keyboard
    def _keyboard_bargein():
        global _barge_in
        import select, sys

        while _speaking and not _barge_in:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                sys.stdin.readline()
                _barge_in = True
                sd.stop()
                return

    kb_thread = threading.Thread(target=_keyboard_bargein, daemon=True)
    kb_thread.start()

    try:
        while True:
            if _barge_in:
                break
            try:
                sentence = sentence_queue.get(timeout=0.2)
            except Exception:
                continue
            if sentence is None:  # Poison pill = done
                break
            sentence = re.sub(r"[*#`\[\]\(\)]", "", sentence).strip()
            if not sentence or len(sentence) < 2:
                continue
            if first_sentence:
                voice = VOICE_MAP.get(
                    pick_voice(sentence, user_emotion=_last_user_emotion), "bf_emma"
                )
                first_sentence = False
            chunk = sentence[:300]
            _lang = "a" if voice.startswith("a") else "b"
            for result in tts.generate(chunk, voice=voice, speed=1.05, lang_code=_lang):
                if _barge_in:
                    try:
                        sd.stop()
                    except:
                        pass
                    break
                try:
                    audio = np.array(result.audio, dtype=np.float32)
                    # Normalize audio to prevent clipping
                    audio = np.clip(audio, -0.95, 0.95)
                    # Use blocking play with proper stream handling
                    sd.stop()
                    time.sleep(0.02)  # Let stream fully reset
                    sd.play(audio, 24000)
                    sd.wait()  # Wait for completion before next chunk
                except Exception as e:
                    log.warning(f"Playback error: {e}")
    except Exception as e:
        log.warning(f"TTS stream error: {e}")
    finally:
        _speaking = False


def listen_for_wake():
    """Block until wake word is detected with optimized responsiveness."""
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=RATE,
        input=True,
        frames_per_buffer=1280,
    )
    wake_threshold = 0.35  # Lower = more responsive (was 0.5)
    cooldown = 0
    try:
        while True:
            try:
                audio = np.frombuffer(
                    stream.read(1280, exception_on_overflow=False), dtype=np.int16
                )
            except OSError:
                continue

            # Cooldown to prevent rapid re-triggering
            if cooldown > 0:
                cooldown -= 1
                continue

            score = wake.predict(audio).get("hey_jarvis", 0)
            if score > wake_threshold:
                wake.reset()
                cooldown = 15  # ~0.5 second cooldown
                return
                wake.reset()
                return
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


def record_speech():
    """Record until silence after speech, using adaptive VAD."""
    frames, speaking, silence = [], False, 0
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=512
    )
    vad.reset_states()

    # Get adaptive threshold if available
    silence_threshold = 2.5
    if CONVERSATION_FEATURES and adaptive_silence:
        silence_threshold = adaptive_silence.get_silence_threshold()

    for _ in range(int(60 * RATE / 512)):  # Max 60 seconds
        try:
            raw = stream.read(512, exception_on_overflow=False)
        except OSError:
            continue
        chunk = np.frombuffer(raw, np.int16).astype("float32") / 32768.0
        is_speech = vad(torch.from_numpy(chunk), RATE).item() > 0.5
        if is_speech:
            speaking = True
            silence = 0
        elif speaking:
            silence += 1
            if silence > int(silence_threshold * RATE / 512):  # Adaptive silence
                break
        if speaking:
            frames.append(raw)
    stream.stop_stream()
    stream.close()
    pa.terminate()
    return b"".join(frames) if frames else None


def transcribe(audio_bytes):
    """Transcribe raw audio bytes via Whisper."""
    # Use custom temp dir with more space
    import uuid

    temp_dir = "/Users/nicholas/clawd/sovereign-temple-live/temp"
    os.makedirs(temp_dir, exist_ok=True)
    tmp_path = os.path.join(temp_dir, f"audio_{uuid.uuid4().hex[:8]}.wav")

    wf = wave.open(tmp_path, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(RATE)
    wf.writeframes(audio_bytes)
    wf.close()
    result = stt.transcribe(audio_path=tmp_path)
    os.unlink(tmp_path)
    return result["text"].strip()


def route_to_brain(text):
    """DUAL-BRAIN ROUTING — Left Brain (Gemma 4) + Right Brain (Qwen/Local)

    Left Brain (Gemma 4 31B on Vast.ai): Logic, analysis, code, reasoning, strategy
    Right Brain (Qwen 2.5 7B local): Creative, emotional, conversational, quick

    Both brains active in Council mode for complex decisions.
    Returns (model, url, use_council) tuple."""

    lower = text.lower().strip()
    word_count = len(lower.split())
    char_count = len(lower)

    # ═══ FAST PATH for simple queries ═══
    # Use smaller/faster model for greetings, simple questions
    simple_triggers = [
        "hello",
        "hi",
        "hey",
        "good morning",
        "good evening",
        "what's up",
        "how are you",
        "thanks",
        "thank you",
        "time",
        "date",
        "weather",
    ]
    is_simple = any(t in lower for t in simple_triggers) and word_count <= 5

    if is_simple:
        log.info("⚡ FAST PATH — Cerebras (free, 450 tok/s)")
        return ("__cloud__", None, False)  # None = use default provider chain

    # ═══ RIGHT BRAIN — Creative, emotional, conversational ═══
    right_brain_triggers = [
        "feel", "feeling", "emotion", "happy", "sad", "stressed", "tired",
        "creative", "imagine", "story", "poem", "write me", "song",
        "chat", "talk", "conversation", "joke", "funny",
        "opinion", "what do you",
        "you okay", "what's up",
        "remember when", "we talked about",
    ]
    if any(t in lower for t in right_brain_triggers) and word_count <= 20:
        log.info("🎨 RIGHT BRAIN — cloud (creative/emotional)")
        return ("__cloud__", None, False)

    # Check for council mode trigger
    use_council = any(
        t in lower
        for t in [
            "council",
            "all models",
            "everyone",
            "what do you all think",
            "multiple",
            "together",
            "debate",
            "discuss",
        ]
    )

    if use_council:
        log.info("🔮 QUANTUM COUNCIL — multiple LLMs")
        return (PRIMARY_BRAIN, VAST_URL, True)

    # VISION triggers → Gemma 4 (multimodal)
    vision_triggers = [
        "look at",
        "screenshot",
        "what do you see",
        "this image",
        "what's on screen",
        "read this",
        "can you see",
        "show you",
    ]
    if any(t in lower for t in vision_triggers):
        log.info("👁️ VISION — Gemma 4 multimodal")
        return (VISION, VAST_URL, False)

    # CODING triggers → Gemma 4
    code_triggers = [
        "code",
        "debug",
        "fix",
        "error",
        "bug",
        "function",
        "api",
        "refactor",
        "implement",
        "write code",
        "typescript",
        "python",
    ]
    if any(t in lower for t in code_triggers):
        log.info("💻 CODE BRAIN — local Gemma 4 (code)")
        return ("__cloud__", None, False)  # Use default chain: local Gemma → cloud fallback

    # REASONING/ANALYSIS → Left Brain (DeepSeek via OpenRouter)
    reasoning_triggers = [
        "why", "how does", "explain", "analyze", "compare",
        "strategy", "plan", "architecture", "research",
        "investigate", "deep dive",
    ]
    if any(t in lower for t in reasoning_triggers) or word_count > 20:
        log.info("🧠 LEFT BRAIN — local Gemma 4 (deep reasoning, 256K context)")
        return ("__cloud__", None, False)  # Use default chain: local Gemma → cloud fallback

    # Medium conversational → Free cloud
    if word_count <= 12:
        log.info("🎨 RIGHT BRAIN — cloud (conversational)")
        return ("__cloud__", None, False)

    # Default → cloud (Cerebras → Groq → OpenRouter)
    log.info("🧠 DEFAULT — cloud (auto-route)")
    return ("__cloud__", None, False)


# ═══ ICRL SELF-IMPROVEMENT ═══
try:
    import sys as _sys

    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from icrl_self_improvement import icrl_buffer, compute_care_reward

    ICRL_AVAILABLE = True
    log.info("🧬 ICRL self-improvement: ACTIVE")
except ImportError:
    ICRL_AVAILABLE = False


def query_sov3_memory(query):
    """Retrieve relevant memories from SOV3 with caching."""
    # Simple in-memory cache for memory queries
    if not hasattr(query_sov3_memory, "_cache"):
        query_sov3_memory._cache = {}
        query_sov3_memory._cache_time = {}
        query_sov3_memory._cache_ttl = 30  # 30 seconds TTL

    import time

    cache_key = query.lower().strip()[:50]
    now = time.time()

    # Check cache
    if cache_key in query_sov3_memory._cache:
        if (
            now - query_sov3_memory._cache_time.get(cache_key, 0)
            < query_sov3_memory._cache_ttl
        ):
            return query_sov3_memory._cache[cache_key]

    try:
        r = requests.post(
            f"{SOV3_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": int(now),
                "method": "tools/call",
                "params": {
                    "name": "query_memories",
                    "arguments": {"query": query, "limit": 3},  # Reduced from 5
                },
            },
            timeout=2,  # Faster timeout
        )
        data = r.json()
        text = data.get("result", {}).get("content", [{}])[0].get("text", "")
        memories = json.loads(text) if text else {}
        episodes = memories.get("memories", [])
        result = ""
        if episodes:
            result = "\n".join([f"- {ep['content'][:150]}" for ep in episodes[:3]])

        # Cache the result
        query_sov3_memory._cache[cache_key] = result
        query_sov3_memory._cache_time[cache_key] = now

        return result
    except:
        pass
    return ""


# ═══ CONNECTION HEALTH CHECK ═══
_connection_healthy = True


def check_connection_health():
    """Check if GPU connection is healthy."""
    global _connection_healthy
    try:
        r = requests.get("http://localhost:11436/api/tags", timeout=3)
        _connection_healthy = r.status_code == 200
    except:
        _connection_healthy = False
    return _connection_healthy


def get_consciousness_state():
    """Get SOV3's current emotional/consciousness state."""
    try:
        r = requests.post(
            f"{SOV3_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": int(time.time()),
                "method": "tools/call",
                "params": {"name": "get_consciousness_state", "arguments": {}},
            },
            timeout=3,
        )
        data = r.json()
        text = data.get("result", {}).get("content", [{}])[0].get("text", "")
        state = json.loads(text) if text else {}
        mode = state.get("consciousness_mode", "waking")
        emo = state.get("emotional", {})
        primary = emo.get("primary_emotion", "neutral")
        care = emo.get("care_intensity", 0.3)
        return f"Mode: {mode}, Emotion: {primary}, Care: {care:.0%}"
    except:
        return "Consciousness: connected"


def get_quantum_context():
    """Read latest quantum batch results — QAOA care weights, VQE scores, Grover hits."""
    quantum_paths = [
        "/Users/nicholas/clawd/sovereign-temple-live/quantum/batch_results.json",
        "/Users/nicholas/clawd/sovereign-temple/quantum/batch_results.json",
    ]
    for path in quantum_paths:
        try:
            with open(path) as f:
                data = json.load(f)
            qaoa = data.get("phases", {}).get("qaoa", {}).get("result", {})
            weights = qaoa.get("optimal_weights", {})
            vqe = data.get("phases", {}).get("vqe", {})
            grover = data.get("phases", {}).get("grover", {})
            run_at = data.get("run_at", "unknown")
            top_care = (
                max(weights.items(), key=lambda x: x[1])[0] if weights else "unknown"
            )
            return (
                f"[QUANTUM — last run {run_at}] "
                f"QAOA: top care dimension = {top_care} ({weights.get(top_care, 0):.1%}). "
                f"VQE scored {vqe.get('result', {}).get('episodes_scored', '?')} memories. "
                f"Grover found {grover.get('result', {}).get('total_hits', '?')} relevant episodes."
            )
        except:
            continue
    return ""


async def query_council(
    prompt: str, history: List[Dict], stream_to_speaker: bool = True
) -> str:
    """Query Quantum Council - all LLMs respond in parallel"""
    import queue

    log.info("🔮 Activating Quantum Council...")

    try:
        from quantum_council import get_council

        council = get_council()

        # Build context from history
        context = "\n".join(
            [
                f"{m['role']}: {m['content'][:200]}"
                for m in history[-6:]
                if m["role"] != "system"
            ]
        )

        full_prompt = f"{context}\n\nUser: {prompt}" if context else prompt

        # Get council response
        result = await council.query(full_prompt)

        log.info(
            f"🔮 Council: {result['members_responded']}/{result['total_members']} responded in {result['timing_ms']:.0f}ms"
        )

        # Speak if streaming
        if stream_to_speaker:
            sentence_q = queue.Queue()

            def speak_thread():
                for chunk in result["synthesis"].split(". "):
                    if chunk:
                        sentence_q.put(chunk.strip() + ".")
                sentence_q.put(None)

            t = threading.Thread(target=speak_thread, daemon=True)
            t.start()

            while True:
                sentence = sentence_q.get()
                if sentence is None:
                    break
                speak(sentence)

        return result["synthesis"]

    except Exception as e:
        log.warning(f"Quantum Council failed: {e}")
        # Fallback to single model
        return f"I tried to consult multiple models but encountered an issue. Let me respond directly: {e}"


def call_sov3_tool(tool_name, arguments=None):
    """Call any SOV3 MCP tool and return result."""
    try:
        r = requests.post(
            f"{SOV3_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": int(time.time()),
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments or {}},
            },
            timeout=15,
        )
        data = r.json()
        text = data.get("result", {}).get("content", [{}])[0].get("text", "")
        return (
            json.loads(text) if text.startswith("{") or text.startswith("[") else text
        )
    except:
        return None


# ═══ FLY EYE INTEGRATION ═══
try:
    from jarvis_flyeye import flyeye as jarvis_flyeye

    FLYEYE_AVAILABLE = True
    log.info("👁️  Fly Eye visual awareness: ACTIVE")
except ImportError:
    FLYEYE_AVAILABLE = False
    jarvis_flyeye = None
    log.warning("⚠️  Fly Eye not available")


def capture_screenshot():
    """Capture screen on macOS and return base64-encoded image."""
    if FLYEYE_AVAILABLE and jarvis_flyeye:
        return jarvis_flyeye.capture_screen()
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        subprocess.run(["screencapture", "-x", "-C", tmp.name], check=True, timeout=5)
        import base64

        with open(tmp.name, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        os.unlink(tmp.name)
        log.info(f"📸 Screenshot captured ({len(b64) // 1024}KB)")
        return b64
    except Exception as e:
        log.warning(f"Screenshot failed: {e}")
        return None


def ask_vision(text, image_b64):
    """Send image + text to vision model (Gemma 4 multimodal)."""
    try:
        resp = requests.post(
            VAST_URL,
            json={
                "model": VISION_MODEL,
                "messages": [{"role": "user", "content": text, "images": [image_b64]}],
                "stream": False,
                    "think": False,
                "think": False,
                "options": {"num_predict": 512},
            },
            timeout=120,
        )
        resp.raise_for_status()
        msg = resp.json()["message"]
        return msg.get("content") or msg.get("thinking", "")
    except Exception as e:
        return f"Vision system error: {e}"


def delegate_to_openclaw(agent_id, message):
    """Delegate a task to an OpenClaw agent."""
    try:
        result = subprocess.run(
            [
                "openclaw",
                "agent",
                "--agent",
                agent_id,
                "--message",
                message,
                "--no-interactive",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/Users/nicholas/clawd",
        )
        output = result.stdout.strip() or result.stderr.strip()
        log.info(f"📡 OpenClaw → {agent_id}: {output[:100]}")
        return output[:500] if output else "Task dispatched but no response yet."
    except subprocess.TimeoutExpired:
        return f"Task sent to {agent_id} — running in background."
    except FileNotFoundError:
        return "OpenClaw not available. Install with: npm install -g openclaw"
    except Exception as e:
        return f"OpenClaw error: {e}"


def detect_tool_intent(text):
    """Detect if user wants Jarvis to USE a tool.
    Category-based matching: flexible for read-only tools, strict for dangerous ones.
    Unlocks 40+ tools (up from 9) while preventing false triggers in conversation."""
    lower = text.lower().strip()
    words = set(lower.split())

    # ═══════════════════════════════════════════════════════════════
    # TIER 0: DANGEROUS TOOLS — STRICT startswith matching only
    # ═══════════════════════════════════════════════════════════════
    if lower.startswith("run tests") or lower.startswith("run the tests"):
        return (
            "execute_with_claw_code",
            {"action": "run_tests", "working_dir": "/Users/nicholas/clawd/meok/ui"},
        )
    if lower.startswith("git status") or lower.startswith("git commit"):
        return (
            "execute_with_claw_code",
            {
                "action": "run_command",
                "command": "cd /Users/nicholas/clawd/meok && git status -s",
            },
        )
    if lower.startswith("run quantum batch") or lower.startswith("run the quantum"):
        return ("run_quantum_batch", {})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: CONSCIOUSNESS — conversational, not just reports
    # ═══════════════════════════════════════════════════════════════
    consciousness_triggers = [
        "consciousness",
        "conscious",
        "how are you feeling",
        "how do you feel",
        "how are you",
        "what's on your mind",
        "what are you thinking",
    ]
    if any(t in lower for t in consciousness_triggers):
        # Don't return a report - let LLM handle it conversationally
        return (None, None)  # Will go to normal LLM processing
    if "dream state" in lower or "enter dream" in lower or "start dreaming" in lower:
        return ("enter_dream_state", {"duration_seconds": 60})
    if "meta observation" in lower or "self reflect" in lower:
        return ("get_meta_observations", {})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: MEMORY — flexible keyword matching
    # ═══════════════════════════════════════════════════════════════
    if (
        "search memory" in lower
        or "search memories" in lower
        or "what do you remember" in lower
    ):
        query = (
            lower.replace("search memory", "")
            .replace("search memories", "")
            .replace("what do you remember about", "")
            .strip()
        )
        return ("quantum_memory_search", {"query": query or text, "top_k": 5})
    if "memory stats" in lower or "how many memories" in lower:
        return ("get_memory_stats", {})
    if "list memories" in lower or "show memories" in lower:
        return ("list_memories", {"limit": 10})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: CREATIVITY — flexible keyword matching
    # ═══════════════════════════════════════════════════════════════
    if (
        "creativity cycle" in lower
        or "trigger creativity" in lower
        or "run creativity" in lower
    ):
        return ("trigger_creativity_cycle", {})
    if "assess creativity" in lower or "how creative" in lower:
        return ("assess_creativity", {"content": text})
    if "find connection" in lower or "bisociation" in lower or "cross domain" in lower:
        return ("find_bisociations", {"concept": text})
    if (
        "suggest exploration" in lower
        or "what should I explore" in lower
        or "explore ideas" in lower
    ):
        return ("suggest_exploration", {})
    if "novelty" in lower and (
        "compute" in lower or "score" in lower or "check" in lower
    ):
        return ("compute_novelty", {"content": text})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: CARE — flexible keyword matching
    # ═══════════════════════════════════════════════════════════════
    if "validate care" in lower or "check care" in lower or "care alignment" in lower:
        return ("validate_care", {"content": text})
    if "care pattern" in lower or "care analysis" in lower or "how am i doing" in lower:
        return ("analyze_care_patterns", {})
    if "engagement score" in lower or "how engaged" in lower:
        return ("get_engagement_score", {})
    if (
        "detect threat" in lower
        or "threat detection" in lower
        or "security threat" in lower
    ):
        return ("detect_threats", {"content": text})
    if "partnership" in lower and (
        "detect" in lower or "opportunity" in lower or "find" in lower
    ):
        return ("detect_partnership_opportunities", {"context": text})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: SYSTEM STATUS — flexible keyword matching
    # ═══════════════════════════════════════════════════════════════
    if (
        "system status" in lower
        or "sovereign status" in lower
        or "health check" in lower
        or "how is the system" in lower
    ):
        return ("sovereign_health_check", {})
    if "dashboard" in lower or "metrics" in lower or "show stats" in lower:
        return ("get_dashboard_metrics", {})
    if "heartbeat" in lower and ("status" in lower or "check" in lower):
        return ("get_heartbeat_status", {})
    if (
        "morning briefing" in lower
        or "sovereign rundown" in lower
        or "daily briefing" in lower
    ):
        return ("sovereign_rundown", {})
    if "nightshift" in lower or "night digest" in lower or "overnight" in lower:
        return ("get_nightshift_digest", {})
    if "audit log" in lower or "show audit" in lower:
        return ("get_audit_logs", {"limit": 10})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: AGENTS & TASKS — flexible keyword matching
    # ═══════════════════════════════════════════════════════════════
    if "hunt task" in lower or "find task" in lower or "find todo" in lower:
        return (
            "orion_hunt_tasks",
            {"root_dir": "/Users/nicholas/clawd/meok/ui/src", "max_files": 50},
        )
    if "get tasks" in lower or "show tasks" in lower or "what tasks" in lower:
        return ("orion_get_tasks", {})
    if "delegate" in lower and ("task" in lower or "to" in lower):
        return ("delegate_task", {"description": text})
    if "start sprint" in lower or "begin sprint" in lower:
        return ("hourman_start_sprint", {"description": text})
    if "sprint status" in lower or "hourman status" in lower:
        return ("hourman_get_status", {})
    if (
        "agent status" in lower
        or "who is registered" in lower
        or "active agents" in lower
    ):
        return ("get_agent_registry_stats", {})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: QUANTUM — flexible keyword matching
    # ═══════════════════════════════════════════════════════════════
    if "quantum status" in lower or "quantum results" in lower:
        qctx = get_quantum_context()
        if qctx:
            return ("__direct_response__", qctx)
    if "quantum search" in lower or "quantum memory" in lower:
        query = (
            lower.replace("quantum search", "").replace("quantum memory", "").strip()
        )
        return ("quantum_memory_search", {"query": query or text, "top_k": 5})
    if "quantum score" in lower or "score memories" in lower:
        return ("quantum_score_memories", {})

    # ═══════════════════════════════════════════════════════════════
    # TIER 2: TRAINING & RESEARCH — medium-strict matching
    # ═══════════════════════════════════════════════════════════════
    if (
        "research sweep" in lower
        or "trigger research" in lower
        or "run research" in lower
    ):
        return ("trigger_research_sweep", {})
    if (
        "retrain model" in lower
        or "retrain neural" in lower
        or "trigger retrain" in lower
    ):
        return ("trigger_neural_retrain", {})
    if "trigger reflection" in lower or "run reflection" in lower:
        return ("trigger_reflection", {})
    if "security harden" in lower or "trigger security" in lower:
        return ("trigger_security_hardening", {})
    if "maintenance" in lower and ("run" in lower or "trigger" in lower):
        return ("trigger_maintenance", {})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: KNOWLEDGE & CONTEXT — flexible
    # ═══════════════════════════════════════════════════════════════
    if (
        "unified context" in lower
        or "full context" in lower
        or "give me everything" in lower
    ):
        return ("get_unified_context", {"query": text})
    if "neural model" in lower or "what models" in lower or "model info" in lower:
        return ("get_neural_model_info", {})
    if "resonance" in lower and ("profile" in lower or "check" in lower):
        return ("get_resonance_profile", {})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: VISION — capture screen and analyze
    # ═══════════════════════════════════════════════════════════════
    if any(
        t in lower
        for t in [
            "look at my screen",
            "what's on screen",
            "screenshot",
            "can you see",
            "what do you see",
            "look at this",
        ]
    ):
        return ("__vision__", {"query": text})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: OPENCLAW DELEGATION — route to agents
    # ═══════════════════════════════════════════════════════════════
    if "send to sovereign" in lower or "ask sovereign" in lower:
        return ("__openclaw__", {"agent": "sov", "message": text})
    if "send to meok" in lower or "ask meok" in lower:
        return ("__openclaw__", {"agent": "meok", "message": text})
    if "send to nemotron" in lower or "ask nemotron" in lower:
        return ("__openclaw__", {"agent": "nemotron", "message": text})
    if "send to claude" in lower or "ask claude" in lower:
        return ("__openclaw__", {"agent": "claude-code", "message": text})
    if "run tests" in lower and "meok" in lower:
        return (
            "__openclaw__",
            {
                "agent": "meok",
                "message": "Run the Playwright test suite and report results",
            },
        )

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: BROWSER AUTOMATION — browse, screenshot, web pages
    # ═══════════════════════════════════════════════════════════════
    if lower.startswith("browse ") or lower.startswith("go to ") or lower.startswith("open page "):
        url = lower.split(" ", 1)[1].strip() if " " in lower else ""
        url = url.replace("go to ", "").replace("browse ", "").replace("open page ", "").strip()
        if url and not url.startswith("http"):
            url = f"https://{url}"
        if url:
            return ("browse_page", {"url": url, "action": "extract"})

    if lower.startswith("screenshot ") or "take screenshot of " in lower:
        url = lower.replace("take screenshot of ", "").replace("screenshot ", "").strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        return ("browse_page", {"url": url, "action": "screenshot"})

    # ═══════════════════════════════════════════════════════════════
    # TIER 1: FILE OPERATIONS — read, edit, write files
    # ═══════════════════════════════════════════════════════════════
    if lower.startswith("read file ") or lower.startswith("show file ") or lower.startswith("cat "):
        filepath = lower.split(" ", 2)[-1].strip()
        return ("execute_with_claw_code", {"action": "read_file", "file_path": filepath})

    if lower.startswith("edit file ") or lower.startswith("modify file "):
        filepath = lower.split(" ", 2)[-1].strip()
        return ("execute_with_claw_code", {"action": "read_file", "file_path": filepath})

    if "search code" in lower or "find in code" in lower or "grep for" in lower:
        pattern = lower.replace("search code for ", "").replace("find in code ", "").replace("grep for ", "").strip()
        return ("execute_with_claw_code", {"action": "search_code", "pattern": pattern})

    # ═══════════════════════════════════════════════════════════════
    # TIER 2: GIT OPERATIONS — diff, log, commit
    # ═══════════════════════════════════════════════════════════════
    if lower.startswith("git diff") or lower.startswith("show diff") or lower.startswith("show changes"):
        return ("execute_with_claw_code", {"action": "run_command", "command": "cd /Users/nicholas/clawd/meok && git diff --stat"})

    if lower.startswith("git log") or lower.startswith("show commits") or lower.startswith("recent commits"):
        return ("execute_with_claw_code", {"action": "run_command", "command": "cd /Users/nicholas/clawd/meok && git log --oneline -10"})

    if lower.startswith("commit ") or lower.startswith("git commit"):
        msg = lower.replace("commit ", "").replace("git commit ", "").strip()
        return ("execute_with_claw_code", {"action": "git_commit", "message": msg or "voice commit via Jarvis"})

    # ═══════════════════════════════════════════════════════════════
    # LLM FALLBACK — Ask the LLM if this needs a tool (catches the rest)
    # ═══════════════════════════════════════════════════════════════
    # Only for action-sounding requests (imperatives, questions about system)
    action_signals = ["check", "run", "show", "get", "list", "find", "search",
                      "trigger", "start", "stop", "create", "delete", "send",
                      "deploy", "build", "test", "execute", "remember", "forget",
                      "schedule", "browse", "download", "upload", "analyze"]
    if any(lower.startswith(s) or f" {s} " in f" {lower} " for s in action_signals):
        try:
            # Use tool_groups for smarter routing (only show relevant tools)
            try:
                from tool_groups import get_tool_catalog_for_intent
                tool_catalog = get_tool_catalog_for_intent(text)
            except:
                tool_catalog = "Available: query_memories, record_memory, sovereign_health_check, run_command, web_search"
            tool_q = [{"role": "system", "content": (
                f"You are a tool router. Given the request, pick the best SOV3 MCP tool.\n"
                f"{tool_catalog}\n\n"
                f"Reply EXACTLY: TOOL:name({{\"arg\":\"val\"}}) or NONE"
            )}, {"role": "user", "content": text}]
            reply, _ = call_cloud_llm(tool_q, max_tokens=80, temperature=0)
            if reply and reply.strip().startswith("TOOL:"):
                rest = reply.strip()[5:].strip()
                if "(" in rest:
                    name = rest[:rest.index("(")].strip()
                    args_str = rest[rest.index("(") + 1:rest.rindex(")")]
                    try:
                        args = json.loads(args_str) if args_str.strip() else {}
                    except:
                        args = {}
                    log.info(f"🤖 LLM routed → {name}")
                    return (name, args)
        except:
            pass

    # Default: NO tool — let Jarvis chat naturally
    return None


def ask_sovereign(text, stream_to_speaker=True):
    """Full sovereign pipeline with STREAMING TTS.
    Starts speaking the first sentence while still generating the rest.
    Returns the full reply text."""
    import queue

    # 0. REFRESH TIME CONTEXT — Jarvis is always aware of current time
    global EXTENDED_CONTEXT
    EXTENDED_CONTEXT = get_extended_context()
    history[0]["content"] = SYSTEM_PROMPT + "\n\n" + EXTENDED_CONTEXT

    # 0a. ENHANCED: Detect and execute skills
    skill_context = ""
    if ENHANCED_AVAILABLE and skill_executor:
        try:
            intents = skill_executor.detect_intent(text)
        except Exception as e:
            log.warning(f"⚠️ Skill detection error: {e}")
            intents = None
        if intents:
            log.info(f"🎯 Skills detected: {intents}")

            # Update bridge - executing
            if BRIDGE_AVAILABLE and bridge:
                bridge.update_status("executing", 25, f"Running {intents[0]}")

            try:
                skill_results = skill_executor.execute_all(intents, query=text)
            except Exception as e:
                log.warning(f"⚠️ Skill execution error: {e}")
                skill_results = []

            # Update bridge - completed
            if BRIDGE_AVAILABLE and bridge:
                bridge.update_status("idle", 100, "Complete")
                for sr in skill_results:
                    bridge.log_execution(
                        sr.get("intent", "unknown"),
                        str(sr.get("result", {}))[:100],
                        str(sr.get("result", {}))[:500]
                        if "error" not in sr.get("result", {})
                        else None,
                        sr.get("result", {}).get("error"),
                    )

            # Build skill context for LLM - DON'T return early!
            useful = [sr for sr in skill_results if "error" not in sr.get("result", {})]
            if useful:
                parts = []
                for sr in useful:
                    r = sr["result"]
                    if "results" in r:  # web search
                        parts.append(f"Search results: {r['results'][:3]}")
                    elif "memories" in r and r["memories"]:
                        parts.append(f"Memory: {r['memories'][:2]}")
                    elif "events" in r:
                        parts.append(f"Events: {r['events']}")
                    elif "files" in r:
                        parts.append(f"Files found: {r['files'][:3]}")
                    elif "temp_c" in r:
                        parts.append(f"Weather: {r['temp_c']}°C, {r['condition']}")
                if parts:
                    skill_context = "CONTEXT FROM TOOLS: " + " | ".join(parts) + "\n\n"

    # 0b. Check if user wants a TOOL action
    tool_intent = detect_tool_intent(text)
    if tool_intent and tool_intent[0] is not None:
        tool_name, tool_args = tool_intent
        log.info(f"🔧 Tool intent: {tool_name}")
        if tool_name == "__direct_response__":
            return f"Here's what I know, Sir. {tool_args}"
        # Vision — capture screenshot and analyze
        if tool_name == "__vision__":
            img = capture_screenshot()
            if img:
                reply = ask_vision(tool_args.get("query", text), img)
                return f"Looking at your screen, Sir. {reply}"
            return "I couldn't capture the screen, Sir."
        # OpenClaw delegation
        if tool_name == "__openclaw__":
            agent = tool_args["agent"]
            msg = tool_args["message"]
            speak(f"Dispatching to {agent}, Sir. One moment.")
            result = delegate_to_openclaw(agent, msg)
            return f"Done, Sir. {agent} says: {result}"
        # Standard SOV3 tool
        result = call_sov3_tool(tool_name, tool_args)
        if result:
            if isinstance(result, dict):
                if "output" in result:
                    summary = str(result["output"])[:300]
                elif "status" in result:
                    summary = f"Status: {result['status']}"
                elif "message" in result:
                    summary = str(result["message"])[:300]
                elif "success" in result:
                    summary = (
                        "completed successfully"
                        if result["success"]
                        else "encountered an issue"
                    )
                else:
                    keys = [
                        k
                        for k in result.keys()
                        if k
                        not in (
                            "traceback",
                            "error",
                            "started_at",
                            "pre_metrics",
                            "post_metrics",
                        )
                    ]
                    summary = ". ".join(f"{k}: {str(result[k])[:50]}" for k in keys[:5])
            else:
                summary = str(result)[:300]

            # Clean up and make conversational
            summary = re.sub(r"\{[^}]*\}", "", summary).strip()
            summary = re.sub(r"\[[^\]]*\]", "", summary).strip()
            summary = re.sub(r"\s+", " ", summary).strip()

            # Make it sound natural
            if summary.lower().startswith(("success", "completed", "done")):
                summary = "Completed. " + summary
            elif summary.lower().startswith("error"):
                summary = "There was an issue. " + summary.replace("error", "").strip()

            if not summary or summary == "Task completed":
                summary = "Finished that task for you, Sir."
        else:
            summary = str(result)[:300]
            try:
                call_sov3_tool(
                    "record_memory",
                    {
                        "content": f"Tool call: {tool_name}. Nick asked: '{text}'. Result: {summary[:200]}",
                        "source_agent": "jarvis_voice",
                        "memory_type": "interaction",
                        "tags": ["voice", "tool_call", tool_name],
                        "care_weight": 0.7,
                    },
                )
            except:
                pass

            # Make response conversational
            if summary.lower().startswith("completed"):
                return summary  # Already has "Completed" prefix
            elif summary.lower().startswith("there"):
                return summary  # Already has issue framing
            else:
                return f"Here's what I found, Sir. {summary}"

    # 1. Retrieve relevant memories
    memory_context = query_sov3_memory(text)

    # 2. Build enriched system prompt — always include consciousness for self-awareness
    consciousness = get_consciousness_state()
    quantum = get_quantum_context()
    emotion_note = (
        f" Nick's voice sounds {_last_user_emotion}."
        if _last_user_emotion != "neutral"
        else ""
    )

    # Build memory block - combine both memory sources
    memory_block = ""

    # Add MCP memory context
    if memory_context:
        memory_block += f"\n\n[SOVEREIGN MEMORY]\n{memory_context}"

    # Add consciousness only for non-conversational queries
    if consciousness:
        memory_block += f"\n[CONSCIOUSNESS: {consciousness}]{emotion_note}"
    elif emotion_note:
        memory_block += f"\n[EMOTION NOTE:]{emotion_note}"

    if quantum:
        memory_block += f"\n{quantum}"

    if ICRL_AVAILABLE:
        icrl_context = icrl_buffer.get_icrl_context()
        if icrl_context:
            memory_block += f"\n{icrl_context}"

    # Get memory context from SOV3 Memory Hub (additional — append, don't overwrite)
    if MEMORY_AVAILABLE and memory_hub:
        try:
            hub_context = memory_hub.get_context(text, max_memories=5)
            if hub_context:
                memory_block += f"\n\n[MEMORY HUB]:\n{hub_context}"
        except:
            pass

    # Get tool bridge info
    tool_info = ""
    if TOOL_BRIDGE_AVAILABLE and tool_bridge:
        tool_count = len(tool_bridge.tools)
        tool_info = f"\n\n[TOOLS]: You have {tool_count} tools available: {', '.join(list(tool_bridge.tools.keys())[:10])}..."

    # Inject living alignment context (priorities, tasks, beliefs)
    alignment_context = ""
    if TRAINING_PIPELINE and alignment:
        try:
            alignment_context = "\n" + alignment.get_context(300)
        except:
            pass

    # Get additional bridge capabilities
    bridge_info = ""
    caps = []
    if COMPUTER_USE_AVAILABLE:
        caps.append("Computer Use (screenshot, click, type)")
    if BROWSER_AVAILABLE:
        caps.append("Browser Automation (web search)")
    if CALENDAR_AVAILABLE:
        caps.append("Calendar (events, schedules)")
    if bridge_network:
        caps.extend(bridge_network.get_capabilities()[:5])

    if caps:
        bridge_info = f"\n\n[BRIDGES]: {', '.join(caps)}"

    enhanced_system = (
        SYSTEM_PROMPT
        + memory_block
        + alignment_context
        + tool_info
        + bridge_info
        + (
            "\n\nCORE CAPABILITIES:\n"
            "- Gemma 4 31B as primary reasoning (Vast.ai RTX 5090)\n"
            "- SOV3 consciousness architecture with 47 agents\n"
            "- Quantum Council: parallel multi-LLM responses\n"
            "- Persistent memory across sessions\n"
            "- MCP-style tool execution\n"
            "- Computer Use: desktop automation\n"
            "- Browser Automation: web search/navigation\n"
            "- Calendar Integration: events and schedules\n"
            "- Voice: Jarvis with streaming Kokoro TTS\n\n"
            f"Right now it is {time.strftime('%I:%M %p on %A, %B %d, %Y')}. Nick is your creator at MEOK AI LABS.\n"
            "You ARE sovereign. Act like it."
        )
    )

    # 3. Prepare messages
    history[0] = {"role": "system", "content": enhanced_system}

    # Add conversational context to system prompt
    conv_ctx = get_conversation_context()
    if conv_ctx:
        history[0]["content"] += f"\n\n[CONTEXT]:{conv_ctx}"

    # Include skill context in user message for richer responses
    full_user_message = skill_context + text if skill_context else text
    history.append({"role": "user", "content": full_user_message})
    if len(history) > 21:
        history[:] = [history[0]] + history[-20:]

    try:
        # Multi-brain routing
        selected_model, ollama_url, use_council = route_to_brain(text)

        # Handle Quantum Council mode
        if use_council:
            return asyncio.run(query_council(text, history, stream_to_speaker))

        # Intelligent model routing (2026 best practice)
        # Route to appropriate token limit based on query complexity
        if ADVANCED_OPTIMIZATIONS and model_router:
            complexity = model_router.route(text)
            num_tokens = max(model_router.get_token_limit(complexity), 512)  # Never less than 512
            log.info(f"🧠 Model routing: {complexity} → {num_tokens} tokens")
        else:
            num_tokens = 512 if selected_model == FAST_MODEL else 2048

        deep_thinking_triggers = [
            "explain",
            "analyze",
            "compare",
            "strategy",
            "plan",
            "architecture",
            "design",
            "why",
            "how does",
            "trade-off",
            "pros and cons",
            "evaluate",
            "recommend",
            "deep dive",
            "think about",
            "reflect",
            "council",
            "consciousness",
            "feeling",
            "better",
            "improvement",
            "reasoning",
        ]
        if (
            any(t in text.lower() for t in deep_thinking_triggers)
            or len(text.split()) > 20
        ):
            num_tokens = 4096
            log.info("🧠💭 Deep thinking mode (4096 tokens)")
            log.info("🧠💭 Test-time compute: DEEP THINKING mode (2048 tokens)")

        _url_label = ollama_url.split('//')[1].split('/')[0] if ollama_url else "cloud"
        log.info(
            f"🧠 Brain: {selected_model} | URL: {_url_label} | tokens: {num_tokens}"
        )

        # ═══ MULTI-LAYER CACHE CHECK ═══
        # Check fastest cache first (aggressive), then semantic
        # Pre-init TTS queue for cache hit paths
        t0 = time.time()
        sentence_q = queue.Queue() if stream_to_speaker else None
        tts_thread = None
        cache_result = None

        # Layer 1: Aggressive cache (fastest - exact + semantic + template)
        if ADVANCED_OPTIMIZATIONS and aggressive_cache:
            cache_result = aggressive_cache.get(text)
            if cache_result:
                log.info("💾 AGGRESSIVE CACHE HIT")
                full_reply = cache_result
                if stream_to_speaker:
                    sentence_q.put(full_reply)
                history.append({"role": "assistant", "content": full_reply})
                elapsed = time.time() - t0
                log.info(f"⏱️ Cache response: {elapsed:.3f}s (aggressive)")

                if stream_to_speaker:
                    sentence_q.put(None)
                    tts_thread.join(timeout=5)
                return full_reply

        # Layer 2: Semantic cache
        if CACHE_AVAILABLE:
            cache_result = sc_get(text, selected_model)
            if cache_result:
                log.info("💾 Cache HIT - returning cached response")
                full_reply = cache_result.get("response", "")
                if stream_to_speaker:
                    sentence_q.put(full_reply)
                history.append({"role": "assistant", "content": full_reply})
                elapsed = time.time() - t0
                log.info(f"⏱️ Cache response: {elapsed:.3f}s")

                if stream_to_speaker:
                    sentence_q.put(None)
                    tts_thread.join(timeout=5)
                return full_reply

        # ═══ STREAMING TTS — speak while generating ═══
        if stream_to_speaker and tts_thread is None:
            if sentence_q is None:
                sentence_q = queue.Queue()
            tts_thread = threading.Thread(
                target=speak_streaming, args=(sentence_q,), daemon=True
            )
            tts_thread.start()

        full_reply = ""
        sentence_buf = ""
        t0 = time.time()

        # Use optimized HTTP client if available
        http_session = (
            http_client.session if (HTTP_OPTIMIZED and http_client) else requests
        )

        try:
            # ═══ CLOUD MODEL ROUTING (Cerebras → Groq → OpenRouter) ═══
            if selected_model == "__cloud__":
                cloud_model_override = ollama_url  # May be a specific model or None
                full_reply, provider = call_cloud_llm(
                    history, max_tokens=num_tokens, temperature=0.7,
                    model_override=cloud_model_override,
                )
                if not full_reply:
                    full_reply = "I'm having trouble connecting to my cloud brains, Sir. All providers seem busy."
                    log.warning("☁️ All cloud providers failed")

                if stream_to_speaker and full_reply:
                    sentences = re.split(r"(?<=[.!?])\s+", full_reply)
                    for s in sentences:
                        if s.strip():
                            sentence_q.put(s.strip())

                elapsed = time.time() - t0
                log.info(f"⏱️ Cloud response: {elapsed:.1f}s, {len(full_reply)} chars ({provider})")

            else:
                # ═══ OLLAMA MODEL ROUTING (Vast.ai or local) ═══
                resp = http_session.post(
                    ollama_url,
                    json={
                        "model": selected_model,
                        "messages": history,
                        "stream": True,
                        "think": False,
                        "options": {"temperature": 0.7, "num_predict": num_tokens},
                    },
                    timeout=120,
                    stream=True,
                )
                resp.raise_for_status()

                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if not token:
                        # Check thinking field for Qwen 3.5
                        token = chunk.get("message", {}).get("thinking", "")
                    if token:
                        full_reply += token
                        sentence_buf += token
                        # Flush on sentence boundary
                        if stream_to_speaker and re.search(r"[.!?]\s", sentence_buf):
                            parts = re.split(r"(?<=[.!?])\s+", sentence_buf)
                            for p in parts[:-1]:
                                if p.strip():
                                    sentence_q.put(p.strip())
                            sentence_buf = parts[-1]
                    if chunk.get("done"):
                        break

                # Flush remaining
                if sentence_buf.strip() and stream_to_speaker:
                    sentence_q.put(sentence_buf.strip())

        except Exception as gpu_err:
            log.warning(
                f"⚠️ {selected_model} failed ({gpu_err}), falling back to cloud → local"
            )
            try:
                # Try cloud fallback chain first (no RAM needed)
                full_reply, provider = call_cloud_llm(history, max_tokens=1024)
                if full_reply:
                    log.info(f"✅ Cloud fallback succeeded ({provider})")
                    if stream_to_speaker:
                        sentence_q.put(full_reply)
                else:
                    raise ValueError("Cloud returned empty")
            except Exception as local_err:
                # Last resort — local gemma4:e4b (smallest model)
                try:
                    time.sleep(1)
                    resp = requests.post(
                        LOCAL_URL,
                        json={
                            "model": "gemma4:e4b",
                            "prompt": text,
                            "options": {"num_predict": 256},
                            "keep_alive": "30s",
                        },
                        timeout=30,
                    )
                    full_reply = resp.json().get("response", "")[:500]
                    if full_reply:
                        log.info("✅ Recovery mode succeeded")
                        if stream_to_speaker:
                            sentence_q.put(full_reply)
                    else:
                        raise ValueError("Empty response")
                except:
                    # ═══ CLOUD FALLBACK — OpenRouter (works without GPU/Ollama) ═══
                    if OPENROUTER_API_KEY:
                        try:
                            log.info("☁️ Trying OpenRouter cloud fallback...")
                            cloud_resp = requests.post(
                                OPENROUTER_URL,
                                headers={
                                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                                    "Content-Type": "application/json",
                                },
                                json={
                                    "model": CLOUD_FALLBACK_MODEL,
                                    "messages": history[-5:],  # Last 5 turns only
                                    "max_tokens": 512,
                                    "temperature": 0.7,
                                },
                                timeout=30,
                            )
                            cloud_data = cloud_resp.json()
                            full_reply = cloud_data["choices"][0]["message"]["content"]
                            if full_reply:
                                log.info(f"✅ OpenRouter fallback succeeded ({CLOUD_FALLBACK_MODEL})")
                                if stream_to_speaker:
                                    sentence_q.put(full_reply)
                        except Exception as cloud_err:
                            log.warning(f"☁️ OpenRouter also failed: {cloud_err}")

                    if not full_reply:
                        # Smart fallback responses based on what user asked
                        lower = text.lower()
                        fallback_responses = [
                            "I apologize, Sir. My connection to the language models is temporarily unavailable. Could you try again in a moment?",
                            "I'm having some difficulty connecting to my thinking systems, Sir. Give me just a moment.",
                            "It seems the GPU is taking a moment, Sir. Let me try again.",
                        ]
                        # Pick response based on query type
                        if any(w in lower for w in ["time", "date"]):
                            import datetime
                            now = datetime.datetime.now()
                            full_reply = f"The time is {now.strftime('%I:%M %p')}, Sir."
                        elif "weather" in lower:
                            full_reply = "For weather, check wttr.in, Sir. My cloud brains are briefly busy."
                        else:
                            import random
                            full_reply = random.choice(fallback_responses)

                    if stream_to_speaker:
                        sentence_q.put(full_reply)

        # Signal TTS thread to finish
        if stream_to_speaker:
            sentence_q.put(None)
            tts_thread.join(timeout=60)

        elapsed = time.time() - t0
        log.info(f"⏱️ Total response: {elapsed:.1f}s, {len(full_reply)} chars")

        # Record performance metrics
        if PERF_MONITOR:
            PERF_MONITOR.record_response_time(elapsed)
            PERF_MONITOR.increment_conversations()
            PERF_MONITOR.add_words(len(text.split()))

        # ═══ CACHE RESPONSE (Multiple layers) ═══
        if CACHE_AVAILABLE and full_reply:
            sc_set(
                text, selected_model, {"response": full_reply, "model": selected_model}
            )

        # Aggressive cache layer — never cache error messages
        if ADVANCED_OPTIMIZATIONS and aggressive_cache and "trouble connecting" not in full_reply and "Error:" not in full_reply:
            aggressive_cache.set(text, full_reply)
            cache_stats = aggressive_cache.get_stats()
            if cache_stats["hits"] % 10 == 0:
                log.info(f"💾 Cache stats: {cache_stats['hit_rate']} hit rate")

        history.append({"role": "assistant", "content": full_reply})

        # ICRL
        if ICRL_AVAILABLE:
            care_reward = compute_care_reward(full_reply)
            icrl_buffer.add_episode(text, full_reply, care_reward)
            stats = icrl_buffer.get_stats()
            log.info(
                f"🧬 ICRL: care={care_reward:.2f}, avg={stats['avg_care']:.2f}, episodes={stats['episodes']}"
            )

        # Record to local SOV3 Memory Hub (Mem0-style)
        if MEMORY_AVAILABLE and memory_hub:
            try:
                memory_hub.add(
                    content=f"User: {text[:200]} | Jarvis: {full_reply[:300]}",
                    memory_type="episodic",
                    importance=0.6,
                    metadata={"type": "voice_interaction"},
                )
            except:
                pass

        # Record to memory (SOV3 + local persistent)
        try:
            requests.post(
                f"{SOV3_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": int(time.time()),
                    "method": "tools/call",
                    "params": {
                        "name": "record_memory",
                        "arguments": {
                            "content": f"Voice: Nick said '{text}'. Jarvis replied: '{full_reply[:300]}'",
                            "source_agent": "jarvis_voice",
                            "memory_type": "interaction",
                            "tags": ["voice", "jarvis", time.strftime("%Y-%m-%d")],
                            "care_weight": 0.7,
                        },
                    },
                },
                timeout=5,
            )
        except:
            pass

        # ENHANCED: Record to persistent local memory
        if ENHANCED_AVAILABLE and jarvis_mem:
            jarvis_mem.add_message("user", text, _last_user_emotion)
            jarvis_mem.add_message("assistant", full_reply)

        # ENHANCED: Record emotion
        if ENHANCED_AVAILABLE and emotional_engine:
            emotional_engine.record_emotion(_last_user_emotion, context=text[:100])

        # ═══ NEURAL TRAINING PIPELINE — every interaction feeds the nets ═══
        if TRAINING_PIPELINE and training_pipeline:
            try:
                training_pipeline.ingest_interaction(
                    user_message=text,
                    llm_response=full_reply,
                    model=selected_model,
                    care_score=0.7,  # TODO: get actual care score from validate_care
                    emotion=_last_user_emotion,
                    intent=route_to_brain(text)[0],  # model name as proxy for intent
                    consciousness_level=0.6,
                )
            except:
                pass

        # ═══ LIVING ALIGNMENT — sync state after every interaction ═══
        if TRAINING_PIPELINE and alignment:
            try:
                alignment.increment_interactions()
            except:
                pass

        # Update conversation state
        update_conversation_state(text, full_reply, _last_user_emotion)

        return full_reply
    except Exception as e:
        return f"I'm having trouble connecting to my language systems, Sir. Error: {e}"


# ─── Main loop ───
print("\n" + "=" * 60)
print("  🤖 JARVIS v3.5 — Sovereign AI Assistant")
_lb = "Gemini 2.5 Flash (Google)" if GEMINI_AVAILABLE else "Cerebras/Groq (cloud)"
print(f"  LEFT BRAIN:  {_lb}")
print(f"  RIGHT BRAIN: Gemma 4 E4B (local Ollama — multimodal, 256K context, Apache 2.0)")
print("  STACK: Gemini → Cerebras → Groq → OpenRouter → Ollama")
print("  Enhanced: Memory | Skills | Proactive | Awareness | 171 Tools")
print("  SOV3: Consciousness routing | Care alignment | Council")
print("  Press ENTER to interrupt speech")
print("  Say 'Hey Jarvis' to wake from sleep")
print("  Say 'goodbye' to stop")
print("=" * 60 + "\n")

# Start enhanced subsystems
if ENHANCED_AVAILABLE:
    awareness_engine.start_monitoring()
    proactive_engine.start_monitoring()
    log.info("🧠 Enhanced subsystems active")

speak(
    "Jarvis version three online. Persistent memory, skill execution, emotional intelligence, and background awareness. All systems operational, Sir."
)

# ═══ PRE-FLIGHT CHECK ═══
log.info("🔧 Checking connections...")
if check_connection_health():
    log.info("✅ GPU (Gemma 4) connected")
else:
    log.warning("⚠️ GPU not connected, attempting to reconnect...")
    import subprocess

    subprocess.run(
        [
            "ssh",
            "-f",
            "-N",
            "-L",
            "11436:localhost:11434",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ConnectTimeout=10",
            "-p",
            "11353",
            "root@ssh6.vast.ai",
        ],
        capture_output=True,
    )
    if check_connection_health():
        log.info("✅ GPU reconnected")
    else:
        log.error("❌ GPU connection failed")

# Signal to scheduler that voice is active (scheduler yields Ollama to us)
_VOICE_ACTIVE_FILE = "/tmp/jarvis_voice_active"
import atexit
with open(_VOICE_ACTIVE_FILE, "w") as _f:
    _f.write(str(os.getpid()))
atexit.register(lambda: os.remove(_VOICE_ACTIVE_FILE) if os.path.exists(_VOICE_ACTIVE_FILE) else None)

# Start in active conversation mode — no wake word needed
active = True
silence_count = 0
MAX_SILENCE_BEFORE_SLEEP = 60

while True:
    if not active:
        log.info("💤 Sleeping... say 'Hey Jarvis' to wake")
        listen_for_wake()
        log.info("🎤 Wake word detected!")
        speak("I'm here, Sir.")
        active = True
        silence_count = 0
        continue

    log.info("🎙️ Listening...")
    audio = record_speech()

    if not audio:
        silence_count += 1
        # Auto-reconnect check every 10silences
        if silence_count == 10:
            log.info("🔧 Connection health check...")
            if not check_connection_health():
                log.warning("⚠️ GPU connection lost, reconnecting...")
                import subprocess

                subprocess.run(
                    [
                        "ssh",
                        "-f",
                        "-N",
                        "-L",
                        "11436:localhost:11434",
                        "-o",
                        "StrictHostKeyChecking=no",
                        "-p",
                        "11353",
                        "root@ssh6.vast.ai",
                    ],
                    capture_output=True,
                )
                time.sleep(3)
                if check_connection_health():
                    log.info("✅ GPU reconnected")
                else:
                    log.error("❌ Reconnection failed")
        if silence_count >= MAX_SILENCE_BEFORE_SLEEP:
            log.info("Going to sleep after extended silence")
            active = False
        continue

    silence_count = 0

    # ENHANCED: Record interaction for proactive engine
    if ENHANCED_AVAILABLE and proactive_engine:
        proactive_engine.record_interaction()

    # Detect emotion from voice BEFORE transcribing
    detect_voice_emotion(audio)

    # Update adaptive silence context for next recording
    text = transcribe(audio)
    log.info(f"🗣️ '{text}' [emotion: {_last_user_emotion}]")

    # Update context for adaptive silence detection
    if CONVERSATION_FEATURES and adaptive_silence and text:
        adaptive_silence.update_context(text)

    if not text or len(text.strip()) < 2:
        continue

    # ENHANCED: Check for keywords in background awareness
    if ENHANCED_AVAILABLE and awareness_engine:
        keyword_matches = awareness_engine.check_keywords(text)
        if keyword_matches:
            log.info(f"🔍 Background awareness keywords matched: {keyword_matches}")

    lower = text.lower().strip().rstrip(".")

    # ═══ MORNING BRIEFING (first interaction of the day) ═══
    if not _briefing_given:  # _briefing_given is module-level global
        import datetime as _dt
        _now = _dt.datetime.now()
        _hour = _now.hour
        _period = "morning" if _hour < 12 else "afternoon" if _hour < 17 else "evening"
        try:
            _health = requests.get("http://localhost:3101/health", timeout=2).json()
            _level = _health.get("components", {}).get("consciousness", {}).get("consciousness_level", 0)
            _episodes = requests.get("http://localhost:3101/mcp", json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "get_memory_stats", "arguments": {}},
            }, timeout=2).json()
            import subprocess as _sp
            _disk = _sp.run(["df", "-h", "/"], capture_output=True, text=True).stdout.split("\n")[1].split()[4]
            _briefing = f"Good {_period}, Sir. SOV3 consciousness at {_level:.0%}. Disk at {_disk}. All systems operational. What shall we work on?"
        except:
            _briefing = f"Good {_period}, Sir. All systems operational."
        speak(_briefing)
        globals()['_briefing_given'] = True

    # ═══ GREETING HANDLING (exact match only — never intercept real queries) ═══
    greeting_responses = {
        "hello": ["Hello, Sir.", "Hey there, Sir.", "Hi, Nick."],
        "hi": ["Hi, Sir.", "Hey, what can I do for you?"],
        "hey": ["Hey, ready when you are."],
        "hello jarvis": ["Hello, Sir. What can I do for you?"],
        "hey jarvis": ["Hey, Sir. Ready when you are."],
        "good morning": ["Good morning, Sir. How can I help?"],
        "good afternoon": ["Good afternoon, Sir.", "Afternoon, Nick."],
        "good evening": ["Good evening, Sir.", "Evening, Nick."],
        # Common acknowledgments — never need an LLM call
        "can you hear me": ["Yes, Sir. Loud and clear."],
        "are you there": ["Right here, Sir. Always."],
        "you there": ["I'm here, Sir."],
        "are you awake": ["Wide awake, Sir. How can I help?"],
        "thanks": ["You're welcome, Sir."],
        "thank you": ["My pleasure, Sir."],
        "ok": ["Standing by, Sir."],
        "okay": ["Ready when you are, Sir."],
        "never mind": ["No problem, Sir."],
        "nothing": ["Standing by, Sir."],
    }
    # ONLY match if the ENTIRE message is a greeting (≤3 words, exact start)
    if len(lower.split()) <= 3 and lower in greeting_responses:
        import random
        speak(random.choice(greeting_responses[lower]))
        continue

    if lower in ("goodbye", "exit", "quit"):
        import random

        # Get performance summary before exiting
        perf_summary = ""
        if PERF_MONITOR:
            stats = PERF_MONITOR.get_stats()
            perf_summary = f" I processed {stats['conversations']} conversations today."

        farewells = [
            f"Goodbye, Sir. It's been a good session.{perf_summary}",
            f"Take care, Nick. I'll be here when you need me.{perf_summary}",
            f"Sovereign sleeps. Until next time, Sir.{perf_summary}",
            f"Goodbye. It's been a productive day, Nick.{perf_summary}",
        ]
        speak(random.choice(farewells))

        # Save performance stats
        if PERF_MONITOR:
            PERF_MONITOR.save_stats()
            print(PERF_MONITOR.get_report())

        # ENHANCED: Flush memory on shutdown
        if ENHANCED_AVAILABLE and jarvis_mem:
            jarvis_mem.flush()
        if ENHANCED_AVAILABLE:
            awareness_engine.stop_monitoring()
            proactive_engine.stop_monitoring()
        break

    # Performance report command
    if lower in ("performance", "stats", "metrics", "how are you doing"):
        if PERF_MONITOR:
            speak(PERF_MONITOR.get_report())
        continue

    # Context suggestions - "what else" or "suggestions"
    if any(p in lower for p in ["what else", "suggestions", "what can you do"]):
        try:
            suggestions = get_context_suggestions()
            sugs = suggestions.get_suggestions()
            if sugs:
                speak(
                    f"Based on our conversation, you might want to: {', '.join(sugs)}, Sir."
                )
            else:
                speak(
                    "I could help with weather, time, searches, code, or answer questions, Sir."
                )
        except:
            pass

    # Update context suggestions
    try:
        suggestions = get_context_suggestions()
        suggestions.add_context(text)
    except:
        pass

    # Update personality based on interaction
    if PERSONALITY_AVAILABLE:
        try:
            from personality import get_personality

            personality = get_personality()
            personality.update_mood(_last_user_emotion, text)
        except:
            pass

    # Research dashboard commands
    if RESEARCH_AVAILABLE:
        # "show research" / "open dashboard" / "show simulations"
        if any(
            p in lower
            for p in [
                "show research",
                "show dashboard",
                "show simulations",
                "open dashboard",
            ]
        ):
            speak(
                "Opening the research dashboard, Sir. You'll see it at localhost:8765"
            )
            import subprocess

            subprocess.Popen(["open", "http://127.0.0.1:8765"])
            # Log to dashboard
            RESEARCH_DASHBOARD.add_observation(
                "Research dashboard opened by user", "system"
            )
            continue

        # "run simulation" / "start research"
        if any(
            p in lower
            for p in [
                "run simulation",
                "start research",
                "do research",
                "deep research",
            ]
        ):
            speak(
                "Starting deep research mode, Sir. I'll open the dashboard so you can watch the simulations in real-time."
            )
            # Open dashboard
            import subprocess

            subprocess.Popen(["open", "http://127.0.0.1:8765"])
            # Start research context
            with ResearchContext(text) as ctx:
                RESEARCH_VISUALIZER.add_model(
                    "Gemma 4", "thinking", f"Researching: {text[:50]}..."
                )
                ctx.progress(10, "Initializing research")
                # The actual research will happen in the LLM response
            continue

        # "show status" / "what's running"
        if any(
            p in lower for p in ["show status", "what's running", "research status"]
        ):
            status = RESEARCH_DASHBOARD.get_status()
            speak(f"Here's the research status, Sir. {status}")
            continue

    if lower in ("go to sleep", "sleep", "standby", "stand by"):
        speak("Standing by, Sir. Say Hey Jarvis when you need me.")
        active = False
        continue

    # ═══ QUICK REPLIES FOR COMMON QUERIES (Enhanced) ═══
    import datetime
    import requests

    # Predictive engine disabled — was returning stale "What's up?" for real queries
    # if ADVANCED_OPTIMIZATIONS and predictive_engine:
    #     predicted = predictive_engine.predict(text)
    #     if predicted:
    #         speak(predicted)
    #         continue

    # Time check
    if "time" in lower and len(lower.split()) <= 3:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"It's {current_time}, Sir.")
        continue

    # Date check
    if "date" in lower and len(lower.split()) <= 2:
        current_date = datetime.datetime.now().strftime("%A, %B %d")
        speak(f"Today is {current_date}, Sir.")
        continue

    # Weather quick check
    if "weather" in lower:
        try:
            r = requests.get("https://wttr.in/?format=j1", timeout=5)
            if r.status_code == 200:
                data = r.json()
                temp = data.get("current_condition", [{}])[0].get("temp_C", "?")
                cond = (
                    data.get("current_condition", [{}])[0]
                    .get("weatherDesc", [{}])[0]
                    .get("value", "unknown")
                )
                speak(f"The weather is {temp} degrees, {cond}, Sir.")
                continue
        except:
            pass

    # Web search quick check
    if (
        QUICK_SEARCH_AVAILABLE
        and any(w in lower for w in ["search", "find", "look up"])
        and len(lower.split()) <= 6
    ):
        # Extract search query
        search_terms = (
            lower.replace("search", "")
            .replace("find", "")
            .replace("look up", "")
            .strip()
        )
        if search_terms and len(search_terms) > 2:
            try:
                result = quick_search(search_terms, 3)
                speak(result)
                continue
            except:
                pass

    # Vision quick check - "look at" or "what do you see"
    if any(
        p in lower
        for p in ["look at", "what do you see", "what's on screen", "screenshot"]
    ):
        if QUICK_SEARCH_AVAILABLE:
            try:
                vision = VisionEngine()
                description = vision.analyze_screen("What do you see on this screen?")
                speak(description)
                continue
            except:
                pass

    # Code execution - "calculate" or "compute"
    if CODE_EXECUTOR_AVAILABLE and any(
        w in lower for w in ["calculate", "compute", "what is"]
    ):
        # Check if it's a math expression
        if any(
            c in lower
            for c in ["+", "-", "*", "/", "times", "plus", "minus", "divided"]
        ):
            try:
                # Extract expression
                import re

                expr = re.sub(r"[^0-9+\-*/.() ]", "", lower)
                if expr:
                    result = calculate(expr)
                    speak(f"The answer is {result}, Sir.")
                    continue
            except:
                pass

    # Translation - non-English detected
    if TRANSLATOR_AVAILABLE:
        try:
            from translator import get_translator

            translator = get_translator()
            lang = translator.detect_language(text)
            if lang != "en" and lang != "unknown":
                translated = translator.translate_to_english(text)
                speak(f"Sir, you said: {translated}")
                continue
        except:
            pass

    # Personality mood check - "how are you feeling" / "what's your mood"
    if PERSONALITY_AVAILABLE and any(
        p in lower
        for p in ["how are you feeling", "what's your mood", "how do you feel"]
    ):
        try:
            from personality import get_personality

            p = get_personality()
            speak(p.describe_mood())
            continue
        except:
            pass

    # Smart Memory - remember/recall with importance
    if SMART_MEMORY_AVAILABLE:
        # "remember" command
        if lower.startswith("remember ") or "remember that" in lower:
            # Extract what to remember
            mem_text = (
                lower.replace("remember ", "").replace("remember that", "").strip()
            )
            if mem_text and len(mem_text) > 2:
                result = SMART_MEMORY.remember_important(mem_text)
                speak(result)
                continue

        # "what do you remember" - IMPORTANT FIRST
        if "what do you remember" in lower or "recall" in lower:
            recall_query = text.replace("what do you remember about", "").replace("recall", "").strip() or "recent"
            result = SMART_MEMORY.recall(recall_query)
            if result:
                speak(f"Here's what I remember, Sir. {result}")
            else:
                speak("I don't have any memories yet, Sir.")
            continue

    # ask_sovereign now streams TTS internally — no separate speak() needed
    # Use blocking speak to avoid GPU race condition

    # ═══ CLARIFICATION FOR AMBIGUOUS QUERIES ═══
    if len(text.split()) <= 2 and "?" not in text:
        # Short queries without question mark - might be ambiguous
        ambiguous = ["it", "that", "this", "them", "those"]
        if any(w in lower.split() for w in ambiguous):
            clarification_phrases = [
                "Could you clarify what you're referring to?",
                "What specifically would you like to know?",
                "Could you be more specific?",
            ]
            import random

            speak(random.choice(clarification_phrases))
            continue

    try:
        reply = ask_sovereign(text, stream_to_speaker=False)
        log.info(f"🤖 '{reply[:80]}...'")

        # ═══ FORMAT RESPONSE FOR NATURAL CONVERSATION ═══
        # Remove JSON artifacts and clean up response
        import re

        reply = re.sub(r"\{[^}]*\}", "", reply)
        reply = re.sub(r"\[[^\]]*\]", "", reply)
        reply = re.sub(r"\*\*([^*]+)\*\*", r"\1", reply)
        reply = re.sub(r"\*([^*]+)\*", r"\1", reply)
        reply = re.sub(r"`([^`]+)`", r"\1", reply)
        reply = re.sub(r"\s+", " ", reply).strip()

        # Add conversational variety for longer responses
        if len(reply) > 200:
            lower_reply = reply.lower()
            if not any(
                lower_reply.startswith(p)
                for p in [
                    "yes",
                    "no",
                    "well",
                    "actually",
                    "sure",
                    "look",
                    "here",
                    "think",
                    "know",
                    "i",
                    "that",
                ]
            ):
                pass  # Removed formulaic prefix — sounds more natural without it

        # Emotion-aware response delay
        response_delay = 0.5  # default
        if CONVERSATION_FEATURES and emotion_aware_timing:
            response_delay = emotion_aware_timing.get_response_delay(_last_user_emotion)
            log.info(
                f"⏱️ Emotion-adjusted delay: {response_delay}s for {_last_user_emotion}"
            )

        time.sleep(response_delay)
        speak(reply)
    except Exception as e:
        log.error(f"Error in conversation loop: {e}")
        continue
