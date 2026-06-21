/**
 * MEOKCLAW Extension Popup — Lightweight chat UI
 */

const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("msg-input");
const sendBtn = document.getElementById("btn-send");
const statusEl = document.getElementById("status");

let messages = [];
let isStreaming = false;

// Check engine status
chrome.runtime.sendMessage({ type: "GET_STATUS" }, (status) => {
  if (status?.engineReady) {
    statusEl.textContent = "● Local";
    statusEl.className = "status online";
  } else {
    statusEl.textContent = "○ Cloud";
    statusEl.className = "status";
  }
});

// Send message
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isStreaming) return;

  addMessage(text, "user");
  inputEl.value = "";
  messages.push({ role: "user", content: text });

  isStreaming = true;
  sendBtn.disabled = true;
  const assistantMsg = addMessage("", "assistant");

  // Try streaming via background
  const response = await chrome.runtime.sendMessage({
    type: "CHAT",
    payload: { messages, requirePrivate: false },
  });

  if (response?.success) {
    assistantMsg.textContent = response.text;
    messages.push({ role: "assistant", content: response.text });
  } else {
    assistantMsg.textContent = "Error: " + (response?.error || "Unknown");
  }

  isStreaming = false;
  sendBtn.disabled = false;
}

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
  return div;
}

sendBtn.addEventListener("click", sendMessage);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});

// Quick actions
document.getElementById("btn-summarize").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const response = await chrome.runtime.sendMessage({ type: "SUMMARIZE_PAGE" });
  if (response?.success) {
    addMessage("📄 Page Summary:\n\n" + response.text, "assistant");
  }
});

// Listen for streaming tokens from background
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "STREAM_TOKEN") {
    // Update last assistant message incrementally
    const lastMsg = chatEl.querySelector(".msg.assistant:last-child");
    if (lastMsg) lastMsg.textContent += msg.token;
  }
});
