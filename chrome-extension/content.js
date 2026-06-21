/**
 * MEOKCLAW Content Script — Injected into every webpage
 *
 * Capabilities:
 * - Extract page text for summarization
 * - Highlight text and offer AI explanations
 * - Inject floating MEOKCLAW assistant button
 * - Detect code blocks and offer inline explanations
 */

(function() {
  'use strict';

  // Prevent double-injection
  if (window.__MEOKCLAW_INJECTED) return;
  window.__MEOKCLAW_INJECTED = true;

  // ── Floating Action Button ───────────────────────────────────────
  function createFloatingButton() {
    const btn = document.createElement("div");
    btn.id = "meokclaw-float";
    btn.innerHTML = "◈";
    btn.style.cssText = `
      position: fixed; bottom: 24px; right: 24px;
      width: 48px; height: 48px; border-radius: 50%;
      background: linear-gradient(135deg, #00ff88, #00cc6a);
      color: #000; display: flex; align-items: center;
      justify-content: center; font-size: 20px; font-weight: 700;
      cursor: pointer; z-index: 2147483647; box-shadow: 0 4px 20px rgba(0,255,136,0.3);
      transition: transform 0.2s, box-shadow 0.2s; user-select: none;
    `;
    btn.addEventListener("mouseenter", () => {
      btn.style.transform = "scale(1.1)";
      btn.style.boxShadow = "0 6px 30px rgba(0,255,136,0.5)";
    });
    btn.addEventListener("mouseleave", () => {
      btn.style.transform = "scale(1)";
      btn.style.boxShadow = "0 4px 20px rgba(0,255,136,0.3)";
    });
    btn.addEventListener("click", () => {
      chrome.runtime.sendMessage({ type: "TOGGLE_SIDEPANEL" });
    });
    document.body.appendChild(btn);
  }

  // ── Text Selection Tooltip ───────────────────────────────────────
  function createSelectionTooltip() {
    let tooltip = null;

    document.addEventListener("mouseup", () => {
      const selection = window.getSelection().toString().trim();
      if (!selection || selection.length < 10) {
        if (tooltip) { tooltip.remove(); tooltip = null; }
        return;
      }

      const range = window.getSelection().getRangeAt(0);
      const rect = range.getBoundingClientRect();

      tooltip = document.createElement("div");
      tooltip.id = "meokclaw-tooltip";
      tooltip.innerHTML = `
        <button id="mcc-explain">Explain</button>
        <button id="mcc-summarize">Summarize</button>
        <button id="mcc-translate">Translate</button>
      `;
      tooltip.style.cssText = `
        position: fixed; z-index: 2147483646;
        left: ${rect.left + rect.width / 2 - 80}px;
        top: ${rect.top - 40}px;
        background: #1a1a2e; border: 1px solid #333;
        border-radius: 8px; padding: 4px; display: flex; gap: 4px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      `;

      tooltip.querySelectorAll("button").forEach(b => {
        b.style.cssText = `
          background: #111; border: 1px solid #333; color: #e0e0e0;
          padding: 4px 10px; border-radius: 4px; font-size: 12px;
          cursor: pointer; white-space: nowrap;
        `;
        b.addEventListener("mouseenter", () => b.style.borderColor = "#00ff88");
        b.addEventListener("mouseleave", () => b.style.borderColor = "#333");
      });

      tooltip.querySelector("#mcc-explain").addEventListener("click", () => {
        sendToAssistant(`Explain this:\n\n${selection}`);
        tooltip.remove(); tooltip = null;
      });
      tooltip.querySelector("#mcc-summarize").addEventListener("click", () => {
        sendToAssistant(`Summarize this:\n\n${selection}`);
        tooltip.remove(); tooltip = null;
      });
      tooltip.querySelector("#mcc-translate").addEventListener("click", () => {
        sendToAssistant(`Translate to English:\n\n${selection}`);
        tooltip.remove(); tooltip = null;
      });

      document.body.appendChild(tooltip);
    });

    document.addEventListener("mousedown", (e) => {
      if (tooltip && !tooltip.contains(e.target)) {
        tooltip.remove(); tooltip = null;
      }
    });
  }

  function sendToAssistant(prompt) {
    chrome.runtime.sendMessage({
      type: "CHAT",
      payload: { messages: [{ role: "user", content: prompt }] },
    });
  }

  // ── Code Block Enhancement ───────────────────────────────────────
  function enhanceCodeBlocks() {
    const codeBlocks = document.querySelectorAll("pre code, pre");
    codeBlocks.forEach((block) => {
      if (block.dataset.meokclawEnhanced) return;
      block.dataset.meokclawEnhanced = "1";

      const btn = document.createElement("button");
      btn.textContent = "Explain";
      btn.style.cssText = `
        position: absolute; top: 4px; right: 4px;
        background: #00ff88; color: #000; border: none;
        padding: 2px 8px; border-radius: 4px; font-size: 11px;
        cursor: pointer; opacity: 0; transition: opacity 0.2s;
      `;
      const parent = block.closest("pre") || block;
      parent.style.position = "relative";
      parent.appendChild(btn);

      parent.addEventListener("mouseenter", () => btn.style.opacity = "1");
      parent.addEventListener("mouseleave", () => btn.style.opacity = "0");

      btn.addEventListener("click", () => {
        const code = block.textContent;
        sendToAssistant(`Explain this code:\n\n\`\`\`\n${code}\n\`\`\``);
      });
    });
  }

  // ── Init ─────────────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  function init() {
    createFloatingButton();
    createSelectionTooltip();
    enhanceCodeBlocks();

    // Re-scan for new code blocks (SPA navigation)
    const observer = new MutationObserver(() => enhanceCodeBlocks());
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();
