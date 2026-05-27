/**
 * MEOKCLAW Chrome Extension — Background Service Worker (MV3)
 *
 * Architecture:
 * - Service worker: API calls, WebLLM inference, state management
 * - Content script: DOM extraction, injection of AI suggestions
 * - Popup/Sidepanel: UI, chat interface
 *
 * WebLLM runs in the service worker for local inference.
 * Falls back to MEOKCLAW cloud API when local model unavailable.
 */

import { CreateMLCEngine } from "@mlc-ai/web-llm";

const CONFIG = {
  cloudApi: "https://api.meokclaw.io/api/dual-brain",
  defaultModel: "gemma-3-4b-it-q4f16_1-MLC",
  fallbackModel: "Phi-3-mini-4k-instruct-q4f16_1-MLC",
};

let webllmEngine = null;
let engineReady = false;

// ── WebLLM Initialization ──────────────────────────────────────────
async function initWebLLM() {
  try {
    if (typeof navigator === "undefined" || !navigator.gpu) {
      console.log("[MEOKCLAW] WebGPU not available, using cloud only");
      return false;
    }
    webllmEngine = await CreateMLCEngine(CONFIG.defaultModel, {
      initProgressCallback: (report) => {
        console.log("[WebLLM]", report.text);
        broadcastToPanels({ type: "WEBLLM_PROGRESS", report });
      },
    });
    engineReady = true;
    console.log("[MEOKCLAW] WebLLM engine ready");
    return true;
  } catch (e) {
    console.error("[MEOKCLAW] WebLLM init failed:", e);
    return false;
  }
}

// ── Message Routing ────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "CHAT") {
    handleChat(message.payload, sender).then(sendResponse);
    return true; // async
  }
  if (message.type === "SUMMARIZE_PAGE") {
    handleSummarize(sender).then(sendResponse);
    return true;
  }
  if (message.type === "EXTRACT_TEXT") {
    handleExtractText(sender.tab.id).then(sendResponse);
    return true;
  }
  if (message.type === "GET_STATUS") {
    sendResponse({ engineReady, webgpu: !!navigator.gpu });
    return false;
  }
});

// ── Chat Handler (Local → Cloud fallback) ──────────────────────────
async function handleChat(payload, sender) {
  const { messages, requirePrivate } = payload;

  // Try local first if private mode or engine ready
  if ((requirePrivate || engineReady) && webllmEngine) {
    try {
      const stream = await webllmEngine.chat.completions.create({
        messages,
        temperature: 0.7,
        max_tokens: 1024,
        stream: true,
      });

      let fullText = "";
      for await (const chunk of stream) {
        const text = chunk.choices[0]?.delta?.content || "";
        fullText += text;
        broadcastToPanels({ type: "STREAM_TOKEN", token: text, tabId: sender.tab?.id });
      }
      return { success: true, text: fullText, source: "local" };
    } catch (e) {
      console.warn("[MEOKCLAW] Local inference failed, falling back:", e);
    }
  }

  // Cloud fallback
  try {
    const apiKey = await getApiKey();
    const response = await fetch(CONFIG.cloudApi, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
      body: JSON.stringify({ message: messages[messages.length - 1].content, context: messages }),
    });
    const data = await response.json();
    return { success: true, text: data.response || data.content, source: "cloud" };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// ── Page Summarization ─────────────────────────────────────────────
async function handleSummarize(sender) {
  const text = await extractPageText(sender.tab.id);
  const prompt = `Summarize this web page in 3 bullet points:\n\n${text.slice(0, 8000)}`;
  return handleChat({ messages: [{ role: "user", content: prompt }] }, sender);
}

async function handleExtractText(tabId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      // Extract readable text, filtering nav/ads
      const article = document.querySelector("article, main, [role='main']");
      if (article) return article.innerText;
      return document.body.innerText.slice(0, 15000);
    },
  });
  return results[0]?.result || "";
}

async function extractPageText(tabId) {
  return handleExtractText(tabId);
}

// ── Helpers ────────────────────────────────────────────────────────
async function getApiKey() {
  const stored = await chrome.storage.local.get("apiKey");
  return stored.apiKey || "";
}

function broadcastToPanels(message) {
  chrome.runtime.sendMessage(message).catch(() => {});
}

// ── Side Panel Toggle ──────────────────────────────────────────────
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

// ── Init ───────────────────────────────────────────────────────────
initWebLLM();
