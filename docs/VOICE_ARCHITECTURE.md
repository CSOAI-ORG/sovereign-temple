# Voice AI on Laptops & Phones - How It Works & Our Implementation

## How Consumer Voice AI Works

### 1. **Web Speech API (Browser-based)**
```javascript
// Every modern browser has this built-in
const recognition = new webkitSpeechRecognition();
recognition.continuous = true;
recognition.interimResults = true;

recognition.onresult = (event) => {
  for (let i = event.resultIndex; i < event.results.length; i++) {
    if (event.results[i].isFinal) {
      console.log(event.results[i][0].transcript);
    }
  }
};
```
- Uses browser's built-in speech recognition (Chrome = Google, Safari = Apple)
- Works offline on some devices
- Quality varies by browser/OS

### 2. **Native Mobile Voice (iOS/Android)**
- **iOS**: Apple Speech framework, Siri engine under the hood
- **Android**: Google Speech API, on-device recognition on newer phones
- Both can run partially offline with on-device ML models

### 3. **Cloud Voice APIs** (what we're using)
- **Whisper** (OpenAI): Best accuracy, cloud or local (whisper.cpp)
- **Cloud STT**: Send audio → get text
- **Cloud TTS**: Send text → get audio

## Why "They" Are Better

1. **On-device ML**: Apple Neural Engine, Google Tensor
2. **Acoustic models**: Trained on billions of hours of speech
3. **Language models**: Context-aware transcription
4. **Hardware optimization**: Custom chips for voice

## Our Solution - Sovereign Voice Stack

| Layer | Current | Goal |
|-------|---------|------|
| **STT** | Whisper (cloud) | whisper.cpp (local) |
| **LLM** | Ollama + cloud | All locally |
| **TTS** | Kokoro (MLX) | Kokoro + Piper (mobile) |

## Local Voice Options

### STT - Speech to Text
| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| whisper.cpp | 75MB-2.9GB | Fast | Excellent |
| Vosk | 50MB | Very Fast | Good |
| Whisper (MLX) | 1-3GB | Fast (Apple GPU) | Best |

### TTS - Text to Speech
| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| **Piper** | 50MB | Real-time | Good |
| **Kokoro** | 82MB | Fast | Excellent |
| CoquiTTS | 100MB+ | Medium | Good |

## Running Local Voice

### Install whisper.cpp (STT)
```bash
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make
./main -m models/ggml-large.bin -f sample.wav
```

### Install Piper (TTS)
```bash
# Download binary
curl -LO https://github.com/rhasspy/piper/releases/download/2024.08.08/piper_linux_amd64.tar.gz
tar -xzf piper_linux_amd64.tar.gz
echo "test" | ./piper/piper --model en_US-lessac.onnx --output_file test.wav
```

### Install Kokoro (Apple Silicon)
```bash
pip install kokoro-mlx mlx-audio
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    JARVIS Voice Stack                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🎤 MIC ──► VAD ──► STT ──► LLM ──► TTS ──► 🔊 SPEAKER     │
│             │        │        │       │                     │
│           Silero   Whisper  SOV3    Kokoro                  │
│           (local)  (cloud)  (local) (MLX)                   │
│                                                             │
│  Providers:                                                 │
│  - STT: whisper.cpp, Whisper (MLX), Web Speech API         │
│  - TTS: Kokoro (MLX), Piper, Web Speech API, edge-tts       │
│  - LLM: Ollama, OpenRouter, Cloud APIs                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Claude Code Voice Mode Features to Mimic

1. **Push-to-talk**: Hold spacebar/button to record
2. **Continuous**: Multiple sentences in one go
3. **Fast**: Stream responses, don't wait for full generation
4. **Interruptible**: Can stop speaking anytime
5. **Hybrid**: Type or speak seamlessly

## Current Implementation Files

- `voice_pipeline/jarvis_compass.py` - Full voice pipeline
- `voice_pipeline/jarvis_claude_voice.py` - Claude Code style
- `voice_pipeline/jarvis_smooth.py` - Smooth streaming TTS
- `voice_server.py` - WebSocket server for browser voice

## Testing Commands

```bash
# Test Claude Code style voice
python voice_pipeline/jarvis_claude_voice.py

# Test whisper.cpp (need to install)
# ./main -m models/ggml-base.bin - microphone

# Test Kokoro TTS
python -c "
from mlx_audio.tts.utils import load_model
import numpy as np
import sounddevice as sd
tts = load_model('mlx-community/Kokoro-82M-bf16')
for r in tts.generate('Hello, I am JARVIS.'):
    sd.play(np.array(r.audio), 24000)
    sd.wait()
"
```

## Mobile/Phone Strategy

For phones, we'll use:
1. **React Native** with native voice modules
2. **Web Speech API** as fallback
3. **WebSocket** to local server for heavy processing
4. **Piper** for lightweight TTS on mobile

## TODO

- [ ] Add whisper.cpp for true local STT
- [ ] Add Piper TTS for mobile
- [ ] Build React Native voice component
- [ ] Add push-to-talk to MEOK chat UI
