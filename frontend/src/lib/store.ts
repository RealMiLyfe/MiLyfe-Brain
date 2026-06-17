/**
 * Zustand Global State Store
 */

import { create } from "zustand";

export interface AgentState {
  id: string;
  role: string;
  name: string;
  status: string;
  current_task: string | null;
  thoughts: string[];
  actions_taken: any[];
  progress: number;
  model: string;
  avatar_color: string;
}

export interface StreamEvent {
  event_type: string;
  agent_id?: string;
  agent_role?: string;
  data: Record<string, any>;
  timestamp: string;
}

export interface Playbook {
  id: string;
  title: string;
  description: string;
  status: string;
  steps: any[];
  created_at: string;
  completed_at?: string;
  error?: string;
}

export interface ApprovalRequest {
  id: string;
  action_type: string;
  description: string;
  details: Record<string, any>;
  agent_id: string;
  agent_role: string;
  risk_level: string;
}

interface BrainStore {
  // Agents
  agents: Map<string, AgentState>;
  setAgent: (agent: AgentState) => void;
  removeAgent: (id: string) => void;

  // Events
  events: StreamEvent[];
  addEvent: (event: StreamEvent) => void;
  clearEvents: () => void;

  // Playbook
  currentPlaybook: Playbook | null;
  setCurrentPlaybook: (playbook: Playbook | null) => void;

  // Approvals
  pendingApprovals: ApprovalRequest[];
  addApproval: (approval: ApprovalRequest) => void;
  removeApproval: (id: string) => void;

  // Connection
  isConnected: boolean;
  setConnected: (connected: boolean) => void;

  // Theme
  isDark: boolean;
  toggleTheme: () => void;

  // Active view
  activeView: string;
  setActiveView: (view: string) => void;
}

export const useBrainStore = create<BrainStore>((set) => ({
  // Agents
  agents: new Map(),
  setAgent: (agent) =>
    set((state) => {
      const agents = new Map(state.agents);
      agents.set(agent.id, agent);
      return { agents };
    }),
  removeAgent: (id) =>
    set((state) => {
      const agents = new Map(state.agents);
      agents.delete(id);
      return { agents };
    }),

  // Events
  events: [],
  addEvent: (event) =>
    set((state) => ({
      events: [...state.events.slice(-200), event],
    })),
  clearEvents: () => set({ events: [] }),

  // Playbook
  currentPlaybook: null,
  setCurrentPlaybook: (playbook) => set({ currentPlaybook: playbook }),

  // Approvals
  pendingApprovals: [],
  addApproval: (approval) =>
    set((state) => ({ pendingApprovals: [...state.pendingApprovals, approval] })),
  removeApproval: (id) =>
    set((state) => ({
      pendingApprovals: state.pendingApprovals.filter((a) => a.id !== id),
    })),

  // Connection
  isConnected: false,
  setConnected: (connected) => set({ isConnected: connected }),

  // Theme
  isDark: true,
  toggleTheme: () => set((state) => ({ isDark: !state.isDark })),

  // View
  activeView: "playbook",
  setActiveView: (view) => set({ activeView: view }),
}));
