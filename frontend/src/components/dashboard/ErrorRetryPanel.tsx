"use client";

import { useState } from "react";
import { playbookApi } from "@/lib/api";
import { useStore } from "@/lib/store";

interface ErrorRetryPanelProps {
  playbookId: string;
  error?: string;
}

export default function ErrorRetryPanel({
  playbookId,
  error,
}: ErrorRetryPanelProps) {
  const setCurrentPlaybook = useStore((s) => s.setCurrentPlaybook);
  const setView = useStore((s) => s.setView);
  const [retrying, setRetrying] = useState(false);

  function getPlainEnglishError(raw?: string): string {
    if (!raw) return "An unexpected error occurred during playbook execution.";
    if (raw.includes("timeout"))
      return "The operation timed out. This usually means a step took longer than expected.";
    if (raw.includes("connection"))
      return "A connection issue prevented completion. Check that local services are running.";
    if (raw.includes("permission"))
      return "A permission error occurred. The agent may not have access to the required resource.";
    if (raw.includes("model") || raw.includes("ollama"))
      return "The AI model failed to respond. Ensure your local model server is running.";
    return `An error occurred: ${raw}`;
  }

  async function handleRetry() {
    setRetrying(true);
    try {
      const playbook = await playbookApi.rerun(playbookId);
      setCurrentPlaybook(playbook);
    } catch {
      // Error will be shown in dashboard
    } finally {
      setRetrying(false);
    }
  }

  function handleEditAndResubmit() {
    setView("playbook");
  }

  return (
    <div
      role="alert"
      className="p-5 rounded-lg border border-[var(--destructive)] border-opacity-40 bg-[var(--destructive)] bg-opacity-5 animate-slide-up"
    >
      <div className="flex items-start gap-3">
        <span className="text-[var(--destructive)] text-xl">✕</span>
        <div className="flex-1">
          <h4 className="font-semibold text-[var(--destructive)] mb-1">
            Playbook Failed
          </h4>
          <p className="text-sm text-[var(--foreground)] mb-4">
            {getPlainEnglishError(error)}
          </p>

          {error && (
            <details className="mb-4">
              <summary className="text-xs text-[var(--muted-foreground)] cursor-pointer hover:text-[var(--foreground)]">
                Technical details
              </summary>
              <pre className="mt-2 p-3 rounded bg-[var(--muted)] text-xs text-[var(--muted-foreground)] overflow-auto max-h-32">
                {error}
              </pre>
            </details>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="px-4 py-2 rounded-lg bg-[var(--primary)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {retrying ? "Retrying..." : "Retry"}
            </button>
            <button
              onClick={handleEditAndResubmit}
              className="px-4 py-2 rounded-lg border border-[var(--border)] text-sm font-medium text-[var(--foreground)] hover:bg-[var(--muted)] transition-colors"
            >
              Edit & Resubmit
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
