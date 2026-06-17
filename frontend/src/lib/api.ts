import type {
  StreamEvent,
  Playbook,
  PlaybookStep,
  Agent,
  Notification,
  PendingApproval,
} from "./store";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Fetch helper ---

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${errorBody}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Types ---

export interface PlaybookCreateRequest {
  title: string;
  natural_language_input: string;
  steps?: Partial<PlaybookStep>[];
}

export interface PlaybookStatusResponse {
  id: string;
  status: string;
  progress: number;
  steps_completed: number;
  steps_total: number;
  steps_running: number;
  steps_failed: number;
  current_step?: string;
  error?: string;
}

export interface PlaybookGraphResponse {
  nodes: Array<{
    id: string;
    label: string;
    status: string;
    x: number;
    y: number;
  }>;
  edges: Array<{ from: string; to: string }>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

export interface Settings {
  model_light: string;
  model_heavy: string;
  model_premium: string;
  safety_enabled: boolean;
  human_in_loop: boolean;
  max_concurrent_agents: number;
  auto_approve_low_risk: boolean;
}

export interface Document {
  id: string;
  filename: string;
  size: number;
  uploaded_at: string;
  chunk_count: number;
}

export interface SelfTestResult {
  test_name: string;
  passed: boolean;
  message: string;
  duration_ms: number;
}

export interface SchedulerJob {
  id: string;
  title: string;
  cron: string;
  next_run: string;
  last_run?: string;
  enabled: boolean;
}

export interface QueueStatusResponse {
  running: { id: string; title: string; started_at: string } | null;
  waiting: Array<{ id: string; title: string; queued_at: string }>;
  completed: Array<{
    id: string;
    title: string;
    completed_at: string;
    status: string;
  }>;
}

export interface TokenStats {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_estimate: number;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  role: string;
  action: string;
  description: string;
  risk_level: string;
}

// --- API Modules ---

export const playbookApi = {
  create: (data: PlaybookCreateRequest) =>
    fetchApi<Playbook>("/api/playbooks", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  list: () => fetchApi<Playbook[]>("/api/playbooks"),

  get: (id: string) => fetchApi<Playbook>(`/api/playbooks/${id}`),

  getStatus: (id: string) =>
    fetchApi<PlaybookStatusResponse>(`/api/playbooks/${id}/status`),

  getGraph: (id: string) =>
    fetchApi<PlaybookGraphResponse>(`/api/playbooks/${id}/graph`),

  rerun: (id: string) =>
    fetchApi<Playbook>(`/api/playbooks/${id}/rerun`, { method: "POST" }),

  delete: (id: string) =>
    fetchApi<void>(`/api/playbooks/${id}`, { method: "DELETE" }),
};

export const agentApi = {
  roles: () => fetchApi<string[]>("/api/agents/roles"),

  active: () => fetchApi<Agent[]>("/api/agents/active"),

  spawn: (role: string) =>
    fetchApi<Agent>("/api/agents/spawn", {
      method: "POST",
      body: JSON.stringify({ role }),
    }),

  retire: (id: string) =>
    fetchApi<void>(`/api/agents/${id}/retire`, { method: "POST" }),
};

export const chatApi = {
  send: (sessionId: string, message: string) =>
    fetchApi<ChatMessage>(`/api/chat/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content: message }),
    }),

  history: (sessionId: string) =>
    fetchApi<ChatMessage[]>(`/api/chat/${sessionId}/messages`),

  sessions: () => fetchApi<ChatSession[]>("/api/chat/sessions"),

  delete: (sessionId: string) =>
    fetchApi<void>(`/api/chat/${sessionId}`, { method: "DELETE" }),
};

export const settingsApi = {
  get: () => fetchApi<Settings>("/api/settings"),

  save: (settings: Partial<Settings>) =>
    fetchApi<Settings>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),
};

export const documentsApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${API_BASE}/api/documents/upload`, {
      method: "POST",
      body: formData,
    }).then((res) => {
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      return res.json() as Promise<Document>;
    });
  },

  search: (query: string) =>
    fetchApi<Array<{ id: string; content: string; score: number }>>(
      `/api/documents/search?q=${encodeURIComponent(query)}`
    ),

  list: () => fetchApi<Document[]>("/api/documents"),

  delete: (id: string) =>
    fetchApi<void>(`/api/documents/${id}`, { method: "DELETE" }),
};

export const selfTestApi = {
  run: () => fetchApi<SelfTestResult[]>("/api/selftest/run", { method: "POST" }),
};

export const workspaceApi = {
  tree: () => fetchApi<{ name: string; type: string; children?: unknown[] }>("/api/workspace/tree"),
};

export const notificationsApi = {
  list: () => fetchApi<Notification[]>("/api/notifications"),

  readAll: () =>
    fetchApi<void>("/api/notifications/read-all", { method: "POST" }),
};

export const queueApi = {
  status: () => fetchApi<QueueStatusResponse>("/api/queue/status"),
};

export const schedulerApi = {
  jobs: () => fetchApi<SchedulerJob[]>("/api/scheduler/jobs"),

  create: (data: { title: string; cron: string }) =>
    fetchApi<SchedulerJob>("/api/scheduler/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/scheduler/jobs/${id}`, { method: "DELETE" }),
};

export const tokensApi = {
  stats: () => fetchApi<TokenStats>("/api/tokens/stats"),
};

export const logsApi = {
  list: (params?: { role?: string; action?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.role) searchParams.set("role", params.role);
    if (params?.action) searchParams.set("action", params.action);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    const qs = searchParams.toString();
    return fetchApi<LogEntry[]>(`/api/logs${qs ? `?${qs}` : ""}`);
  },
};

export const healthApi = {
  check: () => fetchApi<{ status: string; version: string }>("/api/health"),
};

// --- WebSocket Client ---

type EventHandler = (event: StreamEvent) => void;
type ConnectionHandler = () => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private eventHandlers: EventHandler[] = [];
  private connectHandlers: ConnectionHandler[] = [];
  private disconnectHandlers: ConnectionHandler[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private shouldReconnect = true;

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const wsBase = API_BASE.replace(/^http/, "ws");
    this.ws = new WebSocket(`${wsBase}/ws/stream`);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.connectHandlers.forEach((h) => h());
    };

    this.ws.onmessage = (msg) => {
      try {
        const event: StreamEvent = JSON.parse(msg.data);
        this.eventHandlers.forEach((h) => h(event));
      } catch {
        console.warn("Failed to parse WebSocket message:", msg.data);
      }
    };

    this.ws.onclose = () => {
      this.disconnectHandlers.forEach((h) => h());
      if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        this.reconnectTimer = setTimeout(() => {
          this.reconnectAttempts++;
          this.connect();
        }, delay);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  onEvent(handler: EventHandler): () => void {
    this.eventHandlers.push(handler);
    return () => {
      this.eventHandlers = this.eventHandlers.filter((h) => h !== handler);
    };
  }

  onConnect(handler: ConnectionHandler): () => void {
    this.connectHandlers.push(handler);
    return () => {
      this.connectHandlers = this.connectHandlers.filter((h) => h !== handler);
    };
  }

  onDisconnect(handler: ConnectionHandler): () => void {
    this.disconnectHandlers.push(handler);
    return () => {
      this.disconnectHandlers = this.disconnectHandlers.filter((h) => h !== handler);
    };
  }
}

export const wsClient = new WebSocketClient();
