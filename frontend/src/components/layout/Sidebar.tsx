"use client";

import { BookOpen, LayoutDashboard, MessageSquare, ListOrdered, Calendar, History, FileText, Settings, Pencil, Brain } from "lucide-react";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { NotificationBell } from "@/components/notifications/NotificationBell";

const NAV_ITEMS = [
  { id: "playbook", label: "Playbook", icon: BookOpen },
  { id: "editor", label: "Editor", icon: Pencil },
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "queue", label: "Queue", icon: ListOrdered },
  { id: "scheduler", label: "Scheduler", icon: Calendar },
  { id: "history", label: "History", icon: History },
  { id: "logs", label: "Logs", icon: FileText },
  { id: "settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  activeView: string;
  onNavigate: (view: string) => void;
}

export function Sidebar({ activeView, onNavigate }: SidebarProps) {
  return (
    <aside className="w-64 h-screen bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-gray-800 flex items-center gap-2">
        <Brain className="w-7 h-7 text-brain-500" />
        <h1 className="text-lg font-bold text-white">MiLyfe Brain</h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                isActive
                  ? "bg-brain-600/20 text-brain-400 font-medium"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              <Icon className="w-4 h-4" />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-gray-800 flex items-center justify-between">
        <NotificationBell />
        <ThemeToggle />
        <div className="w-2 h-2 rounded-full bg-green-400" title="Connected" />
      </div>
    </aside>
  );
}
