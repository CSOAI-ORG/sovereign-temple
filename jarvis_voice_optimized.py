#!/usr/bin/env python3
"""
JARVIS Voice Optimizer - Improved voice processing
- Noise reduction
- Audio normalization
- Better VAD
- Emotion detection improvements
"""

import numpy as np
import sounddevice as sd
from scipy import signal
from scipy.signal import butter, filtfilt


class VoiceOptimizer:
    """Optimize voice audio quality"""

    def __init__(self):
        self.noise_profile = None
        self.sample_rate = 16000

    def normalize_audio(
        self, audio: np.ndarray, target_level: float = 0.5
    ) -> np.ndarray:
        """Normalize audio to target level"""
        if len(audio) == 0:
            return audio

        # RMS normalization
        rms = np.sqrt(np.mean(audio**2))
        if rms > 0:
            audio = audio * (target_level / rms)

        # Peak normalization
        peak = np.abs(audio).max()
        if peak > 0.95:
            audio = audio * (0.95 / peak)

        return np.clip(audio, -0.95, 0.95)

    def remove_silence(
        self, audio: np.ndarray, threshold: float = 0.01, min_silence: float = 0.3
    ) -> np.ndarray:
        """Remove silence from audio"""
        # Calculate energy
        energy = np.abs(audio)

        # Find non-silent segments
        non_silent = energy > threshold

        if not any(non_silent):
            return audio

        # Find contiguous non-silent regions
        segments = []
        start = None

        for i, is_speech in enumerate(non_silent):
            if is_speech and start is None:
                start = i
            elif not is_speech and start is not None:
                if (i - start) / self.sample_rate >= min_silence:
                    segments.append((start, i))
                start = None

        if start is not None and (len(audio) - start) / self.sample_rate >= min_silence:
            segments.append((start, len(audio)))

        if not segments:
            return audio

        # Concatenate segments
        return np.concatenate([audio[s:e] for s, e in segments])

    def apply_highpass(self, audio: np.ndarray, cutoff: int = 80) -> np.ndarray:
        """Apply highpass filter to remove low frequency noise"""
        nyquist = self.sample_rate / 2
        b, a = butter(2, cutoff / nyquist, btype="high")
        return filtfilt(b, a, audio)

    def apply_lowpass(self, audio: np.ndarray, cutoff: int = 8000) -> np.ndarray:
        """Apply lowpass filter for cleaner audio"""
        nyquist = self.sample_rate / 2
        b, a = butter(2, cutoff / nyquist, btype="low")
        return filtfilt(b, a, audio)

    def enhance_voice(self, audio: np.ndarray) -> np.ndarray:
        """Complete voice enhancement pipeline"""
        # Highpass to remove rumble
        audio = self.apply_highpass(audio)

        # Normalize
        audio = self.normalize_audio(audio)

        # Remove silence
        audio = self.remove_silence(audio)

        # Light lowpass to smooth
        audio = self.apply_lowpass(audio, cutoff=7500)

        return audio

    def detect_voice_activity(self, audio: np.ndarray, threshold: float = 0.02) -> bool:
        """Better VAD using multiple methods"""
        # Method 1: RMS energy
        rms = np.sqrt(np.mean(audio**2))

        # Method 2: Zero crossing rate
        zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2

        # Method 3: Spectral centroid
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1 / self.sample_rate)
        centroid = np.sum(freqs * np.abs(fft)) / (np.sum(np.abs(fft)) + 1e-10)

        # Voice if any method detects speech
        is_voice = (rms > threshold) or (zcr > 0.1) or (centroid > 200)

        return is_voice

    def get_audio_features(self, audio: np.ndarray) -> dict:
        """Extract audio features for analysis"""
        # Energy
        rms = np.sqrt(np.mean(audio**2))

        # Zero crossing rate
        zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2

        # Pitch (simple autocorrelation)
        autocorr = np.correlate(audio, audio, mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]
        peaks = np.argsort(autocorr)[-5:]
        pitch = self.sample_rate / (peaks[-1] + 1) if peaks[-1] > 0 else 0

        # Spectral features
        fft = np.abs(np.fft.rfft(audio))
        spectral_centroid = np.sum(np.arange(len(fft)) * fft) / (np.sum(fft) + 1e-10)
        spectral_rolloff = np.where(np.cumsum(fft) > 0.85 * np.sum(fft))[0][0] / len(
            fft
        )

        return {
            "rms": rms,
            "zcr": zcr,
            "pitch": pitch,
            "spectral_centroid": spectral_centroid,
            "spectral_rolloff": spectral_rolloff,
            "duration": len(audio) / self.sample_rate,
        }

    def detect_emotion_from_audio(self, audio: np.ndarray) -> str:
        """Detect emotion from audio features"""
        features = self.get_audio_features(audio)

        # Energy-based
        if features["rms"] > 0.1:
            if features["pitch"] > 200:
                return "excited"
            return "energetic"
        elif features["rms"] < 0.02:
            return "quiet"

        # Pitch-based
        if features["pitch"] < 100:
            return "serious"
        elif features["pitch"] > 250:
            return "happy"

        # ZCR-based
        if features["zcr"] > 0.2:
            return "animated"

        return "neutral"


# Global optimizer
voice_optimizer = VoiceOptimizer()


def optimize_audio(audio: np.ndarray) -> np.ndarray:
    return voice_optimizer.enhance_voice(audio)


def detect_voice(audio: np.ndarray) -> bool:
    return voice_optimizer.detect_voice_activity(audio)


def get_emotion(audio: np.ndarray) -> str:
    return voice_optimizer.detect_emotion_from_audio(audio)


if __name__ == "__main__":
    print("Voice Optimizer ready")
    print(f"  - normalize: Yes")
    print(f"  - silence removal: Yes")
    print(f"  - highpass filter: Yes")
    print(f"  - VAD: Yes")
    print(f"  - emotion detection: Yes")
