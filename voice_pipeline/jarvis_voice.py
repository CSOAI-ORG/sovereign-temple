#!/usr/bin/env python3
"""
MEOK AI LABS — Jarvis Voice Pipeline
Local voice service for workshop use.

Architecture:
  Mic → Silero VAD → STT (whisper/VibeVoice) → SOV3 → TTS (Kokoro/VibeVoice) → Speaker

Phase 1 (now):   Silero VAD + openWakeWord detection
Phase 2 (May):   + lightning-whisper-mlx STT + Kokoro TTS
Phase 3 (June):  + VibeVoice-ASR + VibeVoice-Realtime

Run: python3 voice_pipeline/jarvis_voice.py
"""

import sys
import time
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
log = logging.getLogger("jarvis-voice")

# ── Check dependencies ────────────────────────────────────────────────────────

SILERO_OK = False
WAKEWORD_OK = False
WHISPER_OK = False
KOKORO_OK = False

try:
    import torch
    from silero_vad import load_silero_vad, get_speech_timestamps
    SILERO_OK = True
    log.info("✅ Silero VAD available")
except ImportError:
    log.warning("❌ Silero VAD not installed: pip install silero-vad")

try:
    import openwakeword
    from openwakeword.model import Model as WakeWordModel
    WAKEWORD_OK = True
    log.info("✅ openWakeWord available")
except ImportError:
    log.warning("❌ openWakeWord not installed: pip install openwakeword")

try:
    from lightning_whisper_mlx import LightningWhisperMLX
    WHISPER_OK = True
    log.info("✅ lightning-whisper-mlx available")
except ImportError:
    log.info("⏳ lightning-whisper-mlx not installed (Phase 2)")

try:
    from kokoro import KPipeline
    KOKORO_OK = True
    log.info("✅ Kokoro TTS available")
except ImportError:
    log.info("⏳ Kokoro TTS not installed (Phase 2)")


# ── VAD Service ───────────────────────────────────────────────────────────────

class VoiceActivityDetector:
    """Silero VAD wrapper for detecting speech segments."""

    def __init__(self):
        if not SILERO_OK:
            raise RuntimeError("Silero VAD not installed")
        self.model = load_silero_vad()
        log.info("Silero VAD model loaded")

    def detect_speech(self, audio_tensor, sample_rate=16000):
        """Returns list of speech segments with start/end timestamps."""
        timestamps = get_speech_timestamps(
            audio_tensor,
            self.model,
            sampling_rate=sample_rate,
            min_silence_duration_ms=500,  # 500ms silence = end of utterance
            speech_pad_ms=100,
        )
        return timestamps

    def is_speech(self, audio_chunk, sample_rate=16000):
        """Quick check: does this chunk contain speech?"""
        timestamps = self.detect_speech(audio_chunk, sample_rate)
        return len(timestamps) > 0


# ── Wake Word Service ─────────────────────────────────────────────────────────

class WakeWordDetector:
    """openWakeWord wrapper — listens for 'hey jarvis' or custom wake word."""

    def __init__(self, wake_words=None):
        if not WAKEWORD_OK:
            raise RuntimeError("openWakeWord not installed")
        # Download default models on first use
        openwakeword.utils.download_models()
        self.model = WakeWordModel(
            wakeword_models=wake_words or ["hey_jarvis"],
            inference_framework="onnx",
        )
        log.info("Wake word detector loaded: %s", wake_words or ["hey_jarvis"])

    def predict(self, audio_chunk):
        """Process 80ms audio chunk. Returns dict of wake word → confidence."""
        prediction = self.model.predict(audio_chunk)
        return prediction


# ── STT Service (Phase 2) ────────────────────────────────────────────────────

class SpeechToText:
    """Speech-to-text using lightning-whisper-mlx (Apple Silicon optimized)."""

    def __init__(self, model_size="distil-medium.en"):
        if not WHISPER_OK:
            raise RuntimeError("lightning-whisper-mlx not installed: pip install lightning-whisper-mlx")
        self.whisper = LightningWhisperMLX(model=model_size, batch_size=12)
        log.info("Whisper STT loaded: %s", model_size)

    def transcribe(self, audio_path):
        """Transcribe audio file to text."""
        result = self.whisper.transcribe(audio_path)
        return result.get("text", "").strip()


# ── TTS Service (Phase 2) ────────────────────────────────────────────────────

class TextToSpeech:
    """Text-to-speech using Kokoro-82M (Apache 2.0, 20-50x realtime on M4)."""

    def __init__(self, lang_code="b", voice="bf_emma"):
        if not KOKORO_OK:
            raise RuntimeError("Kokoro not installed: pip install kokoro-mlx")
        self.pipeline = KPipeline(lang_code=lang_code)
        self.voice = voice
        log.info("Kokoro TTS loaded: lang=%s voice=%s", lang_code, voice)

    def speak(self, text, output_path="/tmp/jarvis_response.wav"):
        """Generate speech from text. Returns path to audio file."""
        import soundfile as sf
        for _, _, audio in self.pipeline(text, voice=self.voice):
            sf.write(output_path, audio, 24000)
        return output_path


# ── Pipeline Orchestrator ─────────────────────────────────────────────────────

class JarvisVoicePipeline:
    """
    Full voice pipeline: Wake Word → VAD → STT → SOV3 → TTS → Speaker.
    Initializes only available components.
    """

    def __init__(self):
        self.vad = VoiceActivityDetector() if SILERO_OK else None
        self.wake = WakeWordDetector() if WAKEWORD_OK else None
        self.stt = SpeechToText() if WHISPER_OK else None
        self.tts = TextToSpeech() if KOKORO_OK else None

        available = []
        if self.vad: available.append("VAD")
        if self.wake: available.append("WakeWord")
        if self.stt: available.append("STT")
        if self.tts: available.append("TTS")

        log.info("Jarvis Voice Pipeline initialized: [%s]", " → ".join(available) or "NO COMPONENTS")
        if not available:
            log.warning("No voice components available. Install: pip install silero-vad openwakeword")

    def status(self):
        return {
            "vad": SILERO_OK,
            "wake_word": WAKEWORD_OK,
            "stt": WHISPER_OK,
            "tts": KOKORO_OK,
            "phase": 2 if (WHISPER_OK and KOKORO_OK) else 1,
        }


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pipeline = JarvisVoicePipeline()
    status = pipeline.status()
    print(json.dumps(status, indent=2))

    if not any(status.values()):
        print("\n⚠️  No voice components available.")
        print("Install Phase 1: pip install silero-vad openwakeword")
        print("Install Phase 2: pip install lightning-whisper-mlx kokoro-mlx")
        sys.exit(1)

    print("\n✅ Jarvis Voice Pipeline ready.")
    print(f"   Phase: {status['phase']}")
    print(f"   Components: VAD={status['vad']}, Wake={status['wake_word']}, STT={status['stt']}, TTS={status['tts']}")
