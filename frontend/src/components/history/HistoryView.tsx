"use client";

import { useEffect, useState } from "react";
import { playbookApi } from "@/lib/api";
import { useBrainStore } from "@/lib/store";

export default function HistoryView() {
  const [playbooks, setPlaybooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { setCurrentPlaybook, setView } = useBrainStore();

  useEffect(() => {
    playbookApi.list().then((data) => { setPlaybooks(data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const viewPlaybook = (pb: any) => {
    setCurrentPlaybook(pb);
    setView("dashboard");
  };

  if (loading) return <div className="text-[var(--muted-foreground)]">Loading...</div>;

  return (
    <div className="animate-fadeIn">
      <h2 className="text-xl font-bold mb-4">Playbook History</h2>
      {playbooks.length === 0 ? (
        <p className="text-[var(--muted-foreground)]">No playbooks yet.</p>
      ) : (
        <div className="space-y-3">
          {playbooks.map((pb) => (
            <div
              key={pb.id}
              className="bg-[var(--card)] border border-[var(--border)] rounded-lg p-4 hover:border-[var(--primary)]/50 cursor-pointer transition-colors"
              onClick={() => viewPlaybook(pb)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">{pb.title}</h3>
                  <p className="text-xs text-[var(--muted-foreground)] mt-1">{pb.description?.slice(0, 80)}</p>
                </div>
                <div className="text-right">
                  <StatusBadge status={pb.status} />
                  <p className="text-xs text-[var(--muted-foreground)] mt-1">
                    {new Date(pb.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "text-gray-400", running: "text-blue-400", completed: "text-green-400", failed: "text-red-400",
  };
  return <span className={`text-xs font-medium ${colors[status] || "text-gray-400"}`}>{status}</span>;
}
