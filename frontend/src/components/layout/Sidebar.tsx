"use client";

import { useStore, type ViewType } from "@/lib/store";
import {
  Brain,
  MessageSquare,
  LayoutDashboard,
  Code,
  Clock,
  Calendar,
  History,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { clsx } from "clsx";
import { motion } from "framer-motion";

interface NavItem {
  id: ViewType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

const navItems: NavItem[] = [
  { id: "playbook", label: "Playbook", icon: Brain },
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "editor", label: "Editor", icon: Code },
  { id: "queue", label: "Queue", icon: Clock },
  { id: "scheduler", label: "Scheduler", icon: Calendar },
  { id: "history", label: "History", icon: History },
  { id: "logs", label: "Logs", icon: FileText },
  { id: "settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const activeView = useStore((state) => state.activeView);
  const setActiveView = useStore((state) => state.setActiveView);
  const collapsed = useStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useStore((state) => state.toggleSidebar);

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 64 : 220 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="h-screen flex flex-col border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50"
    >
      {/* Logo area */}
      <div className="h-14 flex items-center justify-center border-b border-slate-200 dark:border-slate-700 px-3">
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-sm text-slate-800 dark:text-slate-100">
              MiLyfe Brain
            </span>
          </motion.div>
        )}
        {collapsed && (
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto scrollbar-thin">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              className={clsx(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                isActive
                  ? "bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 hover:text-slate-800 dark:hover:text-slate-200"
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon
                className={clsx(
                  "w-5 h-5 flex-shrink-0",
                  isActive
                    ? "text-primary-600 dark:text-primary-400"
                    : "text-slate-500 dark:text-slate-400"
                )}
              />
              {!collapsed && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.05 }}
                >
                  {item.label}
                </motion.span>
              )}
              {!collapsed && item.badge && item.badge > 0 && (
                <span className="ml-auto text-xs px-1.5 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 font-medium">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <div className="p-2 border-t border-slate-200 dark:border-slate-700">
        <button
          onClick={toggleSidebar}
          className="w-full flex items-center justify-center p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>
    </motion.aside>
  );
}
