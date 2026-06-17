"use client";

import { useState } from "react";
import { rerunPlaybook } from "@/lib/api";
import { AlertTriangle, RotateCcw, X, ChevronDown, ChevronRight } from "lucide-react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import { toast } from "sonner";

interface ErrorRetryPanelProps {
  playbookId: string;
  error: string;
  stepName?: string;
  agentRole?: string;
  details?: string;
  onDismiss: () => void;
}

export function ErrorRetryPanel({
  playbookId,
  error,
  stepName,
  agentRole,
  details,
  onDismiss,
}: ErrorRetryPanelProps) {
  const [isRetrying, setIsRetrying] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await rerunPlaybook(playbookId);
      toast.success("Playbook restarted");
      onDismiss();
    } catch {
      toast.error("Retry failed");
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="border-2 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10 rounded-xl p-4 space-y-3"
    >
      <div className="flex items-start gap-3">
        <div className="p-1.5 bg-red-100 dark:bg-red-900/30 rounded-lg flex-shrink-0">
          <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-sm text-red-800 dark:text-red-300">
            Execution Failed
          </h4>
          <p className="text-sm text-red-700 dark:text-red-400 mt-1">{error}</p>

          {(stepName || agentRole) && (
            <div className="flex gap-3 mt-2 text-xs">
              {stepName && (
                <span className="text-red-600 dark:text-red-400">
                  Step: <span className="font-medium">{stepName}</span>
                </span>
              )}
              {agentRole && (
                <span className="text-red-600 dark:text-red-400">
                  Agent: <span className="font-medium capitalize">{agentRole}</span>
                </span>
              )}
            </div>
          )}
        </div>
        <button onClick={onDismiss} className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 flex-shrink-0">
          <X className="w-4 h-4 text-red-400" />
        </button>
      </div>

      {/* Collapsible details */}
      {details && (
        <div>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline"
          >
            {showDetails ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            Error Details
          </button>
          {showDetails && (
            <pre className="mt-2 p-3 bg-red-100 dark:bg-red-900/20 rounded-lg text-xs font-mono text-red-800 dark:text-red-300 overflow-x-auto max-h-40">
              {details}
            </pre>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleRetry}
          disabled={isRetrying}
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
            "bg-red-600 hover:bg-red-700 text-white",
            isRetrying && "opacity-60 cursor-not-allowed"
          )}
        >
          <RotateCcw className={clsx("w-3.5 h-3.5", isRetrying && "animate-spin")} />
          {isRetrying ? "Retrying..." : "Retry"}
        </button>
        <button
          onClick={onDismiss}
          className="px-3 py-1.5 rounded-lg text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/20 transition-colors"
        >
          Dismiss
        </button>
      </div>
    </motion.div>
  );
}
