import { create } from "zustand";

// Types
export interface AgentState {
  id: string;
  role: string;
  name: string;
  status: string;
  current_task: string | null;
  thoughts: string[];
  actions_taken: number;
  progress: number;
  model: string;
  avatar_color: string;
}

export interface StreamEvent {
  event_type: string;
  agent_id: string | null;
  agent_role: string | null;
  data: Record<string, any>;
  timestamp: string;
  playbook_id: string | null;
}

export interface Playbook {
  id: string;
  title: string;
  description: string;
  status: string;
  steps: any[];
  created_at: string;
  total_tokens: number;
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

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
}

// View type
export type ViewType =
  | "playbook"
  | "editor"
  | "dashboard"
  | "chat"
  | "queue"
  | "scheduler"
  | "history"
  | "logs"
  | "settings";

// Store
interface BrainStore {
  // Navigation
  currentView: ViewType;
  setView: (view: ViewType) => void;

  // Agents
  agents: Map<string, AgentState>;
  setAgents: (agents: AgentState[]) => void;

  // Events
  events: StreamEvent[];
  addEvent: (event: StreamEvent) => void;
  clearEvents: () => void;

  // Playbooks
  currentPlaybook: Playbook | null;
  setCurrentPlaybook: (pb: Playbook | null) => void;
  playbooks: Playbook[];
  setPlaybooks: (pbs: Playbook[]) => void;

  // Approvals
  pendingApprovals: ApprovalRequest[];
  addApproval: (req: ApprovalRequest) => void;
  removeApproval: (id: string) => void;

  // Notifications
  notifications: Notification[];
  unreadCount: number;
  setNotifications: (notifs: Notification[]) => void;
  addNotification: (notif: Notification) => void;

  // Connection
  isConnected: boolean;
  setConnected: (v: boolean) => void;

  // Theme
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useBrainStore = create<BrainStore>((set, get) => ({
  // Navigation
  currentView: "playbook",
  setView: (view) => set({ currentView: view }),

  // Agents
  agents: new Map(),
  setAgents: (agents) => {
    const map = new Map<string, AgentState>();
    agents.forEach((a) => map.set(a.id, a));
    set({ agents: map });
  },

  // Events
  events: [],
  addEvent: (event) =>
    set((s) => ({ events: [...s.events.slice(-200), event] })),
  clearEvents: () => set({ events: [] }),

  // Playbooks
  currentPlaybook: null,
  setCurrentPlaybook: (pb) => set({ currentPlaybook: pb }),
  playbooks: [],
  setPlaybooks: (pbs) => set({ playbooks: pbs }),

  // Approvals
  pendingApprovals: [],
  addApproval: (req) =>
    set((s) => ({ pendingApprovals: [...s.pendingApprovals, req] })),
  removeApproval: (id) =>
    set((s) => ({
      pendingApprovals: s.pendingApprovals.filter((a) => a.id !== id),
    })),

  // Notifications
  notifications: [],
  unreadCount: 0,
  setNotifications: (notifs) =>
    set({ notifications: notifs, unreadCount: notifs.filter((n) => !n.read).length }),
  addNotification: (notif) =>
    set((s) => ({
      notifications: [notif, ...s.notifications],
      unreadCount: s.unreadCount + 1,
    })),

  // Connection
  isConnected: false,
  setConnected: (v) => set({ isConnected: v }),

  // Sidebar
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
}));
