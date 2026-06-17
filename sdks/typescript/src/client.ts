import { MiLyfeBrainError } from './errors';
import type {
  AgentRole,
  AgentState,
  ChatMessage,
  ChatSendRequest,
  HealthResponse,
  MiLyfeBrainConfig,
  Playbook,
  PlaybookCreate,
  PlaybookStatus,
  StreamEvent,
  TokenStats,
} from './types';

/**
 * MiLyfe Brain TypeScript SDK Client.
 *
 * @example
 * ```ts
 * const client = new MiLyfeBrainClient({ baseUrl: 'http://localhost:8200' });
 * const playbook = await client.createPlaybook({
 *   title: 'Build API',
 *   description: 'Create a REST API with CRUD endpoints',
 * });
 * ```
 */
export class MiLyfeBrainClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  private timeout: number;

  constructor(config: MiLyfeBrainConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.timeout = config.timeout ?? 300000;
    this.headers = {
      'Content-Type': 'application/json',
    };
    if (config.apiKey) {
      this.headers['X-API-Key'] = config.apiKey;
    }
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    params?: Record<string, string | number>,
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url.toString(), {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new MiLyfeBrainError(response.status, error.detail ?? response.statusText);
      }

      if (response.status === 204) return undefined as T;
      return response.json() as Promise<T>;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ─── Health ────────────────────────────────────────────────────────

  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('GET', '/health');
  }

  // ─── Playbooks ─────────────────────────────────────────────────────

  async createPlaybook(data: PlaybookCreate): Promise<Playbook> {
    return this.request<Playbook>('POST', '/api/playbooks/', data);
  }

  async listPlaybooks(status?: string, limit = 50): Promise<Playbook[]> {
    const params: Record<string, string | number> = { limit };
    if (status) params.status = status;
    return this.request<Playbook[]>('GET', '/api/playbooks/', undefined, params);
  }

  async getPlaybook(id: string): Promise<Playbook> {
    return this.request<Playbook>('GET', `/api/playbooks/${id}`);
  }

  async getPlaybookStatus(id: string): Promise<PlaybookStatus> {
    return this.request<PlaybookStatus>('GET', `/api/playbooks/${id}/status`);
  }

  async rerunPlaybook(id: string): Promise<Playbook> {
    return this.request<Playbook>('POST', `/api/playbooks/${id}/rerun`);
  }

  async deletePlaybook(id: string): Promise<void> {
    await this.request<void>('DELETE', `/api/playbooks/${id}`);
  }

  // ─── Agents ────────────────────────────────────────────────────────

  async listActiveAgents(): Promise<AgentState[]> {
    return this.request<AgentState[]>('GET', '/api/agents/active');
  }

  async spawnAgent(role: AgentRole, task: string, model?: string): Promise<AgentState> {
    return this.request<AgentState>('POST', '/api/agents/spawn', { role, task, model });
  }

  async retireAgent(id: string): Promise<void> {
    await this.request<void>('DELETE', `/api/agents/${id}`);
  }

  // ─── Chat ──────────────────────────────────────────────────────────

  async chat(data: ChatSendRequest): Promise<ChatMessage> {
    return this.request<ChatMessage>('POST', '/api/chat/send', data);
  }

  async getChatHistory(sessionId: string): Promise<ChatMessage[]> {
    return this.request<ChatMessage[]>('GET', `/api/chat/history/${sessionId}`);
  }

  async listChatSessions(): Promise<Array<{ id: string; title: string; created_at: string }>> {
    return this.request('GET', '/api/chat/sessions');
  }

  // ─── Streaming (SSE) ───────────────────────────────────────────────

  async *streamEvents(): AsyncGenerator<StreamEvent> {
    const response = await fetch(`${this.baseUrl}/api/stream/sse`, {
      headers: this.headers,
    });

    if (!response.body) throw new Error('No response body for SSE stream');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          yield data as StreamEvent;
        }
      }
    }
  }

  // ─── Documents ─────────────────────────────────────────────────────

  async uploadDocument(file: File | Blob, collection = 'default'): Promise<unknown> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('collection', collection);

    const response = await fetch(`${this.baseUrl}/api/documents/upload`, {
      method: 'POST',
      headers: { ...(this.headers['X-API-Key'] ? { 'X-API-Key': this.headers['X-API-Key'] } : {}) },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new MiLyfeBrainError(response.status, error.detail);
    }
    return response.json();
  }

  async searchDocuments(query: string, nResults = 5): Promise<unknown[]> {
    const result = await this.request<{ results: unknown[] }>('POST', '/api/documents/search', {
      query,
      n_results: nResults,
    });
    return result.results;
  }

  // ─── Tokens ────────────────────────────────────────────────────────

  async getTokenStats(days = 7): Promise<TokenStats> {
    return this.request<TokenStats>('GET', '/api/tokens/stats', undefined, { days });
  }

  // ─── Settings ──────────────────────────────────────────────────────

  async getSettings(): Promise<Record<string, unknown>> {
    return this.request('GET', '/api/settings/');
  }

  async updateSettings(settings: Record<string, unknown>): Promise<void> {
    await this.request('POST', '/api/settings/', settings);
  }

  // ─── Self-test ─────────────────────────────────────────────────────

  async runSelfTest(): Promise<{ passed: boolean; tests: Array<{ name: string; passed: boolean }> }> {
    return this.request('POST', '/api/selftest/run');
  }
}
