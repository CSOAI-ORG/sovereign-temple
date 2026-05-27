# API Keys Required for Full Operation
**Status:** 5-Minute Setup for Complete System Activation

## 🔑 REQUIRED API KEYS (All Free Tiers Available)

### 1. OpenRouter - **MOST IMPORTANT** 
- **URL:** https://openrouter.ai  
- **Free tier:** $5 credit to start, pay-per-use after
- **Gives access to:** DeepSeek Reasoner, DeepSeek Coder, Claude, GPT-4, Gemini, 200+ models
- **Add to .env:** `OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY`
- **Why critical:** This unlocks DeepSeek reasoning for robot design

### 2. Cerebras - **FREE 1M tokens/day**
- **URL:** https://cloud.cerebras.ai
- **Free tier:** 1 million tokens per day (huge)
- **Models:** Llama 3.1 70B at 450 tokens/second  
- **Add to .env:** `CEREBRAS_API_KEY=csk-YOUR_KEY`
- **Why important:** Ultra-fast inference for quick robot queries

### 3. Groq - **FREE tier available**
- **URL:** https://console.groq.com
- **Free tier:** Generous limits
- **Models:** Fast Llama, Mixtral, Gemma
- **Add to .env:** `GROQ_API_KEY=gsk-YOUR_KEY`
- **Why useful:** Backup fast inference

### 4. Google AI Studio - **FREE tier**
- **URL:** https://aistudio.google.com  
- **Free tier:** Generous quotas
- **Models:** Gemini 1.5 Pro, Flash, thinking models
- **Add to .env:** `GOOGLE_AI_KEY=YOUR_KEY`
- **Why valuable:** Research and creative robot design

## 🚀 CURRENT STATUS WITHOUT API KEYS

**What works NOW (with Ollama local only):**
- ✅ Robot design generation (using local Llama models)
- ✅ STL file creation (mock generation)
- ✅ G-code generation (template-based)
- ✅ Print queue management
- ✅ Cluster simulation (mock scoring)

**What activates with API keys:**
- 🔥 **DeepSeek reasoning** for advanced robot design
- 🔥 **Ultra-fast Cerebras inference** for quick queries  
- 🔥 **Gemini research** for cutting-edge robotics papers
- 🔥 **Cross-model routing** based on task complexity

## ⚡ ACTIVATION SEQUENCE (5 minutes)

```bash
# 1. Get OpenRouter key (2 minutes)
open https://openrouter.ai
# Sign up, get API key, add $5 credit

# 2. Get Cerebras key (1 minute)  
open https://cloud.cerebras.ai
# Sign up, get free API key

# 3. Get Groq key (1 minute)
open https://console.groq.com  
# Sign up, get free API key

# 4. Get Google key (1 minute)
open https://aistudio.google.com
# Sign up, get free API key

# 5. Update .env file (30 seconds)
cd /Users/nicholas/clawd/sovereign-temple
nano .env
# Replace the placeholder keys
```

## 🧪 TESTING COMMANDS

```bash
# Test the complete system:
cd /Users/nicholas/clawd/sovereign-temple
python3 test_genesis_pipeline.py

# Test individual components:
python3 -c "
import asyncio
from llm_providers.router import router
async def test():
    result = await router.route('Design a robot leg', intent='robotics')
    print(result)
asyncio.run(test())
"
```

## 🎯 EXPECTED OUTPUT WITH API KEYS

```
🚀 Testing Genesis → G-code Pipeline with DeepSeek
============================================================
1. Testing voice-to-robot pipeline...
Command: Design me a security quadruped robot for my 6.5 acre farm...
✅ Design complete: v7_security_quad
   Print time: 18 hours
   STL files: 11
   G-code files: 22

2. Testing DeepSeek routing...
   'What is 2+2?...' → ollama/llama3.1:8b (intent: quick)
   'Design a robot leg joint...' → openrouter/deepseek-coder (intent: robotics) 
   'Simulate physics for quadruped...' → openrouter/deepseek-reasoner (intent: genesis)
   'Write beautiful poetry...' → openrouter/gemini-2.5-flash (intent: creative)
   'Debug this Python function...' → openrouter/deepseek-coder (intent: code)

🎯 Genesis → G-code Pipeline Test Complete!
```

## 🔥 IMMEDIATE BENEFITS

**With API keys you get:**
- **DeepSeek V3** - State-of-the-art reasoning for robot design
- **1M free tokens/day** from Cerebras for rapid iteration  
- **Multi-model intelligence** routed automatically by task type
- **Research capabilities** with Gemini for latest robotics papers
- **Complete autonomy** from "voice command" to "printing G-code"

**Cost:** ~$5-10 to start, then pay-per-use (very affordable)
**Time to setup:** 5 minutes  
**Value:** Sovereign robot manufacturing pipeline

---

**Ready when you are! Just grab those API keys and watch the Genesis → G-code pipeline come alive! 🤖🔥**