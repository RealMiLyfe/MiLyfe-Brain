export type AgentRole =
  | 'orchestrator'
  | 'researcher'
  | 'coder'
  | 'executor'
  | 'critic'
  | 'designer'
  | 'writer'
  | 'debugger'
  | 'planner';

export type TaskStatus =
  | 'pending'
  | 'running'
  | 'awaiting_approval'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type TaskComplexity = 'light' | 'medium' | 'heavy';

export interface MiLyfeBrainConfig {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
}

export interface PlaybookStep {
  id: string;
  description: string;
  agent_role?: AgentRole;
  depends_on: string[];
  complexity: TaskComplexity;
  tools_needed: string[];
  status?: TaskStatus;
  result?: string;
}

export interface PlaybookCreate {
  title: string;
  description: string;
  raw_text?: string;
  steps?: PlaybookStep[];
  auto_execute?: boolean;
}

export interface Playbook {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  steps: PlaybookStep[];
  created_at: string;
  completed_at?: string;
  error?: string;
}

export interface PlaybookStatus {
  status: TaskStatus;
  progress: number;
  current_step?: string;
  agents_active: number;
  steps_completed: number;
  steps_total: number;
}

export interface AgentState {
  id: string;
  role: AgentRole;
  name: string;
  status: string;
  current_task?: string;
  thoughts: string[];
  actions_taken: number;
  progress: number;
  model: string;
  avatar_color: string;
}

export interface StreamEvent {
  event_type: string;
  agent_id?: string;
  agent_role?: AgentRole;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: string;
  content: string;
  model?: string;
  tokens_used: number;
  tool_calls: Record<string, unknown>[];
  created_at: string;
}

export interface ChatSendRequest {
  message: string;
  session_id?: string;
  model?: string;
  context_files?: string[];
}

export interface ApprovalRequest {
  id: string;
  action_type: string;
  description: string;
  details: Record<string, unknown>;
  agent_id: string;
  agent_role: AgentRole;
  risk_level: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  services: {
    ollama: 'connected' | 'disconnected';
    chromadb: 'connected' | 'disconnected';
    redis: 'connected' | 'disconnected';
    database: 'connected' | 'disconnected';
  };
  uptime_seconds: number;
}

export interface TokenStats {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  by_model: Record<string, number>;
  by_role: Record<string, number>;
}
