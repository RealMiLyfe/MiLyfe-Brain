"use client";

import { useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { PlaybookInput } from "@/components/playbook/PlaybookInput";
import { PlaybookEditor } from "@/components/playbook/PlaybookEditor";
import { Dashboard } from "@/components/dashboard/Dashboard";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { QueueStatus } from "@/components/queue/QueueStatus";
import { SchedulerView } from "@/components/scheduler/SchedulerView";
import { HistoryView } from "@/components/history/HistoryView";
import { LogViewer } from "@/components/logs/LogViewer";
import { SettingsView } from "@/components/settings/SettingsView";

type View = "playbook" | "editor" | "dashboard" | "chat" | "queue" | "scheduler" | "history" | "logs" | "settings";

export default function Home() {
  const [activeView, setActiveView] = useState<View>("playbook");

  const renderView = () => {
    switch (activeView) {
      case "playbook": return <PlaybookInput onSubmit={() => setActiveView("dashboard")} />;
      case "editor": return <PlaybookEditor />;
      case "dashboard": return <Dashboard />;
      case "chat": return <ChatInterface />;
      case "queue": return <QueueStatus />;
      case "scheduler": return <SchedulerView />;
      case "history": return <HistoryView />;
      case "logs": return <LogViewer />;
      case "settings": return <SettingsView />;
      default: return <PlaybookInput onSubmit={() => setActiveView("dashboard")} />;
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar activeView={activeView} onNavigate={(view) => setActiveView(view as View)} />
      <main className="flex-1 overflow-auto">
        {renderView()}
      </main>
    </div>
  );
}
