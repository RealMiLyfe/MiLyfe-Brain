import { create } from "zustand";

export type ViewType =
  | "playbook"
  | "dashboard"
  | "chat"
  | "queue"
  | "scheduler"
  | "history"
  | "logs"
  | "settings";

export interface Agent {
  id: string;
  role: string;
  state: "idle" | "working" | "completed" | "failed";
  currentTask?: string;
}

export interface StreamEvent {
  id: string;
  timestamp: string;
  type: string;
  role?: string;
  action?: string;
  description: string;
  risk_level?: "low" | "medium" | "high" | "critical";
  data?: Record<string, unknown>;
}

export interface PlaybookStep {
  id: string;
  description: string;
  role: string;
  complexity: "low" | "medium" | "high";
  dependencies: string[];
  status: "pending" | "running" | "completed" | "failed" | "skipped";
}

export interface Playbook {
  id: string;
  title: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  steps: PlaybookStep[];
  created_at: string;
  completed_at?: string;
  error?: string;
}

export interface PendingApproval {
  id: string;
  action_type: string;
  description: string;
  risk_level: "low" | "medium" | "high" | "critical";
  playbook_id: string;
  step_id: string;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
  read: boolean;
  created_at: string;
}

interface AppStore {
  // Navigation
  currentView: ViewType;
  setView: (view: ViewType) => void;

  // Agents
  agents: Map<string, Agent>;
  setAgents: (agents: Map<string, Agent>) => void;
  updateAgent: (id: string, agent: Partial<Agent>) => void;

  // Events
  events: StreamEvent[];
  addEvent: (event: StreamEvent) => void;
  clearEvents: () => void;

  // Playbook
  currentPlaybook: Playbook | null;
  setCurrentPlaybook: (playbook: Playbook | null) => void;
  playbooks: Playbook[];
  setPlaybooks: (playbooks: Playbook[]) => void;

  // Approvals
  pendingApprovals: PendingApproval[];
  addApproval: (approval: PendingApproval) => void;
  removeApproval: (id: string) => void;

  // Notifications
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Notification) => void;
  markAllRead: () => void;

  // Connection
  isConnected: boolean;
  setConnected: (connected: boolean) => void;

  // UI
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
}

export const useStore = create<AppStore>((set, get) => ({
  // Navigation
  currentView: "playbook",
  setView: (view) => set({ currentView: view }),

  // Agents
  agents: new Map(),
  setAgents: (agents) => set({ agents }),
  updateAgent: (id, partial) => {
    const agents = new Map(get().agents);
    const existing = agents.get(id);
    if (existing) {
      agents.set(id, { ...existing, ...partial });
      set({ agents });
    }
  },

  // Events
  events: [],
  addEvent: (event) =>
    set((state) => ({
      events: [event, ...state.events].slice(0, 200),
    })),
  clearEvents: () => set({ events: [] }),

  // Playbook
  currentPlaybook: null,
  setCurrentPlaybook: (playbook) => set({ currentPlaybook: playbook }),
  playbooks: [],
  setPlaybooks: (playbooks) => set({ playbooks }),

  // Approvals
  pendingApprovals: [],
  addApproval: (approval) =>
    set((state) => ({
      pendingApprovals: [...state.pendingApprovals, approval],
    })),
  removeApproval: (id) =>
    set((state) => ({
      pendingApprovals: state.pendingApprovals.filter((a) => a.id !== id),
    })),

  // Notifications
  notifications: [],
  unreadCount: 0,
  addNotification: (notification) =>
    set((state) => ({
      notifications: [notification, ...state.notifications].slice(0, 100),
      unreadCount: state.unreadCount + (notification.read ? 0 : 1),
    })),
  markAllRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  // Connection
  isConnected: false,
  setConnected: (connected) => set({ isConnected: connected }),

  // UI
  sidebarCollapsed: false,
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
}));
