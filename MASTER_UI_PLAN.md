# MEOK OS — Living Character UI Overlay

## What We're Building

Transform the existing MEOK Desktop Tauri app (already transparent, always-on-top, game-aware)
into a living AI character that floats on screen as Jarvis/Sophie.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    SCREEN OVERLAY                     │
│                                                       │
│  ┌──────────┐  ┌─────────────────────────────────┐   │
│  │ Live2D   │  │ Speech Bubble                    │   │
│  │ Character │  │ "Hello Sir, all systems..."     │   │
│  │ (Jarvis/ │  │                                  │   │
│  │  Sophie) │  └─────────────────────────────────┘   │
│  │          │                                        │
│  │ 🎤 ━━━━ │  ← Lip-sync from Kokoro TTS           │
│  └──────────┘                                        │
│       ↑                                              │
│  Click to expand → Full chat panel                   │
└──────────────────────────────────────────────────────┘
         │ WebSocket
         ▼
┌─────────────────────────────────────────────────────┐
│              SOV3 BACKEND (FastAPI)                   │
│                                                       │
│  Voice Pipeline:  Whisper STT → Gemma 4 → Kokoro TTS │
│  Memory:          PostgreSQL + pgvector               │
│  Tools:           171 MCP tools                       │
│  Neural Models:   9 trained models                    │
│  Consciousness:   Dreams, reflections, curiosity      │
│  Agents:          47 agents + Taskiq queue            │
└─────────────────────────────────────────────────────┘
```

## What Already Exists

1. **meok-desktop/** — Tauri app, transparent, always-on-top, game detection
   - PaperclipButton (floating button)
   - ChatPanel (expandable chat)
   - Voice activation (Ctrl+Shift+V)
   - StatusRing (connection indicator)
   - Game color detection

2. **SOV3** — Full backend with voice, tools, memory, consciousness
3. **Kokoro TTS** — Already generating speech
4. **Whisper STT** — Already transcribing

## What Needs Building

### Phase 1: WebSocket Bridge (1 hour)
- Add WebSocket endpoint to SOV3 for real-time character control
- Send: `{ type: "speak", text, emotion, persona }` to frontend
- Receive: `{ type: "user_input", text }` from frontend
- Bridge existing voice pipeline to WebSocket events

### Phase 2: Live2D Character (2 hours)
- Add pixi-live2d-display to the Tauri app
- Free Live2D model for prototype (Hiyori or custom)
- Basic lip-sync from audio volume
- Emotion state → expression changes

### Phase 3: Character Switching (1 hour)
- Jarvis model (male, professional)
- Sophie model (female, warm)
- Switch based on persona state from backend

### Phase 4: HeadTTS Viseme Lip-Sync (2 hours)
- Replace volume-based lip-sync with proper viseme data
- HeadTTS already works with Kokoro
- Frame-accurate mouth animation

## Tech Stack

- **Frontend**: Tauri v2 + React + PixiJS + pixi-live2d-display
- **Backend**: FastAPI + WebSocket + SOV3
- **TTS**: Kokoro-82M (existing) + HeadTTS for visemes
- **STT**: Lightning Whisper MLX (existing)
- **LLM**: Gemma 4 E4B local (existing)
- **Animation**: Live2D Cubism (free models available)

## Key Repos to Reference

- Open-LLM-VTuber: github.com/Open-LLM-VTuber/Open-LLM-VTuber
- LLM-Live2D-Desktop-Assistant: github.com/ylxmf2005/LLM-Live2D-Desktop-Assitant
- HeadTTS (Kokoro + visemes): github.com/met4citizen/HeadTTS
- pixi-live2d-display: github.com/guansss/pixi-live2d-display
- CrabNebula desktop pet: github.com/crabnebula-dev/koi-pond
