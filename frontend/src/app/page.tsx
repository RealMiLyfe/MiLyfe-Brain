"use client";

import { useEffect } from "react";
import { useStore } from "@/lib/store";
import { wsClient } from "@/lib/api";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import Sidebar from "@/components/layout/Sidebar";
import PlaybookInput from "@/components/playbook/PlaybookInput";
import PlaybookEditor from "@/components/playbook/PlaybookEditor";
import Dashboard from "@/components/dashboard/Dashboard";
import ChatInterface from "@/components/chat/ChatInterface";
import QueueStatus from "@/components/queue/QueueStatus";
import SchedulerView from "@/components/scheduler/SchedulerView";
import HistoryView from "@/components/history/HistoryView";
import LogViewer from "@/components/logs/LogViewer";
import SettingsView from "@/components/settings/SettingsView";
import NotificationBell from "@/components/notifications/NotificationBell";
import ErrorBoundary from "@/components/ErrorBoundary";

export default function HomePage() {
  const currentView = useStore((s) => s.currentView);
  const isConnected = useStore((s) => s.isConnected);
  const setConnected = useStore((s) => s.setConnected);
  const addEvent = useStore((s) => s.addEvent);
  const addApproval = useStore((s) => s.addApproval);
  const addNotification = useStore((s) => s.addNotification);

  useKeyboardShortcuts();

  // WebSocket connection
  useEffect(() => {
    wsClient.connect();

    const unsubEvent = wsClient.onEvent((event) => {
      addEvent(event);

      // Handle special event types
      if (event.type === "approval_required" && event.data) {
        addApproval({
          id: event.id,
          action_type: (event.data.action_type as string) || "unknown",
          description: event.description,
          risk_level: event.risk_level || "medium",
          playbook_id: (event.data.playbook_id as string) || "",
          step_id: (event.data.step_id as string) || "",
        });
      }

      if (event.type === "notification" && event.data) {
        addNotification({
          id: event.id,
          title: (event.data.title as string) || "Notification",
          message: event.description,
          type: (event.data.notification_type as "info" | "success" | "warning" | "error") || "info",
          read: false,
          created_at: event.timestamp,
        });
      }
    });

    const unsubConnect = wsClient.onConnect(() => {
      setConnected(true);
    });

    const unsubDisconnect = wsClient.onDisconnect(() => {
      setConnected(false);
    });

    return () => {
      unsubEvent();
      unsubConnect();
      unsubDisconnect();
      wsClient.disconnect();
    };
  }, [setConnected, addEvent, addApproval, addNotification]);

  function renderView() {
    switch (currentView) {
      case "playbook":
        return (
          <div className="space-y-8">
            <PlaybookInput />
            <PlaybookEditor />
          </div>
        );
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
  }

  return (
    <>
      {/* Skip navigation link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:rounded-lg focus:bg-[var(--primary)] focus:text-white"
      >
        Skip to main content
      </a>

      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <Sidebar />

        {/* Main area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header
            className="flex items-center justify-between px-6 py-3 border-b border-[var(--border)] bg-[var(--card)]"
            role="banner"
          >
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-bold">MiLyfe Brain</h1>
              <div
                className="flex items-center gap-1.5"
                aria-label={
                  isConnected ? "Connected to server" : "Disconnected from server"
                }
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    isConnected
                      ? "bg-[var(--success)]"
                      : "bg-[var(--destructive)]"
                  } ${isConnected ? "animate-pulse-dot" : ""}`}
                />
                <span className="text-xs text-[var(--muted-foreground)]">
                  {isConnected ? "Connected" : "Disconnected"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <NotificationBell />
            </div>
          </header>

          {/* Content */}
          <main
            id="main-content"
            className="flex-1 overflow-y-auto p-6"
            role="main"
            aria-label={`${currentView} view`}
          >
            <ErrorBoundary>{renderView()}</ErrorBoundary>
          </main>
        </div>
      </div>
    </>
  );
}
