"use client";

import { useState } from "react";
import { AlertTriangle, RotateCcw, X, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { playbookApi } from "@/lib/api";

interface ErrorInfo {
  stepId: string;
  stepDescription: string;
  agentRole: string;
  error: string;
  playbookId: string;
}

interface Props {
  errors: ErrorInfo[];
  onDismiss?: (stepId: string) => void;
}

export function ErrorRetryPanel({ errors, onDismiss }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<Set<string>>(new Set());

  if (errors.length === 0) return null;

  const handleRetry = async (error: ErrorInfo) => {
    setRetrying((prev) => new Set(prev).add(error.stepId));
    try {
      await playbookApi.rerun(error.playbookId);
    } catch (e) {
      console.error("Retry failed:", e);
    } finally {
      setRetrying((prev) => {
        const next = new Set(prev);
        next.delete(error.stepId);
        return next;
      });
    }
  };

  return (
    <div className="bg-red-950/30 border border-red-500/30 rounded-xl overflow-hidden">
      <div className="px-4 py-3 flex items-center gap-2 border-b border-red-500/20">
        <AlertTriangle className="w-4 h-4 text-red-400" />
        <span className="text-sm font-medium text-red-300">
          {errors.length} Error{errors.length > 1 ? "s" : ""} Encountered
        </span>
      </div>

      <AnimatePresence>
        {errors.map((error) => (
          <motion.div
            key={error.stepId}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="border-b border-red-500/10 last:border-b-0"
          >
            {/* Error Header */}
            <div
              className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-red-500/5"
              onClick={() => setExpandedId(expandedId === error.stepId ? null : error.stepId)}
            >
              <div className="w-2 h-2 bg-red-400 rounded-full shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white truncate">{error.stepDescription}</p>
                <p className="text-xs text-gray-500 capitalize">{error.agentRole}</p>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-gray-500 transition-transform ${
                  expandedId === error.stepId ? "rotate-180" : ""
                }`}
              />
            </div>

            {/* Expanded Error Details */}
            {expandedId === error.stepId && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="px-4 pb-3 space-y-2"
              >
                <pre className="bg-gray-900 rounded-lg p-3 text-xs text-red-300 overflow-x-auto max-h-32">
                  {error.error}
                </pre>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleRetry(error)}
                    disabled={retrying.has(error.stepId)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg disabled:opacity-50 transition-colors"
                  >
                    <RotateCcw className={`w-3 h-3 ${retrying.has(error.stepId) ? "animate-spin" : ""}`} />
                    {retrying.has(error.stepId) ? "Retrying..." : "Retry Playbook"}
                  </button>
                  {onDismiss && (
                    <button
                      onClick={() => onDismiss(error.stepId)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs rounded-lg transition-colors"
                    >
                      <X className="w-3 h-3" /> Dismiss
                    </button>
                  )}
                </div>
              </motion.div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
