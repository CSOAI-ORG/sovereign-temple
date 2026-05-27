# Jarvis Voice Pipeline - Architecture & Optimization Guide

## Current Setup

### Stack Components
| Component | Model | Framework | Notes |
|-----------|-------|-----------|-------|
| Wake Word | hey_jarvis | OpenWakeWord (ONNX) | Always-listening |
| VAD | Silero | PyTorch | Speech detection |
| STT | distil-large-v3 | LightningWhisperMLX | Transcription |
| LLM | qwen3.5:9b / nemotron-3-super:cloud | Ollama | Conversation |
| TTS | Kokoro-82M | MLX-Audio | Speech synthesis |

### Ports
- MCP Server: **3200** (changed from 3100 due to OrbStack conflict)
- MEOK UI: 3000
- Ollama: 11434

---

## Voice Optimization Issues & Fixes

### Issue 1: Staggered Audio
**Cause:** Non-blocking playback with insufficient buffer management

**Fixes Applied:**
```python
# 1. Audio normalization - prevent clipping
audio = np.clip(audio, -0.95, 0.95)

# 2. Blocking playback with wait
sd.play(audio, RATE)
sd.wait()  # Wait for completion

# 3. Stream reset between chunks
sd.stop()
time.sleep(0.02)  # Let stream fully reset
sd.play(audio, RATE)
```

### Issue 2: Metal Buffer Conflicts
**Cause:** Metal GPU buffer not properly released between plays

**Fix:** Added explicit stream management:
```python
try:
    sd.stop()
except:
    pass
time.sleep(0.02)
sd.play(audio, RATE)
```

### Issue 3: Callback-Based Streaming (Advanced)
For smoother playback, use callback-based streaming:
- See `voice_pipeline/jarvis_smooth.py` for implementation
- Uses `OutputStream` with callback for non-blocking playback
- Proper buffer queue for streaming LLM output

---

## Testing Commands

```bash
# Activate voice environment
cd /Users/nicholas/clawd/sovereign-temple
source jarvis-env/bin/activate

# Test simple TTS
python3 -c "
import numpy as np
import sounddevice as sd
from mlx_audio.tts.utils import load_model
tts = load_model('mlx-community/Kokoro-82M-bf16')
for r in tts.generate('Hello world', voice='bm_daniel'):
    sd.play(np.array(r.audio), 24000)
    sd.wait()
print('Done')
"

# Test with new smooth player
python3 voice_pipeline/jarvis_smooth.py
```

---

## MCP Server Commands

```bash
# Test MCP consciousness
curl -X POST http://localhost:3200/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_consciousness_state","arguments":{}},"id":"1"}'

# Test delegation
curl -X POST http://localhost:3200/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"delegate_to_department","arguments":{"department":"content","task":"Write a blog post","priority":5}},"id":"1"}'
```

---

## Key Files

- `voice_pipeline/jarvis_compass.py` - Main voice pipeline
- `voice_pipeline/jarvis_smooth.py` - Optimized streaming version
- `voice_pipeline/test_voice.py` - Test suite
- `sovereign-mcp-server.py` - MCP server (port 3200)
- `department_mcp_tools.py` - Department agent tools

---

## References

- [MLX-Audio](https://github.com/Blaizzy/mlx-audio) - TTS/STT on Apple Silicon
- [Kokoro MLX](https://github.com/gabrimatic/kokoro-mlx) - TTS model
- [SoundDevice Docs](https://python-sounddevice.readthedocs.io/) - Audio playback
- [OpenWakeWord](https://github.com/dscripka/openwakeword) - Wake word detection

---

## TODO

- [ ] Test jarvis_smooth.py callback-based streaming
- [ ] Add WebSocket for real-time voice streaming
- [ ] Integrate with MEOK chat UI
- [ ] Add voice command hotkey (Ctrl+Shift+V)
