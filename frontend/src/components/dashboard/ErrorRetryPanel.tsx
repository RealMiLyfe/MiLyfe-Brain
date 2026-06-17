"use client";

import { useState } from "react";
import { playbookApi } from "@/lib/api";
import { useBrainStore } from "@/lib/store";

export default function ErrorRetryPanel() {
  const { currentPlaybook, setCurrentPlaybook, setView } = useBrainStore();
  const [retrying, setRetrying] = useState(false);

  if (!currentPlaybook || currentPlaybook.status !== "failed") return null;

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const result = await playbookApi.rerun(currentPlaybook.id) as any;
      setCurrentPlaybook(result);
      setView("dashboard");
    } catch {}
    setRetrying(false);
  };

  // Parse error for plain-English explanation
  const errorText = (currentPlaybook as any).error || "Unknown error";
  const explanation = getPlainEnglishError(errorText);

  return (
    <div className="bg-red-500/5 border border-red-500/30 rounded-lg p-4 animate-fadeIn">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center shrink-0">
          <span className="text-red-400 text-sm">!</span>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-red-400 text-sm">Playbook Failed</h3>
          <p className="text-sm text-[var(--foreground)] mt-1">{explanation}</p>
          <details className="mt-2">
            <summary className="text-xs text-[var(--muted-foreground)] cursor-pointer hover:text-[var(--foreground)]">
              Technical details
            </summary>
            <pre className="text-xs text-[var(--muted-foreground)] mt-1 p-2 bg-[var(--background)] rounded overflow-auto max-h-32">
              {errorText}
            </pre>
          </details>
        </div>
      </div>

      <div className="flex gap-2 mt-4">
        <button
          onClick={handleRetry}
          disabled={retrying}
          className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg text-sm hover:opacity-90 disabled:opacity-50"
        >
          {retrying ? "Retrying..." : "Retry from Failure"}
        </button>
        <button
          onClick={() => setView("playbook")}
          className="px-4 py-2 border border-[var(--border)] rounded-lg text-sm hover:bg-[var(--muted)]/30"
        >
          Edit & Resubmit
        </button>
      </div>
    </div>
  );
}

function getPlainEnglishError(error: string): string {
  const lower = error.toLowerCase();
  if (lower.includes("timeout") || lower.includes("timed out")) return "The task took too long and was stopped. Try breaking it into smaller steps.";
  if (lower.includes("connection") || lower.includes("connect")) return "Could not connect to the AI model. Check that Ollama is running.";
  if (lower.includes("model") && lower.includes("not found")) return "The requested AI model is not installed. Pull it with: ollama pull <model-name>";
  if (lower.includes("permission")) return "A required action was blocked by safety settings. Check Settings > Safety.";
  if (lower.includes("empty") || lower.includes("no response")) return "The AI model returned an empty response. It might be overloaded — try again.";
  if (lower.includes("memory") || lower.includes("oom")) return "Ran out of memory. Try a smaller model or close other applications.";
  return `Something went wrong: ${error.slice(0, 150)}`;
}
