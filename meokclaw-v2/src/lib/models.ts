export interface ModelPreset {
  id: string;
  name: string;
  provider: string;
  description: string;
  maxTokens: number;
  costPer1kInput: number;
  costPer1kOutput: number;
  tags: string[];
  fallbackChain: string[];
}

export const MODEL_PRESETS: ModelPreset[] = [
  {
    id: "gemma4-local",
    name: "Gemma 4 (Local)",
    provider: "ollama",
    description: "Deep reasoning, 256K context. Left brain.",
    maxTokens: 256000,
    costPer1kInput: 0,
    costPer1kOutput: 0,
    tags: ["local", "reasoning", "coding", "vision"],
    fallbackChain: ["deepseek-reasoner", "llama-3.3-70b-free"],
  },
  {
    id: "qwen-creative",
    name: "Qwen 2.5 (Creative)",
    provider: "ollama",
    description: "Right brain. Emotional, conversational, quick.",
    maxTokens: 32768,
    costPer1kInput: 0,
    costPer1kOutput: 0,
    tags: ["local", "creative", "emotional"],
    fallbackChain: ["gemma-free", "claude-haiku"],
  },
  {
    id: "cerebras-fast",
    name: "Cerebras (Fast)",
    provider: "cerebras",
    description: "Free tier. 450 tok/s. Greetings & simple queries.",
    maxTokens: 8192,
    costPer1kInput: 0,
    costPer1kOutput: 0,
    tags: ["cloud", "fast", "free"],
    fallbackChain: ["groq-llama", "openrouter-free"],
  },
  {
    id: "deepseek-reasoner",
    name: "DeepSeek Reasoner",
    provider: "openrouter",
    description: "Chain-of-thought reasoning. Analysis & strategy.",
    maxTokens: 64000,
    costPer1kInput: 0.00055,
    costPer1kOutput: 0.00219,
    tags: ["cloud", "reasoning", "coding"],
    fallbackChain: ["gemma4-local", "claude-sonnet"],
  },
  {
    id: "nemotron-super",
    name: "Nemotron 3 Super",
    provider: "openclaw",
    description: "Agentic tasks. OpenClaw orchestration.",
    maxTokens: 128000,
    costPer1kInput: 0,
    costPer1kOutput: 0,
    tags: ["cloud", "agentic", "orchestration"],
    fallbackChain: ["gemma4-local", "deepseek-reasoner"],
  },
];

export function getPresetById(id: string): ModelPreset | undefined {
  return MODEL_PRESETS.find((m) => m.id === id);
}

export function getFallbackChain(preset: ModelPreset): ModelPreset[] {
  return preset.fallbackChain
    .map((fid) => getPresetById(fid))
    .filter(Boolean) as ModelPreset[];
}
