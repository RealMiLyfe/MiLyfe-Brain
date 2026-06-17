// MiLyfe Brain API Client - Full typed API covering all 19 endpoint groups

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface Playbook {
  id: string;
  title: string;
  description: string;
  steps: PlaybookStep[];
  status: PlaybookStatus;
  model: string;
  created_at: string;
  updated_at: string;
}

export interface PlaybookStep {
  id: string;
  name: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  agent_role?: string;
  output?: string;
  started_at?: string;
  completed_at?: string;
}

export type PlaybookStatus = "draft" | "running" | "paused" | "completed" | "failed" | "cancelled";

export interface Agent {
  id: string;
  role: string;
  name: string;
  status: "idle" | "active" | "busy" | "retired";
  current_task?: string;
  model: string;
  spawned_at: string;
  tokens_used: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: string;
  session_id: string;
  tool_calls?: ToolCall[];
  model?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
  last_message_at: string;
}

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  uploaded_at: string;
  chunks: number;
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  uptime: number;
  services: Record<string, boolean>;
}

export interface SelfTestResult {
  name: string;
  passed: boolean;
  duration_ms: number;
  message?: string;
}

export interface Settings {
  model_light: string;
  model_heavy: string;
  model_premium: string;
  approval_destructive: boolean;
  approval_browsing: boolean;
  approval_gui: boolean;
  workspace_path: string;
  max_concurrent_agents: number;
  auto_approve_safe: boolean;
}

export interface Notification {
  id: string;
  type: "info" | "warning" | "error" | "success";
  title: string;
  message: string;
  read: boolean;
  created_at: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: "debug" | "info" | "warning" | "error";
  role?: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface SchedulerJob {
  id: string;
  name: string;
  cron_expression: string;
  playbook_id?: string;
  command?: string;
  enabled: boolean;
  last_run?: string;
  next_run?: string;
}

export interface TokenStats {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  by_model: Record<string, { tokens: number; cost: number }>;
  by_agent: Record<string, { tokens: number; cost: number }>;
}

export interface QueueItem {
  id: string;
  type: string;
  status: "waiting" | "running" | "completed" | "failed";
  priority: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  agent_id?: string;
}

export interface QueueStatusData {
  running: number;
  waiting: number;
  completed: number;
  failed: number;
  items: QueueItem[];
}

export interface DaemonStatus {
  running: boolean;
  pid?: number;
  uptime?: number;
  memory_mb?: number;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

export interface WorkspaceNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: WorkspaceNode[];
  size?: number;
}

export interface StreamEvent {
  id: string;
  type: string;
  agent_role?: string;
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface DigestData {
  summary: string;
  stats: {
    playbooks_run: number;
    agents_spawned: number;
    tokens_used: number;
    errors: number;
  };
  highlights: string[];
}

// ─── API Client ─────────────────────────────────────────────────────────────

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  // Remove Content-Type for FormData
  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "Unknown error");
    throw new ApiError(response.status, errorBody);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) return undefined as unknown as T;
  return JSON.parse(text) as T;
}

// ─── Playbook Endpoints ─────────────────────────────────────────────────────

export async function createPlaybook(data: {
  prompt: string;
  model?: string;
  auto_execute?: boolean;
}): Promise<Playbook> {
  return request<Playbook>("/api/playbooks", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listPlaybooks(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<Playbook[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return request<Playbook[]>(`/api/playbooks${query}`);
}

export async function getPlaybook(id: string): Promise<Playbook> {
  return request<Playbook>(`/api/playbooks/${id}`);
}

export async function getPlaybookStatus(id: string): Promise<{
  status: PlaybookStatus;
  progress: number;
  current_step?: string;
  steps: PlaybookStep[];
}> {
  return request(`/api/playbooks/${id}/status`);
}

export async function rerunPlaybook(id: string): Promise<Playbook> {
  return request<Playbook>(`/api/playbooks/${id}/rerun`, {
    method: "POST",
  });
}

export async function deletePlaybook(id: string): Promise<void> {
  return request<void>(`/api/playbooks/${id}`, {
    method: "DELETE",
  });
}

// ─── Agent Endpoints ────────────────────────────────────────────────────────

export async function spawnAgent(data: {
  role: string;
  model?: string;
  task?: string;
}): Promise<Agent> {
  return request<Agent>("/api/agents/spawn", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listActiveAgents(): Promise<Agent[]> {
  return request<Agent[]>("/api/agents");
}

export async function retireAgent(id: string): Promise<void> {
  return request<void>(`/api/agents/${id}/retire`, {
    method: "POST",
  });
}

// ─── Chat Endpoints ─────────────────────────────────────────────────────────

export async function chatSend(data: {
  message: string;
  session_id?: string;
  model?: string;
}): Promise<ChatMessage> {
  return request<ChatMessage>("/api/chat/send", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getChatHistory(sessionId: string): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/api/chat/history/${sessionId}`);
}

export async function listSessions(): Promise<ChatSession[]> {
  return request<ChatSession[]>("/api/chat/sessions");
}

// ─── Document Endpoints ─────────────────────────────────────────────────────

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  return request<Document>("/api/documents/upload", {
    method: "POST",
    body: formData,
  });
}

export async function searchDocuments(query: string, limit?: number): Promise<Document[]> {
  const params = new URLSearchParams({ query });
  if (limit) params.set("limit", String(limit));
  return request<Document[]>(`/api/documents/search?${params.toString()}`);
}

// ─── Health Endpoints ───────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/api/health");
}

export async function runSelfTest(): Promise<SelfTestResult[]> {
  return request<SelfTestResult[]>("/api/selftest", {
    method: "POST",
  });
}

// ─── Settings Endpoints ─────────────────────────────────────────────────────

export async function getSettings(): Promise<Settings> {
  return request<Settings>("/api/settings");
}

export async function updateSettings(data: Partial<Settings>): Promise<Settings> {
  return request<Settings>("/api/settings", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ─── Workspace / Filesystem Endpoints ───────────────────────────────────────

export async function getWorkspaceTree(): Promise<WorkspaceNode[]> {
  return request<WorkspaceNode[]>("/api/workspace/tree");
}

export async function downloadWorkspace(): Promise<Blob> {
  const response = await fetch(`${BASE_URL}/api/workspace/download`);
  if (!response.ok) throw new ApiError(response.status, "Download failed");
  return response.blob();
}

// ─── Notification Endpoints ─────────────────────────────────────────────────

export async function getNotifications(params?: {
  unread_only?: boolean;
  limit?: number;
}): Promise<Notification[]> {
  const searchParams = new URLSearchParams();
  if (params?.unread_only) searchParams.set("unread_only", "true");
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return request<Notification[]>(`/api/notifications${query}`);
}

export async function markAllRead(): Promise<void> {
  return request<void>("/api/notifications/read-all", {
    method: "POST",
  });
}

// ─── Log Endpoints ──────────────────────────────────────────────────────────

export async function getLogs(params?: {
  level?: string;
  role?: string;
  limit?: number;
  offset?: number;
  search?: string;
}): Promise<{ logs: LogEntry[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.level) searchParams.set("level", params.level);
  if (params?.role) searchParams.set("role", params.role);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.search) searchParams.set("search", params.search);
  const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return request<{ logs: LogEntry[]; total: number }>(`/api/logs${query}`);
}

// ─── Scheduler Endpoints ────────────────────────────────────────────────────

export async function getSchedulerJobs(): Promise<SchedulerJob[]> {
  return request<SchedulerJob[]>("/api/scheduler/jobs");
}

export async function createSchedulerJob(data: {
  name: string;
  cron_expression: string;
  playbook_id?: string;
  command?: string;
  enabled?: boolean;
}): Promise<SchedulerJob> {
  return request<SchedulerJob>("/api/scheduler/jobs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSchedulerJob(
  id: string,
  data: Partial<SchedulerJob>
): Promise<SchedulerJob> {
  return request<SchedulerJob>(`/api/scheduler/jobs/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteSchedulerJob(id: string): Promise<void> {
  return request<void>(`/api/scheduler/jobs/${id}`, {
    method: "DELETE",
  });
}

// ─── Token Stats Endpoints ──────────────────────────────────────────────────

export async function getTokenStats(): Promise<TokenStats> {
  return request<TokenStats>("/api/tokens/stats");
}

// ─── Queue Endpoints ────────────────────────────────────────────────────────

export async function getQueueStatus(): Promise<QueueStatusData> {
  return request<QueueStatusData>("/api/queue/status");
}

// ─── Daemon Endpoints ───────────────────────────────────────────────────────

export async function getDaemonStatus(): Promise<DaemonStatus> {
  return request<DaemonStatus>("/api/daemon/status");
}

// ─── Skills Endpoints ───────────────────────────────────────────────────────

export async function getSkills(): Promise<Skill[]> {
  return request<Skill[]>("/api/skills");
}

// ─── Digest Endpoint ────────────────────────────────────────────────────────

export async function getDigest(): Promise<DigestData> {
  return request<DigestData>("/api/digest");
}

// ─── Streaming / SSE ────────────────────────────────────────────────────────

export function createEventSource(playbookId: string): EventSource {
  return new EventSource(`${BASE_URL}/api/stream/${playbookId}`);
}

// ─── Export ─────────────────────────────────────────────────────────────────

export { ApiError };
