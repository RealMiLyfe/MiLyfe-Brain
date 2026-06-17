"use client";

import { useStore, ViewType } from "@/lib/store";

interface NavItem {
  id: ViewType;
  label: string;
  icon: string;
  shortcut: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "playbook", label: "Playbook", icon: "P", shortcut: "⌘1" },
  { id: "dashboard", label: "Dashboard", icon: "D", shortcut: "⌘2" },
  { id: "chat", label: "Chat", icon: "C", shortcut: "⌘3" },
  { id: "queue", label: "Queue", icon: "Q", shortcut: "⌘4" },
  { id: "scheduler", label: "Scheduler", icon: "S", shortcut: "⌘5" },
  { id: "history", label: "History", icon: "H", shortcut: "⌘6" },
  { id: "logs", label: "Logs", icon: "L", shortcut: "⌘7" },
  { id: "settings", label: "Settings", icon: "G", shortcut: "⌘8" },
];

export default function Sidebar() {
  const currentView = useStore((s) => s.currentView);
  const setView = useStore((s) => s.setView);
  const sidebarCollapsed = useStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useStore((s) => s.toggleSidebar);

  return (
    <aside
      role="navigation"
      aria-label="Main navigation"
      className={`flex flex-col h-full bg-[var(--card)] border-r border-[var(--border)] transition-all duration-200 ${
        sidebarCollapsed ? "w-16" : "w-56"
      }`}
    >
      {/* Collapse toggle */}
      <div className="flex items-center justify-between p-3 border-b border-[var(--border)]">
        {!sidebarCollapsed && (
          <span className="text-sm font-semibold text-[var(--primary)]">
            MiLyfe
          </span>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded hover:bg-[var(--muted)] transition-colors"
          aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          title="Toggle sidebar (⌘/)"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            className="text-[var(--muted-foreground)]"
          >
            <path
              d={sidebarCollapsed ? "M6 3l5 5-5 5" : "M10 3l-5 5 5 5"}
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>

      {/* Navigation items */}
      <nav className="flex-1 py-2 space-y-1 px-2">
        {NAV_ITEMS.map((item) => {
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? "bg-[var(--primary)] bg-opacity-15 text-[var(--primary)]"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
              }`}
              aria-current={isActive ? "page" : undefined}
              title={`${item.label} (${item.shortcut})`}
            >
              <span
                className={`flex items-center justify-center w-7 h-7 rounded text-xs font-bold ${
                  isActive
                    ? "bg-[var(--primary)] text-white"
                    : "bg-[var(--muted)] text-[var(--muted-foreground)]"
                }`}
              >
                {item.icon}
              </span>
              {!sidebarCollapsed && <span>{item.label}</span>}
              {!sidebarCollapsed && (
                <span className="ml-auto text-xs text-[var(--muted-foreground)] opacity-60">
                  {item.shortcut}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-[var(--border)]">
        {!sidebarCollapsed && (
          <p className="text-[10px] text-[var(--muted-foreground)] text-center leading-tight">
            100% Local &bull; Zero Cloud
          </p>
        )}
      </div>
    </aside>
  );
}
