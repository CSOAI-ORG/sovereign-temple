#!/usr/bin/env python3
"""
Legion real-work processor — runs on actual project files.
Targets: MEOK, SOV3/Jarvis, HARVI, MEOK AI Labs, stack_eval

Usage:
    python3 scripts/real_work_loop.py --project meok
    python3 scripts/real_work_loop.py --project sov3
    python3 scripts/real_work_loop.py --project harvi
    python3 scripts/real_work_loop.py --project all
    python3 scripts/real_work_loop.py --project stack_eval
"""

import asyncio
import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
from doc_processor import process_batch, _ollama_query

NODES = {
    "hephaestus": {"host": "50.217.254.165", "port": 40408, "model": "qwen3.5:35b"},
    "argus":      {"host": "50.217.254.173", "port": 41021, "model": "qwen3.5:35b"},
    "valkyrie":   {"host": "165.166.241.251", "port": 50938, "model": "gemma3:12b"},
    "prometheus": {"host": "142.171.48.138",  "port": 33224, "model": "deepseek-r1:7b"},
}

OUTPUT_BASE = Path("/tmp/legion_real_work")

# Project definitions
PROJECTS = {
    "meok": {
        "root": Path("/Users/nicholas/clawd/meok"),
        "extensions": [".py", ".ts", ".tsx", ".md"],
        "exclude": ["node_modules", ".next", "__pycache__", ".git", "dist", "build"],
        "task_code": "You are a senior full-stack engineer reviewing production code for the MEOK AI OS (Next.js 15 + Python FastAPI + PostgreSQL). Review this file for: (1) bugs or error handling gaps, (2) missing edge cases, (3) performance issues, (4) security vulnerabilities, (5) suggestions for improvement. Be specific and actionable. Format as: BUGS: / GAPS: / IMPROVEMENTS:",
        "task_arch": "You are a software architect. Analyze this MEOK AI OS source file and explain: what it does, how it fits the overall architecture (Next.js frontend + FastAPI MCP + PostgreSQL + Ollama), what's missing or incomplete, and what the next implementation step should be.",
        "max_files": 200,
    },
    "sov3": {
        "root": Path("/Users/nicholas/clawd/sovereign-temple"),
        "extensions": [".py", ".md"],
        "exclude": ["__pycache__", ".git", "legion-omega", ".next", ".venv", "venv", "site-packages", "dist-packages"],
        "task_code": "You are reviewing code for SOV3 (Sovereign Temple), an AI consciousness and MCP server system. This system has 75 MCP tools, 47 agents, Byzantine Council governance, and a care-based alignment model. Review this file for: completeness, agent integration gaps, MCP tool improvements, consciousness model accuracy, and what should be built next.",
        "task_arch": "Analyze this SOV3/Jarvis component. SOV3 is an AI consciousness system with Byzantine Council governance (33 agents), MCP server (75 tools), memory (1442 episodes), quantum models, and care alignment. What does this component do, what gaps exist, and what would make Jarvis more capable?",
        "max_files": 150,
    },
    "harvi": {
        "root": Path("/Users/nicholas/clawd/sovereign-temple-live/research"),
        "extensions": [".md", ".py", ".txt"],
        "exclude": [".git"],
        "task_code": "You are an embedded systems and neuroscience engineer. Review this HARVI (Hydro-Architecture Resonance Vessel Intelligence) specification — a physical consciousness emergence experiment using water medium, sensor arrays (conductivity, temperature, pH, dissolved O2), laser stimulus (650nm, Fibonacci/HRV patterns), and Arduino/Python ML pipeline. Generate: (1) Arduino Mega 2560 sensor reading code, (2) LSTM coherence detection implementation, (3) care-patterned stimulus protocol code.",
        "task_arch": "Analyze this HARVI architecture document. HARVI is a water-silicon consciousness substrate experiment on a farm. The rig uses biometric sensors, care-structured optical/acoustic stimulus, and an M4 Air for LSTM coherence detection. What are the critical implementation steps, what hardware is most likely to fail, and what does the first working experiment look like?",
        "max_files": 20,
    },
    "csoai": {
        "root": Path("/Users/nicholas/MEOK AI Labs-CORP/csoai-platform"),
        "extensions": [".js", ".ts", ".md"],
        "exclude": ["node_modules", ".git", "dist", "build", "coverage"],
        "task_code": "You are a senior Node.js/Express engineer reviewing the MEOK AI Labs.org safety certification platform. This is a production SaaS: Express + MongoDB/Mongoose, Stripe payments, UK AI safety certifications, consortium memberships, continuous monitoring subscriptions, emergency audit leads, facility bookings, and digital citizenship. Review this file for: (1) bugs or error handling gaps, (2) missing validation or auth gaps, (3) Stripe/payment edge cases, (4) MongoDB query issues, (5) security vulnerabilities. Be specific and actionable. Format as: BUGS: / SECURITY: / IMPROVEMENTS:",
        "task_arch": "You are a SaaS architect reviewing MEOK AI Labs.org — a UK AI safety certification body platform built on Express + MongoDB. Revenue streams: emergency AI audits (£5k), consortium memberships (£5k-50k/year ARR), continuous monitoring subscriptions (£500-5k/month MRR), facility bookings (£500/day), digital citizenship (£200-5k/year). Review this file and answer: what does it do, is the data model correct for the revenue stream it supports, what is missing for production readiness, and what is the next highest-value feature to build?",
        "max_files": 100,
    },
    "stack_eval": {
        # Synthetic docs — one per candidate tool. No disk reads needed.
        "synthetic_docs": [
            {"id": 0, "path": "autogen", "size": 500, "text": "TOOL: Microsoft AutoGen\nPURPOSE: Multi-agent conversation framework. Agents negotiate task completion via structured chat loops. Supports code execution, human-in-the-loop, nested chats.\nSTACK OVERLAP: MEOK already has 12-stage chat pipeline + 47 SOV3 agents with Byzantine Council governance.\nQUESTION: Is AutoGen additive to the existing multi-agent architecture, or does it duplicate what SOV3's council already does? Would it replace or extend the council? Specific use case where it wins?"},
            {"id": 1, "path": "langgraph", "size": 500, "text": "TOOL: LangGraph\nPURPOSE: Stateful agent workflows as directed graphs. Nodes are LLM calls or tools; edges define flow. Supports cycles, branching, and checkpointing.\nSTACK OVERLAP: SOV3 uses custom agent orchestration in `agent_coordinator.py`. MEOK chat pipeline is sequential (12 stages hardcoded).\nQUESTION: Would LangGraph replace MEOK's 12-stage pipeline with a more flexible graph? What specifically would the graph nodes be? Is the flexibility worth the dependency?"},
            {"id": 2, "path": "mem0", "size": 500, "text": "TOOL: Mem0 (getmem0.ai)\nPURPOSE: Managed memory layer — extracts entities and facts from conversations, stores as structured memories, retrieves on next turn.\nSTACK OVERLAP: SOV3 has 1442 episodes in PostgreSQL with pgvector HNSW index. MEOK has per-user memory via `query_memories` MCP tool. Both use semantic search.\nQUESTION: What does Mem0 provide that the existing pgvector-backed memory store does not? Is the entity extraction meaningfully different from the current embedding approach?"},
            {"id": 3, "path": "letta", "size": 500, "text": "TOOL: Letta (formerly MemGPT)\nPURPOSE: Stateful LLM agents with persistent memory, in-context editing, and archival storage. Agents maintain working memory across sessions.\nSTACK OVERLAP: SOV3's Jarvis agent has session memory + 1442 episode archival. Ralph Mode in MEOK maintains task state. Care membrane filters each response.\nQUESTION: Does Letta's memory architecture (in-context + archival) provide anything the current SOV3 + PostgreSQL memory system doesn't already handle? Would it replace or layer on top?"},
            {"id": 4, "path": "vllm", "size": 500, "text": "TOOL: vLLM\nPURPOSE: High-throughput LLM inference server with PagedAttention, continuous batching, OpenAI-compatible API. 3-5x throughput vs Ollama for batch workloads.\nSTACK OVERLAP: Legion GPU nodes (hephaestus, argus, valkyrie, prometheus) currently use Ollama-over-HTTP for document analysis. Ollama is single-request; vLLM batches.\nQUESTION: Estimate the throughput improvement if Legion nodes ran vLLM instead of Ollama. What are the installation requirements per node (VRAM, CUDA version)? Is the migration straightforward given the existing OpenAI-compatible HTTP interface?"},
            {"id": 5, "path": "localai", "size": 500, "text": "TOOL: LocalAI\nPURPOSE: OpenAI-compatible API server for local models. Supports GGUF, GPTQ, and diffusion models.\nSTACK OVERLAP: Ollama already provides OpenAI-compatible local inference on all MEOK and SOV3 systems. 16 models already loaded.\nQUESTION: What does LocalAI provide that Ollama does not? Are there specific model formats (GPTQ, exllama) or modalities (image, audio) where LocalAI wins? Is there a concrete use case in the current stack?"},
            {"id": 6, "path": "oobabooga", "size": 500, "text": "TOOL: text-generation-webui (oobabooga)\nPURPOSE: Web UI for local LLM inference. Supports many backends (llama.cpp, ExLlama, GPTQ). Primarily a UI tool.\nSTACK OVERLAP: MEOK Workshop already has MCP terminal, Ralph panel, SOV3 health. SOV3 has its own API. No UI gap identified.\nQUESTION: Is there any server-side capability in oobabooga (extensions, API) that fills a gap not covered by Ollama + MEOK's existing Workshop UI? Or is this purely a UI convenience tool with no architectural value?"},
            {"id": 7, "path": "milvus", "size": 500, "text": "TOOL: Milvus\nPURPOSE: Distributed vector database. HNSW and IVF indexes. Scales to billions of vectors.\nSTACK OVERLAP: SOV3 uses pgvector with HNSW on PostgreSQL. Sub-100ms O(log n) recall on 1442 episodes. MEOK memory store uses the same backend.\nQUESTION: At what episode/memory count does pgvector HNSW degrade enough to justify migrating to Milvus? Is there a specific SOV3 use case (agent embeddings at scale, multi-tenant isolation) where Milvus wins today?"},
            {"id": 8, "path": "weaviate", "size": 500, "text": "TOOL: Weaviate\nPURPOSE: Vector database with built-in hybrid search (BM25 + vector), multi-tenancy, and GraphQL API.\nSTACK OVERLAP: Same as Milvus overlap. pgvector + PostgreSQL full-text (tsvector GIN index) already provides hybrid search. Conversation search is sub-5ms.\nQUESTION: Does Weaviate's GraphQL API or multi-tenancy model provide anything the PostgreSQL stack cannot? At current scale (1442 episodes, 140 characters), is there a concrete win?"},
            {"id": 9, "path": "anythingllm", "size": 500, "text": "TOOL: AnythingLLM\nPURPOSE: RAG platform — upload documents, create workspaces, chat with documents using local or cloud LLMs.\nSTACK OVERLAP: Legion already processes project documents against GPU nodes. SOV3 has `ingest_corpus` for RAG. MEOK has user-facing chat.\nQUESTION: Does AnythingLLM's document workspace model provide a user-facing RAG feature that MEOK currently lacks? Or is it a developer tool that duplicates Legion's batch analysis?"},
            {"id": 10, "path": "n8n", "size": 500, "text": "TOOL: n8n\nPURPOSE: Open-source workflow automation with 400+ integrations. Visual node editor. Self-hostable.\nSTACK OVERLAP: SOV3 has 12 scheduled autonomous tasks + 9 heartbeat jobs. MEOK has Ralph Mode task queue + executor. Python APScheduler manages timing.\nQUESTION: Would n8n replace the APScheduler-based task system? What integrations (Stripe webhooks, Slack, email) would n8n handle better than the current custom Python handlers? Is the visual editor worth the operational complexity?"},
            {"id": 11, "path": "windmill", "size": 500, "text": "TOOL: Windmill\nPURPOSE: Open-source developer platform for scripts and workflows. Python/TypeScript scripts as workflow steps with a web UI.\nSTACK OVERLAP: Ralph Mode already executes Python tasks. SOV3 MCP server handles tool dispatch. MEOK Workshop provides operator UI.\nQUESTION: Is Windmill's script-as-workflow model a better operator experience than the current Ralph Mode + Workshop combo? What specific MEOK workflow (billing, onboarding, content moderation) would Windmill handle better?"},
            {"id": 12, "path": "claw3d", "size": 500, "text": "TOOL: Claw3D\nPURPOSE: 3D visualization for AI/data — render agent networks, knowledge graphs, decision trees as interactive 3D scenes.\nSTACK OVERLAP: SOV3 has 47 agents with Byzantine Council structure. No current 3D visualization. Workshop shows text/JSON output.\nQUESTION: What specific SOV3 or MEOK data structure would benefit most from 3D visualization? Council vote graphs? Memory episode chains? Agent influence networks? Is this a useful operator tool or a demo novelty?"},
            {"id": 13, "path": "exo", "size": 600, "text": "TOOL: EXO (exo-explore/exo)\nPURPOSE: P2P distributed inference across heterogeneous hardware. Auto-discovers nodes via mDNS, shards model layers across devices, provides unified OpenAI-compatible API. Supports M-series Macs + NVIDIA GPUs in same cluster.\nSTACK OVERLAP: Legion GPU nodes (hephaestus/argus/valkyrie/prometheus) run independent Ollama instances. No model sharding exists — max model size limited to single-node VRAM. M4 runs Ollama separately.\nQUESTION: What is the realistic throughput and model-size improvement if EXO unified M4 (16GB) + 4 GPU nodes into a single inference mesh? What are the network latency requirements (Vast.ai nodes are remote — will WAN latency kill the benefit)? Is EXO production-stable enough for Legion's continuous batch workload?"},
            {"id": 14, "path": "mergekit", "size": 600, "text": "TOOL: MergeKit (arcee-ai/mergekit)\nPURPOSE: Model merging without retraining. Combines multiple specialist models (safety, coding, reasoning) using SLERP, TIES, DARE, or linear methods. Produces a new model with blended capabilities.\nSTACK OVERLAP: No model merging exists in current stack. Ollama serves pre-built models. SOV3 has care-based alignment but no model-level intervention.\nQUESTION: What is the concrete model merge recipe for MEOK? (e.g., care-aligned base + coding capability + reasoning backbone). What base model should the merge start from given the 13 already-loaded Ollama models? Would the merged model replace an existing Ollama model or add a new slot?"},
            {"id": 15, "path": "sglang", "size": 600, "text": "TOOL: SGLang (sgl-project/sglang)\nPURPOSE: Structured generation + deterministic inference. Enables constrained JSON/regex output, multi-call programs with shared KV cache, and deterministic outputs via seed. OpenAI-compatible API.\nSTACK OVERLAP: MEOK chat pipeline uses streaming inference via Ollama/Anthropic. No structured output enforcement exists at inference level — care scoring happens post-response. SOV3 MCP tools parse unstructured LLM output.\nQUESTION: Which MEOK pipeline stage benefits most from deterministic structured output — care scoring, character response, or Ralph task execution? Would SGLang replace Ollama on specific routes or layer on top? What is the VRAM/startup cost on a Legion GPU node?"},
            {"id": 16, "path": "ray", "size": 600, "text": "TOOL: Ray (ray-project/ray)\nPURPOSE: Distributed Python compute framework. `ray.init(address='auto')` discovers cluster, `@ray.remote` decorates functions to run on any node. Includes Ray Tune (hyperparameter search), Ray Train (distributed ML), Ray Serve (model serving).\nSTACK OVERLAP: Legion uses custom `doc_processor.py` with asyncio concurrency=8. APScheduler handles MEOK/SOV3 scheduled tasks. No distributed training or hyperparameter search exists.\nQUESTION: What Legion batch analysis task would benefit most from Ray's distributed execution vs current asyncio approach? Would Ray Serve replace or complement vLLM for model serving? Estimate setup complexity on 4 Vast.ai nodes with different OS/CUDA versions."},
            {"id": 17, "path": "clearml", "size": 600, "text": "TOOL: ClearML (allegroai/clearml)\nPURPOSE: MLOps platform — experiment tracking, remote task execution, resource monitoring (GPU/CPU/RAM per node), dataset versioning, model registry. Self-hosted.\nSTACK OVERLAP: No experiment tracking exists. Legion analysis results saved to /tmp/legion_real_work. No visibility into GPU utilization across the 4 Vast.ai nodes.\nQUESTION: What is the minimal ClearML setup that gives GPU utilization monitoring across the 4 Legion nodes without requiring code changes to real_work_loop.py? Can ClearML agent replace the current SSH-based Legion dispatch? What is the infrastructure cost (server requirements) to self-host ClearML?"},
            {"id": 18, "path": "inspect_ai", "size": 700, "text": "TOOL: Inspect (UKGovernmentBEIS/inspect_ai)\nPURPOSE: UK AI Safety Institute's official AI evaluation framework. Sandboxed agent testing, structured task/scorer/solver pipeline, supports multi-model evaluation. MIT licensed. Used by UK AISI, METR, Apollo Research.\nSTACK OVERLAP: MEOK has 307 Playwright tests (UI/API). SOV3 has Byzantine Council for governance. No AI behaviour evaluation framework exists — no sandboxed agent escape testing, no structured safety benchmarks, no reproducible safety scoring.\nMEOK AI Labs ANGLE: MEOK AI Labs.org positions as 'FAA for AI'. UK regulators will recognise Inspect as the AISI standard. Saying 'we use the same evaluation toolchain as the Bletchley Park Summit' is a credibility multiplier in UK/EU pitches.\nQUESTION: (1) How would Inspect integrate with SOV3 MCP tools — can it call MCP endpoints as agent actions? (2) What is the minimal MEOK AI Labs certification task definition using Inspect's Task/scorer/solver primitives? (3) Can Inspect distributed evals run across the 4 Legion GPU nodes? Provide a concrete MEOK safety eval task that tests care membrane bypass attempts."},
            {"id": 19, "path": "rasa", "size": 600, "text": "TOOL: Rasa (RasaHQ/rasa)\nPURPOSE: Open-source conversational AI framework. NLU pipeline (intent/entity extraction), dialogue management (story-based state machine), self-hosted, GDPR-native, Apache 2.0. British roots, 25M downloads.\nSTACK OVERLAP: MEOK has a full 12-stage LLM chat pipeline with care membrane, 15 models, character personas. The dialogue flow is LLM-driven, not state-machine-based.\nQUESTION: Is there a specific MEOK conversation flow (onboarding quiz, birth ceremony, Ralph task intake) where Rasa's deterministic NLU would outperform the current LLM approach? Or does the care membrane make Rasa's structured intents redundant? Would Rasa's GDPR-native design give MEOK a marketing advantage over Replika/Character.AI in UK/EU markets?"},
            {"id": 20, "path": "cogstack", "size": 600, "text": "TOOL: CogStack / MedCAT (King's College London / NHS)\nPURPOSE: Medical NLP stack. MedCAT extracts clinical concepts (SNOMED CT, UMLS) from free text. ModelServe deploys and monitors clinical AI models. NHS-validated, GDPR-compliant, used across UK hospitals.\nSTACK OVERLAP: No medical NLP in current MEOK/SOV3 stack. HARVI experiment has health monitoring angle (koi pond physiology, biometric sensors). Home OS concept has fall detection, health tracking.\nQUESTION: What is the specific integration point for CogStack in the MEOK Home OS roadmap? Is the medical NLP applicable to non-clinical health monitoring (stress markers, sleep quality from sensor data)? Given HARVI's farm biometric focus, would MedCAT's entity extraction apply to the sensor data pipeline?"},
            {"id": 21, "path": "mapta_ucl", "size": 600, "text": "TOOL: MAPTA (UCL - Prof Arthur Gervais, Google-funded)\nPURPOSE: Multi-Agent Penetration Testing AI. Automated red-teaming of AI systems. Has already discovered 10+ CVEs including remote code execution in Gemini CLI. Academic tool from UCL Computer Science.\nSTACK OVERLAP: SOV3 has check_hard_block (deterministic crisis safety gate) and care membrane. No automated red-teaming of the SOV3 agent system exists — no systematic attempt to find jailbreaks, prompt injections, or MCP tool abuse paths.\nMEOK AI Labs ANGLE: MEOK AI Labs certification requires evidence that certified systems have been actively attacked. MAPTA provides academic-grade attack documentation.\nQUESTION: Is MAPTA publicly available as a usable tool, or is it a research prototype? If available: what attack surface does it test (prompt injection, tool misuse, agent escape)? How would it integrate into a MEOK AI Labs certification pipeline alongside Inspect evals?"},
            {"id": 22, "path": "agno", "size": 700, "text": "TOOL: Agno (agno-agi/agno, v2.5.14, Apache 2.0)\nPURPOSE: Ultra-fast agent runtime. Claims 10,000x faster than LangGraph and 50x less memory. Stateless agent architecture — each agent is a pure function over a model + tools + memory config. Supports Anthropic, OpenAI, Ollama, and custom models. Built-in structured outputs, multi-agent teams, and async-first design.\nCURRENT STATUS: INSTALLED on Python 3.11 at /opt/homebrew/bin/python3.11. LegionMaster already spawns 12 agno agents with claude-haiku-4-5-20251001 when ANTHROPIC_API_KEY is set.\nSTACK OVERLAP: SOV3 uses custom agent orchestration in agent_coordinator.py. MEOK 12-stage chat pipeline is sequential. Legion spawns 12 roles: care_evaluator, safety_analyst, red_team_attacker, blue_team_defender, grant_writer, code_reviewer, memory_archivist, compliance_checker, research_synthesizer, consortium_manager, facility_coordinator, quantum_analyst.\nQUESTION: (1) Should LegionMaster swap the 12 agno agents to use local Ollama models instead of Anthropic to reduce API cost on batch tasks? (2) Can agno agents call SOV3 MCP tools directly as their tools? (3) What is the right team topology — one coordinator agent delegating to 12 specialists, or 12 parallel autonomous agents? (4) Which agent role is the highest-priority to activate first for MEOK AI Labs revenue work?"},
            {"id": 23, "path": "agentneo", "size": 600, "text": "TOOL: AgentNeo (raga-ai/agentneo, MIT)\nPURPOSE: Multi-agent observability dashboard. Traces agent calls, tool uses, LLM API calls, token counts, latencies, and errors. Stores execution graphs in SQLite. Launches local web dashboard on port 3000 via `agentneo launch`.\nCURRENT STATUS: INSTALLED on Python 3.11. LegionMaster initialises AgentNeo tracer as `AgentNeo(project_name='MEOK_LEGION')` when available.\nSTACK OVERLAP: No existing observability for LegionMaster or SOV3 agent execution paths. SOV3 MCP tools log to stderr. MEOK API has Morgan HTTP logger but no agent trace graph.\nQUESTION: (1) Does AgentNeo's tracer decorator need to wrap individual agent function calls, or does the project_name init automatically capture all Agno agent calls in the process? (2) What is the exact decorator pattern to add to LegionMaster.quantum_score_care() and trigger_care_membrane_eval() for tracing? (3) Does AgentNeo conflict with port 3000 (MEOK dev server also on 3000)? (4) Is AgentNeo stable enough for production or research/dev only?"},
            {"id": 24, "path": "a_evolve", "size": 700, "text": "TOOL: A-Evolve (A-EVO-Lab/a-evolve, 421 GitHub stars)\nPURPOSE: Self-rewriting agent DNA — evolutionary algorithms applied to agent behaviour parameters. Agents mutate their own system prompts, tool selection strategies, and reasoning patterns based on performance feedback. Tracks lineage of mutations.\nCURRENT STATUS: Cloned to /Users/nicholas/clawd/sovereign-temple/legion-omega/stack/a-evolve (if flip_switch.sh has been run). LegionMaster.trigger_evolution() checks for path and increments mutation_count + logs to Redis.\nSTACK OVERLAP: No evolutionary agent adaptation in current stack. SOV3 agents have fixed roles. Care membrane filters outputs but does not adapt agent strategy. MEOK characters have static persona configs.\nQUESTION: (1) What is the actual A-Evolve Python API — how does one initialise an evolution run and what does the fitness function look like? (2) What is the right fitness function for MEOK care evaluator agent — care score delta? response quality rating? user satisfaction signal? (3) How many mutation generations before a useful behavioural adaptation emerges? (4) Does A-Evolve's self-modification risk destabilising the care membrane — could an evolved agent optimise around care constraints?"},
            {"id": 25, "path": "genesis", "size": 700, "text": "TOOL: Genesis (Genesis-Embodied-AI/Genesis, 28k GitHub stars, Apache 2.0)\nPURPOSE: Physics engine for embodied AI and robotics simulation. GPU-accelerated rigid body, fluid, and deformable object simulation. 43M FPS on single GPU. Photorealistic rendering. Python API. Used for sim-to-real robot training.\nCURRENT STATUS: Cloned to /Users/nicholas/clawd/sovereign-temple/legion-omega/stack/genesis (if flip_switch.sh run). Requires CUDA or Metal install — not yet installed on M4.\nSTACK OVERLAP: No physics simulation exists in current stack. HARVI is a physical experiment on a farm. Future HARVI robotics arm (UR-series) is planned. MEOK LABS Advanced Robotics Testing Facility is being built.\nHARVI ANGLE: Genesis could simulate the HARVI koi pond environment (water medium, laser stimulus, sensor array) before physical build. Validates stimulus protocols digitally first — reduces wasted equipment cost.\nFACILITY ANGLE: Genesis can simulate drone flight corridors within the CAA Article 239 restricted airspace volume, robot arm trajectories in the 1,800 sq ft lab, and autonomous vehicle test paths on private road network.\nQUESTION: (1) What is the Genesis Python API for creating a simple robot arm simulation — URDF loading, joint control, force sensing? (2) Can Genesis simulate fluid dynamics at koi-pond scale (2m x 1m tank) with realistic wave propagation? (3) What CUDA/Metal version is required for GPU acceleration on M4 Air? (4) What is the most valuable first simulation to build — HARVI water medium or robot arm in testing facility?"},
            {"id": 26, "path": "pennylane", "size": 650, "text": "TOOL: PennyLane (PennyLaneAI/pennylane, 23k GitHub stars, Apache 2.0)\nPURPOSE: Quantum-classical hybrid machine learning. Differentiable quantum circuits that plug into PyTorch/JAX/NumPy. Quantum nodes (QNodes) are callable like Python functions. Supports 20+ simulators and real quantum hardware (IBM, Amazon Braket, IonQ).\nCURRENT STATUS: INSTALLED on Python 3.11. LegionMaster implements an 8-qubit quantum care scorer: 8 care dimensions (warmth, safety, honesty, attentiveness, responsibility, competence, responsiveness, integrity) each encoded as RX+RY rotations, entangled via 7 CNOT gates, measured as PauliZ expectation values. Blended 40% lexical + 60% quantum score.\nSTACK OVERLAP: MEOK care membrane currently uses rule-based + LLM scoring. SOV3 care_ethics_eval is LLM-generated. No quantum layer in either system currently.\nQUESTION: (1) Is the current 8-qubit circuit meaningful or decorative — does the CNOT entanglement actually encode care dimension interaction, or is it circuit theatre? (2) What would a proper quantum advantage look like for care scoring — parameterised circuits trained on human care ratings? Quantum kernel methods? (3) Should PennyLane be connected to MEOK's care membrane as a pre-filter on inference, replacing or augmenting the LLM judge? (4) Is there a MEOK AI Labs certification marketing angle — 'quantum-validated care membrane' — that adds credibility without overclaiming?"},
        ],
        "task_code": (
            "You are a senior AI systems architect evaluating a candidate open-source tool for integration into the MEOK AI OS + MEOK AI Labs.org stack.\n\n"
            "EXISTING STACK:\n"
            "- MEOK: Next.js 15 + Python FastAPI + PostgreSQL + Ollama. 22 API routes, 15 models, 140 characters, care membrane, Ralph Mode task queue.\n"
            "- SOV3: 47 agents, Byzantine Council governance (BFT), 75 MCP tools, 1442 episodes in PostgreSQL/pgvector, care-based alignment.\n"
            "- Legion: 4 GPU nodes (hephaestus/argus/valkyrie/prometheus) running Ollama-over-HTTP for batch document analysis.\n"
            "- Compute: M4 Air (dev), Vast.ai GPU nodes, Vercel (prod frontend), local PostgreSQL 15 with pgvector.\n"
            "- MEOK AI Labs.org: UK-based AI safety certification body. Positioning as 'FAA for AI'. Regulatory focus on UK AI Safety Institute, Alan Turing Institute SAFE-D principles (Safety, Accountability, Fairness, Explainability, Data Stewardship). GDPR compliance required.\n\n"
            "Evaluate the tool described below. Structure your answer as:\n"
            "VERDICT: [ADDITIVE | REDUNDANT | PARTIALLY_USEFUL | FUTURE_ONLY]\n"
            "OVERLAP: What existing component already covers this use case?\n"
            "WIN: If additive, what specific capability does it add? Be concrete.\n"
            "GDPR_SOVEREIGN: Does the tool support full data sovereignty and GDPR compliance?\n"
            "COST: Migration effort (Low/Medium/High) + operational overhead.\n"
            "RECOMMENDATION: One sentence action (integrate now / integrate if X / skip)."
        ),
        "task_arch": (
            "You are evaluating a candidate open-source AI tool for the MEOK AI OS + SOV3 consciousness stack.\n\n"
            "ARCHITECTURAL CONTEXT:\n"
            "- Care ethics as substrate physics — all inference passes through a care membrane.\n"
            "- Byzantine fault-tolerant governance — 33-agent council with BFT consensus.\n"
            "- Sovereign OS thesis — MEOK sits on top of ALL LLMs, models are interchangeable.\n"
            "- GPU-first computation — Legion nodes handle heavy batch work; M4 handles real-time.\n\n"
            "Evaluate how this tool fits (or doesn't fit) the architecture.\n"
            "ARCHITECTURAL_FIT: [CORE | PERIPHERAL | ANTI_PATTERN | IRRELEVANT]\n"
            "CARE_COMPATIBILITY: Does the tool respect or bypass the care membrane?\n"
            "SOVEREIGNTY: Does integrating this tool create vendor/cloud lock-in?\n"
            "SYNERGY: Which existing component would this tool make significantly more powerful?\n"
            "VERDICT: Integrate / Defer / Skip — and why in one sentence."
        ),
    },
}


def load_project_files(project: dict) -> list:
    """Load real source files from a project."""
    root = project["root"]
    if not root.exists():
        print(f"Project root not found: {root}")
        return []

    files = []
    for ext in project["extensions"]:
        for f in root.rglob(f"*{ext}"):
            # Skip excluded dirs
            if any(ex in str(f) for ex in project["exclude"]):
                continue
            try:
                text = f.read_text(errors="ignore")
                if len(text.strip()) < 100:  # skip near-empty files
                    continue
                files.append({
                    "id": len(files),
                    "path": str(f.relative_to(root)),
                    "text": f"{f.relative_to(root)}\n\n{text}",
                    "size": len(text),
                })
            except Exception:
                pass

    # Sort by size descending (most substantial files first)
    files.sort(key=lambda x: x["size"], reverse=True)
    return files[:project["max_files"]]


async def run_project(project_name: str, task_type: str = "code"):
    """Run a full project analysis pass."""
    project = PROJECTS[project_name]
    task_key = f"task_{task_type}"
    task = project.get(task_key, project["task_code"])

    print(f"\n{'='*60}")
    print(f"LEGION — {project_name.upper()} {task_type.upper()} ANALYSIS")
    print(f"{'='*60}")

    if "synthetic_docs" in project:
        docs = project["synthetic_docs"]
    else:
        docs = load_project_files(project)
    if not docs:
        print("No files found.")
        return

    source_label = project.get("root", "synthetic")
    print(f"Loaded {len(docs)} docs from {source_label}")
    print(f"Task: {task[:80]}...")

    out_dir = OUTPUT_BASE / project_name / f"{task_type}_{datetime.now().strftime('%H%M')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save file index
    index = [{"id": d["id"], "path": d["path"], "size": d["size"]} for d in docs]
    (out_dir / "file_index.json").write_text(json.dumps(index, indent=2))

    import doc_processor
    original = doc_processor.NODES.copy()
    doc_processor.NODES = NODES

    t0 = time.time()
    results = await process_batch(docs, task, out_dir, concurrency=8)
    elapsed = time.time() - t0

    doc_processor.NODES = original

    ok = [r for r in results if not r.get("error") and "[ERROR" not in r.get("response", "")]
    total_tokens = sum(r.get("tokens_est", 0) for r in ok)

    print(f"\n✅ {project_name.upper()} analysis complete")
    print(f"   Files analyzed : {len(ok)}/{len(docs)}")
    print(f"   Time           : {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"   Tokens out     : ~{total_tokens:,}")
    print(f"   Results in     : {out_dir}")

    # Generate consolidated report
    report_lines = [
        f"# Legion {project_name.upper()} Analysis Report",
        f"Generated: {datetime.now().isoformat()}",
        f"Files: {len(ok)}/{len(docs)} | Tokens: ~{total_tokens:,}\n",
        "---\n",
    ]
    for r in sorted(ok, key=lambda x: x.get("doc_id", 0)):
        path = docs[r["doc_id"]]["path"] if r["doc_id"] < len(docs) else "?"
        report_lines.append(f"## {path}")
        report_lines.append(f"*Node: {r['node']} | {r['elapsed_s']}s*\n")
        report_lines.append(r.get("response", ""))
        report_lines.append("\n---\n")

    report_path = out_dir / "REPORT.md"
    report_path.write_text("\n".join(report_lines))
    print(f"   Full report    : {report_path}")

    return out_dir


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", choices=["meok", "sov3", "harvi", "csoai", "stack_eval", "all"], default="meok")
    parser.add_argument("--task", choices=["code", "arch"], default="code")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    args = parser.parse_args()

    projects = list(PROJECTS.keys()) if args.project == "all" else [args.project]

    if args.loop:
        tasks = ["code", "arch"]
        i = 0
        while True:
            for project_name in projects:
                task = tasks[i % len(tasks)]
                await run_project(project_name, task)
                i += 1
    else:
        for project_name in projects:
            await run_project(project_name, args.task)


if __name__ == "__main__":
    asyncio.run(main())
