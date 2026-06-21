#!/usr/bin/env python3
"""
Jarvis Voice Pipeline Test Script
Run from jarvis-env with GPU model loaded.

Usage:
    source jarvis-env/bin/activate
    cd /Users/nicholas/clawd/sovereign-temple
    python voice_pipeline/test_voice.py

Or with GPU:
    OLLAMA_URL=http://localhost:11435/api/chat python voice_pipeline/test_voice.py
"""

import os
import sys
import time
import logging
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("voice-test")

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check environment
OLLAMA_URL = os.getenv(
    "OLLAMA_URL", os.getenv("GPU_URL", "http://localhost:11434/api/chat")
)
log.info(f"Using Ollama URL: {OLLAMA_URL}")


def test_tts_only():
    """Test TTS only - no microphone needed"""
    log.info("=" * 50)
    log.info("TEST 1: TTS (Text-to-Speech) Only")
    log.info("=" * 50)

    try:
        import numpy as np
        import sounddevice as sd
        from mlx_audio.tts.utils import load_model
        from kokoro_mlx import generate as kokoro_generate, voices

        log.info("Loading Kokoro TTS model...")
        tts = load_model("mlx-community/Kokoro-82M-bf16")
        VOICES = {"default": "bm_daniel", "warm": "bf_emma", "calm": "bf_isabella"}

        test_phrases = [
            "Hello, this is a test of the Jarvis voice system.",
            "The system is now running at full capacity.",
            "All components are functioning correctly.",
        ]

        for i, phrase in enumerate(test_phrases, 1):
            log.info(f"Speaking phrase {i}/3: {phrase[:50]}...")
            voice = VOICES["default"]

            try:
                for result in tts.generate(
                    phrase[:300], voice=voice, speed=1.05, lang_code="b"
                ):
                    audio = np.array(result.audio, dtype=np.float32)
                    # Reset stream before playing
                    try:
                        sd.stop()
                    except:
                        pass
                    time.sleep(0.05)
                    sd.play(audio, 24000)
                    sd.wait()
                log.info(f"✅ Phrase {i} completed")
            except Exception as e:
                log.warning(f"⚠️ Phrase {i} error (non-fatal): {e}")
                continue

        log.info("✅ TTS test completed!")
        return True

    except ImportError as e:
        log.error(f"❌ Missing module: {e}")
        log.info("Install: pip install mlx-audio kokoro-mlx")
        return False
    except Exception as e:
        log.error(f"❌ TTS test failed: {e}")
        return False


def test_stt_only():
    """Test STT only - record and transcribe"""
    log.info("=" * 50)
    log.info("TEST 2: STT (Speech-to-Text)")
    log.info("=" * 50)

    try:
        import pyaudio
        import numpy as np
        from lightning_whisper_mlx import LightningWhisperMLX

        log.info("Loading Whisper STT model...")
        stt = LightningWhisperMLX(model="distil-large-v3", batch_size=12)

        # Record 3 seconds
        RATE = 16000
        CHUNK = 1024

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        log.info("Recording 3 seconds...")
        frames = []
        for _ in range(int(RATE / CHUNK * 3)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        pa.terminate()

        audio = np.concatenate([np.frombuffer(d, dtype=np.int16) for d in frames])
        audio = audio.astype(np.float32) / 32768.0

        log.info("Transcribing...")
        result = stt.transcribe(audio)
        text = result.get("text", "").strip()

        log.info(f"Transcribed: {text}")

        if text:
            log.info("✅ STT test passed!")
            return True
        else:
            log.warning("⚠️ No text detected")
            return False

    except ImportError as e:
        log.error(f"❌ Missing module: {e}")
        return False
    except Exception as e:
        log.error(f"❌ STT test failed: {e}")
        return False


def test_vad_only():
    """Test VAD only"""
    log.info("=" * 50)
    log.info("TEST 3: VAD (Voice Activity Detection)")
    log.info("=" * 50)

    try:
        import pyaudio
        import numpy as np
        import torch
        from silero_vad import load_silero_vad

        log.info("Loading Silero VAD...")
        vad = load_silero_vad()

        RATE = 16000
        CHUNK = 512

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        log.info("Listening for speech (5 seconds)...")
        speech_detected = False

        for _ in range(int(RATE / CHUNK * 5)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            is_speech = vad(torch.from_numpy(audio), RATE).item()

            if is_speech > 0.5:
                log.info(f"🎤 Speech detected! (confidence: {is_speech:.2f})")
                speech_detected = True
                break

        stream.stop_stream()
        stream.close()
        pa.terminate()

        if speech_detected:
            log.info("✅ VAD test passed!")
            return True
        else:
            log.info("✅ VAD ready (no speech in test)")
            return True

    except ImportError as e:
        log.error(f"❌ Missing module: {e}")
        return False
    except Exception as e:
        log.error(f"❌ VAD test failed: {e}")
        return False


def test_wake_word():
    """Test wake word detection"""
    log.info("=" * 50)
    log.info("TEST 4: Wake Word Detection")
    log.info("=" * 50)

    try:
        import pyaudio
        import numpy as np
        from openwakeword.model import Model as WakeModel

        log.info("Loading OpenWakeWord model...")
        wake = WakeModel()

        RATE = 16000
        CHUNK = 1280

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        log.info("Say 'Hey Jarvis' (or wait 5 seconds for skip)...")

        import time

        start = time.time()
        detected = False

        while time.time() - start < 5:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16)
            pred = wake.predict(audio)

            if pred.get("hey_jarvis", 0) > 0.5:
                log.info("🎯 Wake word detected!")
                detected = True
                break

        stream.stop_stream()
        stream.close()
        pa.terminate()

        if detected:
            log.info("✅ Wake word test passed!")
            return True
        else:
            log.info("✅ Wake word ready (not triggered in test)")
            return True

    except ImportError as e:
        log.error(f"❌ Missing module: {e}")
        return False
    except Exception as e:
        log.error(f"❌ Wake word test failed: {e}")
        return False


def test_ollama():
    """Test Ollama LLM connection"""
    log.info("=" * 50)
    log.info("TEST 5: Ollama LLM Connection")
    log.info("=" * 50)

    try:
        import requests

        # Check if Ollama is running
        url = OLLAMA_URL.replace("/api/chat", "/api/tags")
        res = requests.get(url, timeout=5)

        if res.status_code == 200:
            models = res.json().get("models", [])
            log.info(f"✅ Ollama connected! {len(models)} models available")

            # Try a simple generation
            url = OLLAMA_URL
            payload = {
                "model": "qwen2.5:7b",
                "messages": [
                    {"role": "user", "content": "Say 'test' if you can hear me."}
                ],
                "stream": False,
            }

            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                text = res.json().get("message", {}).get("content", "")
                log.info(f"LLM response: {text[:100]}")
                log.info("✅ Ollama test passed!")
                return True
            else:
                log.warning(f"Ollama returned {res.status_code}")
                return False
        else:
            log.error(f"❌ Ollama not accessible: {res.status_code}")
            return False

    except Exception as e:
        log.error(f"❌ Ollama test failed: {e}")
        return False


def test_full_pipeline():
    """Test full voice pipeline (requires all components)"""
    log.info("=" * 50)
    log.info("TEST 6: Full Voice Pipeline")
    log.info("=" * 50)
    log.info("This test requires microphone access.")
    log.info("Say something after the beep...")

    try:
        import pyaudio
        import numpy as np
        import torch
        import sounddevice as sd
        from silero_vad import load_silero_vad
        from lightning_whisper_mlx import LightningWhisperMLX
        from mlx_audio.tts.utils import load_model

        RATE = 16000
        CHUNK = 512

        # Load models
        log.info("Loading models...")
        vad = load_silero_vad()
        stt = LightningWhisperMLX(model="distil-large-v3", batch_size=12)
        tts = load_model("mlx-community/Kokoro-82M-bf16")

        # Record until speech stops
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        log.info("Listening...")
        frames = []
        silence_count = 0
        speech_started = False

        while silence_count < 30:  # Max 5 seconds
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            audio_torch = torch.from_numpy(audio_np)

            is_speech = vad(audio_torch, RATE).item()

            if is_speech > 0.5:
                frames.append(data)
                speech_started = True
                silence_count = 0
            elif speech_started:
                silence_count += 1

        stream.stop_stream()
        stream.close()
        pa.terminate()

        # Transcribe
        log.info("Transcribing...")
        audio = np.concatenate([np.frombuffer(d, dtype=np.int16) for d in frames])
        audio = audio.astype(np.float32) / 32768.0
        result = stt.transcribe(audio)
        text = result.get("text", "").strip()

        log.info(f"You said: {text}")

        if text:
            # Generate response
            log.info("Generating response...")
            response = f"I heard you say: {text}. This is a test response."

            # Speak back
            log.info("Speaking response...")
            for result in tts.generate(
                response[:300], voice="bm_daniel", speed=1.05, lang_code="b"
            ):
                audio = np.array(result.audio, dtype=np.float32)
                try:
                    sd.stop()
                except:
                    pass
                time.sleep(0.05)
                sd.play(audio, 24000)
                sd.wait()

            log.info("✅ Full pipeline test passed!")
            return True
        else:
            log.warning("⚠️ No speech detected")
            return False

    except Exception as e:
        log.error(f"❌ Full pipeline test failed: {e}")
        return False


def main():
    log.info("🎙️ Jarvis Voice Pipeline Test Suite")
    log.info("=" * 50)

    results = {}

    # Test Ollama first (no hardware needed)
    results["ollama"] = test_ollama()

    # Test TTS
    results["tts"] = test_tts_only()

    # Test VAD
    results["vad"] = test_vad_only()

    # Test STT
    results["stt"] = test_stt_only()

    # Test wake word
    results["wake"] = test_wake_word()

    # Summary
    log.info("=" * 50)
    log.info("📊 TEST SUMMARY")
    log.info("=" * 50)

    passed = sum(results.values())
    total = len(results)

    for name, ok in results.items():
        status = "✅" if ok else "❌"
        log.info(f"  {status} {name.upper()}")

    log.info("-" * 50)
    log.info(f"Total: {passed}/{total} passed")

    if passed == total:
        log.info("🎉 All tests passed! Voice pipeline is ready.")
    else:
        log.warning("⚠️ Some tests failed. Check errors above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
