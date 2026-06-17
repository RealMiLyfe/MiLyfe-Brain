import { create } from "zustand";
import type {
  Agent,
  StreamEvent,
  Playbook,
  Notification,
} from "./api";

// ─── Types ──────────────────────────────────────────────────────────────────

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

export interface PendingApproval {
  id: string;
  action: string;
  description: string;
  agent_role: string;
  created_at: string;
  risk_level: "low" | "medium" | "high";
}

interface AppState {
  // Navigation
  activeView: ViewType;
  sidebarCollapsed: boolean;

  // Agents
  agents: Map<string, Agent>;

  // Events / Streaming
  events: StreamEvent[];

  // Playbook
  currentPlaybook: Playbook | null;

  // Approvals
  pendingApprovals: PendingApproval[];

  // Connection
  isConnected: boolean;

  // Theme
  theme: "light" | "dark";

  // Notifications
  notifications: Notification[];
  unreadCount: number;

  // Actions
  setActiveView: (view: ViewType) => void;
  toggleSidebar: () => void;
  addEvent: (event: StreamEvent) => void;
  clearEvents: () => void;
  setPlaybook: (playbook: Playbook | null) => void;
  setAgents: (agents: Agent[]) => void;
  addAgent: (agent: Agent) => void;
  removeAgent: (id: string) => void;
  updateAgent: (id: string, updates: Partial<Agent>) => void;
  addApproval: (approval: PendingApproval) => void;
  resolveApproval: (id: string) => void;
  setConnected: (connected: boolean) => void;
  toggleTheme: () => void;
  setTheme: (theme: "light" | "dark") => void;
  setNotifications: (notifications: Notification[]) => void;
  addNotification: (notification: Notification) => void;
  markAllNotificationsRead: () => void;
}

// ─── Store ──────────────────────────────────────────────────────────────────

export const useStore = create<AppState>((set, get) => ({
  // Initial state
  activeView: "dashboard",
  sidebarCollapsed: false,
  agents: new Map(),
  events: [],
  currentPlaybook: null,
  pendingApprovals: [],
  isConnected: false,
  theme: "dark",
  notifications: [],
  unreadCount: 0,

  // Actions
  setActiveView: (view) => set({ activeView: view }),

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  addEvent: (event) =>
    set((state) => ({
      events: [...state.events.slice(-99), event],
    })),

  clearEvents: () => set({ events: [] }),

  setPlaybook: (playbook) => set({ currentPlaybook: playbook }),

  setAgents: (agents) => {
    const map = new Map<string, Agent>();
    agents.forEach((a) => map.set(a.id, a));
    set({ agents: map });
  },

  addAgent: (agent) =>
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

  updateAgent: (id, updates) =>
    set((state) => {
      const agents = new Map(state.agents);
      const existing = agents.get(id);
      if (existing) {
        agents.set(id, { ...existing, ...updates });
      }
      return { agents };
    }),

  addApproval: (approval) =>
    set((state) => ({
      pendingApprovals: [...state.pendingApprovals, approval],
    })),

  resolveApproval: (id) =>
    set((state) => ({
      pendingApprovals: state.pendingApprovals.filter((a) => a.id !== id),
    })),

  setConnected: (connected) => set({ isConnected: connected }),

  toggleTheme: () =>
    set((state) => ({
      theme: state.theme === "dark" ? "light" : "dark",
    })),

  setTheme: (theme) => set({ theme }),

  setNotifications: (notifications) =>
    set({
      notifications,
      unreadCount: notifications.filter((n) => !n.read).length,
    }),

  addNotification: (notification) =>
    set((state) => ({
      notifications: [notification, ...state.notifications],
      unreadCount: state.unreadCount + (notification.read ? 0 : 1),
    })),

  markAllNotificationsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),
}));
