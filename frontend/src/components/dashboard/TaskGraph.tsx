"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import type { PlaybookStep } from "@/lib/api";

interface TaskGraphProps {
  steps: PlaybookStep[];
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-slate-200 dark:bg-slate-600 border-slate-300 dark:border-slate-500",
  running: "bg-blue-100 dark:bg-blue-900/40 border-blue-400 dark:border-blue-500 ring-2 ring-blue-300 dark:ring-blue-700",
  completed: "bg-green-100 dark:bg-green-900/40 border-green-400 dark:border-green-500",
  failed: "bg-red-100 dark:bg-red-900/40 border-red-400 dark:border-red-500",
  skipped: "bg-slate-100 dark:bg-slate-700 border-slate-300 dark:border-slate-500 opacity-60",
};

const STATUS_DOT: Record<string, string> = {
  pending: "bg-slate-400",
  running: "bg-blue-500 animate-pulse",
  completed: "bg-green-500",
  failed: "bg-red-500",
  skipped: "bg-slate-400",
};

const ROLE_ICONS: Record<string, string> = {
  orchestrator: "O",
  researcher: "R",
  coder: "C",
  executor: "E",
  critic: "Cr",
  designer: "D",
  writer: "W",
  debugger: "Db",
  planner: "P",
};

export function TaskGraph({ steps }: TaskGraphProps) {
  if (!steps || steps.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-slate-400 dark:text-slate-500">
        No steps to visualize
      </div>
    );
  }

  // Calculate layout (simple linear/layered)
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const totalCount = steps.length;
  const percentage = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>
          {completedCount}/{totalCount} steps complete
        </span>
        <span>{percentage}%</span>
      </div>
      <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-primary-500 to-green-400 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      {/* Step graph (vertical pipeline view) */}
      <div className="relative space-y-0">
        {steps.map((step, idx) => (
          <div key={step.id} className="relative">
            {/* Connector line */}
            {idx < steps.length - 1 && (
              <div className="absolute left-[19px] top-[38px] bottom-0 w-0.5 bg-slate-200 dark:bg-slate-700 z-0" />
            )}

            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={clsx(
                "relative z-10 flex items-start gap-3 p-3 rounded-lg border transition-all",
                STATUS_COLORS[step.status] || STATUS_COLORS.pending
              )}
            >
              {/* Status circle */}
              <div className="flex-shrink-0 w-[22px] h-[22px] rounded-full border-2 border-white dark:border-slate-800 flex items-center justify-center bg-white dark:bg-slate-800 shadow-sm">
                <div className={clsx("w-3 h-3 rounded-full", STATUS_DOT[step.status] || STATUS_DOT.pending)} />
              </div>

              {/* Step content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-700 dark:text-slate-200 truncate">
                    {step.name}
                  </span>
                  {step.agent_role && (
                    <span className="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 font-mono">
                      {ROLE_ICONS[step.agent_role] || step.agent_role}
                    </span>
                  )}
                </div>
                {step.output && step.status === "completed" && (
                  <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2">
                    {step.output.slice(0, 120)}
                    {step.output.length > 120 ? "..." : ""}
                  </p>
                )}
              </div>

              {/* Timing */}
              {step.started_at && step.completed_at && (
                <span className="flex-shrink-0 text-[10px] text-slate-400 dark:text-slate-500">
                  {Math.round(
                    (new Date(step.completed_at).getTime() - new Date(step.started_at).getTime()) / 1000
                  )}s
                </span>
              )}
            </motion.div>
          </div>
        ))}
      </div>
    </div>
  );
}
