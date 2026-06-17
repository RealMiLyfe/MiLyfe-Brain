"use client";

import { motion } from "framer-motion";
import { clsx } from "clsx";

interface PlaybookProgressProps {
  progress: number;
  status: "running" | "completed" | "failed" | "paused" | "pending";
  title: string;
  stepsCompleted: number;
  stepsTotal: number;
}

export function PlaybookProgress({ progress, status, title, stepsCompleted, stepsTotal }: PlaybookProgressProps) {
  const gradientMap = {
    running: "from-blue-500 to-cyan-400",
    completed: "from-green-500 to-emerald-400",
    failed: "from-red-500 to-rose-400",
    paused: "from-amber-500 to-yellow-400",
    pending: "from-slate-400 to-slate-300",
  };

  const badgeMap = {
    running: "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400",
    completed: "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400",
    failed: "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400",
    paused: "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400",
    pending: "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card space-y-3"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200 truncate">
          {title}
        </h3>
        <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium capitalize", badgeMap[status])}>
          {status}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <motion.div
          className={clsx("h-full rounded-full bg-gradient-to-r", gradientMap[status])}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(progress, 100)}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{stepsCompleted} / {stepsTotal} steps</span>
        <span className="font-medium text-slate-700 dark:text-slate-300">{Math.round(progress)}%</span>
      </div>
    </motion.div>
  );
}
