"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { PlaybookInput } from "@/components/playbook/PlaybookInput";
import { Dashboard } from "@/components/dashboard/Dashboard";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { SettingsView } from "@/components/settings/SettingsView";
import { HistoryView } from "@/components/history/HistoryView";
import { LogViewer } from "@/components/logs/LogViewer";
import { QueueStatus } from "@/components/queue/QueueStatus";
import { SchedulerView } from "@/components/scheduler/SchedulerView";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { useStore } from "@/lib/store";
import { Brain } from "lucide-react";

export default function Home() {
  const activeView = useStore((state) => state.activeView);

  const renderContent = () => {
    switch (activeView) {
      case "playbook":
        return <PlaybookInput />;
      case "editor":
        return <PlaybookInput />;
      case "dashboard":
        return <Dashboard />;
      case "chat":
        return <ChatInterface />;
      case "queue":
        return <QueueStatus />;
      case "scheduler":
        return <SchedulerView />;
      case "history":
        return <HistoryView />;
      case "logs":
        return <LogViewer />;
      case "settings":
        return <SettingsView />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-surface-900">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 flex items-center justify-between px-6 border-b border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <Brain className="w-6 h-6 text-primary-500" />
            <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
              MiLyfe Brain
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 font-medium">
              v0.1
            </span>
          </div>
          <div className="flex items-center gap-3">
            <NotificationBell />
            <ThemeToggle />
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto p-6 scrollbar-thin">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}
