"use client";

import { useState, useEffect } from "react";
import { queueApi, QueueStatusResponse } from "@/lib/api";

export default function QueueStatus() {
  const [queue, setQueue] = useState<QueueStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const data = await queueApi.status();
        if (!cancelled) setQueue(data);
      } catch {
        // Silently handle
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    poll();
    const interval = setInterval(poll, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--muted-foreground)]">
        Loading queue status...
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <h2 className="text-xl font-bold mb-6">Queue</h2>

      {/* Running */}
      <section className="mb-6">
        <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wide mb-2">
          Currently Running
        </h3>
        {queue?.running ? (
          <div className="p-4 rounded-lg border border-[var(--primary)] border-opacity-40 bg-[var(--primary)] bg-opacity-5">
            <div className="flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse-dot" />
              <div>
                <p className="text-sm font-medium">{queue.running.title}</p>
                <p className="text-xs text-[var(--muted-foreground)]">
                  Started{" "}
                  {new Date(queue.running.started_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm text-[var(--muted-foreground)]">
            No playbook currently running
          </div>
        )}
      </section>

      {/* Waiting */}
      <section className="mb-6">
        <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wide mb-2">
          Waiting ({queue?.waiting.length || 0})
        </h3>
        {queue?.waiting && queue.waiting.length > 0 ? (
          <div className="space-y-2">
            {queue.waiting.map((item, idx) => (
              <div
                key={item.id}
                className="p-3 rounded-lg border border-[var(--border)] bg-[var(--card)] flex items-center gap-3"
              >
                <span className="text-xs font-mono text-[var(--muted-foreground)] w-6">
                  #{idx + 1}
                </span>
                <div>
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Queued{" "}
                    {new Date(item.queued_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm text-[var(--muted-foreground)]">
            Queue is empty
          </div>
        )}
      </section>

      {/* Completed */}
      <section>
        <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wide mb-2">
          Recently Completed ({queue?.completed.length || 0})
        </h3>
        {queue?.completed && queue.completed.length > 0 ? (
          <div className="space-y-2">
            {queue.completed.map((item) => (
              <div
                key={item.id}
                className="p-3 rounded-lg border border-[var(--border)] bg-[var(--card)] flex items-center justify-between"
              >
                <div>
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Completed{" "}
                    {new Date(item.completed_at).toLocaleTimeString()}
                  </p>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                    item.status === "completed"
                      ? "bg-[var(--success)] bg-opacity-15 text-[var(--success)]"
                      : "bg-[var(--destructive)] bg-opacity-15 text-[var(--destructive)]"
                  }`}
                >
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm text-[var(--muted-foreground)]">
            No completed items
          </div>
        )}
      </section>
    </div>
  );
}
