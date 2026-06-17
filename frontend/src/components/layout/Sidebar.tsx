"use client";

import { useBrainStore, ViewType } from "@/lib/store";

const NAV_ITEMS: { id: ViewType; label: string; icon: string }[] = [
  { id: "playbook", label: "Playbook", icon: "P" },
  { id: "dashboard", label: "Dashboard", icon: "D" },
  { id: "chat", label: "Chat", icon: "C" },
  { id: "queue", label: "Queue", icon: "Q" },
  { id: "scheduler", label: "Scheduler", icon: "S" },
  { id: "history", label: "History", icon: "H" },
  { id: "logs", label: "Logs", icon: "L" },
  { id: "settings", label: "Settings", icon: "G" },
];

export default function Sidebar() {
  const { currentView, setView, sidebarCollapsed, toggleSidebar } = useBrainStore();

  return (
    <aside
      className={`${sidebarCollapsed ? "w-16" : "w-56"} h-screen border-r border-[var(--border)] bg-[var(--card)] flex flex-col transition-all duration-200`}
    >
      <div className="h-14 flex items-center justify-between px-4 border-b border-[var(--border)]">
        {!sidebarCollapsed && (
          <span className="text-sm font-bold text-[var(--primary)]">BRAIN</span>
        )}
        <button onClick={toggleSidebar} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] text-lg">
          {sidebarCollapsed ? ">" : "<"}
        </button>
      </div>

      <nav className="flex-1 py-2">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => setView(item.id)}
            className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
              currentView === item.id
                ? "bg-[var(--primary)]/10 text-[var(--primary)] border-r-2 border-[var(--primary)]"
                : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--muted)]/50"
            }`}
          >
            <span className="w-6 h-6 rounded flex items-center justify-center text-xs font-bold bg-[var(--muted)]">
              {item.icon}
            </span>
            {!sidebarCollapsed && <span>{item.label}</span>}
          </button>
        ))}
      </nav>

      <div className="p-4 border-t border-[var(--border)]">
        {!sidebarCollapsed && (
          <div className="text-xs text-[var(--muted-foreground)]">
            100% Local • Zero Cloud
          </div>
        )}
      </div>
    </aside>
  );
}
