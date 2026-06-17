"use client";

import { useEffect } from "react";
import { useBrainStore } from "@/lib/store";
import { WebSocketClient } from "@/lib/api";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
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
import KeyboardShortcutsHelp from "@/components/KeyboardShortcutsHelp";

const ws = new WebSocketClient();

export default function Home() {
  const { currentView, setConnected, addEvent } = useBrainStore();

  // Global keyboard shortcuts
  useKeyboardShortcuts();

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
    <>
      {/* Skip navigation link (accessibility) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-[var(--primary)] focus:text-white focus:rounded-lg"
      >
        Skip to main content
      </a>

      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex flex-col overflow-hidden" role="main">
          {/* Header */}
          <header className="h-14 border-b border-[var(--border)] flex items-center justify-between px-6" role="banner">
            <h1 className="text-lg font-semibold text-[var(--foreground)]">
              MiLyfe Brain
            </h1>
            <div className="flex items-center gap-4">
              <kbd className="hidden md:inline-block px-1.5 py-0.5 text-[10px] bg-[var(--muted)] border border-[var(--border)] rounded text-[var(--muted-foreground)]">
                ? for shortcuts
              </kbd>
              <NotificationBell />
              <ConnectionIndicator />
            </div>
          </header>

          {/* Main content area */}
          <div
            id="main-content"
            className="flex-1 overflow-auto p-6 focus:outline-none"
            tabIndex={-1}
            role="region"
            aria-label={`${currentView} view`}
          >
            {renderView()}
          </div>
        </main>
      </div>

      {/* Keyboard shortcuts help modal */}
      <KeyboardShortcutsHelp />

      {/* Live region for screen reader announcements */}
      <div
        id="sr-announcements"
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      />
    </>
  );
}

function ConnectionIndicator() {
  const isConnected = useBrainStore((s) => s.isConnected);
  return (
    <div className="flex items-center gap-2 text-xs" role="status" aria-label={isConnected ? "Connected to server" : "Disconnected from server"}>
      <div
        className={`w-2 h-2 rounded-full transition-colors ${isConnected ? "bg-[var(--success)]" : "bg-[var(--destructive)]"}`}
        aria-hidden="true"
      />
      <span className="text-[var(--muted-foreground)]">{isConnected ? "Live" : "Offline"}</span>
    </div>
  );
}
