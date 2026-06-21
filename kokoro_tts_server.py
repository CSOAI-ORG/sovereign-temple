#!/usr/bin/env python3
"""
Kokoro TTS HTTP Server for Amica
Port 8180 — POST /tts {"text":"...", "voice":"af_bella"} → WAV audio
"""

import io
import json
import logging
import os
import glob
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler

log = logging.getLogger("kokoro_tts")

MODEL = None

def get_model():
    global MODEL
    if MODEL is None:
        from mlx_audio.tts.generate import load_model
        MODEL = load_model("mlx-community/Kokoro-82M-bf16")
        log.info("Kokoro model loaded")
    return MODEL


def synthesize(text: str, voice: str = "af_bella") -> bytes:
    from mlx_audio.tts.generate import generate_audio
    model = get_model()

    tmpdir = tempfile.mkdtemp()
    prefix = "tts"

    # Strip emotion tags and stage directions before generating speech
    import re
    text = re.sub(r'\[[\w]+\]\s*', '', text)          # Remove [happy] etc
    text = re.sub(r'\([^)]{5,}\)\s*', '', text)        # Remove (stage directions)
    text = text.strip()
    if not text:
        return b""

    generate_audio(text, model=model, voice=voice, speed=0.9,
                   output_path=tmpdir, file_prefix=prefix,
                   save=True, play=False, verbose=False)

    # Find generated file (adds _000 suffix)
    wavs = sorted(glob.glob(os.path.join(tmpdir, f"{prefix}*.wav")))
    if wavs and os.path.getsize(wavs[0]) > 100:
        with open(wavs[0], "rb") as f:
            data = f.read()
        # Cleanup
        for w in wavs:
            os.unlink(w)
        os.rmdir(tmpdir)
        return data

    # Cleanup on failure
    for w in wavs:
        os.unlink(w)
    os.rmdir(tmpdir)
    return b""


class TTSHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            text = data.get("text", data.get("message", ""))
            voice = data.get("voice", "af_bella")
            if not text:
                self.send_error(400, "No text")
                return

            wav = synthesize(text, voice)
            if not wav:
                self.send_error(500, "TTS failed")
                return

            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(wav)
        except Exception as e:
            log.error(f"TTS error: {e}")
            self.send_error(500, str(e))

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        log.info(fmt % args)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print("Loading Kokoro model...")
    get_model()
    server = HTTPServer(("0.0.0.0", 8180), TTSHandler)
    print("Kokoro TTS running on http://localhost:8180")
    server.serve_forever()
