#!/usr/bin/env python3
"""
MEOK AI LABS — Jarvis Live Voice Loop
Speak to Jarvis, hear Sovereign respond. Runs entirely on M4. Zero API costs.

Architecture:
  Mic (sounddevice) → Silero VAD → lightning-whisper-mlx → SOV3 /chat → mlx-audio Kokoro TTS → Speaker

Usage:
  python3 voice_pipeline/jarvis_voice_live.py

Requirements:
  pip3 install sounddevice lightning-whisper-mlx mlx-audio silero-vad numpy
"""

import sys
import time
import json
import logging
import tempfile
import threading
import numpy as np

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S"
)
log = logging.getLogger("jarvis")

# ── Audio config ─────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_DURATION_MS = 30  # 30ms chunks for VAD
SOV3_URL = "http://localhost:3200"
WHISPER_MODEL = "distil-small.en"  # Fast, accurate, small

# ── Import dependencies ──────────────────────────────────────────────────────
try:
    import sounddevice as sd

    log.info("✅ sounddevice")
except ImportError:
    log.error("❌ pip3 install sounddevice")
    sys.exit(1)

try:
    import torch
    from silero_vad import load_silero_vad, get_speech_timestamps

    log.info("✅ Silero VAD")
except ImportError:
    log.error("❌ pip3 install silero-vad")
    sys.exit(1)

try:
    from lightning_whisper_mlx import LightningWhisperMLX

    log.info("✅ lightning-whisper-mlx")
except ImportError:
    log.error("❌ pip3 install lightning-whisper-mlx")
    sys.exit(1)

TTS_AVAILABLE = False
try:
    import subprocess

    # mlx-audio TTS via CLI (most reliable on system Python)
    TTS_AVAILABLE = True
    log.info("✅ mlx-audio TTS (via CLI)")
except Exception:
    log.warning("⚠️ TTS not available — responses will be text-only")

# ── Load models ──────────────────────────────────────────────────────────────
log.info("Loading Silero VAD model...")
vad_model = load_silero_vad()

log.info(f"Loading Whisper STT model ({WHISPER_MODEL})...")
whisper = LightningWhisperMLX(model=WHISPER_MODEL, batch_size=12)

log.info("🟢 Jarvis is ready. Speak to begin.")
print("\n" + "=" * 50)
print("  🎙️  JARVIS LIVE — Speak naturally")
print("  Press Ctrl+C to stop")
print("=" * 50 + "\n")

# ── Voice Activity Detection ─────────────────────────────────────────────────


def record_until_silence(timeout_sec=10, silence_duration_ms=800):
    """Record audio until VAD detects end of speech."""
    audio_chunks = []
    silence_chunks = 0
    silence_threshold = int(silence_duration_ms / BLOCK_DURATION_MS)
    max_chunks = int(timeout_sec * 1000 / BLOCK_DURATION_MS)

    block_size = int(SAMPLE_RATE * BLOCK_DURATION_MS / 1000)
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", blocksize=block_size
    )
    stream.start()

    speaking = False
    chunk_count = 0

    try:
        while chunk_count < max_chunks:
            data, _ = stream.read(block_size)
            audio_chunks.append(data.copy())
            chunk_count += 1

            # VAD check
            tensor = torch.from_numpy(data.flatten())
            timestamps = get_speech_timestamps(
                tensor, vad_model, sampling_rate=SAMPLE_RATE
            )

            if timestamps:
                speaking = True
                silence_chunks = 0
            elif speaking:
                silence_chunks += 1
                if silence_chunks >= silence_threshold:
                    break  # End of utterance
    finally:
        stream.stop()
        stream.close()

    if not speaking:
        return None

    audio = np.concatenate(audio_chunks, axis=0).flatten()
    return audio


def transcribe_audio(audio_array):
    """Transcribe numpy audio array using lightning-whisper-mlx."""
    import soundfile as sf

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio_array, SAMPLE_RATE)
        result = whisper.transcribe(f.name)
    text = result.get("text", "").strip()
    return text


def query_sovereign(text):
    """Send text to SOV3 /chat and get response. Falls back to local Ollama if SOV3 is down."""
    import urllib.request

    try:
        req = urllib.request.Request(
            f"{SOV3_URL}/chat",
            data=json.dumps({"message": text, "model": "local"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", data.get("text", str(data)))
    except Exception as e:
        log.warning(f"SOV3 error: {e}, falling back to local Ollama")
        try:
            import requests as _req

            r = _req.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "qwen3.5:9b",
                    "messages": [{"role": "user", "content": text}],
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 512},
                },
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["message"]["content"]
        except Exception as ollama_err:
            log.error(f"Local Ollama fallback also failed: {ollama_err}")
            return "I'm having trouble connecting to my systems. Please try again."


def speak_response(text):
    """Speak text using mlx-audio Kokoro TTS."""
    if not TTS_AVAILABLE or not text:
        return
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out_path = f.name
        # Use mlx_audio CLI for TTS
        subprocess.run(
            [
                sys.executable,
                "-m",
                "mlx_audio.tts.generate",
                "--text",
                text[:500],  # Limit length
                "--output",
                out_path,
            ],
            capture_output=True,
            timeout=30,
        )
        # Play audio
        import soundfile as sf

        data, sr = sf.read(out_path)
        sd.play(data, sr)
        sd.wait()
    except Exception as e:
        log.warning(f"TTS error: {e}")
        print(f"\n💬 Jarvis: {text}\n")


# ── Main Loop ────────────────────────────────────────────────────────────────


def main():
    while True:
        try:
            # Listen for speech
            sys.stdout.write("🎙️  Listening... ")
            sys.stdout.flush()
            audio = record_until_silence(timeout_sec=15)

            if audio is None or len(audio) < SAMPLE_RATE * 0.3:  # < 0.3s = noise
                sys.stdout.write("(silence)\r")
                continue

            print("🔄 Processing...")

            # Transcribe
            text = transcribe_audio(audio)
            if not text or len(text.strip()) < 2:
                print("(couldn't understand)")
                continue

            print(f"🗣️  You: {text}")

            # Query Sovereign
            response = query_sovereign(text)
            print(f"🤖 Jarvis: {response}")

            # Speak response
            speak_response(response)

        except KeyboardInterrupt:
            print("\n\n👋 Jarvis signing off. Sovereign sleeps.")
            break
        except Exception as e:
            log.error(f"Loop error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
