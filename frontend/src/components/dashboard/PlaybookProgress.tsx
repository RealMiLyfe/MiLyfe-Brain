"use client";

import { motion } from "framer-motion";
import { clsx } from "clsx";
import { CheckCircle, XCircle, Loader2, Clock, Zap } from "lucide-react";
import type { PlaybookStatus } from "@/lib/api";

interface PlaybookProgressProps {
  title: string;
  status: PlaybookStatus;
  progress: number;
  currentStep?: string;
  totalSteps: number;
  completedSteps: number;
  startedAt?: string;
}

const STATUS_CONFIG: Record<
  string,
  { icon: typeof Zap; color: string; label: string; bgColor: string }
> = {
  draft: { icon: Clock, color: "text-slate-500", label: "Draft", bgColor: "bg-slate-100 dark:bg-slate-800" },
  running: { icon: Loader2, color: "text-blue-500", label: "Running", bgColor: "bg-blue-50 dark:bg-blue-900/20" },
  paused: { icon: Clock, color: "text-amber-500", label: "Paused", bgColor: "bg-amber-50 dark:bg-amber-900/20" },
  completed: { icon: CheckCircle, color: "text-green-500", label: "Completed", bgColor: "bg-green-50 dark:bg-green-900/20" },
  failed: { icon: XCircle, color: "text-red-500", label: "Failed", bgColor: "bg-red-50 dark:bg-red-900/20" },
  cancelled: { icon: XCircle, color: "text-slate-500", label: "Cancelled", bgColor: "bg-slate-50 dark:bg-slate-800" },
};

export function PlaybookProgress({
  title,
  status,
  progress,
  currentStep,
  totalSteps,
  completedSteps,
  startedAt,
}: PlaybookProgressProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  const Icon = config.icon;
  const isRunning = status === "running";

  // Calculate elapsed time
  const elapsed = startedAt
    ? Math.round((Date.now() - new Date(startedAt).getTime()) / 1000)
    : 0;
  const elapsedStr = elapsed > 60
    ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
    : `${elapsed}s`;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx("rounded-xl border p-5", config.bgColor, "border-slate-200 dark:border-slate-700")}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center", config.bgColor)}>
            <Icon className={clsx("w-5 h-5", config.color, isRunning && "animate-spin")} />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-100">
              {title}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {completedSteps}/{totalSteps} steps {config.label.toLowerCase()}
            </p>
          </div>
        </div>
        <div className="text-right">
          <span className={clsx("text-xs px-2.5 py-1 rounded-full font-medium", config.color, config.bgColor)}>
            {config.label}
          </span>
          {startedAt && (
            <p className="text-[10px] text-slate-400 mt-1">{elapsedStr}</p>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="relative w-full h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <motion.div
          className={clsx(
            "absolute top-0 left-0 h-full rounded-full",
            status === "completed" && "bg-green-500",
            status === "running" && "bg-gradient-to-r from-blue-500 to-primary-500",
            status === "failed" && "bg-red-400",
            status === "paused" && "bg-amber-400",
            !["completed", "running", "failed", "paused"].includes(status) && "bg-slate-400"
          )}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
        {isRunning && (
          <motion.div
            className="absolute top-0 left-0 h-full w-full bg-gradient-to-r from-transparent via-white/20 to-transparent"
            animate={{ x: ["0%", "100%"] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
          />
        )}
      </div>

      {/* Current step */}
      {currentStep && (
        <div className="mt-3 flex items-center gap-2">
          {isRunning && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
            </span>
          )}
          <span className="text-xs text-slate-600 dark:text-slate-300">
            {currentStep}
          </span>
        </div>
      )}

      {/* Progress percentage */}
      <div className="flex justify-end mt-2">
        <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
          {progress}%
        </span>
      </div>
    </motion.div>
  );
}
