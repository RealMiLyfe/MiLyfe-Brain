"use client";

import { useEffect, useState } from "react";
import { queueApi } from "@/lib/api";

export default function QueueStatus() {
  const [queue, setQueue] = useState<any>({ running: null, waiting: [], completed: [] });

  useEffect(() => {
    const load = () => queueApi.status().then(setQueue).catch(() => {});
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="animate-fadeIn">
      <h2 className="text-xl font-bold mb-6">Execution Queue</h2>

      {/* Running */}
      <Section title="Running">
        {queue.running ? (
          <QueueCard item={queue.running} status="running" />
        ) : (
          <p className="text-sm text-[var(--muted-foreground)]">No playbook running</p>
        )}
      </Section>

      {/* Waiting */}
      <Section title={`Waiting (${queue.waiting?.length || 0})`}>
        {queue.waiting?.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">Queue empty</p>
        ) : (
          queue.waiting?.map((item: any, i: number) => (
            <QueueCard key={item.playbook_id} item={item} status="queued" position={i + 1} />
          ))
        )}
      </Section>

      {/* Completed */}
      <Section title={`Recently Completed (${queue.completed?.length || 0})`}>
        {queue.completed?.map((item: any) => (
          <QueueCard key={item.playbook_id} item={item} status={item.status} />
        ))}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <h3 className="text-sm font-medium text-[var(--muted-foreground)] mb-3">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function QueueCard({ item, status, position }: { item: any; status: string; position?: number }) {
  const statusColors: Record<string, string> = {
    running: "border-blue-500/50 bg-blue-500/5",
    queued: "border-[var(--border)]",
    completed: "border-green-500/30",
    failed: "border-red-500/30",
  };
  return (
    <div className={`p-3 border rounded-lg ${statusColors[status] || ""}`}>
      <div className="flex justify-between items-center">
        <div>
          {position && <span className="text-xs text-[var(--muted-foreground)] mr-2">#{position}</span>}
          <span className="text-sm font-medium">{item.title}</span>
        </div>
        <span className="text-xs text-[var(--muted-foreground)]">{status}</span>
      </div>
    </div>
  );
}
