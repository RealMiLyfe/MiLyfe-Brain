"use client";

import { type PlaybookStep } from "@/lib/api";
import { User, Code, Search, FileText, Eye, TestTube, Rocket, Palette, BarChart3 } from "lucide-react";
import { motion } from "framer-motion";
import { clsx } from "clsx";

interface TaskGraphProps {
  steps: PlaybookStep[];
}

const ROLE_ICONS: Record<string, React.ElementType> = {
  planner: User,
  coder: Code,
  researcher: Search,
  writer: FileText,
  reviewer: Eye,
  tester: TestTube,
  deployer: Rocket,
  designer: Palette,
  data_analyst: BarChart3,
};

const STATUS_COLORS: Record<string, string> = {
  pending: "border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800",
  running: "border-blue-400 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/20",
  completed: "border-green-400 dark:border-green-500 bg-green-50 dark:bg-green-900/20",
  failed: "border-red-400 dark:border-red-500 bg-red-50 dark:bg-red-900/20",
  skipped: "border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-slate-800/50",
};

const DOT_COLORS: Record<string, string> = {
  pending: "bg-slate-400",
  running: "bg-blue-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
  skipped: "bg-slate-400",
};

export function TaskGraph({ steps }: TaskGraphProps) {
  if (!steps.length) {
    return (
      <div className="card text-center py-8 text-sm text-slate-400 dark:text-slate-500">
        No steps to visualize
      </div>
    );
  }

  return (
    <div className="card overflow-y-auto max-h-[500px]">
      <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200 mb-4">Task Flow</h3>
      <div className="relative pl-6">
        {/* Vertical line */}
        <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-slate-200 dark:bg-slate-700" />

        {steps.map((step, i) => {
          const Icon = ROLE_ICONS[step.agent_role || "planner"] || User;
          const isRunning = step.status === "running";

          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="relative flex items-start gap-3 mb-4 last:mb-0"
            >
              {/* Node dot */}
              <div className={clsx("absolute -left-6 top-3 w-3 h-3 rounded-full border-2 border-white dark:border-slate-900 z-10", DOT_COLORS[step.status])}>
                {isRunning && (
                  <motion.div
                    className="absolute inset-0 rounded-full bg-blue-400"
                    animate={{ scale: [1, 1.8, 1], opacity: [0.6, 0, 0.6] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                )}
              </div>

              {/* Step card */}
              <div className={clsx("flex-1 p-3 rounded-lg border-2 transition-colors", STATUS_COLORS[step.status])}>
                <div className="flex items-center gap-2">
                  <Icon className="w-4 h-4 text-slate-500 dark:text-slate-400 flex-shrink-0" />
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 capitalize">
                    {step.agent_role || "agent"}
                  </span>
                  <span className={clsx("ml-auto text-xs px-1.5 py-0.5 rounded font-medium", DOT_COLORS[step.status].replace("bg-", "text-"))}>
                    {step.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-700 dark:text-slate-300 line-clamp-2">
                  {step.name}
                </p>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
