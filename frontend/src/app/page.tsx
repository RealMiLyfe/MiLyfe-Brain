"use client";

import { useEffect } from "react";
import { useBrainStore } from "@/lib/store";
import { WebSocketClient } from "@/lib/api";
import Sidebar from "@/components/layout/Sidebar";
import PlaybookInput from "@/components/playbook/PlaybookInput";
import Dashboard from "@/components/dashboard/Dashboard";
import ChatInterface from "@/components/chat/ChatInterface";
import HistoryView from "@/components/history/HistoryView";
import LogViewer from "@/components/logs/LogViewer";
import SettingsView from "@/components/settings/SettingsView";
import QueueStatus from "@/components/queue/QueueStatus";
import SchedulerView from "@/components/scheduler/SchedulerView";
import NotificationBell from "@/components/notifications/NotificationBell";

const ws = new WebSocketClient();

export default function Home() {
  const { currentView, setConnected, addEvent } = useBrainStore();

  useEffect(() => {
    ws.onConnect = () => setConnected(true);
    ws.onDisconnect = () => setConnected(false);
    ws.onEvent = (event) => addEvent(event);
    ws.connect();
    return () => ws.disconnect();
  }, []);

  const renderView = () => {
    switch (currentView) {
      case "playbook":
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
        return <PlaybookInput />;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 border-b border-[var(--border)] flex items-center justify-between px-6">
          <h1 className="text-lg font-semibold text-[var(--foreground)]">
            MiLyfe Brain
          </h1>
          <div className="flex items-center gap-4">
            <NotificationBell />
            <ConnectionIndicator />
          </div>
        </header>
        <div className="flex-1 overflow-auto p-6">
          {renderView()}
        </div>
      </main>
    </div>
  );
}

function ConnectionIndicator() {
  const isConnected = useBrainStore((s) => s.isConnected);
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-[var(--success)]" : "bg-[var(--destructive)]"}`} />
      <span className="text-[var(--muted-foreground)]">{isConnected ? "Live" : "Disconnected"}</span>
    </div>
  );
}
