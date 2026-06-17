"use client";

import { motion } from "framer-motion";
import { clsx } from "clsx";

interface AgentAvatarProps {
  role: string;
  name?: string;
  status?: "idle" | "active" | "busy" | "retired";
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

const ROLE_CONFIG: Record<
  string,
  { color: string; bgColor: string; emoji: string }
> = {
  planner: {
    color: "text-purple-500",
    bgColor: "bg-purple-100 dark:bg-purple-900/30",
    emoji: "🧠",
  },
  coder: {
    color: "text-cyan-500",
    bgColor: "bg-cyan-100 dark:bg-cyan-900/30",
    emoji: "💻",
  },
  reviewer: {
    color: "text-amber-500",
    bgColor: "bg-amber-100 dark:bg-amber-900/30",
    emoji: "🔍",
  },
  executor: {
    color: "text-emerald-500",
    bgColor: "bg-emerald-100 dark:bg-emerald-900/30",
    emoji: "⚡",
  },
  researcher: {
    color: "text-pink-500",
    bgColor: "bg-pink-100 dark:bg-pink-900/30",
    emoji: "🔬",
  },
  writer: {
    color: "text-orange-500",
    bgColor: "bg-orange-100 dark:bg-orange-900/30",
    emoji: "✍️",
  },
  tester: {
    color: "text-teal-500",
    bgColor: "bg-teal-100 dark:bg-teal-900/30",
    emoji: "🧪",
  },
  deployer: {
    color: "text-indigo-500",
    bgColor: "bg-indigo-100 dark:bg-indigo-900/30",
    emoji: "🚀",
  },
  monitor: {
    color: "text-lime-500",
    bgColor: "bg-lime-100 dark:bg-lime-900/30",
    emoji: "📊",
  },
};

const SIZE_CLASSES = {
  sm: "w-8 h-8 text-sm",
  md: "w-10 h-10 text-base",
  lg: "w-14 h-14 text-xl",
};

export function AgentAvatar({
  role,
  name,
  status = "idle",
  size = "md",
  showLabel = false,
}: AgentAvatarProps) {
  const config = ROLE_CONFIG[role.toLowerCase()] || ROLE_CONFIG.planner;
  const isActive = status === "active" || status === "busy";

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative">
        <motion.div
          animate={
            isActive
              ? {
                  scale: [1, 1.05, 1],
                  transition: { repeat: Infinity, duration: 2 },
                }
              : {}
          }
          className={clsx(
            "rounded-full flex items-center justify-center",
            config.bgColor,
            SIZE_CLASSES[size]
          )}
        >
          <span role="img" aria-label={role}>
            {config.emoji}
          </span>
        </motion.div>

        {/* Status indicator */}
        <span
          className={clsx(
            "absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white dark:border-slate-800",
            status === "active" && "bg-green-500",
            status === "busy" && "bg-amber-500",
            status === "idle" && "bg-slate-400",
            status === "retired" && "bg-red-400"
          )}
        />

        {/* Active pulse ring */}
        {isActive && (
          <motion.div
            animate={{
              scale: [1, 1.6],
              opacity: [0.5, 0],
            }}
            transition={{
              repeat: Infinity,
              duration: 1.5,
              ease: "easeOut",
            }}
            className={clsx(
              "absolute inset-0 rounded-full border-2",
              status === "active" && "border-green-400",
              status === "busy" && "border-amber-400"
            )}
          />
        )}
      </div>

      {showLabel && (
        <div className="text-center">
          <p className={clsx("text-xs font-medium capitalize", config.color)}>
            {role}
          </p>
          {name && (
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate max-w-[80px]">
              {name}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
