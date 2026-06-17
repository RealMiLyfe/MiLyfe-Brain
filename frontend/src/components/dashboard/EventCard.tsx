"use client";

import { motion } from "framer-motion";
import { clsx } from "clsx";
import {
  Zap,
  Brain,
  CheckCircle2,
  XCircle,
  Play,
  Wrench,
  Eye,
  ShieldAlert,
} from "lucide-react";
import type { StreamEvent } from "@/lib/api";

const EVENT_CONFIG: Record<string, { icon: typeof Zap; color: string; bg: string }> = {
  agent_spawned: { icon: Play, color: "text-green-500", bg: "bg-green-50 dark:bg-green-900/20" },
  step_started: { icon: Zap, color: "text-blue-500", bg: "bg-blue-50 dark:bg-blue-900/20" },
  step_completed: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-50 dark:bg-green-900/20" },
  step_failed: { icon: XCircle, color: "text-red-500", bg: "bg-red-50 dark:bg-red-900/20" },
  thought: { icon: Brain, color: "text-purple-500", bg: "bg-purple-50 dark:bg-purple-900/20" },
  action: { icon: Wrench, color: "text-amber-500", bg: "bg-amber-50 dark:bg-amber-900/20" },
  approval_required: { icon: ShieldAlert, color: "text-red-500", bg: "bg-red-50 dark:bg-red-900/20" },
  playbook_completed: { icon: CheckCircle2, color: "text-emerald-500", bg: "bg-emerald-50 dark:bg-emerald-900/20" },
  playbook_started: { icon: Play, color: "text-blue-500", bg: "bg-blue-50 dark:bg-blue-900/20" },
};

const ROLE_EMOJI: Record<string, string> = {
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

interface EventCardProps {
  event: StreamEvent;
  index: number;
}

export function EventCard({ event, index }: EventCardProps) {
  const config = EVENT_CONFIG[event.type] || EVENT_CONFIG.action || { icon: Eye, color: "text-slate-400", bg: "bg-slate-50 dark:bg-slate-800" };
  const Icon = config.icon;

  // Parse content for display
  let displayContent = event.type.replace(/_/g, " ");
  try {
    const data = JSON.parse(event.content);
    if (data.description) displayContent = data.description;
    else if (data.result_preview) displayContent = data.result_preview;
    else if (data.error) displayContent = `Error: ${data.error}`;
    else displayContent = event.type.replace(/_/g, " ");
  } catch {
    displayContent = event.content || event.type.replace(/_/g, " ");
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.02 }}
      className={clsx(
        "flex items-start gap-2.5 py-2 px-2.5 rounded-lg transition-colors",
        "hover:bg-slate-50 dark:hover:bg-slate-700/30"
      )}
    >
      {/* Icon */}
      <div className={clsx("w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5", config.bg)}>
        <Icon className={clsx("w-3.5 h-3.5", config.color)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          {event.agent_role && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-mono font-medium">
              {ROLE_EMOJI[event.agent_role] || event.agent_role}
            </span>
          )}
          <span className="text-xs font-medium text-slate-700 dark:text-slate-200 capitalize">
            {event.type.replace(/_/g, " ")}
          </span>
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
          {displayContent.slice(0, 150)}
        </p>
      </div>

      {/* Timestamp */}
      <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono whitespace-nowrap flex-shrink-0">
        {new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
      </span>
    </motion.div>
  );
}
