"use client";

import { useStore } from "@/lib/store";
import { usePlaybookStatus } from "@/hooks/usePlaybookStatus";
import TaskGraph from "./TaskGraph";
import ApprovalDialog from "./ApprovalDialog";
import ErrorRetryPanel from "./ErrorRetryPanel";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-[var(--muted-foreground)]",
  running: "bg-[var(--primary)]",
  completed: "bg-[var(--success)]",
  failed: "bg-[var(--destructive)]",
  cancelled: "bg-[var(--warning)]",
};

export default function Dashboard() {
  const currentPlaybook = useStore((s) => s.currentPlaybook);
  const events = useStore((s) => s.events);
  const pendingApprovals = useStore((s) => s.pendingApprovals);
  const { status } = usePlaybookStatus(currentPlaybook?.id || null);

  if (!currentPlaybook) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--muted-foreground)]">
        <div className="text-center">
          <p className="text-lg mb-2">No active playbook</p>
          <p className="text-sm">
            Create a playbook to see the execution dashboard.
          </p>
        </div>
      </div>
    );
  }

  const progress = status?.progress ?? 0;
  const stepsCompleted = status?.steps_completed ?? 0;
  const stepsRunning = status?.steps_running ?? 0;
  const stepsFailed = status?.steps_failed ?? 0;
  const stepsTotal = status?.steps_total ?? currentPlaybook.steps.length;
  const playbookStatus = status?.status ?? currentPlaybook.status;

  const recentEvents = events.slice(0, 50);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">{currentPlaybook.title}</h2>
          <p className="text-sm text-[var(--muted-foreground)]">
            ID: {currentPlaybook.id}
          </p>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-xs font-medium text-white ${
            STATUS_COLORS[playbookStatus] || STATUS_COLORS.pending
          }`}
        >
          {playbookStatus}
        </span>
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-sm mb-1">
          <span className="text-[var(--muted-foreground)]">Progress</span>
          <span className="font-medium">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 rounded-full bg-[var(--muted)] overflow-hidden">
          <div
            className="h-full rounded-full bg-[var(--primary)] transition-all duration-500"
            style={{ width: `${progress}%` }}
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      {/* Step counts */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-2xl font-bold">{stepsTotal}</p>
          <p className="text-xs text-[var(--muted-foreground)]">Total</p>
        </div>
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-2xl font-bold text-[var(--success)]">
            {stepsCompleted}
          </p>
          <p className="text-xs text-[var(--muted-foreground)]">Completed</p>
        </div>
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-2xl font-bold text-[var(--primary)]">
            {stepsRunning}
          </p>
          <p className="text-xs text-[var(--muted-foreground)]">Running</p>
        </div>
        <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
          <p className="text-2xl font-bold text-[var(--destructive)]">
            {stepsFailed}
          </p>
          <p className="text-xs text-[var(--muted-foreground)]">Failed</p>
        </div>
      </div>

      {/* Task Graph */}
      <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
        <h3 className="text-sm font-medium mb-3">Task Graph</h3>
        <TaskGraph playbookId={currentPlaybook.id} />
      </div>

      {/* Error panel */}
      {playbookStatus === "failed" && (
        <ErrorRetryPanel
          playbookId={currentPlaybook.id}
          error={status?.error || currentPlaybook.error}
        />
      )}

      {/* Approval dialog */}
      {pendingApprovals.length > 0 && (
        <ApprovalDialog approval={pendingApprovals[0]} />
      )}

      {/* Live event stream */}
      <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
        <h3 className="text-sm font-medium mb-3">
          Live Events{" "}
          <span className="text-[var(--muted-foreground)]">
            ({recentEvents.length})
          </span>
        </h3>
        <div className="max-h-64 overflow-y-auto space-y-1">
          {recentEvents.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)] py-4 text-center">
              Waiting for events...
            </p>
          ) : (
            recentEvents.map((event) => (
              <div
                key={event.id}
                className="flex items-start gap-2 py-1.5 px-2 rounded text-xs hover:bg-[var(--muted)] transition-colors animate-slide-up"
              >
                <span className="text-[var(--muted-foreground)] whitespace-nowrap">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
                {event.role && (
                  <span className="px-1.5 py-0.5 rounded bg-[var(--primary)] bg-opacity-20 text-[var(--primary)] font-medium">
                    {event.role}
                  </span>
                )}
                <span className="text-[var(--foreground)] flex-1">
                  {event.description}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
