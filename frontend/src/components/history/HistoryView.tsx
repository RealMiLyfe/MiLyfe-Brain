"use client";

import { useState, useEffect } from "react";
import { playbookApi } from "@/lib/api";
import { useStore, Playbook } from "@/lib/store";

const STATUS_BADGES: Record<string, { bg: string; text: string }> = {
  pending: { bg: "bg-[var(--muted)]", text: "text-[var(--muted-foreground)]" },
  running: { bg: "bg-[var(--primary)] bg-opacity-15", text: "text-[var(--primary)]" },
  completed: { bg: "bg-[var(--success)] bg-opacity-15", text: "text-[var(--success)]" },
  failed: { bg: "bg-[var(--destructive)] bg-opacity-15", text: "text-[var(--destructive)]" },
  cancelled: { bg: "bg-[var(--warning)] bg-opacity-15", text: "text-[var(--warning)]" },
};

export default function HistoryView() {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [loading, setLoading] = useState(true);
  const setCurrentPlaybook = useStore((s) => s.setCurrentPlaybook);
  const setView = useStore((s) => s.setView);

  useEffect(() => {
    async function load() {
      try {
        const list = await playbookApi.list();
        setPlaybooks(list);
      } catch {
        // Handle error silently
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function viewPlaybook(playbook: Playbook) {
    setCurrentPlaybook(playbook);
    setView("dashboard");
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-[var(--muted-foreground)]">Loading history...</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <h2 className="text-xl font-bold mb-4">Playbook History</h2>

      {playbooks.length === 0 ? (
        <div className="text-center py-12 text-[var(--muted-foreground)]">
          <p className="text-lg mb-1">No playbooks yet</p>
          <p className="text-sm">
            Create your first playbook to see it here.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {playbooks.map((pb) => {
            const badge = STATUS_BADGES[pb.status] || STATUS_BADGES.pending;
            return (
              <button
                key={pb.id}
                onClick={() => viewPlaybook(pb)}
                className="w-full text-left p-4 rounded-lg border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-sm">{pb.title}</h3>
                    <p className="text-xs text-[var(--muted-foreground)] mt-0.5">
                      {new Date(pb.created_at).toLocaleDateString()} &bull;{" "}
                      {pb.steps.length} steps
                    </p>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${badge.bg} ${badge.text}`}
                  >
                    {pb.status}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
