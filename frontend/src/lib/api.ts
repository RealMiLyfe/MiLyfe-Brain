const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8200";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Playbooks
export const playbookApi = {
  create: (data: { title: string; description: string; raw_text?: string; auto_execute?: boolean }) =>
    fetchApi("/api/playbooks/", { method: "POST", body: JSON.stringify(data) }),
  list: () => fetchApi<any[]>("/api/playbooks/"),
  get: (id: string) => fetchApi(`/api/playbooks/${id}`),
  getStatus: (id: string) => fetchApi(`/api/playbooks/${id}/status`),
  getGraph: (id: string) => fetchApi(`/api/playbooks/${id}/graph`),
  rerun: (id: string) => fetchApi(`/api/playbooks/${id}/rerun`, { method: "POST" }),
  delete: (id: string) => fetchApi(`/api/playbooks/${id}`, { method: "DELETE" }),
};

// Agents
export const agentApi = {
  roles: () => fetchApi("/api/agents/roles"),
  active: () => fetchApi<any[]>("/api/agents/active"),
  spawn: (role: string, task: string) =>
    fetchApi("/api/agents/spawn", { method: "POST", body: JSON.stringify({ role, task }) }),
  retire: (id: string) => fetchApi(`/api/agents/${id}`, { method: "DELETE" }),
};

// Chat
export const chatApi = {
  send: (data: { message: string; session_id?: string; model_override?: string }) =>
    fetchApi("/api/chat/send", { method: "POST", body: JSON.stringify(data) }),
  history: (sessionId: string) => fetchApi<any[]>(`/api/chat/history/${sessionId}`),
  sessions: () => fetchApi<any[]>("/api/chat/sessions"),
  deleteSession: (id: string) => fetchApi(`/api/chat/sessions/${id}`, { method: "DELETE" }),
  capabilities: () => fetchApi("/api/chat/capabilities"),
};

// Settings
export const settingsApi = {
  get: () => fetchApi("/api/settings/"),
  save: (data: any) => fetchApi("/api/settings/", { method: "POST", body: JSON.stringify(data) }),
};

// Documents
export const documentsApi = {
  upload: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/documents/upload`, { method: "POST", body: form });
    return res.json();
  },
  search: (query: string, limit = 5) =>
    fetchApi("/api/documents/search", { method: "POST", body: JSON.stringify({ query, limit }) }),
  list: () => fetchApi("/api/documents/"),
  delete: (id: string) => fetchApi(`/api/documents/${id}`, { method: "DELETE" }),
};

// Self-test
export const selfTestApi = {
  run: () => fetchApi("/api/selftest/run", { method: "POST" }),
};

// Other
export const workspaceApi = { tree: () => fetchApi("/api/workspace/tree") };
export const notificationsApi = {
  list: () => fetchApi<any[]>("/api/notifications/"),
  readAll: () => fetchApi("/api/notifications/read-all", { method: "POST" }),
};
export const queueApi = { status: () => fetchApi("/api/queue/status") };
export const schedulerApi = {
  jobs: () => fetchApi<any[]>("/api/scheduler/jobs"),
  create: (data: any) => fetchApi("/api/scheduler/jobs", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) => fetchApi(`/api/scheduler/jobs/${id}`, { method: "DELETE" }),
};
export const tokensApi = { stats: () => fetchApi("/api/tokens/stats") };
export const logsApi = {
  list: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return fetchApi<any[]>(`/api/logs/${qs}`);
  },
};
export const healthApi = { check: () => fetchApi("/health") };

// WebSocket
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: any = null;
  onEvent: ((event: any) => void) | null = null;
  onConnect: (() => void) | null = null;
  onDisconnect: (() => void) | null = null;

  connect() {
    try {
      this.ws = new WebSocket(`${WS_URL}/api/stream/ws`);
      this.ws.onopen = () => { this.onConnect?.(); };
      this.ws.onmessage = (e) => {
        try { const data = JSON.parse(e.data); this.onEvent?.(data); } catch {}
      };
      this.ws.onclose = () => {
        this.onDisconnect?.();
        this.reconnectTimer = setTimeout(() => this.connect(), 3000);
      };
      this.ws.onerror = () => { this.ws?.close(); };
    } catch {}
  }

  disconnect() {
    clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }
}
