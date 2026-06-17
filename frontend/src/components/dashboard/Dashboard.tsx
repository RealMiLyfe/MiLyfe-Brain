"use client";

import { useEffect, useState } from "react";
import { playbookApi } from "@/lib/api";
import { useBrainStore } from "@/lib/store";

export default function Dashboard() {
  const { currentPlaybook, events } = useBrainStore();
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    if (!currentPlaybook) return;
    const poll = setInterval(async () => {
      try {
        const s = await playbookApi.getStatus(currentPlaybook.id);
        setStatus(s);
      } catch {}
    }, 2000);
    return () => clearInterval(poll);
  }, [currentPlaybook]);

  if (!currentPlaybook) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--muted-foreground)]">
        No active playbook. Create one from the Playbook view.
      </div>
    );
  }

  const progress = status?.progress || 0;
  const pbEvents = events.filter((e) => e.playbook_id === currentPlaybook.id);

  return (
    <div className="animate-fadeIn space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">{currentPlaybook.title}</h2>
          <p className="text-sm text-[var(--muted-foreground)]">{currentPlaybook.description.slice(0, 100)}</p>
        </div>
        <StatusBadge status={status?.status || currentPlaybook.status} />
      </div>

      {/* Progress */}
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-lg p-4">
        <div className="flex justify-between text-sm mb-2">
          <span>Progress</span>
          <span>{Math.round(progress * 100)}%</span>
        </div>
        <div className="h-3 bg-[var(--muted)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[var(--primary)] rounded-full transition-all duration-500"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
        {status && (
          <div className="flex gap-4 mt-3 text-xs text-[var(--muted-foreground)]">
            <span>Steps: {status.completed_steps}/{status.total_steps}</span>
            {status.running_steps > 0 && <span className="text-blue-400">Running: {status.running_steps}</span>}
            {status.failed_steps > 0 && <span className="text-red-400">Failed: {status.failed_steps}</span>}
          </div>
        )}
      </div>

      {/* Event Log */}
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-lg">
        <div className="p-3 border-b border-[var(--border)]">
          <h3 className="text-sm font-medium">Live Event Stream</h3>
        </div>
        <div className="max-h-96 overflow-auto p-3 space-y-2">
          {pbEvents.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">Waiting for events...</p>
          ) : (
            pbEvents.slice(-50).map((event, i) => (
              <div key={i} className="flex gap-2 text-xs animate-slideUp">
                <span className="text-[var(--muted-foreground)] w-16 shrink-0">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
                {event.agent_role && (
                  <span className="px-1.5 py-0.5 rounded bg-[var(--muted)] text-[var(--muted-foreground)]">
                    {event.agent_role}
                  </span>
                )}
                <span className="text-[var(--foreground)]">
                  {event.event_type}: {JSON.stringify(event.data).slice(0, 100)}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-gray-500/20 text-gray-400",
    running: "bg-blue-500/20 text-blue-400",
    completed: "bg-green-500/20 text-green-400",
    failed: "bg-red-500/20 text-red-400",
  };
  return (
    <span className={`px-3 py-1 rounded-full text-xs font-medium ${colors[status] || colors.queued}`}>
      {status}
    </span>
  );
}
