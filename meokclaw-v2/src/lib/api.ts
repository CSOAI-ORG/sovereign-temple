const SOV3_URL = process.env.NEXT_PUBLIC_SOV3_URL || "http://localhost:3101";
const MEOK_MCP_URL = process.env.NEXT_PUBLIC_MEOK_MCP_URL || "http://localhost:3102";
const MEOK_API_URL = process.env.NEXT_PUBLIC_MEOK_API_URL || "http://localhost:3200";

export interface HealthStatus {
  status: string;
  version?: string;
  timestamp?: string;
  components?: Record<string, any>;
  proxied_by?: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "tool" | "system" | "reasoning";
  content: string;
  metadata?: {
    model?: string;
    hemisphere?: string;
    tokens_in?: number;
    tokens_out?: number;
    cost?: number;
    cost_usd?: number;
    latency_ms?: number;
    tool_calls?: ToolCall[];
  };
  timestamp?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  result?: any;
  status: "pending" | "running" | "success" | "error";
}

export interface ConversationBranch {
  id: string;
  parentId: string | null;
  messages: ChatMessage[];
  label: string;
  createdAt: string;
}

export async function fetchSov3Health(): Promise<HealthStatus> {
  const res = await fetch(`${SOV3_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("SOV3 health check failed");
  return res.json();
}

export async function fetchMeokMcpHealth(): Promise<HealthStatus> {
  const res = await fetch(`${MEOK_MCP_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("MEOK MCP health check failed");
  return res.json();
}

export async function fetchMeokApiHealth(): Promise<HealthStatus> {
  const res = await fetch(`${MEOK_API_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("MEOK API health check failed");
  return res.json();
}

export async function sendChatMessage(
  message: string,
  modelId: string,
  history: ChatMessage[]
): Promise<ReadableStream<Uint8Array> | null> {
  const res = await fetch(`${SOV3_URL}/mcp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: {
        name: "sov3_chat",
        arguments: { message, model_id: modelId, history },
      },
    }),
  });
  if (!res.ok) return null;
  return res.body;
}

export async function listMcpTools(): Promise<any[]> {
  const res = await fetch(`${SOV3_URL}/mcp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/list",
    }),
  });
  if (!res.ok) return [];
  const data = await res.json();
  return data.result?.tools || [];
}
