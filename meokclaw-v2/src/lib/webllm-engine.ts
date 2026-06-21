/**
 * WebLLM Engine — In-browser LLM inference via WebGPU.
 *
 * Zero server cost. 100% private. Works offline after first model load.
 * Powered by MLC-LLM / WebLLM (@mlc-ai/web-llm).
 *
 * Usage:
 *   const engine = await getWebLLMEngine();
 *   const reply = await engine.chat.completions.create({ messages: [...] });
 */

import { CreateMLCEngine, MLCEngine, ChatCompletionMessageParam } from "@mlc-ai/web-llm";

// Model mapping: tier -> WebLLM model ID
const WEBLLM_MODELS = {
  l1: "gemma-3-4b-it-q4f16_1-MLC",     // 2.5GB, fast
  l2: "Qwen2.5-7B-Instruct-q4f16_1-MLC", // 4.5GB, capable
  fallback: "Phi-3-mini-4k-instruct-q4f16_1-MLC", // 2GB, reliable
};

let engineInstance: MLCEngine | null = null;
let currentModel: string = "";

/**
 * Initialize or return cached WebLLM engine.
 * @param tier "l1" | "l2" — model size tier
 * @param onProgress callback for download/load progress
 */
export async function getWebLLMEngine(
  tier: "l1" | "l2" = "l1",
  onProgress?: (report: { progress: number; text: string }) => void
): Promise<MLCEngine> {
  const modelId = WEBLLM_MODELS[tier] || WEBLLM_MODELS.l1;

  // Reuse if same model already loaded
  if (engineInstance && currentModel === modelId) {
    return engineInstance;
  }

  // Check WebGPU support
  const nav = navigator as any;
  if (typeof navigator !== "undefined" && !nav.gpu) {
    throw new Error(
      "WebGPU not supported. Use Chrome/Edge on Windows/macOS, or Chrome on Android."
    );
  }

  const initProgressCallback = onProgress || ((report) => console.log("[WebLLM]", report.text));

  engineInstance = await CreateMLCEngine(modelId, {
    initProgressCallback,
  });
  currentModel = modelId;

  return engineInstance;
}

/**
 * Quick chat completion using WebLLM.
 */
export async function webllmChat(
  messages: ChatCompletionMessageParam[],
  options?: {
    tier?: "l1" | "l2";
    temperature?: number;
    max_tokens?: number;
    onProgress?: (report: { progress: number; text: string }) => void;
  }
) {
  const engine = await getWebLLMEngine(options?.tier || "l1", options?.onProgress);

  const reply = await engine.chat.completions.create({
    messages,
    temperature: options?.temperature ?? 0.7,
    max_tokens: options?.max_tokens ?? 1024,
    stream: false,
  });

  return reply.choices[0]?.message?.content || "";
}

/**
 * Streaming chat completion via WebLLM.
 */
export async function* webllmChatStream(
  messages: ChatCompletionMessageParam[],
  options?: {
    tier?: "l1" | "l2";
    temperature?: number;
    max_tokens?: number;
  }
) {
  const engine = await getWebLLMEngine(options?.tier || "l1");

  const stream = await engine.chat.completions.create({
    messages,
    temperature: options?.temperature ?? 0.7,
    max_tokens: options?.max_tokens ?? 1024,
    stream: true,
  });

  for await (const chunk of stream) {
    const content = chunk.choices[0]?.delta?.content;
    if (content) yield content;
  }
}

/**
 * Check if WebGPU is available and ready.
 */
export function isWebGPUSupported(): boolean {
  if (typeof navigator === "undefined") return false;
  return "gpu" in (navigator as any);
}

/**
 * Get recommended tier based on available VRAM estimate.
 */
export function getRecommendedWebLLMTier(): "l1" | "l2" | null {
  if (!isWebGPUSupported()) return null;
  // L2 needs ~6GB VRAM. L1 needs ~3GB.
  // Heuristic: assume L1 for safety, upgrade if known high-end
  return "l1";
}
