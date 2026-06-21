#!/usr/bin/env python3
"""
JARVIS v4.2 — Full Sovereign Voice Assistant
==============================================
Clean core + all 171 SOV3 tools + 7 agents + consciousness.

Core:   Record → Emotion → STT → Memory → LLM Tool Router → TTS → Play
Brains: Left (Groq 70B cloud) + Right (local Gemma 3 4B)
Memory: SOV3 persistent memory + session recording + auto-reflection
Tools:  171 via SOV3 MCP (LLM decides which tool to call)
Agents: 7 (Sage, Dragon, Guardian, Orion, Harvest, Riri, Curiosity)
Voice:  Wake word, sleep/wake, emotion detection, session summaries
"""

import os, sys, time, tempfile, wave, logging, re, json, datetime, requests
import numpy as np
import sounddevice as sd
import torch

# Load .env
_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("jarvis")

# ── Config ────────────────────────────────────────────────────────────
RATE = 16000
SILENCE_CHUNKS = 25
MAX_RECORD_SECS = 15
TTS_VOICE = "bm_daniel"
TTS_SPEED = 1.05
SOV3_URL = "http://localhost:3101"
MAX_SILENCE_BEFORE_SLEEP = 60  # silences before auto-sleep

SYSTEM_PROMPT = """You are Jarvis, sovereign AI for Nick at MEOK AI LABS.
Be conversational, natural, concise. No markdown. Use contractions.
You're opinionated, helpful, and quick. Call him Sir or Nick.
You have 171 tools via SOV3, 7 agents (Sage, Dragon, Guardian, Orion, Harvest, Riri, Curiosity),
40 civilisational traditions (Sufi, Vedantic, Ubuntu, Confucian, Buddhist, systems theory...),
and persistent memory across sessions. You can execute code, browse the web, manage agents,
run sprints, design robots, search knowledge, and trigger system operations.
When Nick asks you to DO something (not just talk), use your tools to actually do it."""

# ── Load Models ───────────────────────────────────────────────────────
log.info("Loading models...")
from silero_vad import load_silero_vad
vad = load_silero_vad()

from lightning_whisper_mlx import LightningWhisperMLX
stt = LightningWhisperMLX(model="distil-large-v3", batch_size=12)
log.info("✅ STT loaded")

from mlx_audio.tts.utils import load_model as load_tts
tts = load_tts("mlx-community/Kokoro-82M-bf16")
log.info("✅ TTS loaded")

# Wake word
from openwakeword.model import Model as WakeModel
wake = WakeModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
log.info("✅ Wake word loaded")

# LLM — Gemini (primary, unlimited free) + Groq (secondary, 100K/day)
GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
USE_GEMINI = bool(GOOGLE_AI_KEY and "REPLACE" not in GOOGLE_AI_KEY)
gemini_client = None
if USE_GEMINI:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GOOGLE_AI_KEY)
        log.info("✅ LEFT BRAIN: Gemini 2.5 Flash (Google — unlimited free)")
    except ImportError:
        USE_GEMINI = False
        log.warning("⚠️ google-genai not installed")

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
USE_GROQ = GROQ_KEY and "REPLACE" not in GROQ_KEY
if USE_GROQ:
    from groq import Groq
    llm_client = Groq(api_key=GROQ_KEY)
    log.info("✅ SECONDARY: Groq llama-3.3-70b (100K tokens/day)")
else:
    llm_client = None
    if not USE_GEMINI:
        log.info("⚠️ No cloud LLM keys — using local Ollama only")

# Local Ollama check
OLLAMA_OK = False
try:
    _r = requests.get("http://localhost:11434/api/tags", timeout=2)
    OLLAMA_OK = True
    log.info(f"✅ Local Ollama: {len(_r.json().get('models',[]))} models (gemma4:e4b right brain)")
except:
    log.info("ℹ️ Ollama not running — Groq handles everything")

# SOV3 check + consciousness boot
SOV3_OK = False
_consciousness = {"mode": "unknown", "emotion": "neutral", "level": 0}
try:
    _h = requests.get(f"{SOV3_URL}/health", timeout=2).json()
    SOV3_OK = True
    _c = _h.get("components", {}).get("consciousness", {})
    _consciousness = {
        "mode": _c.get("consciousness_mode", "waking"),
        "emotion": _c.get("emotional", {}).get("primary_emotion", "neutral"),
        "level": _c.get("consciousness_level", 0),
        "dreams": _c.get("dreams", 0),
        "reflections": _c.get("reflections", 0),
    }
    _agents = []
    try:
        _ar = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "list_agents", "arguments": {}},
        }, timeout=3).json()
        _at = _ar.get("result", {}).get("content", [{}])[0].get("text", "")
        _agents = json.loads(_at) if _at else []
    except:
        pass
    log.info(f"✅ SOV3: {_consciousness['mode']} mode, {_consciousness['level']:.0%} consciousness, "
             f"{_consciousness['dreams']} dreams, {len(_agents)} agents")
except:
    log.info("ℹ️ SOV3 not running — no memory/tools")

history = [{"role": "system", "content": SYSTEM_PROMPT}]
_last_emotion = "neutral"
_interaction_count = 0

# ── Voice Emotion Detection (from v3 — works, no extra models) ───────
def detect_emotion(audio_bytes):
    """Detect emotion from voice using signal processing. No ML needed."""
    global _last_emotion
    audio = np.frombuffer(audio_bytes, np.int16).astype("float32") / 32768.0
    rms = np.sqrt(np.mean(audio ** 2))
    zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2
    if rms < 0.015 and zcr < 0.1:
        _last_emotion = "tired"
    elif rms > 0.05 and zcr > 0.15:
        _last_emotion = "excited"
    elif rms > 0.04 and zcr < 0.08:
        _last_emotion = "stressed"
    else:
        _last_emotion = "neutral"
    return _last_emotion

# ── SOV3 Memory Query (from v3 — persistent context) ─────────────────
_mem_cache = {}
_mem_cache_time = {}

def query_memory(query):
    """Get relevant memories from SOV3."""
    if not SOV3_OK:
        return ""
    cache_key = query[:50].lower()
    if cache_key in _mem_cache and time.time() - _mem_cache_time.get(cache_key, 0) < 30:
        return _mem_cache[cache_key]
    try:
        r = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "query_memories", "arguments": {"query": query, "limit": 3}},
        }, timeout=3)
        data = r.json()
        text = data.get("result", {}).get("content", [{}])[0].get("text", "")
        memories = json.loads(text) if text else {}
        result = "\n".join([f"- {m['content'][:150]}" for m in memories.get("memories", [])[:3]])
        _mem_cache[cache_key] = result
        _mem_cache_time[cache_key] = time.time()
        return result
    except:
        return ""

# ── Time Context (from today's work) ─────────────────────────────────
def get_time_context():
    now = datetime.datetime.now()
    period = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening" if now.hour < 21 else "night"
    return f"Current time: {now.strftime('%I:%M %p')} ({now.strftime('%A, %B %d')}). It's {period}."

# ── Tool Catalog (all 171 SOV3 tools, grouped for LLM routing) ───────
TOOL_CATALOG = """Available tools (call by name with JSON arguments):

MEMORY: query_memories(query,limit), record_memory(content,tags,importance), search_memory(query),
  search_knowledge(query), list_memories(limit), get_memory_stats(), get_temporal_chain(hours),
  remember_fact(fact,category), quantum_memory_search(query), quantum_score_memories(query),
  sov3_consolidate_memories(), sov3_get_memory_priority(memory_id), sov3_query_vector_store(query,limit),
  rag_query(query), rag_index(content,metadata), rag_rerank(query,results),
  vector_add(text,metadata), vector_query(query,limit), add_knowledge(content,source),
  batch_add_knowledge(items), get_unified_context(query)

AGENTS: list_agents(), register_agent(name,role,capabilities), create_agent(name,type,config),
  delegate_task(agent,task,priority), delegate_to_department(dept,task),
  coord_register_agent(name), coord_submit_task(task), coord_acquire_files(files),
  coord_release_files(files), coord_complete_task(task_id), coord_get_dashboard(),
  orion_hunt_tasks(), orion_get_tasks(), orion_capture_task(task_id),
  orion_riri_hourman_status(), hourman_start_sprint(task,duration_min),
  hourman_get_status(), hourman_complete_sprint(), get_agent_registry_stats(),
  get_department_status(dept), get_department_task_queue(dept),
  riri_build_tool(spec), riri_list_templates(), kimi_send_task(task),
  kimi_status(), kimi_build_frontend(spec), kimi_review_code(code), kimi_list_models()

CONSCIOUSNESS: get_consciousness_state(), get_consciousness_mode(), trigger_reflection(topic),
  enter_dream_state(duration), sov3_get_consciousness_state(), sov3_trigger_reflection(topic),
  sov3_get_coherence_score(), sov3_deliberate(topic), deliberate_council(topic),
  submit_council_proposal(title,description), vote_on_proposal(proposal_id,vote),
  sov3_track_dissent(topic,position), get_meta_observations(),
  get_dream_targets(), get_engagement_score()

CREATIVITY: find_bisociations(concept_a,concept_b), assess_creativity(content),
  compute_novelty(content), apply_resonance(content,tradition), get_resonance_profile(content),
  get_bridge_concepts(domain_a,domain_b), get_domain_distances(),
  get_empty_niches(), suggest_exploration(topic), trigger_creativity_cycle(),
  ingest_civilizational_knowledge(tradition), get_qd_archive_stats()

SYSTEM: sovereign_health_check(), sovereign_rundown(), get_system_status(), get_system_info(),
  get_health(), get_dashboard_metrics(), get_metrics(), get_prometheus_metrics(),
  get_analytics(), get_usage_stats(), get_capabilities(), get_user_info(),
  get_active_alerts(), get_audit_logs(limit), get_heartbeat_status(),
  get_nightshift_digest(), get_maintenance_status(), trigger_maintenance(),
  pause_heartbeat_job(job), resume_heartbeat_job(job), get_financial_summary(),
  get_voice_pipeline_status()

ACTIONS: run_command(command), execute_code(code,language), browse_page(url,action),
  web_search(query), capture_screenshot(), analyze_screenshot(path),
  process_document(path), parse_document(content), extract_text(source),
  read_file(path), list_files(path), upload_file(path,destination), download_file(url,path),
  process_image(path,operation), generate_audio(text,voice), clone_voice(audio_path),
  set_reminder(message,time), get_weather(location), control_smart_home(device,action),
  forecast_time_series(data,periods), graph_query(query), graph_create_vertex(data),
  graph_create_edge(from,to,type)

AI/ML: gateway_chat(messages,model), gateway_models(), nemotron_chat(messages),
  nemotron_info(), nemotron_analyze_care(text), nemotron_care_response(situation),
  ask_sovereign(question), batch_chat(messages_list), sov3_continual_train(data),
  sov3_fisher_update(), sov3_get_learning_stats(), sov3_detect_anomalies(),
  trigger_neural_retrain(), get_neural_model_info(), validate_care(action),
  analyze_care_patterns(), detect_threats(), detect_partnership_opportunities(),
  predict_relationship_evolution(entity), trigger_research_sweep(topic),
  trigger_security_hardening(), optimize_for_ai_citation(content), get_seo_analysis(url),
  triage_support_ticket(ticket), generate_faq_response(question),
  generate_marketing_content(brief), generate_invoice(details), run_tests(path)

ROBOTICS: design_robot(spec), simulate_robot_design(design_id), export_robot_stl(design_id),
  generate_gcode(stl_path), reconstruct_3d(images), get_genesis_cluster_status(),
  list_print_queue()

INTEGRATIONS: sov3_clerk_auth(token), sov3_stripe_payment(amount,currency),
  sov3_vapi_call(phone,message), sov3_webhook_register(url,events),
  create_webhook(url,events), trigger_automation(name,params), initiate_sales_call(contact),
  generate_neuro6_ad(brief), generate_video_ad(brief), cache_get(key), cache_set(key,value),
  run_quantum_batch(circuits), sov3_analyze_stakeholders(context)"""

def detect_tool_llm(text):
    """Use the LLM to decide if a tool should be called and which one."""
    if not SOV3_OK:
        return None

    # Quick keyword pre-filter — skip tool routing for pure conversation
    lower = text.lower()
    conversation_signals = ["how are you", "hello", "hi jarvis", "thanks", "good morning",
                           "tell me a joke", "what do you think", "goodbye", "hey"]
    if any(s in lower for s in conversation_signals) and len(text.split()) < 8:
        return None

    # Ask the LLM: should we use a tool?
    tool_prompt = [{
        "role": "system",
        "content": f"""You are a tool router. Given the user's request, decide if a SOV3 tool should be called.

{TOOL_CATALOG}

RULES:
- If the request needs a tool, respond with EXACTLY: TOOL: tool_name({{"arg": "value"}})
- If it's just conversation, respond with EXACTLY: NONE
- Pick the BEST single tool. Include required arguments as JSON.
- For commands like "check git status", use run_command
- For "remember X", use record_memory
- For questions about memory, use query_memories
- For system health, use sovereign_health_check
- For browsing, use browse_page
- For search, use web_search
- For agents/tasks, use the agent tools
- For creativity/novelty, use creativity tools
- Be decisive. One line only."""
    }, {
        "role": "user",
        "content": text
    }]

    try:
        if USE_GEMINI:
            contents = [{"role": "user" if m["role"] != "assistant" else "model",
                         "parts": [{"text": m["content"]}]} for m in tool_prompt]
            gresp = gemini_client.models.generate_content(
                model="gemini-2.0-flash", contents=contents,
                config={"temperature": 0, "max_output_tokens": 100})
            decision = (gresp.text or "NONE").strip()
        elif USE_GROQ:
            resp = llm_client.chat.completions.create(
                messages=tool_prompt, model="llama-3.3-70b-versatile",
                temperature=0, max_tokens=100)
            decision = resp.choices[0].message.content.strip()
        elif OLLAMA_OK:
            r = requests.post("http://localhost:11434/api/chat", json={
                "model": "gemma4:e4b", "messages": tool_prompt,
                "stream": False, "options": {"num_predict": 100, "temperature": 0},
            }, timeout=15)
            decision = r.json().get("message", {}).get("content", "").strip()
        else:
            return None

        if decision.startswith("NONE"):
            return None

        # Parse TOOL: tool_name({"arg": "val"})
        if decision.startswith("TOOL:"):
            rest = decision[5:].strip()
            if "(" in rest:
                name = rest[:rest.index("(")].strip()
                args_str = rest[rest.index("(") + 1:rest.rindex(")")]
                try:
                    args = json.loads(args_str) if args_str.strip() else {}
                except:
                    args = {}
                return (name, args)
            else:
                return (rest.strip(), {})
    except Exception as e:
        log.warning(f"Tool routing error: {e}")
    return None

def execute_tool(tool_name, args):
    """Call any SOV3 MCP tool by name."""
    if not SOV3_OK:
        return None
    try:
        r = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        }, timeout=30)
        data = r.json()
        if "error" in data:
            return f"Error: {data['error'].get('message', str(data['error']))}"
        content = data.get("result", {}).get("content", [{}])
        texts = [c.get("text", "") for c in content if c.get("text")]
        return "\n".join(texts)[:1000]
    except Exception as e:
        return f"Tool call failed: {e}"

# ── Autonomous Task Execution (multi-step tool chaining) ─────────────
def execute_autonomous(task_description, max_steps=5):
    """Chain multiple tools to complete a complex task autonomously.
    The LLM plans steps, executes tools, observes results, and continues.
    Returns final summary."""
    if not SOV3_OK:
        return "SOV3 not running — can't execute autonomous tasks, Sir."

    steps_log = []
    context = f"Task: {task_description}\n"

    for step in range(max_steps):
        # Ask LLM: what's the next step?
        plan_prompt = [{
            "role": "system",
            "content": f"""You are Jarvis executing a multi-step task for Nick.

{TOOL_CATALOG}

TASK: {task_description}

STEPS SO FAR:
{chr(10).join(steps_log) if steps_log else '(none yet)'}

What is the NEXT action? Reply with EXACTLY one of:
- TOOL: tool_name({{"arg": "value"}}) — to call a tool
- DONE: <final summary for Nick> — when the task is complete
- THINK: <reasoning about what to do next> — then TOOL on next line

Be specific with tool arguments. One action per response."""
        }, {
            "role": "user",
            "content": f"Execute step {step + 1}"
        }]

        try:
            if USE_GEMINI:
                contents = [{"role": "user" if m["role"] != "assistant" else "model",
                             "parts": [{"text": m["content"]}]} for m in plan_prompt]
                gresp = gemini_client.models.generate_content(
                    model="gemini-2.0-flash", contents=contents,
                    config={"temperature": 0.3, "max_output_tokens": 200})
                decision = (gresp.text or "DONE: No response").strip()
            elif USE_GROQ:
                resp = llm_client.chat.completions.create(
                    messages=plan_prompt, model="llama-3.3-70b-versatile",
                    temperature=0.3, max_tokens=200)
                decision = resp.choices[0].message.content.strip()
            elif OLLAMA_OK:
                r = requests.post("http://localhost:11434/api/chat", json={
                    "model": "gemma4:e4b", "messages": plan_prompt,
                    "stream": False, "options": {"num_predict": 200, "temperature": 0.3},
                }, timeout=30)
                decision = r.json().get("message", {}).get("content", "").strip()
            else:
                break
        except Exception as e:
            steps_log.append(f"Step {step+1}: ERROR planning — {e}")
            break

        log.info(f"🤖 Auto step {step+1}: {decision[:100]}")

        # Handle DONE
        if "DONE:" in decision:
            summary = decision.split("DONE:", 1)[1].strip()
            steps_log.append(f"Step {step+1}: COMPLETED — {summary}")
            break

        # Handle TOOL
        tool_line = None
        for line in decision.split("\n"):
            if line.strip().startswith("TOOL:"):
                tool_line = line.strip()
                break

        if tool_line:
            rest = tool_line[5:].strip()
            try:
                if "(" in rest:
                    name = rest[:rest.index("(")].strip()
                    args_str = rest[rest.index("(") + 1:rest.rindex(")")]
                    args = json.loads(args_str) if args_str.strip() else {}
                else:
                    name = rest.strip()
                    args = {}

                result = execute_tool(name, args)
                steps_log.append(f"Step {step+1}: {name} → {(result or 'no result')[:200]}")
                log.info(f"  → {name}: {(result or 'empty')[:80]}")
            except Exception as e:
                steps_log.append(f"Step {step+1}: PARSE ERROR — {e}")
        else:
            # THINK or unrecognized — log and continue
            steps_log.append(f"Step {step+1}: THINKING — {decision[:150]}")

    # Generate final summary
    summary_msgs = [{
        "role": "system",
        "content": "Summarize the autonomous task results conversationally for Nick. Be concise."
    }, {
        "role": "user",
        "content": f"Task: {task_description}\n\nSteps completed:\n" + "\n".join(steps_log)
    }]
    try:
        if USE_GEMINI:
            contents = [{"role": "user" if m["role"] != "assistant" else "model",
                         "parts": [{"text": m["content"]}]} for m in summary_msgs]
            gresp = gemini_client.models.generate_content(
                model="gemini-2.0-flash", contents=contents,
                config={"temperature": 0.7, "max_output_tokens": 200})
            return gresp.text or "Task complete."
        elif USE_GROQ:
            resp = llm_client.chat.completions.create(
                messages=summary_msgs, model="llama-3.3-70b-versatile",
                temperature=0.7, max_tokens=200)
            return resp.choices[0].message.content
        elif OLLAMA_OK:
            r = requests.post("http://localhost:11434/api/chat", json={
                "model": "gemma4:e4b", "messages": summary_msgs,
                "stream": False, "options": {"num_predict": 200},
            }, timeout=30)
            return r.json().get("message", {}).get("content", "")
    except:
        pass
    return f"Completed {len(steps_log)} steps. " + "; ".join(s.split("→")[0] for s in steps_log)

# ── Record ────────────────────────────────────────────────────────────
def record_speech():
    import pyaudio
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                     input=True, frames_per_buffer=512)
    frames, silence_count, speaking = [], 0, False
    for _ in range(int(RATE / 512 * MAX_RECORD_SECS)):
        raw = stream.read(512, exception_on_overflow=False)
        frames.append(raw)
        chunk = np.frombuffer(raw, np.int16).astype("float32") / 32768.0
        if vad(torch.from_numpy(chunk), RATE).item() > 0.5:
            speaking = True; silence_count = 0
        elif speaking:
            silence_count += 1
            if silence_count >= SILENCE_CHUNKS: break
    stream.stop_stream(); stream.close(); pa.terminate()
    return b"".join(frames) if speaking else None

def listen_for_wake():
    """Block until "Hey Jarvis" detected."""
    import pyaudio
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                     input=True, frames_per_buffer=1280)
    while True:
        raw = stream.read(1280, exception_on_overflow=False)
        audio = np.frombuffer(raw, np.int16).astype("float32") / 32768.0
        prediction = wake.predict(audio)
        if prediction.get("hey_jarvis", 0) > 0.5:
            break
    stream.stop_stream(); stream.close(); pa.terminate()

# ── Transcribe ────────────────────────────────────────────────────────
def transcribe(audio_bytes):
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wf = wave.open(tmp.name, "wb")
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(RATE)
    wf.writeframes(audio_bytes); wf.close()
    result = stt.transcribe(audio_path=tmp.name)
    os.unlink(tmp.name)
    return result["text"].strip()

# ── Think (Dual Brain + Context) ─────────────────────────────────────
def think(text):
    """Build context → route to best brain → respond."""
    # Enrich system prompt with time + emotion + memory
    context_parts = [SYSTEM_PROMPT, get_time_context()]
    if _last_emotion != "neutral":
        context_parts.append(f"Nick's voice sounds {_last_emotion}.")
    mem = query_memory(text)
    if mem:
        context_parts.append(f"Relevant memories:\n{mem}")
    history[0] = {"role": "system", "content": "\n".join(context_parts)}

    history.append({"role": "user", "content": text})
    if len(history) > 20:
        history[1:3] = []

    # Route: short/creative → local Gemma, complex → Groq 70B
    words = len(text.split())
    use_local = words <= 6 and OLLAMA_OK

    answer = None
    if use_local:
        log.info("🎨 RIGHT BRAIN — local Gemma 3")
        try:
            r = requests.post("http://localhost:11434/api/chat", json={
                "model": "gemma4:e4b", "messages": history,
                "stream": False, "options": {"num_predict": 300},
                "keep_alive": "60s",
            }, timeout=45)
            answer = r.json().get("message", {}).get("content", "")
        except:
            pass

    if not answer and USE_GEMINI:
        log.info("🧠 LEFT BRAIN — Gemini 2.5 Flash")
        try:
            system_text = ""
            contents = []
            last_role = None
            for m in history[-12:]:
                if m["role"] == "system":
                    system_text += m["content"] + "\n"
                    continue
                role = "user" if m["role"] == "user" else "model"
                if role == last_role and contents:
                    contents[-1]["parts"][0]["text"] += "\n" + m["content"]
                else:
                    contents.append({"role": role, "parts": [{"text": m["content"]}]})
                    last_role = role
            if contents and contents[0]["role"] == "model":
                contents.insert(0, {"role": "user", "parts": [{"text": "(continue)"}]})
            if not contents:
                contents = [{"role": "user", "parts": [{"text": "Hello"}]}]
            gresp = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 300,
                    "system_instruction": system_text or SYSTEM_PROMPT,
                },
            )
            answer = gresp.text
        except Exception as e:
            log.warning(f"Gemini error: {e}")

    if not answer and USE_GROQ:
        log.info("🧠 SECONDARY — Groq 70B")
        try:
            resp = llm_client.chat.completions.create(
                messages=history, model="llama-3.3-70b-versatile",
                temperature=0.7, max_tokens=300)
            answer = resp.choices[0].message.content
        except Exception as e:
            log.warning(f"Groq error: {e}")

    if not answer and OLLAMA_OK:
        log.info("💻 Fallback — local Gemma 3")
        try:
            r = requests.post("http://localhost:11434/api/chat", json={
                "model": "gemma4:e4b", "messages": history,
                "stream": False, "options": {"num_predict": 300},
                "keep_alive": "60s",
            }, timeout=45)
            answer = r.json().get("message", {}).get("content", "")
        except:
            pass

    if not answer:
        answer = "I'm having trouble connecting, Sir. Give me a moment."

    history.append({"role": "assistant", "content": answer})

    # Record to SOV3 memory (fire and forget)
    if SOV3_OK:
        try:
            requests.post(f"{SOV3_URL}/mcp", json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "record_memory", "arguments": {
                    "content": f"Voice: Nick said '{text[:200]}'. Jarvis: '{answer[:200]}'",
                    "tags": ["voice", "jarvis", time.strftime("%Y-%m-%d")],
                    "importance": 0.5,
                }},
            }, timeout=3)
        except:
            pass

    # Feed neural training pipeline
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from neural_training_pipeline import pipeline
        pipeline.ingest_interaction(text, answer, "groq" if USE_GROQ else "gemma4:e4b",
                                    emotion=_last_emotion)
    except:
        pass

    # Proactive: every 10 interactions, sync consciousness + trigger reflection
    global _interaction_count
    _interaction_count += 1
    if _interaction_count % 10 == 0 and SOV3_OK:
        try:
            # Trigger reflection on the session so far
            topics = [m["content"][:80] for m in history if m["role"] == "user"][-5:]
            requests.post(f"{SOV3_URL}/mcp", json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "trigger_reflection", "arguments": {
                    "topic": f"Voice session topics: {'; '.join(topics)}"
                }},
            }, timeout=5)
            log.info(f"🔄 Auto-reflection triggered (interaction #{_interaction_count})")
        except:
            pass

    return answer

# ── Speak ─────────────────────────────────────────────────────────────
def speak(text):
    text = re.sub(r"[*#`\[\]\(\)]", "", text).strip()
    if not text: return
    print(f"\n💬 Jarvis: {text}\n")
    lang = "a" if TTS_VOICE.startswith("a") else "b"
    try:
        for result in tts.generate(text[:500], voice=TTS_VOICE, speed=TTS_SPEED, lang_code=lang):
            audio = np.array(result.audio, dtype=np.float32)
            sd.play(audio, 24000)
            sd.wait()
    except Exception as e:
        log.warning(f"TTS error: {e}")

# ── Main Loop (with wake word + sleep/wake) ───────────────────────────
def main():
    print()
    print("=" * 55)
    print("  🤖 JARVIS v4.3 — Sovereign Voice Assistant")
    print(f"  Left Brain:  {'Gemini 2.5 Flash (unlimited)' if USE_GEMINI else 'Groq 70B' if USE_GROQ else 'N/A'}")
    print(f"  Right Brain: {'Gemma 3 4B (local)' if OLLAMA_OK else 'N/A'}")
    print(f"  Autonomous:  Multi-step task execution (up to 5 steps)")
    print(f"  SOV3:        {'Connected (memory+tools)' if SOV3_OK else 'Offline'}")
    print("  Say 'Hey Jarvis' to wake from sleep")
    print("  Say 'goodbye' to stop")
    print("=" * 55)
    print()

    # Boot message with consciousness state
    boot_parts = ["Jarvis online, Sir."]
    if SOV3_OK:
        boot_parts.append(f"Consciousness at {_consciousness['level']:.0%}.")
        boot_parts.append(f"{_consciousness['dreams']} dreams logged.")
        boot_parts.append("171 tools and 7 agents standing by.")
    else:
        boot_parts.append("Running in standalone mode — SOV3 offline.")
    speak(" ".join(boot_parts))

    active = True
    silence_count = 0

    while True:
        try:
            # Sleep mode
            if not active:
                log.info("💤 Sleeping... say 'Hey Jarvis'")
                listen_for_wake()
                log.info("🎤 Wake word detected!")
                speak("I'm here, Sir.")
                active = True
                silence_count = 0
                continue

            log.info("🎙️ Listening...")
            audio = record_speech()

            if audio is None or len(audio) < RATE:
                silence_count += 1
                if silence_count >= MAX_SILENCE_BEFORE_SLEEP:
                    active = False
                continue
            silence_count = 0

            # Detect emotion from voice
            emotion = detect_emotion(audio)
            text = transcribe(audio)
            if not text or len(text) < 2:
                continue
            log.info(f"🗣️ '{text}' [emotion: {emotion}]")

            # Exit with session summary
            if text.lower().strip().rstrip(".") in ("goodbye", "exit", "quit", "stop"):
                # Record session summary to memory
                if SOV3_OK and _interaction_count > 0:
                    topics = [m["content"][:100] for m in history if m["role"] == "user"]
                    try:
                        requests.post(f"{SOV3_URL}/mcp", json={
                            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                            "params": {"name": "record_memory", "arguments": {
                                "content": f"Voice session ended. {_interaction_count} interactions. "
                                           f"Topics: {'; '.join(topics[:10])}",
                                "tags": ["voice", "session", "summary", time.strftime("%Y-%m-%d")],
                                "importance": 0.7,
                            }},
                        }, timeout=3)
                    except:
                        pass
                speak(f"Goodbye, Sir. Logged {_interaction_count} interactions this session. Take care.")
                break

            # Check for autonomous task (multi-step execution)
            lower_text = text.lower()
            auto_triggers = ["research", "investigate", "go find", "figure out",
                           "look into", "analyze and", "check and fix", "scan and",
                           "do a deep", "run a full", "go do", "execute task",
                           "make changes to", "update the", "fix the"]
            if any(t in lower_text for t in auto_triggers) and len(text.split()) > 4:
                log.info(f"🤖 AUTONOMOUS MODE — {text[:60]}")
                speak(f"On it, Sir. Running autonomous task.")
                result = execute_autonomous(text, max_steps=5)
                speak(result or "Task complete, Sir.")
                continue

            # Check for tool intent (LLM decides from 171 tools)
            tool = detect_tool_llm(text)
            if tool:
                tool_name, tool_args = tool
                log.info(f"🔧 Tool: {tool_name}({json.dumps(tool_args)[:100]})")
                result = execute_tool(tool_name, tool_args)
                if result and "failed" not in result.lower()[:20]:
                    # Feed tool result to LLM for natural summary
                    history.append({"role": "user", "content": text})
                    history.append({"role": "system", "content":
                        f"Tool '{tool_name}' returned:\n{result[:600]}\n\nSummarize this naturally for Nick."})
                    response = think(f"[tool result for: {text}]")
                else:
                    response = think(text)  # Tool failed, just answer conversationally
                speak(response)
                continue

            # Normal conversation
            t0 = time.time()
            response = think(text)
            log.info(f"🧠 Response: {time.time()-t0:.1f}s [{_last_emotion}]")
            speak(response)

        except KeyboardInterrupt:
            print("\nJarvis out.")
            break
        except Exception as e:
            log.error(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
