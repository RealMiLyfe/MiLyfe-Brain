/**
 * MiLyfe Brain — Full typed API client.
 * Covers all 19 endpoint groups.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8200";

async function fetchAPI(path: string, options?: RequestInit) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text().catch(() => "Unknown error");
    throw new Error(`API Error ${res.status}: ${error}`);
  }
  return res.json();
}

// ─── Playbook API ────────────────────────────────────────────────────────────

export const playbookApi = {
  create: (data: { title: string; description: string; raw_text?: string; auto_execute?: boolean }) =>
    fetchAPI("/api/playbooks/", { method: "POST", body: JSON.stringify(data) }),
  list: () => fetchAPI("/api/playbooks/"),
  get: (id: string) => fetchAPI(`/api/playbooks/${id}`),
  getStatus: (id: string) => fetchAPI(`/api/playbooks/${id}/status`),
  getGraph: (id: string) => fetchAPI(`/api/playbooks/${id}/graph`),
  rerun: (id: string) => fetchAPI(`/api/playbooks/${id}/rerun`, { method: "POST" }),
  delete: (id: string) => fetchAPI(`/api/playbooks/${id}`, { method: "DELETE" }),
};

// ─── Agent API ───────────────────────────────────────────────────────────────

export const agentApi = {
  roles: () => fetchAPI("/api/agents/roles"),
  active: () => fetchAPI("/api/agents/active"),
  spawn: (role: string, model?: string) =>
    fetchAPI("/api/agents/spawn", { method: "POST", body: JSON.stringify({ role, model }) }),
  message: (id: string, message: string) =>
    fetchAPI(`/api/agents/${id}/message`, { method: "POST", body: JSON.stringify({ message }) }),
  retire: (id: string) => fetchAPI(`/api/agents/${id}`, { method: "DELETE" }),
};

// ─── Chat API ────────────────────────────────────────────────────────────────

export const chatApi = {
  send: (message: string, session_id?: string, model?: string) =>
    fetchAPI("/api/chat/send", { method: "POST", body: JSON.stringify({ message, session_id, model }) }),
  history: (sessionId: string) => fetchAPI(`/api/chat/history/${sessionId}`),
  sessions: () => fetchAPI("/api/chat/sessions"),
  deleteSession: (id: string) => fetchAPI(`/api/chat/sessions/${id}`, { method: "DELETE" }),
  capabilities: () => fetchAPI("/api/chat/capabilities"),
};

// ─── Settings API ────────────────────────────────────────────────────────────

export const settingsApi = {
  get: () => fetchAPI("/api/settings/"),
  save: (settings: Record<string, any>) =>
    fetchAPI("/api/settings/", { method: "POST", body: JSON.stringify({ settings }) }),
};

// ─── Documents API ───────────────────────────────────────────────────────────

export const documentsApi = {
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_URL}/api/documents/upload`, { method: "POST", body: formData });
    return res.json();
  },
  search: (query: string, limit?: number) =>
    fetchAPI("/api/documents/search", { method: "POST", body: JSON.stringify({ query, limit }) }),
  list: () => fetchAPI("/api/documents/"),
  delete: (id: string) => fetchAPI(`/api/documents/${id}`, { method: "DELETE" }),
};

// ─── Workspace API ───────────────────────────────────────────────────────────

export const workspaceApi = {
  tree: (path?: string) => fetchAPI(`/api/workspace/tree${path ? `?path=${path}` : ""}`),
  read: (path: string) => fetchAPI(`/api/workspace/read?path=${path}`),
  recent: () => fetchAPI("/api/workspace/recent"),
};

// ─── Self-Test API ───────────────────────────────────────────────────────────

export const selfTestApi = {
  run: () => fetchAPI("/api/selftest/run", { method: "POST" }),
};

// ─── Notifications API ───────────────────────────────────────────────────────

export const notificationsApi = {
  list: (unreadOnly?: boolean) => fetchAPI(`/api/notifications/?unread_only=${unreadOnly || false}`),
  readAll: () => fetchAPI("/api/notifications/read-all", { method: "POST" }),
};

// ─── Queue API ───────────────────────────────────────────────────────────────

export const queueApi = {
  status: () => fetchAPI("/api/queue/status"),
  pause: () => fetchAPI("/api/queue/pause", { method: "POST" }),
  resume: () => fetchAPI("/api/queue/resume", { method: "POST" }),
};

// ─── Scheduler API ───────────────────────────────────────────────────────────

export const schedulerApi = {
  list: () => fetchAPI("/api/scheduler/jobs"),
  create: (data: { title: string; cron_expression: string; playbook_id?: string }) =>
    fetchAPI("/api/scheduler/jobs", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) => fetchAPI(`/api/scheduler/jobs/${id}`, { method: "DELETE" }),
};

// ─── Export/Import API ───────────────────────────────────────────────────────

export const exportImportApi = {
  export: (id: string) => fetchAPI(`/api/playbooks/io/export/${id}`, { method: "POST" }),
  import: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_URL}/api/playbooks/io/import`, { method: "POST", body: formData });
    return res.json();
  },
};

// ─── Tokens API ──────────────────────────────────────────────────────────────

export const tokensApi = {
  stats: () => fetchAPI("/api/tokens/stats"),
  history: (days?: number) => fetchAPI(`/api/tokens/history?days=${days || 7}`),
};

// ─── Logs API ────────────────────────────────────────────────────────────────

export const logsApi = {
  list: (params?: { playbook_id?: string; agent_role?: string; limit?: number }) => {
    const query = new URLSearchParams(params as any).toString();
    return fetchAPI(`/api/logs/?${query}`);
  },
  stats: () => fetchAPI("/api/logs/stats"),
};

// ─── Download API ────────────────────────────────────────────────────────────

export const downloadApi = {
  workspace: () => `${API_URL}/api/download/workspace`,
};

// ─── Health API ──────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => fetchAPI("/health"),
};

// ─── Brain API ───────────────────────────────────────────────────────────────

export const brainApi = {
  daemonStatus: () => fetchAPI("/api/brain/daemon/status"),
  skills: () => fetchAPI("/api/brain/skills"),
  memory: (role?: string) => fetchAPI(`/api/brain/memory${role ? `?role=${role}` : ""}`),
  digest: () => fetchAPI("/api/brain/digest"),
};

// ─── WebSocket Client ────────────────────────────────────────────────────────

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(`${WS_URL}/api/stream/ws`);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data.event_type || "unknown";
        this.listeners.get(eventType)?.forEach((cb) => cb(data));
        this.listeners.get("*")?.forEach((cb) => cb(data));
      } catch {}
    };

    this.ws.onclose = () => {
      this.reconnectTimeout = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = () => this.ws?.close();
  }

  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event)!.add(callback);
    return () => this.listeners.get(event)?.delete(callback);
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.ws?.close();
  }
}
