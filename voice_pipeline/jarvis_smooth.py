#!/usr/bin/env python3
"""
Jarvis Voice Pipeline - Optimized for Smooth Playback
Uses callback-based streaming for glitch-free audio on Apple Silicon

Key fixes:
1. Uses OutputStream with callback for smooth continuous playback
2. Proper buffer management to prevent underruns
3. Audio normalization to prevent clipping
4. Thread-safe queue for LLM-to-speech streaming

Based on mlx-audio best practices + sounddevice streaming docs
"""

import os
import re
import time
import queue
import logging
import threading
import numpy as np
import sounddevice as sd
import torch
from typing import Optional, Generator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("jarvis-voice")

RATE = 24000  # Kokoro output rate

# Audio queue for streaming from TTS to playback
audio_queue: queue.Queue = queue.Queue()
playing = False
stream = None


class StreamingPlayer:
    """Callback-based audio player for smooth playback"""

    def __init__(self, sample_rate=RATE, blocksize=1024):
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.playing = False
        self.stream = None

    def callback(self, outdata, frames, time_info, status):
        """Non-blocking callback - smooth playback"""
        if status:
            log.warning(f"Stream status: {status}")

        with self.buffer_lock:
            if len(self.buffer) >= frames:
                # Copy from buffer
                outdata[:] = self.buffer[:frames].reshape(-1, 1)
                self.buffer = self.buffer[frames:]
            elif self.playing:
                # Fade out gracefully
                fade_len = min(frames, 256)
                outdata[:] = np.zeros((frames, 1), dtype=np.float32)
            else:
                outdata[:] = np.zeros((frames, 1), dtype=np.float32)

    def add_audio(self, audio: np.ndarray):
        """Add audio chunk to buffer"""
        with self.buffer_lock:
            # Normalize and smooth the transition
            audio = np.clip(audio, -0.95, 0.95)
            if len(self.buffer) > 0 and len(audio) > 0:
                # Crossfade at boundaries
                fade_len = min(128, len(audio), len(self.buffer))
                crossfade = np.linspace(0, 1, fade_len)
                self.buffer[-fade_len:] *= 1 - crossfade
                audio[:fade_len] = (
                    crossfade * audio[:fade_len]
                    + (1 - crossfade) * self.buffer[-fade_len:]
                )
            self.buffer = np.concatenate([self.buffer, audio])
            self.playing = True

    def start(self):
        """Start the stream"""
        if self.stream is None:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.blocksize,
                channels=1,
                dtype=np.float32,
                callback=self.callback,
            )
            self.stream.start()
            log.info("Audio stream started")

    def stop(self):
        """Stop the stream"""
        self.playing = False
        with self.buffer_lock:
            self.buffer = np.array([], dtype=np.float32)
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            log.info("Audio stream stopped")


def speak_smooth(text: str, voice: str = "bm_daniel"):
    """Speak text using smooth streaming playback"""
    global playing

    from mlx_audio.tts.utils import load_model

    log.info(f"Loading TTS model...")
    tts = load_model("mlx-community/Kokoro-82M-bf16")

    player = StreamingPlayer(sample_rate=RATE, blocksize=512)
    player.start()
    playing = True

    # Split into sentences for streaming
    sentences = re.split(r"(?<=[.!?])\s+", text)

    try:
        for sentence in sentences:
            if not sentence or len(sentence) < 2:
                continue
            if not playing:
                break

            sentence = sentence.strip()[:300]

            # Generate audio for this sentence
            for result in tts.generate(
                sentence, voice=voice, speed=1.05, lang_code="b"
            ):
                if not playing:
                    break
                audio = np.array(result.audio, dtype=np.float32)
                player.add_audio(audio)

        # Let playback finish
        time.sleep(0.5)

    finally:
        playing = False
        player.stop()


def speak_blocking(text: str, voice: str = "bm_daniel"):
    """Simple blocking playback - safer for testing"""
    from mlx_audio.tts.utils import load_model

    log.info(f"Loading TTS...")
    tts = load_model("mlx-community/Kokoro-82M-bf16")

    # Generate all audio first
    all_audio = []
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        if not sentence or len(sentence) < 2:
            continue
        sentence = sentence.strip()[:300]

        for result in tts.generate(sentence, voice=voice, speed=1.05, lang_code="b"):
            audio = np.array(result.audio, dtype=np.float32)
            all_audio.append(audio)

    # Concatenate and normalize
    if all_audio:
        full_audio = np.concatenate(all_audio)
        full_audio = np.clip(full_audio, -0.95, 0.95)

        log.info(f"Playing {len(full_audio) / RATE:.1f}s of audio...")
        sd.play(full_audio, RATE)
        sd.wait()
        log.info("Done")


def test_voice():
    """Test the voice output"""
    print("=== Jarvis Voice Test ===")

    phrases = [
        "Hello. I am Jarvis. I am now online and ready to assist you.",
        "The voice system has been optimized for smooth playback on Apple Silicon.",
        "All systems are operational. How may I help you today?",
    ]

    print("\n1. Testing blocking mode (more reliable)...")
    for i, phrase in enumerate(phrases, 1):
        print(f"\nPhrase {i}/3: {phrase[:50]}...")
        speak_blocking(phrase)
        time.sleep(0.5)

    print("\n✅ Voice test complete!")
    return True


if __name__ == "__main__":
    test_voice()
